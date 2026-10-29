"""QA visual da fase4: somente dados sintéticos descartáveis e porta8602.

Exemplos (usar o Python do ambiente de desenvolvimento):
  python scripts/check_bento_planning.py --label antes --baseline 522d7aa
  python scripts/check_bento_planning.py --label depois

O baseline sobrepõe apenas os quatro módulos de apresentação e seus dois CSS,
em um app temporário. Não faz checkout, não copia dados, backups ou ambiente.
"""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.capture_bento import demo_server, _ready as _base_ready, _screen, font_probe, SIZES
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local

SCREENS = [('calendario', 'Calendário', 'Calendário de estudos'),
           ('simulados', 'Simulados', 'Seus simulados'),
           ('evolucao', 'Evolução', 'Sua evolução')]
MODULES = ('mock_schedule_ui', 'mock_exams_ui', 'study_evolution_ui', 'study_calendar_ui')


def contrast_report(output):
    """WCAG/sRGB dos pares de texto declarados no CSS, sem estimar por imagem."""
    tokens = dict(re.findall(r'--([\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})',
                             (ROOT / 'osler/bento.css').read_text(encoding='utf-8').split('@media (prefers-contrast:more)')[0]))
    def luminance(color):
        channels = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
        linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channels]
        return sum(v*w for v, w in zip(linear, (.2126, .7152, .0722)))
    pairs = [('Texto principal', 'o-ink', 'o-card'), ('Texto de apoio', 'o-ink-2', 'o-card'),
             ('Texto secundário', 'o-ink-3', 'o-card'), ('Texto sobre fundo', 'o-ink-2', 'o-bg'),
             ('Ação primária', '#FFFFFF', 'o-primary-strong'), ('Seleção', 'o-primary-strong', 'o-primary-tint'),
             ('Descanso', 'o-sand-ink', 'o-sand')]
    pairs += [('Área '+area, 'a-'+area+'-ink', 'a-'+area+'-tint')
              for area in ('clinica', 'cirurgia', 'pediatria', 'go', 'preventiva', 'neutral')]
    rows = []
    for label, foreground, background in pairs:
        foreground = tokens.get(foreground, foreground); background = tokens.get(background, background)
        a, b = sorted((luminance(foreground), luminance(background)))
        ratio = (b+.05)/(a+.05)
        rows.append({'pair': label, 'foreground': foreground, 'background': background,
                     'ratio': round(ratio, 2), 'AA_normal_text': ratio >= 4.5})
    report = {'method': 'WCAG relative luminance sRGB; authored bento.css text pairs', 'pairs': rows,
              'scope': 'Texto em cards, chips e controles. Preenchimentos decorativos das barras não são texto; os valores têm rótulos numéricos próprios.'}
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def _ready(page, heading):
    # A marca notRunning pode ser observada antes do evento de um widget
    # alcançar o servidor. Deixe o evento iniciar e aguarde a remoção de stale.
    page.wait_for_timeout(200)
    _base_ready(page, heading)
    page.wait_for_function("!document.querySelector('[data-stale=\"true\"]')", timeout=60000)


def _choose_date(page, day):
    cell = page.locator('.st-key-calendar_cell_'+day.isoformat()+' button:visible').first
    if cell.count():
        cell.click()
        _ready(page, 'Calendário de estudos')
        return
    picker = page.locator('.st-key-calendar_reference input:visible').first
    picker.fill(day.isoformat() if picker.get_attribute('type') == 'date' else day.strftime('%d/%m/%Y'))
    picker.press('Enter')
    _ready(page, 'Calendário de estudos')


def _wrapper(temporary, baseline=None):
    """Somente código da apresentação; fontes locais seguem no static do wrapper."""
    app = temporary / 'app.py'
    (temporary / 'static/fonts').mkdir(parents=True)
    shutil.copy2(ROOT / 'static/fonts/InterVariable.woff2', temporary / 'static/fonts/InterVariable.woff2')
    source = 'import sys, types\nfrom pathlib import Path\n'
    source += f'sys.path.insert(0, {str(ROOT)!r})\n'
    if baseline:
        def previous(path):
            return subprocess.run(['git', 'show', f'{baseline}:{path}'], cwd=ROOT,
                                  check=True, capture_output=True).stdout.decode('utf-8')
        source += 'import osler\n'
        for name in MODULES:
            code = previous(f'osler/{name}.py')
            source += (f'm = types.ModuleType("osler.{name}")\n'
                       f'm.__package__ = "osler"\nm.__file__ = {str(ROOT / "osler" / (name + ".py"))!r}\n'
                       f'sys.modules["osler.{name}"] = m\nsetattr(osler, {name!r}, m)\n'
                       f'exec(compile({code!r}, m.__file__, "exec"), m.__dict__)\n')
        css = '\n'.join(previous(f'osler/{name}') for name in ('study.css', 'bento.css'))
        source += ('import streamlit as st\nimport osler.study_style as style\n'
                   'from osler.bento import area_styles\n'
                   f'def baseline_style():\n    st.html("<style>" + {css!r} + area_styles() + "</style>")\n'
                   'style.apply_study_style = baseline_style\n')
    source += 'from osler.ui import run\nrun()\n'
    app.write_text(source, encoding='utf-8')
    return app


