import unittest
from datetime import datetime, timezone
from scripts.arvexq_stage64_auto_capture import select_future

PLAN = {"startDate":"2026-10-21","endDate":"2026-11-19","developmentIds":[]}
NOW = datetime(2026,10,22,3,0,tzinfo=timezone.utc)  # JST 12:00
def race(owner,n,clock="14:00",date="2026-10-22"):
    return {"id":f"{owner}-{date}-place-{n:02d}","date":date,"circuit":owner,
            "startTime":clock,"fieldSize":3,"horses":[]}

class AutoCapture(unittest.TestCase):
    def test_select_future_isolates_circuits_and_off_times(self):
        rows=[race("jra",1),race("nar",2),race("jra",3,"12:10"),race("jra",4,"12:30")]
        chosen,audit=select_future({"details":rows},"jra",PLAN,NOW)
        self.assertEqual([r["id"] for r in chosen],[rows[0]["id"]])
        self.assertEqual(audit["circuitRaces"],3)
        self.assertEqual(len(audit["excluded"]),2)

    def test_does_not_fill_unknown_or_missing_time(self):
        row=race("nar",1);row.pop("startTime")
        chosen,audit=select_future({"details":[row]},"nar",PLAN,NOW)
        self.assertFalse(chosen)
        self.assertEqual(audit["excluded"][0]["reason"],"no-verified-start-time")

    def test_rejects_outside_window_and_frozen_development(self):
        old=race("nar",1,date="2026-10-20"); dev=race("nar",2)
        p=dict(PLAN,developmentIds=[dev["id"]])
        chosen,audit=select_future({"details":[old,dev]},"nar",p,NOW)
        self.assertFalse(chosen)
        self.assertEqual(len(audit["excluded"]),2)

    def test_duplicate_fails_closed(self):
        row=race("jra",1)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            select_future({"details":[row,dict(row)]},"jra",PLAN,NOW)

    def test_naive_clock_and_missing_saved_rows_fail(self):
        with self.assertRaises(ValueError):
            select_future({"details":[]},"nar",PLAN,NOW)
        with self.assertRaises(ValueError):
            select_future({"details":[race("nar",1)]},"nar",PLAN,datetime(2026,10,22))

    def test_keep_unscorable_preoff_in_forecast_cohort(self):
        row=race("nar",1)  # no horse history: separate research stage records blockers
        selected,_=select_future({"details":[row]},"nar",PLAN,NOW)
        self.assertEqual(selected,[row])

if __name__=="__main__": unittest.main()
