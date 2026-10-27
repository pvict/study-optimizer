"""Verifica estados de Hoje somente em cenários sintéticos temporários, porta8602."""
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_ready
from scripts.seed_demo_data import seed_demo_data
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.planner_service import today_local


def check(output):
    from playwright.sync_api import sync_playwright
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    results=[];remote=[];interaction={};url='http://127.0.0.1:8602/'
    with tempfile.TemporaryDirectory(prefix='osler-bento-fase2-check-') as temporary:
        root=Path(temporary).resolve()
        assert root.is_relative_to(Path(tempfile.gettempdir()).resolve()) and root.name.startswith('osler-bento-fase2-check-')
        for case in ['rest','complete','not_started','mock','empty','error','linked']:
            folder=root/case;today=today_local();day=today.isoformat()
            if case in {'empty','error'}:
                folder.mkdir();(folder/'SYNTHETIC-DEMO.json').write_text('{"synthetic":true}')
            else:seed_demo_data(folder,today)
            service=AdaptiveService(Repository(folder));record=service.store.profile()
            if case=='rest':service.configure_day(day,120,'descanso',0)
            elif case=='complete':
                topic=service.catalog(day)[0][0]
                service.save_entry(StudyEntry(topic['path'],day,100,correct=90),session_id='demo-complete')
            elif case=='not_started':service.store.save_profile(replace(AdaptiveProfile(**record['configured_profile']),start_date=(today+timedelta(days=5)).isoformat()),record['id'])
            elif case=='mock':service.apply_mock_schedule(service.preview_mock_schedule(day,7))
            elif case=='linked':service.store.save_profile(replace(AdaptiveProfile(**record['configured_profile']),review_strategy='balanced_v2'),record['id'])
            before=service.store.events()
            app_path=ROOT/'app.py'
            if case=='error':
                app_path=root/'error_app.py'
                app_path.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom osler.adaptive_service import AdaptiveService\ndef fail(*args):raise ValueError("Falha sintética ao carregar o plano. Abra os arquivos para conferir.")\nAdaptiveService.overview=fail\nfrom osler.ui import run\nrun()\n',encoding='utf-8')
            with demo_server(folder,url,output,app_path),sync_playwright() as p:
                browser=p.chromium.launch(channel='msedge',headless=True)
                for width,height in [(1366,768),(390,844)]:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    def local_only(route):
                        if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                        else:remote.append(route.request.url);route.abort()
                    context.route('**/*',local_only)
                    page=context.new_page();page.goto(url);_ready(page,'Olá')
                    collapse=page.get_by_role('button',name='Collapse sidebar',exact=True)
                    if width<900 and collapse.is_visible():collapse.click()
                    assert not page.get_by_test_id('stException').count(),case
                    expected={'rest':'Hoje é descanso','complete':'Meta registrada','not_started':'Tudo pronto para começar',
                        'mock':'Hoje é dia de simulado','empty':'Seu estudo começa aqui','error':'Falha sintética','linked':'Ritmo da semana'}[case]
                    assert expected in page.locator('[data-testid=stMain]').inner_text(),case
                    page.screenshot(path=str(output/f'estado-{case}-{width}x{height}.png'))
                    metrics=page.evaluate('''()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
                      cards:[...document.querySelectorAll('[class*="st-key-bento-"]')].map(e=>({key:[...e.classList].find(c=>c.startsWith('st-key-')),padding:getComputedStyle(e).padding,background:getComputedStyle(e).backgroundColor,
                        rect:e.getBoundingClientRect().toJSON(),primary:e.querySelectorAll('[data-testid="stBaseButton-primary"]').length})),
                      buttons:[...document.querySelectorAll('[data-testid="stMain"] button')].filter(e=>e.checkVisibility()).map(e=>({label:e.innerText,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
                      colors:Object.fromEntries(['--o-ink','--o-ink-2','--o-card','--o-bg','--o-primary-strong','--o-primary-tint','--o-sand','--o-sand-ink',...['clinica','cirurgia','pediatria','go','preventiva','neutral'].flatMap(s=>['ink','tint','solid'].map(k=>'--a-'+s+'-'+k))].map(k=>[k,getComputedStyle(document.documentElement).getPropertyValue(k).trim()]))})''')
                    assert metrics['documentWidth']<=width,case
                    assert all(b['height']>=44 and b['width']>=44 for b in metrics['buttons']),case
                    assert all(c['primary']<=1 for c in metrics['cards']),case
                    results.append({'case':case,'size':[width,height],**metrics})
                    if case=='linked' and width==1366:
                        primary=page.locator('[class*="st-key-bento-hero-"] [data-testid="stBaseButton-primary"]').first
                        primary.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
                        interaction['keyboardFocus']=primary.evaluate('(e)=>({active:e===document.activeElement,outline:getComputedStyle(e).outline})')
                        assert interaction['keyboardFocus']['active'] and '3px' in interaction['keyboardFocus']['outline']
                        page.keyboard.press('Enter');_ready(page,'Registrar resultado')
                        interaction['enterOpensRegister']=True
                        button=page.locator('.st-key-nav_today button');button.focus();page.keyboard.press('Space');_ready(page,'Olá')
                        interaction['spaceOpensToday']=True
                        done=page.get_by_role('tab',name='Feito hoje (20)',exact=True);done.click()
                        assert 'Registrado às' in page.locator('[data-testid=stMain]').inner_text()
                        interaction['doneTabWithLocalTime']=True
                        page.get_by_role('tab',name='Para fazer',exact=True).click()
                        page.get_by_role('button',name='Iniciar pausa de 10 min',exact=True).click()
                        page.wait_for_function("/09:5[0-9]/.test(document.querySelector('.st-key-bento-pause')?.innerText||'')",timeout=8000)
                        page.get_by_role('button',name='Dispensar pausa',exact=True).click()
                        page.locator('.st-key-bento-pause').wait_for(state='hidden')
                        interaction['fragmentPauseAndDismiss']=True
                        # Zoom CSS de200% no navegador, sem declarar como zoom nativo.
                        page.locator('html').evaluate("e=>e.style.zoom='2'")
                        action=page.locator('[class*="st-key-bento-hero-"] button').first
                        action.scroll_into_view_if_needed()
                        interaction['zoomCSS200']={'visible':action.is_visible(),'documentWidth':page.evaluate('document.documentElement.scrollWidth'),'viewport':1366}
                        page.screenshot(path=str(output/'zoom-css-200.png'))
                    elif case=='linked':
                        title=page.locator('[class*="st-key-bento-hero-"] h3').first
                        title.evaluate("e=>e.textContent='Tema sintético com um nome muito extenso para verificar a quebra de linha e a continuidade das ações de registro no celular'")
                        interaction['longName390']=title.evaluate('(e)=>({width:e.clientWidth,scrollWidth:e.scrollWidth,documentWidth:document.documentElement.scrollWidth})')
                        assert interaction['longName390']['documentWidth']<=390
                        page.screenshot(path=str(output/'nome-longo-390.png'))
                    context.close()
                browser.close()
            assert service.store.events()==before,'A verificação visual gravou estudo indevidamente.'
    report={'synthetic':True,'cases':results,'interaction':interaction,'blocked_remote_requests':sorted(set(remote))}
    (output/'estados-e-acessibilidade.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'states':len(results),'interaction':interaction,'remoteRequests':len(remote)},ensure_ascii=False))


if __name__=='__main__':check(ROOT/'evidencias/bento/fase2')
