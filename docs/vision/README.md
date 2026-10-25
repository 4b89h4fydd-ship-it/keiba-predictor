# ARVEXQ internal video analysis — free/open backend

The system now uses PekingU/rtdetr_r50vd (Apache-2.0) for the horse detector,
supervision.ByteTrack (MIT) for visual track IDs, and Tesseract (Apache-2.0)
for provisional saddlecloth OCR. It DOES NOT use Ultralytics, an AGPL model,
or a paid enterprise AI license. Follow each open source attribution license.

This **does not** grant rights to JRA or NAR race video. Commercial reuse and
automated acquisition of source footage must be independently authorized.

## Internal-only execution

The scheduled workflow is .github/workflows/arvexq-internal-vision.yml.
If an authorized feed is configured, it downloads the pinned and public
Apache-2.0 RT-DETR checkpoint directly from Hugging Face, caches it, then
processes approved race videos entirely within GitHub Actions. There is no
iPhone video UI. No third-party weightsUrl or commercial AI-license secret
is required.

Pinned model:
- Hugging Face: PekingU/rtdetr_r50vd
- Revision: df939e661d8c52e80608d1ec566561aabd25a4e7
- Files: model.safetensors, config.json, preprocessor_config.json, README.md
- License in model card must explicitly be Apache-2.0.
- No remote code execution: inference loads local_files_only=True.

Authorization inputs, when lawful racing footage becomes available:
- Secret ARVEXQ_VIDEO_FEED_URL: authorized HTTPS JSON batch
- Secret ARVEXQ_VIDEO_FEED_TOKEN: provider bearer token
- Variable ARVEXQ_VIDEO_ALLOWED_HOSTS: exact host allowlist

No ARVEXQ_ULTRALYTICS_LICENSE_VERIFIED secret is required.

Feed jobs need videoUrl, videoSha256 and config containing raceId, raceDate,
horseNumbers, official stable horse IDs, track, raceNumber, rightsVerified,
autoIdentifySaddlecloth, cameraCutsSeconds, and a separately reviewed
ground-plane homography for each camera segment.

The default nightly schedule is 02:30 JST; it reports
blocked-no-authorized-video-source if not configured, without inventing
analysis. Raw videos are not saved as project outputs. Compact movement
observations are matched to *earlier* races only, with strict race/horse
identity checks; missing or ambiguous identity is not guessed.

Manual test with an authorized local video:

    python -m pip install -r requirements-vision.txt
    python scripts/arvexq_fetch_open_vision_model.py --output-dir .arvexq-data/vision-model
    python scripts/arvexq_video_analyze.py --video race.mp4 --config race-video.json --weights .arvexq-data/vision-model --output race-evidence.json

No research video evidence is served in the iPhone-facing API. The current
backend has not yet passed real-race tracking accuracy or temporal
video-on/video-off betting ROI validation; results remain research-only and
do not automatically adjust production marks, probabilities or betting.

Note: free/open-source model licensing does not guarantee free compute.
GitHub Actions usage quotas, large files and video processing limits apply.


## Ground-truth accuracy evaluation (2026-10-25)

The public CC-licensed Vienna harness video is a **detector/tracker technical
check only**; it does not display JRA/NAR entry numbers and has not been
independently annotated with horse identities. Merely detecting 87 objects
across 32 frames is not detection accuracy, racehorse ID correctness, or
evidence of better Japanese racing predictions.

New: a benchmark comparing actual video detection boxes with separately
human-reviewed, frame-complete truth. It computes IoU-matched precision and
recall, global track identity F1 (IDF1-like), and **adjacent matched** identity
switch counts. Missing annotations always cause failure, not a zero or 100%
accuracy display.

Each real-video smoke run now archives the anonymous frame-level detection
boxes and a template for independent human annotation, **not** videos or
automatically assumed labels. The template deliberately declares
`reviewed: false`. It must never be used as truth without independently checking every
sampled frame including all missed horses, using stable identities for
the same horse across frames.

Example once actual reviewed annotations exist:

    python scripts/arvexq_vision_benchmark.py \
      --prediction .arvexq-data/vision-smoke-4hz.json \
      --truth approved-independent-ground-truth.json \
      --output .arvexq-data/vision-accuracy-audit.json

The reviewed truth JSON must include `videoSha256`, an annotation
attestation with method `independent-manual-review`,
`reviewed: true`, independent annotator and version, and
`usedModelPredictionsAsTruth: false`. It must include exactly
the same timestamps as the prediction's observedFrames. Each labelled horse
entry has the stable visual `horseId` and bounding box
`[x1,y1,x2,y2]`. Reported scores apply ONLY to that
reviewed clip and do not authorize deployment to live forecasts.
