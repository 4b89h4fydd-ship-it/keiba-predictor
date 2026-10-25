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
