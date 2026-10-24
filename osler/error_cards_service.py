"""Lotes e realizações de cards pessoais, separados das sessões de questões."""
from collections import defaultdict
from copy import deepcopy
from datetime import date,timedelta
import hashlib
import json
import re

from .error_cards import parse_error_cards,plan_error_cards
from .files import write_immutable
from .planner_service import today_local
from .storage import utc_now
from .study_storage import StudyStore,_encoded
from .models import stable_topic_id


def _expansion_parent(unresolved,path):
    exact=[r for r in unresolved if r['path']==path]
    matches=exact or [r for r in unresolved if stable_topic_id(r['path'])==stable_topic_id(path)]
    if len(matches)!=1:raise ValueError('Grupo ausente ou ambíguo. Use o caminho original completo do grupo.')
    return matches[0]


def expanded_snapshot(events):
    original=next((r for r in reversed(events) if r['kind']=='error_cards.snapshot'),None)
    if not original:return None
    snapshot=deepcopy(original);tree=snapshot['tree'];snapshot['supplements']=[]
    for event in events:
        if event['kind']!='error_cards.expand' or event['snapshot_id']!=snapshot['id']:continue
        for resolution in event['resolutions']:
            parent=_expansion_parent(tree['unresolved'],resolution['parent_path'])
            if sum(c['count'] for c in resolution['children'])!=parent['count']:raise ValueError('As contagens do complemento não conferem com o grupo original.')
            parent_node=next(n for n in tree['nodes'] if n['path']==parent['path'])
            children=[]
            for child in resolution['children']:
                path=parent['path']+[child['name']]
                children.append({'topic_id':stable_topic_id(path),'path':path,'label':child['name'],'count':child['count'],
                                 'indent':parent_node['indent']+20,'branch':False,'has_children':False,'specific':True,'source_paths':[path]})
            tree['topics'].extend(children)
            pos=tree['nodes'].index(parent_node)+1;tree['nodes'][pos:pos]=deepcopy(children)
            parent_node['has_children']=True
            tree['unresolved'].remove(parent)
        snapshot['supplements'].append({'source':event['source'],'filename':event['filename'],'sha256':event['sha256']})
    tree['schedulable']=sum(t['count'] for t in tree['topics']);tree['unallocated']=sum(r['count'] for r in tree['unresolved'])
    if tree['total']!=tree['schedulable']+tree['unallocated']:raise ValueError('As contagens do lote não conferem após o complemento.')
    return snapshot


