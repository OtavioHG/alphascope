from __future__ import annotations

from pathlib import Path

from alphascope.rust import compute_pct_returns, detect_volume_spikes, rust_backend_available


def test_rust_bindings_python_fallback_is_usable() -> None:
    returns = compute_pct_returns([100.0, 105.0, 102.9])
    spikes = detect_volume_spikes([1.0, 1.1, 1.2, 3.5], window=3, threshold=1.0)

    assert len(returns) == 3
    assert returns[0] == 0.0
    assert isinstance(rust_backend_available(), bool)
    assert spikes[-1] is True


def test_multilanguage_scaffold_files_exist() -> None:
    expected_paths = [
        Path("src/alphascope/rust/Cargo.toml"),
        Path("services/go/ingestion_service/main.go"),
        Path("research/julia/monte_carlo_simulation.jl"),
        Path("research/R/statistical_validation.R"),
        Path("sql/views/latest_strategy_health.sql"),
        Path("scripts/setup_environment.ps1"),
        Path("frontend/package.json"),
    ]
    for path in expected_paths:
        assert path.exists(), f"Missing scaffold file: {path}"
