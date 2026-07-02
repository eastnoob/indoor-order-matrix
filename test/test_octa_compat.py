from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OCTA_SOURCE = ROOT / "OCTA_toolbox-master"
if str(OCTA_SOURCE) not in sys.path:
    sys.path.insert(0, str(OCTA_SOURCE))


def test_positions_legacy_random_pattern_alias():
    from octa.Positions import Positions

    assert Positions.CreateRandomPattern is Positions.CreateRandomPositions
