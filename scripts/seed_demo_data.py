"""Cenário SINTÉTICO para revisão visual. Nunca usa a pasta de dados do usuário.

Uso: python scripts/seed_demo_data.py <pasta-nova-no-temporario> [--as-of AAAA-MM-DD]
O chamador preserva as capturas e remove a pasta temporária ao concluir.
"""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

AREAS = {
    'Clínica Médica': ['Insuficiência Cardíaca','Miocardite','Diabetes Mellitus','Pneumonia','Asma','Hipertensão Arterial','Anemia','Doença Renal Crônica'],
    'Clínica Cirúrgica': ['Apendicite','Diverticulite','Pancreatite Aguda','Abdome Agudo Obstrutivo','Cicatrização e Avaliação de Feridas','Trauma Torácico','Hérnias','Queimaduras'],
    'Pediatria': ['Imunizações','Cardiopatias Congênitas','Bronquiolite','Desidratação','Crescimento Infantil','Imunodeficiências Primárias','Icterícia Neonatal','Desenvolvimento Infantil'],
    'Ginecologia e Obstetrícia': ['Contracepção','Pré-Natal de Baixo Risco','Trabalho de Parto','Climatério e Menopausa','Síndrome dos Ovários Policísticos','Hemorragia Pós-Parto','Vaginose Bacteriana','Câncer de Mama'],
    'Preventiva & Social': ['Estudos Epidemiológicos','Bioestatística','Saúde do Trabalhador','Vigilância Epidemiológica','Organização Jurídica do SUS','Atributos da APS','Indicadores de Saúde','Medidas de Associação'],
}


def _destination(destination):
    raw=Path(destination).absolute()
    for p in [raw,*raw.parents]:
        try:
            # Reparse points incluem junções no Windows, também no Python3.11
            # (Path.is_junction só foi acrescentado no Python3.12).
            if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:
                raise ValueError('Use uma pasta temporária nova, sem links ou junções.')
        except FileNotFoundError:continue
    target=raw.resolve();temporary=Path(tempfile.gettempdir()).resolve()
    if target==temporary or not target.is_relative_to(temporary) or 'data' in [p.casefold() for p in target.parts]:
        raise ValueError('O cenário só pode ser criado em uma nova subpasta temporária; data/ é proibida.')
    if target.exists() or any((p/'osler.sqlite3').exists() for p in target.parents):
        raise ValueError('Destino existente ou banco encontrado. Nenhum dado foi alterado.')
    return target


def _pdf(kind,observed):
    """Mesmo layout documental dos fixtures, ampliado para cinco áreas."""
    import pymupdf
    doc=pymupdf.open();title='Qbank' if kind=='qbank' else 'Flashcards'
    counts=[(name,[(topic,0 if j%3==0 else 20+2*j) for j,topic in enumerate(topics)]) for name,topics in AREAS.items()]
    total=4000 if kind=='qbank' else 6400
    studied=sum(n if kind=='qbank' else (80 if n else 0) for _,topics in counts for _,n in topics)
    cover=doc.new_page();cover.insert_text((48,50),observed.strftime('%d/%m/%Y'))
    cover.insert_text((48,80),title.upper()+' - ACERVO & ACURÁCIA')
    cover.insert_text((48,110),'Detalhado por área - 40 temas no acervo')
    cover.insert_text((48,140),f'{studied} de {total} '+('questões respondidas' if kind=='qbank' else 'cards feitos'))
    cover.insert_text((48,160),f'{studied//2} de {studied} feitos já vistos 2+ vezes' if kind=='flashcards' else f'{int(studied*.8)} acertos em {studied} respondidas')
    for area,topics in counts:
        page=doc.new_page();page.insert_text((48,60),f'Estatísticas > {title} > Acervo & acurácia')
        page.insert_text((48,78),'Todos · '+observed.strftime('%d/%m/%Y'))
        page.insert_text((48,112),'Tema')
        for x,text in zip([320,385,462,515],['Questões' if kind=='qbank' else 'Cards','Respondidas' if kind=='qbank' else 'Feitos','% visto','% acerto' if kind=='qbank' else '% revisado']):
            page.insert_text((x,112),text,fontsize=8)
        def row(y,level,name,available,done,metric):
            page.insert_text((48+10.5*level,y),name,fontsize=9)
            for x,text in zip([330,402,472,530],[str(available),str(done),f'{100*done/available:.0f}%',metric]):page.insert_text((x,y),text,fontsize=9)
        area_studied=sum(n if kind=='qbank' else (80 if n else 0) for _,n in topics)
        row(145,0,area,800 if kind=='qbank' else 1280,area_studied,'80%')
        for j,(topic,n) in enumerate(topics):
            done=n if kind=='qbank' else (80 if n else 0)
            row(167+22*j,1,topic,100 if kind=='qbank' else 160,done,f'{55+5*j}%' if done else '-')
    result=doc.tobytes();doc.close();return result


