# Blackjack solver and playable strategy table

Play consecutive blackjack rounds in a local browser, compare counting strategies,
and inspect action expected values. The project combines an exact infinite-deck
solver, a finite six-deck simulator, and an interactive table.

The exact baseline derives action EVs from card probabilities using dynamic
programming and Python `Fraction` arithmetic, without simulation or depth cutoffs.
Counting-informed EVs are approximations; finite-shoe outcomes are simulated.

The project also includes an experimental **finite six-deck counting evaluator**:
`python3 -m blackjack evaluate`. It compares the existing strategy with
counting-informed play and separate 1–4-unit betting, under every-round,
26-card (primary), and 52-card reshuffling. See [usage and model limitations](FINITE_SHOE.md)
and [reproducible results](exports/finite_evaluation.md). These shallow-shoe
experiments are not verified or calibrated Macau continuous-shuffler behavior.

Additional researched counts (Wong Halves, Hi-Opt II/Omega II with ace side
counts, centered KO, and full visible composition) are available through
`python3 -m blackjack.counting_research`. See [research and reproduction](COUNTING_RESEARCH.md)
and [the larger 26/52-card comparison](exports/counting_research.md).
Use `--thresholds 104 156` for [the deeper-shoe comparison](exports/deeper_shoe_research.md).

## Play in your browser

Requires Python 3.10 or newer; no runtime dependencies. From this directory:

```sh
python3 -m blackjack gui --open
```

Or run `python3 -m blackjack gui` and open http://127.0.0.1:8765.
Use `--port 9000` to change the port. Stop the server with Ctrl+C.
The page waits for you to choose the first deal.

- Leave starting cards blank for a random hand, or enter two cards such as `8 8`.
  Choose a random dealer or a specific upcard, then click **Deal round**.
- Choose **Hit**, **Stand**, **Double**, or **Split**. After an action requiring a
  card, click **Draw randomly** or type a rank and click **Use card**.
- Split hands play sequentially. Doubles receive one card; split aces receive one
  card each. The dealer completes automatically after all hands finish.
- **Next round** retains the shoe, visible count and session profit. Starting-card
  fields apply only once and clear after a successful deal. **Deal round** uses
  the current shoe; **New shoe & deal** resets the session. The reshuffle selector
  is always visible and changes take effect before the next round. Playing strategy
  is under the collapsed strategy control.
- Default reshuffle threshold is 26 physical cards. Alternatives are 52, 104, 156,
  or every round. Finish the current round before resetting the shoe and count.
  The initial wager is always one unit, with extra wagers for doubles and splits.

The suggested action and EV update after each exposed card. Detailed action EVs
and the baseline comparison are in a collapsed table. Strategy changes preserve
play state. EVs after a split refer only to the active hand; the original split
EV includes both children. Round results include all wagers and hands.

Only visible cards enter recommendations. Hidden dealer cards count toward shoe
penetration but stay private until revealed; they remain unseen when mucked on
player blackjack or all-bust rounds. Manual card entry conditions the remaining
shoe and all unrevealed holes on the supplied rank and prior negative peeks. It
resamples those latent cards, rather than rejecting a card merely because it was
the sampled hole. This conditioning uses rejection sampling with a 10,000-attempt
limit; an incompatible or exceptionally difficult request returns an error without
changing the game. Random draws use the existing shuffled shoe without replacement.

Baseline action EVs are exact for the infinite-deck model. Counting estimates
retain the research approximations: Hi-Lo stationary probabilities, and first-order
rank effects with baseline continuation for other methods. They are not exact
finite-shoe EVs and may be less accurate with depletion. Sampled outcomes are not
EV estimates. The shallow reshuffle policies are experimental approximations,
not verified or calibrated Macau machine behavior.

Run regression tests with `python3 -m unittest discover -s tests`.

## Command-line solver

Python 3.10+; no runtime dependencies. From this directory:

```sh
python3 -m blackjack query 8 8 --upcard A
python3 -m blackjack query A 7 --upcard 6
python3 -m blackjack query 8 A --upcard 6 --origin split
python3 -m blackjack query A 10 --upcard 10 --origin split-aces
python3 -m blackjack query 2 3 4 --upcard 6
python3 -m blackjack overall
python3 -m blackjack export --output exports
python3 -m unittest discover -s tests -v
```

