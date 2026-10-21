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

    def test_explicit_zero_race_prefetch_is_not_a_missing_data_failure(self):
        for owner in ("jra", "nar"):
            with self.subTest(owner=owner):
                chosen, audit = select_future({"races": [], "details": []},
                                              owner, PLAN, NOW)
                self.assertEqual(chosen, [])
                self.assertEqual(audit["circuit"], owner)
                self.assertEqual(audit["sourceRows"], 0)
                self.assertEqual(audit["selected"], [])
                self.assertFalse(audit["fullCalendarVerified"])
                self.assertFalse(audit["independentlyVerifiedPreoff"])

    def test_missing_details_cannot_be_disguised_as_zero_races(self):
        for source in ({"details": []},
                       {"races": [race("nar", 1)], "details": []},
                       {"races": [], "details": None}):
            with self.subTest(source=source), self.assertRaises(ValueError):
                select_future(source, "nar", PLAN, NOW)

    def test_saved_prefetch_index_and_details_must_match_before_freeze(self):
        first = race("jra", 1)
        second = race("nar", 2)
        extra = race("jra", 3)
        complete = {"races": [first, second], "details": [second, first]}
        chosen, audit = select_future(complete, "jra", PLAN, NOW)
        self.assertEqual([r["id"] for r in chosen], [first["id"]])
        self.assertFalse(audit["fullCalendarVerified"])
        self.assertFalse(audit["independentlyVerifiedPreoff"])
        # An incomplete D1 detail readback must never become a partial cohort.
        invalid_pairs = [
            {"races": [first, second], "details": [first]},
            {"races": [first], "details": [first, extra]},
            {"races": [first, first], "details": [first]},
            {"races": [first], "details": [first, first]},
            {"races": [], "details": [first]},
        ]
        for source in invalid_pairs:
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "races/details identity mismatch"
            ):
                select_future(source, "jra", PLAN, NOW)

    def test_saved_prefetch_invalid_race_index_fails_closed(self):
        target = race("nar", 1)
        for malformed in (None, {}, [None], [{"id": ""}], [{"id": 1}]):
            source = {"races": malformed, "details": [target]}
            with self.subTest(index=malformed), self.assertRaisesRegex(
                ValueError, "race index invalid"
            ):
                select_future(source, "nar", PLAN, NOW)

    def test_keep_unscorable_preoff_in_forecast_cohort(self):
        row=race("nar",1)  # no horse history: separate research stage records blockers
        selected,_=select_future({"details":[row]},"nar",PLAN,NOW)
        self.assertEqual(selected,[row])

if __name__=="__main__": unittest.main()
