# Finite six-deck evaluation results

Experimental shallow-shoe approximations, not verified or calibrated Macau CSM behavior.

Seed: `20260907`. Independent shoes per mode: **250,000**. Bet range: **1–4**, linear ramp reaching the maximum at estimated edge **1%**. No skipped rounds or tuned parameters.

All ± values below are 95% confidence half-widths using independent whole-shoe clusters. Profit includes split/double stakes; the wager denominator includes initial bets only. Variance is marginal round-profit variance in squared units. Runtime is per mode, excluding table construction.

| Reshuffle | Play | Bet | Rounds | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Runtime (s) |
|---|---|---|---:|---:|---:|---:|---:|
| every-round | baseline | constant | 250,000 | -0.007002 ± 0.004487 | -0.7002% ± 0.4487% | 1.31001 | 16.20 |
| every-round | baseline | bounded | 250,000 | -0.007002 ± 0.004487 | -0.7002% ± 0.4487% | 1.31001 | 16.46 |
| every-round | counting | constant | 250,000 | -0.007194 ± 0.004492 | -0.7194% ± 0.4492% | 1.31339 | 16.82 |
| every-round | counting | bounded | 250,000 | -0.007194 ± 0.004492 | -0.7194% ± 0.4492% | 1.31339 | 16.71 |
| 26 | baseline | constant | 1,292,109 | -0.006463 ± 0.001974 | -0.6463% ± 0.1974% | 1.31040 | 26.60 |
| 26 | baseline | bounded | 1,292,109 | -0.006500 ± 0.001991 | -0.6458% ± 0.1978% | 1.33246 | 27.21 |
| 26 | counting | constant | 1,293,296 | -0.006381 ± 0.001977 | -0.6381% ± 0.1977% | 1.31582 | 30.83 |
| 26 | counting | bounded | 1,293,296 | -0.006464 ± 0.002001 | -0.6409% ± 0.1983% | 1.34747 | 33.02 |
| 52 | baseline | constant | 2,482,008 | -0.005006 ± 0.001424 | -0.5006% ± 0.1424% | 1.31075 | 41.01 |
| 52 | baseline | bounded | 2,482,008 | -0.004823 ± 0.001499 | -0.4658% ± 0.1448% | 1.45170 | 41.17 |
| 52 | counting | constant | 2,485,101 | -0.004903 ± 0.001428 | -0.4903% ± 0.1428% | 1.31705 | 46.54 |
| 52 | counting | bounded | 2,485,101 | -0.004634 ± 0.001529 | -0.4435% ± 0.1463% | 1.50966 | 47.10 |

All configurations have negative estimated returns, with individual 95% intervals below zero.

Every matched counting-versus-baseline interval includes zero: this run does not establish a counting improvement.

## Matched-shoe differences

Counting minus baseline. Positive values favor counting. Bounded-mode comparisons include both playing changes and changes in the forecast used for betting. Intervals that contain zero do not establish an improvement. These intervals are not adjusted for multiple comparisons.

| Reshuffle | Bet | Profit/round difference [95% CI] | Profit/wagers difference, percentage points [95% CI] |
|---|---|---:|---:|
| every-round | constant | -0.000192 [-0.000646, +0.000262] | -0.0192 [-0.0646, +0.0262] |
| every-round | bounded | -0.000192 [-0.000646, +0.000262] | -0.0192 [-0.0646, +0.0262] |
| 26 | constant | +0.000083 [-0.000358, +0.000524] | +0.0083 [-0.0358, +0.0524] |
| 26 | bounded | +0.000036 [-0.000423, +0.000494] | +0.0049 [-0.0406, +0.0504] |
| 52 | constant | +0.000103 [-0.000330, +0.000536] | +0.0103 [-0.0330, +0.0536] |
| 52 | bounded | +0.000189 [-0.000324, +0.000702] | +0.0223 [-0.0270, +0.0716] |

## Forecast and penetration diagnostics

Forecast error is realized unit profit minus predicted unit edge. It measures aggregate bias with sampling uncertainty, not calibration at each count. Long-run variance includes within-shoe dependence.

| Reshuffle | Play | Bet | Mean initial bet | Raised bets | Mean cards/shoe | Max cards/shoe | Long-run variance | Forecast error [95% CI] |
|---|---|---|---:|---:|---:|---:|---:|---:|
| every-round | baseline | constant | 1.00000 | 0.000% | 5.469 | 14 | 1.31001 | -0.001298 [-0.005785, +0.003189] |
| every-round | baseline | bounded | 1.00000 | 0.000% | 5.469 | 14 | 1.31001 | -0.001298 [-0.005785, +0.003189] |
| every-round | counting | constant | 1.00000 | 0.000% | 5.464 | 14 | 1.31339 | -0.001490 [-0.005983, +0.003002] |
| every-round | counting | bounded | 1.00000 | 0.000% | 5.464 | 14 | 1.31339 | -0.001490 [-0.005983, +0.003002] |
| 26 | baseline | constant | 1.00000 | 0.000% | 28.291 | 37 | 1.31048 | -0.000502 [-0.002477, +0.001472] |
| 26 | baseline | bounded | 1.00645 | 1.636% | 28.291 | 37 | 1.33272 | -0.000502 [-0.002477, +0.001472] |
| 26 | counting | constant | 1.00000 | 0.000% | 28.282 | 37 | 1.31530 | -0.000477 [-0.002455, +0.001500] |
| 26 | counting | bounded | 1.00862 | 1.643% | 28.282 | 37 | 1.34746 | -0.000477 [-0.002455, +0.001500] |
| 52 | baseline | constant | 1.00000 | 0.000% | 54.350 | 65 | 1.30994 | +0.001043 [-0.000382, +0.002468] |
| 52 | baseline | bounded | 1.03542 | 6.050% | 54.350 | 65 | 1.45270 | +0.001043 [-0.000382, +0.002468] |
| 52 | counting | constant | 1.00000 | 0.000% | 54.344 | 65 | 1.31906 | +0.001030 [-0.000399, +0.002459] |
| 52 | counting | bounded | 1.04488 | 6.095% | 54.344 | 65 | 1.51196 | +0.001030 [-0.000399, +0.002459] |

Table construction: **0.88 s**. Total evaluation wall time: **361.76 s**.

Environment: Python 3.12.3; `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`.

Stationary count-adjusted tables approximate finite-shoe decisions and forecasts; the physical simulation samples without replacement. Machine behavior and policy-model error are outside these confidence intervals. See [model, methodology, and reproduction instructions](../FINITE_SHOE.md).
