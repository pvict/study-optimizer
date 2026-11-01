"""Auditoria de navegação em cópia temporária do banco; nunca usa a base ativa no app."""
import argparse
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from osler.workspace import active_data_dir


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'evidencias'/('auditoria-runtime-'+datetime.now().strftime('%Y-%m-%d-%H%M%S')))
    args=parser.parse_args()
    from playwright.sync_api import sync_playwright
    out=args.output.resolve()
    if out.exists():raise FileExistsError('Escolha uma pasta nova para preservar as evidências anteriores.')
    out.mkdir(parents=True)
    source=active_data_dir(ROOT);checks=[]
    with tempfile.TemporaryDirectory(prefix='osler-audit-') as temporary:
        folder=Path(temporary);data=folder/'data';data.mkdir()
        with closing(sqlite3.connect(source.joinpath('osler.sqlite3').as_uri()+'?mode=ro',uri=True)) as db,closing(sqlite3.connect(data/'osler.sqlite3')) as target:
            db.backup(target)
        shutil.copytree(source/'exports',data/'exports')
        from scripts.check_bento_planning import _wrapper
        wrapper=_wrapper(folder)
        with socket.socket() as probe:probe.bind(('127.0.0.1',8603))
        with (out/'server.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(wrapper),'--server.address','127.0.0.1','--server.port','8603','--server.fileWatcherType','none','--browser.gatherUsageStats','false'],
                cwd=ROOT,env={**os.environ,'OSLER_DATA_DIR':str(data)},stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                for _ in range(100):
                    try:
                        with urlopen('http://127.0.0.1:8603/_stcore/health',timeout=1) as response:
                            if response.status==200:break
                    except OSError:time.sleep(.2)
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='msedge',headless=True)
                    page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                    page.route('**/*',lambda r:r.continue_() if urlsplit(r.request.url).hostname in {'127.0.0.1',None} else r.abort())
                    def timed(label,action,heading):
                        start=time.perf_counter();action()
                        page.get_by_role('heading',name=heading,exact=True).wait_for(timeout=180000)
                        page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'",timeout=180000)
                        page.wait_for_function("!document.querySelector('[data-stale=\"true\"]') && !document.querySelector('[data-testid=stSkeleton]')",timeout=180000)
                        page.evaluate('document.fonts.ready')
                        page.wait_for_timeout(350)
                        errors=page.locator('[data-testid="stException"]').all_text_contents()
                        row={'action':label,'browser_seconds':round(time.perf_counter()-start,3),'exceptions':errors,'no_page_overflow':page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')}
                        checks.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
                        page.screenshot(path=str(out/(str(len(checks))+'-'+label+'.png')),full_page=False)
                    timed('hoje-inicial',lambda:page.goto('http://127.0.0.1:8603/'),'Olá')
                    routes=[('attention','atencao','Temas em atenção'),('topics','temas','Temas e desempenho'),
                            ('calendar','calendario','Calendário de estudos'),('mocks','simulados','Seus simulados'),
                            ('evolution','evolucao','Sua evolução'),('register','registro','Registrar resultado'),
                            ('flashcards','flashcards','Seus cards de erros'),('today','hoje-retorno','Olá')]
                    for key,label,heading in routes:
                        timed(label,lambda key=key:page.locator('.st-key-nav_'+key).get_by_role('button').click(),heading)
                    # Viewport estreita: geometria apenas, não validação em dispositivo físico.
                    page.set_viewport_size({'width':390,'height':844})
                    close=page.get_by_role('button',name='Collapse sidebar',exact=True)
                    if close.is_visible():close.click()
                    page.wait_for_timeout(400)
                    checks.append({'action':'hoje-mobile','no_page_overflow':page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')})
                    page.screenshot(path=str(out/'hoje-mobile.png'))
                    browser.close()
            finally:
                if process.poll() is None:
                    if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
                    else:process.terminate()
                    process.wait(timeout=15)
                (out/'browser-metrics.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Auditoria terminou; cópia temporária removida. Dados ativos preservados.',flush=True)


if __name__=='__main__':main()
