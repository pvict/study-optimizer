"""Geometria do registro em base sintética, sem tocar nos dados ativos."""
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


def main():
    from playwright.sync_api import sync_playwright
    out=ROOT/'evidencias/alinhamento-registro';out.mkdir(parents=True,exist_ok=True)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='osler-layout-') as folder:
        folder=Path(folder);data=folder/'scenario';seed_demo_data(data,today_local())
        with demo_server(data,'http://127.0.0.1:8602/',out,app_path=_wrapper(folder)),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                for width,height in [(1440,1000),(768,1024),(390,844)]:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    context.route('**/*',lambda r:r.continue_() if urlsplit(r.request.url).hostname in {'127.0.0.1',None} else r.abort())
                    page=context.new_page();page.goto('http://127.0.0.1:8602/');_ready(page,'Olá')
                    _screen(page,'registrar','Registrar','Registrar resultado',width)
                    page.wait_for_timeout(400)
                    for state in (['expanded','collapsed'] if width==1440 else ['collapsed']):
                        if width==1440 and state=='collapsed':
                            page.get_by_role('button',name='Collapse sidebar',exact=True).click()
                            page.wait_for_timeout(250)
                        title=page.get_by_role('heading',name='Registrar resultado',exact=True).bounding_box()
                        card=page.locator('.st-key-bento-record').bounding_box()
                        gap=card['y']-title['y']-title['height']
                        assert abs(title['x']-card['x'])<=1,(width,state,title,card)
                        assert 16<=gap<=40,(width,state,gap)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        groups=page.locator('[data-testid="stButtonGroup"]')
                        for group in groups.all():
                            boxes=[b.bounding_box() for b in group.locator('button').all() if b.is_visible()]
                            assert len(boxes)>=2
                            for a,b in zip(boxes,boxes[1:]):
                                separation=b['x']-a['x']-a['width'] if abs(a['y']-b['y'])<2 else b['y']-a['y']-a['height']
                                assert separation>=7,(width,separation)
                        page.screenshot(path=str(out/f'registro-{width}-{state}.png'))
                        checks.append({'width':width,'sidebar':state,'aligned':True,'title_card_gap':round(gap,1),'no_page_overflow':True})
                    context.close()
            finally:browser.close()
    result={'synthetic':True,'checks':checks,'temporary_data_removed':True}
    (out/'resultado.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
