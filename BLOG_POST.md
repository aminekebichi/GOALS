# GOALS: Predicting Premier League Match Outcomes Through Position-Specific Player Performance

---

GOALS is a predictive analytics tool that surfaces player performance as the mechanism through which match outcomes are anticipated. Future fixtures appear on the calendar with their projected results — win, draw, or loss — derived not from team-level statistics or historical head-to-head records, but from the aggregated performance signatures of the players expected to take the pitch. Past match cards carry this further: they show the predicted outcome alongside the actual result and, upon interaction, expose the individual player metrics and position-specific scores that informed the model's judgment. The central argument of the system is that a football match is not an atomic event between two clubs — it is the emergent product of twenty-two individual performances, each of which can be measured, normalised, and compared on a common scale.

---

## The Prediction Problem

Football resists prediction in ways that other sports do not. In competitions where scoring is frequent and individual dominance is reliable, statistical models can achieve high accuracy with relatively simple features. The English Premier League offers no such conditions. A single VAR review, a defensive miscommunication in the third minute, or an injury sustained in the warm-up can render pre-match statistical relationships largely irrelevant. Even the most sophisticated published models operate in a narrow band, rarely exceeding 60% three-class accuracy on home win, draw, and away win outcomes.

The natural baseline against which any model must be measured is the degenerate classifier that always predicts a home win. Given that home sides win approximately 44% of Premier League fixtures in a typical season, this trivial strategy achieves an accuracy that many more elaborate approaches fail to surpass. The requirement, then, is not merely to outperform this baseline — which sets only a low floor — but to do so in a manner that is interpretable and grounded in the observable mechanics of the match.

The approach taken here is to construct an explicit performance fingerprint for each player in each fixture, aggregate those fingerprints to the team level, and train a classifier to learn which configurations of team-level performance scores are predictive of the three possible outcomes.

---

## Data Acquisition and Integration

The pipeline draws on two complementary data sources that differ in granularity and scope.

**FotMob** provides match-level player statistics scraped across four Premier League seasons (2021/22 through 2024/25), yielding one record per player per fixture. The available metrics span goal contributions, expected goal indicators (xG, xA), shooting volume, chance creation, dribbling, defensive actions (tackles won, interceptions, clearances, blocks, recoveries, aerial duels won), and — for goalkeepers — saves, save rate, xG on target faced, diving saves, saves inside the box, high claims, and sweeper actions.

**FBref** contributes season-level aggregated statistics, most notably progressive passes, playing time distributions, and supplementary defensive metrics. These serve as contextual modifiers that describe a player's broader tendencies across the full season rather than their performance on any given night.

Merging the two sources requires reconciling player name representations across databases. FBref records names with full diacritical marks and consistent formatting; FotMob representations vary in ways that do not follow a predictable rule. A fuzzy join on the composite key of player name, match date, and club — using token sort ratio matching with a minimum threshold of 85 — resolves the majority of discrepancies while filtering out spurious matches.

---

## Position-Specific Composite Scoring

The foundational design decision of the model is the rejection of a position-agnostic feature space. A midfielder recording two interceptions is performing a routine defensive function; a striker recording the same is demonstrating something unusual about either their defensive recovery or their positioning — the statistical value differs materially depending on role context. Similarly, a goalkeeper making eight saves in a match may be exceptional or may be a symptom of a badly organised defence. Raw statistics, unmediated by positional context, conflate these interpretive differences.

To encode this context explicitly, four position-specific linear composite functions are defined — one each for forwards (ATT), midfielders (MID), defenders (DEF), and goalkeepers (GK). Each function assigns empirically motivated weights to the statistics most relevant to that position. Prior to the application of any composite function, all input metrics are z-score standardised using parameters fitted exclusively on the three training seasons (2021/22, 2022/23, 2023/24). The scaler is never refit on the held-out test season; this constraint is essential to prevent information leakage and to ensure that the composite scores remain on a common interpretive scale across seasons, where a value of +1.5 consistently denotes performance 1.5 standard deviations above the positional mean.

**ATT (Forwards):**
```
ATT = 0.25×(Goals + Assists) + 0.20×xG + 0.15×xA
    + 0.15×Dribbles + 0.10×Shots + 0.10×ChancesCreated + 0.05×Recoveries
```

