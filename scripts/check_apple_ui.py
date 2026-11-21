"""QA de apresentação em dados sintéticos; não usa a base ativa."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_screen,SIZES,SCREENS
from scripts.check_bento_planning import _wrapper,_ready,_metrics,contrast_report
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local


def main():
    from playwright.sync_api import sync_playwright
    parser=argparse.ArgumentParser();parser.add_argument('--baseline');args=parser.parse_args()
    label='antes' if args.baseline else 'depois'
    output=ROOT/'evidencias/apple-ui'/label;output.mkdir(parents=True,exist_ok=True)
    records=[]
    with tempfile.TemporaryDirectory(prefix='osler-apple-ui-') as folder:
        folder=Path(folder);data=folder/'scenario';seed_demo_data(data,today_local())
        with demo_server(data,'http://127.0.0.1:8602/',output,app_path=_wrapper(folder,args.baseline)),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                sizes=[SIZES[0],SIZES[-1]] if args.baseline else SIZES
                screens=[SCREENS[0],SCREENS[3]] if args.baseline else SCREENS
                for width,height in sizes:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    context.route('**/*',lambda route:route.continue_() if urlsplit(route.request.url).hostname in {'127.0.0.1',None} else route.abort())
                    page=context.new_page();page.goto('http://127.0.0.1:8602/');_ready(page,'Olá')
                    for name,label_text,heading in screens:
                        _screen(page,name,label_text,heading,width);_ready(page,heading)
                        metrics=_metrics(page)
                        if metrics['exceptions'] or metrics['documentWidth']>width+2 or metrics['mainWidth']>metrics['mainClientWidth']+2:
                            raise RuntimeError(f'{name}/{width}: {metrics["exceptions"] or "overflow"}')
                        if not args.baseline:
                            close=page.get_by_role('button',name='Collapse sidebar',exact=True)
                            if close.is_visible():close.click()
                            page.wait_for_timeout(150)
                            title=page.get_by_role('heading',name=heading,exact=True).bounding_box()
                            if title['y']<56:raise RuntimeError(f'Título sob cabeçalho em {name}/{width}: {title}')
                            if width>=900:
                                page.get_by_role('button',name='Expand sidebar',exact=True).click()
                                page.wait_for_timeout(400)
                        if width in (1440,390):page.screenshot(path=str(output/f'{name}-{width}.png'))
                        records.append({'screen':name,'width':width,'overflow':metrics['overflowing'],'exceptions':metrics['exceptions']})
                    # Collapse sidebar at desktop as well: top controls must not cover title.
                    _screen(page,'hoje','Hoje','Olá',width);_ready(page,'Olá')
                    close=page.get_by_role('button',name='Collapse sidebar',exact=True)
                    if close.is_visible():close.click()
                    page.wait_for_timeout(200)
                    title=page.get_by_role('heading',name='Olá',exact=True).bounding_box()
                    if title['y']<48:raise RuntimeError('Título coberto pela barra superior')
                    page.keyboard.press('Tab')
                    focus=page.evaluate('''() => {const s=getComputedStyle(document.activeElement);return {tag:document.activeElement.tagName,outline:s.outlineStyle}}''')
                    records.append({'screen':'collapsed-header','width':width,'heading_y':title['y'],'focus':focus})
                    if not args.baseline and width==1440:
                        page.emulate_media(contrast='more',reduced_motion='reduce')
                        page.screenshot(path=str(output/'alto-contraste.png'))
                    context.close()
            finally:browser.close()
    report=contrast_report(output/'contraste.json')
    if not args.baseline and not all(r['AA_normal_text'] for r in report['pairs']):raise RuntimeError('Contraste insuficiente')
    (output/'verificacao.json').write_text(json.dumps({'synthetic':True,'records':records,'temporary_data_removed':True},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(records),'exceptions':0,'document_overflow':0,'temporary_data_removed':True}))


if __name__=='__main__':main()
