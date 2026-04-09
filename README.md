# Moscow Geocoder Docker

A service-oriented prototype for **Moscow address geocoding** with baseline and improved matching pipelines, API serving, and Docker runtime.

## Why This Project
Free-form address input is messy. Production geocoding systems need to handle normalization, approximate matching, candidate scoring, and stable API behavior — not just exact string lookup.

This repository demonstrates a compact geocoding workflow with two matching modes and explicit service packaging.

## Problem Statement
Map a free-form Moscow address to a normalized building record with coordinates.

## Overview
The implementation keeps two modes:
- **basic** — exact / normalized matching pipeline
- **improved** — fuzzy street matching with additional scoring

That makes the project useful both as a baseline and as a small experiment in search-quality improvement.

## Architecture
1. load building data
2. normalize city / street / house fields
3. run one of the geocoding flows
4. rank candidates
5. return normalized match with coordinates
6. serve the result via FastAPI or CLI

## Repository Structure
```text
src/
  data_loader.py          # building dataset loading
  normalize.py            # address normalization
  geocode_basic.py        # baseline matching
  geocode_improved.py     # improved matching / scoring
  api.py                  # FastAPI application
scripts/
  run_basic_cli.py        # CLI run for baseline
  run_improved_cli.py     # CLI run for improved mode
  run_evaluate.py         # evaluation entrypoint
static/                   # static assets
ARCHITECTURE.md
DOCKER.md
PROJECT_CHECKLIST.md
SCORE_EXPLANATION.md
Dockerfile
docker-compose.yml
requirements.txt
README.md
```

## What the Improved Pipeline Adds
Compared with a direct normalized lookup, the improved mode introduces:
- fuzzy street matching
- more flexible candidate scoring
- better handling of imperfect user input

This is the right direction for real address search, where spelling and formatting noise are common.

## Evaluation
This repository is naturally evaluated on:
- successful match rate
- ranking quality of returned candidates
- robustness to input noise
- API correctness and runtime stability

The presence of `run_evaluate.py` and `SCORE_EXPLANATION.md` makes the project especially good for demonstrating that matching quality is treated as an engineering concern rather than only an algorithmic one.

## Running Locally
```bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
pip install -r requirements.txt
uvicorn src.api:app --reload
```

Or with Docker:
```bash
docker compose up --build
```

## Example API Call
```bash
curl -X POST "http://127.0.0.1:8000/geocode" \
  -H "Content-Type: application/json" \
  -d '{"address": "Москва, Тверская 7"}'
```

## Why This Repo Looks Strong
- clear distinction between baseline and improved pipelines
- explicit architecture documentation
- API layer, evaluation script, and Dockerized runtime
- pragmatic focus on search quality, not only on code elegance

## Suggested Next Improvements
- add a benchmark table for basic vs improved matching
- log common error types by address component
- support candidate confidence calibration
- add batch geocoding mode
- expose ranking explanation fields in API responses

## Limitations
- geographic scope is intentionally narrow
- data quality drives a large share of geocoding quality
- exact production relevance depends on real address distribution and business constraints

## Takeaway
This repository is more than a simple address parser. It demonstrates how to turn fuzzy matching logic into a **service with architecture, evaluation hooks, and reproducible runtime**.
