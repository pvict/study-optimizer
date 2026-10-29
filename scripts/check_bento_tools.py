"""Capturas Bento fase5: cenário sintético descartável, sem banco ativo ou rede externa."""
import argparse
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from scripts import check_bento_planning as qa
from scripts.capture_bento import SIZES, SCREENS, demo_server, _screen, font_probe
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local

ROOT=Path(__file__).resolve().parents[1]
TARGETS=[s for s in SCREENS if s[0] in {'flashcards','arquivos','ajustes'}]


def seed_cards(data):
    """Criações reais do modelo, apenas no cenário descartável identificado."""
    from osler.storage import Repository
    from osler.adaptive_service import AdaptiveService
    from osler.error_cards_service import ErrorCardsService
    from osler.study_models import StudyEntry
    repo=Repository(data);service=AdaptiveService(repo);day=today_local().isoformat()
    topics,_=service.catalog(day)
    for i,n in enumerate((70,80,45)):
        service.save_entry(StudyEntry(topics[-i-1]['path'],day,10,7,cards_created=n,
                           source='Criação sintética para QA da fase5'),f'qa-fase5-{i}')
    cards=ErrorCardsService(repo);cards.configure(200,{},cards.token())
    view=cards.overview();item=view['items'][0]
    cards.record(item['topic_id'],day,10,2,None,'qa-primeira-passagem',view['token'])


def capture(label,baseline=None,audit=False,targets=None):
    from playwright.sync_api import sync_playwright
    output=ROOT/'evidencias/bento/fase5';output.mkdir(parents=True,exist_ok=True)
    records=[];remote=[];fonts=[];interactions={};url='http://127.0.0.1:8602/'
    qa.MODULES=('practical_reduction_ui','error_cards_ui','guide_settings_ui','bento_day_ui','adaptive_ui','ui')
    with tempfile.TemporaryDirectory(prefix='osler-bento-fase5-') as temp:
        temp=Path(temp);data=temp/'scenario';seed_demo_data(data,today_local());seed_cards(data)
        app=qa._wrapper(temp,baseline)
        with demo_server(data,url,output,app_path=app),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                for width,height in SIZES:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    def local_only(route):
                        if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                        else:remote.append(route.request.url);route.abort()
                    context.route('**/*',local_only)
                    page=context.new_page();page.goto(url);qa._ready(page,'Olá')
                    fonts.append({'size':[width,height],**font_probe(page)})
                    for name,visible,heading in TARGETS:
                        if targets and name not in targets:continue
                        _screen(page,name,visible,heading,width)
                        page.locator('[data-testid="stMain"]').evaluate('e=>e.scrollTop=0')
                        qa._snapshot(page,output,label,name,[width,height],records)
                        if name=='flashcards':
                            page.locator('.st-key-ec_mode label').filter(has_text='Reduzir outras revisões').click()
                            qa._ready(page,'Sua lista para diminuir as revisões')
                            qa._snapshot(page,output,label,'flashcards-reducao',[width,height],records)
                        if name=='ajustes':
                            for section in ['Minhas provas','Instituições e incidências']:
                                page.locator('.st-key-study_settings_section label').filter(has_text=section).click()
                                qa._ready(page,heading)
                                qa._snapshot(page,output,label,'ajustes-'+('provas' if section=='Minhas provas' else 'incidencias'),[width,height],records)
                        if label=='depois' and width in (1366,390):
                            page.locator('[data-testid="stMain"]').evaluate('e=>e.scrollTop=0')
                            page.evaluate('document.activeElement?.blur()')
                            for _ in range(40):
                                page.keyboard.press('Tab')
                                focus=page.evaluate('''() => {let e=document.activeElement;return {tag:e?.tagName,outline:getComputedStyle(e).outlineWidth,text:(e?.innerText||e?.getAttribute('aria-label')||'').slice(0,100)}}''')
                                if focus['tag'] in ('BUTTON','INPUT') and focus['outline']!='0px':break
                            interactions[f'{name}-keyboard-{width}']=focus
                            page.evaluate('document.documentElement.style.zoom="2"')
                            qa._snapshot(page,output,label,name+'-zoom200',[width,height],records)
                            page.evaluate('document.documentElement.style.zoom=""')
                    if audit and width in (1366,390):
                        for name,visible,heading in SCREENS:
                            if name in {'flashcards','arquivos','ajustes'}:continue
                            _screen(page,name,visible,heading,width)
                            page.locator('[data-testid="stMain"]').evaluate('e=>e.scrollTop=0')
                            qa._snapshot(page,output,label,'auditoria-'+name,[width,height],records)
                    context.close()
            finally:browser.close()
        removed=str(temp)
    report={'synthetic':True,'baseline':baseline,'screens':records,'fontEvidence':fonts,
            'interaction':interactions,'blockedRemoteRequests':remote,
            'temporaryDirectoryRemoved':not Path(removed).exists(),
            'zoomMethod':'CSS zoom=2; não equivale a zoom nativo do navegador'}
    manifest=output/(label+'-manifest.json')
    if targets and manifest.exists():
        previous=json.loads(manifest.read_text(encoding='utf-8'))
        replacements={r['image']:r for r in records}
        previous_names={r['image'] for r in previous['screens']}
        records=[replacements.get(r['image'],r) for r in previous['screens']]+[r for r in records if r['image'] not in previous_names]
        report['screens']=records
        report['interaction']={**previous['interaction'],**interactions}
        report['blockedRemoteRequests']=previous['blockedRemoteRequests']+remote
    report['checks']={
        'noDocumentOverflow':all(r['documentWidth']<=r['viewport'] for r in records),
        'noTextOverflow':all(not r['overflowing'] for r in records),
        'buttons44px':all(b['rect']['width']>=43.9 and b['rect']['height']>=43.9 for r in records for b in r['buttons']),
        'noRemoteRequests':not report['blockedRemoteRequests']}
    manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    qa.contrast_report(output/'contraste-texto.json')
    print(json.dumps({'captures':len(records),'checks':report['checks'],'temporaryDirectoryRemoved':report['temporaryDirectoryRemoved']}))
    return report


