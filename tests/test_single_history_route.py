"""Ensure no opt-in alternate history provider can be silently registered."""
import os
import unittest
from unittest.mock import patch

from arvexq.databanks.legacy_bridge import register_legacy_sources
from arvexq.databanks.registry import registry
from arvexq.ingest.fallback_enrichment import _validated_early_timing


class CanonicalHistoryRouteRegression(unittest.TestCase):
    def test_unapproved_optional_provider_configuration_is_ignored(self):
        with patch.dict(os.environ, {
            "ARVEXQ_AUTHORIZED_HISTORY_FEEDS_JSON": '[{"name":"shadow_history","circuit":"both","url":"https://example.com/data"}]'
        }):
            register_legacy_sources({})
        self.assertNotIn("shadow_history", registry.names())

    def test_existing_observed_timing_validation_remains(self):
        observed = {"sourceKind":"individual_sensor", "sourceRef":"official:horse:1",
                    "first200mSeconds": 13.4}
        self.assertEqual(_validated_early_timing(observed)["first200mSeconds"], 13.4)
        self.assertIsNone(_validated_early_timing({"sourceKind":"official_race_lap",
                                                    "sourceRef":"race:1","first200mSeconds":13.4}))


if __name__ == "__main__":
    unittest.main()
