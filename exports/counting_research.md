# Additional counting methods: held-out evaluation

Experimental six-deck shallow-shoe models, not calibrated Macau continuous-shuffler behavior.

Seed **20260908**; **5,000,000 independent shoes per scenario**; initial bets **1–4**, no skipping. No evaluation outcomes were used to fit or select parameters.

Published tags are implemented with our analytic playing/forecast adapters; these are not the authors' complete published index systems. `composition` uses every visible rank with first-order action sensitivities; it is not an exact finite-shoe optimizer or an upper bound.

The practical threshold was fixed before evaluation at **0.1 percentage point of profit per initial wager**. A detectable improvement, a practically noticeable improvement, and a positive return are separate questions.

## 26-card threshold

± denotes a nominal shoe-clustered 95% confidence half-width. Variance is marginal round-profit variance in squared units. The three betting alternatives share the exact same playing path, so the listed playing runtime is shared, not additive.

| Method | Bets | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Shared runtime (s) |
|---|---|---:|---:|---:|---:|
| baseline | constant | -0.004673 ± 0.000441 | -0.4673% ± 0.0441% | 1.30948 | 2.07 |
| baseline | ramp | -0.004648 ± 0.000445 | -0.4619% ± 0.0442% | 1.33132 | 2.07 |
| baseline | positive-step | -0.004439 ± 0.000491 | -0.4233% ± 0.0468% | 1.62412 | 2.07 |
| hilo | constant | -0.004635 ± 0.000442 | -0.4635% ± 0.0442% | 1.31444 | 2.38 |
| hilo | ramp | -0.004587 ± 0.000447 | -0.4548% ± 0.0443% | 1.34580 | 2.38 |
| hilo | positive-step | -0.004339 ± 0.000493 | -0.4136% ± 0.0470% | 1.64024 | 2.38 |
| halves | constant | -0.004615 ± 0.000442 | -0.4615% ± 0.0442% | 1.31400 | 2.63 |
| halves | ramp | -0.004566 ± 0.000447 | -0.4525% ± 0.0443% | 1.34804 | 2.63 |
| halves | positive-step | -0.004362 ± 0.000510 | -0.4093% ± 0.0478% | 1.75083 | 2.63 |
| hiopt2-ace | constant | -0.004622 ± 0.000442 | -0.4622% ± 0.0442% | 1.31611 | 2.67 |
| hiopt2-ace | ramp | -0.004577 ± 0.000447 | -0.4541% ± 0.0443% | 1.34503 | 2.67 |
| hiopt2-ace | positive-step | -0.004284 ± 0.000502 | -0.4051% ± 0.0475% | 1.69818 | 2.67 |
| omega2-ace | constant | -0.004608 ± 0.000442 | -0.4608% ± 0.0442% | 1.31609 | 1.95 |
| omega2-ace | ramp | -0.004574 ± 0.000447 | -0.4534% ± 0.0443% | 1.34813 | 1.95 |
| omega2-ace | positive-step | -0.004370 ± 0.000507 | -0.4111% ± 0.0477% | 1.73424 | 1.95 |
| ko-centered | constant | -0.004625 ± 0.000442 | -0.4625% ± 0.0442% | 1.31443 | 1.74 |
| ko-centered | ramp | -0.004581 ± 0.000446 | -0.4548% ± 0.0443% | 1.34095 | 1.74 |
| ko-centered | positive-step | -0.004283 ± 0.000498 | -0.4063% ± 0.0473% | 1.67329 | 1.74 |
| composition | constant | -0.004555 ± 0.000442 | -0.4555% ± 0.0442% | 1.31751 | 4.41 |
| composition | ramp | -0.004500 ± 0.000448 | -0.4459% ± 0.0444% | 1.35164 | 4.41 |
| composition | positive-step | -0.004173 ± 0.000509 | -0.3920% ± 0.0478% | 1.74624 | 4.41 |

Total scenario runtime including shuffle and comparisons: **31.14 s**.

