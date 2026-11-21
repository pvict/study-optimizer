from copy import deepcopy
import unittest
import osler.study_replanning as replanning


class RecoveryDates(unittest.TestCase):
    def summarize(self, backlog, bookings):
        fn = getattr(replanning, 'backlog_schedule', None)
        self.assertTrue(callable(fn), 'Falta a classificação de datas reais de recuperação')
        return fn(backlog, bookings, '2026-11-16')

    def test_expired_and_completed_reservations_do_not_hide_missing_dates(self):
        backlog = [{'topic_id': t, 'questions': 20} for t in ['old', 'done', 'missing']]
        rows = self.summarize(backlog, [
            {'topic_id': 'old', 'date': '2026-11-15', 'remaining': 20},
            {'topic_id': 'done', 'date': '2026-11-18', 'remaining': 0}])
        self.assertEqual([r['recovery_current'] for r in rows], [False, False, False])
        self.assertEqual([r['recovery_date'] for r in rows], ['2026-11-15', None, None])

    def test_today_and_future_are_reserved_once_per_topic_without_mutating_input(self):
        backlog = [{'topic_id': 'a', 'questions': 20}, {'topic_id': 'b', 'questions': 10}]
        bookings = [
            {'topic_id': 'a', 'date': '2026-11-14', 'remaining': 20},
            {'topic_id': 'a', 'date': '2026-11-19', 'remaining': 20},
            {'topic_id': 'a', 'date': '2026-11-18', 'remaining': 20},
            {'topic_id': 'b', 'date': '2026-11-16', 'remaining': 10}]
        before = deepcopy((backlog, bookings))
        rows = self.summarize(backlog, bookings)
        self.assertEqual([r['recovery_date'] for r in rows], ['2026-11-18', '2026-11-16'])
        self.assertEqual([r['recovery_current'] for r in rows], [True, True])
        self.assertEqual((backlog, bookings), before)


if __name__ == '__main__':
    unittest.main()
