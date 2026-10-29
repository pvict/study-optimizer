"""Série flexível: prévia, versão substituta e desfazer no StudyAgenda."""
from copy import deepcopy
from datetime import timedelta
from .planning import _date
from .planner_service import today_local
from .study_models import AdaptiveProfile
from .study_calendar import forecast_calendar
from .mock_schedule import schedule_dates,calendar_changes


class MockScheduleServiceMixin:
    def recorded_mock_days(self):
        from .study_read_model import read_events,latest_active
        return {r['data']['day'] for r in latest_active(read_events(self.repository,'mock_exams'),'exam_key') if not r['data'].get('practice_id')}

    def mock_schedule_undo_reason(self,plan_id):
        from .study_agenda import effective_applies
        current=today_local().isoformat(); records=self.agenda.records()
        def dates(events):
            return {d for r in effective_applies(events,current) if r.get('scope')=='mock_schedule'
                    for d in r.get('overrides',{})}
        canceled={'id':max((r['id'] for r in records),default=0)+1,'kind':'reschedule.cancel','plan_id':plan_id,'created_day':current}
        changed=dates(records)^dates(records+[canceled])
        if any(d<current for d in changed): return 'Desfazer alteraria datas passadas. Ajuste apenas os próximos simulados individualmente.'
        if changed&self.recorded_mock_days(): return 'Já há resultado registrado em uma data afetada. Preserve o registro e ajuste apenas os próximos simulados.'
        return None

    def mock_schedule(self,as_of=None):
        day=as_of or today_local().isoformat()
        return next((r for r in reversed(self.agenda.active(self.store.active(day),day)['active'])
                     if r.get('scope')=='mock_schedule'),None)

    def preview_mock_move(self,occurrence_id,new_day):
        old=self.mock_schedule()
        if not old: raise ValueError('Programe o primeiro simulado antes de mover datas.')
        request=old['request']; changes=dict(request['exceptions'])
        occurrence=next((r for r in old['occurrences'] if r['occurrence_id']==occurrence_id),None)
        current=today_local().isoformat()
        if not occurrence or (occurrence['date'] or occurrence_id)<current: raise ValueError('Escolha uma ocorrência de hoje ou futura. Datas passadas ficam no histórico.')
        if occurrence['date'] in self.recorded_mock_days(): raise ValueError('Já há resultado registrado para este simulado. Ajuste apenas os próximos.')
        if new_day is not None:
            _date(new_day)
            if new_day<current: raise ValueError('Escolha uma data de hoje em diante.')
        changes[occurrence_id]=new_day
        return self.preview_mock_schedule(request['first_day'],request['interval'],exceptions=changes,end=request['end'],_editing=True)

    def preview_mock_schedule(self,first_day,interval,*,exceptions=None,end=None,_editing=False):
        current=today_local().isoformat(); token=self.agenda.token(); old=self.mock_schedule(current)
        p=AdaptiveProfile(**self.store.profile()['profile'])
        end=end or min(p.exam_date,(_date(current)+timedelta(days=547)).isoformat())
        _date(first_day); _date(end)
        if first_day<current and not (_editing and old and first_day==old['request']['first_day']): raise ValueError('O primeiro simulado deve ser hoje ou no futuro.')
        if (not _editing and first_day<(p.start_date or current)) or end>p.exam_date or end>(_date(current)+timedelta(days=547)).isoformat(): raise ValueError('Use datas dentro do cronograma e até 18 meses à frente.')
        request={'first_day':first_day,'interval':interval,'end':end,'exceptions':dict(exceptions or {})}
        occurrences=schedule_dates(first_day,interval,end,request['exceptions'])
        if old:
            previous={r['occurrence_id']:r for r in old['occurrences']}
            for origin,row in previous.items():
                if (row['date'] or origin)<current:
                    updated=next((r for r in occurrences if r['occurrence_id']==origin),None)
                    if not updated or updated['date']!=row['date']: raise ValueError('Datas passadas da série ficam preservadas. Mova apenas ocorrências futuras.')
        sessions=self.store.active(current)
        base=self.agenda.active(sessions,current,excluded_plan_ids=[old['id']] if old else [])
        settings=self.store.days()
        exam_days={r['date'] for r in self.exam_dates(current) if r['kind']=='exam_date'}
        overrides={}
        for occurrence in occurrences:
            day=occurrence['date']
            if day is None: continue
            if day>=current and p.start_date and day<p.start_date: raise ValueError('Escolha uma data a partir do início do cronograma.')
            prior=base['overrides'].get(day,{})
            conflict=('Prova cadastrada' if day in exam_days else 'Programação especial existente' if prior.get('mode') in {'final_review','final_rest','mock_day'} else None)
            if conflict:
                if day>=current and day!=occurrence['original_date']: raise ValueError(conflict+'. Escolha outro dia para o simulado.')
                occurrence.update(status='blocked',reason=conflict); continue
            overrides[day]={'mode':'mock_reserved','occurrence_id':occurrence['occurrence_id'],'label':'Simulado programado'}
        before_view=self.overview(current)
        agenda=deepcopy(base); agenda['overrides'].update(overrides)
        after_view=self.overview(current,_agenda_override=agenda)
        old_dates={r['date'] for r in old['occurrences'] if r['date'] and r['date']>=current and r['status']=='reserved'} if old else set()
        new_dates={r['date'] for r in occurrences if r['date'] and r['date']>=current and r['status']=='reserved'}
        changed=old_dates^new_dates
        # A série cobre a preparação. A comparação não inventa resultados: começa
        # com 28 dias; uma edição distante amplia até 14 dias após a data movida.
        changed_near=changed if old else {min(new_dates)} if new_dates else set()
        horizon=max(27,max(((_date(d)-_date(current)).days+14 for d in changed_near),default=27))
        horizon=min(547,horizon,(_date(end)-_date(current)).days)
        if horizon<0: raise ValueError('O período terminou. Confira a data da prova.')
        def project(view,active):
            return forecast_calendar(view['planning_states'],p,current,horizon+1,sessions,settings,view['plan'],active,next_contact_only=True)
        before_calendar=project(before_view,before_view['agenda'])
        after_calendar=project(after_view,agenda)
        topic_changes=calendar_changes(before_calendar,after_calendar)
        rows=[]; selected=[]
        after_by_id={r['topic_id']:r for r in topic_changes}
        for row in base['rows']:
            moved=after_by_id.get(row['topic_id'])
            if row['date'] in new_dates and moved and moved['after_date']:
                rows.append({**row,'date':moved['after_date'],'questions':row['remaining']})
                selected.append(row['topic_id'])
        if rows:
            # Reproduzir exatamente a ordem de reservas que o StudyAgenda terá
            # após substituir as selecionadas, antes de prometer novas datas.
            cutoff=max((e['id'] for e in self.store.events()),default=0)
            agenda['rows']=[r for r in base['rows'] if r['topic_id'] not in selected]+[
                {**r,'remaining':r['questions'],'cutoff':cutoff,'created_day':current} for r in rows]
            after_view=self.overview(current,_agenda_override=agenda)
            after_calendar=project(after_view,agenda)
            topic_changes=calendar_changes(before_calendar,after_calendar)
        if token!=self.agenda.token(): raise ValueError('Seu plano mudou. Recalcule a prévia.')
        area_conflicts=[r for r in base.get('area_practice',[]) if r['date'] in new_dates]
        return {'request':request,'occurrences':occurrences,'overrides':overrides,'rows':rows,'selected':selected,'area_conflicts':area_conflicts,
                'topic_changes':topic_changes,'unassigned':[r for r in topic_changes if r['after_date'] is None],
                'window_start':current,'window_end':after_calendar[-1]['date'],'created_day':current,'token':token,
                'replaces_plan_id':old['id'] if old else None,'editing':_editing}

    def apply_mock_schedule(self,preview):
        if preview['created_day']!=today_local().isoformat() or preview['token']!=self.agenda.token(): raise ValueError('O plano mudou. Recalcule a prévia antes de aplicar.')
        r=preview['request']
        fresh=self.preview_mock_schedule(r['first_day'],r['interval'],exceptions=r['exceptions'],end=r['end'],_editing=preview['editing'])
        if fresh!=preview: raise ValueError('A programação mudou. Recalcule a prévia.')
        return self.agenda.append({**fresh,'kind':'reschedule.apply','scope':'mock_schedule',
            'cutoff':max((e['id'] for e in self.store.events()),default=0)},fresh['token'])
