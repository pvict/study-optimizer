import unittest
import tempfile
from pathlib import Path
from datetime import date,timezone,timedelta
from unittest.mock import patch
from osler.error_cards import parse_error_cards


class RecoveryTests(unittest.TestCase):
    def test_service_keeps_external_counts_out_of_performance_and_detects_stale_save(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            token=a.agenda.token();s.save(294,30,60,50,70,day,token)
            v=a.overview(day)
            self.assertEqual(v['plan']['routine_override']['recovery_reserved'],30)
            self.assertLessEqual(v['plan']['target_questions'],30)
            self.assertLessEqual(a.overview(day,questions=120)['plan']['target_questions'],30)
            token=a.agenda.token();s.record(day,20,token)
            with self.assertRaises(ValueError):s.record(day,5,token)
            v=a.overview(day)
            self.assertEqual(v['agenda']['quantity_recovery']['remaining'],274)
            self.assertEqual(v['plan']['routine_override']['recovery_reserved'],30)
            self.assertFalse(a.store.events())

    def test_html_ignores_training_counter(self):
        html='<div class="TreeNode-x" style="margin-left: 0px;"><span class="Label-x">Tema</span><p class="StatInfo-x">50</p><p class="StatInfo-x">8</p></div>'
        self.assertEqual(parse_error_cards(html)['total'],50)

    def test_external_schedule_conserves_count_and_skips_mock(self):
        from osler.recovery import project_questions
        rows=project_questions(294,30,'2026-11-14','2026-12-31',{}, {'2026-11-15':{'mode':'mock_reserved'}})
        self.assertEqual(sum(rows.values()),294)
        self.assertEqual(len(rows),10)
        self.assertNotIn('2026-11-15',rows)
        self.assertTrue(all(n<=30 for n in rows.values()))

    def test_decks_are_whole_and_large_deck_is_alone(self):
        from osler.recovery import project_decks
        topics=[{'topic_id':str(n),'path':['Area',str(n)],'count':n} for n in [20,30,65,133]]
        rows=project_decks(topics,{},'2026-11-14','2027-02-01',{}, {},50,70)
        self.assertEqual(sum(r['cards'] for r in rows),248)
        self.assertEqual(len([d for r in rows for d in r['decks']]),4)
        self.assertTrue(all(len(r['decks'])==1 for r in rows if r['cards']>70))
        self.assertTrue(all(d['count'] in [20,30,65,133] for r in rows for d in r['decks']))

    def test_missed_deck_carries_without_increasing_daily_target(self):
        from osler.recovery import project_decks
        topics=[{'topic_id':str(n),'path':['Area',str(n)],'count':n} for n in [20,30,65]]
        rows=project_decks(topics,{'20':20},'2026-11-20','2027-01-01',{}, {},50,70)
        self.assertEqual(sum(r['cards'] for r in rows),95)
        self.assertEqual(rows[0]['date'],'2026-11-20')
        self.assertTrue(all(r['cards']<=70 for r in rows))

    def test_finishing_daily_cards_does_not_offer_another_deck_today(self):
        from osler.recovery import project_decks
        topics=[{'topic_id':str(n),'path':['Area',str(n)],'count':n} for n in [20,30,65]]
        rows=project_decks(topics,{'20':20,'30':30},'2026-11-20','2027-01-01',{}, {},50,70,done_today=50)
        self.assertEqual(rows[0]['date'],'2026-11-21')

    def test_recording_same_sized_batches_is_not_silently_deduplicated(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            s.save(100,30,60,50,70,day,a.agenda.token())
            s.record(day,10,a.agenda.token());s.record(day,10,a.agenda.token())
            self.assertEqual(a.overview(day)['agenda']['quantity_recovery']['remaining'],80)

    def test_recovery_reservation_is_inside_total_and_area_is_not_subtracted_twice(self):
        from osler.study_replanning import effective_routine
        from osler.study_models import AdaptiveProfile
        _,q=effective_routine(AdaptiveProfile(max_questions=120),{'questions':120},
                             {'recovery_limit':60,'recovery_reserved':30,'area_reserved':20})
        self.assertEqual(q,10)

    def test_extra_mode_does_not_expand_recovery_ceiling(self):
        from osler.study_replanning import effective_routine
        from osler.study_models import AdaptiveProfile
        _,q=effective_routine(AdaptiveProfile(max_questions=120),{'questions':120},
                             {'mode':'extra','extra_questions':20,'recovery_limit':60,'recovery_reserved':30})
        self.assertEqual(q,30)

    def test_already_completed_questions_reduce_external_capacity(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        from osler.study_models import StudyEntry
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            a.store.save_batch([('ordinary',StudyEntry(['Area','Tema'],day,50,correct=25),0)])
            s.save(100,30,60,50,70,day,a.agenda.token())
            self.assertEqual(a.overview(day)['plan']['routine_override']['recovery_reserved'],10)
            with self.assertRaises(ValueError):s.record(day,30,a.agenda.token())
            s.record(day,10,a.agenda.token())
            self.assertEqual(a.overview(day)['plan']['routine_override']['recovery_reserved'],10)

    def test_completed_large_deck_keeps_smaller_question_limit(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        from osler.error_cards_service import ErrorCardsService
        html=b'<div class="TreeNode-x" style="margin-left: 0px;"><span class="Label-x">Tema</span><p class="StatInfo-x">100</p></div>'
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo);c=ErrorCardsService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            c.import_html(html,'cards.html',day,'pass',c.token());snap=c.latest_snapshot()
            s.save(100,30,60,50,70,day,a.agenda.token(),snap['tree']['topics'],snap['id'])
            self.assertEqual(a.overview(day)['plan']['routine_override']['recovery_limit'],30)
            c.record(snap['tree']['topics'][0]['topic_id'],day,100,0,None,'session-1',c.token())
            self.assertEqual(a.overview(day)['plan']['routine_override']['recovery_limit'],30)
            old_id=snap['id'];c.import_html(html,'cards.html',day,'pass',c.token(),new_pass=True)
            self.assertNotEqual(old_id,c.latest_snapshot()['id'])

    def test_configuration_can_return_to_previous_values(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            for total in (100,200,100):s.save(total,30,60,50,70,day,a.agenda.token())
            self.assertEqual(s.settings()['total'],100)

    def test_failed_stage_does_not_import_snapshot_into_live_repository(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery_apply import apply_recovery
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            token=a.agenda.token()
            p={'token':token,'total':100,'daily':30,'limit':60,'target':50,'ceiling':70,'start':day,
               'raw':b'invalid','filename':'bad.html','observed_day':day}
            with self.assertRaises(ValueError):apply_recovery(repo,p)
            self.assertEqual(a.agenda.token(),token)

    def test_successful_apply_keeps_created_cards_and_preserves_question_history(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery_apply import apply_recovery
        from osler.recovery import RecoveryService
        from osler.study_models import StudyEntry
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo)
            day=__import__('osler.planner_service',fromlist=['today_local']).today_local().isoformat()
            a.store.save_batch([('ordinary',StudyEntry(['Area','Tema'],day,10,correct=5,cards_created=12),0)])
            before=a.store.events();p={'token':a.agenda.token(),'total':100,'daily':30,'limit':60,'target':50,'ceiling':70,
                'start':day,'raw':None,'filename':None,'observed_day':day}
            self.assertTrue(apply_recovery(repo,p))
            self.assertEqual(a.store.events(),before)
            self.assertEqual(sum(t['count'] for t in RecoveryService(repo).settings()['topics']),12)


if __name__=='__main__':unittest.main()
