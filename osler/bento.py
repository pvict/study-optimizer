"""Primitivas de apresentação Bento. Sem regra de estudo ou acesso a dados."""
from html import escape
import math
from numbers import Real

from .models import normalize_path

AREA_SLUGS={
    'clinica medica':'clinica','clinica cirurgica':'cirurgia','pediatria':'pediatria',
    'ginecologia e obstetricia':'go','preventiva & social':'preventiva',
}
AREA_LABELS={'clinica':'Clínica Médica','cirurgia':'Clínica Cirúrgica','pediatria':'Pediatria',
             'go':'Ginecologia e Obstetrícia','preventiva':'Preventiva & Social','neutral':''}
STATE_CHIPS={'dominado':('Dominado','check_circle'),'aprendendo':('Aprendendo','trending_up'),
             'alerta':('Em alerta','priority_high'),'sem_registro':('Sem estudo','radio_button_unchecked')}


def _slug(slug):return slug if isinstance(slug,str) and slug in AREA_LABELS else 'neutral'


def _text(text):
    if text is None:return '—'
    if not isinstance(text,str):raise ValueError('Texto visual inválido.')
    return escape(text,quote=True)


def _number(value,name,optional=False):
    if value is None and optional:return None
    try:valid=isinstance(value,Real) and not isinstance(value,bool) and math.isfinite(value) and value>=0
    except OverflowError:valid=False
    if not valid:
        raise ValueError(name+' deve ser um número finito e não negativo.')
    return value


def area_slug(path):
    if not path:return 'neutral'
    if not isinstance(path,(list,tuple)) or not isinstance(path[0],str):raise ValueError('Caminho do tema inválido.')
    return AREA_SLUGS.get(normalize_path([path[0]])[0],'neutral')


def eyebrow(text,slug='neutral'):
    return f'<span class="o-eyebrow o-eyebrow--{_slug(slug)}">{_text(text)}</span>'


def chip(text,state=None):
    known=isinstance(state,str) and state in STATE_CHIPS
    label=STATE_CHIPS[state][0] if known else text
    # Ícones permanecem disponíveis no mapeamento para widgets Material nativos.
    # Não emitir ligaturas de uma fonte de ícones que não foi empacotada.
    return f'<span class="o-chip o-chip--{state if known else "plain"}">{_text(label)}</span>'


def pct(done,total):
    done=_number(done,'Realizado',True);total=_number(total,'Total',True)
    if done is None or total is None or total==0:return None
    return min(1.0,done/total)


def ring(done,total,size=96):
    """SVG estático para st.markdown(..., unsafe_allow_html=True); st.html remove SVG."""
    if type(size) is not int or not 32<=size<=512:raise ValueError('Tamanho do anel deve estar entre32 e512 pixels.')
    progress=pct(done,total);radius=42;circumference=2*math.pi*radius
    label='Sem meta definida' if total is None or total==0 else f'Meta de {total:g} questões; realizado não informado' if done is None else f'{done:g} de {total:g} questões'
    arc='' if progress is None else (f'<circle cx="50" cy="50" r="42" class="o-ring-arc" fill="none" '
        f'stroke-width="9" stroke-linecap="round" stroke-dasharray="{progress*circumference:.1f} {circumference:.1f}" transform="rotate(-90 50 50)"/>')
    center='—' if progress is None else f'{done:g}/{total:g}'
    return (f'<svg class="o-ring" width="{size}" height="{size}" viewBox="0 0 100 100" role="img" aria-label="{_text(label)}">'
            f'<circle cx="50" cy="50" r="42" class="o-ring-track" fill="none" stroke-width="9"/>{arc}'
            f'<text x="50" y="54" text-anchor="middle">{center}</text></svg>')


def bar(value,slug='neutral',target=None,label=''):
    value=_number(value,'Percentual',True);target=_number(target,'Meta',True)
    _text(label)
    if target is not None and target>1:raise ValueError('Meta visual deve estar entre0 e1.')
    if value is None:
        missing=label+': percentual não informado' if label else 'Percentual não informado'
        return f'<span class="o-missing" role="img" aria-label="{_text(missing)}">—</span>'
    _number(value*100,'Percentual exibido')
    width=min(1,value)*100
    tick='' if target is None else f'<span class="o-bar-tick" style="left:{target*100:.1f}%"></span>'
    label=label or f'{value*100:.1f}%'.replace('.',',')
    return (f'<div class="o-bar" role="img" aria-label="{_text(label)}">'
            f'<span class="o-bar-fill o-bar-fill--{_slug(slug)}" style="width:{width:.1f}%"></span>{tick}</div>')


def area_styles():
    """Variações fixas por área, com os valores definidos apenas em bento.css."""
    return '\n'.join(
        f'.st-key-bento-hero-{slug}{{background:var(--a-{slug}-tint);border-color:color-mix(in srgb,var(--a-{slug}-fill) 30%,transparent)}}\n'
        f'.st-key-bento-hero-{slug} [data-testid="stBaseButton-primary"]{{background:var(--a-{slug}-solid);border-color:var(--a-{slug}-solid);color:#fff}}\n'
        f'[data-testid="stHtml"] .o-calendar-area--{slug}{{color:var(--a-{slug}-ink);background:var(--a-{slug}-tint)}}\n'
        f'[data-testid="stHtml"] .o-eyebrow--{slug}{{color:var(--a-{slug}-ink);background:var(--a-{slug}-tint)}}\n'
        f'[data-testid="stHtml"] .o-bar-fill--{slug}{{background:var(--a-{slug}-fill)}}'
        for slug in AREA_LABELS)
