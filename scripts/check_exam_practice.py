"""QA visual descartável: nunca lê nem replica os dados ativos do usuário."""
from datetime import timedelta
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.capture_bento import demo_server,_ready,_screen,SIZES
from scripts.check_bento_planning import _wrapper,_metrics
from scripts.seed_demo_data import seed_demo_data
from osler.adaptive_service import AdaptiveService
from osler.mock_exams import MockExams
from osler.planner_service import today_local
from osler.storage import Repository


def main():
    from playwright.sync_api import sync_playwright
    output=ROOT/'evidencias/exam-practice';output.mkdir(parents=True,exist_ok=True)
    records=[];remote=[];today=today_local()
    with tempfile.TemporaryDirectory(prefix='osler-exam-practice-') as temporary:
        temporary=Path(temporary);folder=temporary/'scenario';seed_demo_data(folder,today)
        service=AdaptiveService(Repository(folder))
        service.apply_area_schedule(service.preview_area_schedule(today.isoformat(),(today+timedelta(days=55)).isoformat(),1,20,['UNESP','SUS-SP']))
        exam=MockExams(service.repository).active()[0]
        catalog,_=service.catalog(today.isoformat())
        service.save_mock_errors(exam['exam_key'],exam['version'],[{'path':t['path'],'errors':3} for t in catalog[:3]],0,service.agenda.token())
        preview=service.preview_mock_correction(exam['exam_key'],today.isoformat(),40)
        if preview['unassigned']:raise RuntimeError('O cenário sintético não coube na capacidade configurada.')
        service.apply_mock_correction(preview)
        with demo_server(folder,'http://127.0.0.1:8602/',output,app_path=_wrapper(temporary)),sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                for width,height in SIZES:
                    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                    def local_only(route):
                        if urlsplit(route.request.url).hostname in {'127.0.0.1',None}:route.continue_()
                        else:remote.append(route.request.url);route.abort()
                    context.route('**/*',local_only)
                    page=context.new_page();page.goto('http://127.0.0.1:8602/');_ready(page,'Olá')
                    for name,label,heading in [('hoje','Hoje','Olá'),('calendario','Calendário','Calendário de estudos'),('simulados','Simulados','Seus simulados')]:
                        _screen(page,name,label,heading,width)
                        tabs=['Treinos por área','Correção'] if name=='simulados' else [None]
                        for tab in tabs:
                            if tab:
                                page.get_by_role('tab',name=tab,exact=True).click()
                                page.wait_for_timeout(150)
                            if tab=='Treinos por área':
                                page.get_by_text('Configurar o rodízio',exact=True).click()
                                page.get_by_role('button',name='Ver prévia do rodízio',exact=True).click()
                                page.get_by_text('Confira antes de aplicar',exact=True).wait_for()
                                page.get_by_text('Ajustar a data de um tema nesta prévia',exact=True).click()
                            metrics=_metrics(page)
                            if metrics['exceptions']:raise RuntimeError(metrics['exceptions'])
                            if metrics['documentWidth']>width+2 or metrics['mainWidth']>metrics['mainClientWidth']+2:raise RuntimeError(f'Overflow em {name}/{tab}/{width}')
                            if width in (1440,390):
                                file=f'{name}-{tab or "principal"}-{width}.png'.replace(' ','-')
                                page.screenshot(path=str(output/file))
                            records.append({'screen':name,'tab':tab,'width':width,'overflow':metrics['overflowing'],'exceptions':metrics['exceptions']})
                    context.close()
            finally:browser.close()
    (output/'verificacao.json').write_text(json.dumps({'synthetic':True,'sizes':SIZES,'records':records,'remote_requests_blocked':remote,'temporary_data_removed':True},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'screens':len(records),'exceptions':0,'document_overflow':0,'temporary_data_removed':True}))


if __name__=='__main__':main()
