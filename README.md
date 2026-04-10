# alpha-generated

This project is a practical workspace for generating and testing WorldQuant alpha ideas with AI-assisted workflows.

It combines:
- a LangGraph-based alpha generation loop,
- model-driven hypothesis and formula creation,
- validation before submission,
- and automated backtest submission to WorldQuant endpoints.

The goal is simple: iterate quickly, reject bad formulas early, and keep only usable alpha candidates.

## What This Repository Is

This is an experimentation and tooling repo, not a single app.

It includes:
- notebooks for rapid iteration (`miner.ipynb` as the main workflow),
- supporting modules and alternative implementations,
- and related research/project folders collected in one place.

## Quick Start

1. Create and activate a Python virtual environment.
2. Install dependencies used by the notebook (for example: `langgraph`, `httpx`, `python-dotenv`).
3. Add credentials to `.env` (OpenRouter and WorldQuant).
4. Open and run `miner.ipynb`.

## Current Focus

The primary workflow right now is the WorldQuant miner notebook, which runs a controlled alpha-generation loop and submits validated expressions for simulation.
