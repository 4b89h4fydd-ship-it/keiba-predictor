# ARVEXQ offline video detector — verified evidence only

This branch adds real video decoding and horse-class detection/tracking, **not**
validated race-horse recognition or live forecast integration.

## Run

Create a licensed local race video `race.mp4`, local horse-detection weights
`horse-detector.pt` (COCO horse class 17), and a reviewed configuration file.
Do **not** download or redistribute third-party footage without permission.

```sh
python -m pip install -r requirements-vision.txt
python scripts/arvexq_video_analyze.py \
  --video race.mp4 \
  --weights horse-detector.pt \
  --config race-video.json \
  --output race-evidence.json
```

Example `race-video.json` (the horse tracker IDs are **illustrative only**;
a reviewer must replace the identity mappings with actual verified footage
evidence before claiming horse-level observations):

```json
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
    "homographies": {
      "camera-0": [[1,0,0],[0,1,0],[0,0,1]],
      "camera-1": [[1,0,0],[0,1,0],[0,0,1]],
      "camera-2": [[1,0,0],[0,1,0],[0,0,1]]
    }
  },
  "verifiedIdentityMap": {
    "camera-0": {
      "7": {"horseNumber": 1, "verified": true, "evidence": "human-reviewed saddlecloth"},
      "9": {"horseNumber": 2, "verified": true, "evidence": "human-reviewed saddlecloth"}
    }
  }
}
```

**Important:** identity IDs above and the identity homography are placeholders,
NOT usable horse observations; ground-plane calibration MUST use measured
control points in actual metres. The processor requires **one independently reviewed homography for each
camera segment** when the footage changes viewpoints. The matrix shown above
is deliberately a placeholder, not valid course calibration. If a camera
switch occurs without a corresponding measured matrix, the analysis rejects
the input. Declared camera cuts also ensure tracks are never interpolated
across camera transitions.

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
  showing `◎` win/top-3 calibration and **actual payout-based** trio and
  trifecta return with missing source disclosures.
- Only promote genuinely observed and statistically useful features. An
  inferred event is never labelled as observed, and no unverified revenue
  improvement is reported.


## Internal automatic job (no iPhone video UI)

The GitHub Actions workflow [ARVEXQ Internal Video Analysis](../../.github/workflows/arvexq-internal-vision.yml)
is scheduled daily at 02:30 JST. It is **research-only**, does not
modify the current published mark/forecast engine, and records
`blocked-no-authorized-video-source` when the provider is absent.

Required private GitHub Actions configuration:

- Secret `ARVEXQ_VIDEO_FEED_URL`: HTTPS URL of an authorized race-video feed
  listing actual licensed past video and model locations
- Secret `ARVEXQ_VIDEO_FEED_TOKEN`: bearer token for that provider
- Repository variable `ARVEXQ_VIDEO_ALLOWED_HOSTS`: a comma-separated
  exact allowlist for feed, video, and model URLs

Feed response (schema only; **not real or accessible media**):

```json
{
  "jobs": [{
    "videoUrl": "https://approved.example/video.mp4",
    "videoSha256": "64 lowercase sha256 hex digits",
    "weightsUrl": "https://approved.example/model.pt",
    "weightsSha256": "64 lowercase sha256 hex digits",
    "config": {
      "raceId": "nar-2026-10-24-園田-01",
      "raceDate": "2026-10-24",
      "track": "園田",
      "raceNumber": 1,
      "rightsVerified": true,
      "autoIdentifySaddlecloth": true,
      "horseNumbers": [1, 2, 3],
      "horseIdentityByNumber": {"1": "stable-official-horse-id-1"},
      "cameraCutsSeconds": [],
      "calibration": {
        "reviewed": true,
        "coordinateSystem": "ground-plane-meters",
        "source": "surveyed points",
        "homography": [[1,0,0],[0,1,0],[0,0,1]]
      }
    }
  }]
}
```

The `horseIdentityByNumber` example is intentionally incomplete and would
be rejected: every declared runner needs its real stable official horse ID.
The identity matrix is also an invalid example of real surveyed calibration.
Configure genuine data before expecting the job to process any races.

The job uses real video and YOLO horse detections, and optionally
`pytesseract` to OCR saddlecloth digits. Automatic OCR assignments are
classified as **provisional**, not independently validated identities.
Consensus requires at least three frames. Unknown horses/camera sections
are not guessed. Video rights, frame calibration and SHA checks are mandatory.

The job stores compact research facts, **not original videos**. An immutable
cache is restored during Full Prefetch under `ARVEXQ_VISION_EVIDENCE_DIR`;
only the exact older race, date, track, race number and stable horse ID may
attach the evidence to a later entry. Neither the past race result nor
future video can alter a pre-race forecast. Without compatible official
identifiers this connection reports zero coverage rather than inventing a join.

**Limits:** GitHub Actions caches are not a permanent dataset and may expire.
The current shared video features remain research-only until a separately
date-held-out, verified accuracy/ROI comparison approves their learned
influence on production marks and betting. No app screens for video are added.
