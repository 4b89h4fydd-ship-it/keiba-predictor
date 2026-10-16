"""Compressed histories cannot bypass the active model's source restrictions."""
import copy
import unittest
from tests.test_unified_jra_nar_observed_authority import race
from arvexq.ingest.career_transport import pack_horse
from arvexq.prediction.observed_model import rank_jra, _history_rates

class ArchiveScopeTests(unittest.TestCase):
    def test_scoped_history_cannot_resurrect_unverified_margins(self):
        d = race("中央")
        for h in d["horses"]:
            # One official run plus many unverified margins in the sidecar.
            for q in h["recentRaces"][1:]:
                q.pop("marginEvidence")
                q["marginSeconds"] = 9.0
        plain = rank_jra(copy.deepcopy(d["horses"]), d)
        packed = [pack_horse(h, d["date"]) for h in d["horses"]]
        archived = rank_jra(packed, d)
        self.assertEqual([r["score"] for r in plain], [r["score"] for r in archived])
        self.assertTrue(all(r["sample"] == 1 for r in archived))

    def test_flat_career_rates_cannot_restore_archived_jump_start(self):
        d = race("中央")
        h = d["horses"][0]
        jump = dict(h["recentRaces"][0], date="2026-08-01", surface="障害", finish=1)
        h["allPastRuns"] = h["recentRaces"] + [jump]
        packed = pack_horse(h, d["date"])
        self.assertEqual(_history_rates(packed, d)["starts"], 5)
        self.assertEqual(_history_rates(packed, d)["winRate"], 2/5)
