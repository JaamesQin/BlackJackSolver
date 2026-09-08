# Additional counting methods: held-out evaluation

Experimental six-deck shallow-shoe models, not calibrated Macau continuous-shuffler behavior.

Seed **20260909**; **5,000,000 independent shoes per scenario**; initial bets **1–4**, no skipping. No evaluation outcomes were used to fit or select parameters.

Published tags are implemented with our analytic playing/forecast adapters; these are not the authors' complete published index systems. `composition` uses every visible rank with first-order action sensitivities; it is not an exact finite-shoe optimizer or an upper bound.

The practical threshold was fixed before evaluation at **0.1 percentage point of profit per initial wager**. A detectable improvement, a practically noticeable improvement, and a positive return are separate questions.

## 104-card threshold

± denotes a nominal shoe-clustered 95% confidence half-width. Variance is marginal round-profit variance in squared units. The three betting alternatives share the exact same playing path, so the listed playing runtime is shared, not additive.

| Method | Bets | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Shared runtime (s) |
|---|---|---:|---:|---:|---:|
| baseline | constant | -0.004782 ± 0.000227 | -0.4782% ± 0.0227% | 1.30916 | 7.12 |
| baseline | ramp | -0.003773 ± 0.000274 | -0.3353% ± 0.0243% | 1.89878 | 7.12 |
| baseline | positive-step | -0.002864 ± 0.000387 | -0.2066% ± 0.0279% | 3.79447 | 7.12 |
| hilo | constant | -0.004602 ± 0.000228 | -0.4602% ± 0.0228% | 1.31608 | 8.63 |
| hilo | ramp | -0.003300 ± 0.000286 | -0.2872% ± 0.0249% | 2.07216 | 8.63 |
| hilo | positive-step | -0.002410 ± 0.000392 | -0.1735% ± 0.0282% | 3.90095 | 8.63 |
| halves | constant | -0.004577 ± 0.000228 | -0.4577% ± 0.0228% | 1.31608 | 9.39 |
| halves | ramp | -0.003237 ± 0.000287 | -0.2810% ± 0.0249% | 2.09692 | 9.39 |
| halves | positive-step | -0.002205 ± 0.000398 | -0.1567% ± 0.0283% | 4.02567 | 9.39 |
| hiopt2-ace | constant | -0.004486 ± 0.000228 | -0.4486% ± 0.0228% | 1.31814 | 9.87 |
| hiopt2-ace | ramp | -0.003179 ± 0.000285 | -0.2774% ± 0.0249% | 2.06627 | 9.87 |
| hiopt2-ace | positive-step | -0.002088 ± 0.000396 | -0.1493% ± 0.0283% | 3.97112 | 9.87 |
| omega2-ace | constant | -0.004507 ± 0.000228 | -0.4507% ± 0.0228% | 1.31826 | 6.91 |
| omega2-ace | ramp | -0.003202 ± 0.000287 | -0.2785% ± 0.0249% | 2.08904 | 6.91 |
| omega2-ace | positive-step | -0.002321 ± 0.000398 | -0.1652% ± 0.0283% | 4.01414 | 6.91 |
| ko-centered | constant | -0.004602 ± 0.000228 | -0.4602% ± 0.0228% | 1.31632 | 6.24 |
| ko-centered | ramp | -0.003373 ± 0.000284 | -0.2951% ± 0.0248% | 2.04374 | 6.24 |
| ko-centered | positive-step | -0.002404 ± 0.000394 | -0.1725% ± 0.0282% | 3.93379 | 6.24 |
| composition | constant | -0.004382 ± 0.000228 | -0.4382% ± 0.0228% | 1.31881 | 15.78 |
| composition | ramp | -0.002987 ± 0.000288 | -0.2590% ± 0.0250% | 2.10920 | 15.78 |
| composition | positive-step | -0.001941 ± 0.000399 | -0.1378% ± 0.0283% | 4.04069 | 15.78 |

Total scenario runtime including shuffle and comparisons: **77.72 s**.

