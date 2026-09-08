"""Reproducible Monte Carlo; uncertainty uses independent whole-shoe clusters."""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
from random import Random
from time import perf_counter

from .counting import BettingPolicy, Counting, StrategyTables
from .finite import shoe_rounds


class Statistics:
    def __init__(self):
        self.cycles = 0
        self.rounds = 0
        self.profit = self.wagers = self.squares = 0.0
        self.xx = self.nn = self.ww = self.xn = self.xw = 0.0
        self.predicted = self.unit_profit = 0.0
        self.residual = self.residual_sq = self.residual_n = 0.0
        self.cards = self.visible = self.raised = self.clipped = 0
        self.min_bet = math.inf
        self.max_bet = 0.0
        self.max_cards_per_shoe = 0

    def add_cycle(self, rounds, minimum=1.0):
        n = 0
        x = w = residual = 0.0
        cards = 0
        for r in rounds:
            n += 1
            x += r.profit
            w += r.initial_bet
            self.squares += r.profit ** 2
            self.predicted += r.estimated_edge
            self.unit_profit += r.unit_profit
            residual += r.unit_profit - r.estimated_edge
            cards += r.cards_dealt
            self.visible += r.visible_cards
            self.raised += r.initial_bet > minimum
            self.clipped += abs(r.true_count_before) > 12
            self.min_bet = min(self.min_bet, r.initial_bet)
            self.max_bet = max(self.max_bet, r.initial_bet)
        self.cycles += 1
        self.rounds += n
        self.profit += x
        self.wagers += w
        self.xx += x * x
        self.nn += n * n
        self.ww += w * w
        self.xn += x * n
        self.xw += x * w
        self.residual += residual
        self.residual_sq += residual * residual
        self.residual_n += residual * n
        self.cards += cards
        self.max_cards_per_shoe = max(self.max_cards_per_shoe, cards)

    def report(self):
        k, n = self.cycles, self.rounds
        if k < 2:
            raise ValueError("At least two independent shoes are required for uncertainty")
        mean = self.profit / n
        roi = self.profit / self.wagers
        residual_ss = max(0.0, self.xx - 2 * mean * self.xn + mean * mean * self.nn)
        roi_ss = max(0.0, self.xx - 2 * roi * self.xw + roi * roi * self.ww)
        se = math.sqrt(k / (k - 1) * residual_ss) / n
        roi_se = math.sqrt(k / (k - 1) * roi_ss) / self.wagers
        error = self.residual / n
        error_ss = max(0.0, self.residual_sq - 2 * error * self.residual_n + error * error * self.nn)
        error_se = math.sqrt(k / (k - 1) * error_ss) / n
        return {
            "shoes": k, "rounds": n,
            "expected_profit_per_round": mean,
            "profit_per_round_se": se,
            "profit_per_round_ci95": [mean - 1.96 * se, mean + 1.96 * se],
            "profit_relative_to_initial_wagers": roi,
            "profit_relative_to_initial_wagers_se": roi_se,
            "profit_relative_to_initial_wagers_ci95": [roi - 1.96 * roi_se, roi + 1.96 * roi_se],
            "round_profit_variance": max(0.0, self.squares / n - mean * mean),
            "long_run_variance_per_round": residual_ss / (k - 1) / (n / k),
            "total_profit": self.profit, "total_initial_wagers": self.wagers,
            "mean_initial_bet": self.wagers / n,
            "observed_bet_range": [self.min_bet, self.max_bet],
            "fraction_raised_bets": self.raised / n,
            "mean_predicted_unit_edge": self.predicted / n,
            "mean_realized_unit_profit": self.unit_profit / n,
            "prediction_bias_realized_minus_predicted": error,
            "prediction_bias_ci95": [error - 1.96 * error_se, error + 1.96 * error_se],
            "mean_cards_per_round": self.cards / n,
            "mean_cards_per_shoe": self.cards / k,
            "max_cards_per_shoe": self.max_cards_per_shoe,
            "hidden_cards_mucked": self.cards - self.visible,
            "pre_round_count_clips": self.clipped,
        }


class PairedStatistics:
    """Paired difference between ratios, using matching independent shoe seeds."""
    def __init__(self):
        self.cycles = []

    def report(self, left, right, denominator):
        # The modes can play different numbers of rounds per matched shoe.
        # Influence-function differences preserve that random-denominator effect.
        a = left["expected_profit_per_round" if denominator == 1 else "profit_relative_to_initial_wagers"]
        b = right["expected_profit_per_round" if denominator == 1 else "profit_relative_to_initial_wagers"]
        k = len(self.cycles)
        da = sum(c[0][denominator] for c in self.cycles) / k
        db = sum(c[1][denominator] for c in self.cycles) / k
        influences = [(y[0] - b * y[denominator]) / db - (x[0] - a * x[denominator]) / da
                      for x, y in self.cycles]
        center = sum(influences) / k
        se = math.sqrt(sum((v - center) ** 2 for v in influences) / (k - 1) / k)
        return {"difference": b - a, "se": se,
                "ci95": [b - a - 1.96 * se, b - a + 1.96 * se]}