Cards accept `A`, `1`, `2`–`10`, `T`, `J`, `Q`, `K`, case-insensitively;
comma-separated cards also work. Supply cards in deal order. For a split hand,
the first card is the card retained from the pair. Use `split-aces` for aces.
Invalid cards and impossible histories such as hitting an original natural or
drawing after bust are rejected. `--help` describes each command.
Optional installation: `python3 -m pip install .` provides the `blackjack` command.

The Python API returns exact fractions:

```python
from blackjack import Hand, Solver

solver = Solver()
result = solver.query(Hand((8, 8)), 1)
print(result["post_check"]["optimal_actions"])
print(result["post_check"]["actions"])
print(solver.overall()["pre_check_ev"])
```

## Rules and units

In the exact baseline, draws are independent: A and 2–9 each have probability
1/13, tens 4/13. The playable table and evaluator draw without replacement from
a six-deck shoe. The following game and payout rules apply to both models.
Aces count as 1 or 11. The dealer receives a hidden second card and checks for
natural blackjack before any player decision. Dealer blackjack wins against
everything except a player natural, which pushes. An original two-card A–10
pays +1.5 when the dealer has no natural. The dealer hits below 17 and stands on
all 17s, including soft 17.

The player can hit or stand; bust loses immediately. Any two-card hand can
double, taking exactly one card and standing, except split aces. An original
pair of equal point value can split once; no resplitting. Non-ace split hands
can double. Split aces take one card each and stand. Split 21 is ordinary 21.
Both split hands face the same dealer. Ordinary wins/losses return +1/−1 per
wager, ties 0. No surrender, insurance, side bets, or bankroll constraints.

All EVs are **net profit in original-bet units**, including extra wagers:
double outcomes are +2/0/−2; the split action includes both hands and any later
doubles, so round payoff can range from −4 to +4. Stakes returned on a push
are not profit. Querying one already-split hand reports that hand's contribution
in original-bet units, excluding its sibling. Such a query describes a live
one-unit hand, not a hand already completed by doubling.

`post_check` conditions on the dealer having no natural. `pre_check.actions`
means "take this action if the dealer check clears, then play optimally";
there is no actual decision before the check. For a non-natural initial hand,
with dealer blackjack probability `q`, each action satisfies:

```text
EV_before(action) = -q + (1-q) * EV_after(action)
EV_before(player natural) = (1-q) * 3/2
q = 4/13 against A; 1/13 against ten; 0 otherwise
```

Thus no split or double stake is lost to a dealer natural: these stakes have
not been placed yet. `dealer_blackjack_probability` is this **prior** `q`, not
the probability after a negative check (which is zero). `pre_check` is null
for split or multi-card hands because these occur after the check.
Naturals and busts have settlement values and no legal actions. Split aces
have only forced stand. Every exact tie is returned in `optimal_actions`.

## Derivation

`blackjack/solver.py` separates the draw model, hand/provenance validation,
dealer probabilities, action recurrences, and initial-deal integration.

1. Enumerate the dealer hole card, excluding A–10 naturals, and normalize by
   `1-q`. Recursively draw below 17 to obtain probabilities of bust and 17–21.
2. For player total `t <= 21`, stand value `S(t)` is dealer bust probability
   plus probability of lower dealer totals minus probability of higher totals.
   Define `S(bust) = -1`, even when the dealer would bust.
3. For continuation hand `h`, define `V(bust) = -1` and
   `V(h) = max(S(h), sum_c p(c)*V(h+c))`. After a hit, double/split are illegal.
4. At two cards, additionally evaluate `2*sum_c p(c)*S(h+c)` for double.
   For a non-ace pair `r,r`, split value is
   `2*sum_c p(c)*max(stand(r,c), hit(r,c), double(r,c))`.
   For aces use `2*sum_c p(c)*stand(A,c)`. No split child receives natural pay
   or can split again.
