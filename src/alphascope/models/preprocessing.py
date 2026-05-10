import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List

class DataPreprocessor:
    """
    Handles data labeling, feature selection, and temporal splitting.
    """
    
    def __init__(self, target_col: str = "target", horizon: int = 4):
        self.target_col = target_col
        self.horizon = horizon  # Number of periods ahead to predict
        self.scaler = StandardScaler()

    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates a binary label: 1 if close price increases after 'horizon' periods, 0 otherwise.
        """
        df = df.sort_values("timestamp")
        # Calculate future return
        df["future_close"] = df["close"].shift(-self.horizon)
        df["future_return"] = (df["future_close"] - df["close"]) / df["close"]
        
        # Binary target: 1 if return > 0 (or a threshold like 0.005)
        df[self.target_col] = (df["future_return"] > 0).astype(int)
        
        # Drop last rows where we don't have future data
        return df.dropna(subset=["future_close"])

    def prepare_features(self, df: pd.DataFrame, feature_cols: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts features and target, applies scaling.
        """
        X = df[feature_cols].values
        y = df[self.target_col].values
        
        X_scaled = self.scaler.fit_transform(X)
        return X_scaled, y

    def temporal_split(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> Tuple:
        """
        Splits data without shuffling to respect time series order.
        """
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        return X_train, X_test, y_train, y_test
