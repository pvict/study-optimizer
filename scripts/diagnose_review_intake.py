"""Diagnóstico protegido em RAM: fonte SQLite somente leitura; nenhuma cópia em disco."""
import argparse
from contextlib import contextmanager
from datetime import date
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def diagnose(label,baseline=None,report_difficulty=False):
    if not re.fullmatch(r'[a-z0-9-]{1,60}',label):raise ValueError('Use um nome simples para a evidencia, sem caminhos.')
    if baseline:
        import osler
        for name in ('review_policy','adaptive_planning','study_capacity'):
            code=subprocess.run(['git','show',f'{baseline}:osler/{name}.py'],cwd=ROOT,check=True,capture_output=True).stdout.decode('utf-8')
            module=types.ModuleType('osler.'+name);module.__package__='osler';module.__file__=str(ROOT/'osler'/f'{name}.py')
            sys.modules[module.__name__]=module;setattr(osler,name,module)
            exec(compile(code,module.__file__,'exec'),module.__dict__)
    from osler.storage import Repository
    from osler.workspace import active_data_dir
    from osler.adaptive_service import AdaptiveService
    from osler.planner_service import today_local
    from osler.topic_contacts import forecast_topic_contacts
    from osler.study_models import StudyEntry
    from osler.observations import Observation
    from osler.assessment_service import AssessmentService
    from osler.matching_service import load_matching
    root=active_data_dir(ROOT);memory=sqlite3.connect(':memory:');memory.row_factory=sqlite3.Row
    original=sqlite3.connect((root/'osler.sqlite3').as_uri()+'?mode=ro',uri=True)
    original.execute('PRAGMA query_only=ON');original.backup(memory);original.close()
    class MemoryRepository(Repository):
        def __init__(self):
            self.root=root;self.originals=root/'originals';self.exports=root/'exports';self.db_path=root/'osler.sqlite3'
        @contextmanager
        def _connection(self):
            with memory:yield memory
    try:
        repo=MemoryRepository();service=AdaptiveService(repo);day=today_local().isoformat()
        if report_difficulty:
            topics,sources=service.catalog(day)
            topic=next(t for t in topics if t['topic_id']=='eefb2166b39edd9e9df0128b')
            service.save_entry(StudyEntry(topic['path'],day,kind='contato',source='Relato do usuario: questoes realizadas com muita dificuldade, sem contagens informadas'),'relato-taquiarritmias-2026-10-28')
            matching=load_matching(repo,sources['qbank'],sources['flashcards'])
            row=next(r for r in matching.rows if (r.qbank or r.flashcards).path==topic['path'])
            assessment=AssessmentService(repo)
            assessment.save_observation(matching,row.row_id,Observation(day,'Relato do usuario nesta conversa','informado_usuario',
                dificuldade='alta',nota='Muita dificuldade ao realizar questoes de taquiarritmia hoje. Nenhuma taxa ou contagem informada.'),assessment.store.revision(row.row_id))
        view=service.overview(day);forecast=forecast_topic_contacts(service,view)
        rows=[]
        for state in view['planning_states']:
            contact=forecast['contacts'].get(state['topic_id'])
            rows.append({k:state.get(k) for k in ('topic_id','path','review_committed','initial_contact_deadline','last_contact','review_interval_days',
                         'priority','evidence_priority','learning_state','initial_rank','reported_difficulty')})
            rows[-1].update(contact=contact,wait=(date.fromisoformat(contact['date'])-date.fromisoformat(day)).days if contact else None)
        initial=[r['wait'] for r in rows if not r['review_committed'] and r['last_contact'] and r['wait'] is not None]
        initial.sort()
        output={'date':day,'baseline':baseline,'reported_difficulty_in_memory':report_difficulty,'coverage':forecast['coverage'],
                'profile':{k:view['profile'][k] for k in ('max_questions','max_topics','new_share','workload_mode','review_strategy')},
                'known_initial_contacts':{'count':len(initial),'median_wait':initial[len(initial)//2] if initial else None,
                    'p90_wait':initial[min(len(initial)-1,int(len(initial)*.9))] if initial else None,
                    'over_30_days':sum(n>30 for n in initial),'over_90_days':sum(n>90 for n in initial)},'rows':rows}
        folder=ROOT/'evidencias/taquiarritmias';folder.mkdir(exist_ok=True)
        (folder/(label+'.json')).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
        target=next(r for r in rows if r['topic_id']=='eefb2166b39edd9e9df0128b')
        print(json.dumps({'label':label,'coverage':output['coverage'],'known_initial_contacts':output['known_initial_contacts'],'target':target},ensure_ascii=True,indent=2))
    finally:memory.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    parser.add_argument('--baseline');parser.add_argument('--report-difficulty',action='store_true')
    args=parser.parse_args();diagnose(args.label,args.baseline,args.report_difficulty)
