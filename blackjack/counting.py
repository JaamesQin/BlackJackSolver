"""Observable Hi-Lo policy with a stationary, count-adjusted EV approximation.

The simulator is finite-shoe; these decision tables deliberately are not an
exact finite-shoe solution. No simulated or evaluation outcomes tune the tables.
"""
from dataclasses import dataclass
from functools import cache
import math

from .solver import Hand, Solver

HI_LO = (0, -1, 1, 1, 1, 1, 1, 0, 0, 0, -1)
BASE = (0.0,) + (1 / 13,) * 9 + (4 / 13,)


@dataclass(frozen=True)
class Observation:
    """Public information only. Unseen includes face-down discarded hole cards."""
    visible_counts: tuple[int, ...] = (0,) * 11
    dealt: int = 0

    @property
    def running_count(self):
        return sum(n * tag for n, tag in zip(self.visible_counts, HI_LO))

    @property
    def true_count(self):
        unseen = 312 - sum(self.visible_counts)
        return self.running_count * 52 / unseen


class Counter:
    """Only the game engine records physically dealt and legitimately seen cards."""
    def __init__(self):
        self.counts = [0] * 11
        self.dealt = 0

    def observe(self, card):
        self.counts[card] += 1

    def snapshot(self):
        return Observation(tuple(self.counts), self.dealt)


def adjusted_probabilities(true_count):
    """Linear conditional-composition approximation, per individual rank.

    Five low ranks lose RC/10 cards each; five high ranks gain RC/10 each
    (four high ranks are aggregated as ten). This preserves total mass and
    the observed high-minus-low imbalance. Neutral ranks retain base mass.
    """
    if not math.isfinite(true_count) or abs(true_count) > 12:
        raise ValueError("Table true count must be finite and in [-12, 12]")
    return tuple(0.0 if c == 0 else BASE[c] - HI_LO[c] *
                 (4 if c == 10 else 1) * true_count / 520 for c in range(11))


def state(cards):
    raw = sum(cards)
    return raw, 1 in cards


def total(raw, ace):
    return raw + 10 if ace and raw <= 11 else raw


class Baseline:
    """Decisions from the existing exact infinite-deck solver, including ties."""
    def __init__(self):
        s = Solver()
        self.continuation = {}
        self.two = {}
        for up in range(1, 11):
            for raw in range(2, 22):
                for ace in (False, True):
                    t = total(raw, ace)
                    soft = ace and raw <= 11
                    # Match the production stand-first tie order exactly.
                    self.continuation[up, raw, ace] = (
                        "hit" if s._hit(t, soft, up) > s.stand(t, up) else "stand")
            for origin in ("original", "split", "split-aces"):
                for c in range(1, 11):
                    if (origin == "split" and c == 1) or (origin == "split-aces" and c != 1):
                        continue
                    for d in range(1, 11):
                        h = Hand((c, d), origin)
                        a = s.actions(h, up)
                        if a:
                            self.two[up, c, d, origin] = max(a, key=a.get)

    def choose(self, cards, upcard, origin, observation):
        if len(cards) == 2:
            return self.two[upcard, cards[0], cards[1], origin]
        raw, ace = state(cards)
        return self.continuation[upcard, raw, ace]