## 156-card threshold

± denotes a nominal shoe-clustered 95% confidence half-width. Variance is marginal round-profit variance in squared units. The three betting alternatives share the exact same playing path, so the listed playing runtime is shared, not additive.

| Method | Bets | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Shared runtime (s) |
|---|---|---:|---:|---:|---:|
| baseline | constant | -0.004787 ± 0.000186 | -0.4787% ± 0.0186% | 1.30913 | 10.62 |
| baseline | ramp | -0.002686 ± 0.000255 | -0.2196% ± 0.0208% | 2.45118 | 10.62 |
| baseline | positive-step | -0.001469 ± 0.000353 | -0.0961% ± 0.0231% | 4.69855 | 10.62 |
| hilo | constant | -0.004523 ± 0.000186 | -0.4523% ± 0.0186% | 1.31634 | 12.99 |
| hilo | ramp | -0.001878 ± 0.000268 | -0.1495% ± 0.0214% | 2.72838 | 12.99 |
| hilo | positive-step | -0.000723 ± 0.000358 | -0.0472% ± 0.0234% | 4.85902 | 12.99 |
| halves | constant | -0.004443 ± 0.000186 | -0.4443% ± 0.0186% | 1.31677 | 14.13 |
| halves | ramp | -0.001614 ± 0.000270 | -0.1280% ± 0.0214% | 2.77564 | 14.13 |
| halves | positive-step | -0.000334 ± 0.000363 | -0.0215% ± 0.0234% | 4.99171 | 14.13 |
| hiopt2-ace | constant | -0.004361 ± 0.000187 | -0.4361% ± 0.0187% | 1.31839 | 14.90 |
| hiopt2-ace | ramp | -0.001546 ± 0.000268 | -0.1233% ± 0.0214% | 2.73262 | 14.90 |
| hiopt2-ace | positive-step | -0.000263 ± 0.000361 | -0.0171% ± 0.0234% | 4.93873 | 14.90 |
| omega2-ace | constant | -0.004373 ± 0.000187 | -0.4373% ± 0.0187% | 1.31855 | 10.71 |
| omega2-ace | ramp | -0.001583 ± 0.000270 | -0.1258% ± 0.0214% | 2.76318 | 10.71 |
| omega2-ace | positive-step | -0.000430 ± 0.000363 | -0.0278% ± 0.0234% | 4.98202 | 10.71 |
| ko-centered | constant | -0.004470 ± 0.000186 | -0.4470% ± 0.0186% | 1.31690 | 9.73 |
| ko-centered | ramp | -0.001791 ± 0.000267 | -0.1433% ± 0.0214% | 2.70478 | 9.73 |
| ko-centered | positive-step | -0.000593 ± 0.000360 | -0.0386% ± 0.0234% | 4.91040 | 9.73 |
| composition | constant | -0.004127 ± 0.000187 | -0.4127% ± 0.0187% | 1.31883 | 23.78 |
| composition | ramp | -0.001154 ± 0.000271 | -0.0914% ± 0.0215% | 2.78894 | 23.78 |
| composition | positive-step | +0.000171 ± 0.000364 | +0.0110% ± 0.0234% | 5.00873 | 23.78 |

Total scenario runtime including shuffle and comparisons: **110.74 s**.

## Improvements over the existing Hi-Lo adapter

Differences are percentage points of profit per initial wager, candidate minus Hi-Lo with the same betting policy. The family intervals correct for all reported comparisons and absolute estimates; they are intentionally conservative.