Goal and assist contributions receive the highest weight, acknowledging that direct involvement in scoring remains the primary function of an attacker. Expected goal metrics supplement this by capturing shot quality independent of finishing variance — a forward who generates high-xG opportunities and consistently reaches dangerous positions scores positively even in matches where the ball does not cross the line.

**MID (Midfielders):**
```
MID = 0.20×ProgressivePasses + 0.20×ChancesCreated + 0.15×xA
    + 0.15×(Goals + Assists) + 0.15×TacklesWon + 0.10×Interceptions + 0.05×Recoveries
```

Progressive ball-carrying and chance creation are co-weighted, reflecting the dual mandate of the modern central midfielder. Defensive contributions — tackles and interceptions — account for 25% of the composite, ensuring that the score does not reward a positionally irresponsible midfielder whose statistics resemble those of an attacking player.

**DEF (Defenders):**
```
DEF = 0.25×TacklesWon + 0.20×AerialDuelsWon + 0.20×Clearances
    + 0.15×Interceptions + 0.10×Blocks + 0.10×ProgressivePasses
```

Defensive solidity metrics are assigned the dominant share of the composite weight. Progressive passing is included at 10% to acknowledge the growing tactical value of defenders capable of initiating build-up play, though it is deliberately subordinated to the primary defensive signals.

**GK (Goalkeepers):**
```
GK = 0.30×Saves + 0.25×xGOT + 0.15×DivingSaves + 0.15×SavesInsideBox
   + 0.10×HighClaims + 0.05×SweeperActions
```

Save volume carries the largest individual weight, supplemented by xG on target faced as a difficulty-adjusted modifier. A goalkeeper who makes five saves against an accumulated xGOT of 4.5 is performing qualitatively differently from one who makes five saves against xGOT of 1.2; the composite function is sensitive to this distinction.

The output of each positional function is a single z-score per player per match, expressed on a unified scale across all four positions. A composite score of +2.0 denotes exceptional performance regardless of role; a score of −1.5 indicates a performance well below the positional average.

---

## From Individual Scores to Match-Level Features

Having obtained per-player composite scores, the transition to match-level classification requires a fixed-length feature representation. The team-level feature vector is constructed by summing the composite scores of each position group within the starting eleven:

```
Home team: [Σ ATT scores, Σ MID scores, Σ DEF scores, GK score]
Away team: [Σ ATT scores, Σ MID scores, Σ DEF scores, GK score]
```

This yields **eight features per match** — four for the home side and four for the away side. The aggregation is additive rather than averaged in order to preserve the effect of squad depth within a position group; a team with three high-performing forwards contributing collectively is meaningfully different from a team with one exceptional forward and two below-average ones.

---

## Classification and Validation

Two classifier architectures were evaluated against the eight-dimensional match feature space:

- **Logistic Regression** with L2 regularisation
- **Random Forest Classifier** with 100 estimators at default depth

Both models were trained with `class_weight='balanced'` to counteract the structural class imbalance inherent in Premier League outcomes — approximately 45% home wins, 25% draws, and 30% away wins. Without this correction, the classifier converges toward near-exclusive home win prediction, achieving the naive baseline accuracy while failing to generalise across all three outcome classes.

Temporal integrity in validation is treated as a non-negotiable constraint. Walk-forward cross-validation was applied within the training period: earlier seasons serve as training folds and later seasons as validation folds, with the ordering strictly preserved. Standard k-fold cross-validation with shuffling would introduce future match results into the training distribution, producing validation estimates that are optimistic and methodologically unsound. No shuffling is applied at any stage of the pipeline.

---

## Evaluation on the Held-Out Test Season

The 2024/25 season (266 Premier League fixtures) constitutes the held-out test set. No observations from this season are used during feature normalisation, model training, or hyperparameter selection.

| Model | Accuracy | Macro F1 |
|-------|----------|----------|
| Logistic Regression | **55.6%** | **0.549** |
| Random Forest Classifier | 54.8% | 0.535 |
| Naive baseline (home win always) | 44.0% | ~0.21 |

