from pathlib import Path
import sys


PAIRUSDT_ROOT = Path(__file__).resolve().parents[1]

if str(PAIRUSDT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAIRUSDT_ROOT))
