from pathlib import Path
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAIRUSDT_ROOT = WORKSPACE_ROOT / "01_pairUSDT"
BACKEND_ROOT = WORKSPACE_ROOT / "02_backend"

for path in (WORKSPACE_ROOT, PAIRUSDT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
