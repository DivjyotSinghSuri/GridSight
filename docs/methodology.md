# GridSight - Methodology & Design Decisions

## 1. Project Philosophy

GridSight is designed as an end-to-end renewable energy analytics platform rather than a standalone machine learning project.

The objective is to build a reproducible forecasting system covering:

- Data ingestion
- Cloud storage
- Data warehousing
- Analytics engineering
- Feature engineering
- Machine learning
- Experiment tracking
- Forecast serving
- Monitoring

Machine learning is treated as one component of the overall data platform.

---

# 2. System Architecture

```
APIs
    ↓
AWS S3 (Bronze)
    ↓
DuckDB
    ↓
dbt
    ↓
Machine Learning
    ↓
Dashboard
```

# 2.1 Pipeline Orchestration

GridSight is orchestrated using Apache Airflow to automate the end-to-end forecasting workflow.

Rather than executing individual scripts manually, Airflow manages task execution, scheduling, retries and dependency management, ensuring a reproducible production pipeline.

The pipeline executes once per day and consists of the following tasks:

```text
Daily Ingestion
        ↓
Load Bronze
        ↓
dbt Transformations
        ↓
Forecast Generation
        ↓
Forecast Validation
```

Each task begins only after its upstream dependencies complete successfully.

The DAG includes retry policies and validation checks to improve robustness against transient failures.

The orchestration layer separates workflow management from business logic, allowing ingestion, transformation and forecasting components to evolve independently.

### Design Principles

Each layer has a single responsibility.

- APIs collect raw data.
- AWS S3 preserves immutable source data.
- DuckDB stores analytical datasets.
- dbt performs transformations.
- Machine Learning trains forecasting models.
- Dashboard consumes forecasts and analytics.

---

# 3. Data Architecture

## Decision

Use the **Medallion Architecture**.

```
Bronze
   ↓
Silver
   ↓
Gold
```

### Reason

- Bronze preserves raw source data.
- Silver standardizes and cleans datasets.
- Gold contains machine-learning-ready features.

Business logic only flows downstream.

---

# 4. Data Sources

| Source | Purpose |
|---------|---------|
| Open-Meteo Weather API | Historical weather observations |
| Open-Meteo Solar API | Solar irradiance observations |
| Open-Meteo Daily API | Sunrise, sunset and daylight information |
| ENTSO-E Transparency Platform | Actual solar generation |

### Reason

All sources are public, reproducible and suitable for research.

---

# 5. Storage Strategy

```
API Sources
      ↓
AWS S3 (Bronze Data Lake)
      ↓
DuckDB
      ↓
dbt Models
```

### Design Decisions

- AWS S3 acts as immutable storage.
- DuckDB serves as the analytical warehouse.
- dbt owns all transformations.
- Python is responsible only for ingestion.

---

# 6. Bronze Layer Philosophy

## Purpose

Preserve source data with minimal modification.

### Allowed Transformations

- XML parsing
- Basic type conversion
- API normalization
- CSV generation

### Not Allowed

- Feature engineering
- Business rules
- Aggregations
- Derived metrics

Bronze should always be reproducible directly from the APIs.

---

# 7. Silver Layer Philosophy

## Purpose

Prepare clean analytical datasets.

### Responsibilities

- Rename columns
- Standardize naming conventions
- Standardize units
- Remove unnecessary columns
- Correct temporal grain
- Correct spatial grain

Feature engineering is intentionally excluded from the Silver layer.

---

# 8. Data Grain Standardization

One of the most important design decisions in the project.

## Final Grain

```
One Row
=
One Hour
=
Germany
```

Every downstream transformation assumes this grain.

Before joining datasets, ensure every table represents the same business grain unless a different relationship is intentionally designed.

---

# 9. Temporal Aggregation

## Generation Data

ENTSO-E provides:

- Average Power (MW)
- Every 15 minutes

### Decision

Aggregate using:

```sql
AVG(generation_mw)
```

instead of:

```sql
SUM(generation_mw)
```

### Reason

Generation values represent average power over each interval rather than cumulative energy.

Using `SUM()` would produce physically incorrect values.

---

# 10. Spatial Aggregation

Weather and irradiance observations are collected at **25 sampling locations** across Germany.

Generation is available only at the national level.

### Problem

Different spatial granularities would create many-to-many joins.

### Decision

Aggregate weather and irradiance to Germany-wide hourly averages within the Silver layer.

### Initial Aggregations

| Variable | Aggregation |
|----------|-------------|
| Temperature | AVG |
| Relative Humidity | AVG |
| Precipitation | AVG |
| Cloud Cover | AVG |
| Wind Speed | AVG |
| Solar Irradiance Metrics | AVG |

---

# 11. Wind Direction

## Decision

Exclude from the initial feature set.

### Reason

Wind direction is a circular variable.

Arithmetic averaging produces incorrect results.