5. Choose the maximum legal value, apply the pre-check mixture, and average
   over all player deals and dealer upcards. The 55 unordered player pairs
   carry probability `p(c)*p(d)` for equal cards and `2*p(c)*p(d)` otherwise.

The internal state is total plus whether an ace currently counts as 11;
provenance and two-card privileges are handled at decision boundaries.
Every draw increases the sum with all aces counted as 1, so recursion terminates
without a cutoff. Memoization reuses derived values. A shared dealer correlates
split outcomes, but expectation is additive. Under independent draws, playing
one split hand does not change the other hand's or dealer's distribution.

## Results and exports

For exactly these rules:

| Quantity | Net original-bet units |
|---|---:|
| Overall EV before dealer check | **−0.005703880122735894** |
| House edge per initial bet | **0.5703880122735894%** |
| Overall EV conditional on no dealer natural | +0.04134997536897865 |
| Probability of dealer natural | 8/169 = 0.047337278106508875 |

The conditional overall EV reweights upcards by the chance that the check
clears and includes winning player naturals. It is not the unconditional
profit and is not a simple unweighted average of post-check table entries.
The exact unconditional EV is:

```text
-40248916821673328324125295 / 7056410014866816666030739693
```

Generated files in `exports/`:

| File | Contents |
|---|---|
| `overall.json` | Overall EVs, house edge, and dealer natural probability |
| `initial.json` | All 550 initial hand/upcard cases, all action EVs before/after check, exact fractions and decimal previews |
| `initial.csv` | Same initial strategies and EVs in spreadsheet form |
| `continuation.csv` | 250 reachable non-bust multi-card total/soft/upcard states; stand/hit EVs after check |
| `split_hands.csv` | 1,000 split-card/drawn-card/upcard cases, including forced split aces, after check |

CSV decimals are rounded only during serialization; blank action cells mean
illegal actions. JSON EV objects contain `decimal` and lossless `exact` fields.
Use Python API fractions for lossless continuation/split-hand EVs.

## Verification

Run `python3 -m unittest discover -s tests -v`. Interactive-table regressions cover
manual and random draws, consecutive rounds, sequential splits, doubles, hidden-card
isolation, invalid-action rollback, and changing shuffle settings between rounds.

The unittest suite verifies exact probability normalization, initial-deal mass,
soft-17 standing, multiple aces, natural settlement, peek conditioning for
every action, bust priority, action legality, and split/double wager scaling.
It explicitly enumerates both split-ace draws against a **single shared dealer
outcome** and checks the joint EV equals the additive split recurrence.

An independent oracle uses 60-digit decimal arithmetic, ace-as-one sums and
ace presence, and a bottom-up player dynamic program. It independently builds
dealer distributions and compares every legal action in all 550 initial
cases, every legal action in all 1,000 split-hand cases, continuation values,
and overall EV to exact results within `1e-55`.
The few familiar strategy examples are test assertions only; the solver never
reads them. CLI success/error handling and export row counts are also tested.

## Extension path and limitations

The original exact engine implements the specified infinite-deck rules only. It calculates expected
profit, not variance, a round payoff distribution, or bankroll risk.
`IndependentDrawModel` isolates a stationary probability law and accepts exact
probabilities, making alternate independent draw laws possible. It is **not**
a finite-shoe implementation.

An exact finite-shoe EV solver remains future work. It would require an immutable
round state containing remaining
counts for A through ten, visible cards, hand provenance/wagers, pending split
hands, and dealer information. Transitions must return both the next state and
its probability, removing drawn cards. Cache keys must include composition.
Maintain the posterior over the unobserved dealer hole card, conditioned on
the peek result and later observations; the policy must never see the actual
hidden card. Dealer terminal probabilities then depend on the updated shoe.
Solve split hands jointly and sequentially because draws from one change the
other's possibilities; the present `2 * single_hand_EV` shortcut no longer
applies. Retain the current infinite-deck engine as a regression reference.

The existing counting policies use observable information and are evaluated
against finite-shoe outcomes with separate playing and betting decisions. They
do not solve composition-dependent finite-shoe optimal play. Count-adjusted
stationary probabilities and first-order rank effects remain approximations.
