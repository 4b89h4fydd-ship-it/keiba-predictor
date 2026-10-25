#!/usr/bin/env python3
"""Download a pinned Apache-2.0 RT-DETR model once for private offline inference.

This fetches ONLY publicly shared open model files from Hugging Face. It
never downloads race video, does not use remote code, and is not a license
waiver for video feeds. Subsequent video analysis loads local_files_only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MODEL_REPO = "PekingU/rtdetr_r50vd"
MODEL_REVISION = "df939e661d8c52e80608d1ec566561aabd25a4e7"
FILES = ("config.json", "preprocessor_config.json", "model.safetensors", "README.md")


def prepare_model(output_dir: str | Path, *, fetcher=None) -> Path:
    if fetcher is None:
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError("huggingface-hub needed for free open-model download") from exc
        fetcher = snapshot_download
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    fetcher(repo_id=MODEL_REPO, revision=MODEL_REVISION,
            allow_patterns=list(FILES), local_dir=str(directory))
    if any(not (directory / p).is_file() or not (directory / p).stat().st_size for p in FILES):
        raise ValueError("incomplete RT-DETR snapshot, no video inference permitted")
    model_card = (directory / "README.md").read_text(encoding="utf-8").lower()
    if "license: apache-2.0" not in model_card:
        raise ValueError("upstream model license is not Apache-2.0")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=".arvexq-data/vision-model")
    args = parser.parse_args(argv)
    path = prepare_model(args.output_dir)
    print("OPEN_VISION_MODEL_READY", MODEL_REPO, MODEL_REVISION, str(path))


if __name__ == "__main__":
    main()
