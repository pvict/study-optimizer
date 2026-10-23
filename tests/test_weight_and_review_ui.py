from streamlit.testing.v1 import AppTest
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService

APP='''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.final_review_ui import render_exam_weights
render_exam_weights(AdaptiveService(Repository(os.environ['WEIGHT_UI_ROOT'])))
'''


def test_weight_ui_blocks_inputs_without_individual_files(tmp_path,sample_pdf,monkeypatch):
    from test_exam_weight_policy import configured
    service,target,_=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('WEIGHT_UI_ROOT',str(tmp_path))
    app=AppTest.from_string(APP,default_timeout=60).run()
    assert not app.exception
    assert all(c.disabled for c in app.checkbox)
    assert any('incidência individual' in m.value.lower() for m in app.info)
    assert service.store.profile()['id']==0


def test_weight_ui_requires_preview_before_profile_is_saved(tmp_path,sample_pdf,monkeypatch):
    from test_exam_weight_policy import configured
    service,target,_=configured(tmp_path,sample_pdf,True)
    monkeypatch.setenv('WEIGHT_UI_ROOT',str(tmp_path))
    app=AppTest.from_string(APP,default_timeout=60).run()
    app.checkbox[0].check().run()
    next(n for n in app.number_input if 'Importância' in n.label).set_value(1.5).run()
    assert service.store.profile()['id']==0
    app.button(key='exam_weight_preview').click().run()
    assert not app.exception and service.store.profile()['id']==0
    assert any('Banca B' in str(d.value) for d in app.dataframe)
    app.button(key='exam_weight_apply').click().run()
    assert not app.exception
    assert service.store.profile()['profile']['institution_weights']=={'Banca A':1.5,'Banca B':1}


def test_search_table_always_shows_real_next_review_in_history_view(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    repo,*_,topic=setup_assessment(tmp_path,sample_pdf)
    original_catalog=AdaptiveService.catalog
    def snapshot_catalog(self,as_of,include_parents=False):
        topics,sources=original_catalog(self,as_of,include_parents)
        for t in topics:
            if t['path']==topic.qbank.path:
                t['planner_snapshot']={'observed_date':'2026-10-15','unique_questions':34,'available_questions':99,
                    'confident_accuracy_pct':73.5,'last_contact':'2026-10-14','pending_reviews':0,'dataset_id':1}
        return topics,sources
    monkeypatch.setattr(AdaptiveService,'catalog',snapshot_catalog)
    monkeypatch.setenv('WEIGHT_UI_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_tables_ui import render_topic_table
render_topic_table(AdaptiveService(Repository(os.environ['WEIGHT_UI_ROOT'])),lambda *args:None)
''',default_timeout=90).run()
    app.text_input(key='statistics_search').set_value('Feridas').run()
    assert not app.exception
    frame=next(d.value for d in app.dataframe if 'Estado' in d.value.columns and 'Tema' in d.value.columns)
    assert 'Próxima revisão' in frame.columns
    assert frame['Próxima revisão'].iloc[0] not in (None,'')
    assert app.radio(key='statistics_source').value=='Histórico da Osler'
    app.radio(key='statistics_source').set_value('Blocos registrados no app').run()
    assert not app.exception
    assert any('Próxima revisão' in d.value.columns for d in app.dataframe)


def test_weight_ui_can_clear_legacy_raw_weights_after_all_exams_are_removed(tmp_path,sample_pdf,monkeypatch):
    import json
    from dataclasses import replace
    from test_exam_weight_policy import configured
    from osler.study_models import AdaptiveProfile
    from osler.exam_goals import ExamGoals
    service,target,_=configured(tmp_path,sample_pdf)
    p=replace(AdaptiveProfile(),institution_weights={'Banca A':1.5,'Banca B':1})
    with service.repository._connection() as db:
        db.execute('INSERT INTO study_profiles(payload,created_at) VALUES(?,?)',(json.dumps(p.to_dict()),'2026-10-15'))
    ExamGoals(service.repository).void(target['target_id'],target['version'])
    monkeypatch.setenv('WEIGHT_UI_ROOT',str(tmp_path))
    app=AppTest.from_string(APP,default_timeout=60).run()
    app.button(key='exam_weight_preview').click().run()
    assert not app.exception
    assert any('Pesos antigos' in m.value for m in app.info)
    app.button(key='exam_weight_apply').click().run()
    assert not app.exception
    assert service.store.profile()['configured_profile']['institution_weights']=={'Banca A':1,'Banca B':1}


def test_topic_table_rejects_stale_overview_before_caching_dates(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.study_models import StudyDay
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    original=AdaptiveService.overview
    changed=[]
    def racing_overview(self,*args,**kwargs):
        view=original(self,*args,**kwargs)
        if not changed:
            self.store.save_day(view['date'],StudyDay(kind='descanso'),0)
            changed.append(True)
        return view
    monkeypatch.setattr(AdaptiveService,'overview',racing_overview)
    monkeypatch.setenv('WEIGHT_UI_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_tables_ui import render_topic_table
render_topic_table(AdaptiveService(Repository(os.environ['WEIGHT_UI_ROOT'])),lambda *args:None)
''',default_timeout=90).run()
    assert not app.exception and any('plano mudou' in i.value for i in app.info)
    assert not app.dataframe
    next(b for b in app.button if b.label=='Atualizar tabela').click().run()
    assert not app.exception and app.dataframe
