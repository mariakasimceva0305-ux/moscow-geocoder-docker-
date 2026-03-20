# moscow-geocoder-docker

Moscow address geocoding prototype with baseline and improved matching pipelines, API serving, and Docker runtime.

## Overview

This repository contains a hackathon/demo geocoder that maps free-form Moscow addresses to normalized building records with coordinates. The implementation keeps two geocoding modes:

- `basic` - exact/normalized matching flow
- `improved` - fuzzy street matching with additional scoring

## Architecture / Pipeline

1. Load building dataset (`src/data_loader.py`)
2. Normalize city/street/house fields (`src/normalize.py`)
3. Run geocoding:
   - baseline pipeline (`src/geocode_basic.py`)
   - improved pipeline (`src/geocode_improved.py`)
4. Return ranked candidates with lat/lon
5. Serve via FastAPI (`src/api.py`) or CLI scripts (`scripts/`)

## Repository Structure

- `src/` - core geocoding logic and API
- `scripts/run_basic_cli.py` - CLI entry for baseline mode
- `scripts/run_improved_cli.py` - CLI entry for improved mode
- `scripts/run_evaluate.py` - evaluation run script
- `docker-compose.yml` - API + PostgreSQL runtime configuration
- `Dockerfile` - application container build
- `requirements.txt` - Python dependencies
- `test_api.py`, `test_format_requirements.py` - validation scripts

## Setup and Run

### Local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker compose up --build
```

API is exposed on `http://localhost:8000`.

## API Example

```bash
curl "http://localhost:8000/geocode/improved?address=Москва, Тверская улица, 7&limit=3"
```

Response is JSON with matched objects and coordinates.

## Evaluation

Evaluation pipeline is available in `src/evaluate.py` and `scripts/run_evaluate.py`.

The evaluation script computes and saves:

- text similarity score (mean/median)
- geographic distance in meters (mean/median)
- successful prediction counts

Output file: `evaluation_results.csv`.

No fixed benchmark numbers are stored in the repository.

## Project Status

Archived hackathon prototype / demo implementation.