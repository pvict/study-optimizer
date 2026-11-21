"""Trocas auditáveis apenas no plano de hoje; histórico de estudo intacto."""
import uuid
from collections import defaultdict
from datetime import timedelta
from .planner_service import today_local
from .models import normalize_path
from .study_swaps import replacement_candidates,swap_rows
from .planning import _date
from .study_models import AdaptiveProfile
from .study_replanning import preview_replan
from .study_allocation import topic_is_new


class DailySwapServiceMixin:
    def preview_return_deferral(self,day,topic_id):
        """Adia disponibilidade declarada; nunca altera resultados ou a origem do lote."""
        if day!=today_local().isoformat(): raise ValueError('Adie o retorno pelo plano de hoje.')
        token=self.agenda.token()
        view=self.overview(day)
        item=next((t for t in view['plan']['items'] if t['topic_id']==topic_id),None)
        if item is None: raise ValueError('Esse bloco não está mais no plano. Atualize a página.')
        lots=[q for q in item.get('pending_reviews',[]) if q['due_date']<=day]
        if not lots: raise ValueError('Este bloco não tem retornos previstos para hoje.')
        tomorrow=(_date(day)+timedelta(days=1)).isoformat()
        if tomorrow>view['profile']['exam_date']: raise ValueError('Amanhã está depois do fim da preparação. Ajuste a data em Ajustes antes de adiar.')
        previous=next((r for r in view['agenda']['rows'] if r['topic_id']==topic_id),{})
        cutoff=max((e['id'] for e in self.store.events()),default=0)
        row={'topic_id':topic_id,'path':item['path'],'date':tomorrow,'original_due':tomorrow,
             'previous_original_due':previous.get('original_due',min(q.get('original_due_date',q['due_date']) for q in lots)),
             'questions':max(item['questions'],previous.get('remaining',0)),
             'new_topic':topic_is_new(item),'return_unavailable':True}
        payload={'kind':'reschedule.apply','scope':'return_unavailable','created_day':day,'available_from':tomorrow,
                 'selected':[topic_id],'rows':[row],'overrides':{},'cutoff':cutoff,
                 'return_dates':{q['session_id']:tomorrow for q in lots}}
        agenda=self.agenda.active(view['sessions'],day,proposed=payload)
        after=self.overview(day,_agenda_override=agenda)
        original_ids={i['topic_id'] for i in view['plan']['items']}
        replacements=[i for i in after['plan']['items'] if i['topic_id'] not in original_ids]
        if self.agenda.token()!=token: raise ValueError('Seu plano mudou. Confira o adiamento novamente.')
        return {'day':day,'topic_id':topic_id,'token':token,'available_from':tomorrow,'item':item,
                'plan':after['plan'],'replacements':replacements,'payload':payload}

    def defer_return(self,day,topic_id,expected_token):
        if self.agenda.token()!=expected_token: raise ValueError('Seu plano mudou. Confira o adiamento novamente.')
        preview=self.preview_return_deferral(day,topic_id)
        if preview['token']!=expected_token: raise ValueError('Seu plano mudou. Confira o adiamento novamente.')
        return self.agenda.append({**preview['payload'],'request_id':uuid.uuid4().hex},expected_token)

    def undo_return_deferral(self,day,plan_id,expected_token):
        if day!=today_local().isoformat(): raise ValueError('Desfaça pelo plano de hoje.')
        active=self.agenda.active(self.store.active(day),day)
        record=next((r for r in active.get('return_deferrals',[]) if r['id']==plan_id and r['created_day']==day),None)
        if record is None: raise ValueError('Esse adiamento já não está ativo hoje.')
        return self.agenda.append({'kind':'reschedule.cancel','plan_id':plan_id,'created_day':day},expected_token)

    def _swap_return_plan(self,view,original):
        from .study_calendar import forecast_calendar
        profile=AdaptiveProfile(**view['profile'])
        start=(_date(view['date'])+timedelta(days=1)).isoformat()
        available=min(90,(_date(profile.exam_date)-_date(start)).days+1)
        if available<=0: return None
        for days in sorted({min(14,available),min(30,available),available}):
            calendar=forecast_calendar(view['planning_states'],profile,view['date'],days+1,
                                       view['sessions'],self.store.days(),view['plan'],view['agenda'])
            usage=defaultdict(lambda:{'new':0,'reviews':0,'total':0,'slots':0})
            for day in calendar[1:]:
                for item in day['items']:
                    if item['topic_id']==original['topic_id'] or item.get('rescheduled') or item['priority']=='normal': continue
                    group='new' if topic_is_new(item) else 'reviews'
                    usage[day['date']][group]+=item['questions']
                    usage[day['date']]['total']+=item['questions']
                    usage[day['date']]['slots']+=1
            due=original.get('original_due') or original.get('retention_due') or view['date']
            row={**original,'original_due':due,'days_late':max(0,(_date(view['date'])-_date(due)).days)}
            existing=[r for r in view['agenda']['rows'] if r['topic_id']!=original['topic_id']]
            proposal=preview_replan([row],profile,start,days,'balanced',self.store.days(),existing,
                                    usage=usage,previous_overrides=view['agenda']['overrides'])
            if not proposal['rows']:
                share=profile.new_share if topic_is_new(original) else 1-profile.new_share
                chunk=max(min(profile.min_block,original['questions']),min(original['questions'],int(profile.max_questions*share)))
                if chunk<original['questions']:
                    proposal=preview_replan([{**row,'questions':chunk}],profile,start,days,'balanced',self.store.days(),existing,
                                           usage=usage,previous_overrides=view['agenda']['overrides'])
            if proposal['rows']:
                row=proposal['rows'][0]
                balance=max((r['remaining'] for r in view['agenda']['rows'] if r['topic_id']==original['topic_id']),default=original['questions'])
                return {**row,'first_block_questions':row['questions'],'questions':max(original['questions'],balance)}
        return None

    def swap_options(self,day,topic_id):
        if day!=today_local().isoformat(): raise ValueError('Troque os temas no plano de hoje. O histórico dos outros dias fica preservado.')
        token=self.agenda.token()
        view=self.overview(day)
        original=next((t for t in view['plan']['items'] if t['topic_id']==topic_id),None)
        if original is None: raise ValueError('Esse bloco não está mais no plano. Atualize a página.')
        excluded={t['topic_id'] for t in view['plan']['items']}
        done={tuple(normalize_path(s['entry']['path'])) for s in view['sessions'] if s['entry']['day']==day and s['entry']['kind']=='bloco'}
        excluded.update(t['topic_id'] for t in view['planning_states'] if tuple(normalize_path(t['path'])) in done)
        excluded.update(r['topic_id'] for r in view['agenda']['rows'])
        for swap in view['agenda'].get('swaps',[]):
            if swap['day']==day: excluded.update(swap['excluded_ids'])
        result=replacement_candidates(original,view['planning_states'],excluded,day)
        result['return_plan']=self._swap_return_plan(view,original)
        if self.agenda.token()!=token: raise ValueError('Seu plano mudou. Abra a troca novamente.')
        return {**result,'original':original,'token':token,'view':view}

    def swap_topic(self,day,source_id,target_id,expected_token,mode='manual'):
        if self.agenda.token()!=expected_token: raise ValueError('Seu plano mudou. Abra a troca novamente.')
        if mode not in {'manual','recommended'}: raise ValueError('Forma de escolha inválida.')
        options=self.swap_options(day,source_id)
        if options['token']!=expected_token: raise ValueError('Seu plano mudou. Abra a troca novamente.')
        chosen=next((t for t in options['manual'] if t['topic_id']==target_id),None)
        if chosen is None: raise ValueError('Escolha um tema específico disponível, com banco suficiente e fora dos outros blocos.')
        if mode=='recommended' and (options['recommended'] is None or options['recommended']['topic_id']!=target_id):
            raise ValueError('A sugestão mudou. Confira novamente.')
        original=options['original']
        if not options['return_plan']: raise ValueError('Não há vaga para remanejar este bloco nos próximos 90 dias antes da prova. Ajuste a rotina antes de trocar.')
        previous=next((s for s in options['view']['agenda'].get('swaps',[]) if s['slot_id']==original.get('day_swap_id')),None)
        slot=previous['slot_id'] if previous else uuid.uuid4().hex
        cutoff=max((e['id'] for e in self.store.events()),default=0)
        prior=swap_rows([previous],options['view']['sessions'],day)[0] if previous else {}
        payload={'kind':'day.swap','slot_id':slot,'day':day,'created_day':today_local().isoformat(),
                 'origin_id':previous.get('origin_id',source_id) if previous else source_id,
                 'topic_id':target_id,'path':chosen['path'],'from_path':original['path'],
                 'excluded_ids':sorted(set((previous['excluded_ids'] if previous else [])+[source_id])),
                 'questions':original['questions'],'cutoff':cutoff,'mode':mode,
                 'allowed_peers':[t['topic_id'] for t in options['view']['plan']['items'] if t['topic_id']!=source_id],
                 'peer_origins':[t.get('day_swap_origin_id',t['topic_id']) for t in options['view']['plan']['items'] if t['topic_id']!=source_id],
                 'reference_share':options['view']['profile']['new_share'],
                 'allocation_share':options['view']['plan']['capacity'].get('effective_share',options['view']['profile']['new_share']),
                 'quota_path':original.get('swap_quota_path',original['path']),
                 'extra_only':original.get('is_extra_swap',bool(original.get('added_by_user') and original.get('extra_pending')==original['questions'])),
                 'extra_ids':sorted(set(original.get('swap_extra_ids',[])+[e['extra_id'] for e in options['view']['day']['settings']['extra_topics'] if e['topic_id']==source_id])),
                 'prior_credits':prior.get('prior_credits',[])+prior.get('credits',[]),
                 'returns':(previous.get('returns',[]) if previous else [])+[{**options['return_plan'],'cutoff':cutoff}]}
        self.agenda.append(payload,expected_token)
        return slot

    def undo_swap(self,day,slot_id,expected_token):
        if day!=today_local().isoformat(): raise ValueError('Somente as trocas de hoje podem ser desfeitas.')
        active=self.agenda.active(self.store.active(day),day).get('swaps',[])
        chosen=next((s for s in active if s['day']==day and s['slot_id']==slot_id),None)
        if chosen is None: raise ValueError('Essa troca já não está ativa.')
        return self.agenda.append({'kind':'day.swap.cancel','slot_id':slot_id,'apply_id':chosen['id'],'day':day,'created_day':day},expected_token)
