"""Valores capturados no lote B, antes de centralizar os parâmetros."""
from dataclasses import asdict
import json
from pathlib import Path
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_models import AdaptiveProfile,StudyEntry


def cases():
    def topic(name,total=100,answered=0):
        return {'topic_id':name,'path':['Área',name],'total':total,'answered_pdf':answered,
                'pdf_accuracy':{'value':85 if answered else None,'operator':'=','raw':'85%' if answered else '-'},
                'report_date':'2026-09-30','studied_cards':0}
    def session(day,n,correct,confident,mode='novas',name='A'):
        entry=StudyEntry(['Área',name],day,n,correct,mode=mode,confident_correct=confident).to_dict()
        return {'id':int(day[-2:]),'session_id':name+day,'version':1,'entry':entry}
    topics=[topic('A'),topic('B',30,10),topic('C',5)]
    samples=[[],[session('2026-10-01',30,29,29)],
             [session('2026-10-01',30,29,29),session('2026-10-08',30,29,29)],
             [session('2026-10-01',30,20,10)],
             [session('2026-10-01',10,9,None)],
             [session('2026-10-01',30,30,30),session('2026-10-08',30,30,30,'repetidas')],
             [session('2026-10-01',20,15,12,'mistas')]]
    for i,sessions in enumerate(samples):
        for mode in ('fixed','adaptive'):
            yield {'name':str(i)+'-'+mode,'topics':topics,'sessions':sessions,
                   'profile':asdict(AdaptiveProfile(max_questions=60,max_topics=3,new_share=.5,workload_mode=mode)),
                   'datasets':[{'id':1,'institutions':['X'],'unit':'questoes','observed_date':'2026-10-01',
                                'rows':[{'path':['Área','A'],'value':40,'band':'alta'},{'path':['Área','B'],'value':10,'band':'baixa'}]}]}


def outputs(case):
    profile=AdaptiveProfile(**case['profile'])
    states=topic_states(case['topics'],case['sessions'],case['datasets'],{},'2026-10-15',profile)
    fields=('topic_id','performance','confidence','spacing','priority','evidence_priority','score','importance',
            'next_review','review_interval_days','recommended_questions','dose_kind','learning_state','available_new')
    plan=allocate_day(states,profile,None,'normal',case['sessions'],'2026-10-15',question_target=60)
    return {'states':[{k:t[k] for k in fields} for t in states],
            'items':[{k:i[k] for k in ('topic_id','questions','new_questions','repeat_questions')} for i in plan['items']],
            'questions':plan['questions'],'target_questions':plan['target_questions'],'distribution':plan['distribution']}


def test_parameters_v1_keep_lote_b_statistical_evidence_and_intervals():
    expected=json.loads((Path(__file__).parent/'fixtures/algorithm_v1_baseline.json').read_text(encoding='utf-8'))
    for case in cases():
        actual=outputs(case);original=expected[case['name']]
        # A política4.3 inclui o acervo C de5 questões antes excluído. O golden
        # original fica imutável para proteger estimativas, intervalos e metas.
        # A política4.5 corrige prioridade operacional; as estimativas, doses
        # e intervalos do golden permanecem protegidos, independentemente da ordem.
        operational={'priority','evidence_priority'}
        evidence=lambda rows:sorted([{k:v for k,v in r.items() if k not in operational} for r in rows],key=lambda r:r['topic_id'])
        assert evidence(actual['states'])==evidence(original['states'])
        assert actual['target_questions']==original['target_questions']
        assert actual['questions']<=actual['target_questions']
        totals={t['topic_id']:t['total'] for t in case['topics']}
        assert all(i['questions']>=10 or i['questions']==totals[i['topic_id']]<10 for i in actual['items'])
