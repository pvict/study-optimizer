"""Retomada por quantidades, sem inventar questões, acertos ou vencimentos."""
from datetime import date,timedelta
from collections import defaultdict
from copy import deepcopy
import json

EXCLUSIVE={'mock_day','mock_reserved','final_rest','final_review','external_day'}


def available(day,settings,overrides):
    return settings.get(day,{}).get('kind')!='descanso' and overrides.get(day,{}).get('mode') not in EXCLUSIVE


def project_questions(remaining,daily,start,end,settings,overrides):
    rows={};current=date.fromisoformat(start)
    while current<=date.fromisoformat(end) and remaining:
        day=current.isoformat()
        if available(day,settings,overrides):
            n=min(remaining,daily);rows[day]=n;remaining-=n
        current+=timedelta(days=1)
    return rows


def project_decks(topics,covered,start,end,settings,overrides,target=50,ceiling=70,done_today=0):
    pending=[{**t,'count':max(0,t['count']-covered.get(t['topic_id'],0))} for t in topics]
    pending=[t for t in pending if t['count']];rows=[];current=date.fromisoformat(start)
    while pending and current<=date.fromisoformat(end):
        day=current.isoformat()
        if available(day,settings,overrides) and not (day==start and done_today>=target):
            daily_target=max(0,target-done_today) if day==start else target
            daily_ceiling=max(0,ceiling-done_today) if day==start else ceiling
            big=[t for t in pending if t['count']>ceiling]
            small=[t for t in pending if t['count']<=daily_ceiling]
            chosen=[]
            if big and (day!=start or not done_today) and (current.weekday()==5 or not small):chosen=[big[0]]
            elif small:
                chosen=[small[0]];n=chosen[0]['count']
                while n<daily_target:
                    fits=[t for t in small if t not in chosen and n+t['count']<=daily_ceiling]
                    if not fits:break
                    item=min(fits,key=lambda t:abs(daily_target-n-t['count']))
                    if n>=40 and abs(daily_target-n)<abs(daily_target-n-item['count']):break
                    chosen.append(item);n+=item['count']
            if chosen:
                rows.append({'date':day,'cards':sum(t['count'] for t in chosen),'decks':chosen})
                ids={t['topic_id'] for t in chosen};pending=[t for t in pending if t['topic_id'] not in ids]
        current+=timedelta(days=1)
    return rows


