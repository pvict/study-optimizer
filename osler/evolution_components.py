"""Componentes geométricos da jornada; valores escapados e estados explícitos."""
from html import escape
from datetime import timedelta
from .planning import _date


def number(n): return f'{n:,}'.replace(',','.')
def date_label(day): return '/'.join(reversed(day.split('-')))


def point_at(snapshot,day):
    if day==snapshot['as_of']: return snapshot['points'][0]
    return next((p for p in reversed(snapshot['points']) if p['date']<=day),snapshot['points'][0])


def journey_svg(context,selected,mobile=False):
    snapshot=context['snapshot']; today=context['as_of']; end=context['end']
    end_label='Fim da preparação' if context['exam_in_horizon'] else 'Horizonte disponível'
    candidates=[('Hoje',today)]+[(label,(_date(today)+timedelta(days=n)).isoformat()) for label,n in [('2 semanas',14),('1 mês',30),('3 meses',90)] if (_date(today)+timedelta(days=n)).isoformat()<end]+[(end_label,end)]
    seen=set(); nodes=[]
    for label,day in candidates:
        if day not in seen: nodes.append((label,day)); seen.add(day)
    if mobile:
        label=next((label for label,day in nodes if day==selected),'Data escolhida')
        nodes=[('Hoje',today)]+([(label,selected)] if today<selected<end else [])+([(end_label,end)] if end>today else [])
    w=360 if mobile else 1040; h=70*len(nodes)+12 if mobile else 190
    last=max(1,len(nodes)-1)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="Jornada: realizado hoje e marcos previstos até o fim do cenário" font-family="Arial, sans-serif">']
    if len(nodes)>1:
        coords=f'x1="18" y1="28" x2="18" y2="{28+70*(len(nodes)-1)}"' if mobile else 'x1="26" y1="28" x2="858" y2="28"'
        parts.append(f'<line {coords} stroke="#9babbe" stroke-width="2" stroke-dasharray="5 5"/>')
    for i,(label,day) in enumerate(nodes):
        p=point_at(snapshot,day); x=18 if mobile else 26+i*832/last; y=28+70*i if mobile else 28
        real=day==today; active=day==selected
        parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="'+('#0066CC' if real or active else '#ffffff')+'" stroke="#005BB5" stroke-width="2"/>')
        tx=42 if mobile else x; ty=y-2 if mobile else 63
        label_text=label+' · '+day[8:10]+'/'+day[5:7] if mobile else label
        parts.append(f'<text x="{tx}" y="{ty}" fill="#1D1D1F" font-size="16" font-weight="600">{escape(label_text)}</text>')
        if not mobile: parts.append(f'<text x="{tx}" y="87" fill="#52627a" font-size="14">{date_label(day)}</text>')
        detail=f"{number(p['attempts'])} respostas · {p['coverage_pct']:.0f}% dos temas" if mobile else f"{number(p['attempts'])} respostas no app"
        parts.append(f'<text x="{tx}" y="{ty+22 if mobile else 112}" fill="#1D1D1F" font-size="14">{escape(detail)}</text>')
        if not mobile: parts.append(f'<text x="{tx}" y="135" fill="#1D1D1F" font-size="14">{p["coverage_pct"]:.0f}% dos temas</text>')
        parts.append(f'<text x="{tx}" y="{ty+41 if mobile else 158}" fill="#52627a" font-size="13">'+('Realizado e documentado' if real else 'Previsto no cenário')+'</text>')
    return ''.join(parts)+'</svg>'


def journey_html(context,selected):
    """Marcos em HTML nativo: st.html remove SVG e deixava a jornada vazia."""
    snapshot=context['snapshot']; today=context['as_of']; end=context['end']
    end_label='Fim da preparação' if context['exam_in_horizon'] else 'Horizonte disponível'
    candidates=[('Hoje',today)]+[(label,(_date(today)+timedelta(days=n)).isoformat()) for label,n in [('2 semanas',14),('1 mês',30),('3 meses',90)] if (_date(today)+timedelta(days=n)).isoformat()<end]+[(end_label,end)]
    seen=set(); nodes=[]
    for label,day in candidates:
        if day not in seen: nodes.append((label,day)); seen.add(day)
    if today<selected<end and selected not in seen:
        nodes.append(('Data escolhida',selected));nodes.sort(key=lambda node:node[1])
    pieces=['<div class="evo-journey"><ol class="o-journey-nodes" aria-label="Marcos realizados e previstos no cenário">']
    for label,day in nodes:
        point=point_at(snapshot,day);real=day==today
        pieces.append('<li'+(' aria-current="step"' if day==selected else '')+'><strong>'+escape(label)+
            '</strong><time datetime="'+escape(day)+'">'+escape(date_label(day))+'</time><p>'+escape(number(point['attempts']))+
            ' respostas no app</p><p>'+f"{point['coverage_pct']:.0f}% dos temas"+'</p><small>'+
            ('Realizado e documentado' if real else 'Previsto no cenário')+'</small></li>')
    return ''.join(pieces)+'</ol></div>'


def achievement_html(achievements):
    pieces=['<ul class="evo-achievements" aria-label="Conquistas verificáveis">']
    for a in achievements:
        status='Conquistado' if a['earned'] else 'Previsto em '+date_label(a['projected_date']) if a['projected_date'] else 'Em construção'
        if a['earned'] and not a['earned_date']: status='Reconhecido no histórico'
        path='<path d="m6 12 4 4 8-8"/>' if a['earned'] else '<path d="M8 4h10v9H8M8 4v16"/>'
        icon='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+path+'</svg>'
        pieces.append('<li class="'+('earned' if a['earned'] else 'pending')+'">'+icon+'<div><strong>'+escape(a['title'])+'</strong><span>'+escape(status)+'</span><p>'+escape(a['description'])+'</p></div></li>')
    return ''.join(pieces)+'</ul>'
