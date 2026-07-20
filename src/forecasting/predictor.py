import joblib
import pandas as pd
from datetime import datetime, UTC
from .config import MODEL_FEATURES, PRODUCTION_MODEL_PATH

def load_model():
  production_model = joblib.load(PRODUCTION_MODEL_PATH)
  return production_model

def prepare_features(df):
  X = df[MODEL_FEATURES]
  return X

def predict(model, X):
  predictions = model.predict(X)
  return predictions

def create_forecast_df(df, predictions):

    forecast_df = df[["timestamp"]].copy()
    forecast_df.rename(
        columns={
            "timestamp": "forecast_timestamp"
        },
        inplace=True
    )

    forecast_df["predicted_generation_mw"] = predictions
    forecast_df["forecast_created_at"] = datetime.now(UTC)
    forecast_df["model_name"] = "Ridge Regression"
    forecast_df["model_version"] = "v1.0"

    forecast_df = forecast_df[
    [
        "forecast_created_at",
        "forecast_timestamp",
        "predicted_generation_mw",
        "model_name",
        "model_version"
    ]
]
    return forecast_df

def run_prediction(df):
    model = load_model()

    X = df.drop(columns=["timestamp"]).copy()
    X = X.loc[:, model.feature_names_in_]

    predictions = predict(model, X)

    return create_forecast_df(df, predictions)