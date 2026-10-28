"""QA de Temas/Registro em cenário descartável, sem acesso à porta8501."""
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_ready,_screen,SIZES
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService


def check():
    from playwright.sync_api import sync_playwright
    output=ROOT/'evidencias/bento/fase3';output.mkdir(parents=True,exist_ok=True)
    results=[];remote=[];interaction={};url='http://127.0.0.1:8602/'
    with tempfile.TemporaryDirectory(prefix='osler-bento-fase3-check-') as temporary:
        folder=Path(temporary)/'scenario';seed_demo_data(folder,today_local())
        service=AdaptiveService(Repository(folder));before=len(service.store.events())
        with demo_server(folder,url,output),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            for width,height in SIZES:
                context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                def local_only(route):
                    if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                    else:remote.append(route.request.url);route.abort()
                context.route('**/*',local_only)
                page=context.new_page();page.goto(url);_ready(page,'Olá')
                _screen(page,'temas','Temas','Temas e desempenho',width)
                page.locator('.st-key-statistics_layout label').filter(has_text='Lista').click();_ready(page,'Temas e desempenho')
                grid=page.locator('.st-key-bento_topics_grid');grid.scroll_into_view_if_needed()
                cards=page.locator('[class*="st-key-bento-topic-"]')
                assert cards.count()==12
                page.screenshot(path=str(output/f'cards-{width}x{height}.png'))
                metrics=page.evaluate('''()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
                  cards:[...document.querySelectorAll('[class*="st-key-bento-topic-"]')].map(e=>({padding:getComputedStyle(e).padding,background:getComputedStyle(e).backgroundColor,width:e.clientWidth,scrollWidth:e.scrollWidth})),
                  buttons:[...document.querySelectorAll('.st-key-bento_topics_grid button')].filter(e=>e.checkVisibility()).map(e=>({text:e.innerText,height:e.getBoundingClientRect().height,width:e.getBoundingClientRect().width}))})''')
                assert metrics['documentWidth']<=width
                assert all(c['padding']=='24px' and c['scrollWidth']<=c['width'] for c in metrics['cards'])
                assert all(b['height']>=44 and b['width']>=44 for b in metrics['buttons'])
                results.append(metrics)
                if width in (1366,390):
                    title=cards.first.locator('h3')
                    title.evaluate("e=>e.textContent='Tema sintético com um nome muito extenso para verificar a quebra de linha e a continuidade das ações no celular'")
                    assert page.evaluate('document.documentElement.scrollWidth')<=width
                    cards.first.scroll_into_view_if_needed()
                    page.screenshot(path=str(output/f'nome-longo-{width}.png'))
                    action=cards.first.get_by_role('button',name='Registrar resultado',exact=True)
                    action.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
                    focus=action.evaluate('(e)=>({active:e===document.activeElement,outline:getComputedStyle(e).outline})')
                    assert focus['active'] and '3px' in focus['outline']
                    interaction[f'keyboard-{width}']=focus
                    page.keyboard.press('Enter');_ready(page,'Registrar resultado')
                    page.get_by_role('spinbutton',name='Quantas questões você fez?',exact=True).fill('10')
                    page.get_by_role('spinbutton',name='Quantas acertou?',exact=True).fill('11')
                    save=page.get_by_role('button',name='Salvar resultado e atualizar meu plano',exact=True)
                    save.click();_ready(page,'Registrar resultado')
                    error=page.get_by_text('Acertos não podem passar de 10.',exact=True);error.wait_for()
                    error.scroll_into_view_if_needed();page.screenshot(path=str(output/f'validacao-{width}.png'))
                    assert page.get_by_role('spinbutton',name='Quantas acertou?',exact=True).input_value()=='11'
                    count=len(service.store.events());assert count==before+(1 if width==390 else 0)
                    page.get_by_role('spinbutton',name='Quantas acertou?',exact=True).fill('8')
                    save.click();_ready(page,'Registrar resultado')
                    page.get_by_text('Registro concluído',exact=True).wait_for()
                    page.get_by_role('button',name='Próximo bloco',exact=True).scroll_into_view_if_needed()
                    page.screenshot(path=str(output/f'salvo-{width}.png'))
                    assert len(service.store.events())==count+1
                    page.get_by_role('button',name='Próximo bloco',exact=True).click();_ready(page,'Registrar resultado')
                    page.get_by_role('spinbutton',name='Quantas questões você fez?',exact=True).wait_for()
                    assert len(service.store.events())==count+1
                    interaction[f'save-and-next-{width}']=True
                    if width==1366:
                        page.locator('html').evaluate("e=>e.style.zoom='2'")
                        save=page.get_by_role('button',name='Salvar resultado e atualizar meu plano',exact=True)
                        save.scroll_into_view_if_needed();assert save.is_visible()
                        assert page.evaluate('document.documentElement.scrollWidth')<=1366
                        page.screenshot(path=str(output/'registro-zoom200.png'))
                        interaction['zoomCSS200']=True
                        page.locator('html').evaluate("e=>e.style.zoom='1'")
                    _screen(page,'temas','Temas','Temas e desempenho',width)
                    for tab in ['Erros abertos','Plano de corte','Minha meta']:
                        page.get_by_role('tab',name=tab,exact=True).click();_ready(page,'Temas e desempenho')
                        assert not page.get_by_test_id('stException').count()
                        page.screenshot(path=str(output/f'aba-{tab.split()[0].lower()}-{width}.png'))
                context.close()
            browser.close()
    report={'synthetic':True,'sizes':results,'interaction':interaction,'blocked_remote_requests':remote}
    (output/'temas-registro-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sizes':len(results),'interaction':interaction,'remoteRequests':len(remote)},ensure_ascii=False))


if __name__=='__main__':check()
