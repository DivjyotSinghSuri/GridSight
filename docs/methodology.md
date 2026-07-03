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
| V3 | Lag Features | Temporal dependence |
| V4 | Rolling Statistics | Local trends and smoothing |
| V5 | Daylight Features | Solar geometry |
| V6 | Interaction Features | Nonlinear relationships |
| V7 | Advanced Solar Features *(Future)* | Additional solar-specific engineering |

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

---

# 20. Experiment Methodology

Experiments follow a controlled methodology.

## Rules

Only one experimental variable changes at a time.

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

Never compare:

- Different models
- Different feature sets

simultaneously.

---

# 21. Evaluation Metrics

Every experiment records:

- Dataset Version
- Model
- Feature Set
- Hyperparameters
- Notes

Primary evaluation metric:

- MAPE

Secondary metrics:

- MAE
- RMSE

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

---

# 23. Research Methodology

The research question is not fixed before experimentation.

Instead:

1. Build the platform.
2. Conduct reproducible experiments.
3. Analyze empirical results.
4. Draw conclusions from evidence.

This minimizes confirmation bias and improves reproducibility.

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