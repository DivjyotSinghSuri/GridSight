GridSight - Methodology & Design Decisions
1. Data Architecture

Decision: Use Medallion Architecture (Bronze → Silver → Gold).

Reason:

Bronze preserves raw source data.
Silver standardizes and cleans data.
Gold contains ML-ready features.
2. Data Sources

Weather: Open-Meteo

Solar Irradiance: Open-Meteo Solar

Generation: ENTSO-E (Actual Generation)

3. Storage Architecture

Raw API data

→ AWS S3 (Bronze Data Lake)

→ DuckDB (Warehouse)

→ dbt (Transformations)

4. Bronze Layer Philosophy

Store data as close to the source as possible.

Only perform:

basic type parsing
XML → tabular conversion
no business logic
no feature engineering
5. Silver Layer Philosophy

Silver is responsible for:

renaming columns
standardizing units
correcting data grain
removing unnecessary columns
preparing clean datasets

No feature engineering.

6. Generation Aggregation

ENTSO-E provides:

Average power (MW)
every 15 minutes

Decision

Aggregate using:

AVG(generation_mw)

instead of SUM.

Reason

Values represent average power over each 15-minute interval, not cumulative energy.

7. Spatial Aggregation

Weather & irradiance:

25 grid cells

Generation:

Germany-wide

Problem

Different spatial granularity caused many-to-many joins.

Decision

Aggregate grid-level observations into one national observation per hour in the Silver layer.

Initial aggregation:

Temperature → AVG
Humidity → AVG
Precipitation → AVG
Cloud Cover → AVG
Wind Speed → AVG
Irradiance metrics → AVG
8. Wind Direction

Decision

Drop initially.

Reason

Circular variable
Arithmetic mean is incorrect
Expected low predictive contribution
Can revisit later using vector averaging or sine/cosine encoding
9. Gold Layer Philosophy

One row

=

One hour

Contains:

target
raw predictors
engineered features

Only model-ready data.

10. Gold Materialization

Materialize as:

TABLE

Reason:

expensive joins
lag features
rolling windows
repeatedly read during training
11. Join Strategy

Driving table:

Generation

LEFT JOIN

Weather

LEFT JOIN

Irradiance

Reason:

Target must always exist.

12. Feature Engineering Strategy

Do not engineer everything at once.

Incremental versions:

V1

Raw features

↓

V2

Calendar features

↓

V3

Sunrise / Sunset / Daylight

↓

V4

Lag features

↓

V5

Rolling statistics

↓

V6

Interaction features

↓

V7

Advanced solar features

13. Experiment Methodology

First compare:

Different models

Same features

↓

Choose best model

↓

Keep model fixed

↓

Compare feature sets

↓

Run ablation study

Never change:

model
features

at the same time.

14. Evaluation Metrics

Track every experiment.

Metrics:

MAE
RMSE
MAPE

Log:

dataset version
model
features added
notes
15. Research Methodology

Potential paper themes:

Feature engineering impact
Model comparison
Feature ablation

Paper should emerge from experiments, not the other way around.

16. Engineering Principle

Every new feature must answer:

Why should this improve forecasting?
How is it computed?
How much did it improve performance?

If one of those cannot be answered, reconsider adding it.

Validate the grain of every dataset before joining. All tables participating in a join should represent the same business grain (e.g., one row per hour) unless a deliberate many-to-one or one-to-many relationship is intended.