class Approximation:
    """Float bottom-up DP; either optimize or evaluate the fixed baseline policy."""
    def __init__(self, probabilities, baseline=None):
        self.p = probabilities
        self.continuation = {}
        self.two = {}
        self.dealers = {}
        self.action_values = {}
        self.state_action_values = {}
        self.initial_values = {}
        for up in range(1, 11):
            self._build_upcard(up, baseline)
        self.edge = sum(self.p[up] * self.p[c] * self.p[d] *
                        self.initial_values[up, c, d]
                        for up in range(1, 11) for c in range(1, 11) for d in range(1, 11))

    def _build_upcard(self, up, baseline):
        p = self.p

        @cache
        def dealer(raw, ace):
            t = total(raw, ace)
            if t >= 17:
                slot = 0 if t > 21 else t - 16
                return tuple(float(i == slot) for i in range(6))
            out = [0.0] * 6
            for c in range(1, 11):
                for i, prob in enumerate(dealer(raw + c, ace or c == 1)):
                    out[i] += p[c] * prob
            return tuple(out)

        q = p[10] if up == 1 else p[1] if up == 10 else 0.0
        dist = [0.0] * 6
        for c in range(1, 11):
            if {c, up} == {1, 10}:
                continue
            for i, prob in enumerate(dealer(up + c, up == 1 or c == 1)):
                dist[i] += p[c] * prob / (1 - q)
        self.dealers[up] = tuple(dist)
        stand = {t: (-1.0 if t > 21 else dist[0] + sum(
            prob * ((t > d) - (t < d)) for d, prob in zip(range(17, 22), dist[1:])))
                 for t in range(2, 32)}
        values = {}
        actions = {}
        for raw in range(21, 1, -1):
            for ace in (False, True):
                t = total(raw, ace)
                hit = sum(p[c] * (-1.0 if raw + c > 21 else values[raw + c, ace or c == 1])
                          for c in range(1, 11))
                double = 2 * sum(p[c] * stand[total(raw + c, ace or c == 1)] for c in range(1, 11))
                a = {"stand": stand[t], "hit": hit, "double": double}
                actions[raw, ace] = a
                self.state_action_values[up, raw, ace, 0] = {k: a[k] for k in ("stand", "hit")}
                self.state_action_values[up, raw, ace, 1] = dict(a)
                choice = baseline.continuation[up, raw, ace] if baseline else (
                    "hit" if hit > stand[t] else "stand")
                self.continuation[up, raw, ace] = choice
                values[raw, ace] = a[choice]
        split = {}
        for c in range(1, 11):
            child = 0.0
            origin = "split-aces" if c == 1 else "split"
            for d in range(1, 11):
                a = actions[c + d, c == 1 or d == 1]
                choice = ("stand" if c == 1 else baseline.two[up, c, d, origin]
                          if baseline else max(a, key=a.get))
                self.two[up, c, d, origin] = choice
                child += p[d] * a[choice]
            split[c] = 2 * child
        for c in range(1, 11):
            for d in range(1, 11):
                if {c, d} == {1, 10}:
                    self.initial_values[up, c, d] = (1 - q) * 1.5
                    continue
                a = dict(actions[c + d, c == 1 or d == 1])
                if c == d:
                    a["split"] = split[c]
                    self.state_action_values[up, c + d, c == 1, 2] = dict(a)
                self.action_values[up, c, d] = a
                choice = baseline.two[up, c, d, "original"] if baseline else max(a, key=a.get)
                self.two[up, c, d, "original"] = choice
                self.initial_values[up, c, d] = -q + (1 - q) * a[choice]
        dealer.cache_clear()


class StrategyTables:
    """Quarter-count grid, capped at +/-12; fixed before evaluation, never fitted."""
    def __init__(self, step=0.25):
        if not math.isfinite(step) or step <= 0 or step > 1 or not math.isclose(12 / step, round(12 / step)):
            raise ValueError("step must be in (0, 1] and divide 12")
        self.step = step
        self.limit = round(12 / step)
        self.baseline = Baseline()
        self.optimized = {}
        self.baseline_edges = {}
        for index in range(-self.limit, self.limit + 1):
            p = adjusted_probabilities(index * step)
            self.optimized[index] = Approximation(p)
            self.baseline_edges[index] = Approximation(p, self.baseline).edge

    def index(self, observation):
        return max(-self.limit, min(self.limit, round(observation.true_count / self.step)))

    def estimate(self, observation, playing):
        if playing not in ("baseline", "counting"):
            raise ValueError("playing must be baseline or counting")
        i = self.index(observation)
        return self.baseline_edges[i] if playing == "baseline" else self.optimized[i].edge


class Counting:
    def __init__(self, tables):
        self.tables = tables

    def choose(self, cards, upcard, origin, observation):
        table = self.tables.optimized[self.tables.index(observation)]
        if len(cards) == 2:
            return table.two[upcard, cards[0], cards[1], origin]
        raw, ace = state(cards)
        return table.continuation[upcard, raw, ace]


@dataclass(frozen=True)
class BettingPolicy:
    """Initial wager only. A linear positive-edge ramp, not a bankroll model."""
    minimum: float = 1.0
    maximum: float = 4.0
    full_bet_edge: float = 0.01
    bounded: bool = False

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.minimum, self.maximum, self.full_bet_edge)):
            raise ValueError("Bet settings must be finite")
        if not 0 < self.minimum <= self.maximum or self.full_bet_edge <= 0:
            raise ValueError("Require 0 < minimum <= maximum and full_bet_edge > 0")

    def choose(self, estimated_edge):
        if not math.isfinite(estimated_edge):
            raise ValueError("Estimated edge must be finite")
        if not self.bounded:
            return self.minimum
        fraction = max(0.0, min(1.0, estimated_edge / self.full_bet_edge))
        return self.minimum + (self.maximum - self.minimum) * fraction
