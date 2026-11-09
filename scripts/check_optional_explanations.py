"""Confere apresentação e gravação somente em base sintética descartável."""
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_screen
from scripts.check_bento_planning import _wrapper,_ready
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService


def main():
    from playwright.sync_api import sync_playwright
    out=ROOT/'evidencias/explicacoes-opcionais';out.mkdir(parents=True,exist_ok=True)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='osler-help-') as folder:
        folder=Path(folder);data=folder/'scenario';seed_demo_data(data,today_local())
        service=AdaptiveService(Repository(data))
        with demo_server(data,'http://127.0.0.1:8602/',out,app_path=_wrapper(folder)),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                for width,height in [(1440,1000),(768,1024),(390,844)]:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    context.route('**/*',lambda r:r.continue_() if urlsplit(r.request.url).hostname in {'127.0.0.1',None} else r.abort())
                    page=context.new_page();page.goto('http://127.0.0.1:8602/');_ready(page,'Olá')
                    before=len(service.store.events())
                    _screen(page,'atencao','Temas em atenção','Temas em atenção',width)
                    explanation=page.get_by_text('Sugestões de estudo com os dados locais. A ordem segue a política atual do plano; não é previsão de aprovação.',exact=True)
                    assert not explanation.count()
                    page.screenshot(path=str(out/f'atencao-{width}.png'))
                    expand=page.get_by_role('button',name='Expand sidebar',exact=True)
                    if expand.is_visible():expand.click()
                    page.get_by_text('Mostrar explicações',exact=True).click();_ready(page,'Temas em atenção')
                    assert explanation.is_visible()
                    page.get_by_label('Mostrar explicações',exact=True).focus();page.keyboard.press('Space');_ready(page,'Temas em atenção')
                    assert not explanation.count() and len(service.store.events())==before
                    _screen(page,'registrar','Registrar','Registrar resultado',width)
                    page.get_by_label('Quantas questões você fez?',exact=True).fill('27')
                    page.get_by_label('Quantas acertou?',exact=True).fill('19')
                    page.get_by_label('Desses acertos, quantos foram com convicção?',exact=True).fill('11')
                    page.get_by_role('button',name='Salvar resultado e atualizar meu plano',exact=True).click()
                    page.get_by_role('dialog').get_by_role('button',name='Salvar resultado',exact=True).click()
                    page.get_by_role('heading',name='Registro concluído',exact=True).wait_for(timeout=30000)
                    _ready(page,'Registrar resultado')
                    details=page.locator('details').filter(has=page.get_by_text('Detalhes do resultado e da revisão',exact=True))
                    assert details.count()==1 and details.get_attribute('open') is None
                    assert page.get_by_text('70,4%',exact=True).is_visible()
                    assert page.get_by_text('40,7%',exact=True).is_visible()
                    assert len(service.store.events())==before+1
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    page.screenshot(path=str(out/f'resultado-{width}.png'))
                    details.locator('summary').focus();page.keyboard.press('Enter')
                    assert details.get_attribute('open') is not None
                    page.screenshot(path=str(out/f'detalhes-{width}.png'))
                    checks.append({'width':width,'help_opt_in':True,'toggle_no_writes':True,
                                   'saved_once':True,'details_collapsed':True,'keyboard_disclosure':True,'no_page_overflow':True})
                    context.close()
            finally:browser.close()
    result={'synthetic':True,'checks':checks,'temporary_data_removed':True}
    (out/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
