"""Captura cobertura/temas específicos com dados sintéticos descartáveis8602."""
from pathlib import Path
import json,sys,tempfile
from shutil import copyfile
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.seed_demo_data import seed_demo_data
from scripts.capture_bento import demo_server,_ready,_screen
from osler.planner_service import today_local
from osler.models import stable_topic_id


def check():
    from playwright.sync_api import sync_playwright
    output=ROOT/'evidencias/cobertura';output.mkdir(parents=True,exist_ok=True)
    day=today_local().isoformat();results=[];remote=[];url='http://127.0.0.1:8602/'
    with tempfile.TemporaryDirectory(prefix='osler-coverage-ui-') as temporary:
        root=Path(temporary);folder=root/'scenario';seed_demo_data(folder,today_local())
        (root/'static/fonts').mkdir(parents=True)
        copyfile(ROOT/'static/fonts/InterVariable.woff2',root/'static/fonts/InterVariable.woff2')
        wrapper=root/'app.py'
        wrapper.write_text('''import sys
sys.path.insert(0,ROOT)
from osler.adaptive_service import AdaptiveService
from osler.models import stable_topic_id
from osler.topic_catalog import mark_practice_units,is_practice_topic
if not hasattr(AdaptiveService,'_coverage_original_catalog'):
    AdaptiveService._coverage_original_catalog=AdaptiveService.catalog
original=AdaptiveService._coverage_original_catalog
def catalog(self,as_of,include_parents=False):
    topics,sources=original(self,as_of,include_parents=True)
    path=['Preventiva & Social','Medicina Legal','Saúde do Trabalhador (sintético)']
    p={'topic_id':stable_topic_id(path),'path':path,'total':486,'answered_pdf':46,
       'pdf_accuracy':{'value':96,'operator':'=','raw':'96%'},'report_date':DAY,'studied_cards':0,'is_leaf':False}
    child={**p,'path':path+['Segurança do Trabalhador (sintético)'],'topic_id':stable_topic_id(path+['Segurança do Trabalhador (sintético)']),
           'total':1,'answered_pdf':0,'pdf_accuracy':{'value':None,'operator':None,'raw':'—'},'is_leaf':True}
    topics=mark_practice_units([*topics,p,child])
    return [t for t in topics if include_parents or is_practice_topic(t)],sources
AdaptiveService.catalog=catalog
from osler.ui import run
run()
'''.replace('ROOT',repr(str(ROOT))).replace('DAY',repr(day)),encoding='utf-8')
        with demo_server(folder,url,output,wrapper),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            for width,height in [(1366,768),(390,844)]:
                context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                def local_only(route):
                    if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                    else:remote.append(route.request.url);route.abort()
                context.route('**/*',local_only)
                page=context.new_page();page.goto(url);_ready(page,'Olá')
                _screen(page,'temas','Temas','Temas e desempenho',width)
                search=page.get_by_role('textbox',name='Buscar tema',exact=True)
                search.fill('Trabalhador (sintético)');search.press('Enter');_ready(page,'Temas e desempenho')
                try:page.get_by_text('2 temas nos filtros.',exact=False).wait_for(timeout=10000)
                except Exception:
                    print(page.get_by_test_id('stMain').inner_text()[-3500:])
                    page.screenshot(path=str(output/'qa-falha.png'))
                    raise
                page.get_by_text('Próximo contato com data:',exact=False).wait_for()
                assert not page.get_by_test_id('stException').count()
                page.get_by_text('Próximo contato com data:',exact=False).scroll_into_view_if_needed()
                page.screenshot(path=str(output/f'temas-{width}.png'))
                page.locator('.st-key-statistics_layout label').filter(has_text='Lista').click();_ready(page,'Temas e desempenho')
                page.locator('.st-key-bento_topics_grid').wait_for()
                buttons=page.locator('.st-key-bento_topics_grid').get_by_role('button',name='Registrar resultado',exact=True)
                buttons.nth(1).wait_for()
                assert buttons.count()==2
                parent_id=stable_topic_id(['Preventiva & Social','Medicina Legal','Saúde do Trabalhador (sintético)'])
                page.locator('.st-key-list_record_'+parent_id).get_by_role('button').click();_ready(page,'Registrar resultado')
                page.get_by_text('Tema completo, incluindo subtemas.',exact=False).wait_for()
                page.screenshot(path=str(output/f'registro-{width}.png'))
                dimensions=page.evaluate('({width:innerWidth,documentWidth:document.documentElement.scrollWidth})')
                assert dimensions['documentWidth']<=width
                results.append(dimensions);context.close()
            browser.close()
    (output/'qa-sintetico.json').write_text(json.dumps({'results':results,'remote':remote},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sizes':len(results),'remote':len(remote)}))


if __name__=='__main__':check()
