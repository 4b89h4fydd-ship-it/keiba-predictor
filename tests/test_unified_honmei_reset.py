"""Regression guard for the unified honmei on the isolated reset branch."""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from arvexq.prediction.observed_model import apply_observed_marks
from test_unified_jra_nar_observed_authority import race


class UnifiedHonmeiRegression(TestCase):
    def test_win_and_place_axis_are_same_horse(self):
        for circuit in ('中央','地方'):
            with self.subTest(circuit=circuit):
                source=race(circuit);before=deepcopy(source['horses'])
                detail=apply_observed_marks(source)
                self.assertEqual(detail['predictionStatus'],'disabled')
                self.assertEqual(detail['horses'],before)
                self.assertNotIn('honmeiDecision',detail)
