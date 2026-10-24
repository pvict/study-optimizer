from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_daily_excess import configured
from test_adaptive_planning import topic


def test_day_summary_shows_real_excess_and_keeps_other_blocks(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); before=s.overview('2026-10-15'); s.remember_day(before)
    first=before['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    topics=[{**topic(name),'is_leaf':True} for name in 'ABCDEF']
    monkeypatch.setattr(AdaptiveService,'catalog',lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None}))
    monkeypatch.setenv('EXCESS_UI_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_day_ui import render_study_day
render_study_day(AdaptiveService(Repository(os.environ['EXCESS_UI_ROOT'])),lambda *args:None,lambda *args:None)
''',default_timeout=90).run()
    assert not app.exception
    assert any('2 questões além dos blocos previstos' in m.value for m in app.markdown)
    assert len([b for b in app.button if b.label=='Registrar este bloco'])==5
