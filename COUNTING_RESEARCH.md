# Researching additional counting methods

This extends the [finite-shoe experiment](FINITE_SHOE.md) with five additional
counting-information models and a larger independent evaluation. The original
rules, visibility convention, 26/52-card round-end reshuffling, and no-skipping
constraint are preserved. These remain **experimental approximations**, not
verified or calibrated Macau continuous-shuffler behavior.

## Research and methods

The useful distinction is between information for playing decisions and
information for betting. QFIT's published comparison describes betting
correlation and playing efficiency as different measures; neither measures
performance under our particular shallow-shoe model. Its software strategy
catalog states that the included strategy tables have permission from their
respective copyright holders. We use the published card tags and derive our own
adjustments, without importing proprietary strategy tables.
[QFIT comparison](https://www.qfit.com/card-counting.htm),
[QFIT strategy catalog](https://www.qfit.com/card_counting_systems.htm).

| Implemented adapter | A | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | T | Extra information |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Existing Hi-Lo | −1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | −1 | None |
| Wong Halves | −1 | 0.5 | 1 | 1 | 1.5 | 1 | 0.5 | 0 | −0.5 | −1 | None |
| Hi-Opt II + aces | 0 | 1 | 1 | 2 | 2 | 1 | 1 | 0 | 0 | −2 | Visible ace count |
| Omega II + aces | 0 | 1 | 1 | 2 | 2 | 2 | 1 | 0 | −1 | −2 | Visible ace count |
| KO, centered | −1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | −1 | Visible card count to remove drift |
| Full composition | — | — | — | — | — | — | — | — | — | — | All ten visible rank counts |

Wong Halves distinguishes low cards using fractional weights and includes
aces in its main count. Hi-Opt II and Omega II use zero for aces, motivating
separate ace information. QFIT documents ace side counts for betting and
separate side-count adjustments for play. Our two-feature adapters use ace
information in both tasks; they are not the authors' original side-count
index schemes.
[Wong Halves](https://www.qfit.com/cardcounting/Wong-Halves/),
[Hi-Opt II](https://www.qfit.com/cardcounting/Hi-Opt-II/),
[Omega II](https://www.qfit.com/cardcounting/Omega-II/),
[side-count implementation guidance](https://www.qfit.com/blackjack-side-counting-setup.htm).

KO is unbalanced: its tags sum to +4 per deck. We center each tag by its
full-deck mean, 1/13, and use the unseen-card denominator. This **KO-tag
adapter is not conventional KO with its initial running count and fixed
pivot/index rules**. The tag and balance distinction follow the
[QFIT comparison](https://www.qfit.com/card-counting.htm).

Full composition is a computer-assisted information benchmark, substantially
more demanding than keeping a scalar count. It retains all observed rank
removals instead of grouping ranks. Its playing calculation is still an
approximation, so it is **not an optimal finite-shoe policy or an upper bound**.
None of the methods can use insurance, surrender, unseen dealer ranks, future
ranks, or cards from a previous shuffle. Published insurance-efficiency numbers
therefore offer no benefit in this experiment.

## Common analytic adaptation

The original Hi-Lo adapter is preserved exactly: a quarter-true-count grid,
stationary draw-law optimization, and its original forecast. The baseline still
plays the original exact infinite-deck policy. The new methods use a common
first-order approximation so their information content can be compared without
fitting a different model to simulation outcomes for each one.

Let `p` be the infinite-deck rank distribution, `n` the number of visible cards,
`v_c` the number seen of rank `c`, and `U=312-n`. The full-composition probability
shift is:

```text
delta_c = (n*p_c - v_c)/U
```

For a tag vector `t`, center it as `t'_c = t_c - sum(p*t)`. The projected shift is:

```text
R = sum(v_c*t'_c)
variance = sum(p_c*t'_c^2)
projected_delta_c = -p_c*t'_c*R/(U*variance)
```

This is a weighted linear projection of the rank information onto the count.
For Hi-Opt II and Omega II, add the projection onto the centered ace indicator.
Their balanced ace-neutral counts are orthogonal to that indicator under `p`,
so the two projected shifts can be added. This is an analytic approximation to
conditional composition, not an exact posterior distribution. Historical
negative-peek constraints on hidden mucked cards are ignored as before.

We derive action values `Q_0` and sensitivities `g` from the existing stationary
solver, following the **fixed baseline policy after the candidate action**:

```text
Q_approx(action) = Q_0(action) + sum(g_action,c * projected_delta_c)
```

Sensitivities use central differences with `epsilon=1e-5` in directions
`unit_rank_c - p`; this keeps probability mass normalized. The policy selects
the best legal approximate action at every new observation. It retains the
same split/double privileges and special treatment of split aces. The simulator
itself deals without replacement and settles actual outcomes.

The next-round forecast uses the same first-order expansion of baseline-policy
EV. It is computed before dealing. It does not anticipate all future policy
changes, and it does not include an empirically calibrated finite-deck intercept.
This differs from the existing Hi-Lo optimized-grid forecast. Consequently,
comparisons with Hi-Lo test the **whole adapter**, not just a substitution of
count tags into an identical nonlinear solver. Same-framework comparisons among
the five new methods more directly compare their information content.

No coefficients were fitted to sampled outcomes. No betting or playing
parameters were selected from the final evaluation. Validation uses seed 77123
and deterministic numerical directions; the final experiment uses seed
**20260908**, separate from the previous experiment's 20260907.

## Betting comparisons

All methods are evaluated under three separate policies:

1. **constant:** always 1 unit by default.
2. **ramp:** the existing linear 1–4-unit ramp; minimum for a nonpositive
   forecast, maximum at a forecast of +1%.
3. **positive-step:** 4 units for a strictly positive forecast, otherwise 1.

The step policy tests a more aggressive use of small positive forecasts. If
the conditional EV were known exactly, maximizing one-round expected profit
under a fixed [1,4] bound would choose the upper bound for positive EV and the
lower bound for negative EV. Here the forecast is approximate, so that argument
does not establish the policy's actual profitability. It also does not minimize
variance or bankroll risk. The measured variance is reported.

The baseline's variable-bet policies use the existing Hi-Lo forecast evaluated
for baseline play, matching the earlier experiment. All bets are determined
before the round's first card. Playing never receives the wager. Thus the same
unit-profit trajectory can evaluate all three precommitted betting policies
exactly, without rerunning the playing path or leaking future information.

## Reproduce

The core package still requires only Python's standard library. The larger
research evaluation additionally uses **g++ with C++17** for speed. It compiles
an evaluator and writes its model coefficients into a temporary directory;
there are no installed Python dependencies or checked-in executable binaries.

```sh
# Main checked-in experiment: five million independent shoes per scenario.
python3 -m blackjack.counting_research --shoes 5000000 --seed 20260908 \
  --output exports/counting_research.json

# Smaller run, with the same methods and all three betting policies.
python3 -m blackjack.counting_research --shoes 100000 --seed 123456 \
  --output /tmp/counting-comparison.json

# Deeper-shoe sensitivity study: 104 and 156 cards (one third and half a shoe).
python3 -m blackjack.counting_research --thresholds 104 156 \
  --shoes 5000000 --seed 20260909 --output exports/deeper_shoe_research.json

# Configurable betting limits and ramp; every round is still played.
python3 -m blackjack.counting_research --shoes 100000 \
  --min-bet 1 --max-bet 4 --full-bet-edge 0.01 \
  --output /tmp/counting-custom.json

python3 -m unittest discover -s tests -v
```

The default research sample is two million shoes per scenario; the checked-in
run uses five million, fixed before inspecting its outcomes. The default
thresholds are 26 and 52; `--thresholds` selects distinct values from 26, 52,
104, and 156. A JSON checkpoint containing sufficient statistics is
written after each completed scenario. The final JSON and Markdown report
contain the results and comparisons. Runtime is hardware-dependent.

- [Measured results and interpretation](exports/counting_research.md)
- [All metrics and paired comparisons](exports/counting_research.json)
- [Raw sufficient statistics](exports/counting_research.moments.json)
- [104/156-card results](exports/deeper_shoe_research.md)

The deeper-shoe run uses the same frozen coefficients, count limits, and bet
settings, with a separate seed and output. Dealing, hidden-card treatment,
and round-end reshuffling are identical. Larger thresholds are sensitivity
experiments, not claims about Macau shuffler penetration. First-order policy
and forecast approximations may be less accurate farther from a full shoe;
the physical simulator still draws without replacement. The Hi-Lo adapter
retains its original ±12 true-count cap. No parameters are recalibrated for
104 or 156 cards.

The completed deeper-shoe run used five million independent shoes at each
threshold and the exact same coefficient SHA-256 as the 26/52-card experiment.
At 104 cards, full composition with positive-step bets returned −0.1378% of
initial wagers, versus −0.4782% for baseline constant bets. At 156 cards,
the same combination reached a point estimate of +0.0110%, but its nominal
95% interval [−0.0124%, +0.0344%] and family interval
[−0.0337%, +0.0557%] both include zero. Thus the half-shoe experiment approaches
break-even without establishing a positive player edge. All constant-bet and
ramp configurations remain negative.

Full composition does now measurably outperform Hi-Lo with the same
positive-step bets: +0.0357 percentage points at 104 cards (family interval
[+0.0064, +0.0650]) and +0.0582 at 156 ([+0.0310, +0.0854]). Both gains remain
below the 0.1-point practical benchmark. At 156 cards, round-profit variance
is 5.00873 for full composition/positive-step, versus 1.30913 for baseline
constant bets. Scenario runtimes were 77.72 seconds and 110.74 seconds;
including compilation and coefficient generation, the full run took 191.39
seconds. See the linked report for all seven methods and three betting policies.

In this fixed experiment, no new adapter's improvement over Hi-Lo reaches the
predefined 0.1-percentage-point benchmark: even the upper family confidence
bounds are below it. The largest point improvement over Hi-Lo using the same
bets is full composition with positive-step bets, +0.0217 percentage points at
26 cards and +0.0283 at 52; both family intervals include zero.

Changing betting has a larger effect. Hi-Lo's positive-step policy improves
profit per initial wager over Hi-Lo constant bets by +0.0499 percentage points
at 26 cards and +0.1396 at 52. The latter's family interval is
[+0.1026, +0.1767], above the noticeable-improvement benchmark. This is a
reduction in losses: its 52-card return is still −0.3193%.

The highest observed return is full composition with positive-step bets:
−0.3920% at 26 cards and −0.2910% at 52. Relative to baseline constant bets,
the respective lifts are +0.0753 and +0.1772 percentage points, with family
intervals [+0.0346, +0.1161] and [+0.1332, +0.2211]. Only the latter establishes
a lift above the declared benchmark. Its 52-card per-round variance is 2.63865,
versus 1.30950 for baseline constant bets. Every absolute return remains negative
at the family confidence level. These findings apply to the implemented
adapters and model, not to all possible counting strategies.

Reproducibility metadata records the coefficient SHA-256, finite-difference
step, compiler, RNG, seed, platform, and bet settings. Shuffling uses
`std::mt19937_64`, an explicitly implemented unbiased bounded draw, and a
descending Fisher–Yates shuffle. Each scenario starts a fresh RNG with the
specified seed. All methods receive the same sequence of full-shoe permutations.
They can finish different numbers of rounds, which the paired statistics handle.

## Uncertainty and what counts as an advantage

The experiment fixes **0.1 percentage point** of improvement in profit per
initial wager as a practical noticeable-improvement benchmark. That is a design
choice, not a universal definition of economic significance.

A detectable reduction in losses, an improvement exceeding that benchmark,
and a positive absolute return are reported as separate questions. The data
include comparisons with baseline/constant, with the original Hi-Lo adapter
under the same betting policy, and between betting policies within a method.

As before, independent complete shoes are the sampling clusters. Random round
counts and total initial wagers are handled as ratio denominators. The C++
evaluator accumulates both within-mode moments and cross-mode moments; Python
constructs the same paired influence-function intervals as the original
explicit per-shoe implementation. Nominal 95% intervals are accompanied by
conservative **Bonferroni family 95% intervals**, covering all reported absolute
and paired estimates for both profit metrics (272 estimates in this design).
No independence between methods is needed for that correction.

Per-round variance, long-run variance, mean bets, raised-bet frequency,
forecast bias, penetration, and runtime are retained. The three betting
alternatives share a playing path; their displayed runtime must not be summed
three times. The many simulated paths across methods are also matched, not
independent samples. Confidence intervals quantify sampling error under the
specified game, not error in the machine model, linear policy approximation,
rank projection, or forecast calibration.

## Implementation checks

The tests compare the C++ and original Python engines on **150 identical full
shoes at each of 26, 52, 104, and 156 cards for all seven methods**, checking every round's unit
payoff, pre-deal forecast, all three bets, cards dealt, and cards exposed.
Other tests check:

- Original baseline and Hi-Lo adapter decisions are preserved.
- Probability projections preserve mass and center KO's drift correctly.
- Ace side counts distinguish observations with identical main counts.
- Action/EV derivatives agree in an independent numerical direction.
- Cross-moment paired errors match explicit per-shoe paired errors.
- The accelerator reproduces its results with the same seed.
- Existing tests still cover hidden/future-card invariance, betting before
  dealing, split/double stakes, dealer peek, soft 17, and reshuffle timing.

Files: `blackjack/counting_methods.py` defines the adapters and exports
coefficients; `research/counting_benchmark.cpp` performs fast physical
simulation; `blackjack/counting_research.py` runs and reports the experiment.
The new methods are also callable from the Python simulator via `ResearchPolicy`.
