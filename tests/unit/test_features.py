import pandas as pd
import numpy as np
import pytest
from alphascope.features.technical import TechnicalFeatures

def test_calculate_all_features():
    # Create mock candle data
    data = {
        "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109] * 10,
        "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110] * 10,
        "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108] * 10,
        "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5] * 10,
        "volume": [1000] * 100
    }
    df = pd.DataFrame(data)
    
    result_df = TechnicalFeatures.calculate_all(df)
    
    assert "rsi" in result_df.columns
    assert "macd" in result_df.columns
    assert "bb_upper" in result_df.columns
    assert "pct_return" in result_df.columns
    assert "volatility" in result_df.columns
    assert "relative_volume" in result_df.columns
    
def test_clean_dataframe():
    df = pd.DataFrame({
        "a": [1, 2, np.nan],
        "b": [4, np.nan, 6]
    })
    cleaned = TechnicalFeatures.clean_dataframe(df)
    assert len(cleaned) == 1
    assert not cleaned.isnull().values.any()
