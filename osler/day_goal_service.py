"""Meta efetiva por data, com simulação em memória e aplicação auditada."""
from contextlib import contextmanager
from copy import copy
from dataclasses import replace
import sqlite3

from .planner_service import today_local,valid_date
from .study_models import StudyDay


@contextmanager
def _simulation(service):
    # Compartilha somente os arquivos imutáveis; toda escrita vai ao SQLite RAM.
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    try:
        with service.repository._connection() as source:source.backup(db)
        repo=copy(service.repository)
        @contextmanager
        def connection():
            with db:yield db
        repo._connection=connection
        staged=copy(service)
        staged.__init__(repo)
        yield staged
    finally:db.close()


def goal_summary(view):
    plan=view['plan'];over=plan['routine_override']
    external=over.get('recovery_reserved',0)
    area=over.get('area_reserved',0)
    themes=plan['base_questions']+plan.get('extra_questions',0)
    if plan['kind']=='descanso':themes=area=external=0
    total=themes+area+external
    return {'total':total,'themes':themes,'area':area,'external':external,
            'planned':sum(i['questions'] for i in plan['items']),
            'done':max(0,plan['done_questions']-sum(t.get('done',0) for t in plan.get('area_tasks',[]))),
            'items':[{'topic_id':i['topic_id'],'path':i['path'],'questions':i['questions']} for i in plan['items']]}


class DayGoalServiceMixin:
    def preview_day_goal(self,day,questions,kind='normal'):
        valid_date(day)
        if type(questions) is not int or questions<=0:
            raise ValueError('Informe uma meta positiva de questões.')
        token=self.agenda.token();before=self.overview(day)
        if before['plan'].get('not_started'):
            raise ValueError('Este dia é anterior ao início do cronograma. Ajuste a data de início em Ajustes.')
        mode=before['plan']['routine_override'].get('mode')
        owners={'mock_reserved':'Simulados','mock_day':'Simulados','final_review':'Revisão final no Calendário',
                'final_rest':'Revisão final no Calendário','external_day':'Revisões externas em Hoje'}
        if mode in owners:
            raise ValueError('Este dia tem uma programação protegida. Ajuste primeiro em '+owners[mode]+'.')
        plan=before['plan'];recovery=before['agenda'].get('quantity_recovery') or {}
        external_done=recovery.get('done_today',0) if recovery.get('anchor')==day else 0
        pending_area=sum(max(0,t['questions']-t.get('done',0)) for t in plan.get('area_tasks',[]) if not t['completed'])
        record=self.store.day(day,self.store.profile()['profile']['max_questions'])
        manual=sum(e['questions'] for e in record['settings']['extra_topics'] if e.get('over_limit'))
        base_questions=questions-manual if kind!='descanso' else min(1000,questions)
        StudyDay(questions=base_questions,kind=kind,effective_goal=True).validate()
        from .study_allocation import pending_extra_questions
        from .study_swaps import swap_rows
        from .exam_practice import practice_context
        ordinary=practice_context(before['agenda'],day,before['sessions'])['ordinary_sessions']
        pending_extras=pending_extra_questions(record['settings'],before['states']+before['planning_states'],
            ordinary,day,swap_rows(before['agenda'].get('swaps',[]),before['sessions'],day))
        minimum=plan['done_questions']+external_done+pending_area+pending_extras
        if kind=='descanso' and pending_area:
            raise ValueError('Há um treino por área reservado. Remaneje o treino em Simulados antes de marcar descanso.')
        if kind=='descanso' and pending_extras:
            raise ValueError('Há questões extras reservadas. Retire os extras antes de marcar descanso.')
        if kind!='descanso' and questions<minimum:
            raise ValueError(f'Este dia já tem {minimum} questões realizadas ou reservadas para treino e extras. '
                             f'Use uma meta de pelo menos {minimum} ou remaneje o treino e retire os extras.')
        settings=replace(StudyDay(**record['settings']),questions=base_questions,kind=kind,effective_goal=True)
        with _simulation(self) as staged:
            staged.store.save_day(day,settings,record['revision'])
            after=staged.overview(day)
        if goal_summary(after)['total']!=(0 if kind=='descanso' else questions):
            raise ValueError('As reservas deste dia não permitem esse total. Confira os treinos e extras antes de alterar a meta.')
        if token!=self.agenda.token():raise ValueError('Os dados mudaram. Confira a prévia novamente.')
        return {'request':{'day':day,'questions':questions,'kind':kind},'created_day':today_local().isoformat(),
                'token':token,'revision':record['revision'],'before':goal_summary(before),'after':goal_summary(after),
                'previous_settings':record['settings'],'settings':settings.to_dict(),
                'replaces_recovery_limit':plan['routine_override'].get('recovery_limit')}

    def apply_day_goal(self,preview):
        if preview['token']!=self.agenda.token() or preview['created_day']!=today_local().isoformat():
            raise ValueError('Os dados mudaram. Confira a prévia novamente.')
        fresh=self.preview_day_goal(**preview['request'])
        if fresh!=preview:raise ValueError('A prévia mudou. Confira novamente antes de aplicar.')
        return self.store.save_day(preview['request']['day'],StudyDay(**fresh['settings']),fresh['revision'],
            expected_planning_token=fresh['token'],audit_preview=fresh)
