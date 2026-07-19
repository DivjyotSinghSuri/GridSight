from .config import DATASET_COLUMNS
def validate_table_not_empty(df):
    """
    Ensures the input DataFrame contains at least one row.
    """
    if df.empty:
      raise ValueError("Input DataFrame is empty.")
    
def validate_required_columns(df, expected_columns):
  """
  Ensures all the required columns are present in the DataFrame.
  """
  
  missing_columns = set(expected_columns) - set(df.columns)
  extra_columns = set(df.columns) - set(expected_columns)

  if missing_columns:
      raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

  if extra_columns:
      raise ValueError(
            f"Unexpected columns found: {sorted(extra_columns)}"
        )
      
def validate_missing_values(df):
  """
    Ensures the input DataFrame contains no missing values.
  """

  missing_values = df.isna().sum()
  missing_values = missing_values[missing_values > 0]

  if not missing_values.empty:
    raise ValueError(
      f"Missing values detected:\n{missing_values.to_string()}"
        )

def validate_duplicate_timestamps(df):
  """
    Ensures there are no duplicate timestamps.
  """

  duplicate_count = df["timestamp"].duplicated().sum()

  if duplicate_count > 0:
      raise ValueError(
          f"Found {duplicate_count} duplicate timestamp(s)."
        )
      
def validate_feature_order(df, expected_columns):
    """
    Ensures the feature columns are in the expected order.
    """

    if list(df.columns) != expected_columns:
        raise ValueError(
            "Feature column order does not match the expected schema."
        )
        
def validate_dataset(df):
    """
    Runs all validation checks before prediction.
    """

    validate_table_not_empty(df)
    validate_required_columns(df, DATASET_COLUMNS)
    validate_feature_order(df, DATASET_COLUMNS)
    validate_missing_values(df)
    validate_duplicate_timestamps(df)