class ErrorCardsService:
    def __init__(self,repo):
        self.repo=repo; StudyStore(repo)

    def _events(self,db=None):
        if db is None:
            with self.repo._connection() as connection:return self._events(connection)
        return [{'id':r['id'],**json.loads(r['payload'])} for r in db.execute(
            "SELECT id,payload FROM study_plan_runs WHERE json_extract(payload,'$.kind') LIKE 'error_cards.%' ORDER BY id")]

    def token(self):return max((r['id'] for r in self._events()),default=0)

    def _append(self,payload,token,validate=None):
        encoded=_encoded(payload); digest=hashlib.sha256(encoded.encode()).hexdigest()
        with self.repo._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            duplicate=db.execute('SELECT id FROM study_plan_runs WHERE digest=?',(digest,)).fetchone()
            if duplicate:return duplicate['id']
            events=self._events(db)
            if max((r['id'] for r in events),default=0)!=token:raise ValueError('Os cards foram atualizados em outra tela. Atualize a página antes de salvar.')
            if validate:validate(events)
            return db.execute('INSERT INTO study_plan_runs(payload,digest,created_at) VALUES(?,?,?)',(encoded,digest,utc_now())).lastrowid

    def latest_snapshot(self):
        return expanded_snapshot(self._events())

    def expand_groups(self,resolutions,evidence,filename,token):
        if not isinstance(resolutions,list) or not resolutions or len(resolutions)>100:raise ValueError('Informe os grupos e seus subtemas específicos.')
        if not isinstance(evidence,bytes) or not evidence.startswith(b'\x89PNG\r\n\x1a\n') or len(evidence)>20*1024*1024:raise ValueError('Preserve o print original em PNG, de até20 MB.')
        for r in resolutions:
            if not isinstance(r,dict) or not isinstance(r.get('parent_path'),list) or not r['parent_path'] or any(not isinstance(p,str) or not p.strip() for p in r['parent_path']):raise ValueError('Caminho do grupo inválido.')
            if not isinstance(r.get('children'),list) or not r['children']:raise ValueError('Informe os filhos do grupo.')
            for child in r['children']:
                if not isinstance(child,dict) or not isinstance(child.get('name'),str) or not child['name'].strip() or len(child['name'])>300 or type(child.get('count')) is not int or child['count']<0:raise ValueError('Subtema ou contagem inválidos.')
        snapshot=self.latest_snapshot()
        if not snapshot:raise ValueError('Importe a árvore original antes de completar os grupos.')
        digest=hashlib.sha256(evidence).hexdigest()
        payload={'kind':'error_cards.expand','snapshot_id':snapshot['id'],'resolutions':resolutions,'sha256':digest,
                 'filename':str(filename)[:200],'source':'exports/error-cards/'+digest+'.png'}
        def validate(events):
            current=expanded_snapshot(events)
            if current['id']!=snapshot['id']:raise ValueError('O retrato mudou. Confira novamente os grupos antes de completar.')
            seen=set()
            existing={t['topic_id'] for t in current['tree']['topics']}
            for r in resolutions:
                parent=_expansion_parent(current['tree']['unresolved'],r['parent_path']);key=tuple(parent['path'])
                if key in seen:raise ValueError('Esse grupo já foi completado ou não consta entre os grupos sem subtema.')
                seen.add(key)
                if sum(c['count'] for c in r['children'])!=parent['count']:raise ValueError('A soma dos subtemas deve ser igual à contagem que faltava no grupo.')
                for child in r['children']:
                    child_id=stable_topic_id(parent['path']+[child['name']])
                    if child_id in existing:raise ValueError('Subtema repetido. Nenhuma contagem foi acrescentada.')
                    existing.add(child_id)
        for event in self._events():
            if {k:v for k,v in event.items() if k!='id'}==payload:return event['id']
        validate(self._events())
        folder=self.repo.exports/'error-cards';folder.mkdir(exist_ok=True);write_immutable(folder/(digest+'.png'),evidence)
        return self._append(payload,token,validate)

    def import_html(self,data,filename,day,scope,token):
        if scope not in {'inventory','pending','pass'}:raise ValueError('Informe se o arquivo é inventário ou lote a estudar.')
        self._day(day)
        if len(data)>20*1024*1024:raise ValueError('O arquivo deve ter até20 MB.')
        try:tree=parse_error_cards(data.decode('utf-8-sig'))
        except UnicodeDecodeError as exc:raise ValueError('Salve o HTML em UTF-8 antes de importar.') from exc
        digest=hashlib.sha256(data).hexdigest()
        for previous in self._events():
            if previous['kind']=='error_cards.snapshot' and previous['sha256']==digest and previous['scope']==scope:return previous['id']
        folder=self.repo.exports/'error-cards';folder.mkdir(exist_ok=True)
        write_immutable(folder/(digest+'.html'),data)
        return self._append({'kind':'error_cards.snapshot','sha256':digest,'filename':str(filename)[:200],
                             'observed_day':day,'scope':scope,'tree':tree,'source':'exports/error-cards/'+digest+'.html'},token)

    def settings(self):
        return next((r for r in reversed(self._events()) if r['kind']=='error_cards.settings'),{'daily':200,'days':{}})

    def configure(self,daily,days,token):
        if type(daily) is not int or not 0<=daily<=2000:raise ValueError('Escolha de0 a2000 cards por dia.')
        if not isinstance(days,dict):raise ValueError('Ajustes de dias inválidos.')
        for day,n in days.items():
            date.fromisoformat(day)
            if type(n) is not int or not 0<=n<=2000:raise ValueError('Escolha de0 a2000 cards por dia.')
        return self._append({'kind':'error_cards.settings','daily':daily,'days':days,'previous_token':token},token)

    @staticmethod
    def _day(day):
        if not isinstance(day,str) or date.fromisoformat(day).isoformat()!=day or day>today_local().isoformat():raise ValueError('Use uma data de estudo de hoje ou anterior.')

    @staticmethod
    def _history(events):
        voided={r['event_id'] for r in events if r['kind']=='error_cards.void'}
        return [{**r,'voided':r['id'] in voided} for r in events if r['kind']=='error_cards.session']

    def history(self):return self._history(self._events())

    def record(self,topic_id,day,covered,repeats,recalled,session_key,token):
        self._day(day)
        if any(type(n) is not int or not 0<=n<=5000 for n in (covered,repeats)) or covered+repeats==0:raise ValueError('Informe os cards estudados, sem duplicar repetições.')
        if recalled is not None and (type(recalled) is not int or not 0<=recalled<=covered+repeats):raise ValueError('Lembrados deve estar entre0 e o total de respostas.')
        if not isinstance(session_key,str) or not re.fullmatch(r'[\w.-]{1,128}',session_key):raise ValueError('Identificação do registro inválida.')
        snapshot=self.latest_snapshot()
        if not snapshot or snapshot['scope']=='inventory':raise ValueError('Importe um lote de pendentes ou escolha uma nova passagem antes de registrar.')
        topics={t['topic_id']:t for t in snapshot['tree']['topics']}
        if topic_id not in topics or day<snapshot['observed_day']:raise ValueError('Escolha um tema específico e uma data a partir do retrato importado.')
        def validate(events):
            if any(r.get('session_key')==session_key for r in events):raise ValueError('Este identificador já foi usado. Inicie outro registro.')
            done=sum(r['covered'] for r in self._history(events) if not r['voided'] and r['snapshot_id']==snapshot['id'] and r['topic_id']==topic_id)
            if done+covered>topics[topic_id]['count']:raise ValueError('Há mais cards diferentes que o saldo do tema. Informe repetições no campo separado ou importe um novo retrato.')
        return self._append({'kind':'error_cards.session','snapshot_id':snapshot['id'],'session_key':session_key,
                             'topic_id':topic_id,'path':topics[topic_id]['path'],'day':day,'covered':covered,'repeats':repeats,'recalled':recalled},token,validate)

    def undo(self,event_id,token):
        if not any(r['id']==event_id and not r['voided'] for r in self.history()):raise ValueError('Este registro já foi desfeito ou não existe.')
        return self._append({'kind':'error_cards.void','event_id':event_id},token)

    def routine(self):
        from .adaptive_service import AdaptiveService
        q=AdaptiveService(self.repo);day=today_local().isoformat()
        return {'profile':q.store.profile()['profile'],'days':q.store.days(),'overrides':q.agenda.active(q.store.active(day),day)['overrides']}

    def capacity(self,day,routine,settings=None):
        settings=settings or self.settings(); profile=routine['profile']
        if day in settings['days']:return settings['days'][day],'Carga escolhida para este dia'
        if profile.get('start_date') and day<profile['start_date'] or day>profile['exam_date']:return 0,'Fora do período de preparação'
        config=routine['days'].get(day,{})
        if config.get('kind')=='descanso':return 0,'Descanso'
        mode=routine['overrides'].get(day,{}).get('mode')
        if mode in {'mock_day','mock_reserved','final_rest'}:return 0,'Simulado ou descanso reservado'
        return settings['daily'],'Carga habitual de cards de erros'

    def overview(self,day=None,question_view=None,routine=None):
        day=day or today_local().isoformat();events=self._events()
        snapshot=expanded_snapshot(events)
        settings=next((r for r in reversed(events) if r['kind']=='error_cards.settings'),{'daily':200,'days':{}})
        if question_view is None:
            from .adaptive_service import AdaptiveService
            question_view=AdaptiveService(self.repo).overview(day)
        routine=routine or self.routine(); budget,reason=self.capacity(day,routine,settings)
        qp=question_view.get('plan',{})
        if day not in settings['days'] and (qp.get('kind')=='descanso' or qp.get('not_started')):budget=0;reason='Descanso, simulado ou antes do início'
        history=[r for r in self._history(events) if not r['voided'] and r['day']<=day]
        done=sum(r['covered']+r['repeats'] for r in history if r['day']==day)
        progress=defaultdict(lambda:{'covered':0,'last_day':None}); covered=0
        if snapshot:
            for r in history:
                if r['snapshot_id']!=snapshot['id']:continue
                p=progress[r['topic_id']];p['covered']+=r['covered'];p['last_day']=max(p['last_day'] or '',r['day']);covered+=r['covered']
        active=bool(snapshot and snapshot['scope']!='inventory' and day>=snapshot['observed_day'])
        ranked=plan_error_cards(snapshot['tree']['topics'],progress,question_view.get('states',[]),day,max(0,budget-done),
            [i['topic_id'] for i in qp.get('items',[])],snapshot['observed_day'],reference_budget=budget,completed_today=done) if active else []
        remaining=max(0,snapshot['tree']['schedulable']-covered) if snapshot else 0
        return {'snapshot':snapshot,'settings':settings,'budget':budget,'budget_reason':reason,'done_today':done,'covered':covered,
                'remaining':remaining,'unallocated':snapshot['tree']['unallocated'] if snapshot else 0,
                'items':[t for t in ranked if t['planned']],'ranked':ranked,'progress':dict(progress),'history':history,
                'active':active,'token':max((r['id'] for r in events),default=0),'routine':routine,'question_view':question_view}

    def forecast(self,view,horizon=120):
        if not view['active']:return {'days':[],'completion':None,'remaining':view['remaining']}
        snapshot=view['snapshot']; progress={k:dict(v) for k,v in view['progress'].items()}; rows=[]
        current=today_local(); end=min(current+timedelta(days=horizon-1),date.fromisoformat(view['routine']['profile']['exam_date']))
        while current<=end:
            day=current.isoformat();capacity,reason=self.capacity(day,view['routine'],view['settings']);reference=capacity
            if current==today_local():capacity=max(0,capacity-view['done_today'])
            question_ids=[i['topic_id'] for i in view['question_view'].get('plan',{}).get('items',[])] if current==today_local() else []
            ranked=plan_error_cards(snapshot['tree']['topics'],progress,view['question_view'].get('states',[]),day,capacity,question_ids=question_ids,snapshot_day=snapshot['observed_day'],reference_budget=reference,completed_today=view['done_today'] if current==today_local() else 0)
            items=[t for t in ranked if t['planned']]
            for t in items:
                p=progress.setdefault(t['topic_id'],{'covered':0,'last_day':None});p['covered']+=t['planned'];p['last_day']=day
            remaining=sum(max(0,t['count']-progress.get(t['topic_id'],{}).get('covered',0)) for t in snapshot['tree']['topics'])
            rows.append({'date':day,'cards':sum(t['planned'] for t in items),'items':items,'remaining':remaining,'reason':reason})
            if not remaining:return {'days':rows,'completion':day,'remaining':0}
            current+=timedelta(days=1)
        return {'days':rows,'completion':None,'remaining':rows[-1]['remaining'] if rows else view['remaining']}