| Threshold | Method / bets | Difference | Nominal 95% CI | Family 95% CI |
|---|---|---:|---:|---:|
| 104 | halves/constant | +0.0025 | [-0.0025, +0.0075] | [-0.0070, +0.0120] |
| 104 | halves/ramp | +0.0062 | [-0.0012, +0.0135] | [-0.0078, +0.0201] |
| 104 | halves/positive-step | +0.0168 | [+0.0044, +0.0292] | [-0.0069, +0.0405] |
| 104 | hiopt2-ace/constant | +0.0116 | [+0.0047, +0.0185] | [-0.0015, +0.0247] |
| 104 | hiopt2-ace/ramp | +0.0098 | [+0.0011, +0.0186] | [-0.0069, +0.0265] |
| 104 | hiopt2-ace/positive-step | +0.0242 | [+0.0107, +0.0377] | [-0.0016, +0.0499] |
| 104 | omega2-ace/constant | +0.0096 | [+0.0026, +0.0165] | [-0.0037, +0.0228] |
| 104 | omega2-ace/ramp | +0.0087 | [-0.0002, +0.0176] | [-0.0083, +0.0257] |
| 104 | omega2-ace/positive-step | +0.0083 | [-0.0054, +0.0219] | [-0.0177, +0.0343] |
| 104 | ko-centered/constant | +0.0001 | [-0.0048, +0.0049] | [-0.0092, +0.0093] |
| 104 | ko-centered/ramp | -0.0079 | [-0.0149, -0.0010] | [-0.0212, +0.0053] |
| 104 | ko-centered/positive-step | +0.0010 | [-0.0111, +0.0131] | [-0.0221, +0.0240] |
| 104 | composition/constant | +0.0220 | [+0.0130, +0.0310] | [+0.0049, +0.0391] |
| 104 | composition/ramp | +0.0281 | [+0.0170, +0.0393] | [+0.0069, +0.0494] |
| 104 | composition/positive-step | +0.0357 | [+0.0203, +0.0511] | [+0.0064, +0.0650] |
| 156 | halves/constant | +0.0080 | [+0.0031, +0.0130] | [-0.0013, +0.0174] |
| 156 | halves/ramp | +0.0215 | [+0.0135, +0.0294] | [+0.0063, +0.0367] |
| 156 | halves/positive-step | +0.0257 | [+0.0147, +0.0366] | [+0.0048, +0.0466] |
| 156 | hiopt2-ace/constant | +0.0162 | [+0.0096, +0.0229] | [+0.0036, +0.0289] |
| 156 | hiopt2-ace/ramp | +0.0262 | [+0.0169, +0.0355] | [+0.0085, +0.0439] |
| 156 | hiopt2-ace/positive-step | +0.0301 | [+0.0179, +0.0422] | [+0.0069, +0.0533] |
| 156 | omega2-ace/constant | +0.0150 | [+0.0083, +0.0217] | [+0.0022, +0.0279] |
| 156 | omega2-ace/ramp | +0.0237 | [+0.0142, +0.0332] | [+0.0056, +0.0418] |
| 156 | omega2-ace/positive-step | +0.0194 | [+0.0071, +0.0317] | [-0.0041, +0.0429] |
| 156 | ko-centered/constant | +0.0053 | [+0.0005, +0.0100] | [-0.0038, +0.0144] |
| 156 | ko-centered/ramp | +0.0062 | [-0.0013, +0.0137] | [-0.0081, +0.0205] |
| 156 | ko-centered/positive-step | +0.0086 | [-0.0020, +0.0192] | [-0.0116, +0.0289] |
| 156 | composition/constant | +0.0396 | [+0.0310, +0.0483] | [+0.0232, +0.0561] |
| 156 | composition/ramp | +0.0581 | [+0.0464, +0.0698] | [+0.0357, +0.0805] |
| 156 | composition/positive-step | +0.0582 | [+0.0439, +0.0724] | [+0.0310, +0.0854] |

## Separating betting effects

Same playing method, changing only the pre-deal bet from constant to ramp or positive-step. Differences below are percentage points of profit per initial wager with family 95% intervals.