def _metrics(page):
    return page.evaluate('''() => {
      const rect=e=>{const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}};
      const visible=e=>e.checkVisibility() && e.getBoundingClientRect().width>0;
      const main=document.querySelector('[data-testid="stMain"]');
      const cards=[...main.querySelectorAll('[class*="st-key-bento-"]')].filter(visible);
      const buttons=[...main.querySelectorAll('button')].filter(visible);
      return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
        mainWidth:main.scrollWidth,mainClientWidth:main.clientWidth,
        heading:main.querySelector('h1')?.innerText,
        metricValues:[...main.querySelectorAll('[data-testid="stMetricValue"]')].filter(visible).map(e=>({
          text:e.innerText,tag:e.tagName,fontSize:getComputedStyle(e).fontSize,
          children:[...e.querySelectorAll('*')].map(n=>({tag:n.tagName,text:n.innerText,fontSize:getComputedStyle(n).fontSize}))})),
        cards:cards.map(e=>({key:[...e.classList].find(c=>c.startsWith('st-key-')),rect:rect(e),
          padding:getComputedStyle(e).padding,background:getComputedStyle(e).backgroundColor,
          scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,
          fontSizes:[...new Set([...e.querySelectorAll('h2,h3,p,span,label')].filter(visible).map(n=>getComputedStyle(n).fontSize))]})),
        buttons:buttons.map(e=>({text:e.innerText.trim().slice(0,100),rect:rect(e),
          primary:e.getAttribute('data-testid')==='stBaseButton-primary'})),
        overflowing:[...main.querySelectorAll('h1,h2,h3,p,label,button,dl,dt,dd')].filter(visible)
          .filter(e=>e.scrollWidth>e.clientWidth+2 && getComputedStyle(e).overflowX==='visible')
          .map(e=>({text:e.innerText.slice(0,100),rect:rect(e),scroll:e.scrollWidth,client:e.clientWidth})),
        exceptions:[...document.querySelectorAll('[data-testid="stException"]')].map(e=>e.innerText)};
    }''')


def _snapshot(page, output, label, name, size, records):
    page.evaluate('document.fonts.ready')
    page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
    path = output / f'{label}-{name}-{size[0]}x{size[1]}.png'
    page.screenshot(path=str(path))
    metrics = _metrics(page)
    if metrics['exceptions']:
        raise RuntimeError(f'Exceção em {name}: {metrics["exceptions"]}')
    records.append({'screen': name, 'size': size, 'image': path.name, **metrics})
    return metrics


def _scenario_capture(page, output, label, width, height, records, interactions):
    _screen(page, 'evolucao', 'Evolução', 'Sua evolução', width)
    page.locator('.st-key-evolution_section').get_by_text('Cenários', exact=True).click()
    _ready(page, 'Sua evolução')
    journey = page.locator('.evo-journey')
    journey.wait_for(state='visible')
    text = journey.inner_text()
    assert 'Hoje' in text, 'Jornada de Cenários sem texto: o navegador pode ter removido SVG.'
    interactions[f'journey-text-{width}'] = text
    _snapshot(page, output, label, 'evolucao-cenarios', [width, height], records)


