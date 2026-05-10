import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from alphascope.models.preprocessing import DataPreprocessor
import logging

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Trains and evaluates ML models for crypto price prediction.
    """
    
    def __init__(self, model_dir: str = "data/models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.preprocessor = DataPreprocessor()

    def train(self, df: pd.DataFrame, feature_cols: list):
        """
        Full training pipeline: Labeling -> Preprocessing -> Training -> Evaluation.
        """
        # 1. Labeling
        df_labeled = self.preprocessor.create_labels(df)
        
        # 2. Feature selection and scaling
        X, y = self.preprocessor.prepare_features(df_labeled, feature_cols)
        
        # 3. Temporal split
        X_train, X_test, y_train, y_test = self.preprocessor.temporal_split(X, y)
        
        # 4. Fit
        logger.info(f"Training model with {len(X_train)} samples...")
        self.model.fit(X_train, y_train)
        
        # 5. Evaluate
        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred)
        
        logger.info(f"Model Accuracy: {acc:.4f}")
        return acc, report

    def save_model(self, symbol: str):
        """
        Serializes the model and the scaler.
        """
        model_path = os.path.join(self.model_dir, f"{symbol.replace('/', '_')}_model.joblib")
        scaler_path = os.path.join(self.model_dir, f"{symbol.replace('/', '_')}_scaler.joblib")
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.preprocessor.scaler, scaler_path)
        logger.info(f"Model saved to {model_path}")

    def load_model(self, symbol: str):
        """
        Loads a serialized model and its scaler.
        """
        model_path = os.path.join(self.model_dir, f"{symbol.replace('/', '_')}_model.joblib")
        scaler_path = os.path.join(self.model_dir, f"{symbol.replace('/', '_')}_scaler.joblib")
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.model = joblib.load(model_path)
            self.preprocessor.scaler = joblib.load(scaler_path)
            return True
        return False