def seed_demo_data(destination,as_of):
    target=_destination(destination)
    if type(as_of) is not date:raise ValueError('Informe uma data válida para o cenário sintético.')
    from osler.planner_service import today_local
    if as_of>today_local():raise ValueError('O cenário não pode registrar estudo futuro.')
    from osler.storage import Repository
    from osler.service import import_bytes
    from osler.adaptive_service import AdaptiveService
    from osler.study_models import AdaptiveProfile,StudyDay,StudyEntry
    from osler.study_errors import ErrorStore,StudyError
    from osler.exam_goals import ExamGoals,ExamTarget
    from osler.mock_exams import MockExams,MockExam
    target.mkdir(parents=True,exist_ok=False);repo=Repository(target)
    for kind in ('qbank','flashcards'):
        import_bytes(repo,_pdf(kind,as_of-timedelta(days=14)),f'SINTETICO-{kind}.pdf')
    service=AdaptiveService(repo);topics,_=service.catalog(as_of.isoformat())
    if len(topics)!=40:raise ValueError('O cenário sintético não produziu os 40 temas esperados.')
    service.store.save_profile(AdaptiveProfile(max_questions=120,max_topics=6,new_share=.5,
        start_date=(as_of-timedelta(days=13)).isoformat(),exam_date=(as_of+timedelta(days=365)).isoformat()),0)
    for i in range(14):
        day=(as_of-timedelta(days=13-i)).isoformat()
        if i==6:
            service.store.save_day(day,StudyDay(questions=120,kind='descanso'),0);continue
        n=10 if i==9 else 20 if i==13 else 40
        correct=round(n*(.55+.4*(i%9)/8))
        service.save_entry(StudyEntry(topics[(i*3)%40]['path'],day,n,correct,
            confident_correct=max(0,correct-n//10),minutes=float(n*2),mode='novas' if i%4 else 'repetidas',source='Cenário sintético de revisão visual'),f'demo-{i}')
    for i in range(3):ErrorStore(repo).save(StudyError(topics[i]['path'],as_of.isoformat(),'lacuna_de_conteudo','Registro sintético para revisão visual.'))
    exam=ExamGoals(repo).save(ExamTarget('Instituição de demonstração',(as_of+timedelta(days=365)).isoformat(),75,100,'Fonte sintética para teste visual'))
    MockExams(repo).save(MockExam(day=(as_of-timedelta(days=2)).isoformat(),questions=100,correct=76,
        name='Simulado sintético',institution='Instituição de demonstração',target_id=exam['target_id'],minutes_used=240,
        areas=[{'area':area,'questions':20,'correct':n} for area,n in zip(AREAS,[18,16,14,15,13])]))
    result={'synthetic':True,'topics':40,'areas':5,'study_days':13,'as_of':as_of.isoformat(),'directory':str(target)}
    (target/'SYNTHETIC-DEMO.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    from osler.planner_service import today_local
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    parser.add_argument('--as-of',type=date.fromisoformat,default=today_local());args=parser.parse_args()
    try:print(json.dumps(seed_demo_data(args.destination,args.as_of),ensure_ascii=False))
    except ValueError as exc:parser.exit(2,str(exc)+'\n')
