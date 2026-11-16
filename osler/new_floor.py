"""Saldo do mínimo de temas novos e alternativas verificadas no alocador."""
from dataclasses import replace
from math import floor


def floor_status(profile,plan):
    target=plan['base_questions']
    enabled=profile.workload_mode=='adaptive' and plan['kind']!='descanso' and not plan.get('not_started')
    required=(min(round(target*profile.new_share),max(profile.min_block,round(target*min(profile.new_share,profile.minimum_new_share))))
              if enabled and profile.new_share>0 and profile.minimum_new_share>0 else 0)
    done=plan.get('new_questions_done_actual',plan['distribution']['done_new'])
    planned=sum(i['questions'] for i in plan['items'] if i.get('is_new_for_day',i.get('status')=='sem_registro'))
    return {'required':required,'done':done,'planned':planned,'missing':max(0,required-done-planned)}


def protected_blocks(plan):
    result={}
    for item in plan['items']:
        fixed=any(item.get(k) for k in ('rescheduled','day_swap_id','daily_proposal_preserved','correction'))
        q=item['questions'] if fixed else item.get('extra_pending',item['questions']) if item.get('added_by_user') else 0
        if q:result[item['topic_id']]=result.get(item['topic_id'],0)+q
    return result


def floor_adjustments(profile,plan,evaluate,*,has_candidates=True,control_share=None,new_capacity=None):
    """Buscar configurações dos controles atuais, sem aumentar a quantidade.

    evaluate executa o alocador com o mesmo estado, sessões e compromissos.
    Uma alternativa não pode liberar novos reduzindo um bloco já reservado.
    """
    status=floor_status(profile,plan)
    result={**status,'options':[],'reason':None}
    if not status['missing']:return result
    if not has_candidates:
        result['reason']='no_candidates'
        return result
    locked=protected_blocks(plan)
    result.update(protected_questions=sum(locked.values()),protected_topics=len(locked),
                  remaining_questions=max(0,plan['target_questions']-plan['done_questions']-sum(locked.values())),
                  new_capacity=new_capacity)
    if new_capacity is not None and new_capacity+status['done']<status['required']:
        result['reason']='limited_candidates'
        return result
    cache={}
    control_share=profile.new_share if control_share is None else control_share
    scale=profile.new_share/control_share if control_share else 1
    def check(topics,share):
        key=(topics,share)
        if key in cache:return cache[key]
        trial_profile=replace(profile,max_topics=topics,new_share=share)
        trial=evaluate(trial_profile)
        counts={i['topic_id']:i['questions'] for i in trial['items']}
        info=floor_status(trial_profile,trial)
        fits=(not info['missing'] and info['done']+info['planned']>=status['required'] and
              trial['target_questions']<=plan['target_questions'] and
              trial['done_questions']+trial['questions']<=max(plan['target_questions'],plan['done_questions']+plan['questions']) and
              all(counts.get(t,0)>=q for t,q in locked.items()))
        option={'max_topics':topics,'new_share':share,'control_new_share':share/scale if scale else share,'planned_new':info['planned'],
                'target_questions':trial['target_questions']} if fits else None
        cache[key]=option
        return option
    shares=[n/20*scale for n in range(floor(control_share*20)+1,21)]
    for topics in range(profile.max_topics+1,11):
        option=check(topics,profile.new_share)
        if option:
            result['options'].append(option);break
    for share in shares:
        option=check(profile.max_topics,share)
        if option:
            result['options'].append(option);break
    if not result['options']:
        for topics in range(profile.max_topics+1,11):
            for share in shares:
                option=check(topics,share)
                if option:break
            else:continue
            result['options'].append(option);break
    if not result['options']:result['reason']='commitments_or_capacity'
    return result
