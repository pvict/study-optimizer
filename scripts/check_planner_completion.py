"""Reproduz cabeçalho/menu e exercita dispensa, somente cenário sintético8602."""
import argparse
from pathlib import Path
import sys,tempfile,json
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_ready
from scripts.seed_demo_data import seed_demo_data
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from osler.planner_service import today_local


def check(label):
    from playwright.sync_api import sync_playwright
    output=ROOT/'evidencias/planner-complementos';output.mkdir(parents=True,exist_ok=True)
    results=[];blocked=[];day=today_local().isoformat();url='http://127.0.0.1:8602/'
    with tempfile.TemporaryDirectory(prefix='osler-planner-completion-') as temporary:
        root=Path(temporary);folder=root/'scenario';seed_demo_data(folder,today_local())
        service=AdaptiveService(Repository(folder))
        practiced={tuple(s['entry']['path']) for s in service.store.active(day)}
        topic=next(t for t in service.catalog(day)[0] if tuple(t['path']) not in practiced)
        service.agenda.append({'kind':'reschedule.apply','created_day':day,'cutoff':max(s['id'] for s in service.store.active(day)),
            'mode':'balanced','start':day,'days':7,
            'selected':[topic['topic_id']],'rows':[{'topic_id':topic['topic_id'],'path':topic['path'],
            'date':day,'original_due':day,'questions':20,'new_topic':False}]},service.agenda.token())
        service.save_entry(StudyEntry(topic['path'],day,10,8),session_id='planner-ui-demo')
        wrapper=root/'app.py'
        wrapper.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom osler.adaptive_service import AdaptiveService\noriginal=AdaptiveService.catalog\ndef catalog(self,*args,**kw):\n topics,sources=original(self,*args,**kw)\n for t in topics:\n  if t["topic_id"]=='+repr(topic['topic_id'])+':t["planner_snapshot"]={"observed_date":'+repr(day)+',"unique_questions":0,"available_questions":10,"confident_accuracy_pct":None,"pending_reviews":0,"last_contact":None}\n return topics,sources\nAdaptiveService.catalog=catalog\nfrom osler.ui import run\nrun()\n',encoding='utf-8')
        before=len(service.store.events())
        with demo_server(folder,url,output,wrapper),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            for width,height in [(1366,768),(1912,1045),(390,844)]:
                context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                def local_only(route):
                    if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                    else:blocked.append(route.request.url);route.abort()
                context.route('**/*',local_only)
                page=context.new_page();page.goto(url);_ready(page,'Olá')
                for collapsed in (False,True):
                    name='Collapse sidebar' if collapsed else 'Expand sidebar'
                    actual=page.get_by_test_id('stSidebar').get_attribute('data-collapsed')=='true'
                    if actual!=collapsed:
                        if collapsed:page.get_by_test_id('stSidebar').hover()
                        page.get_by_role('button',name=name,exact=True).click()
                    page.wait_for_function("collapsed=>document.querySelector('[data-testid=stSidebar]')?.getAttribute('data-collapsed')===String(collapsed)",arg=collapsed)
                    if collapsed:page.wait_for_function("document.querySelector('[data-testid=stSidebar]').getBoundingClientRect().right<=1")
                    page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTo(0,0)')
                    data=page.evaluate('''()=>({title:document.querySelector('h1').getBoundingClientRect().toJSON(),
                      header:document.querySelector('[data-testid=stHeader]').getBoundingClientRect().toJSON(),
                      sidebarCollapsed:document.querySelector('[data-testid=stSidebar]').getAttribute('data-collapsed'),
                      width:innerWidth,documentWidth:document.documentElement.scrollWidth,
                      sidebarButtons:[...document.querySelectorAll('.st-key-bento_sidebar button')].map(e=>({text:e.innerText,align:getComputedStyle(e).textAlign,justify:getComputedStyle(e).justifyContent,child:e.firstElementChild?.outerHTML.slice(0,900)}))})''')
                    results.append({'collapsed':collapsed,**data})
                    if label=='depois':
                        assert data['title']['top']>=data['header']['bottom'] and data['documentWidth']<=width
                        assert all(b['align']=='left' for b in data['sidebarButtons'])
                    page.screenshot(path=str(output/(f'{label}-{width}-'+('fechada' if collapsed else 'aberta')+'.png')))
                if label=='depois':
                    close=page.get_by_role('button',name='Encerrar tema hoje',exact=True)
                    close.scroll_into_view_if_needed();page.screenshot(path=str(output/f'opcao-{width}.png'))
                    close.focus();page.keyboard.press('Enter')
                    page.get_by_role('button',name='Desfazer dispensa',exact=True).wait_for()
                    assert len(service.store.events())==before
                    page.get_by_role('button',name='Desfazer dispensa',exact=True).scroll_into_view_if_needed()
                    page.screenshot(path=str(output/f'encerrado-{width}.png'))
                    page.get_by_role('button',name='Desfazer dispensa',exact=True).click()
                    page.get_by_role('button',name='Encerrar tema hoje',exact=True).wait_for()
                context.close()
            browser.close()
    (output/f'{label}.json').write_text(json.dumps({'results':results,'remote':blocked},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'screens':len(results),'remote':len(blocked)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label',choices=['antes','depois']);check(parser.parse_args().label)