## 52-card threshold

± denotes a nominal shoe-clustered 95% confidence half-width. Variance is marginal round-profit variance in squared units. The three betting alternatives share the exact same playing path, so the listed playing runtime is shared, not additive.

| Method | Bets | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Shared runtime (s) |
|---|---|---:|---:|---:|---:|
| baseline | constant | -0.004682 ± 0.000318 | -0.4682% ± 0.0318% | 1.30950 | 3.87 |
| baseline | ramp | -0.004469 ± 0.000335 | -0.4316% ± 0.0324% | 1.45107 | 3.87 |
| baseline | positive-step | -0.003980 ± 0.000438 | -0.3370% ± 0.0371% | 2.47758 | 3.87 |
| hilo | constant | -0.004590 ± 0.000319 | -0.4590% ± 0.0319% | 1.31554 | 4.57 |
| hilo | ramp | -0.004309 ± 0.000341 | -0.4124% ± 0.0327% | 1.50835 | 4.57 |
| hilo | positive-step | -0.003776 ± 0.000442 | -0.3193% ± 0.0374% | 2.52634 | 4.57 |
| halves | constant | -0.004600 ± 0.000319 | -0.4600% ± 0.0319% | 1.31523 | 5.11 |
| halves | ramp | -0.004328 ± 0.000342 | -0.4136% ± 0.0327% | 1.51740 | 5.11 |
| halves | positive-step | -0.003798 ± 0.000451 | -0.3170% ± 0.0376% | 2.62995 | 5.11 |
| hiopt2-ace | constant | -0.004570 ± 0.000319 | -0.4570% ± 0.0319% | 1.31735 | 5.27 |
| hiopt2-ace | ramp | -0.004298 ± 0.000341 | -0.4120% ± 0.0327% | 1.50390 | 5.27 |
| hiopt2-ace | positive-step | -0.003706 ± 0.000446 | -0.3117% ± 0.0375% | 2.57396 | 5.27 |
| omega2-ace | constant | -0.004571 ± 0.000319 | -0.4571% ± 0.0319% | 1.31742 | 3.75 |
| omega2-ace | ramp | -0.004302 ± 0.000342 | -0.4115% ± 0.0327% | 1.51420 | 3.75 |
| omega2-ace | positive-step | -0.003760 ± 0.000450 | -0.3145% ± 0.0376% | 2.61688 | 3.75 |
| ko-centered | constant | -0.004558 ± 0.000319 | -0.4558% ± 0.0319% | 1.31556 | 3.32 |
| ko-centered | ramp | -0.004310 ± 0.000340 | -0.4138% ± 0.0326% | 1.49361 | 3.32 |
| ko-centered | positive-step | -0.003688 ± 0.000443 | -0.3111% ± 0.0374% | 2.54444 | 3.32 |
| composition | constant | -0.004488 ± 0.000319 | -0.4488% ± 0.0319% | 1.31836 | 8.69 |
| composition | ramp | -0.004196 ± 0.000343 | -0.4008% ± 0.0327% | 1.52316 | 8.69 |
| composition | positive-step | -0.003489 ± 0.000451 | -0.2910% ± 0.0376% | 2.63865 | 8.69 |

Total scenario runtime including shuffle and comparisons: **50.32 s**.

## Improvements over the existing Hi-Lo adapter

Differences are percentage points of profit per initial wager, candidate minus Hi-Lo with the same betting policy. The family intervals correct for all reported comparisons and absolute estimates; they are intentionally conservative.

