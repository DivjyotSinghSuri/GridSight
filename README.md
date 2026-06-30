# GridSight

A cloud-native renewable energy analytics platform that ingests, transforms, and forecasts country-scale solar generation using modern data engineering and machine learning practices.

GridSight follows an ELT architecture to collect meteorological and power system data, build analytical datasets, and train forecasting models.

---

## Features

- Automated weather ingestion using Open-Meteo
- Automated solar irradiance ingestion using Open-Meteo
- Historical generation ingestion using ENTSO-E *(In Progress)*
- Amazon S3 Bronze Data Lake
- DuckDB analytical warehouse
- dbt transformation layer
- Feature engineering pipeline
- LightGBM forecasting model
- Apache Airflow orchestration
- Streamlit dashboard

---

## Architecture

```
                    Open-Meteo API
                  (Weather + Irradiance)
                           │
                           ▼
                 Germany Spatial Grid
                     (5 × 5 Sampling)
                           │
                           ▼
                  Amazon S3 Bronze Layer
                           │
                           ▼
                        DuckDB
                           │
                           ▼
                     dbt Transformations
                    Bronze → Silver → Gold
                           │
                           ▼
                  Feature Engineering
                           │
                           ▼
                  LightGBM Forecast Model
                           │
                           ▼
                  Streamlit Dashboard
```

---

## Technology Stack

| Layer | Technology |
|--------|------------|
| Language | Python |
| Weather Data | Open-Meteo API |
| Irradiance Data | Open-Meteo API |
| Generation Data | ENTSO-E API |
| Storage | Amazon S3 |
| Data Warehouse | DuckDB |
| Transformations | dbt |
| Orchestration | Apache Airflow |
| Machine Learning | LightGBM |
| Dashboard | Streamlit |

---

## Project Structure

```
GridSight/
│
├── ingestion/
│   ├── ingest_weather.py
│   ├── ingest_irradiance.py
│   └── ingest_entsoe.py
│
├── utils/
│   └── grid.py
│
├── data/
│   └── raw/
│
├── gridsight_dbt/
│
├── docs/
│
├── logs/
│
├── config.py
├── logger.py
├── requirements.txt
└── README.md
```

---

## Data Pipeline

### Weather

Open-Meteo API

↓

Germany 5×5 Spatial Grid

↓

Amazon S3 Bronze

---

### Solar Irradiance

Open-Meteo Solar API

↓

Germany 5×5 Spatial Grid

↓

Amazon S3 Bronze

---

### Generation *(In Progress)*

ENTSO-E

↓

Amazon S3 Bronze

---

### Transformations

Bronze

↓

DuckDB

↓

dbt

↓

Silver

↓

Gold

---

### Forecasting

Gold Dataset

↓

Feature Engineering

↓

LightGBM

↓

Predicted Solar Generation

---

## Data Sources

| Dataset | Source | Resolution |
|----------|--------|------------|
| Weather | Open-Meteo | Hourly |
| Solar Irradiance | Open-Meteo | Hourly |
| Solar Generation | ENTSO-E | Hourly |

---

## Current Progress

### Completed

- [x] Germany spatial grid generation
- [x] Weather ingestion pipeline
- [x] Solar irradiance ingestion pipeline
- [x] Amazon S3 Bronze Layer
- [x] Structured logging
- [x] Modular ingestion architecture

### In Progress

- [ ] ENTSO-E generation ingestion
- [ ] DuckDB warehouse
- [ ] dbt transformations
- [ ] Feature engineering
- [ ] LightGBM forecasting
- [ ] Apache Airflow
- [ ] Streamlit dashboard

---

## Roadmap

### Phase 1 — Data Ingestion

- Weather ingestion
- Irradiance ingestion
- Generation ingestion

### Phase 2 — Data Engineering

- DuckDB
- dbt models
- Silver layer
- Gold layer

### Phase 3 — Machine Learning

- Feature engineering
- LightGBM
- Model evaluation

### Phase 4 — Production

- Airflow scheduling
- Streamlit dashboard
- Model monitoring

---

## Future Improvements

- Capacity-weighted weather aggregation
- Polygon-based Germany spatial sampling
- Wind generation forecasting
- Automated model retraining
- Data quality monitoring
- Docker deployment
- CI/CD pipeline

---

## License

This project is licensed under the MIT License.