def evaluate(shoes=100000, seed=20260907, minimum=1.0, maximum=4.0,
             full_bet_edge=0.01, step=0.25, policies=("every-round", "26", "52"), progress=None):
    if shoes < 2:
        raise ValueError("At least two shoes are required")
    bounded = BettingPolicy(minimum, maximum, full_bet_edge, True)
    started = perf_counter()
    tables = StrategyTables(step)
    build_seconds = perf_counter() - started
    results = []
    comparisons = []
    for policy in policies:
        if policy not in ("every-round", "26", "52", "104", "156"):
            raise ValueError("Unknown reshuffle policy")
        threshold = None if policy == "every-round" else int(policy)
        stored = {}
        reports = {}
        for playing_name in ("baseline", "counting"):
            playing = tables.baseline if playing_name == "baseline" else Counting(tables)
            for betting_name in ("constant", "bounded"):
                # Reset to identical random permutations across all four modes.
                # Every new full-shoe shuffle consumes the same RNG calls.
                rng = Random(seed)
                betting = bounded if betting_name == "bounded" else BettingPolicy(minimum, maximum, full_bet_edge)
                stats = Statistics()
                cycle_totals = []
                start = perf_counter()
                for _ in range(shoes):
                    rounds = list(shoe_rounds(rng, threshold, playing, betting,
                                             lambda obs: tables.estimate(obs, playing_name)))
                    stats.add_cycle(rounds, minimum)
                    cycle_totals.append((sum(r.profit for r in rounds), len(rounds),
                                         sum(r.initial_bet for r in rounds)))
                result = {"reshuffle_policy": policy, "playing": playing_name, "betting": betting_name,
                          "runtime_seconds": perf_counter() - start, **stats.report()}
                results.append(result)
                stored[playing_name, betting_name] = cycle_totals
                reports[playing_name, betting_name] = result
                if progress:
                    progress(result)
        for betting_name in ("constant", "bounded"):
            paired = PairedStatistics()
            paired.cycles = list(zip(stored["baseline", betting_name], stored["counting", betting_name]))
            left, right = reports["baseline", betting_name], reports["counting", betting_name]
            comparisons.append({"reshuffle_policy": policy, "betting": betting_name,
                                "direction": "counting minus baseline",
                                "profit_per_round": paired.report(left, right, 1),
                                "profit_relative_to_initial_wagers": paired.report(left, right, 2)})
    return {
        "model": "Experimental six-deck shallow-shoe approximation; not calibrated Macau CSM behavior",
        "configuration": {"shoes_per_mode": shoes, "seed": seed, "decks": 6,
                          "policies": list(policies), "betting": asdict(bounded), "count_grid_step": step,
                          "count_grid_limit": 12, "parameter_tuning": "none; analytic tables and fixed defaults"},
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "table_build_seconds": build_seconds,
        "total_runtime_seconds": perf_counter() - started,
        "uncertainty": "Normal 95% intervals using independent whole-shoe clusters; paired mode comparisons; no multiplicity adjustment",
        "results": results, "paired_comparisons": comparisons,
    }


def add_arguments(parser):
    parser.add_argument("--shoes", type=int, default=100000, help="Independent full-shoe cycles per mode (default: 100000)")
    parser.add_argument("--seed", type=int, default=20260907)
    parser.add_argument("--min-bet", type=float, default=1.0)
    parser.add_argument("--max-bet", type=float, default=4.0)
    parser.add_argument("--full-bet-edge", type=float, default=0.01, help="Estimated edge reaching maximum bet (default: 0.01)")
    parser.add_argument("--count-step", type=float, default=0.25)
    parser.add_argument("--policies", nargs="+", choices=("every-round", "26", "52", "104", "156"), default=["every-round", "26", "52"])
    parser.add_argument("--output", type=Path, default=Path("exports/finite_evaluation.json"))


