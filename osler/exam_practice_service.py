"""Agenda de treinos e correções no mesmo histórico transacional do planejador."""
from copy import deepcopy
from datetime import timedelta

from .exam_practice import area_rotation,validate_errors,correction_doses,practice_context,next_correction_day,EXCLUSIVE
from .mock_exams import MockExam,MockExams
from .models import normalize_path
from .planning import _date,_number
from .planner_service import today_local
from .study_agenda import effective_applies
from .study_models import AdaptiveProfile


class ExamPracticeServiceMixin:
    def exam_learning_agenda(self):
        """Marcos de correção não são questões feitas nem dívida automática."""
        current=today_local().isoformat(); results=MockExams(self.repository).active()
        active=effective_applies(self.agenda.records(),current); sources=[]
        for record in active:
            if record.get('scope') not in {'mock_schedule','area_practice'}: continue
            for r in record.get('occurrences',[]):
                if not r['date'] or r.get('status')=='blocked': continue
                is_area=record['scope']=='area_practice'
                linked=next((e for e in results if e['exam'].get('practice_id')==r['id']),None) if is_area else next((e for e in results if not e['exam'].get('practice_id') and e['exam']['day']==r['date']),None)
                if linked: continue
                sources.append({'source_id':('train:' if is_area else 'full:')+(r['id'] if is_area else r['occurrence_id']),
                    'source_day':r['date'],'name':r['institution']+' · '+r['area'] if is_area else 'Simulado completo','exam_key':None})
        for r in results:
            if r['exam']['correct']==r['exam']['questions']: continue
            sources.append({'source_id':r['exam_key'],'source_day':r['exam']['day'],'name':r['exam']['name'],'exam_key':r['exam_key']})
        for source in sources:
            # A preferência de uma ocorrência acompanha o resultado registrado no mesmo dia.
            aliases={source['source_id']}
            if source['exam_key']:
                result=next(r for r in results if r['exam_key']==source['exam_key'])
                pid=result['exam'].get('practice_id')
                aliases.add('train:'+pid if pid else 'full:'+source['source_day'])
            choice=next((r for r in reversed(active) if r.get('scope')=='correction_day' and r['source_id'] in aliases),None)
            plan=self.correction_schedule(source['exam_key']) if source['exam_key'] else None
            source['date']=plan['start'] if plan else choice['date'] if choice else next_correction_day(source['source_day'])
            source['needs_details']=not plan or not plan['rows']
            source['scheduled_topics']=len(plan['rows']) if plan else 0
            source['needs_move']=source['date']<source['source_day']
            source['stale']=self.mock_errors(source['exam_key'])['stale'] if source['exam_key'] else False
        return sorted(sources,key=lambda r:(r['date'],r['source_id']))

    def preview_correction_day(self,source_id,day):
        _date(day); current=today_local().isoformat()
        source=next((r for r in self.exam_learning_agenda() if r['source_id']==source_id),None)
        if not source or day<max(current,source['source_day']): raise ValueError('Escolha uma data de hoje em diante, após o simulado.')
        if day>self.store.profile()['profile']['exam_date']: raise ValueError('Use uma data dentro da preparação.')
        if source['exam_key'] and self.correction_schedule(source['exam_key']): raise ValueError('Há blocos de correção reservados. Refaça a prévia da distribuição para remanejá-los juntos.')
        old=next((r for r in reversed(effective_applies(self.agenda.records(),current)) if r.get('scope')=='correction_day' and r['source_id']==source_id),None)
        return {'source_id':source_id,'date':day,'before_date':source['date'],'created_day':current,'token':self.agenda.token(),
                'replaces_plan_id':old['id'] if old else None}

    def apply_correction_day(self,preview):
        self._practice_preview_current(preview)
        fresh=self.preview_correction_day(preview['source_id'],preview['date'])
        if fresh!=preview: raise ValueError('A agenda mudou. Recalcule a prévia.')
        return self.agenda.append({**fresh,'kind':'reschedule.apply','scope':'correction_day','rows':[],'cutoff':0},fresh['token'])

    def area_schedule(self):
        active=effective_applies(self.agenda.records(),today_local().isoformat())
        record=next((deepcopy(r) for r in reversed(active) if r.get('scope')=='area_practice'),None)
        if not record: return None
        overrides={}; settings=self.store.days()
        for r in active: overrides.update(r.get('overrides',{}))
        exams={r['date'] for r in self.exam_dates() if r['kind']=='exam_date'}
        for row in record['occurrences']:
            day=row['date']
            if day and (day in exams or settings.get(day,{}).get('kind')=='descanso' or overrides.get(day,{}).get('mode') in EXCLUSIVE):
                row.update(status='blocked',reason='Conflito com prova, simulado completo ou programação protegida; mova este treino.')
        return record

    def preview_area_schedule(self,first,end,frequency,questions,institutions,exceptions=None,topic_dates=None):
        current=today_local().isoformat(); token=self.agenda.token(); old=self.area_schedule()
        p=AdaptiveProfile(**self.store.profile()['profile'])
        if end>p.exam_date or end>(_date(current)+timedelta(days=547)).isoformat(): raise ValueError('Use datas até a prova e até 18 meses à frente.')
        if first<max(current,p.start_date or current) and (not old or first!=old['request']['first']): raise ValueError('Comece a partir de hoje e do início da preparação.')
        if topic_dates is not None and (not isinstance(topic_dates,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in topic_dates.items())):
            raise ValueError('Informe os temas e suas datas na prévia.')
        if exceptions is not None and not isinstance(exceptions,dict): raise ValueError('Informe as mudanças por ocorrência.')
        old_dates=(old or {}).get('request',{}).get('topic_dates',{})
        sessions=self.store.active(current)
        previous_rows={r['topic_id']:r for r in self.agenda.active(sessions,current)['rows'] if old and r['plan_id']==old['id']}
        outstanding=set(previous_rows)
        topic_dates={k:v for k,v in (topic_dates or {}).items() if not (old_dates.get(k)==v and (v<current or k not in outstanding))}
        request=dict(first=first,end=end,frequency=frequency,questions=questions,institutions=institutions,exceptions=exceptions or {},topic_dates=topic_dates or {})
        reconfigured=bool(old and any(request[k]!=old['request'][k] for k in ('first','end','frequency','questions','institutions')))
        if reconfigured:
            valid_ids={r['id'] for r in area_rotation(first,end,frequency,questions,institutions)}
            request['exceptions']={k:v for k,v in request['exceptions'].items() if k in valid_ids}
        occurrences=area_rotation(first,end,frequency,questions,institutions)
        if set(request['exceptions'])-{r['id'] for r in occurrences}: raise ValueError('Ocorrência desconhecida.')
        manual_dates=[]
        for row in occurrences:
            if row['id'] not in request['exceptions']: continue
            day=request['exceptions'][row['id']]
            if day is not None:
                _date(day)
                if not first<=day<=end: raise ValueError('Mova o treino dentro do período da série.')
                manual_dates.append(day)
            row['date']=day
        if len(manual_dates)!=len(set(manual_dates)): raise ValueError('Dois treinos manuais não podem ocupar a mesma data.')
        results=MockExams(self.repository).active(); protected={r['exam']['practice_id'] for r in results if r['exam'].get('practice_id')}
        if old:
            after={r['id']:r for r in occurrences}
            for row in old['occurrences']:
                if (row['date'] or row['original_date'])<current or row['id'] in protected:
                    if row['id'] in (exceptions or {}) and exceptions[row['id']]!=row['date']:
                        raise ValueError('Preserve treinos passados e com resultado. Mude apenas as próximas ocorrências.')
                    after[row['id']]=dict(row)
            occurrences=sorted(after.values(),key=lambda r:(r['original_date'],r['id']))
        base=self.agenda.active(sessions,current,excluded_plan_ids=[old['id']] if old else [])
        settings=self.store.days(); exams={r['date'] for r in self.exam_dates() if r['kind']=='exam_date'}
        from .study_calendar import forecast_calendar
        horizon=min(90,max(1,(_date(end)-_date(current)).days+1))
        def project(agenda):
            ov=self.overview(current,_agenda_override=agenda)
            return forecast_calendar(ov['planning_states'],p,current,horizon,sessions,settings,ov['plan'],agenda,next_contact_only=True)
        baseline=project(base)
        # Operational pressure, not a retention probability: retain the existing
        # incidence/performance ranking and avoid displacing urgent blocks.
        pressure={d['date']:sum(i['questions']*{'urgente':4,'alta':2}.get(i['priority'],1) for i in d['items']) for d in baseline}
        def unavailable(day,dose=questions):
            cfg=settings.get(day,{'kind':'normal','questions':p.max_questions})
            if day in exams: return 'prova'
            if cfg['kind']=='descanso': return 'descanso'
            if base['overrides'].get(day,{}).get('mode') in EXCLUSIVE: return 'programação protegida'
            from .study_replanning import effective_routine
            from .exam_practice import area_extra_volume
            _,budget=effective_routine(p,cfg,base['overrides'].get(day,{}))
            used=sum(s['entry']['questions'] for s in sessions if s['entry']['day']==day and s['entry']['kind']=='bloco')
            used+=area_extra_volume(results,sessions,day).get(day,0)
            if dose>max(0,budget-used): return 'capacidade diária insuficiente'
            return None
        fixed={r['date'] for r in occurrences if r['date'] and (r['date']<current or r['id'] in protected or r['id'] in request['exceptions'])}
        fixed_rows=[r for r in occurrences if r['date'] and (r['date']<current or r['id'] in protected or r['id'] in request['exceptions'])]
        if len(fixed)!=len(fixed_rows): raise ValueError('A data já contém outro treino, inclusive um resultado preservado.')
        occupied=set(fixed)
        for row in occurrences:
            day=row['date']
            if not day or day<current or row['id'] in protected: continue
            row.pop('status',None); row.pop('reason',None)
            if row['id'] in request['exceptions']:
                if unavailable(day): raise ValueError(f'Data manual {day} indisponível: {unavailable(day)}. Escolha uma data livre de programação protegida.')
                row['status']='manual'
                continue
            reason=unavailable(day)
            # Keep valid requested dates; only resolve conflicts/collisions.
            if reason or day in occupied:
                candidates=[(_date(day)+timedelta(days=o)).isoformat() for o in range(-7,8)]
                candidates=[d for d in candidates if max(current,first)<=d<=end and not unavailable(d) and d not in occupied
                            and all(abs((_date(d)-_date(other)).days)>=2 for other in occupied)]
                if candidates:
                    chosen=min(candidates,key=lambda d:(abs((_date(d)-_date(day)).days),pressure.get(d,0),d))
                    row.update(date=chosen,status='moved',reason=f'Remanejado de {day}: {reason or "proximidade de outro treino"}.')
                else: row.update(status='blocked',reason=f'Sem vaga próxima: {reason or "outro treino"}. Ajuste o período ou a carga.')
            occupied.add(row['date'])
        # A comparação usa o mesmo simulador dos próximos contatos; não assume melhora.
        view=self.overview(current); after=deepcopy(base); after['area_practice']=[r for r in occurrences if r['date'] and r.get('status')!='blocked']
        after['area_results']=[r for r in results if r['exam'].get('practice_id')]
        for day in {r['date'] for r in after['area_practice']}:
            if day and base['overrides'].get(day,{}).get('mode') not in EXCLUSIVE:
                after['overrides'][day]={**after['overrides'].get(day,{}),'area_reserved':practice_context(after,day)['reserved']}
        from .mock_schedule import calendar_changes
        options={}
        for day in baseline:
            for item in day['items']:
                options.setdefault(item['topic_id'],{**item,'date':day['date']})
        reservations={r['topic_id']:r for r in base['rows']}
        reservations.update(previous_rows)
        for key,item in options.items():
            if key in reservations: item['questions']=reservations[key]['remaining']
        rows=[]
        for topic_id,day in request['topic_dates'].items():
            _date(day)
            if topic_id not in options: raise ValueError('Escolha um tema presente nesta prévia.')
            item=options[topic_id]
            if not current<=day<=baseline[-1]['date'] or unavailable(day,item['questions']): raise ValueError('Data do tema fora da prévia, protegida ou sem capacidade. Escolha uma data livre.')
            rows.append({**reservations.get(topic_id,{}),'topic_id':topic_id,'path':item['path'],'date':day,'original_due':reservations.get(topic_id,{}).get('original_due',item['date']),
                         'questions':item['questions'],'remaining':item['questions'],'manual_date':True,'created_day':current,'cutoff':max((s['id'] for s in sessions),default=0),'plan_id':0})
        after['rows']=[r for r in after['rows'] if r['topic_id'] not in request['topic_dates']]+deepcopy(rows)
        projected=project(after)
        for row in rows:
            actual=sum(i['questions'] for d in projected if d['date']==row['date'] for i in d['items'] if i['topic_id']==row['topic_id'])
            if actual<row['questions']: raise ValueError(f'Sem capacidade para a dose completa de {row["path"][-1]} nessa data. Escolha outro dia.')
        changes=calendar_changes(project(view['agenda']),projected)
        if token!=self.agenda.token(): raise ValueError('Seu plano mudou. Recalcule a prévia.')
        return {'request':request,'occurrences':occurrences,'topic_changes':changes,'token':token,'created_day':current,
                'replaces_plan_id':old['id'] if old else None,'window_days':horizon,'rows':rows,
                'topic_options':[{'topic_id':i['topic_id'],'path':i['path'],'date':i['date'],'questions':i['questions'],'priority':i['priority']} for i in options.values()]}

    def apply_area_schedule(self,preview):
        self._practice_preview_current(preview)
        fresh=self.preview_area_schedule(**preview['request'])
        if fresh!=preview: raise ValueError('A programação mudou. Recalcule a prévia.')
        if any(r.get('status')=='blocked' for r in fresh['occurrences']): raise ValueError('Há treinos sem vaga. Ajuste a prévia antes de aplicar.')
        return self.agenda.append({**fresh,'kind':'reschedule.apply','scope':'area_practice','selected':list(fresh['request']['topic_dates']),
            'cutoff':max((e['id'] for e in self.store.events()),default=0)},fresh['token'])

    def _practice_preview_current(self,preview):
        if preview['created_day']!=today_local().isoformat() or preview['token']!=self.agenda.token():
            raise ValueError('O plano mudou. Recalcule a prévia.')

    def register_area_result(self,occurrence_id,day,questions,correct,*,unseen=False,token=None):
        old=self.area_schedule()
        row=next((r for r in (old or {}).get('occurrences',[]) if r['id']==occurrence_id),None)
        if not row or not row['date'] or row.get('status')=='blocked': raise ValueError('Escolha um treino programado e disponível.')
        exam=MockExam(day,questions,correct,kind='outro',institution=row['institution'],
            name=row['institution']+' · '+row['area'],unseen_questions=unseen,practice_id=occurrence_id,
            areas=[{'area':row['area'],'questions':questions,'correct':correct}])
        return MockExams(self.repository).save(exam,expected_token=token)

    def mock_errors(self,exam_key):
        exam=next((r for r in MockExams(self.repository).active() if r['exam_key']==exam_key),None)
        if not exam: raise ValueError('Escolha um resultado ativo.')
        last=next((r for r in reversed(self.agenda.records()) if r.get('kind')=='mock.errors' and r['exam_key']==exam_key),None)
        rows=last['errors'] if last else [{'path':t['path'],'errors':t['questions']-t['correct']} for t in exam['exam']['topics'] if t['questions']>t['correct']]
        return {'exam':exam,'errors':rows,'annotation_id':last['id'] if last else 0,
                'stale':bool(last and last['exam_version']!=exam['version'])}

    def save_mock_errors(self,exam_key,version,errors,expected_annotation_id,token):
        context=self.mock_errors(exam_key)
        if context['exam']['version']!=version or context['annotation_id']!=expected_annotation_id: raise ValueError('Os erros ou o resultado mudaram. Atualize a tela.')
        catalog,_=self.catalog(today_local().isoformat())
        exam=context['exam']['exam']; checked=validate_errors(errors,catalog,exam['questions']-exam['correct'])
        return self.agenda.append({'kind':'mock.errors','created_day':today_local().isoformat(),'exam_key':exam_key,
            'exam_version':version,'errors':checked,'previous_id':expected_annotation_id},token)

    def correction_schedule(self,exam_key):
        return next((r for r in reversed(effective_applies(self.agenda.records(),today_local().isoformat()))
            if r.get('scope')=='mock_correction' and r['exam_key']==exam_key),None)

    def preview_mock_correction(self,exam_key,start,questions=40):
        current=today_local().isoformat(); _date(start); _number(questions,'Questões da correção por dia',positive=True,integer=True,maximum=1000)
        token=self.agenda.token(); context=self.mock_errors(exam_key); exam=context['exam']; old=self.correction_schedule(exam_key)
        if context['stale']: raise ValueError('O resultado foi corrigido. Confira e salve novamente os temas errados.')
        if start<max(current,exam['exam']['day']): raise ValueError('Escolha uma data de hoje em diante, após o simulado.')
        view=self.overview(current); p=AdaptiveProfile(**view['profile'])
        if start>p.exam_date: raise ValueError('Escolha uma data dentro da preparação.')
        catalog,_=self.catalog(current)
        errors=validate_errors(context['errors'],catalog,exam['exam']['questions']-exam['exam']['correct'])
        states=view['planning_states']
        institution=exam['exam'].get('institution')
        datasets=[d for d in self.guide.datasets() if institution and
            {tuple(normalize_path([i])) for i in d['institutions']}=={tuple(normalize_path([institution]))}]
        basis=('Incidência conjunta disponível; dificuldade observada e erros informados. Pesos operacionais.' if view['incidence']['contexts'] else
               'Sem incidência importada: dificuldade observada e erros informados; pesos operacionais, sem atribuir frequência à prova.')
        if datasets:
            from .adaptive_planning import incidence_weights
            incidence=incidence_weights(states,datasets,{institution:1},current,p.parameters)
            if incidence['contexts']:
                states=[{**t,'importance':incidence['weights'][t['topic_id']]} for t in states]
                basis=f'Incidência específica de {institution}; dificuldade observada e erros informados. Pesos operacionais.'
        doses=correction_doses(errors,states,p.min_block)
        base=self.agenda.active(view['sessions'],current,excluded_plan_ids=[old['id']] if old else [])
        selected=[r['topic_id'] for r in doses]; replaced=[r for r in base['rows'] if r['topic_id'] in selected]
        usage={}
        from .mock_exams import _prefix
        converted_area_prefixes=tuple(_prefix(r['exam_key']) for r in base.get('area_results',[]))
        for session in view['sessions']:
            e=session['entry']
            if e['kind']=='bloco' and not session['session_id'].startswith(converted_area_prefixes):
                u=usage.setdefault(e['day'],{'total':0,'reviews':0,'slots':0})
                u['total']+=e['questions'];u['reviews']+=e['questions'];u['slots']+=1
        from .exam_practice import schedule_corrections
        planned,unassigned=schedule_corrections(doses,p,start,questions,self.store.days(),base,usage)
        weight_by_id={r['topic_id']:r for r in doses}
        rows=[{**r,'source_exam_key':exam_key,'correction':True,'weight':weight_by_id[r['topic_id']]['weight']} for r in planned]
        if token!=self.agenda.token(): raise ValueError('Seu plano mudou. Recalcule a prévia.')
        return {'exam_key':exam_key,'exam_version':exam['version'],'annotation_id':context['annotation_id'],
                'start':start,'questions':questions,'rows':rows,'selected':selected,'replaced':replaced,
                'unassigned':unassigned,'token':token,'created_day':current,'overrides':{},
                'replaces_plan_id':old['id'] if old else None,'basis':basis}

    def apply_mock_correction(self,preview):
        self._practice_preview_current(preview)
        fresh=self.preview_mock_correction(preview['exam_key'],preview['start'],preview['questions'])
        if fresh!=preview: raise ValueError('A correção mudou. Recalcule a prévia.')
        if fresh['unassigned']: raise ValueError('Há temas sem vaga. Amplie a carga ou antecipe a data antes de aplicar.')
        return self.agenda.append({**fresh,'kind':'reschedule.apply','scope':'mock_correction',
            'cutoff':max((e['id'] for e in self.store.events()),default=0)},fresh['token'])
