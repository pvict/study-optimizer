"""Atualização contínua local, fontes documentais separadas e planos reproduzíveis."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import csv
import hashlib
from io import StringIO
import json
from statistics import median
import uuid

from .adaptive_planning import topic_states, allocate_day, incidence_weights
from .exports import _safe_cell
from .files import write_immutable
from .guide import GuideSettings
from .guide_service import GuideService
from .models import normalize_path
from .planner_service import today_local, valid_date
from .study_models import StudyEntry, AdaptiveProfile, StudyDay
from .study_storage import StudyStore
from .reduction_storage import ReductionStore
from .planner_storage import PlannerStore
from .planning import _date
from .topic_catalog import planning_frontier
from .review_queue import review_queue
from .study_agenda import StudyAgenda
from .study_replanning import effective_routine
from .prevention_service import PreventiveServiceMixin
from .study_prevention import preventive_state
from .planner_snapshot import load_planner_contexts
from .review_policy import POLICY_VERSION
from .capacity_service import CapacityServiceMixin
from .evolution_service import EvolutionServiceMixin
from .swap_service import DailySwapServiceMixin
from .final_review import FinalReviewServiceMixin,special_config,final_reservations


class AdaptiveService(PreventiveServiceMixin,CapacityServiceMixin,EvolutionServiceMixin,DailySwapServiceMixin,FinalReviewServiceMixin):
    def __init__(self,repo):
        self.repository=repo
        self.store=StudyStore(repo)
        self.guide=GuideService(repo)
        self.agenda=StudyAgenda(repo)

    def catalog(self,as_of,include_parents=False):
        q=self.guide._report('qbank',as_of)
        f=self.guide._report('flashcards',as_of)
        if not q: return [],{'qbank':None,'flashcards':None}
        counts=Counter(tuple(normalize_path(t.path)) for t in q.records)
        fcounts=Counter(tuple(normalize_path(t.path)) for t in f.records) if f else {}
        flash={tuple(normalize_path(t.path)):t for t in f.records if (t.is_leaf or include_parents) and fcounts[tuple(normalize_path(t.path))]==1} if f else {}
        topics=[]
        planner,planner_warnings=load_planner_contexts(self.repository,self.guide.datasets(),q.file_sha256,as_of)
        manual={}
        with self.repository._connection() as db:
            rows=db.execute('SELECT o.payload,c.path FROM observations o JOIN assessment_contexts c ON c.row_id=o.row_id WHERE o.active=1 AND o.observation_date<=? AND c.qbank_report=? AND c.flashcards_report=? ORDER BY o.observation_date,o.id',
                            (as_of,q.file_sha256,f.file_sha256 if f else '')).fetchall()
        for record in rows:
            observation=json.loads(record['payload'])
            if (_date(as_of)-_date(observation['data_observacao'])).days<=90:
                manual[tuple(normalize_path(json.loads(record['path'])))]=observation
        reduced={i['topic_key']:i['applied_date'] for i in PlannerStore(self.repository).all_items()
                 if i['status']=='aplicado_manualmente' and i['applied_date'] and i['applied_date']<=as_of}
        for event in ReductionStore(self.repository).events():
            if event['day']>as_of: continue
            for t in event['topics']:
                if event['kind']=='aplicado': reduced[t['topic_id']]=event['day']
                elif event['kind']=='reabrir': reduced.pop(t['topic_id'],None)
        for row in q.records:
            key=tuple(normalize_path(row.path))
            if not (row.is_leaf or include_parents) or counts[key]!=1 or len(row.path)!=row.level+1 or row.total<=0: continue
            card=flash.get(key)
            topics.append({'topic_id':row.topic_id,'path':row.path,'total':row.total,'answered_pdf':row.studied,
                           'pdf_accuracy':{'value':row.acerto_pdf.value,'operator':row.acerto_pdf.operator,'raw':row.acerto_pdf.raw},
                           'report_date':q.report_date,'studied_cards':card.studied if card else None,
                           'cards_reduced_day':reduced.get(row.topic_id),'manual_context':manual.get(key),'is_leaf':row.is_leaf,
                           'planner_snapshot':planner.get(key)})
        sources={'qbank':q.file_sha256,'flashcards':f.file_sha256 if f else None}
        if planner_warnings: sources['planner_warnings']=planner_warnings
        return topics,sources

    def _validate_entry(self,entry,by_path=None):
        entry.validate()
        valid_date(entry.day,past=True)
        if by_path is None:
            catalog,_=self.catalog(today_local().isoformat(),include_parents=True)
            by_path={tuple(normalize_path(t['path'])):t for t in catalog}
        match=by_path.get(tuple(normalize_path(entry.path)))
        if match is None: raise ValueError('Tema não reconhecido de forma única no relatório atual. Use o caminho completo.')
        return replace(entry,path=match['path'])

    def save_entry(self,entry,session_id=None,expected_version=0):
        entry=self._validate_entry(entry)
        return self.store.save_batch([(session_id or uuid.uuid4().hex,entry,expected_version)])[0]

    def import_text(self,text):
        lines=text.lstrip('\ufeff').splitlines()
        if not lines: raise ValueError('A tabela está vazia.')
        delimiter='\t' if '\t' in lines[0] else ';' if ';' in lines[0] else ','
        reader=csv.DictReader(StringIO(text.lstrip('\ufeff')),delimiter=delimiter)
        required={'tema','data','questoes'}
        if not required.issubset(reader.fieldnames or []): raise ValueError('Use as colunas tema, data, questoes e acertos (ou percentual).')
        topics,_=self.catalog(today_local().isoformat(),include_parents=True)
        by_path={tuple(normalize_path(t['path'])):t for t in topics}
        by_name={}
        for t in topics: by_name.setdefault(normalize_path([t['path'][-1]])[0],[]).append(t['path'])
        changes=[]
        digest=hashlib.sha256(text.encode()).hexdigest()[:20]
        for line,row in enumerate(reader,2):
            if None in row: raise ValueError(f'Linha {line}: número de colunas incompatível.')
            name=(row.get('tema') or '').strip()
            path=[p.strip() for p in name.replace('>>','→').split('→') if p.strip()]
            if len(path)==1:
                matches=by_name.get(normalize_path(path)[0],[])
                if len(matches)!=1: raise ValueError(f'Linha {line}: tema ausente ou ambíguo. Use a hierarquia completa.')
                path=matches[0]
            try:
                entry=StudyEntry(path,(row.get('data') or '').strip(),int(row['questoes']),
                                 correct=int(row['acertos']) if row.get('acertos') else None,
                                 percent=float(row['percentual'].rstrip('%').replace(',','.')) if row.get('percentual') else None,
                                 kind=row.get('tipo') or 'bloco',mode=row.get('modalidade') or 'novas',
                                 minutes=float(row['minutos'].replace(',','.')) if row.get('minutos') else None,
                                 last_contact=row.get('ultimo_contato') or None,source='Tabela manual de estudo',
                                 confident_correct=int(row['acertos_conviccao']) if row.get('acertos_conviccao') else None,
                                 review_of=row.get('revisao_de') or None)
                entry=self._validate_entry(entry,by_path)
                sid=row.get('id_sessao') or f'csv-{digest}-{line}'
                version=int(row.get('versao') or 0)
            except (ValueError,TypeError) as exc: raise ValueError(f'Linha {line}: {exc}') from exc
            changes.append((sid,entry,version))
        self.store.save_batch(changes)
        return len(changes)

    def configure_day(self,day,questions,kind,expected_revision):
        valid_date(day)
        current=self.store.day(day,self.store.profile()['profile']['max_questions'])
        settings=replace(StudyDay(**current['settings']),questions=questions,kind=kind)
        return self.store.save_day(day,settings,expected_revision)

    def add_topic(self,day,topic_id,questions,expected_revision):
        valid_date(day,past=True)
        topics,_=self.catalog(day)
        topic=next((t for t in topics if t['topic_id']==topic_id),None)
        if not topic: raise ValueError('Escolha um tema específico, não um grupo ou grande área.')
        current=self.store.day(day,self.store.profile()['profile']['max_questions'])
        settings=StudyDay(**current['settings'])
        if settings.kind=='descanso': raise ValueError('Retome o estudo do dia antes de adicionar revisões.')
        paths={t['topic_id']:tuple(normalize_path(t['path'])) for t in topics}
        chosen_path=paths[topic_id]
        for extra in settings.extra_topics:
            existing_path=paths.get(extra['topic_id'])
            if existing_path and existing_path!=chosen_path and (existing_path[:len(chosen_path)]==chosen_path or chosen_path[:len(existing_path)]==existing_path):
                raise ValueError('Essa revisão se sobrepõe a um grupo ou subtema já adicionado. Acrescente questões ao mesmo bloco ou retire o anterior.')
        extras=[dict(e) for e in settings.extra_topics]
        if type(questions) is not int or questions<=0: raise ValueError('Informe uma quantidade inteira positiva.')
        cutoff=max((e['id'] for e in self.store.events()),default=0)
        extras.append({'extra_id':uuid.uuid4().hex,'topic_id':topic_id,'questions':questions,'after_event_id':cutoff})
        if sum(e['questions'] for e in extras if e['topic_id']==topic_id)>topic['total']: raise ValueError('Quantidade adicional maior que o banco conhecido deste tema.')
        return self.store.save_day(day,replace(settings,extra_topics=extras),expected_revision)

    def remove_added_topic(self,day,topic_id,expected_revision):
        valid_date(day,past=True)
        current=self.store.day(day,self.store.profile()['profile']['max_questions'])
        settings=StudyDay(**current['settings'])
        return self.store.save_day(day,replace(settings,extra_topics=[e for e in settings.extra_topics if e['topic_id']!=topic_id]),expected_revision)

    def overview(self,as_of,minutes=None,kind=None,questions=None,_agenda_override=None):
        valid_date(as_of)
        record=self.store.profile()
        profile=AdaptiveProfile(**record['profile']).validate()
        day=self.store.day(as_of,profile.max_questions)
        day_settings=StudyDay(**day['settings']).validate()
        kind=kind or day_settings.kind
        guide=GuideSettings(**self.guide.settings()['settings']).validate()
        if not profile.institution_weights and guide.institutions:
            profile=replace(profile,institution_weights={name:1 for name in guide.institutions})
        all_topics,sources=self.catalog(as_of,include_parents=True)
        topics=[t for t in all_topics if t.get('is_leaf',True)]
        sessions=self.store.active(as_of)
        dated=sorted(sessions,key=lambda s:(s['entry']['day'],s['id']))
        measured=[e['entry']['minutes']/e['entry']['questions'] for e in dated
                  if e['entry']['kind']=='bloco' and e['entry'].get('minutes') and e['entry']['questions']>0][-20:]
        effective=replace(profile,minutes_per_question=max(.25,median(measured))) if measured else profile
        agenda=self.agenda.active(sessions,as_of) if _agenda_override is None else _agenda_override
        if profile.start_date:
            agenda=deepcopy(agenda)
            for reservation in agenda['rows']:
                reservation['date']=max(reservation['date'],profile.start_date)
                reservation['original_due']=max(reservation['original_due'],profile.start_date)
        override=agenda['overrides'].get(as_of,{})
        config=special_config(day_settings.to_dict(),override)
        if override.get('mode') in {'final_rest','mock_day'}: kind='descanso'
        effective,routine_questions=effective_routine(effective,config,override)
        contacts=[(d['path'],d['day']) for d in self.guide.days() if d['status']!='descanso' and d['path']]
        from .study_errors import ErrorStore
        error_paths=ErrorStore(self.repository).adverse_paths(as_of)
        states=topic_states(topics,sessions,self.guide.datasets(),effective.institution_weights,as_of,effective,contacts,error_paths)
        planning_topics=planning_frontier(all_topics,effective.min_block)
        planning_states=topic_states(planning_topics,sessions,self.guide.datasets(),effective.institution_weights,as_of,effective,contacts,error_paths)
        scheduled={r['topic_id']:r for r in agenda['rows']}
        for t in states+planning_states:
            if t['topic_id'] in scheduled: t['reschedule_date']=scheduled[t['topic_id']]['date']
            t.update(preventive_state(t,as_of,agenda.get('policies',[])))
        incidence=incidence_weights(topics,self.guide.datasets(),effective.institution_weights,as_of)
        extras=[]
        by_id={t['topic_id']:t for t in planning_states}
        missing={e['topic_id'] for e in day_settings.extra_topics}-set(by_id)
        for extra in day_settings.extra_topics:
            if extra['topic_id'] in by_id: extras.append({**by_id[extra['topic_id']],'extra_id':extra['extra_id'],'requested':extra['questions'],'after_event_id':extra['after_event_id']})
        question_target=questions if questions is not None else routine_questions if minutes is None else None
        extra_paths=[tuple(normalize_path(e['path'])) for e in extras]
        disjoint=[t for t in planning_states if not any(tuple(normalize_path(t['path']))!=p and (tuple(normalize_path(t['path']))[:len(p)]==p or p[:len(t['path'])]==tuple(normalize_path(t['path']))) for p in extra_paths)]
        from .study_capacity import capacity_limits
        from .study_swaps import swap_rows
        reservations=agenda['rows']
        swaps=swap_rows(agenda.get('swaps',[]),sessions,as_of)
        if override.get('mode')=='final_review':
            reservations=final_reservations(override,as_of,sessions)
            allowed={r['topic_id'] for r in reservations}
            disjoint=[t for t in disjoint if t['topic_id'] in allowed]
            extras=[]; swaps=[]
        elif override.get('mode') in {'final_rest','mock_day'}: extras=[]; swaps=[]
        plan=allocate_day(disjoint,effective,minutes,kind,sessions,as_of,question_target=question_target,extra_topics=extras if question_target is not None else None,reservations=reservations,capacity_limits=capacity_limits(effective,as_of,self.store.days(),agenda),swaps=swaps)
        warnings=list(incidence['warnings'])+sources.get('planner_warnings',[])
        if len(extras)!=len(day_settings.extra_topics): warnings.append('Uma revisão adicional antiga é ampla ou não existe no catálogo atual. Sua configuração foi preservada; escolha um tema específico para agendar.')
        if any(t['last_contact'] is None and t['answered_pdf'] for t in states): warnings.append('PDF não registra a última data de estudo. Esses temas entram como diagnóstico, sem atraso inventado.')
        if any(t['bank_balance_uncertain'] for t in states): warnings.append('O saldo de questões inéditas é uma estimativa: os arquivos e os blocos podem incluir as mesmas questões ou mostrar totais diferentes.')
        if as_of>profile.exam_date: warnings.append('A data da meta já passou. Ajuste a data para continuar a preparação.')
        if profile.start_date and profile.start_date>profile.exam_date: warnings.append('O início do cronograma está depois da prova de referência. Confira as datas em Ajustes.')
        plan.update({'algorithm_version':POLICY_VERSION,'sources':sources,'profile_id':record['id'],'day_revision':day['revision'],'routine_override':agenda['overrides'].get(as_of,{}),
                     'effective_profile':effective.to_dict(),
                     'session_versions':[(s['session_id'],s['version']) for s in sessions],
                     'incidence_contexts':incidence['contexts']})
        exact=[e['entry'] for e in sessions if e['entry']['kind']=='bloco' and e['entry']['mode']=='novas' and e['entry']['correct'] is not None]
        n=sum(e['questions'] for e in exact)
        portfolio={'new_questions':n,'new_correct':sum(e['correct'] for e in exact),
                   'accuracy':sum(e['correct'] for e in exact)/n if n else None,
                   'measured_weight':sum(t['importance'] for t in states if t['performance']['exact_n']>0)}
        leaf_ids={t['topic_id'] for t in states}
        states+= [t for t in planning_states if t['topic_id'] not in leaf_ids]
        known_ids={t['topic_id'] for t in states}
        recorded_paths={tuple(normalize_path(e['entry']['path'])) for e in sessions}
        other_parents=[t for t in all_topics if t['topic_id'] not in known_ids and tuple(normalize_path(t['path'])) in recorded_paths]
        if other_parents:
            states+=[{**t,'historical_aggregate':True} for t in topic_states(other_parents,sessions,self.guide.datasets(),effective.institution_weights,as_of,effective,contacts,error_paths)]
        return {'date':as_of,'plan':plan,'states':states,'profile':profile.to_dict(),'profile_id':record['id'],'day':day,
                'sessions':sessions,'sources':sources,'warnings':warnings,'portfolio':portfolio,'planning_states':planning_states,'review_queue':review_queue(sessions),
                'time_source':'Mediana de blocos registrados' if measured else 'Estimativa inicial ajustável',
                'incidence':incidence,'agenda':agenda}

    def export(self,view):
        self.store.save_plan(view['plan'])
        data=json.dumps(view['plan'],sort_keys=True,ensure_ascii=False,allow_nan=False,indent=2).encode()
        folder=self.repository.exports/'plano_questoes'/hashlib.sha256(data).hexdigest()
        folder.mkdir(parents=True,exist_ok=True)
        output=StringIO()
        writer=csv.writer(output,delimiter=';')
        writer.writerow(['Tema','Questões','Do banco ainda não respondidas (documental)','Repetição sugerida','Motivo'])
        writer.writerows([_safe_cell(' → '.join(t['path'])),t['questions'],t['new_questions'],t['repeat_questions'],t['reason']] for t in view['plan']['items'])
        write_immutable(folder/'plano.json',data)
        write_immutable(folder/'plano.csv',output.getvalue().encode('utf-8-sig'))
        return folder/'plano.csv'

    def calendar(self,days=60):
        from .study_calendar import forecast_calendar
        current=today_local().isoformat()
        view=self.overview(current)
        return forecast_calendar(view['planning_states'],AdaptiveProfile(**view['profile']),current,days,view['sessions'],self.store.days(),view['plan'],view['agenda'],next_contact_only=True)

    def trajectories(self,as_of):
        from .study_calendar import forecast_calendar
        from .topic_trajectory import trajectory_summary
        view=self.overview(as_of)
        profile=AdaptiveProfile(**view['profile'])
        days=min(548,max(1,(_date(profile.exam_date)-_date(as_of)).days+1))
        calendar=forecast_calendar(view['planning_states'],profile,as_of,days,view['sessions'],self.store.days(),view['plan'],view['agenda'])
        summary=trajectory_summary(view['planning_states'],profile,as_of,calendar)
        summary.update({'calendar':calendar,'view':view,'horizon_end':calendar[-1]['date']})
        return summary

    def remember_day(self,view):
        if view['date']!=today_local().isoformat(): raise ValueError('Somente o plano de hoje pode ser guardado como proposta diária.')
        return self.agenda.remember(view)

    def replanning(self,as_of=None):
        from .study_replanning import collect_backlog
        as_of=as_of or today_local().isoformat()
        view=self.overview(as_of)
        start_date=view['profile'].get('start_date')
        saved=[r for r in self.agenda.daily_plans() if view['agenda']['overrides'].get(r['plan']['date'],{}).get('mode') not in {'final_review','final_rest','mock_day'}]
        backlog=collect_backlog(view['planning_states'],view['sessions'],saved,as_of,start_date=start_date)
        by_id={t['topic_id']:t for t in view['planning_states']}
        known={r['topic_id'] for r in backlog}
        for row in view['agenda']['rows']:
            if start_date and as_of<=start_date: continue
            for t in backlog:
                if t['topic_id']==row['topic_id']: t['questions']=min(t['questions'],row['remaining'])
            if row['original_due']>=as_of or row['topic_id'] in known or row['topic_id'] not in by_id: continue
            t=by_id[row['topic_id']]
            original_due=max(row['original_due'],start_date) if start_date else row['original_due']
            backlog.append({**t,'original_due':original_due,'days_late':(_date(as_of)-_date(original_due)).days,
                            'risk':1.,'questions':row['remaining'],'missed_questions':row['remaining'],'source_days':[]})
        return {**view['agenda'],'backlog':backlog,'view':view,'token':self.agenda.token()}

    def preview_replan(self,start,days,mode,selected=None,extra_questions=20,dates=None):
        from .study_replanning import preview_replan
        current=today_local().isoformat()
        valid_date(start)
        if start<current or (_date(start)-_date(current)).days+days>548: raise ValueError('Escolha datas de hoje até18meses à frente.')
        token=self.agenda.token()
        context=self.replanning(current)
        rows=context['backlog']
        selected=selected if selected is not None else [r['topic_id'] for r in rows]
        if len(set(selected))!=len(selected) or set(selected)-{r['topic_id'] for r in rows}: raise ValueError('Selecione somente temas atrasados reconhecidos.')
        rows=[r for r in rows if r['topic_id'] in selected]
        p=AdaptiveProfile(**context['view']['profile'])
        if p.start_date and start<p.start_date: raise ValueError('Escolha uma data a partir do início do cronograma: '+p.start_date+'.')
        dist=context['view']['plan']['distribution']
        usage={current:{'new':dist['done_new'],'reviews':dist['done_reviews'],'total':context['view']['plan']['done_questions']}}
        preview=preview_replan(rows,p,start,days,mode,self.store.days(),[r for r in context['rows'] if r['topic_id'] not in selected],extra_questions,dates,usage,context['overrides'])
        if token!=self.agenda.token(): raise ValueError('Os dados mudaram durante o cálculo. Atualize a prévia.')
        preview.update({'selected':selected,'token':token,'created_day':current})
        return preview

    def apply_replan(self,preview):
        if preview['token']!=self.agenda.token() or preview['created_day']!=today_local().isoformat(): raise ValueError('O plano mudou. Atualize a prévia antes de aplicar.')
        fresh=self.preview_replan(preview['start'],preview['days'],preview['mode'],preview['selected'],preview['extra_questions'],preview['dates'])
        if fresh!=preview: raise ValueError('A prévia mudou. Recalcule antes de aplicar.')
        if not fresh['rows']: raise ValueError('Nenhum tema coube nessa distribuição. Ajuste as opções da prévia.')
        cutoff=max((e['id'] for e in self.store.events()),default=0)
        return self.agenda.append({**fresh,'kind':'reschedule.apply','cutoff':cutoff},fresh['token'])

    def cancel_replan(self,plan_id,expected_token=None):
        context=self.replanning()
        if plan_id not in {r['id'] for r in context['active']}: raise ValueError('Essa redistribuição já foi desfeita ou não existe.')
        return self.agenda.append({'kind':'reschedule.cancel','plan_id':plan_id,'created_day':today_local().isoformat()},expected_token or context['token'])
