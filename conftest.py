from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
OCTA_SOURCE = PROJECT_ROOT / "OCTA_toolbox-master"

if str(OCTA_SOURCE) not in sys.path:
    sys.path.insert(0, str(OCTA_SOURCE))


def pytest_sessionstart(session):
    os.chdir(PROJECT_ROOT)


def pytest_collectreport(report):
    os.chdir(PROJECT_ROOT)