def _extras(page, output, label, width, height, records, interactions):
    """Estados reversíveis em sessão sintética; sem gravar estudo real."""
    _screen(page, 'calendario', 'Calendário', 'Calendário de estudos', width)
    for mode in ('Semana', 'Mês'):
        page.locator('.st-key-calendar_mode label').filter(has_text=mode).click()
        _ready(page, 'Calendário de estudos')
        _snapshot(page, output, label, 'calendario-'+mode.lower(), [width, height], records)
    previous = page.locator('.st-key-calendar_previous_month button:visible').first
    following = page.locator('.st-key-calendar_next_month button:visible').first
    if previous.count() and following.count():
        original = page.locator('.o-calendar-month').inner_text()
        previous.click(); _ready(page, 'Calendário de estudos')
        moved = page.locator('.o-calendar-month').inner_text()
        following.click(); _ready(page, 'Calendário de estudos')
        restored = page.locator('.o-calendar-month').inner_text()
        interactions[f'month-navigation-{width}'] = {'original': original, 'previous': moved,
                                                     'restored': restored, 'passed': original == restored != moved}
    # O seed inclui descanso e um simulado realmente registrado.
    for name, day in [('descanso', today_local()-timedelta(days=7)),
                      ('simulado', today_local()-timedelta(days=2))]:
        _choose_date(page, day)
        detail = page.locator('.st-key-calendar_selected_detail')
        detail.evaluate("e=>e.scrollIntoView({block:'start'})")
        _snapshot(page, output, label, 'calendario-'+name, [width, height], records)
    for name, visible, heading in SCREENS:
        _screen(page, name, visible, heading, width)
        if name == 'simulados':
            page.get_by_role('tab', name='Resultados', exact=True).click(); _ready(page, heading)
        if name == 'evolucao' and page.locator('.st-key-evolution_section').count():
            _scenario_capture(page, output, label, width, height, records, interactions)
            page.locator('.st-key-evolution_section').get_by_text('Histórico', exact=True).click(); _ready(page, heading)
        # Tab genuíno e Enter/Espaço no controle que recebeu foco.
        action = page.locator('[data-testid="stMain"] button:visible').first
        action.focus(); page.keyboard.press('Shift+Tab'); page.keyboard.press('Tab')
        focus = page.evaluate('''()=>({tag:document.activeElement.tagName,
          text:document.activeElement.innerText?.slice(0,100),
          outline:getComputedStyle(document.activeElement).outline,
          shadow:getComputedStyle(document.activeElement).boxShadow})''')
        interactions[f'keyboard-{name}-{width}'] = focus
        _snapshot(page, output, label, name+'-foco', [width, height], records)
        if name == 'calendario':
            cell = page.locator('[class*="st-key-calendar_cell_"] button:visible').first
            cell.focus(); page.keyboard.press('Enter'); _ready(page, heading)
            interactions[f'enter-calendar-cell-{width}'] = True
        else:
            tab = page.get_by_role('tab').first
            if tab.count():
                tab.focus(); page.keyboard.press('Space'); _ready(page, heading)
                interactions[f'space-tab-{name}-{width}'] = tab.get_attribute('aria-selected') == 'true'
        # Zoom CSS explícito, como nas fases anteriores; não simula Ctrl+plus.
        page.locator('html').evaluate("e=>e.style.zoom='2'")
        _snapshot(page, output, label, name+'-zoom200', [width, height], records)
        page.locator('html').evaluate("e=>e.style.zoom='1'")


def _case_captures(temporary, app, output, label, playwright, records, remote, interactions):
    """Vazio e nomes longos usam repositórios novos, nunca cópias do cenário."""
    from dataclasses import replace
    from osler.storage import Repository
    from osler.adaptive_service import AdaptiveService
    from osler.mock_exams import MockExams, MockExam
    url = 'http://127.0.0.1:8602/'
    for case in ('vazio', 'nomes-longos'):
        folder = temporary / case
        if case == 'vazio':
            folder.mkdir(); (folder / 'SYNTHETIC-DEMO.json').write_text('{"synthetic":true}', encoding='utf-8')
        else:
            seed_demo_data(folder, today_local())
            repository = Repository(folder); mocks = MockExams(repository); current = mocks.active()[-1]
            exam = replace(MockExam(**current['exam']),
                           name='Simulado sintético de residência médica com nome extenso para verificar leitura e continuidade das ações em telas pequenas',
                           areas=[{**a, 'area': a['area']+' — denominação sintética extensa para verificar a quebra de linha'} for a in current['exam']['areas']])
            mocks.save(exam, exam_key=current['exam_key'], expected_version=current['version'])
            service = AdaptiveService(repository)
            service.configure_day((today_local()+timedelta(days=2)).isoformat(), 120, 'descanso', 0)
            service.apply_mock_schedule(service.preview_mock_schedule((today_local()+timedelta(days=1)).isoformat(), 7))
        with demo_server(folder, url, output, app_path=app):
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            try:
                for width, height in ((1366, 768), (390, 844)):
                    context = browser.new_context(viewport={'width': width, 'height': height}, reduced_motion='reduce')
                    def local_only(route):
                        if urlsplit(route.request.url).hostname in {'127.0.0.1', None}: route.continue_()
                        else: remote.append(route.request.url); route.abort()
                    context.route('**/*', local_only)
                    page = context.new_page(); page.goto(url); _ready(page, 'Olá')
                    for name, visible, heading in SCREENS:
                        _screen(page, name, visible, heading, width)
                        if name == 'simulados':
                            page.get_by_role('tab', name='Resultados', exact=True).click(); _ready(page, heading)
                        _snapshot(page, output, label, case+'-'+name, [width, height], records)
                        if case == 'nomes-longos' and name == 'calendario':
                            for special, day in [('descanso-programado', today_local()+timedelta(days=2)),
                                                 ('simulado-programado', today_local()+timedelta(days=1))]:
                                _choose_date(page, day)
                                detail = page.locator('.st-key-calendar_selected_detail')
                                detail.evaluate("e=>e.scrollIntoView({block:'start'})")
                                _snapshot(page, output, label, special, [width, height], records)
                                interactions[f'{special}-{width}'] = detail.inner_text()
                    context.close()
            finally:
                browser.close()


