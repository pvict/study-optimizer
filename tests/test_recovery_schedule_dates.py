"""Datas antigas não podem esconder temas que precisam de reagendamento."""
import copy
import unittest

from osler import study_replanning


class RecoveryScheduleDatesTests(unittest.TestCase):
    def schedule(self, backlog, bookings):
        function=getattr(study_replanning,'backlog_schedule',None)
        self.assertTrue(callable(function),'Falta classificar a data atual de cada recuperação')
        return function(backlog,bookings,'2026-11-15')

    def test_expired_booking_still_needs_a_new_date(self):
        rows=self.schedule([{'topic_id':'A','path':['Área','A']}],
                           [{'topic_id':'A','date':'2026-11-01','remaining':20}])
        self.assertFalse(rows[0]['recovery_current'])
        self.assertEqual(rows[0]['recovery_date'],'2026-11-01')
        self.assertEqual(rows[0]['recovery_status'],'Data vencida — reagendar')

    def test_today_and_future_bookings_are_current(self):
        rows=self.schedule([{'topic_id':x} for x in ['A','B']],
                           [{'topic_id':'A','date':'2026-11-15','remaining':10},
                            {'topic_id':'B','date':'2026-11-20','remaining':20}])
        self.assertTrue(all(r['recovery_current'] for r in rows))
        self.assertEqual(rows[0]['recovery_status'],'Agendado para hoje')
        self.assertEqual(rows[1]['recovery_date'],'2026-11-20')

    def test_completed_or_missing_dates_do_not_reserve_a_new_date(self):
        rows=self.schedule([{'topic_id':x} for x in ['A','B','C']],
                           [{'topic_id':'A','date':'2026-11-20','remaining':0},
                            {'topic_id':'B','date':None,'remaining':20}])
        self.assertTrue(all(not r['recovery_current'] for r in rows))
        self.assertTrue(all(r['recovery_date'] is None for r in rows))

    def test_earliest_current_booking_wins_without_mutating_history(self):
        backlog=[{'topic_id':'A'}]
        bookings=[{'topic_id':'A','date':d,'remaining':20}
                  for d in ['2026-11-01','2026-11-22','2026-11-20']]
        original=copy.deepcopy((backlog,bookings))
        row=self.schedule(backlog,bookings)[0]
        self.assertEqual(row['recovery_date'],'2026-11-20')
        self.assertEqual((backlog,bookings),original)


if __name__=='__main__':unittest.main()
