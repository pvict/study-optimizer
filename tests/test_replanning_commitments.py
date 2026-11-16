import unittest
from datetime import date,datetime,timezone,timedelta
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from unittest.mock import patch
from osler.study_models import AdaptiveProfile
from osler.study_replanning import preview_replan


class ReplanningCommitments(unittest.TestCase):
    def setUp(self):
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return cls(2026,11,16,12,tzinfo=tz)
        stack=ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch('osler.planner_service.datetime',Clock))
        stack.enter_context(patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))))

    def test_swapped_topic_does_not_get_a_second_inexecutable_booking_today(self):
        from osler.adaptive_service import AdaptiveService
        from osler.storage import Repository
        topics=[{'topic_id':n,'path':['Area',n],'total':100,'answered_pdf':0,
                 'pdf_accuracy':{'value':None,'operator':'=','raw':'-'},
                 'report_date':'2026-11-15','studied_cards':0,'is_leaf':True} for n in ['A','B','C','D','E']]
        with TemporaryDirectory() as folder, \
             patch('osler.adaptive_service.today_local',return_value=date(2026,11,16)), \
             patch('osler.planner_service.today_local',return_value=date(2026,11,16)), \
             patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            s=AdaptiveService(Repository(folder))
            s.catalog=lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None})
            s.store.save_profile(AdaptiveProfile(max_questions=80,max_topics=3,new_share=1),0)
            s.agenda.append({'kind':'daily_schedule','plan':{'date':'2026-11-15','items':[
                {'topic_id':'D','path':['Area','D'],'questions':40}]}},s.agenda.token())
            original=next(r['topic_id'] for r in s.overview('2026-11-16')['plan']['items'] if r['topic_id']!='D')
            options=s.swap_options('2026-11-16',original)
            s.swap_topic('2026-11-16',original,'D',options['token'],'manual')
            preview=s.preview_replan('2026-11-16',3,'balanced',selected=['D'])
            self.assertTrue(preview['rows'])
            self.assertGreater(preview['rows'][0]['date'],'2026-11-16')

    def test_completed_area_training_is_not_charged_twice(self):
        preview=self._area_preview(20)
        self.assertTrue(preview['rows'],'30 questões cabem nas 40 vagas ordinárias restantes')
        self.assertEqual(preview['rows'][0]['date'],'2026-11-16')
        self.assertEqual(preview['rows'][0]['questions'],30)

    def test_area_training_above_reservation_still_consumes_capacity(self):
        preview=self._area_preview(40)
        self.assertEqual(preview['rows'],[],'40 feitas + 30 novas ultrapassariam o teto de 60')
        self.assertEqual(len(preview['unassigned']),1)

    def _area_preview(self,actual):
        from datetime import datetime
        from osler.adaptive_service import AdaptiveService
        from osler.storage import Repository
        from osler.study_models import StudyEntry
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return cls(2026,11,16,12,tzinfo=tz)
        topic={'topic_id':'A','path':['Area','A'],'total':100,'answered_pdf':40,
               'pdf_accuracy':{'value':80,'operator':'=','raw':'80%'},'report_date':'2026-11-15','studied_cards':0,'is_leaf':True}
        with TemporaryDirectory() as folder,patch('osler.planner_service.datetime',Clock), \
             patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            s=AdaptiveService(Repository(folder))
            s.catalog=lambda *args,**kwargs:([topic],{'qbank':None,'flashcards':None})
            s.store.save_profile(AdaptiveProfile(max_questions=60,max_topics=3,new_share=0),0)
            s.save_entry(StudyEntry(topic['path'],'2026-11-01',20,10,confident_correct=10),'old')
            s.agenda.append({'kind':'daily_schedule','plan':{'date':'2026-11-15','items':[
                {'topic_id':'A','path':topic['path'],'questions':30}]}},s.agenda.token())
            s.apply_area_schedule(s.preview_area_schedule('2026-11-16','2026-11-30',1,20,['UNESP']))
            s.register_area_result('area-2026-11-16','2026-11-16',actual,18,unseen=True,token=s.agenda.token())
            preview=s.preview_replan('2026-11-16',1,'balanced',selected=['A'])
            return preview

    def test_swap_occupies_today_slot_and_existing_return_keeps_tomorrow(self):
        from osler.adaptive_service import AdaptiveService
        from osler.study_models import StudyEntry
        from osler.storage import Repository
        topics=[{'topic_id':n,'path':['Area',n],'total':100,'answered_pdf':0,
                 'pdf_accuracy':{'value':None,'operator':'=','raw':'-'},
                 'report_date':'2026-11-15','studied_cards':0,'is_leaf':True} for n in ['A','B','C']]
        with TemporaryDirectory() as folder, \
             patch('osler.adaptive_service.today_local',return_value=date(2026,11,16)), \
             patch('osler.planner_service.today_local',return_value=date(2026,11,16)), \
             patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            s=AdaptiveService(Repository(folder))
            s.catalog=lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None})
            s.store.save_profile(AdaptiveProfile(max_questions=20,max_topics=1,new_share=1),0)
            s.agenda.append({'kind':'daily_schedule','plan':{'date':'2026-11-15','items':[
                {'topic_id':'C','path':['Area','C'],'questions':20}]}},s.agenda.token())
            original=s.overview('2026-11-16')['plan']['items'][0]['topic_id']
            replacement=next(n for n in ['A','B'] if n!=original)
            options=s.swap_options('2026-11-16',original)
            s.swap_topic('2026-11-16',original,replacement,options['token'],'manual')
            prior=[dict(r) for r in s.replanning()['rows']]
            preview=s.preview_replan('2026-11-16',3,'balanced',selected=['C'])
            self.assertEqual(preview['rows'][0]['date'],'2026-11-18')
            s.apply_replan(preview)
            self.assertEqual([r for r in s.replanning()['rows'] if r['topic_id']!= 'C'],prior)
            self.assertEqual(s.overview('2026-11-16')['plan']['items'][0]['topic_id'],replacement)
            with patch('osler.planner_service.today_local',return_value=date(2026,11,18)), \
                 patch('osler.adaptive_service.today_local',return_value=date(2026,11,18)):
                s.save_entry(StudyEntry(['Area',original],'2026-11-17',20,20,confident_correct=20),'actual-return')
                self.assertIn('C',[r['topic_id'] for r in s.overview('2026-11-18')['plan']['items']])

    def test_advanced_modes_keep_shared_external_and_area_capacity(self):
        p=AdaptiveProfile(max_questions=60,new_share=0)
        row={'topic_id':'a','path':['Area','A'],'questions':40,'original_due':'2026-11-01','days_late':15}
        prior={'2026-11-16':{'mode':'balanced','recovery_limit':60,'recovery_reserved':30,'area_reserved':10}}
        for mode in ['balanced','reviews','extra']:
            with self.subTest(mode=mode):
                preview=preview_replan([row],p,'2026-11-16',1,mode,{},[],previous_overrides=prior)
                self.assertEqual(preview['rows'],[],'Reservas compartilhadas não podem desaparecer')
                self.assertEqual(len(preview['unassigned']),1)

    def test_external_day_stays_protected_in_advanced_modes(self):
        p=AdaptiveProfile(max_questions=60,new_share=0)
        row={'topic_id':'a','path':['Area','A'],'questions':20,'original_due':'2026-11-01','days_late':15}
        for mode in ['reviews','extra']:
            with self.subTest(mode=mode):
                preview=preview_replan([row],p,'2026-11-16',2,mode,{},[],previous_overrides={'2026-11-16':{'mode':'external_day'}})
                self.assertEqual(preview['rows'][0]['date'],'2026-11-17')
                self.assertNotIn('2026-11-16',preview['overrides'])


if __name__=='__main__':unittest.main()
