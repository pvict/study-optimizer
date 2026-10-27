import math
import pytest

from osler.bento import area_slug,eyebrow,chip,pct,ring,bar,area_styles


@pytest.mark.parametrize('area,slug',[
    (' CLÍNICA MÉDICA ','clinica'),('clinica cirurgica','cirurgia'),('Pediatria','pediatria'),
    ('Ginecologia e Obstetrícia','go'),('Preventiva & Social','preventiva'),('Cirurgia Geral','neutral'),('Desconhecida','neutral')])
def test_actual_area_names_and_normalization(area,slug):
    assert area_slug([area,'Tema'])==slug


def test_unknown_path_and_html_attributes_are_not_interpreted():
    assert area_slug(None)==area_slug([])=='neutral'
    html=eyebrow('<script>"Olá"</script>','x" onmouseover="alert(1)')
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'o-eyebrow--neutral' in html and 'onmouseover' not in html
    html=chip('<img onerror="alert(1)">','x" onclick="bad')
    assert '<img' not in html and '&lt;img' in html and 'o-chip--plain' in html and 'onclick' not in html


def test_known_states_have_neutral_text_and_no_unserved_icon_font():
    for state,text in [('dominado','Dominado'),('aprendendo','Aprendendo'),('alerta','Em alerta'),('sem_registro','Sem estudo')]:
        html=chip('ignorado',state)
        assert text in html and 'material-symbols' not in html


def test_absent_zero_and_exceeded_goal_are_distinct():
    assert pct(None,120) is None and pct(40,None) is None and pct(0,0) is None
    assert pct(0,120)==0 and pct(40,60)==pytest.approx(2/3) and pct(150,120)==1
    missing=ring(None,0)
    assert 'Sem meta definida' in missing and 'stroke-dasharray' not in missing and '—' in missing
    html=ring(40,60)
    assert '40 de 60 questões' in html and f'{2*math.pi*42*2/3:.1f}' in html
    assert '150 de 120 questões' in ring(150,120)
    assert 'Percentual não informado' in bar(None) and 'o-bar-fill' not in bar(None)
    assert 'width:0.0%' in bar(0) and 'width:100.0%' in bar(1.2)


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True,'20',-1])
def test_invalid_numbers_never_reach_css_or_svg(value):
    for call in (lambda:pct(value,120),lambda:pct(20,value),lambda:ring(value,120),lambda:bar(value),lambda:bar(.5,target=value)):
        with pytest.raises(ValueError):call()


@pytest.mark.parametrize('size',[0,-1,True,float('nan'),'96',10000])
def test_svg_size_is_bounded(size):
    with pytest.raises(ValueError):ring(40,60,size)


def test_bar_escapes_aria_and_limits_target_and_classes():
    html=bar(.5,slug='bad" onclick="evil',target=.9,label='Acerto <script>')
    assert 'o-bar-fill--neutral' in html and 'onclick' not in html
    assert 'left:90.0%' in html and '&lt;script&gt;' in html and '<script>' not in html
    with pytest.raises(ValueError):bar(.5,target=1.2)
    css=area_styles()
    assert all(f'.st-key-bento-hero-{slug}' in css for slug in ['clinica','cirurgia','pediatria','go','preventiva','neutral'])
    assert '#FF6B6B' not in css  # valores estão exclusivamente nos tokens CSS


def test_absent_percentage_remains_explicit_with_custom_accessible_label():
    assert 'Acerto: percentual não informado' in bar(None,label='Acerto')
    for value in (10**400,1e308):
        with pytest.raises(ValueError):bar(value)
