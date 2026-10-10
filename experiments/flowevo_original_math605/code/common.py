from pathlib import Path
import json, hashlib, datetime, sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / 'experiments/aflow_math617_capability_probe'
sys.path.insert(0, str(ROOT / 'FlowEvo/src'))

def read(path):
    return json.loads(Path(path).read_text())

def jl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(path, value):
    path = Path(path)
    if not path.is_absolute():
        path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)

def lines(path, rows):
    path = Path(path)
    if not path.is_absolute():
        path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
