import csv
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from functools import cache
from pathlib import Path

from blackjack import Hand, Solver
from blackjack.cli import export
from blackjack.solver import add_card


class DecimalOracle:
    """Independent bottom-up player DP using raw ace-as-one sum.

    No production transition, payoff, or probability functions are used.
    Dealer recursion independently tracks raw sum and whether an ace exists.
    """
    def __init__(self, up):
        self.p = {c: D(4 if c == 10 else 1) / 13 for c in range(1, 11)}
        q = self.p[10] if up == 1 else self.p[1] if up == 10 else D(0)

        @cache
        def dealer(raw, ace):
            total = raw + 10 if ace and raw <= 11 else raw
            if total >= 17:
                return {22 if total > 21 else total: D(1)}
            out = {}
            for c, p in self.p.items():
                for end, prob in dealer(raw + c, ace or c == 1).items():
                    out[end] = out.get(end, D(0)) + p * prob
            return out

        self.dist = {}
        for hole, p in self.p.items():
            if (up == 1 and hole == 10) or (up == 10 and hole == 1):
                continue
            for end, prob in dealer(up + hole, up == 1 or hole == 1).items():
                self.dist[end] = self.dist.get(end, D(0)) + p * prob / (1 - q)
        self.v = {}
        self.a = {}
        for raw in range(21, 0, -1):
            for ace in (False, True):
                total = raw + 10 if ace and raw <= 11 else raw
                stand = self.stand(total)
                hit = sum(p * (D(-1) if raw + c > 21 else self.v[raw + c, ace or c == 1])
                          for c, p in self.p.items())
                double = 2 * sum(p * self.stand(raw + c + (10 if (ace or c == 1) and raw + c <= 11 else 0))
                                 for c, p in self.p.items())
                self.a[raw, ace] = {"stand": stand, "hit": hit, "double": double}
                self.v[raw, ace] = max(stand, hit)

    def stand(self, total):
        if total > 21:
            return D(-1)
        return sum(p * (1 if end == 22 or total > end else -1 if total < end else 0)
                   for end, p in self.dist.items())

    def actions(self, c, d):
        values = dict(self.a[c + d, c == 1 or d == 1])
        if c == d:
            split = D(0)
            for drawn, p in self.p.items():
                options = self.a[c + drawn, c == 1 or drawn == 1]
                split += p * (options["stand"] if c == 1 else max(options.values()))
            values["split"] = 2 * split
        return values


class SolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Solver()

    def test_cards_and_aces(self):
        self.assertEqual(Hand(("A", "A", 9)).state, (21, True))
        self.assertEqual(Hand((1, 1, 10)).state, (12, False))
        self.assertEqual(add_card(17, True, 10), (17, False))
        self.assertEqual(Hand(("J", "K")).cards, (10, 10))
        for cards in ((0, 8), (11, 2), (10,), (1, 10, 2), (10, 9, 5, 2)):
            with self.assertRaises(ValueError):
                Hand(cards)

    def test_probability_mass(self):
        self.assertEqual(sum(r["deal_probability"] for r in self.s.initial_rows()), 1)
        for up in range(1, 11):
            self.assertEqual(sum(self.s.dealer_distribution(up)), 1)
        self.assertEqual(self.s.blackjack_probability(1), F(4, 13))
        self.assertEqual(self.s.blackjack_probability(10), F(1, 13))
        self.assertEqual(self.s._dealer(17, True), (0, 1, 0, 0, 0, 0))

    def test_natural_and_peek(self):
        r = self.s.query(Hand((1, 10)), 1)
        self.assertEqual(r["post_check"]["value"], F(3, 2))
        self.assertEqual(r["pre_check"]["value"], F(27, 26))
        self.assertEqual(r["post_check"]["actions"], {})
        r = self.s.query(Hand((8, 8)), 1)
        for a, v in r["post_check"]["actions"].items():
            self.assertEqual(r["pre_check"]["actions"][a], -F(4, 13) + F(9, 13) * v)

    def test_legality_and_wager_units(self):
        self.assertEqual(set(self.s.actions(Hand((8, 8)), 6)), {"stand", "hit", "double", "split"})
        self.assertEqual(set(self.s.actions(Hand((8, 8), "split"), 6)), {"stand", "hit", "double"})
        self.assertEqual(set(self.s.actions(Hand((2, 3, 4)), 6)), {"stand", "hit"})
        self.assertEqual(set(self.s.actions(Hand((1, 1), "split-aces"), 6)), {"stand"})
        self.assertLess(self.s.value(Hand((1, 10), "split-aces"), 6), 1)
        self.assertEqual(self.s.value(Hand((10, 10, 5)), 6), -1)
        self.assertIsNone(self.s.query(Hand((8, 8), "split"), 1)["pre_check"])
        self.assertEqual(self.s._double(11, False, 6),
                         2 * sum(p * self.s.stand(11 + c, 6) for c, p in self.s.draws))
        self.assertEqual(self.s._split(1, 6),
                         2 * sum(p * self.s.stand(Hand((1, c)).state[0], 6) for c, p in self.s.draws))

    def test_shared_dealer_split_payoff(self):
        # Explicit joint enumeration of both ace draws and the shared dealer.
        joint = F(0)
        for c, p in self.s.draws:
            for d, q in self.s.draws:
                totals = [Hand((1, c)).state[0], Hand((1, d)).state[0]]
                for slot, r in enumerate(self.s.dealer_distribution(10)):
                    payoff = sum(1 if slot == 0 else (t > slot + 16) - (t < slot + 16) for t in totals)
                    joint += p * q * r * payoff
        self.assertEqual(joint, self.s._split(1, 10))

    def test_independent_decimal_oracle(self):
        with localcontext() as ctx:
            ctx.prec = 60
            overall = D(0)
            probability = {c: D(4 if c == 10 else 1) / 13 for c in range(1, 11)}
            def close(exact, decimal):
                self.assertLess(abs(D(exact.numerator) / D(exact.denominator) - decimal), D("1e-55"))
            for up in range(1, 11):
                oracle = DecimalOracle(up)
                for slot, v in enumerate(self.s.dealer_distribution(up)):
                    close(v, oracle.dist.get(22 if slot == 0 else slot + 16, D(0)))
                for c in range(1, 11):
                    for d in range(c, 11):
                        r = self.s.query(Hand((c, d)), up)
                        natural = c == 1 and d == 10
                        values = {} if natural else oracle.actions(c, d)
                        self.assertEqual(set(values), set(r["post_check"]["actions"]))
                        for a, v in values.items():
                            close(r["post_check"]["actions"][a], v)
                        q = probability[10] if up == 1 else probability[1] if up == 10 else D(0)
                        post = D("1.5") if natural else max(values.values())
                        pre = (1-q)*post - (0 if natural else q)
                        overall += probability[c]*probability[d]*probability[up]*(1 if c == d else 2)*pre
                for (raw, ace), v in oracle.v.items():
                    total = raw + 10 if ace and raw <= 11 else raw
                    close(self.s._continuation(total, ace and raw <= 11, up), v)
                for retained in range(1, 11):
                    for drawn in range(1, 11):
                        hand = Hand((retained, drawn), "split-aces" if retained == 1 else "split")
                        expected = oracle.a[retained + drawn, retained == 1 or drawn == 1]
                        if retained == 1:
                            expected = {"stand": expected["stand"]}
                        actual = self.s.actions(hand, up)
                        self.assertEqual(set(actual), set(expected))
                        for action, value in actual.items():
                            close(value, expected[action])
            close(self.s.overall()["pre_check_ev"], overall)

    def test_overall_peek_decomposition(self):
        result = self.s.overall()
        q = F(8, 169)
        self.assertEqual(result["dealer_blackjack_probability"], q)
        # Player and dealer naturals are independent; both natural pushes.
        self.assertEqual(result["pre_check_ev"],
                         (1 - q) * result["post_check_ev_conditional"] - q * (1 - q))

    def test_strategy_examples(self):
        for cards, up, action in (((8, 8), 6, "split"), ((1, 1), 10, "split"),
                                  ((5, 6), 6, "double"), ((10, 6), 10, "hit"),
                                  ((10, 10), 6, "stand"), ((1, 7), 6, "double")):
            self.assertEqual(self.s.query(Hand(cards), up)["post_check"]["optimal_actions"], [action])

    def test_cli_and_exports(self):
        run = subprocess.run([sys.executable, "-m", "blackjack", "query", "8,8", "--upcard", "6"],
                             capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(run.stdout)["post_check"]["optimal_actions"], ["split"])
        bad = subprocess.run([sys.executable, "-m", "blackjack", "query", "0,8", "--upcard", "6"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        with tempfile.TemporaryDirectory() as tmp:
            export(self.s, Path(tmp))
            for name, count in (("initial", 550), ("continuation", 250), ("split_hands", 1000)):
                with (Path(tmp) / f"{name}.csv").open() as f:
                    self.assertEqual(len(list(csv.DictReader(f))), count)
            self.assertEqual(len(json.loads((Path(tmp) / "initial.json").read_text())), 550)


if __name__ == "__main__":
    unittest.main()