| Threshold | Method / bets | Difference | Nominal 95% CI | Family 95% CI |
|---|---|---:|---:|---:|
| 26 | halves/constant | +0.0021 | [-0.0030, +0.0072] | [-0.0076, +0.0118] |
| 26 | halves/ramp | +0.0023 | [-0.0032, +0.0078] | [-0.0082, +0.0128] |
| 26 | halves/positive-step | +0.0043 | [-0.0101, +0.0188] | [-0.0232, +0.0319] |
| 26 | hiopt2-ace/constant | +0.0013 | [-0.0059, +0.0086] | [-0.0125, +0.0152] |
| 26 | hiopt2-ace/ramp | +0.0007 | [-0.0068, +0.0082] | [-0.0137, +0.0151] |
| 26 | hiopt2-ace/positive-step | +0.0085 | [-0.0064, +0.0235] | [-0.0200, +0.0371] |
| 26 | omega2-ace/constant | +0.0028 | [-0.0047, +0.0102] | [-0.0114, +0.0169] |
| 26 | omega2-ace/ramp | +0.0014 | [-0.0063, +0.0091] | [-0.0133, +0.0161] |
| 26 | omega2-ace/positive-step | +0.0025 | [-0.0126, +0.0176] | [-0.0263, +0.0314] |
| 26 | ko-centered/constant | +0.0011 | [-0.0039, +0.0061] | [-0.0084, +0.0106] |
| 26 | ko-centered/ramp | +0.0001 | [-0.0053, +0.0054] | [-0.0102, +0.0103] |
| 26 | ko-centered/positive-step | +0.0074 | [-0.0061, +0.0209] | [-0.0184, +0.0331] |
| 26 | composition/constant | +0.0081 | [-0.0017, +0.0178] | [-0.0105, +0.0267] |
| 26 | composition/ramp | +0.0089 | [-0.0010, +0.0189] | [-0.0101, +0.0279] |
| 26 | composition/positive-step | +0.0217 | [+0.0055, +0.0378] | [-0.0092, +0.0526] |
| 52 | halves/constant | -0.0010 | [-0.0061, +0.0042] | [-0.0108, +0.0088] |
| 52 | halves/ramp | -0.0011 | [-0.0074, +0.0051] | [-0.0132, +0.0109] |
| 52 | halves/positive-step | +0.0023 | [-0.0125, +0.0172] | [-0.0260, +0.0307] |
| 52 | hiopt2-ace/constant | +0.0019 | [-0.0053, +0.0092] | [-0.0118, +0.0157] |
| 52 | hiopt2-ace/ramp | +0.0005 | [-0.0076, +0.0085] | [-0.0149, +0.0159] |
| 52 | hiopt2-ace/positive-step | +0.0077 | [-0.0081, +0.0234] | [-0.0223, +0.0376] |
| 52 | omega2-ace/constant | +0.0019 | [-0.0054, +0.0092] | [-0.0121, +0.0158] |
| 52 | omega2-ace/ramp | +0.0009 | [-0.0072, +0.0091] | [-0.0147, +0.0165] |
| 52 | omega2-ace/positive-step | +0.0048 | [-0.0110, +0.0206] | [-0.0253, +0.0350] |
| 52 | ko-centered/constant | +0.0032 | [-0.0018, +0.0082] | [-0.0064, +0.0128] |
| 52 | ko-centered/ramp | -0.0013 | [-0.0075, +0.0048] | [-0.0130, +0.0104] |
| 52 | ko-centered/positive-step | +0.0082 | [-0.0063, +0.0227] | [-0.0194, +0.0359] |
| 52 | composition/constant | +0.0102 | [+0.0007, +0.0197] | [-0.0079, +0.0283] |
| 52 | composition/ramp | +0.0117 | [+0.0014, +0.0220] | [-0.0080, +0.0313] |
| 52 | composition/positive-step | +0.0283 | [+0.0113, +0.0453] | [-0.0042, +0.0608] |

## Separating betting effects

Same playing method, changing only the pre-deal bet from constant to ramp or positive-step. Differences below are percentage points of profit per initial wager with family 95% intervals.