def capture_states():
    """Estados adicionais em dois tamanhos; sem replicar bancos ou ambientes."""
    from playwright.sync_api import sync_playwright
    from osler.storage import Repository
    from osler.error_cards_service import ErrorCardsService
    from osler.service import import_bytes
    from scripts.seed_demo_data import _pdf
    from datetime import timedelta
    output=ROOT/'evidencias/bento/fase5';output.mkdir(parents=True,exist_ok=True)
    records=[];remote=[];interactions={};url='http://127.0.0.1:8602/'
    with tempfile.TemporaryDirectory(prefix='osler-bento-fase5-estados-') as temporary:
        temp=Path(temporary);app=qa._wrapper(temp)
        with sync_playwright() as p:
            for case in ('vazio','nomes-longos'):
                data=temp/case
                if case=='vazio':
                    data.mkdir();(data/'SYNTHETIC-DEMO.json').write_text('{"synthetic":true}',encoding='utf-8')
                else:
                    seed_demo_data(data,today_local());seed_cards(data)
                    repo=Repository(data)
                    name='Tema sintético com nome extenso para conferir a leitura e a continuidade das ações de estudo em uma tela pequena'
                    tree=('<div class="TreeNode-test" style="margin-left:0px"><span class="Label-test">Clínica Médica</span>'
                          '<svg class="lucide-chevron-down"></svg><p class="StatInfo-test">5</p></div>'
                          '<div class="TreeNode-test" style="margin-left:20px"><span class="Label-test">'+name+
                          '</span><p class="StatInfo-test">5</p></div>').encode('utf-8')
                    cards=ErrorCardsService(repo)
                    cards.import_html(tree,'SINTETICO-arvore-nome-longo.html',today_local().isoformat(),'pending',cards.token())
                    import_bytes(repo,_pdf('flashcards',today_local()-timedelta(days=1)),
                                 'SINTETICO-relatorio-de-flashcards-com-nome-extenso-para-conferir-acesso-ao-nome-completo-e-rastreabilidade.pdf')
                with demo_server(data,url,output,app_path=app):
                    browser=p.chromium.launch(channel='msedge',headless=True)
                    try:
                        for width,height in ((1366,768),(390,844)):
                            context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce',has_touch=width==390)
                            def local_only(route):
                                if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                                else:remote.append(route.request.url);route.abort()
                            context.route('**/*',local_only)
                            page=context.new_page();page.goto(url);qa._ready(page,'Olá')
                            for name,visible,heading in TARGETS:
                                _screen(page,name,visible,heading,width)
                                qa._snapshot(page,output,'depois',case+'-'+name,[width,height],records)
                                if name=='flashcards' and case=='nomes-longos':
                                    page.get_by_role('tab',name='Temas',exact=True).click()
                                    page.locator('.st-key-ec_search input').fill('Tema sintético com nome extenso')
                                    page.locator('.st-key-ec_search input').press('Enter');qa._ready(page,heading)
                                    qa._snapshot(page,output,'depois','deck-nome-longo',[width,height],records)
                                    action=page.get_by_role('button',name='Estudar este tema de cards',exact=True)
                                    action.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
                                    interactions[f'cards-keyboard-{width}']=action.evaluate('(e)=>({focused:e===document.activeElement,outline:getComputedStyle(e).outline})')
                                    page.keyboard.press('Space');qa._ready(page,heading)
                                    page.locator('.st-key-bento-error-cards-record').evaluate('e=>e.scrollIntoView({block:"start"})')
                                    qa._snapshot(page,output,'depois','registro-cards',[width,height],records)
                                if name=='arquivos':
                                    action=page.get_by_role('button',name='Backup e restauração',exact=True)
                                    action.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
                                    interactions[f'backup-keyboard-{case}-{width}']=action.evaluate('(e)=>({focused:e===document.activeElement,outline:getComputedStyle(e).outline})')
                                    page.keyboard.press('Enter')
                                    qa._ready(page,'Backup e restauração')
                                    qa._snapshot(page,output,'depois',case+'-backup',[width,height],records)
                                if name=='ajustes':
                                    slider=page.get_by_role('slider').first
                                    before=slider.evaluate('e=>e.value ?? e.getAttribute("aria-valuenow")');slider.focus();page.keyboard.press('ArrowRight')
                                    interactions[f'slider-keyboard-{case}-{width}']={'before':before,'after':slider.evaluate('e=>e.value ?? e.getAttribute("aria-valuenow")')}
                                    if width==390:
                                        track=page.locator('.st-key-settings_new_share').bounding_box()
                                        thumb=slider.bounding_box()
                                        page.touchscreen.tap(track['x']+track['width']*.7,thumb['y']+thumb['height']/2)
                                        interactions[f'slider-touch-{case}']={'value':slider.evaluate('e=>e.value ?? e.getAttribute("aria-valuenow")'),'method':'Chromium touchscreen.tap, viewport390; sem salvar'}
                            context.close()
                    finally:browser.close()
        removed=str(temp)
    report={'synthetic':True,'screens':records,'interaction':interactions,'blockedRemoteRequests':remote,'temporaryDirectoryRemoved':not Path(removed).exists(),
            'checks':{'noDocumentOverflow':all(r['documentWidth']<=r['viewport'] for r in records),
                      'noTextOverflow':all(not r['overflowing'] for r in records),
                      'buttons44px':all(b['rect']['width']>=43.9 and b['rect']['height']>=43.9 for r in records for b in r['buttons'])}}
    (output/'estados-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'captures':len(records),'checks':report['checks'],'temporaryDirectoryRemoved':report['temporaryDirectoryRemoved']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',default='depois',choices=['antes','depois'])
    parser.add_argument('--baseline');parser.add_argument('--audit',action='store_true')
    parser.add_argument('--target',action='append',choices=['flashcards','arquivos','ajustes'])
    parser.add_argument('--states-only',action='store_true')
    args=parser.parse_args()
    if args.states_only:capture_states()
    else:capture(args.label,args.baseline,args.audit,args.target)
