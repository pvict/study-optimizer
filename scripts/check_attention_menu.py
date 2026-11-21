"""Hoje preservado e atenção em página própria, com cenário temporário."""
import json,sys,tempfile
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_screen
from scripts.check_bento_planning import _wrapper,_ready
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local


def main():
 from playwright.sync_api import sync_playwright
 out=ROOT/'evidencias/atencao-menu';out.mkdir(parents=True,exist_ok=True)
 checks=[]
 with tempfile.TemporaryDirectory(prefix='osler-attention-') as folder:
  folder=Path(folder);data=folder/'scenario';seed_demo_data(data,today_local())
  with demo_server(data,'http://127.0.0.1:8602/',out,app_path=_wrapper(folder)),sync_playwright() as p:
   browser=p.chromium.launch(channel='msedge',headless=True)
   try:
    for width,height in [(1440,1000),(768,1024),(390,844)]:
     context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
     context.route('**/*',lambda r:r.continue_() if urlsplit(r.request.url).hostname in {'127.0.0.1',None} else r.abort())
     page=context.new_page();page.goto('http://127.0.0.1:8602/');_ready(page,'Olá')
     assert not page.get_by_label('Buscar nos temas de atenção',exact=True).count()
     assert not page.get_by_text('Sua carga e os próximos ajustes',exact=True).count()
     page.screenshot(path=str(out/f'hoje-{width}.png'))
     _screen(page,'atencao','Temas em atenção','Temas em atenção',width)
     assert page.get_by_label('Buscar nos temas de atenção',exact=True).count()==1
     assert page.get_by_test_id('stDataFrame').count()
     assert not page.get_by_test_id('stException').count()
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
     page.screenshot(path=str(out/f'atencao-{width}.png'))
     checks.append({'width':width,'today_clear':True,'attention_page':True,'populated_table':True,'no_page_overflow':True})
     context.close()
   finally:browser.close()
 result={'synthetic':True,'checks':checks,'temporary_data_removed':True}
 (out/'resultado.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
