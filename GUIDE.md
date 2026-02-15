# Evidence-Based DSS - Quick Start Guide

## 1. Setup Data
Run the following to generate sample data and run tests:

```bash
python scripts/setup_sample_data.py
pytest
```

## 2. Launch Application
Run the Streamlit app:

```bash
streamlit run app/main.py
```

## 3. Features
- **Decision Board**: View prioritized decision cards.
- **Evidence Input**: Upload Survey/KPI CSVs.
- **Settings**: View current configuration.

## 4. Key Logic
- **Quality Gate**: Checks n-count and missing ratio. Adds penalty if bad data.
- **SAW Priority**: Score = Impact*w + Urgency*w - Uncertainty*w
- **Decision Engine**: Rules (if X < Y then RED) + Recommendation Drafts.
