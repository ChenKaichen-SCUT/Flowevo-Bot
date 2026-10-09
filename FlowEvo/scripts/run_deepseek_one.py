"""Run one official FlowEvo `ours` GSM8K example using ../miyao.txt."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    key = (root.parent / "miyao.txt").read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("miyao.txt is empty")
    env["OPENROUTER_API_KEY"] = key
    env["HF_HUB_OFFLINE"] = "1"
    env["HF_DATASETS_OFFLINE"] = "1"
    env["FLOWEVO_DATASET_DIR"] = str(root / "data" / "datasets")
    env["PYTHONUNBUFFERED"] = "1"
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S_%f")
    out = root / "runs" / f"deepseek_gsm8k_one_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable, "-u", "-m", "src.code_math.runner",
        "--benchmark", "gsm8k", "--limit", "1",
        "--config-path", "configs/deepseek.yaml",
        "--conditions", "ours", "--output-dir", str(out),
    ]
    print(f"Output directory: {out}", flush=True)
    with (out / "run.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command, cwd=root, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
        )
        for line in process.stdout:
            line = line.replace(key, "[REDACTED_API_KEY]")
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
        status = process.wait()
    if status:
        return status
    # The upstream runner can exit successfully even when an episode failed.
    summary = json.loads((out / "summary.json").read_text())
    passed = summary["gsm8k"]["ours"]
    return 0 if passed["n"] == 1 and passed["passed"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
