use pyo3::prelude::*;

#[pyfunction]
fn compute_pct_returns(values: Vec<f64>) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    let mut result = vec![0.0];
    for pair in values.windows(2) {
        let previous = pair[0];
        let current = pair[1];
        let value = if previous == 0.0 { 0.0 } else { (current / previous) - 1.0 };
        result.push(value);
    }
    result
}

#[pyfunction]
fn rolling_zscore(values: Vec<f64>, window: usize) -> Vec<f64> {
    let mut result = Vec::with_capacity(values.len());
    for index in 0..values.len() {
        let start = if index + 1 >= window { index + 1 - window } else { 0 };
        let slice = &values[start..=index];
        let mean = slice.iter().sum::<f64>() / slice.len() as f64;
        let variance = slice
            .iter()
            .map(|value| {
                let diff = value - mean;
                diff * diff
            })
            .sum::<f64>()
            / slice.len() as f64;
        let std = variance.sqrt();
        let score = if std == 0.0 { 0.0 } else { (values[index] - mean) / std };
        result.push(score);
    }
    result
}

#[pymodule]
fn alphascope_rust(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(compute_pct_returns, module)?)?;
    module.add_function(wrap_pyfunction!(rolling_zscore, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{compute_pct_returns, rolling_zscore};

    #[test]
    fn compute_pct_returns_handles_basic_series() {
        let result = compute_pct_returns(vec![100.0, 110.0, 99.0]);
        assert_eq!(result.len(), 3);
        assert_eq!(result[0], 0.0);
        assert!((result[1] - 0.10).abs() < 1e-9);
        assert!((result[2] + 0.10).abs() < 1e-9);
    }

    #[test]
    fn rolling_zscore_handles_zero_window_like_singletons() {
        let result = rolling_zscore(vec![1.0, 1.0, 1.0], 1);
        assert_eq!(result, vec![0.0, 0.0, 0.0]);
    }
}
