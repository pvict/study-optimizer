"""Capturas do app com cenário sintético, servidor próprio e porta separada.

Não conecta na porta8501. Fecha apenas o processo de teste criado aqui.
Exemplo: python scripts/capture_bento.py --data-dir <demo> --output evidencias/bento/fase1 --label antes
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
SIZES=[(1440,900),(1366,768),(768,1024),(390,844)]
SCREENS=[('hoje','Hoje','Olá'),('calendario','Calendário','Calendário de estudos'),
         ('evolucao','Evolução','Sua evolução'),('temas','Temas','Temas e desempenho'),
         ('registrar','Registrar','Registrar resultado'),('simulados','Simulados','Seus simulados'),
         ('ajustes','Ajustes','Ajustes do plano'),('flashcards',None,'Seus cards de erros'),
         ('arquivos',None,'Arquivos e ferramentas')]


def validate_url(url):
    parsed=urlsplit(url)
    if (parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.port!=8602
            or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment):
        raise ValueError('Use somente http://127.0.0.1:8602/ para o servidor sintético.')
    return url


@contextmanager
def demo_server(data_dir,url,output,app_path=ROOT/'app.py'):
    validate_url(url);folder=Path(data_dir).resolve()
    if not folder.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not (folder/'SYNTHETIC-DEMO.json').is_file():
        raise ValueError('Informe o cenário temporário criado por seed_demo_data.py.')
    if json.loads((folder/'SYNTHETIC-DEMO.json').read_text(encoding='utf-8')).get('synthetic') is not True:
        raise ValueError('O cenário não está identificado como sintético.')
    with socket.socket() as probe:probe.bind(('127.0.0.1',8602))
    output.mkdir(parents=True,exist_ok=True)
    with (output/'servidor.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(app_path),
            '--server.address','127.0.0.1','--server.port','8602','--browser.gatherUsageStats','false'],
            cwd=ROOT,env={**os.environ,'OSLER_DATA_DIR':str(folder)},stdout=log,stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            deadline=time.monotonic()+40
            while True:
                if process.poll() is not None:raise RuntimeError('Servidor de teste encerrou; confira servidor.log.')
                try:
                    with urlopen(url+'_stcore/health',timeout=1) as response:
                        if response.status==200:break
                except OSError:
                    if time.monotonic()>deadline:raise TimeoutError('Servidor sintético não iniciou.')
                    time.sleep(.2)
            yield
        finally:
            if process.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
                else:process.terminate()
                process.wait(timeout=15)


def _ready(page,heading):
    page.get_by_role('heading',name=heading,exact=True).wait_for(timeout=60000)
    page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'",timeout=60000)
    # st.html é montado de forma assíncrona mesmo após o script terminar.
    page.wait_for_function("!document.querySelector('[data-testid=stSkeleton]')",timeout=60000)
    page.evaluate('document.fonts.ready')


def _screen(page,name,label,heading,width):
    expand=page.get_by_role('button',name='Expand sidebar',exact=True)
    if expand.is_visible():expand.click()
    routes={'hoje':'today','atencao':'attention','calendario':'calendar','evolucao':'evolution','temas':'topics','registrar':'register',
            'simulados':'mocks','ajustes':'settings','flashcards':'flashcards','arquivos':'files'}
    page.locator('.st-key-nav_'+routes[name]).get_by_role('button').click()
    page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'",timeout=60000)
    # No celular, a lateral aberta cobre a navegação superior. Fechar antes
    # de escolher o destino, em vez de forçar clique através do painel.
    if width<900:
        collapse=page.get_by_role('button',name='Collapse sidebar',exact=True)
        if collapse.is_visible():collapse.click()
    _ready(page,heading)
    if width<900:
        collapse=page.get_by_role('button',name='Collapse sidebar',exact=True)
        if collapse.is_visible():collapse.click()


def font_probe(page):
    """Fonte real via Chromium; fonts.check sozinho também passa se não há face."""
    cdp=page.context.new_cdp_session(page);cdp.send('DOM.enable');cdp.send('CSS.enable')
    node=cdp.send('DOM.querySelector',{'nodeId':cdp.send('DOM.getDocument')['root']['nodeId'],
        'selector':'[data-testid="stMain"] h1'})['nodeId']
    applied=cdp.send('CSS.getPlatformFontsForNode',{'nodeId':node})['fonts']
    heading=page.locator('[data-testid="stMain"] h1').first
    old_style=heading.get_attribute('style')
    try:
        page.evaluate("document.fonts.load('400 15px Inter')")
        heading.evaluate("el=>el.style.fontFamily='Inter, sans-serif'")
        page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        fallback=cdp.send('CSS.getPlatformFontsForNode',{'nodeId':node})['fonts']
        faces=page.evaluate("[...document.fonts].filter(f=>f.family==='Inter').map(f=>({family:f.family,status:f.status,weight:f.weight}))")
        requests=page.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('/app/static/fonts/InterVariable.woff2')).map(r=>({url:r.name,decodedBytes:r.decodedBodySize}))")
    finally:
        heading.evaluate('(el,style)=>style===null?el.removeAttribute("style"):el.setAttribute("style",style)',old_style)
        page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        cdp.detach()
    return {'appliedFonts':applied,'interFallbackFonts':fallback,'interFaces':faces,'localFontRequests':requests}


def capture(data_dir,output,label,all_screens=False,url='http://127.0.0.1:8602/'):
    from playwright.sync_api import sync_playwright
    output=Path(output);results=[];remote=[]
    with demo_server(data_dir,url,output),sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='msedge',headless=True)
        try:
            for width,height in SIZES:
                context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,reduced_motion='reduce')
                def local_only(route):
                    if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                    else:remote.append(route.request.url);route.abort()
                context.route('**/*',local_only)
                page=context.new_page();page.goto(url);_ready(page,'Olá')
                fonts=font_probe(page)
                for name,visible,heading in SCREENS if all_screens else SCREENS[:1]:
                    _screen(page,name,visible,heading,width)
                    if page.get_by_test_id('stException').count():raise RuntimeError('Exceção na tela '+name)
                    path=output/f'{label}-{name}-{width}x{height}.png'
                    page.screenshot(path=str(path),full_page=False)
                    metrics=page.evaluate('''() => ({
                      viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
                      font:getComputedStyle(document.querySelector('[data-testid="stMain"] h1')).fontFamily,
                      titleSize:getComputedStyle(document.querySelector('[data-testid="stMain"] h1')).fontSize,
                      captionOpacity:[...document.querySelectorAll('[data-testid="stCaptionContainer"]')].map(e=>getComputedStyle(e).opacity),
                      cornerShape:CSS.supports('corner-shape','squircle'),
                      buttons:[...document.querySelectorAll('[data-testid="stMain"] button')].filter(e=>e.checkVisibility()).map(e=>({text:e.innerText.trim().slice(0,70),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))
                    })''')
                    results.append({'screen':name,'size':[width,height],'image':path.name,'fontEvidence':fonts,**metrics})
                context.close()
        finally:browser.close()
    summary={'synthetic':True,'label':label,'screens':results,'blocked_remote_requests':sorted(set(remote))}
    (output/f'{label}-manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--label',choices=['antes','depois'],required=True);parser.add_argument('--all-screens',action='store_true')
    parser.add_argument('--url',default='http://127.0.0.1:8602/');args=parser.parse_args()
    result=capture(args.data_dir,args.output,args.label,args.all_screens,args.url)
    print(json.dumps({'synthetic':True,'captures':len(result['screens']),'output':str(args.output),'remote_requests':len(result['blocked_remote_requests'])}))