class RecoveryService:
    def __init__(self,repo):self.repo=repo

    def events(self):
        with self.repo._connection() as db:
            return [dict(id=r['id'],**json.loads(r['payload'])) for r in db.execute(
                "SELECT id,payload FROM study_plan_runs WHERE json_extract(payload,'$.kind') LIKE 'recovery.quantity.%' ORDER BY id")]

    def settings(self):
        return next((e for e in reversed(self.events()) if e['kind']=='recovery.quantity.settings'),None)

    def save(self,total,daily,limit,card_target,card_ceiling,start,token,topics=(),snapshot_id=0):
        for n in [total,daily,limit,card_target,card_ceiling]:
            if type(n) is not int:raise ValueError('Informe quantidades inteiras.')
        if not 0<=total<=100000 or not 1<=daily<limit<=1000 or not 1<=card_target<=card_ceiling<=2000:
            raise ValueError('Confira as metas; a cota de revisões deve ser menor que a carga total.')
        from .planner_service import today_local
        if start<today_local().isoformat():raise ValueError('Escolha hoje ou uma data futura.')
        date.fromisoformat(start)
        from .study_agenda import StudyAgenda
        from .study_storage import StudyStore
        agenda=StudyAgenda(self.repo)
        return agenda.append({'kind':'recovery.quantity.settings','total':total,'daily':daily,'limit':limit,
            'card_target':card_target,'card_ceiling':card_ceiling,'start':start,
            'topics':list(topics),'snapshot_id':snapshot_id,'previous_token':token},token)

    def record(self,day,count,token):
        from .planner_service import today_local
        config=self.settings()
        if not config or not config['start']<=day<=today_local().isoformat():raise ValueError('Data fora da retomada.')
        events=self.events();used=sum(e['count'] for e in events if e['kind']=='recovery.quantity.done' and e['plan_id']==config['id'])
        done=sum(e['count'] for e in events if e['kind']=='recovery.quantity.done' and e['plan_id']==config['id'] and e['day']==day)
        if type(count) is not int or not 0<count<=min(config['daily']-done,config['total']-used):
            raise ValueError('Quantidade acima da cota diária ou do saldo disponível.')
        from .adaptive_service import AdaptiveService
        view=AdaptiveService(self.repo).overview(day)
        room=max(0,view['plan']['routine_override'].get('recovery_reserved',0)-done)
        if count>room:raise ValueError('Essa quantidade ultrapassa o espaço restante na carga total de hoje.')
        from .study_agenda import StudyAgenda
        from .study_storage import StudyStore
        return StudyAgenda(self.repo).append(
            {'kind':'recovery.quantity.done','plan_id':config['id'],'day':day,'count':count,'sequence':len(events)},token)

    def projection(self,as_of,settings,overrides,end,config=None):
        config=config or self.settings()
        if not config:return None
        from .planner_service import today_local
        anchor=max(config['start'],min(as_of,today_local().isoformat()))
        events=[e for e in self.events() if e['kind']=='recovery.quantity.done' and e['plan_id']==config['id'] and e['day']<=anchor]
        used=sum(e['count'] for e in events);done=sum(e['count'] for e in events if e['day']==anchor)
        remaining=max(0,config['total']-used)
        covered=defaultdict(int);cards_done=0;large_studied=set()
        if config['topics']:
            from .error_cards_service import ErrorCardsService
            original_counts={t['topic_id']:t['count'] for t in config['topics']}
            for row in ErrorCardsService(self.repo).history():
                if not row['voided'] and row['snapshot_id']==config['snapshot_id'] and row['day']<=anchor:
                    covered[row['topic_id']]+=row['covered']
                    if row['day']==anchor:cards_done+=row['covered']+row['repeats']
                    if original_counts.get(row['topic_id'],0)>config['card_ceiling']:
                        large_studied.add(row['day'])
        decks=project_decks(config['topics'],covered,anchor,end,settings,overrides,config['card_target'],config['card_ceiling'],cards_done)
        # Capacidade externa depende também de treinos e dos dias de deck grande.
        large={r['date'] for r in decks if r['cards']>config['card_ceiling']}|large_studied
        from .study_storage import StudyStore
        ordinary=sum(r['entry']['questions'] for r in StudyStore(self.repo).active(anchor)
                     if r['entry']['day']==anchor and r['entry']['kind']=='bloco')
        questions={};left=remaining;current=date.fromisoformat(anchor)
        while left and current<=date.fromisoformat(end):
            day=current.isoformat()
            if available(day,settings,overrides):
                cap=min(config['limit'],30) if day in large else config['limit']
                cap=min(settings.get(day,{}).get('questions',cap),cap)
                room=max(0,cap-overrides.get(day,{}).get('area_reserved',0)-(ordinary if day==anchor else 0))
                n=min(left,max(0,config['daily']-(done if day==anchor else 0)),max(0,room-(done if day==anchor else 0)))
                if n:questions[day]=n;left-=n
            current+=timedelta(days=1)
        # Reservas não mudam de ordem só porque o calendário pediu uma data futura.
        return {'config':config,'remaining':remaining,'done_today':done if as_of==anchor else 0,'questions':questions,'decks':decks,'anchor':anchor,'large_days':sorted(large),
                'unassigned_questions':left,'unassigned_cards':sum(max(0,t['count']-covered[t['topic_id']]) for t in config['topics'])-sum(r['cards'] for r in decks)}

    def decorate(self,as_of,settings,overrides,end):
        projection=self.projection(as_of,settings,overrides,end)
        if not projection:return overrides,None
        result=deepcopy(overrides);c=projection['config'];start=projection['anchor']
        large=set(projection['large_days'])
        current=date.fromisoformat(start)
        while current<=date.fromisoformat(end):
            day=current.isoformat()
            if available(day,settings,overrides):
                reserved=projection['questions'].get(day,0)+(projection['done_today'] if day==as_of else 0)
                limit=min(c['limit'],30) if day in large else c['limit']
                # Treinos por área já reservados não podem ultrapassar o total.
                reserved=min(reserved,max(0,limit-result.get(day,{}).get('area_reserved',0)))
                result[day]={**result.get(day,{}),'recovery_limit':limit,'recovery_reserved':reserved}
            current+=timedelta(days=1)
        return result,projection
