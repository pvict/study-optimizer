import unittest
from datetime import date,timezone,timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from osler.study_models import AdaptiveProfile
from osler.study_replanning import preview_replan


class ReplanningCommitments(unittest.TestCase):
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
