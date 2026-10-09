"""Download the exact GSM8K/MATH sources used by FlowEvo, with local exports."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "datasets"
SOURCES = {
    "gsm8k": {
        "repo_id": "openai/gsm8k",
        "revision": "740312add88f781978c0658806c59bc2815b9866",
        "configs": ["main"],
        "expected": {"train": 7473, "test": 1319},
    },
    "math": {
        "repo_id": "EleutherAI/hendrycks_math",
        "revision": "21a5633873b6a120296cce3e2df9d5550074f4a3",
        "configs": [
            "algebra", "counting_and_probability", "geometry",
            "intermediate_algebra", "number_theory", "prealgebra", "precalculus",
        ],
        "expected": {"train": 7500, "test": 5000},
    },
}


def main() -> None:
    manifest = {
        "downloaded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "datasets": {},
    }
    for name, source in SOURCES.items():
        destination = DATA_DIR / name
        print(f"Downloading {source['repo_id']} @ {source['revision']}", flush=True)
        snapshot_download(
            repo_id=source["repo_id"], repo_type="dataset",
            revision=source["revision"], local_dir=destination / "raw",
            allow_patterns=["README.md", "*.yaml"] + [
                f"{config}/*.parquet" for config in source["configs"]
            ],
            max_workers=4,
        )
        info = {**source, "url": f"https://huggingface.co/datasets/{source['repo_id']}",
                "splits": {}, "files": []}
        for split in ("train", "test"):
            count = 0
            category_counts = {}
            export = destination / f"{split}.jsonl"
            temporary = export.with_suffix(".jsonl.tmp")
            with temporary.open("w", encoding="utf-8") as out:
                for config in source["configs"]:
                    files = sorted((destination / "raw" / config).glob(f"{split}-*.parquet"))
                    if not files:
                        raise RuntimeError(f"Missing {name}/{config}/{split}")
                    category_counts[config] = 0
                    for file in files:
                        rows = pq.read_table(file).to_pylist()
                        for row in rows:
                            out.write(json.dumps(row, ensure_ascii=False) + "\n")
                        count += len(rows)
                        category_counts[config] += len(rows)
                        info["files"].append({
                            "path": str(file.relative_to(DATA_DIR)),
                            "rows": len(rows), "bytes": file.stat().st_size,
                            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                        })
            if count != source["expected"][split]:
                raise RuntimeError(f"Unexpected {name}/{split} count: {count}")
            temporary.replace(export)
            info["splits"][split] = {
                "rows": count, "categories": category_counts,
                "jsonl": str(export.relative_to(DATA_DIR)),
                "sha256": hashlib.sha256(export.read_bytes()).hexdigest(),
            }
            print(f"  {name}/{split}: {count} rows -> {export}", flush=True)
        manifest["datasets"][name] = info
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Verified datasets; manifest: {DATA_DIR / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
