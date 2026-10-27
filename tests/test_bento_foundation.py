from pathlib import Path
import re
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def test_both_stylesheets_are_loaded_in_order_without_remote_resources(monkeypatch):
    from osler import study_style
    rendered=[];monkeypatch.setattr(study_style.st,'html',rendered.append)
    study_style.apply_study_style()
    html=''.join(rendered)
    assert html.index('container: study')<html.index('--o-primary:')
    assert '.st-key-bento-hero-cirurgia' in html
    assert 'https://' not in html and 'unsafe_allow_javascript' not in html


def test_local_font_and_static_config_have_a_license():
    config=tomllib.loads((ROOT/'.streamlit/config.toml').read_text(encoding='utf-8'))
    assert config['server']['enableStaticServing'] is True
    font=ROOT/'static/fonts/InterVariable.woff2'
    assert font.read_bytes().startswith(b'wOF2')
    assert 'SIL OPEN FONT LICENSE' in (ROOT/'docs/third-party/Inter-OFL.txt').read_text(encoding='utf-8')
    css=(ROOT/'osler/bento.css').read_text(encoding='utf-8')
    assert '/app/static/fonts/InterVariable.woff2' in css and 'font-display:swap' in css.replace(' ','')
    assert '.emotion-' not in css and '.css-' not in css and 'http' not in css


def test_fixed_tokens_and_neutral_states_are_presentation_only():
    css=(ROOT/'osler/bento.css').read_text(encoding='utf-8')
    for token,value in [('--o-bg','#F6F7FB'),('--o-card','#FFFFFF'),('--o-primary','#4F46E5'),
                        ('--a-cirurgia-fill','#FF6B6B'),('--a-pediatria-solid','#047857'),('--a-preventiva-ink','#92400E')]:
        assert re.search(re.escape(token)+r'\s*:\s*'+re.escape(value),css,re.I)
    assert 'prefers-reduced-motion' in css and 'corner-shape' in css
    assert 'outline-offset:3px' in css.replace(' ','')
    assert '--study-success:var(--o-ink)' in css.replace(' ','')
    assert '--study-warning:var(--o-ink)' in css.replace(' ','')


def test_native_caption_opacity_and_small_controls_have_explicit_accessible_base():
    css=(ROOT/'osler/bento.css').read_text(encoding='utf-8')
    assert re.search(r'\[data-testid="stCaptionContainer"\]\s*\{[^}]*opacity:\s*1',css)
    assert re.search(r'button\s*\{[^}]*min-width:\s*44px',css)


def test_used_text_pairs_meet_aa_without_using_decorative_fills_as_text():
    def lum(value):
        values=[int(value[i:i+2],16)/255 for i in (1,3,5)]
        return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip([.2126,.7152,.0722],values))
    pairs=[('#111827','#F6F7FB'),('#4B5563','#F6F7FB'),('#6B7280','#FFFFFF'),
           ('#3730A3','#EEF2FF'),('#B42318','#FFF1F0'),('#047857','#ECFDF5'),
           ('#6D28D9','#F5F3FF'),('#92400E','#FFFBEB')]
    for fg,bg in pairs:
        a,b=sorted([lum(fg),lum(bg)])
        assert (b+.05)/(a+.05)>=4.5,(fg,bg)
def test_svg_ring_uses_native_markdown_renderer_and_stable_css_anchor():
    css = (ROOT / 'osler/bento.css').read_text(encoding='utf-8')
    fixture = (ROOT / 'tests/fixtures/bento_components_app.py').read_text(encoding='utf-8')
    assert '[data-testid="stMarkdownContainer"]' in css
    assert 'st.markdown(ring(40,60),unsafe_allow_html=True)' in fixture
