# ARVEXQ offline video detector — verified evidence only

This branch adds real video decoding and horse-class detection/tracking, **not**
validated race-horse recognition or live forecast integration.

## Run

Create a licensed local race video \`race.mp4\`, local horse-detection weights
\`horse-detector.pt\` (COCO horse class 17), and a reviewed configuration file.
Do **not** download or redistribute third-party footage without permission.

\`\`\`sh
python -m pip install -r requirements-vision.txt
python scripts/arvexq_video_analyze.py \
  --video race.mp4 \
  --weights horse-detector.pt \
  --config race-video.json \
  --output race-evidence.json
\`\`\`

Example \`race-video.json\` (the horse tracker IDs are **illustrative only**;
a reviewer must replace the identity mappings with actual verified footage
evidence before claiming horse-level observations):

\`\`\`json
{
  "raceId": "nar-2026-10-25-園田-01",
  "raceDate": "2026-10-25",
  "rightsVerified": true,
  "horseNumbers": [1, 2, 3],
  "cameraCutsSeconds": [14.4, 38.0],
  "sampleEveryNFrames": 1,
  "calibration": {
    "reviewed": true,
    "coordinateSystem": "ground-plane-meters",
    "source": "surveyed reference points independently confirmed for each source camera",
    "homography": [[1,0,0],[0,1,0],[0,0,1]]
  },
  "verifiedIdentityMap": {
    "camera-0": {
      "7": {"horseNumber": 1, "verified": true, "evidence": "human-reviewed saddlecloth"},
      "9": {"horseNumber": 2, "verified": true, "evidence": "human-reviewed saddlecloth"}
    }
  }
}
\`\`\`

**Important:** identity IDs above and the identity homography are placeholders,
NOT usable horse observations; ground-plane calibration MUST use measured
control points in actual metres. The current processor assumes **one reviewed
homography** applies to all camera segments. Footage that switches viewpoints
must first be split into uniform-camera clips or use an explicit reviewed
per-camera transform in a future implementation. Declared camera cuts ensure
tracks are never interpolated across camera transitions.

The recorded tracking source includes SHA256 checksums for the actual video
and model weights. Unknown tracker IDs remain unassigned, as do horses hidden
from the camera. The output records provenance, coverage, observed motion,
unidentified detections, and does not claim to detect causal interference.
No forecast marks or buy tickets are changed by this command.

## Acceptance before using it for prediction

- Independent truth-labelled video sample: per-horse detection recall,
  tracker ID switches, and coverage by race and by camera.
- Checked calibration and pace/position alignment against official sectional
  and track records where available.
- Date-split central and local forecasting tests, video-on vs video-off,
  showing \`◎\` win/top-3 calibration and **actual payout-based** trio and
  trifecta return with missing source disclosures.
- Only promote genuinely observed and statistically useful features. An
  inferred event is never labelled as observed, and no unverified revenue
  improvement is reported.
