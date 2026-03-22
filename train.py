#!/usr/bin/env python
"""
train.py — CLI script to train the GOALS ML pipeline.

Usage:
    python train.py
    python train.py --seasons 2021_2022 2022_2023

Runs:
  1. Load FotMob La Liga parquet data for training seasons
  2. Compute position-specific composite scores
  3. Derive match results
  4. Train Random Forest classifier with walk-forward CV
  5. Save artifacts to goals_app/ml/artifacts/
  6. Print metrics summary
"""

import argparse
import sys
from pathlib import Path

# Ensure repo root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from goals_app.config import TRAIN_SEASONS
from goals_app.services.ml_service import train


def main():
    parser = argparse.ArgumentParser(description="Train GOALS ML pipeline")
    parser.add_argument(
        "--seasons",
        nargs="+",
        default=TRAIN_SEASONS,
        help="Seasons to train on (e.g. 2021_2022 2022_2023 2023_2024)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("GOALS — Training ML Pipeline")
    print("=" * 60)
    print(f"Training seasons: {args.seasons}")
    print()

    try:
        metrics = train(args.seasons)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Training complete.")
    print(f"  Matches used:     {metrics['n_train_matches']}")
    print(f"  Seasons:          {metrics['seasons_used']}")
    print(f"  Train accuracy:   {metrics['train_accuracy']:.3f}")
    print(f"  Train macro F1:   {metrics['train_macro_f1']:.3f}")
    if metrics.get("cv_folds"):
        print()
        print("Walk-forward CV:")
        for fold in metrics["cv_folds"]:
            print(f"  val={fold['val_season']}  acc={fold['accuracy']:.3f}  f1={fold['macro_f1']:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
