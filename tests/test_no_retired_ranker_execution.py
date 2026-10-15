"""The retired v207/v212 ranker must never run for either racing circuit."""
import unittest
from unittest.mock import patch

from arvexq.domain import legacy_evaluation


class NoRetiredRankerExecution(unittest.TestCase):
    def test_circuit_specific_authority_ignores_old_ranker(self):
        executed = []
        def current(detail):
            executed.append(detail["circuit"])
            detail["authority"] = "current-only"
            return detail
        with patch.object(
            legacy_evaluation, "SOURCE",
            "def _rank_evaluations(detail):\n"
            "    raise AssertionError('retired legacy ranker was executed')\n"
        ), patch("arvexq.prediction.final_marks.apply_core_marks", side_effect=current):
            namespace = {}
            legacy_evaluation.install_evaluation_core(namespace)
            for circuit in ("地方", "中央"):
                d = {"circuit": circuit}
                self.assertIs(namespace["_rank_evaluations"](d), d)
                self.assertEqual(d["authority"], "current-only")
        self.assertEqual(executed, ["地方", "中央"])


if __name__ == "__main__":
    unittest.main()
