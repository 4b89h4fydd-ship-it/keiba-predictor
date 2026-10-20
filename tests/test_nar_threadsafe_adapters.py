"""Concurrent official NAR history must never share a sqlite connection."""
from __future__ import annotations
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from arvexq.databanks.legacy_bridge import _nar_store_adapters


class NarThreadsafeAdaptersTest(unittest.TestCase):
    def test_nar_store_connection_is_private_per_worker(self):
        created = []
        mutex = threading.Lock()
        class FakeNarStore:
            def __init__(self):
                self.conn = sqlite3.connect(":memory:")  # default check_same_thread=True
                self.owner = threading.get_ident()
                with mutex:
                    created.append(self.owner)
            def recent_races(self, name, date, limit, expected_age=0, expected_sex=""):
                self.last_identity=(expected_age,expected_sex)
                self.conn.execute("SELECT 1").fetchone()
                return [{"date":"2026-09-01","horse":name}][:limit]
            def prize_before(self, name, date):
                return self.conn.execute("SELECT 13").fetchone()[0]
            def stats(self, kind, name, date):
                return {"count":self.conn.execute("SELECT 1").fetchone()[0]}
            def role_profile(self, *args):
                return {"value":self.conn.execute("SELECT 2").fetchone()[0]}

        history, connections = _nar_store_adapters({"NarStore":FakeNarStore})
        race={"date":"2026-10-11","track":"盛岡","distance":1000}
        horse={"name":"確認馬","jockey":"騎手A","trainer":"調教師A"}

        # Explicitly seed the adapter from the caller thread; old global cache
        # then fails in each worker with SQLite's cross-thread ProgrammingError.
        self.assertEqual(history(horse,race,limit=100)["prizeMoneyAtRace"],13)
        self.assertEqual(len(created),1)
        barrier = threading.Barrier(3)
        def inspect():
            barrier.wait(timeout=5)
            found=history(horse,race,limit=100)
            roles=connections(horse,race)
            return threading.get_ident(),found,roles
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(inspect) for _ in range(2)]
            barrier.wait(timeout=5)
            rows=[f.result(timeout=10) for f in futures]
        self.assertEqual(len(created),3)
        self.assertEqual(len(set(created)),3)
        for thread_id, found, roles in rows:
            self.assertIn(thread_id,created)
            self.assertEqual(found["allPastRuns"][0]["date"],"2026-09-01")
            self.assertEqual(roles["jockeyStats"]["count"],1)
            self.assertEqual(roles["trainerProfile"]["value"],2)


    def test_career_adapter_forwards_same_name_identity(self):
        calls=[]
        class IdentityStore:
            def recent_races(self, name, date, limit, expected_age=0, expected_sex=""):
                calls.append((name,date,limit,expected_age,expected_sex))
                return [{"date":"2025-09-03","finish":2}] if expected_age==3 and expected_sex=="牝" else []
            def prize_before(self,name,date):
                return 0
        history,_=_nar_store_adapters({"NarStore":IdentityStore})
        race={"date":"2026-10-16","track":"園田","circuit":"地方"}
        horse={"name":"同名馬","age":"牝3","sex":"牝"}
        result=history(horse,race,100)
        self.assertEqual(len(result["allPastRuns"]),1)
        self.assertEqual(calls,[("同名馬","2026-10-16",100,3,"牝")])
        self.assertEqual(history({"name":"同名馬","age":4,"sex":"牡"},race,100)["allPastRuns"],[])


if __name__ == "__main__":
    unittest.main()
