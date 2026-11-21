"""Prévia completa, backup e configuração versionada da fronteira de revisões."""
from dataclasses import replace
from .study_models import AdaptiveProfile
from .planner_service import today_local
from .planning import _date
from .study_calendar import forecast_calendar
from .topic_grouping import key
from .backups import create_backup


def history(service):
    return [r for r in service.agenda.records() if r.get('kind')=='grouping.change']


def calendar_rows(service,view,progress=None):
    p=AdaptiveProfile(**view['profile']);day=view['date']
    days=max(1,min(548,(_date(p.exam_date)-_date(day)).days+1))
    plans=forecast_calendar(view['planning_states'],p,day,days,view['sessions'],service.store.days(),view['plan'],view['agenda'],next_contact_only=True,progress=progress)
    return [{'date':plan['date'],'questions':plan['questions'],'target':plan['target_questions'],
             'items':[{'topic_id':i['topic_id'],'path':i['path'],'questions':i['questions'],
                       'members':i.get('group_member_paths',[])} for i in plan['items']],
             'override':plan.get('routine_override',{})} for plan in plans]


def preview_grouping(service,mode,paths=(),*,progress=None):
    token=service.agenda.token();record=service.store.profile();day=today_local().isoformat()
    p=replace(AdaptiveProfile(**record['profile']),grouping_mode=mode,grouping_paths=list(paths)).validate()
    if progress:progress('Preparando os dados',0,1)
    before=service.overview(day)
    allowed={key(r['path']) for r in before['grouping_candidates'] if r['eligible']}
    if mode=='custom' and any(key(path) not in allowed for path in paths):
        raise ValueError('Há uma categoria indisponível. Confira as justificativas e refaça a seleção.')
    after=service.overview(day,_profile_override=p.to_dict())
    a=calendar_rows(service,before,(lambda done,total:progress('Calendário atual',done,total)) if progress else None)
    b=calendar_rows(service,after,(lambda done,total:progress('Calendário proposto',done,total)) if progress else None)
    changes=[{'date':x['date'],'before':x,'after':y} for x,y in zip(a,b) if x!=y]
    if token!=service.agenda.token(): raise ValueError('Os dados mudaram. Gere outra prévia.')
    return {'mode':mode,'paths':list(paths),'token':token,'created_day':day,'profile_id':record['id'],
            'previous':{k:record['configured_profile'].get(k,default) for k,default in [('grouping_mode','osler'),('grouping_paths',[])]},
            'before_units':len(before['planning_states']),'after_units':len(after['planning_states']),
            'groups':[{'path':t['path'],'members':t['group_member_paths']} for t in after['planning_states'] if t.get('group_members')],
            'before_calendar':a,'after_calendar':b,'changes':changes,
            'conditional':True}


def apply_grouping(service,preview):
    if preview['token']!=service.agenda.token() or preview['created_day']!=today_local().isoformat():
        raise ValueError('Os dados mudaram. Refaça a prévia antes de aplicar.')
    if preview_grouping(service,preview['mode'],preview['paths'])!=preview:
        raise ValueError('A prévia mudou. Recalcule antes de aplicar.')
    # Backup usa a implementação validada existente: banco consistente e fontes completas.
    backup=create_backup(service.repository)
    record=service.store.profile()
    profile=replace(AdaptiveProfile(**record['configured_profile']),grouping_mode=preview['mode'],grouping_paths=preview['paths'])
    return service.store.save_profile(profile,preview['profile_id'],expected_planning_token=preview['token'],
                                      audit_preview={**preview,'audit_kind':'grouping.change','backup':str(backup)})
