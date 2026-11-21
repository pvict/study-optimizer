"""Cancela/confirma gravações reais em uma base sintética descartável."""
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
    output=ROOT/'evidencias/confirmacoes';output.mkdir(parents=True,exist_ok=True)
    results=[]
    with tempfile.TemporaryDirectory(prefix='osler-confirmation-') as folder:
        folder=Path(folder);data=folder/'scenario';seed_demo_data(data,today_local())
        service=AdaptiveService(Repository(data))
        with demo_server(data,'http://127.0.0.1:8602/',output,app_path=_wrapper(folder)),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                for width,height in [(1440,900),(768,1024),(390,844)]:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    context.route('**/*',lambda route:route.continue_() if urlsplit(route.request.url).hostname in {'127.0.0.1',None} else route.abort())
                    page=context.new_page();page.goto('http://127.0.0.1:8602/');_ready(page,'Olá')
                    _screen(page,'registrar','Registrar','Registrar resultado',width);_ready(page,'Registrar resultado')
                    page.get_by_label('Quantas questões você fez?',exact=True).fill('20')
                    page.get_by_label('Quantas acertou?',exact=True).fill('15')
                    before=len(service.store.events())
                    button=page.get_by_role('button',name='Salvar resultado e atualizar meu plano',exact=True)
                    button.click();dialog=page.get_by_role('dialog');dialog.wait_for()
                    assert len(service.store.events())==before
                    for _ in range(8):
                        page.keyboard.press('Tab')
                        assert page.evaluate('!!document.activeElement.closest("[role=dialog]")')
                    page.keyboard.press('Escape');dialog.wait_for(state='hidden')
                    assert len(service.store.events())==before
                    button.click();dialog.wait_for();dialog.get_by_role('button',name='Cancelar',exact=True).click();dialog.wait_for(state='hidden')
                    assert len(service.store.events())==before
                    button.click();dialog.wait_for()
                    bounds=dialog.bounding_box();assert bounds['x']>=0 and bounds['x']+bounds['width']<=width+1
                    page.screenshot(path=str(output/f'dialogo-{width}.png'))
                    dialog.get_by_role('button',name='Salvar resultado',exact=True).click()
                    page.get_by_role('heading',name='Registro concluído',exact=True).wait_for(timeout=30000)
                    _ready(page,'Registrar resultado')
                    page.get_by_test_id('stToast').filter(has_text='Resultado registrado.').wait_for()
                    assert len(service.store.events())==before+1
                    page.screenshot(path=str(output/f'toast-{width}.png'))
                    page.reload();_ready(page,'Olá')
                    assert len(service.store.events())==before+1
                    results.append({'width':width,'cancel_preserved_data':True,'escape_preserved_data':True,'focus_trapped':True,'saved_once':True,'toast_after_save':True})
                    context.close()
            finally:browser.close()
    (output/'verificacao.json').write_text(json.dumps({'synthetic':True,'checks':results,'temporary_data_removed':True},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sizes':len(results),'cancel':True,'escape':True,'once':True,'toast':True,'temporary_data_removed':True}))


if __name__=='__main__':main()