Future versions may include:

- Vector averaging
- Sine/Cosine encoding

if experiments justify its inclusion.

---

# 12. Gold Layer Philosophy

## Purpose

Provide a fully machine-learning-ready dataset.

Each row contains:

- Target variable
- Raw predictors
- Engineered features

No additional transformations should be required before training.

---

# 13. Materialization Strategy

## Silver

Materialization:

**View**

Reason:

- Lightweight transformations
- Easier maintenance

## Gold

Materialization:

**Table**

Reason:

- Expensive joins
- Window functions
- Frequently accessed during model training

---

# 14. Join Strategy

Driving table:

**Generation**

```
Generation
LEFT JOIN Weather
LEFT JOIN Irradiance
LEFT JOIN Daylight
```

### Reason

Every training observation must contain the target variable.

Missing predictor values are preferable to missing targets.

# 14.1 Forecast Serving

After feature engineering is completed, the production forecasting model generates hourly renewable energy forecasts.

Forecasts are written to the `gold_forecasts` table together with metadata including:

- Forecast timestamp
- Predicted generation (MW)
- Model version
- Forecast creation timestamp

Persisting forecasts enables downstream analytical applications to consume predictions without rerunning the machine learning pipeline.

---

# 15. Feature Engineering Philosophy

Feature engineering is performed exclusively within the Gold layer.

Every feature must answer three questions:

1. Why should this improve forecasting?
2. How is it computed?
3. Can its impact be measured experimentally?

If any answer cannot be justified, the feature should not be included.

---

# 16. Feature Engineering Versions

| Version | Feature Group | Purpose |
|----------|---------------|---------|
| V0 | Historical Generation | Baseline persistence model |
| V1 | Weather + Irradiance | External environmental drivers |
| V2 | Calendar | Seasonality and temporal cycles |
| V3 | Daylight Features | Solar geometry |
| V4 | Rolling Statistics | Local trends and smoothing |
| V5 | Interaction Features | Nonlinear relationships |
| V6 | Advanced Solar Features *(Future)* | Additional solar-specific engineering |

---

# 17. Daylight Features

## Decision

Explicitly engineer daylight features instead of relying solely on irradiance.

### Features

- Daylight Duration
- Sunshine Duration
- Is Daylight
- Minutes Since Sunrise
- Daylight Progress (%)

### Reason

Solar production depends not only on irradiance but also on the position of the sun throughout the day.

---

# 18. Interaction Features

Interaction features are introduced only where a physical relationship exists.

Current interactions:

- Cloud Cover × Shortwave Radiation
- Temperature × Shortwave Radiation
- Wind Speed × Temperature
- Daylight Progress × Shortwave Radiation

### Reason

Capture nonlinear relationships while maintaining interpretability.

---

# 19. Data Quality

Data quality is enforced using dbt tests.

Current tests:

- Unique timestamp
- Non-null timestamp
- Non-null target
- Non-null 168-hour lag
- Accepted values for `is_daylight`
- Accepted values for `is_weekend`
- Daylight progress constrained between 0 and 1

# 19.1 Runtime Validation

In addition to dbt data quality tests, GridSight performs runtime validation during pipeline execution.

Validation includes:

- Forecast table existence
- Non-empty forecast outputs
- Forecast creation timestamp verification
- Required feature availability prior to inference

These checks prevent incomplete or invalid datasets from propagating through the forecasting pipeline and provide an additional layer of production reliability.

---

# 20. Machine Learning Experiment Methodology

GridSight follows an incremental feature engineering strategy.

Rather than engineering all features simultaneously, new feature groups are introduced one version at a time.


```
Feature Version
        ↓
Train Multiple Models
        ↓
Compare Models
        ↓
Select Best Model
        ↓
Feature Ablation
        ↓
Analyze Results
```


For every feature version:

1. Train multiple machine learning models.
2. Evaluate using identical train/test splits.
3. Compare model performance.
4. Select the best-performing model.
5. Perform feature ablation.
6. Explain predictions using SHAP.

Only one experimental variable is modified at a time to ensure that performance improvements can be attributed to a specific feature group.

# 20.1 Production Data Synchronization

Renewable energy datasets originate from independent external APIs that may expose different levels of data freshness.

Weather, irradiance and generation observations are therefore synchronized before forecasting.

Only observations containing all required predictor variables are used for inference.

This prevents incomplete feature vectors from reaching the production model while maintaining consistency across all input datasets.

---

# 21. Evaluation Metrics

Primary evaluation metric:

- WAPE (Weighted Absolute Percentage Error)

Secondary evaluation metrics:

- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)

WAPE was selected because renewable energy generation contains frequent periods of near-zero production (e.g., nighttime), causing MAPE to become unstable and artificially inflate forecasting errors. WAPE provides a more robust and interpretable evaluation for this application.

### Reason

