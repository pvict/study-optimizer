"""Leitura de atividade e retorno do bloco, sem criar resultados ou reservas."""
from .models import normalize_path
from .planner_snapshot import planner_supply


def day_activity(view):
    events=sorted((s for s in view['sessions'] if s['entry']['day']==view['date'] and
                   s['entry']['kind']!='acumulado'),key=lambda s:s.get('id',0),reverse=True)
    return {'events':events,'questions':sum(s['entry']['questions'] for s in events),
            'blocks':sum(s['entry']['kind']=='bloco' for s in events),
            'contacts':sum(s['entry']['kind']=='contato' for s in events)}


def result_feedback(view,session_id):
    event=next((s for s in view['sessions'] if s['session_id']==session_id),None)
    if event is None: return None
    e=event['entry']; n=e['questions']
    state=next((s for s in view['states'] if normalize_path(s['path'])==normalize_path(e['path'])),None)
    target=state['target_accuracy'] if state else view['profile']['target_accuracy']
    accuracy=100*e['correct']/n if n and e.get('correct') is not None else e.get('percent')
    conviction=100*e['confident_correct']/n if n and e.get('confident_correct') is not None else None
    if e['kind']=='contato':
        level,message='info','Contato registrado. Sem questões respondidas, não há uma nova medida de desempenho.'
    elif e['kind']=='acumulado':
        level,message='info','Histórico atualizado. Este total anterior não entra nas questões feitas hoje.'
    elif conviction is None and accuracy is not None and accuracy<target:
        level,message='warning',f'Acerto abaixo da meta de {target:g}% neste bloco. Confira as explicações dos erros; a convicção não foi informada.'
    elif conviction is None:
        level,message='info','Convicção não informada. O acerto foi registrado, mas ainda falta medir a segurança das respostas.'
    elif conviction>=target:
        level,message='success',f'Convicção na meta de {target:g}% neste bloco. Continue conferindo a retenção em encontros espaçados.'
    elif conviction<60:
        level,message='warning','Este bloco pede reforço: menos de 60% das respostas tiveram acerto com convicção.'
    else:
        level,message='warning',f'Convicção abaixo da meta de {target:g}%. Retome as respostas erradas e as que acertou sem segurança.'
    balanced=view['profile'].get('review_strategy')=='balanced_v2'
    if balanced and e['kind']=='bloco':
        if accuracy is None: level,message='info','Acerto não informado. Falta uma medição objetiva para ajustar a revisão do tema.'
        elif accuracy<60: level,message='warning','O bloco teve menos de 60% de acertos. Confira os erros antes do próximo contato.'
        elif accuracy>=target: level,message='success',f'Acerto na meta de {target:g}% neste bloco. O intervalo depende também da amostra e dos encontros espaçados.'
        else: level,message='info',f'Acerto de {accuracy:.1f}% neste bloco, para uma meta de {target:g}%. A amostra e o histórico orientam o próximo contato; insegurança não foi tratada como erro.'
    pending=next(({'questions':q['questions'],'due_date':q['due_date']} for q in view['review_queue'] if q['session_id']==session_id),None)
    next_contact=next_questions=dose_kind=next_kind=theme_questions=theme_contact=None
    coordinated=False
    next_action='Confira as explicações das respostas erradas e sem convicção antes do próximo contato.'
    if state and not state.get('historical_aggregate'):
        next_questions=state.get('theme_recommended_questions',state['recommended_questions'])
        dose_kind=state.get('dose_kind')
        due=state.get('reschedule_date') or state.get('theme_review_due') or state.get('next_review')
        next_contact=max(due or view['date'],view['date'],view['profile'].get('start_date') or view['date'])
        if balanced:
            from .study_capacity import practice_state
            from .study_models import AdaptiveProfile
            p=AdaptiveProfile(**view['profile'])
            theme_questions=next_questions;theme_contact=next_contact
            due=min([q['due_date'] for q in state.get('pending_reviews',[])]+([due] if due else []),default=None)
            next_contact=max(due or view['date'],view['date'],p.start_date or view['date'])
            encounter=practice_state(state,next_contact,p)
            next_questions=encounter['recommended_questions'];next_kind=encounter['review_kind']
        if next_contact>view['profile']['exam_date']: next_contact=None
        if theme_contact and theme_contact>view['profile']['exam_date']: theme_contact=None
        coordinated=bool(balanced and pending and next_contact==pending['due_date'] and next_kind=='combined')
        if dose_kind=='maintenance': next_action='Faça a manutenção com uma amostra de diferentes partes do tema; use novos exemplos quando possível.'
        elif dose_kind in {'diagnostic','practice'}: next_action='No próximo bloco, explore diferentes partes do tema e informe também a convicção.'
        if next_kind=='lot_only': next_action='Faça o retorno vinculado das respostas indicadas. Esse encontro já faz parte da carga; não exige um bloco completo adicional.'
    else:
        next_action='Este registro não tem um tema específico disponível para planejar. Consulte Temas antes de escolher o próximo bloco.'
    return {'event':event,'entry':e,'target':target,'accuracy_pct':accuracy,'conviction_pct':conviction,
            'approximate':e.get('percent') is not None,
            'mistakes':n-e['correct'] if e.get('correct') is not None else None,
            'guesses':e['correct']-e['confident_correct'] if conviction is not None else None,
            'pending':pending,'next_contact':next_contact,'next_questions':next_questions,'coordinated_return':coordinated,
            'next_review_kind':next_kind,'theme_questions':theme_questions,'theme_contact':theme_contact,
            'planner_supply':planner_supply(state,next_questions,0,view['date']) if state and next_questions is not None else None,
            'dose_kind':dose_kind,'next_action':next_action,'level':level,'message':message,
            'small_block':e['kind']=='bloco' and n<view['profile']['min_block']}
