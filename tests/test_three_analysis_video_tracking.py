"""Identity and geometry gates for internal video metrics (no footage UI)."""
import unittest
from arvexq.forecast.video_tracking import features_from_verified_tracks


class TrackingPrivacyAndGeometryTests(unittest.TestCase):
    def setUp(self):
        self.source={"tracks":{1:[
            {"frame":0,"time":0.0,"pixelFoot":[0,0]},
            {"frame":1,"time":1.0,"pixelFoot":[3,0]},
            {"frame":2,"time":2.0,"pixelFoot":[6,0]},
        ]}}
        self.H={n:[[1,0,0],[0,1,0],[0,0,1]] for n in (0,1,2)}

    def test_verified_stable_id_and_distance(self):
        out=features_from_verified_tracks(self.source,identities={1:{"horseId":"101","verified":True}},
            homographies=self.H,race_date="2026-10-20",source="licensed-clip",
            ideal_paths={"101":5.0},expected_horse_ids=["101"])
        self.assertEqual(out["101"]["meanSpeedMps"],3.0)
        self.assertEqual(out["101"]["idealPathExcessMeters"],1.0)
        self.assertTrue(out["101"]["identityVerified"])

    def test_unverified_id_does_not_become_claimed_video_evidence(self):
        with self.assertRaises(ValueError):
            features_from_verified_tracks(self.source,identities={1:{"horseId":"101","verified":False}},
                homographies=self.H,race_date="2026-10-20",source="licensed-clip",
                expected_horse_ids=["101"])

    def test_missing_camera_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            features_from_verified_tracks(self.source,identities={1:{"horseId":"101","verified":True}},
                homographies={0:self.H[0]},race_date="2026-10-20",source="licensed-clip")


if __name__=="__main__":
    unittest.main()
