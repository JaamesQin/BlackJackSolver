# Experimental finite-shoe counting evaluation

The simulator uses one player and a finite six-deck shoe: 24 aces, 24 of each
rank 2–9, and 96 ten-valued cards. It preserves the original solver's S17,
dealer peek, 3:2 natural, double on any two cards, double after splitting,
one split/no resplit, and one-card-only split aces rules. Split 21 is ordinary
21. There is no surrender, insurance, skipping, bankroll limit, or other player.
The original exact infinite-deck solver and its exports are preserved.

These are **experimental shallow-shoe approximations**, not verified or fully
calibrated Macau continuous-shuffler behavior. The primary scenario returns all
cards after the round that reaches **26 physically dealt cards out of 312**.
The comparisons use every-round reshuffling and a 52-card threshold. A fresh,
uniformly shuffled full shoe starts each cycle. Cards are never returned within
a cycle; a threshold never interrupts a round. Threshold overshoot is reported.

Larger 104- and 156-card thresholds are also supported as sensitivity studies:
`python3 -m blackjack evaluate --policies 104 156`. The expanded seven-method
comparison uses `python3 -m blackjack.counting_research --thresholds 104 156`;
see [the deeper-shoe results](exports/deeper_shoe_research.md).

A machine can recycle small groups of used cards into its remaining stock
without the complete resets used here; see the background description in
[US11376489B2, page 28 of the PDF](https://patentimages.storage.googleapis.com/ed/4c/56/2b16c9b94fbb0a/US11376489.pdf#page=28).
That source supplies context, not empirical support for 26/52-card thresholds
or any particular Macau installation. The simulator does not model an output
buffer, reinsertion delay, mixing dynamics, burn cards, or multiple seats.

## Run and reproduce

Python 3.10+, standard library only:

```sh
# Default comparison: all three reshuffle policies; 100,000 shoes per mode.
python3 -m blackjack evaluate

# Reproduce the checked-in evaluation (250,000 independent shoes per mode).
python3 -m blackjack evaluate --shoes 250000 --seed 20260907 \
  --output exports/finite_evaluation.json

# Primary 26-card scenario with a configurable 1–4-unit betting ramp.
python3 -m blackjack evaluate --policies 26 --min-bet 1 --max-bet 4 \
  --full-bet-edge 0.01 --shoes 100000 --seed 12345 \
  --output /tmp/finite-26.json

# Quick smoke test; too small to infer profitability.
python3 -m blackjack evaluate --shoes 100 --output /tmp/finite-smoke.json
python3 -m unittest discover -s tests -v
```

The command writes JSON and a companion Markdown report. Progress and per-mode
runtime go to stderr. `--shoes` counts complete independent shoe cycles, not
rounds. Each mode has the same number of cycles, but playing decisions and
penetration change its number of rounds. The seed reproduces numerical results
on the recorded Python implementation/version; wall-clock timing varies.
All four modes use matching shuffled shoes to reduce comparison noise.

Read the measured results in [the evaluation report](exports/finite_evaluation.md)
and the full [JSON output](exports/finite_evaluation.json).

## Information boundaries and dealing convention

The deal order is player card, dealer upcard, player card, dealer hole card.
All four physically leave the shoe. The player observes only the first three
ranks before the dealer check. A dealer natural reveals the hole card and ends
the round before any playing action or additional wager. Otherwise player
naturals receive 3:2 and the ordinary hands are played.

The dealer reveals the hole card when settling at least one non-busted ordinary
hand, then draws below 17. If the player has a natural or every player hand
busts, the dealer hole card is **mucked unseen** and the dealer does not draw.
This conservative visibility convention is part of this experiment. All dealt
cards, including those mucked face down, count toward the reshuffle threshold.
The simulator never later reveals a mucked rank to the counter.

Split hands are played sequentially: the first child receives its additional
card and finishes before the second child's additional card is dealt. The
second hand's strategy can use cards seen on the first. Both face the same
dealer. No resplitting is allowed, and split aces are forced to stand.

`Observation` contains an immutable tuple of visible rank counts and the
public number of physically dealt cards. Policies receive that snapshot,
their own current hand, its origin, and the dealer upcard. They receive neither
the shoe nor the random generator, hidden ranks, or future ranks. An estimate
and initial bet are computed before the engine draws the first card of a round.
A new `Counter` is constructed at every reshuffle, including every-round mode.

## Playing strategy and next-round forecast

Baseline play takes exactly the action selected by the existing `Fraction`
solver, with its stand-first tie ordering. It ignores the count for playing.

Counting-informed play uses Hi-Lo: 2–6 add +1, aces/tens add −1, 7–9 add zero.
It updates after each visible card, including the current round's cards. Let
`RC` be this running count and `U = 312 - number_of_visible_cards`. The policy
uses `TC = 52 * RC / U`. The unseen pool includes undealt cards and hidden,
mucked hole cards; dividing by only the physical shoe remainder would pretend
those hidden ranks were already known. This is an observable-count estimate,
not a claim to know the actual undealt composition.

At each decision, round TC to the nearest quarter (Python ties-to-even) and
clip to [−12, +12]. The grid is configurable with `--count-step`. For a grid
value `t`, approximate stationary draw probabilities are:

| Rank | Approximate probability |
|---|---:|
| Ace | `1/13 + t/520` |
| Each 2–6 | `1/13 - t/520` |
| Each 7–9 | `1/13` |
| Ten-valued | `4/13 + 4*t/520` |

They are positive and sum to one throughout the grid. The linear approximation
allocates the observed low-versus-high imbalance equally among individual low
and high ranks. It discards within-group rank composition and neutral-card
removal effects. These probabilities feed a bottom-up dynamic program with the
same actions, dealer peek conditioning, and payouts as the original solver.
The tables use double-precision floats; tests compare every initial action at
zero and nonzero counts with the exact rational engine to 13 decimal places.

The simulator still deals **without replacement**. Only the strategy tables
assume stationary independent draws. Consequently, they approximate effects
of depletion within a hand, dealer/player dependence, split-hand dependence,
and the finite-shoe effect of a negative peek. The table conditions the dealer
on no natural, but does not update future player draws for that constraint.
Historical negative-peek information about unrevealed mucked cards is ignored.
This is a practical counting policy, not exact composition-dependent optimal play.

Before a round, the same observable count selects an approximate unconditional
next-round EV per unit of initial wager. Baseline forecasts evaluate the fixed
baseline policy under adjusted probabilities; counting forecasts evaluate the
optimized policy under them. The forecast freezes the count over hypothetical
future play, while actual counting play updates as observations arrive. It
also approximates the initial finite-shoe deal as independent draws. Forecasts
are therefore not calibrated conditional finite-shoe EVs. At a fresh shuffle,
both forecast −0.0057038801227359, the infinite-deck baseline EV.

The output reports average forecast, realized unit profit, and a cluster-based
confidence interval for their mean difference. This checks aggregate bias;
it does not establish conditional calibration at each count.

## Betting is separate

The four comparisons are baseline/constant, baseline/bounded,
counting/constant, and counting/bounded. Constant bets always use the minimum
(default 1). Both bounded modes use the forecast appropriate to their playing
policy. For forecast `e`, minimum `m`, maximum `M`, and full-bet edge `f`:

```text
initial_bet = m + (M - m) * min(1, max(0, e / f))
```

Defaults are `m=1`, `M=4`, and `f=0.01`. Bets can be fractional units, stay within
the bounds, and never skip a round. All nonpositive forecasts receive the
minimum; a forecast of +0.5% receives 2.5 units; +1% receives 4. Doubles and
splits multiply this already selected initial bet and may put up to four times
it at stake. Their additional wagers do not enter the initial-wager denominator.
Playing decisions never receive the bet or bankroll.

Every-round reshuffling erases pre-round counting information. Thus bounded
and constant wagers are identical under defaults, though counting can still
change playing decisions using the newly visible cards during that round.

No parameters were tuned on simulated outcomes. The count mapping, grid,
and betting ramp were fixed before evaluation. There is no fitted regression,
training split, or selected best seed. If parameters are tuned in a later
experiment, use separate seeds/data for training and final evaluation; do not
select a policy or seed by the best reported evaluation profit.

## Statistical interpretation

Profit is net units after settlement, including additional split/double stakes.
For each mode, the report supplies:

- Expected profit per round, estimated as total profit divided by total rounds.
- Profit relative to total **initial** wagers, estimated as a ratio of totals.
- Standard errors and approximate 95% confidence intervals for both ratios.
- Marginal per-round profit variance in squared units, and long-run variance
  per round including dependence between rounds in the same shoe.
- Total rounds, wagers, raised-bet frequency, mean and maximum penetration,
  hidden-card counts, and simulation wall-clock runtime.

Whole shuffled shoes are independent regenerative clusters. If shoe `j` has
profit `X_j` and `N_j` rounds, estimate `mu = sum(X_j)/sum(N_j)`. The standard
error is `sqrt(K/(K-1) * sum((X_j - mu*N_j)^2)) / sum(N_j)`. For profit/wagers,
replace `N_j` by total initial wagers `W_j`. This handles random cycle lengths
and dependence within shoes; treating every round as independent would not.
The marginal variance is `sum(round_profit^2)/N - mu^2`; the long-run variance
is `sum((X_j-mu*N_j)^2)/(K-1) / mean(N_j)`.

Matched-shoe comparisons use differences of the two ratio estimators' cluster
influence values. This remains valid when playing differences change the number
of rounds in a shoe. Confidence intervals describe Monte Carlo uncertainty
under this model, not uncertainty about casino rules, machine dynamics, or the
accuracy of the policy's forecast. They are asymptotic, with no multiple-testing
adjustment. Small smoke runs are not suitable for conclusions. Runtime excludes
table construction in each mode; construction is reported separately once.

## Code and tests

- `blackjack/finite.py`: physical shoe, visibility, dealing, and settlement.
- `blackjack/counting.py`: public observations, baseline actions, approximate
  count tables, next-round estimates, and bounded betting policy.
- `blackjack/evaluation.py`: complete-cycle evaluation, cluster uncertainty,
  matched-shoe comparisons, and reports.
- `tests/test_finite.py`: exact-table comparisons, known-payoff rounds, split
  wager scaling, soft 17, hidden-card/future-card invariance, bet-before-deal
  timing, threshold overshoot, counting reset, ratio errors, and reproducibility.

Python API example for an observed-card forecast (no private shoe needed):

```python
from blackjack.counting import Counter, StrategyTables, BettingPolicy

tables = StrategyTables()
observed = Counter()
for visible_card in [2, 3, 4, 6, 10, 7]:
    observed.observe(visible_card)
    observed.dealt += 1
edge = tables.estimate(observed.snapshot(), playing="counting")
initial_bet = BettingPolicy(bounded=True).choose(edge)
print(edge, initial_bet)
```