def capture(label, baseline=None, output=None, extras=True, extras_only=False, scenarios=False):
    from playwright.sync_api import sync_playwright
    output = Path(output or ROOT / 'evidencias/bento/fase4'); output.mkdir(parents=True, exist_ok=True)
    records, remote, interactions, fonts = [], [], {}, []
    url = 'http://127.0.0.1:8602/'
    with tempfile.TemporaryDirectory(prefix='osler-bento-fase4-') as temporary:
        temporary = Path(temporary)
        scenario = temporary / 'scenario'; seed_demo_data(scenario, today_local())
        app = _wrapper(temporary, baseline)
        with demo_server(scenario, url, output, app_path=app), sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            try:
                for width, height in SIZES:
                    if extras_only and width not in (1366, 390): continue
                    context = browser.new_context(viewport={'width': width, 'height': height},
                                                  device_scale_factor=1, reduced_motion='reduce')
                    def local_only(route):
                        if urlsplit(route.request.url).hostname in {'127.0.0.1', None}: route.continue_()
                        else: remote.append(route.request.url); route.abort()
                    context.route('**/*', local_only)
                    page = context.new_page(); page.goto(url); _ready(page, 'Olá')
                    fonts.append({'size': [width, height], **font_probe(page)})
                    for name, visible, heading in [] if extras_only else SCREENS:
                        _screen(page, name, visible, heading, width)
                        page.locator('[data-testid="stMain"]').evaluate('e=>e.scrollTop=0')
                        _snapshot(page, output, label, name, [width, height], records)
                        if name == 'simulados':
                            page.get_by_role('tab', name='Resultados', exact=True).click(); _ready(page, heading)
                            _snapshot(page, output, label, 'simulados-resultados', [width, height], records)
                    if extras and label == 'depois' and width in (1366, 390):
                        _extras(page, output, label, width, height, records, interactions)
                    elif scenarios and label == 'depois' and width in (1366, 390):
                        _scenario_capture(page, output, label, width, height, records, interactions)
                    context.close()
            finally:
                browser.close()
        if extras and label == 'depois':
            with sync_playwright() as p:
                _case_captures(temporary, app, output, label, p, records, remote, interactions)
        cleaned_folder = str(temporary)
    report = {'synthetic': True, 'label': label, 'baseline': baseline, 'screens': records,
              'fontEvidence': fonts, 'interaction': interactions,
              'blocked_remote_requests': sorted(set(remote)),
              'temporaryDirectoryRemoved': not Path(cleaned_folder).exists(),
              'zoomMethod': 'CSS html zoom=2; viewport preservado; não equivale ao zoom de interface do navegador'}
    report['checks'] = {
        'documentWithoutHorizontalOverflow': all(r['documentWidth'] <= r['viewport'] for r in records),
        'visibleTextWithoutOverflow': all(not r['overflowing'] for r in records),
        'visibleButtonsAtLeast44px': all(b['rect']['width'] >= 43.9 and b['rect']['height'] >= 43.9
                                          for r in records for b in r['buttons']),
        'noRemoteRequests': not remote,
        'interFallbackLoadedLocally': all(f['localFontRequests'] and any(p['isCustomFont'] for p in f['interFallbackFonts'])
                                          for f in fonts),
    }
    suffix = '-extras' if extras_only else ''
    (output / f'{label}{suffix}-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    contrast_report(output / 'contraste-texto.json')
    print(json.dumps({'synthetic': True, 'label': label, 'captures': len(records),
                      'blockedRemoteRequests': len(set(remote)), 'temporaryDirectoryRemoved': report['temporaryDirectoryRemoved']}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True, choices=['antes', 'depois'])
    parser.add_argument('--baseline', help='Commit para sobrepor apenas apresentação no wrapper temporário')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--no-extras', action='store_true')
    parser.add_argument('--extras-only', action='store_true', help='Somente estados adicionais; preserva manifesto principal')
    parser.add_argument('--scenarios', action='store_true', help='Inclui Cenários em1366/390 com prova de jornada textual')
    args = parser.parse_args()
    capture(args.label, args.baseline, args.output, not args.no_extras, args.extras_only, args.scenarios)
