import json
from fractions import Fraction
from pathlib import Path
from random import Random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from blackjack import Hand, Solver
from blackjack.counting import (Approximation, BASE, Baseline, BettingPolicy, Counter,
                                Counting, Observation, StrategyTables, adjusted_probabilities)
from blackjack.evaluation import Statistics, PairedStatistics
from blackjack.finite import FULL_SHOE, RoundResult, Shoe, play_round, shoe_rounds


class ScriptedPolicy:
    def __init__(self, actions=()):
        self.actions = iter(actions)
        self.seen = []

    def choose(self, cards, upcard, origin, observation):
        self.seen.append((cards, upcard, origin, observation))
        return next(self.actions, "stand")


class StrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = StrategyTables()

    def test_zero_count_matches_exact_solver(self):
        s = Solver()
        table = self.tables.optimized[0]
        self.assertAlmostEqual(table.edge, float(s.overall()["pre_check_ev"]), places=13)
        self.assertAlmostEqual(self.tables.baseline_edges[0], table.edge, places=13)
        for up in range(1, 11):
            for actual, expected in zip(table.dealers[up], s.dealer_distribution(up)):
                self.assertAlmostEqual(actual, float(expected), places=13)
            for c in range(1, 11):
                for d in range(1, 11):
                    hand = Hand((c, d))
                    for action, value in s.actions(hand, up).items():
                        self.assertAlmostEqual(table.action_values[up, c, d][action], float(value), places=13)
                    if not hand.natural:
                        chosen = self.tables.baseline.choose((c, d), up, "original", Observation())
                        self.assertEqual(s.actions(hand, up)[chosen], s.value(hand, up))
                    for origin in (("split-aces",) if c == 1 else ("split",)):
                        hand = Hand((c, d), origin)
                        chosen = table.two[up, c, d, origin]
                        self.assertAlmostEqual(float(s.actions(hand, up)[chosen]), float(s.value(hand, up)), places=13)

    def test_nonzero_probabilities_against_exact_fraction_engine(self):
        # This validates the approximation's DP, not its finite-shoe accuracy.
        for tc in (-3, 2):
            class Model:
                outcomes = tuple((c, Fraction(4 if c == 10 else 1, 13) -
                                  Fraction((4 if c == 10 else 1) *
                                           (-1 if c in (1, 10) else 1 if 2 <= c <= 6 else 0) * tc, 520))
                                 for c in range(1, 11))
            exact = Solver(Model())
            table = self.tables.optimized[round(tc / self.tables.step)]
            self.assertAlmostEqual(table.edge, float(exact.overall()["pre_check_ev"]), places=13)
            for row in exact.initial_rows():
                c, d = row["cards"]
                for action, value in row["post_check"]["actions"].items():
                    self.assertAlmostEqual(table.action_values[row["upcard"], c, d][action], float(value), places=13)

    def test_count_and_bet_boundaries(self):
        counter = Counter()
        for card in (2, 3, 4, 10, 7):
            counter.observe(card)
        counter.dealt = 6  # One unknown hole card, whose rank is never counted.
        obs = counter.snapshot()
        self.assertEqual(obs.running_count, 2)
        self.assertAlmostEqual(obs.true_count, 104 / 307)
        self.assertEqual(sum(obs.visible_counts), 5)
        self.assertEqual(obs.dealt, 6)
        counter.observe(1)
        self.assertEqual(obs.running_count, 2)  # Immutable snapshot.
        for tc in (-12, 0, 12):
            p = adjusted_probabilities(tc)
            self.assertAlmostEqual(sum(p), 1)
            self.assertGreater(min(p[1:]), 0)
        self.assertLess(self.tables.optimized[-8].edge, self.tables.optimized[0].edge)
        self.assertGreater(self.tables.optimized[8].edge, self.tables.optimized[0].edge)
        bet = BettingPolicy(bounded=True)
        self.assertEqual([bet.choose(x) for x in (-1, 0, .005, .01, 1)], [1, 1, 2.5, 4, 4])
        self.assertEqual(BettingPolicy().choose(1), 1)
        for args in ((0, 4, .01), (4, 1, .01), (1, 4, 0), (1, float("nan"), .01)):
            with self.assertRaises(ValueError):
                BettingPolicy(*args)


