from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Legacy phase tests exercise modules intentionally moved to src/alphascope/legacy.
collect_ignore = [
    str(ROOT / "tests" / "integration" / "test_phase3_pipeline.py"),
    str(ROOT / "tests" / "integration" / "test_phase4_pipeline.py"),
    str(ROOT / "tests" / "integration" / "test_phase8_pipeline.py"),
    str(ROOT / "tests" / "integration" / "test_phase9_continuous_research.py"),
    str(ROOT / "tests" / "unit" / "test_features.py"),
    str(ROOT / "tests" / "unit" / "test_phase1.py"),
    str(ROOT / "tests" / "unit" / "test_phase3_ranking_backtest.py"),
    str(ROOT / "tests" / "unit" / "test_phase4_trading.py"),
    str(ROOT / "tests" / "unit" / "test_phase6_quant.py"),
    str(ROOT / "tests" / "unit" / "test_phase7_storage.py"),
    str(ROOT / "tests" / "unit" / "test_phase8_discovery.py"),
    str(ROOT / "tests" / "unit" / "test_phase9_evolution.py"),
    str(ROOT / "tests" / "unit" / "test_platform_upgrades.py"),
]
