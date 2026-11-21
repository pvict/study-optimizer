import unittest
import tempfile
import importlib.util
import os
from pathlib import Path
from datetime import date,timezone,timedelta
from unittest.mock import patch


class RecurringQueueTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('streamlit'),'Interface validada no CI com Streamlit')
    def test_return_count_is_editable_without_submitting_the_form_first(self):
        from streamlit.testing.v1 import AppTest
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        from osler.planner_service import today_local
        with tempfile.TemporaryDirectory() as folder:
            a=AdaptiveService(Repository(Path(folder)));day=today_local().isoformat()
            RecoveryService(a.repository).save(3,30,80,50,70,day,a.agenda.token())
            with patch.dict(os.environ,{'RECURRING_UI_ROOT':folder}):
                app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.planner_service import today_local
from osler.recovery_ui import render_recovery
a=AdaptiveService(Repository(os.environ['RECURRING_UI_ROOT']))
render_recovery(a,a.overview(today_local().isoformat()))
''').run()
                self.assertFalse(app.exception)
                field=app.number_input(key='recovery_return_count')
                self.assertFalse(field.proto.disabled)
                self.assertIsNone(field.value)
    def test_failed_or_uncertain_returns_exactly_seven_days_later(self):
        from osler.recurring_questions import outstanding_batches
        cfg={'id':1,'start':'2026-11-14','total':30}
        events=[{'id':2,'kind':'recovery.quantity.done','plan_id':1,'day':'2026-11-14','count':30,'returning':8}]
        self.assertEqual(outstanding_batches(cfg,events,'2026-11-14'),[{'due':'2026-11-21','count':8}])

    def test_confident_or_unknown_answers_do_not_generate_invented_returns(self):
        from osler.recurring_questions import outstanding_batches
        cfg={'id':1,'start':'2026-11-14','total':30}
        for returning in [0,None]:
            events=[{'id':2,'kind':'recovery.quantity.done','plan_id':1,'day':'2026-11-14','count':30,'returning':returning}]
            self.assertEqual(outstanding_batches(cfg,events,'2026-11-21'),[])

    def test_return_can_generate_another_return_after_actual_review(self):
        from osler.recurring_questions import outstanding_batches
        cfg={'id':1,'start':'2026-11-14','total':30}
        events=[{'id':2,'kind':'recovery.quantity.done','plan_id':1,'day':'2026-11-14','count':30,'returning':8},
                {'id':3,'kind':'recovery.quantity.done','plan_id':1,'day':'2026-11-21','count':8,'returning':2}]
        self.assertEqual(outstanding_batches(cfg,events,'2026-11-21'),[{'due':'2026-11-28','count':2}])

    def test_future_generation_is_not_visible_before_it_is_recorded(self):
        from osler.recurring_questions import outstanding_batches
        cfg={'id':1,'start':'2026-11-14','total':0}
        events=[{'id':2,'kind':'recovery.quantity.generated','plan_id':1,'day':'2026-11-16','count':10}]
        self.assertEqual(outstanding_batches(cfg,events,'2026-11-14'),[])
        self.assertEqual(outstanding_batches(cfg,events,'2026-11-16'),[{'due':'2026-11-23','count':10}])

    def test_service_can_review_return_after_initial_balance_is_exhausted(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            with patch('osler.planner_service.today_local',return_value=date(2026,11,14)):
                s.save(30,30,80,50,70,'2026-11-14',a.agenda.token())
                s.record('2026-11-14',30,a.agenda.token(),returning=8)
                p=a.overview('2026-11-14')['agenda']['quantity_recovery']
                self.assertEqual(p['due_now'],0);self.assertEqual(p['remaining'],8)
                self.assertEqual(list(p['questions']),['2026-11-21'])
                with self.assertRaises(ValueError):s.record('2026-11-14',1,a.agenda.token(),returning=0)
            with patch('osler.planner_service.today_local',return_value=date(2026,11,21)):
                s.record('2026-11-21',8,a.agenda.token(),returning=2)
                self.assertEqual(a.overview('2026-11-21')['agenda']['quantity_recovery']['future_returns'],[{'due':'2026-11-28','count':2}])

    def test_future_returns_survive_a_new_pending_balance_without_duplication(self):
        from osler.recurring_questions import outstanding_batches
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))),patch('osler.planner_service.today_local',return_value=date(2026,11,14)):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            s.save(30,30,80,50,70,'2026-11-14',a.agenda.token());s.record('2026-11-14',30,a.agenda.token(),returning=8)
            s.save(10,30,80,50,70,'2026-11-14',a.agenda.token())
            self.assertEqual(outstanding_batches(s.settings(),s.events(),'2026-11-14'),[{'due':'2026-11-14','count':10},{'due':'2026-11-21','count':8}])

    def test_manual_generation_waits_for_due_date_and_shared_capacity(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))),patch('osler.planner_service.today_local',return_value=date(2026,11,14)):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            s.save(0,30,80,50,70,'2026-11-14',a.agenda.token());s.add_generated('2026-11-14',50,a.agenda.token())
            cfg={};over={'2026-11-21':{'mode':'mock_reserved'},'2026-11-22':{'area_reserved':70}}
            p=s.projection('2026-11-14',cfg,over,'2026-12-01')
            self.assertNotIn('2026-11-21',p['questions']);self.assertEqual(p['questions']['2026-11-22'],10)
            self.assertEqual(sum(p['questions'].values()),50)

    def test_backdated_review_cannot_spend_balance_already_used_on_later_day(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            with patch('osler.planner_service.today_local',return_value=date(2026,11,14)):
                s.save(30,30,80,50,70,'2026-11-14',a.agenda.token())
            with patch('osler.planner_service.today_local',return_value=date(2026,11,15)):
                s.record('2026-11-15',30,a.agenda.token(),returning=0)
                token=a.agenda.token()
                with self.assertRaises(ValueError):s.record('2026-11-14',30,token,returning=0)
                self.assertEqual(a.agenda.token(),token)
                self.assertEqual(a.overview('2026-11-15')['agenda']['quantity_recovery']['remaining'],0)

    def test_resetting_balance_does_not_reset_today_used_capacity(self):
        from osler.storage import Repository
        from osler.adaptive_service import AdaptiveService
        from osler.recovery import RecoveryService
        with tempfile.TemporaryDirectory() as folder, patch('osler.planner_service.ZoneInfo',return_value=timezone(timedelta(hours=-3))),patch('osler.planner_service.today_local',return_value=date(2026,11,14)):
            repo=Repository(Path(folder));a=AdaptiveService(repo);s=RecoveryService(repo)
            s.save(30,30,80,50,70,'2026-11-14',a.agenda.token());s.record('2026-11-14',30,a.agenda.token(),returning=0)
            s.save(40,30,80,50,70,'2026-11-14',a.agenda.token())
            p=a.overview('2026-11-14')['agenda']['quantity_recovery']
            self.assertEqual(p['remaining'],40)
            self.assertEqual(p['done_today'],30)
            self.assertNotIn('2026-11-14',p['questions'])
            with self.assertRaises(ValueError):s.record('2026-11-14',30,a.agenda.token(),returning=0)


if __name__=='__main__':unittest.main()
