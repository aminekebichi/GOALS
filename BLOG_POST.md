# GOALS: Using Player Performance to Predict Premier League Match Outcomes

*How composite player scores trained on three seasons of data beat the naive baseline — and what we learned building it.*

---

GOALS is a predictive analytics tool that uses player performance to predict match outcomes. Future matches have their anticipated outcomes visually displayed on each card. Past match cards show the predicted outcome against the actual outcome, and are interactive — clicking through reveals the individual player performances and metrics that were used to make those predictions in the first place. The idea was simple: instead of treating a match as a coin flip between two teams, treat it as the sum of 22 individual player performances that can be measured, scored, and compared.

This post focuses on the machine learning core of that idea — how we get from raw player stats to a match prediction, and where the model succeeds and falls short.

---

## The Problem With Predicting Football

Football is notoriously hard to predict. Unlike basketball, where scoring is frequent and individual talent reliably dominates, a Premier League match can swing on a single deflection. Historically, even the most sophisticated published models struggle to break 60% accuracy on a 3-class problem (home win / draw / away win).

The naive baseline — just always predicting the home team wins — achieves roughly 44% accuracy over a full Premier League season. That's the floor. Any model worth using needs to do better than that, and ideally explain *why* it made a given prediction rather than operating as a black box.

Our approach: build a performance fingerprint for each player in each match, aggregate those fingerprints to team level, and let the classifier learn which team-level patterns correlate with wins, draws, and losses.

---

## Data: Two Sources, Two Granularities

The pipeline pulls from two sources:

**FotMob** (match-level) provides per-match player stats: goals, assists, expected goals (xG), expected assists (xA), shots, dribbles, chances created, tackles won, interceptions, clearances, blocks, recoveries, aerial duels won, and — for goalkeepers — saves, save rate, and xG on target faced. FotMob data was scraped across four Premier League seasons (2021/22 through 2024/25), producing a parquet file with one row per player per match.

**FBref** (season-level) provides aggregated seasonal stats: progressive passes, playing time breakdowns, and miscellaneous defensive actions. These are used as contextual features — they describe a player's season-wide tendencies rather than their performance on a specific night.

The merge step joins the two sources on `(player_name, match_date, team)` using fuzzy string matching (`rapidfuzz`, threshold ≥ 85) to handle the inevitable name inconsistencies between databases — think "Bruno Fernandes" vs "B. Fernandes" vs names with missing diacritics.

---

## The Core Idea: Position-Specific Composite Scores

A midfielder being intercepted twice is normal. A forward being intercepted twice is a bad sign. A goalkeeper making 8 saves could be exceptional or it could mean their defence was terrible. **Context matters.**

Rather than feeding raw stats into a classifier and hoping it figures out the context, we encode that context explicitly through four position-specific formulas — one for forwards (ATT), midfielders (MID), defenders (DEF), and goalkeepers (GK). Each formula assigns different weights to different stats based on what's actually important for that position.

Before applying any formula, all input stats are **z-score normalised** — fitted on the training seasons only (2021/22, 2022/23, 2023/24), never on the test season. This means a score of +1.5 always means "1.5 standard deviations above average for a player in that position," regardless of season-to-season statistical drift.

**ATT (Forwards):**
```
ATT = 0.25×(Goals + Assists) + 0.20×xG + 0.15×xA
    + 0.15×Dribbles + 0.10×Shots + 0.10×ChancesCreated + 0.05×Recoveries
```

Goal involvements carry the most weight (0.25), supported by expected goal metrics that capture shot quality beyond just whether the ball crossed the line. A forward who regularly creates chances but can't finish still scores positively — xG rewards the process.

**MID (Midfielders):**
```
MID = 0.20×ProgressivePasses + 0.20×ChancesCreated + 0.15×xA
    + 0.15×(Goals + Assists) + 0.15×TacklesWon + 0.10×Interceptions + 0.05×Recoveries
```

Progressive passing and chance creation are co-weighted at 0.20 each, reflecting the dual role of a complete midfielder — building up play and pressing off the ball. Defensive contributions (tackles, interceptions) account for 25% of the total, preventing the formula from rewarding forwards-playing-midfielder performances.

**DEF (Defenders):**
```
DEF = 0.25×TacklesWon + 0.20×AerialDuelsWon + 0.20×Clearances
    + 0.15×Interceptions + 0.10×Blocks + 0.10×ProgressivePasses
```

Defensive solidity comes first. Progressive passing is included at 10% weight because modern defenders who can carry the ball out of defence (think Trent Alexander-Arnold) provide genuine value — but it's not the primary signal.

**GK (Goalkeepers):**
```
GK = 0.30×Saves + 0.25×xGOT + 0.15×DivingSaves + 0.15×SavesInsideBox
   + 0.10×HighClaims + 0.05×SweeperActions
```

Saves are weighted most (0.30), but xG on target faced (xGOT) acts as a difficulty-adjusted modifier — making 5 saves against xGOT of 4.5 is much more impressive than making 5 saves against xGOT of 1.2.

The output of applying these formulas is a single composite z-score per player per match, placed on a common scale across all four positions. A score of +2.0 means "exceptional performance regardless of position." A score of -1.5 means "well below average."

---

## From Players to Teams: The Feature Vector

A match needs a fixed-length feature representation. We aggregate the per-player composite scores to the team level by summing the scores of each position group's starting XI:

```
Home team: [sum of ATT scores, sum of MID scores, sum of DEF scores, GK score]
Away team: [sum of ATT scores, sum of MID scores, sum of DEF scores, GK score]
```

This gives us **8 features per match** — the home team's four position-group scores and the away team's four. The intuition: a match where the home team has a combined ATT score of +6.3 and the away team has -1.2 should, all else being equal, favour the home side in attack.

---

## The Classifier

With 8-feature match vectors and 3-class labels (H / D / A), we trained two classifiers:

- **Random Forest Classifier** — 100 trees, default depth, `class_weight='balanced'`
- **Logistic Regression** — L2 regularisation, `class_weight='balanced'`

The `class_weight='balanced'` setting is essential. Premier League outcomes are not uniformly distributed — roughly 45% home wins, 25% draws, 30% away wins. Without balancing, the classifier learns to predict home wins constantly and achieves 44% accuracy while being useless for draws and away wins. Balanced weighting forces the model to genuinely learn all three classes.

**Walk-forward cross-validation** was used within the training seasons. This means validation always uses data from seasons later in time than training — seasons 2021/22 and 2022/23 train to validate on 2023/24, then all three seasons train for the final model. Standard k-fold shuffling would leak future match results into training and produce falsely optimistic validation scores. We never shuffle.

---

## Results on the 2024/25 Season

The 2024/25 season (266 matches) was the held-out test set, never used for fitting or validation at any stage.

| Model | Accuracy | Macro F1 |
|-------|----------|----------|
| Logistic Regression | **55.6%** | **0.549** |
| Random Forest | 54.8% | 0.535 |
| Naive baseline (always home win) | 44.0% | ~0.21 |

Logistic Regression outperforms the Random Forest slightly — likely because the 8-feature linear decision boundary is appropriate for a relatively clean signal, while the Random Forest has more capacity than the data can reliably justify.

Both models beat the naive baseline by a meaningful margin. Macro F1 of 0.549 means the model is doing non-trivial work across all three classes, not just riding home-win prevalence.

That said, 55.6% is not a winning formula for a sportsbook. Football has high inherent randomness — VAR decisions, injuries in warm-up, red cards in the 10th minute — that no statistical model trained on historical performance can capture. The honest framing: our model makes better-than-chance predictions that are explainable through the underlying player performance data.

---

## What Makes It Interesting: The Explainability Layer

The prediction number is one output. The more interesting output is *why*.

Because every match prediction traces back to summed composite scores, which trace back to individual player z-scores, which trace back to weighted combinations of specific stats — the entire chain is auditable. In the GOALS app, clicking a past match card shows:

- Which player had the highest composite z-score (Man of the Match)
- Every player's position-specific score, colour-coded by standard deviation from average (red for above average, amber for average, blue for below average)
- Each player's individual stat breakdown — the raw numbers that fed into their composite score

A user can see not just "the model predicted Arsenal to win" but "Arsenal's forward line had a combined ATT score of +4.8 against Chelsea's +1.1, driven largely by Bukayo Saka's exceptional xA and dribble numbers."

That's a different kind of sports analytics than a win probability percentage with no lineage.

---

## The Tech (Briefly)

The ML pipeline runs entirely in Python notebooks (scikit-learn, pandas, polars). Match-level FotMob data was scraped using a custom async scraper; FBref season stats were collected separately. The final predictions were exported as a parquet file, then seeded into a Neon PostgreSQL database.

The web app is a Next.js 16 application deployed on Vercel, backed by Prisma for type-safe database access and Clerk for authentication. The analytics-heavy pages (Player Stats, Pipeline Metrics) require sign-in; the match calendar and all match/player detail pages are fully public.

---

## What We'd Do Differently

**More features.** The 8 composite scores capture within-game performance well but ignore context: home/away advantage beyond what's implicitly in the feature, recent form (last 5 match composite score rolling average), injury absences, and head-to-head history. Adding rolling form features in particular would likely improve accuracy by 2–3 points.

**Richer validation.** Walk-forward CV across three seasons isn't many folds. More historical data — going back to 2018/19 — would give the model a better chance to distinguish signal from noise.

**Calibrated probabilities.** The classifier outputs raw probabilities (P(H), P(D), P(A)) that sum to 1 but aren't calibrated against actual outcome frequencies. Platt scaling or isotonic regression post-processing would make the displayed confidence percentages more trustworthy.

**Player absence handling.** Currently, if a star player is injured and doesn't appear in the FotMob starting XI, their composite score simply contributes 0. A better approach would incorporate season-average scores for expected starters who don't play, rather than treating absences as zero contribution.

---

## Closing

Football prediction is a hard problem that attracts a lot of overconfident solutions. GOALS doesn't claim to solve it — it claims to make better-than-chance predictions in a way that's transparent about the reasoning. Every card in the app is a testable hypothesis: "this team's players performed at a level that historically correlates with winning." You can see the evidence, challenge the weights, and form your own view.

The 55.6% accuracy number will improve as we add features and data. The explainability layer — the player-level audit trail — is the part we're most proud of.

---

*GOALS is built by Amine Kebichi and Nicholas Annunziata as part of EECE5644 — Introduction to Machine Learning and Pattern Recognition at Northeastern University. The live app is available at [https://project-d7avr.vercel.app](https://project-d7avr.vercel.app). The source code is on [GitHub](https://github.com/aminekebichi/GOALS).*
