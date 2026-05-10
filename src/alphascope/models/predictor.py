import pandas as pd
import numpy as np
from alphascope.models.trainer import ModelTrainer
import logging

logger = logging.getLogger(__name__)

class SignalPredictor:
    """
    Uses trained models to generate real-time trading signals.
    """
    
    def __init__(self, model_dir: str = "data/models"):
        self.trainer = ModelTrainer(model_dir)

    def predict_signal(self, symbol: str, current_features_df: pd.DataFrame, feature_cols: list) -> dict:
        """
        Generates a Buy (1), Sell (0) or Neutral signal based on current features.
        """
        if not self.trainer.load_model(symbol):
            return {"symbol": symbol, "signal": "no_model", "confidence": 0.0}
            
        # Scaling current features
        X = current_features_df[feature_cols].values
        X_scaled = self.trainer.preprocessor.scaler.transform(X)
        
        # Prediction
        prediction = self.trainer.model.predict(X_scaled)[-1]  # Get last prediction
        probabilities = self.trainer.model.predict_proba(X_scaled)[-1]
        
        confidence = probabilities[prediction]
        
        signal_map = {1: "BUY", 0: "SELL"}
        return {
            "symbol": symbol,
            "signal": signal_map.get(prediction),
            "confidence": float(confidence),
            "timestamp": pd.Timestamp.now()
        }