class EngineTests(unittest.TestCase):
    def round(self, cards, actions=(), bet=1):
        counter = Counter()
        policy = ScriptedPolicy(actions)
        result = play_round(Shoe(cards), counter, policy, BettingPolicy(bet, bet), lambda obs: 0)
        return result, counter, policy

    def test_six_deck_composition_and_no_replacement(self):
        self.assertEqual(len(FULL_SHOE), 312)
        shoe = Shoe.shuffled(Random(123))
        draws = [shoe.draw() for _ in range(312)]
        for c in range(1, 11):
            self.assertEqual(draws.count(c), 96 if c == 10 else 24)
        with self.assertRaises(RuntimeError):
            shoe.draw()

    def test_natural_and_peek_settlement(self):
        result, counter, policy = self.round([1, 9, 10, 6])
        self.assertEqual(result.unit_profit, 1.5)
        self.assertEqual((result.cards_dealt, result.visible_cards), (4, 3))
        self.assertEqual(counter.counts[6], 0)
        self.assertFalse(policy.seen)
        for cards, payoff in (([1, 10, 10, 1], 0), ([8, 1, 8, 10], -1)):
            r, _, p = self.round(cards)
            self.assertEqual(r.unit_profit, payoff)
            self.assertEqual(r.visible_cards, 4)
            self.assertFalse(p.seen)  # No split/double wager before peek clears.

    def test_s17_and_bust_priority(self):
        r, _, _ = self.round([10, 1, 7, 6])
        self.assertEqual((r.unit_profit, r.cards_dealt), (0, 4))
        r, counter, _ = self.round([10, 6, 6, 10, 10], ["hit"])
        self.assertEqual((r.unit_profit, r.cards_dealt, r.visible_cards), (-1, 5, 4))
        self.assertEqual(counter.counts[10], 2)  # Dealer hole is not exposed.
        r, _, _ = self.round([10, 6, 2, 10, 10], ["double"], bet=3)
        self.assertEqual((r.unit_profit, r.profit), (-2, -6))

    def test_split_double_scaling_and_visibility(self):
        r, _, policy = self.round([8, 6, 8, 10, 3, 10, 2, 10, 5], ["split", "double", "double"])
        self.assertEqual((r.unit_profit, r.cards_dealt), (-2, 9))
        self.assertEqual([x[2] for x in policy.seen], ["original", "split", "split"])
        second_child = policy.seen[2][3]
        self.assertEqual(second_child.visible_counts[10], 1)  # First child's draw, not hole.
        self.assertEqual(second_child.visible_counts[2], 1)
        self.assertEqual(second_child.dealt, 7)
        r, _, policy = self.round([1, 6, 1, 10, 10, 9, 5], ["split"])
        self.assertEqual(r.unit_profit, -1)  # Split 21 pushes dealer 21; sibling loses.
        self.assertEqual(len(policy.seen), 1)  # Split aces forced to stand.
        # Both split hands double and win against a shared dealer bust.
        r, _, _ = self.round([8, 6, 8, 10, 3, 10, 2, 10, 10], ["split", "double", "double"])
        self.assertEqual(r.unit_profit, 4)

    def test_no_hole_or_future_information_in_decisions(self):
        histories = []
        for hidden, future in ((10, 2), (9, 3)):
            p = ScriptedPolicy()
            bet_observations = []
            def estimate(obs):
                bet_observations.append(obs)
                return .005
            r = play_round(Shoe([10, 6, 6, hidden, future, 10]), Counter(), p,
                           BettingPolicy(bounded=True), estimate)
            self.assertEqual(r.initial_bet, 2.5)
            self.assertEqual(bet_observations, [Observation()])
            self.assertEqual(p.seen[0][3].dealt, 4)
            self.assertEqual(sum(p.seen[0][3].visible_counts), 3)
            histories.append(p.seen)
        self.assertEqual(histories[0], histories[1])

    def test_threshold_counts_hidden_and_finishes_round_then_resets(self):
        for threshold, expected in ((None, 1), (26, 7), (52, 13), (104, 26), (156, 39)):
            snapshots = []
            def estimate(obs):
                snapshots.append(obs)
                return 0
            # Naturals consume four cards, but the dealer hole stays hidden.
            with patch.object(Shoe, "shuffled", side_effect=lambda rng: Shoe([1, 9, 10, 6] * 50)):
                for _ in range(2):
                    rounds = list(shoe_rounds(Random(1), threshold, ScriptedPolicy(), BettingPolicy(), estimate))
                    self.assertEqual(len(rounds), expected)
                    self.assertEqual(sum(r.cards_dealt for r in rounds), 4 * expected)
                    self.assertEqual(sum(r.visible_cards for r in rounds), 3 * expected)
            self.assertEqual(snapshots[0], Observation())
            self.assertEqual(snapshots[expected], Observation())

    def test_betting_cannot_change_play_or_initial_information(self):
        baseline = Baseline()
        runs = []
        for bounded in (False, True):
            runs.append(list(shoe_rounds(Random(77), 52, baseline, BettingPolicy(bounded=bounded), lambda obs: .01)))
        self.assertEqual([r.unit_profit for r in runs[0]], [r.unit_profit for r in runs[1]])
        self.assertEqual([r.cards_dealt for r in runs[0]], [r.cards_dealt for r in runs[1]])
        self.assertEqual([r.profit * 4 for r in runs[0]], [r.profit for r in runs[1]])


class StatisticsTests(unittest.TestCase):
    def test_cluster_ratio_standard_errors(self):
        s = Statistics()
        for profits in ((1, 1), (-1,)):
            s.add_cycle([RoundResult(x, 1, 0, 4, 4, 0) for x in profits])
        r = s.report()
        self.assertAlmostEqual(r["expected_profit_per_round"], 1 / 3)
        self.assertAlmostEqual(r["round_profit_variance"], 8 / 9)
        # Cluster residuals are +4/3, -4/3; random denominator is essential.
        self.assertAlmostEqual(r["profit_per_round_se"], 8 / 9)
        self.assertEqual(r["profit_per_round_se"], r["profit_relative_to_initial_wagers_se"])
        p = PairedStatistics()
        p.cycles = [((2, 2, 2), (2, 2, 2)), ((-1, 1, 1), (-1, 1, 1))]
        self.assertEqual(p.report(r, r, 1)["se"], 0)

    def test_cli_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = [Path(tmp) / f"{i}.json" for i in range(2)]
            for path in files:
                subprocess.run([sys.executable, "-m", "blackjack", "evaluate", "--shoes", "20",
                                "--count-step", "1", "--seed", "314", "--output", str(path)],
                               check=True, capture_output=True, text=True)
                self.assertIn("Profit/round", path.with_suffix(".md").read_text())
            a, b = [json.loads(path.read_text()) for path in files]
            self.assertEqual(len(a["results"]), 12)
            self.assertEqual(a["paired_comparisons"], b["paired_comparisons"])
            for x, y in zip(a["results"], b["results"]):
                x.pop("runtime_seconds")
                y.pop("runtime_seconds")
                self.assertEqual(x, y)
                self.assertGreaterEqual(x["observed_bet_range"][0], 1)
                self.assertLessEqual(x["observed_bet_range"][1], 4)


if __name__ == "__main__":
    unittest.main()
