import joblib
import pandas as pd
from config import MODEL_FEATURES, PRODUCTION_MODEL_PATH

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
  forecast_df["predicted_generation_mw"] = predictions
  return forecast_df

def run_prediction(df):
  model = load_model()
  X = prepare_features(df)
  predictions = predict(model, X)
  forecast_df = create_forecast_df(df, predictions)
  
  return forecast_df
  