Logistic Regression achieves marginally superior performance across both metrics. This result is consistent with the hypothesis that the eight-feature representation encodes a relatively linear signal — the Random Forest's additional model capacity does not translate into improved generalisation and may be inducing a modest degree of overfitting to training-season patterns.

Both models improve substantially over the naive baseline in terms of Macro F1, which weights each class equally. The naive classifier, despite its 44% accuracy, achieves a Macro F1 of approximately 0.21 because it assigns zero probability mass to draws and away wins; the trained models achieve 0.549 and 0.535 respectively, indicating genuine discrimination across all three outcome classes.

A Macro F1 of 0.549 is meaningful, though it reflects the fundamental ceiling imposed by the stochastic nature of the sport. Outcomes that are determined by low-probability events — deflections, goalkeeper errors, red cards in the opening minutes — cannot be recovered from historical performance features regardless of the model's sophistication. The system's claim is not predictive omniscience, but interpretable and statistically grounded inference.

---

## Prediction Transparency and the Audit Trail

The match-level prediction is one output of the system. Arguably more consequential is the traceable chain of evidence that connects the prediction to its constituent inputs. Because every match prediction is a deterministic function of summed composite scores, which are themselves deterministic functions of weighted player statistics, the full derivation is auditable at any level of granularity.

In practice, this means that a past match card in the application is not merely a binary record of whether the model was correct. It surfaces the Man of the Match designation — defined as the player with the highest composite z-score among those who completed at least 45 minutes — alongside the full team rosters, each player annotated with their positional score and colour-coded by standard deviation band (above average, average, or below average). Selecting an individual player reveals the complete statistical breakdown: every metric that contributed to their composite score, the raw value recorded for that fixture, and its normalised representation.

The consequence of this architecture is that a user can reconstruct precisely why the model reached a given conclusion. A prediction that a particular team would win is not an opaque probability estimate — it is the downstream expression of a specific configuration of player performance metrics that, in the training data, were historically associated with winning. This interpretability is a deliberate design property rather than an incidental one.

---

## Infrastructure

The machine learning pipeline is implemented across seven sequential Jupyter notebooks (scikit-learn, pandas, polars), with each stage producing intermediate artefacts consumed by the next. Match-level FotMob data was collected via a custom asynchronous scraper; FBref seasonal statistics were acquired separately. Final predictions were exported as structured parquet files and seeded into a Neon PostgreSQL database, from which the web application reads exclusively.

The web application is a Next.js 16 deployment on Vercel, using Prisma for type-safe database access and Clerk for authentication. Aggregate player statistics and model evaluation metrics are accessible to authenticated users; the match calendar and individual match and player detail pages are publicly accessible without credentials.

---

## Directions for Future Work

Several extensions are likely to yield measurable improvements in predictive performance.

The current feature representation captures within-match player performance but is temporally isolated — each fixture is treated as independent of the matches immediately preceding it. Incorporating rolling performance windows (e.g., composite score averages over the prior five fixtures) would allow the model to account for in-season form trajectories, which are known to be predictive of short-term outcomes.

The treatment of absent players warrants reconsideration. When a player does not appear in the FotMob starting eleven — whether due to injury, suspension, or tactical omission — their contribution to the team-level composite is implicitly set to zero. A more principled approach would impute the player's season-average composite score, preserving the distinction between a team whose key forward is absent and one whose key forward plays but performs poorly.

The classifier outputs raw softmax probabilities whose calibration has not been validated against empirical outcome frequencies. Applying isotonic regression or Platt scaling post-processing would bring the displayed confidence percentages into closer correspondence with observed win rates at equivalent probability values, improving the reliability of the uncertainty estimates surfaced to users.

Finally, extending the historical training window beyond three seasons would provide a more statistically robust basis for the walk-forward validation procedure and reduce the sensitivity of the learned weights to season-specific anomalies.

---

*GOALS was developed by Amine Kebichi and Nicholas Annunziata as part of CS7180 — Vibe Coding at Northeastern University. The live application is available at [https://project-d7avr.vercel.app](https://project-d7avr.vercel.app). The source code is hosted on [GitHub](https://github.com/aminekebichi/GOALS).*