| Threshold | Playing method | Bet change | Difference | Family 95% CI |
|---|---|---|---:|---:|
| 26 | baseline | constant → ramp | +0.0055 | [+0.0001, +0.0108] |
| 26 | baseline | constant → positive-step | +0.0440 | [+0.0138, +0.0743] |
| 26 | hilo | constant → ramp | +0.0087 | [+0.0020, +0.0155] |
| 26 | hilo | constant → positive-step | +0.0499 | [+0.0192, +0.0807] |
| 26 | halves | constant → ramp | +0.0090 | [+0.0019, +0.0161] |
| 26 | halves | constant → positive-step | +0.0522 | [+0.0172, +0.0871] |
| 26 | hiopt2-ace | constant → ramp | +0.0081 | [+0.0017, +0.0146] |
| 26 | hiopt2-ace | constant → positive-step | +0.0571 | [+0.0241, +0.0901] |
| 26 | omega2-ace | constant → ramp | +0.0074 | [+0.0005, +0.0142] |
| 26 | omega2-ace | constant → positive-step | +0.0497 | [+0.0154, +0.0840] |
| 26 | ko-centered | constant → ramp | +0.0077 | [+0.0016, +0.0138] |
| 26 | ko-centered | constant → positive-step | +0.0562 | [+0.0241, +0.0883] |
| 26 | composition | constant → ramp | +0.0096 | [+0.0025, +0.0167] |
| 26 | composition | constant → positive-step | +0.0635 | [+0.0288, +0.0982] |
| 52 | baseline | constant → ramp | +0.0367 | [+0.0253, +0.0480] |
| 52 | baseline | constant → positive-step | +0.1312 | [+0.0947, +0.1678] |
| 52 | hilo | constant → ramp | +0.0465 | [+0.0330, +0.0601] |
| 52 | hilo | constant → positive-step | +0.1396 | [+0.1026, +0.1767] |
| 52 | halves | constant → ramp | +0.0464 | [+0.0324, +0.0603] |
| 52 | halves | constant → positive-step | +0.1429 | [+0.1049, +0.1809] |
| 52 | hiopt2-ace | constant → ramp | +0.0451 | [+0.0317, +0.0584] |
| 52 | hiopt2-ace | constant → positive-step | +0.1453 | [+0.1079, +0.1828] |
| 52 | omega2-ace | constant → ramp | +0.0456 | [+0.0318, +0.0593] |
| 52 | omega2-ace | constant → positive-step | +0.1426 | [+0.1047, +0.1805] |
| 52 | ko-centered | constant → ramp | +0.0420 | [+0.0290, +0.0550] |
| 52 | ko-centered | constant → positive-step | +0.1447 | [+0.1075, +0.1819] |
| 52 | composition | constant → ramp | +0.0480 | [+0.0339, +0.0620] |
| 52 | composition | constant → positive-step | +0.1577 | [+0.1197, +0.1958] |

## Interpretation

Every configuration's return is negative even at the conservative family confidence level. No tested method establishes a positive player edge.

For every new adapter and betting policy, the family interval for improvement over existing Hi-Lo is below the predefined 0.1-percentage-point benchmark. The new methods do not deliver a noticeable increment by that criterion. Some nominal intervals exclude zero, but this is a different, weaker claim.

At 26 cards, the largest observed lift over baseline/constant is **composition/positive-step**, **+0.0753 percentage points**, with family interval **[+0.0346, +0.1161]**. This is a descriptive ranking of all reported methods, not a policy selected for a new out-of-sample claim.

At 52 cards, the largest observed lift over baseline/constant is **composition/positive-step**, **+0.1772 percentage points**, with family interval **[+0.1332, +0.2211]**. This is a descriptive ranking of all reported methods, not a policy selected for a new out-of-sample claim.

Raw JSON includes all comparisons with baseline/constant, same-method betting effects, both uncertainty measures, long-run variance, forecasts, penetration, and raised-bet frequency. Neither sampling interval covers approximation error in machine behavior or policy design.

See [sources, implementation details, tests, and reproduction](../COUNTING_RESEARCH.md).

Coefficient generation and compilation: **3.00 s**. Total wall time: **84.47 s**.

Compiler: `g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`. Python: `3.12.3`. Platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`.
