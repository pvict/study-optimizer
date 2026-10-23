from osler.topic_contacts import apply_next_contacts


def test_due_date_is_kept_separate_from_real_future_slot_without_fake_dates():
    rows=[{'topic_id':'A','Próxima revisão':'2026-10-15','catalog_available':True},
          {'topic_id':'B','Próxima revisão':'2026-10-16','catalog_available':True},
          {'topic_id':'C','Próxima revisão':None,'catalog_available':False}]
    lookup={'contacts':{'A':{'date':'2026-10-19','stage':'Retorno de questões'}},'end':'2026-11-15'}
    shown=apply_next_contacts(rows,lookup)
    assert shown[0]['Próxima revisão']=='19/10/2026'
    assert shown[0]['Revisão devida']=='2026-10-15'
    assert 'Sem vaga' in shown[1]['Próxima revisão']
    assert 'catálogo' in shown[2]['Próxima revisão']
    assert rows[0]['Próxima revisão']=='2026-10-15'


def test_next_contact_uses_real_slot_after_reserved_mock_not_overdue_date(tmp_path,sample_pdf):
    from test_mock_schedule import configured
    from osler.study_models import StudyEntry
    from osler.topic_contacts import forecast_topic_contacts
    service,topic=configured(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(topic.qbank.path,'2026-10-08',20,10,confident_correct=10),'lot')
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-15',7))
    view=service.overview('2026-10-15')
    forecast=forecast_topic_contacts(service,view)
    date=forecast['contacts'][topic.qbank.topic_id]['date']
    assert date>'2026-10-15'
    assert service.overview(date)['plan']['kind']!='descanso'


def test_next_contacts_reject_view_built_before_a_concurrent_day_change(tmp_path,sample_pdf):
    import pytest
    from test_mock_schedule import configured
    from osler.study_models import StudyDay
    from osler.topic_contacts import forecast_topic_contacts
    service,_=configured(tmp_path,sample_pdf)
    old=service.overview('2026-10-15')
    service.store.save_day('2026-10-15',StudyDay(kind='descanso'),0)
    with pytest.raises(ValueError,match='plano mudou'):
        forecast_topic_contacts(service,old)