Solar generation contains numerous zero and near-zero observations during nighttime and around sunrise/sunset.

Traditional MAPE becomes unstable when actual values approach zero.

WAPE provides a more robust percentage-based evaluation while remaining easily interpretable.

---

# 22. Feature Version Roadmap

| Version | New Feature Group | Why Added | Hypothesis |
|----------|-------------------|-----------|------------|
| V0 | Historical Generation | Baseline | Persistence captures temporal dependence |
| V1 | Weather + Irradiance | External drivers | Weather explains generation variability |
| V2 | Calendar | Seasonality | Temporal cycles improve forecasting |
| V3 | Lag Features | Temporal dependence | Recent observations improve prediction |
| V4 | Rolling Statistics | Local trends | Smoothed history reduces noise |
| V5 | Daylight Features | Solar geometry | Explicit daylight representation improves forecasts |
| V6 | Interaction Features | Nonlinear effects | Combined variables capture physical relationships |

# 22.1 Production Model Selection

Following baseline model evaluation and hyperparameter optimization, a single production model is selected for operational forecasting.

The selection process follows:

```text
Baseline Evaluation
        ↓
Hyperparameter Optimization
        ↓
Performance Comparison
        ↓
Production Model Selection
        ↓
Deployment
```

Ridge Regression was selected as the production model after achieving the lowest validation WAPE among all evaluated models following Optuna optimization.

The final model is serialized using Joblib and loaded during each scheduled forecasting run.

---

# 23. Research Methodology

GridSight follows an incremental experimental methodology designed to isolate the contribution of each feature group while maintaining reproducibility.

The experimental workflow consists of:

```text
Feature Engineering Version
            ↓
Baseline Model Training
            ↓
Model Evaluation
            ↓
Hyperparameter Optimization
            ↓
Production Model Selection
            ↓
Feature Ablation
            ↓
SHAP Explainability
            ↓
Result Interpretation
```

Only one feature group is introduced between consecutive experimental versions.

This controlled methodology allows performance improvements to be attributed to specific engineering decisions while minimizing experimental confounding.

The final production pipeline is selected based on optimized validation performance and subsequently deployed for automated daily forecasting.

---

# 24. Engineering Principles

Throughout GridSight, the following principles guide implementation.

- Separate ingestion from transformation.
- Validate data before feature engineering.
- Standardize grain before joining datasets.
- Prefer reproducibility over convenience.
- Keep every engineering decision explainable.
- Measure the contribution of every feature.
- Change only one experimental variable at a time.
- Build incrementally and validate every stage before moving forward.
- Favor simple, interpretable solutions before introducing additional complexity.
- Synchronize heterogeneous data sources before model inference.
- Validate every pipeline stage before downstream execution.
- Separate workflow orchestration from analytical logic.
- Deploy only validated production models.
- Automate forecasting through reproducible scheduled pipelines.

The target variable represents average hourly power (MW). Daily forecasts are obtained by aggregating hourly predictions over 24 hours, yielding an approximation of daily energy generation (MWh).

# 24.1 Dashboard Integration

Forecasts generated by the production pipeline are consumed through a Streamlit dashboard.

The dashboard provides:

- Forecast visualizations
- Historical generation comparisons
- Weather and irradiance analytics
- Model performance metrics
- Pipeline execution status

The dashboard is designed as a read-only analytical interface and does not perform model training or feature engineering.

# Explainability

Model explainability is performed using SHAP.

SHAP is used to:

- rank feature importance
- understand local predictions
- validate engineering assumptions
- compare learned relationships with domain knowledge

Explainability is performed only after the best-performing model has been selected.

# 22. Model Selection Strategy

The following models are evaluated under identical experimental conditions.

- Linear Regression
- XGBoost
- LightGBM

All models use:

- identical training data
- identical testing data
- identical feature versions

The best-performing model is selected using WAPE before hyperparameter tuning, feature ablation and explainability analysis.

# Experimental Results

The baseline experiments demonstrated that incremental feature engineering substantially improved forecasting performance.

Rolling statistics produced the largest improvement, while interaction features provided additional gains.

Surprisingly, Linear Regression outperformed both XGBoost and LightGBM under the initial experimental setup, highlighting the importance of feature engineering over model complexity.

Further analysis is conducted through hyperparameter tuning, feature ablation and SHAP explainability.

# Hyperparameter Optimization

After evaluating baseline model performance, hyperparameter optimization is performed to identify the best production forecasting pipeline.

Optimization is conducted independently for each feature version using Optuna.

```
Feature Version
        ↓
Hyperparameter Optimization
        ↓
Best Hyperparameters
        ↓
Model Evaluation
        ↓
Production Model Selection
```

Each model is optimized using WAPE as the objective function.

The following model families are optimized:

- Ridge Regression
- XGBoost
- LightGBM

The final production model is selected based on the lowest WAPE obtained after optimization.