"""Escolha de uma medição para exibição; não mistura fontes nem altera o modelo."""
from collections import defaultdict

from .models import normalize_path
from .study_statistics import MODES,period_bounds


def _label(day):
    return '/'.join(reversed(day.split('-')))


def confidence_presentation(rows,sessions,period,reference,mode='Todas',*,include_snapshot=False):
    start,end=period_bounds(period,reference)
    dates=defaultdict(list)
    for session in sessions:
        entry=session['entry']
        if (entry['kind']!='bloco' or entry.get('confident_correct') is None or not entry['questions'] or
                entry['day']>end or start and entry['day']<start or MODES[mode] and entry['mode']!=MODES[mode]): continue
        dates[tuple(normalize_path(entry['path']))].append(entry['day'])
    displayed=[]
    for row in rows:
        days=dates[tuple(normalize_path(row['Caminho'].split(' → ')))]; last=max(days,default=None)
        value=row['Com convicção (%)']; count=row['Questões com convicção informada']
        snapshot_day=row.get('Retrato Osler'); snapshot_value=row.get('Convicção (%)')
        use_snapshot=bool(include_snapshot and snapshot_day and snapshot_day<=end and snapshot_value is not None and
                          row.get('Questões distintas Osler') and (value is None or not last or snapshot_day>last))
        if use_snapshot:
            value=snapshot_value
            basis=f"Osler · {row['Questões distintas Osler']} questões distintas · {_label(snapshot_day)}"
        elif value is not None and count and last:
            window=_label(last) if min(days)==last else _label(min(days))+' a '+_label(last)
            basis=f'App · {count} tentativas · {window}'
            if include_snapshot and snapshot_value is not None and snapshot_day==last: basis+=' · retrato no mesmo dia'
        else:
            value=None; basis='Sem convicção informada neste recorte'
        displayed.append({**row,'Convicção principal (%)':value,'Base da convicção':basis})
    return displayed
