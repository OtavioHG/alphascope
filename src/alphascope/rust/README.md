# AlphaScope Rust Extensions

This directory contains the Rust acceleration layer for AlphaScope.

Intended usage:

- heavy feature engineering
- anomaly detection
- signal mining
- large dataset processing
- backtest core acceleration

Python remains the orchestration layer. Rust is optional and accessed through PyO3 bindings compiled with `maturin`.

Expected build flow:

```bash
cd src/alphascope/rust
maturin develop --release
```
