# Link-22 Hypersonic-Inspired Data Link Study

This project contains a research paper draft and reproducible experiments inspired by high-dynamic hypersonic data-link studies, applied to Link-22.

## Contents

- `paper/Link22_Hypersonic_Inspired_DataLink_Paper.md`: Paper draft with figures.
- `experiments/`: Simulation code and configuration.

## Quick Start

```bash
cd experiments
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_experiments.py
```

Figures are copied to `paper/figures` and CSV outputs are stored in `experiments/results`.

## Reproducibility Notes

- All experiments are seeded (`random_seed` in `experiments/config.json`).
- Adjust experiment parameters via `experiments/config.json`.
