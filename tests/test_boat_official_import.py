"""Offline official B/K integration; no invented boats, prices or forecasts."""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import patch

from scripts.arvexq_boat_official import official_day_record
from scripts.arvexq_boat_ingest import ingest_personal_official

DAY=date(2026,10,12)
JST=timezone(timedelta(hours=9))
when=lambda hh,mm: datetime(2026,10,12,hh,mm,tzinfo=JST)

def fixture():
    race=Obj(venue_code="01",race_number=1,race_date=DAY,race_name="予選")
    athletes=[Obj(racer_number=4000+i,name="公式選手"+str(i),
                  racer_class="A1",age=29,weight=52,branch="東京")
              for i in range(1,7)]
    starters=[Obj(venue_code="01",race_number=1,boat_number=i,
                  racer_number=4000+i,motor_number=10+i,boat_part=20+i)
              for i in range(1,7)]
    schedule=Obj(races=[race],racers=athletes,entries=starters)
    times=[Obj(venue_code="01",race_number=1,race_name="予選",
               close_time=when(10,38))]
    return schedule,times

class OfficialBoatDayTests(unittest.TestCase):
    def test_six_official_entrants_and_real_closing_time(self):
        sched,times=fixture()
        day=official_day_record(DAY,sched,times,observed_at=when(9,30))
        self.assertEqual(len(day["races"]),1)
        race=day["races"][0]
        self.assertEqual(race["venue"],"桐生")
        self.assertEqual(race["closeTime"],"10:38")
        self.assertEqual([x["boatNo"] for x in race["entries"]],list(range(1,7)))
        self.assertEqual(race["entries"][5]["player"]["racerNumber"],4006)
        self.assertEqual(race["entries"][5]["motor"]["number"],16)
        self.assertNotIn("forecast",race)
        self.assertNotIn("odds3t",race)
        self.assertNotIn("result",race)
        self.assertTrue(day["personalOnly"])

    def test_partial_program_never_relabels_5_boats_as_6(self):
        sched,times=fixture()
        sched.entries.pop()
        with self.assertRaisesRegex(ValueError,"No complete official B"):
            official_day_record(DAY,sched,times,observed_at=when(9,30))

    def test_missing_official_closing_time_not_guessed(self):
        sched,_=fixture()
        with self.assertRaisesRegex(ValueError,"No complete official B"):
            official_day_record(DAY,sched,[],observed_at=when(9,30))

    def test_official_k_matches_finish_and_payout(self):
        sched,times=fixture()
        ordered=[2,1,3]
        observations=[Obj(venue_code="01",race_number=1,result_position=i,
                          boat_number=n,exhibition_time=6.73,st_timing=.15)
                      for i,n in enumerate(ordered,1)]
        performance=Obj(entries=observations,payouts=[
            Obj(venue_code="01",race_number=1,ticket_type="sanrensho",
                winning_combination="2-1-3",payout=5210)])
        day=official_day_record(DAY,sched,times,performance,when(11,0))
        race=day["races"][0]
        self.assertEqual(race["result"]["trifecta"],"2-1-3")
        self.assertEqual(race["result"]["trifectaPayoutYen"],5210)
        self.assertEqual(race["result"]["timestampMeaning"],"observed-from-official-K")
        self.assertNotIn("odds3t",race)

    def test_mismatched_K_cannot_publish_a_fake_result(self):
        sched,times=fixture()
        perf=Obj(entries=[
            Obj(venue_code="01",race_number=1,boat_number=n,result_position=i,
                exhibition_time=None,st_timing=None)
            for i,n in enumerate([2,1,3],1)],
            payouts=[Obj(venue_code="01",race_number=1,ticket_type="sanrensho",
                         winning_combination="1-2-3",payout=1200)])
        day=official_day_record(DAY,sched,times,perf,when(11,0))
        self.assertNotEqual(day["races"][0].get("result",{}).get("status"),"confirmed")

    def test_public_export_requires_authentication_review(self):
        day=official_day_record(DAY,*fixture(),observed_at=when(9,30))
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ,{"ARVEXQ_BOAT_PRIVATE_ACCESS_VERIFIED":"0"}):
                with self.assertRaises(PermissionError):
                    ingest_personal_official(day,DAY.isoformat(),Path(temp))
            self.assertFalse(list(Path(temp).glob("*.json")))

    def test_private_export_is_atomic_and_idempotent(self):
        day=official_day_record(DAY,*fixture(),observed_at=when(9,30))
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ,{"ARVEXQ_BOAT_PRIVATE_ACCESS_VERIFIED":"1"}):
                path,yes=ingest_personal_official(day,DAY.isoformat(),Path(temp))
                self.assertTrue(yes)
                self.assertFalse(ingest_personal_official(day,DAY.isoformat(),Path(temp))[1])
                self.assertEqual(__import__("json").loads(path.read_text())["races"][0]["entries"][0]["name"],"公式選手1")

if __name__=="__main__":unittest.main()
