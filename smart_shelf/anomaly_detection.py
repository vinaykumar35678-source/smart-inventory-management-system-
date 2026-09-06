"""
anomaly_detection.py — Predictive AI for Stockouts and Theft Detection
Uses Scikit-Learn's IsolationForest to detect anomalous removal behavior.
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import IsolationForest

CSV_PATH = os.path.join(os.path.dirname(__file__), "inventory.csv")

class InventoryAnomalyDetector:
    def __init__(self, contamination=0.05):
        """
        contamination: The proportion of outliers in the data set (expected theft rate).
        """
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.is_fitted = False

    def train(self):
        """Train the Isolation Forest on historical CSV data."""
        if not os.path.exists(CSV_PATH):
            return False

        try:
            df = pd.read_csv(CSV_PATH)
            # Only analyze removal events
            df_removals = df[df["Event_Type"] == "REMOVAL"].copy()
            if len(df_removals) < 10:
                return False  # Not enough data to train reliably
            
            # Feature extraction
            # We look at quantity removed. In a real time-series, we would also look at time elapsed since last removal.
            df_removals['Timestamp'] = pd.to_datetime(df_removals['Timestamp'])
            df_removals = df_removals.sort_values(by=['Product', 'Timestamp'])
            
            # Calculate time difference in seconds between removals of the same product
            df_removals['Time_Diff_Sec'] = df_removals.groupby('Product')['Timestamp'].diff().dt.total_seconds()
            df_removals['Time_Diff_Sec'] = df_removals['Time_Diff_Sec'].fillna(3600) # Default to 1 hour for first removal

            # Features: [Quantity, Time_Diff_Sec]
            # Rapid removal of high quantities is anomalous
            X = df_removals[['Quantity', 'Time_Diff_Sec']].values
            
            self.model.fit(X)
            self.is_fitted = True
            return True
        except Exception as e:
            print(f"[Anomaly Detection] Training error: {e}")
            return False

    def is_anomalous(self, product_name: str, quantity: int, time_since_last_removal_sec: float) -> bool:
        """
        Predict if a current transaction is anomalous.
        Returns True if suspected theft/anomaly, False otherwise.
        """
        if not self.is_fitted:
            # Try to train first
            success = self.train()
            if not success:
                # Fallback heuristic if ML model can't be trained yet
                return quantity >= 3 and time_since_last_removal_sec < 10.0

        # Predict using Isolation Forest (-1 for outlier, 1 for inlier)
        X_test = np.array([[quantity, time_since_last_removal_sec]])
        prediction = self.model.predict(X_test)[0]
        
        return prediction == -1

# Global singleton
detector = InventoryAnomalyDetector()
