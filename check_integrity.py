from pathlib import Path
import hashlib, json
root = Path(__file__).resolve().parent
manifest = json.loads((root / "checksums.json").read_text())
for name, expected in manifest.items():
    path = root / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"Integrity check failed: {name}")
print(f"PASS: {len(manifest)} archived inputs/results/scripts match preparation checksums")
