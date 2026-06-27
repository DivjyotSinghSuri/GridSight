# GridSight

> A cloud-assisted ELT platform for renewable energy forecasting using AWS S3, DuckDB, dbt, Apache Airflow, and LightGBM.

## Overview

GridSight is an end-to-end data engineering and machine learning platform designed to forecast renewable energy generation using weather and irradiance data.

The project follows a modern ELT architecture where raw data is ingested into Amazon S3, transformed using dbt on DuckDB, and used to train machine learning models for next-day solar and wind generation forecasting.

The project also includes analytics dashboards, workflow orchestration with Apache Airflow, and an optional REST API for serving predictions.

---

## Architecture

```
External APIs
        │
        ▼
Python Ingestion Scripts
        │
        ▼
AWS S3 (Raw Data)
        │
        ▼
DuckDB
        │
        ▼
dbt Transformations
        │
        ▼
Star Schema
        │
        ▼
Feature Engineering
        │
        ▼
Machine Learning
        │
        ▼
Analytics Dashboard
```

---

## Technology Stack

| Category | Technologies |
|-----------|--------------|
| Programming | Python, SQL |
| Data Lake | AWS S3 |
| Data Warehouse | DuckDB |
| Transformations | dbt Core |
| Workflow | Apache Airflow |
| Machine Learning | LightGBM, Scikit-learn |
| Dashboard | Streamlit |
| Deployment | FastAPI, Docker |

---

## Planned Features

- Automated data ingestion from multiple APIs
- ELT pipeline using AWS S3 and DuckDB
- Star schema dimensional modeling with dbt
- Feature engineering for renewable forecasting
- Multiple forecasting model comparison
- SHAP explainability
- Interactive analytics dashboard
- Airflow workflow orchestration
- Optional FastAPI deployment

---

## Repository Structure

```
GridSight/

├── ingestion/
├── airflow/
├── dbt_project/
├── ml/
├── dashboard/
├── notebooks/
├── data/
├── docs/
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## Status

🚧 Currently under development.