| Threshold | Playing method | Bet change | Difference | Family 95% CI |
|---|---|---|---:|---:|
| 104 | baseline | constant → ramp | +0.1429 | [+0.1261, +0.1597] |
| 104 | baseline | constant → positive-step | +0.2716 | [+0.2404, +0.3028] |
| 104 | hilo | constant → ramp | +0.1730 | [+0.1541, +0.1920] |
| 104 | hilo | constant → positive-step | +0.2867 | [+0.2551, +0.3184] |
| 104 | halves | constant → ramp | +0.1767 | [+0.1574, +0.1960] |
| 104 | halves | constant → positive-step | +0.3010 | [+0.2691, +0.3329] |
| 104 | hiopt2-ace | constant → ramp | +0.1713 | [+0.1524, +0.1902] |
| 104 | hiopt2-ace | constant → positive-step | +0.2993 | [+0.2675, +0.3312] |
| 104 | omega2-ace | constant → ramp | +0.1722 | [+0.1530, +0.1914] |
| 104 | omega2-ace | constant → positive-step | +0.2854 | [+0.2535, +0.3173] |
| 104 | ko-centered | constant → ramp | +0.1651 | [+0.1464, +0.1838] |
| 104 | ko-centered | constant → positive-step | +0.2877 | [+0.2559, +0.3194] |
| 104 | composition | constant → ramp | +0.1792 | [+0.1598, +0.1986] |
| 104 | composition | constant → positive-step | +0.3005 | [+0.2685, +0.3324] |
| 156 | baseline | constant → ramp | +0.2591 | [+0.2409, +0.2772] |
| 156 | baseline | constant → positive-step | +0.3826 | [+0.3562, +0.4089] |
| 156 | hilo | constant → ramp | +0.3028 | [+0.2830, +0.3226] |
| 156 | hilo | constant → positive-step | +0.4051 | [+0.3784, +0.4319] |
| 156 | halves | constant → ramp | +0.3162 | [+0.2962, +0.3363] |
| 156 | halves | constant → positive-step | +0.4227 | [+0.3959, +0.4496] |
| 156 | hiopt2-ace | constant → ramp | +0.3128 | [+0.2929, +0.3326] |
| 156 | hiopt2-ace | constant → positive-step | +0.4190 | [+0.3922, +0.4458] |
| 156 | omega2-ace | constant → ramp | +0.3115 | [+0.2915, +0.3315] |
| 156 | omega2-ace | constant → positive-step | +0.4095 | [+0.3827, +0.4363] |
| 156 | ko-centered | constant → ramp | +0.3037 | [+0.2840, +0.3234] |
| 156 | ko-centered | constant → positive-step | +0.4085 | [+0.3817, +0.4352] |
| 156 | composition | constant → ramp | +0.3213 | [+0.3012, +0.3414] |
| 156 | composition | constant → positive-step | +0.4237 | [+0.3968, +0.4505] |

## Interpretation

0 configurations establish a positive return at the family confidence level; 5 have intervals containing zero. The remaining configurations have intervals below zero.

For every new adapter and betting policy, the family interval for improvement over existing Hi-Lo is below the predefined 0.1-percentage-point benchmark. The new methods do not deliver a noticeable increment by that criterion. A statistically detectable improvement can still be smaller than this practical benchmark.

At 104 cards, the largest observed lift over baseline/constant is **composition/positive-step**, **+0.3404 percentage points**, with family interval **[+0.3019, +0.3790]**. This is a descriptive ranking of all reported methods, not a policy selected for a new out-of-sample claim.

At 156 cards, the largest observed lift over baseline/constant is **composition/positive-step**, **+0.4897 percentage points**, with family interval **[+0.4557, +0.5237]**. This is a descriptive ranking of all reported methods, not a policy selected for a new out-of-sample claim.

Raw JSON includes all comparisons with baseline/constant, same-method betting effects, both uncertainty measures, long-run variance, forecasts, penetration, and raised-bet frequency. Neither sampling interval covers approximation error in machine behavior or policy design.

See [sources, implementation details, tests, and reproduction](../COUNTING_RESEARCH.md).

Coefficient generation and compilation: **2.90 s**. Total wall time: **191.39 s**.

Compiler: `g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`. Python: `3.12.3`. Platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`.
