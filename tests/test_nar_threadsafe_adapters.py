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
            def recent_races(self, name, date, limit):
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


if __name__ == "__main__":
    unittest.main()