def markdown_report(data):
    """Render saved numerical results without rerunning or changing the experiment."""
    config = data["configuration"]
    bet = config["betting"]
    lines = [
        "# Finite six-deck evaluation results", "",
        "Experimental shallow-shoe approximations, not verified or calibrated Macau CSM behavior.", "",
        f'Seed: `{config["seed"]}`. Independent shoes per mode: **{config["shoes_per_mode"]:,}**. '
        f'Bet range: **{bet["minimum"]:g}–{bet["maximum"]:g}**, linear ramp reaching the maximum '
        f'at estimated edge **{100*bet["full_bet_edge"]:g}%**. No skipped rounds or tuned parameters.', "",
        "All ± values below are 95% confidence half-widths using independent whole-shoe clusters. "
        "Profit includes split/double stakes; the wager denominator includes initial bets only. "
        "Variance is marginal round-profit variance in squared units. Runtime is per mode, excluding table construction.", "",
        "| Reshuffle | Play | Bet | Rounds | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Runtime (s) |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in data["results"]:
        lines.append(f'| {r["reshuffle_policy"]} | {r["playing"]} | {r["betting"]} | {r["rounds"]:,} '
                     f'| {r["expected_profit_per_round"]:+.6f} ± {1.96*r["profit_per_round_se"]:.6f} '
                     f'| {100*r["profit_relative_to_initial_wagers"]:+.4f}% ± {196*r["profit_relative_to_initial_wagers_se"]:.4f}% '
                     f'| {r["round_profit_variance"]:.5f} | {r["runtime_seconds"]:.2f} |')
    if all(r["profit_per_round_ci95"][1] < 0 for r in data["results"]):
        lines += ["", "All configurations have negative estimated returns, with individual 95% intervals below zero."]
    if all(c["profit_per_round"]["ci95"][0] <= 0 <= c["profit_per_round"]["ci95"][1]
           for c in data["paired_comparisons"]):
        lines += ["", "Every matched counting-versus-baseline interval includes zero: this run does not establish a counting improvement."]
    lines += ["", "## Matched-shoe differences", "",
              "Counting minus baseline. Positive values favor counting. Bounded-mode comparisons include "
              "both playing changes and changes in the forecast used for betting. Intervals that contain zero "
              "do not establish an improvement. These intervals are not adjusted for multiple comparisons.", "",
              "| Reshuffle | Bet | Profit/round difference [95% CI] | Profit/wagers difference, percentage points [95% CI] |",
              "|---|---|---:|---:|"]
    for c in data["paired_comparisons"]:
        p, w = c["profit_per_round"], c["profit_relative_to_initial_wagers"]
        lines.append(f'| {c["reshuffle_policy"]} | {c["betting"]} '
                     f'| {p["difference"]:+.6f} [{p["ci95"][0]:+.6f}, {p["ci95"][1]:+.6f}] '
                     f'| {100*w["difference"]:+.4f} [{100*w["ci95"][0]:+.4f}, {100*w["ci95"][1]:+.4f}] |')
    lines += ["", "## Forecast and penetration diagnostics", "",
              "Forecast error is realized unit profit minus predicted unit edge. It measures aggregate "
              "bias with sampling uncertainty, not calibration at each count. Long-run variance includes "
              "within-shoe dependence.", "",
              "| Reshuffle | Play | Bet | Mean initial bet | Raised bets | Mean cards/shoe | Max cards/shoe | Long-run variance | Forecast error [95% CI] |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in data["results"]:
        ci = r["prediction_bias_ci95"]
        lines.append(f'| {r["reshuffle_policy"]} | {r["playing"]} | {r["betting"]} '
                     f'| {r["mean_initial_bet"]:.5f} | {100*r["fraction_raised_bets"]:.3f}% '
                     f'| {r["mean_cards_per_shoe"]:.3f} | {r["max_cards_per_shoe"]} '
                     f'| {r["long_run_variance_per_round"]:.5f} '
                     f'| {r["prediction_bias_realized_minus_predicted"]:+.6f} [{ci[0]:+.6f}, {ci[1]:+.6f}] |')
    lines += ["", f'Table construction: **{data["table_build_seconds"]:.2f} s**. '
              f'Total evaluation wall time: **{data["total_runtime_seconds"]:.2f} s**.', "",
              f'Environment: Python {data["environment"]["python"]}; `{data["environment"]["platform"]}`.', "",
              "Stationary count-adjusted tables approximate finite-shoe decisions and forecasts; "
              "the physical simulation samples without replacement. Machine behavior and policy-model error "
              "are outside these confidence intervals. See [model, methodology, and reproduction instructions](../FINITE_SHOE.md).", ""]
    return "\n".join(lines)


def run(args):
    import sys
    def progress(r):
        print(f'{r["reshuffle_policy"]:>11} {r["playing"]:>8} {r["betting"]:>8}: '
              f'{r["rounds"]:,} rounds, profit/round {r["expected_profit_per_round"]:+.6f} '
              f'+/- {1.96*r["profit_per_round_se"]:.6f}, {r["runtime_seconds"]:.2f}s', file=sys.stderr, flush=True)
    result = evaluate(args.shoes, args.seed, args.min_bet, args.max_bet,
                      args.full_bet_edge, args.count_step, tuple(args.policies), progress)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    report = args.output.with_suffix(".md")
    # An explicitly supplied .md JSON destination must not be overwritten.
    if report == args.output:
        report = args.output.with_name(args.output.name + ".report.md")
    report.write_text(markdown_report(result))
    return {"output": str(args.output), "report": str(report),
            "total_runtime_seconds": result["total_runtime_seconds"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), indent=2))
    except ValueError as exc:
        parser.error(str(exc))
