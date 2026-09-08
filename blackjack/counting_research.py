"""Research evaluation of published count-tag adapters on shallow six-deck shoes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
from statistics import NormalDist
import subprocess
import tempfile
from time import perf_counter

from .counting import BettingPolicy
from .counting_methods import METHODS, ResearchModels
from .evaluation import Statistics

BET_NAMES = ("constant", "ramp", "positive-step")
RAW_FIELDS = ("cycles", "rounds", "profit", "wagers", "squares", "xx", "nn", "ww", "xn", "xw",
              "predicted", "unit_profit", "residual", "residual_sq", "residual_n", "cards", "visible",
              "raised", "min_bet", "max_bet", "max_cards_per_shoe")
SOURCE = Path(__file__).resolve().parents[1] / "research" / "counting_benchmark.cpp"


def compile_evaluator(destination):
    command = ["g++", "-std=c++17", "-O3", "-Wall", "-Wextra", str(SOURCE), "-o", str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return command


def statistics_from_raw(row):
    if len(row) != len(RAW_FIELDS):
        raise ValueError("Unexpected statistics format")
    result = Statistics()
    for name, value in zip(RAW_FIELDS, row):
        setattr(result, name, value)
    return result


def paired_from_moments(a, b, cross, denominator, z=1.96):
    """Difference of regenerative ratios; cross is sum outer([X,N,W]_a,b)."""
    if a.cycles != b.cycles or a.cycles < 2:
        raise ValueError("Matched statistics must have the same shoe count >= 2")
    k = a.cycles
    da = a.rounds if denominator == 1 else a.wagers
    db = b.rounds if denominator == 1 else b.wagers
    ra, rb = a.profit / da, b.profit / db
    aa = a.nn if denominator == 1 else a.ww
    bb = b.nn if denominator == 1 else b.ww
    xa = a.xn if denominator == 1 else a.xw
    xb = b.xn if denominator == 1 else b.xw
    va = a.xx - 2 * ra * xa + ra * ra * aa
    vb = b.xx - 2 * rb * xb + rb * rb * bb
    cov = cross[0] - ra * cross[denominator * 3] - rb * cross[denominator] + ra * rb * cross[denominator * 3 + denominator]
    variance = k / (k - 1) * (va / da**2 + vb / db**2 - 2 * cov / (da * db))
    se = math.sqrt(max(0.0, variance))
    return {"difference": rb - ra, "se": se, "ci95": [rb - ra - 1.96 * se, rb - ra + 1.96 * se],
            "family_ci95": [rb - ra - z * se, rb - ra + z * se]}


def process_outputs(raw_outputs, config):
    # Cover all reported absolute and paired estimates, for both profit metrics.
    family = 2 * sum(len(r["stats"]) + len(r["pairs"]) for r in raw_outputs.values())
    z = NormalDist().inv_cdf(1 - .05 / (2 * family))
    results, comparisons = [], []
    for threshold, raw in raw_outputs.items():
        stats = [statistics_from_raw(row) for row in raw["stats"]]
        for i, s in enumerate(stats):
            report = s.report()
            report.pop("pre_round_count_clips")
            report.update(reshuffle_policy=str(threshold), method=METHODS[i // 3], betting=BET_NAMES[i % 3],
                          shared_play_runtime_seconds=raw["method_seconds"][i // 3])
            for metric, se in (("expected_profit_per_round", "profit_per_round_se"),
                               ("profit_relative_to_initial_wagers", "profit_relative_to_initial_wagers_se")):
                report[metric + "_family_ci95"] = [report[metric] - z * report[se], report[metric] + z * report[se]]
            results.append(report)
        for row in raw["pairs"]:
            a, b = row[:2]
            comparisons.append({"reshuffle_policy": str(threshold),
                                "reference": METHODS[a // 3] + "/" + BET_NAMES[a % 3],
                                "candidate": METHODS[b // 3] + "/" + BET_NAMES[b % 3],
                                "profit_per_round": paired_from_moments(stats[a], stats[b], row[2:], 1, z),
                                "profit_relative_to_initial_wagers": paired_from_moments(stats[a], stats[b], row[2:], 2, z)})
    return {"configuration": config, "uncertainty": {"cluster": "independent complete shoes", "family_size": family,
             "family_z": z, "correction": "Bonferroni across every reported absolute and paired estimate, both metrics"},
            "results": results, "comparisons": comparisons,
            "scenario_runtime_seconds": {k: v["runtime_seconds"] for k, v in raw_outputs.items()}}


def markdown_report(data):
    config = data["configuration"]
    lines = ["# Additional counting methods: held-out evaluation", "",
             "Experimental six-deck shallow-shoe models, not calibrated Macau continuous-shuffler behavior.", "",
             f'Seed **{config["seed"]}**; **{config["shoes_per_scenario"]:,} independent shoes per scenario**; '
             f'initial bets **{config["minimum"]:g}–{config["maximum"]:g}**, no skipping. '
             "No evaluation outcomes were used to fit or select parameters.", "",
             "Published tags are implemented with our analytic playing/forecast adapters; these are not the authors' complete published index systems. "
             "`composition` uses every visible rank with first-order action sensitivities; it is not an exact finite-shoe optimizer or an upper bound.", "",
             "The practical threshold was fixed before evaluation at **0.1 percentage point of profit per initial wager**. "
             "A detectable improvement, a practically noticeable improvement, and a positive return are separate questions.", ""]
    for threshold in config["thresholds"]:
        lines += [f"## {threshold}-card threshold", "",
                  "± denotes a nominal shoe-clustered 95% confidence half-width. Variance is marginal round-profit variance in squared units. "
                  "The three betting alternatives share the exact same playing path, so the listed playing runtime is shared, not additive.", "",
                  "| Method | Bets | Profit/round ±95% | Profit/initial wagers ±95% | Variance | Shared runtime (s) |",
                  "|---|---|---:|---:|---:|---:|"]
        for r in data["results"]:
            if r["reshuffle_policy"] != str(threshold):
                continue
            lines.append(f'| {r["method"]} | {r["betting"]} | {r["expected_profit_per_round"]:+.6f} ± {1.96*r["profit_per_round_se"]:.6f} '
                         f'| {100*r["profit_relative_to_initial_wagers"]:+.4f}% ± {196*r["profit_relative_to_initial_wagers_se"]:.4f}% '
                         f'| {r["round_profit_variance"]:.5f} | {r["shared_play_runtime_seconds"]:.2f} |')
        lines += ["", f'Total scenario runtime including shuffle and comparisons: **{data["scenario_runtime_seconds"][str(threshold)]:.2f} s**.', ""]
    lines += ["## Improvements over the existing Hi-Lo adapter", "",
              "Differences are percentage points of profit per initial wager, candidate minus Hi-Lo with the same betting policy. "
              "The family intervals correct for all reported comparisons and absolute estimates; they are intentionally conservative.", "",
              "| Threshold | Method / bets | Difference | Nominal 95% CI | Family 95% CI |",
              "|---|---|---:|---:|---:|"]
    for c in data["comparisons"]:
        reference_method, reference_bet = c["reference"].split("/")
        candidate_method, candidate_bet = c["candidate"].split("/")
        if reference_method != "hilo" or candidate_method == "hilo" or reference_bet != candidate_bet:
            continue
        v = c["profit_relative_to_initial_wagers"]
        lines.append(f'| {c["reshuffle_policy"]} | {c["candidate"]} | {100*v["difference"]:+.4f} '
                     f'| [{100*v["ci95"][0]:+.4f}, {100*v["ci95"][1]:+.4f}] '
                     f'| [{100*v["family_ci95"][0]:+.4f}, {100*v["family_ci95"][1]:+.4f}] |')
    lines += ["", "## Separating betting effects", "",
              "Same playing method, changing only the pre-deal bet from constant to ramp or positive-step. "
              "Differences below are percentage points of profit per initial wager with family 95% intervals.", "",
              "| Threshold | Playing method | Bet change | Difference | Family 95% CI |",
              "|---|---|---|---:|---:|"]
    for c in data["comparisons"]:
        reference_method, reference_bet = c["reference"].split("/")
        candidate_method, candidate_bet = c["candidate"].split("/")
        if reference_method != candidate_method or reference_bet != "constant":
            continue
        v = c["profit_relative_to_initial_wagers"]
        lines.append(f'| {c["reshuffle_policy"]} | {candidate_method} | constant → {candidate_bet} '
                     f'| {100*v["difference"]:+.4f} '
                     f'| [{100*v["family_ci95"][0]:+.4f}, {100*v["family_ci95"][1]:+.4f}] |')
    lines += ["", "## Interpretation", ""]
    if all(r["profit_relative_to_initial_wagers_family_ci95"][1] < 0 for r in data["results"]):
        lines.append("Every configuration's return is negative even at the conservative family confidence level. No tested method establishes a positive player edge.")
    else:
        positive = [r for r in data["results"] if r["profit_relative_to_initial_wagers_family_ci95"][0] > 0]
        uncertain = [r for r in data["results"] if r["profit_relative_to_initial_wagers_family_ci95"][0] <= 0
                     <= r["profit_relative_to_initial_wagers_family_ci95"][1]]
        lines.append(f'{len(positive)} configurations establish a positive return at the family confidence level; '
                     f'{len(uncertain)} have intervals containing zero. The remaining configurations have intervals below zero.')
        if positive:
            lines += ["", "Positive configurations: " + "; ".join(
                f'{r["reshuffle_policy"]} cards, {r["method"]}/{r["betting"]}' for r in positive) + "."]
    new_vs_hilo = [c for c in data["comparisons"] if c["reference"].startswith("hilo/")
                   and not c["candidate"].startswith("hilo/")]
    if all(c["profit_relative_to_initial_wagers"]["family_ci95"][1] < config["practical_improvement_threshold"]
           for c in new_vs_hilo):
        lines += ["", "For every new adapter and betting policy, the family interval for improvement over existing Hi-Lo "
                  "is below the predefined 0.1-percentage-point benchmark. The new methods do not deliver a noticeable "
                  "increment by that criterion. A statistically detectable improvement can still be smaller than this practical benchmark."]
    for threshold in config["thresholds"]:
        candidates = [c for c in data["comparisons"] if c["reshuffle_policy"] == str(threshold) and c["reference"] == "baseline/constant"]
        best = max(candidates, key=lambda c: c["profit_relative_to_initial_wagers"]["difference"])
        v = best["profit_relative_to_initial_wagers"]
        lines += ["", f'At {threshold} cards, the largest observed lift over baseline/constant is **{best["candidate"]}**, '
                  f'**{100*v["difference"]:+.4f} percentage points**, with family interval '
                  f'**[{100*v["family_ci95"][0]:+.4f}, {100*v["family_ci95"][1]:+.4f}]**. '
                  "This is a descriptive ranking of all reported methods, not a policy selected for a new out-of-sample claim."]
    lines += ["", "Raw JSON includes all comparisons with baseline/constant, same-method betting effects, "
              "both uncertainty measures, long-run variance, forecasts, penetration, and raised-bet frequency. "
              "Neither sampling interval covers approximation error in machine behavior or policy design.", "",
              "See [sources, implementation details, tests, and reproduction](../COUNTING_RESEARCH.md).", ""]
    if "total_runtime_seconds" in data:
        lines += [f'Coefficient generation and compilation: **{data["build_seconds"]:.2f} s**. '
                  f'Total wall time: **{data["total_runtime_seconds"]:.2f} s**.', "",
                  f'Compiler: `{config["compiler"]}`. Python: `{config["python"]}`. '
                  f'Platform: `{config["platform"]}`.', ""]
    return "\n".join(lines)


def evaluate(shoes=2000000, seed=20260908, output=Path("exports/counting_research.json"),
             minimum=1., maximum=4., full_bet_edge=.01, thresholds=(26, 52)):
    if shoes < 2 or not 0 <= seed < 2**64:
        raise ValueError("Require >=2 shoes and a 64-bit unsigned seed")
    BettingPolicy(minimum, maximum, full_bet_edge, True)
    thresholds = tuple(thresholds)
    if not thresholds or len(set(thresholds)) != len(thresholds) or any(t not in (26, 52, 104, 156) for t in thresholds):
        raise ValueError("Choose distinct thresholds from 26, 52, 104, 156")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    with tempfile.TemporaryDirectory(prefix="blackjack-research-") as tmp:
        binary, model = Path(tmp) / "evaluate", Path(tmp) / "models.bin"
        command = compile_evaluator(binary)
        models = ResearchModels()
        models.export(model)
        build_time = perf_counter() - start
        checksum = hashlib.sha256(model.read_bytes()).hexdigest()
        raw = {}
        for threshold in thresholds:
            # stderr remains attached so long evaluations report progress.
            run = subprocess.run([str(binary), str(model), str(shoes), str(seed), str(threshold),
                                  str(minimum), str(maximum), str(full_bet_edge)],
                                 check=True, text=True, stdout=subprocess.PIPE)
            raw[str(threshold)] = json.loads(run.stdout)
            # A checkpoint preserves a completed scenario during long evaluations.
            output.with_suffix(".moments.json").write_text(json.dumps(raw, indent=2) + "\n")
    config = {"shoes_per_scenario": shoes, "seed": seed, "thresholds": list(thresholds), "methods": list(METHODS),
              "minimum": minimum, "maximum": maximum, "full_bet_edge": full_bet_edge,
              "practical_improvement_threshold": .001, "parameter_tuning": "none; analytic derivatives and fixed defaults",
              "finite_difference_epsilon": models.epsilon, "model_sha256": checksum,
              "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
              "compile_flags": command[1:5], "rng": "std::mt19937_64; unbiased rejection; descending Fisher-Yates",
              "python": platform.python_version(), "platform": platform.platform()}
    data = process_outputs(raw, config)
    data.update(build_seconds=build_time, total_runtime_seconds=perf_counter() - start)
    output.write_text(json.dumps(data, indent=2) + "\n")
    report = output.with_suffix(".md") if output.suffix != ".md" else output.with_name(output.name + ".report.md")
    report.write_text(markdown_report(data))
    return {"output": str(output), "report": str(report), "runtime_seconds": data["total_runtime_seconds"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shoes", type=int, default=2000000)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--output", type=Path, default=Path("exports/counting_research.json"))
    parser.add_argument("--min-bet", type=float, default=1.)
    parser.add_argument("--max-bet", type=float, default=4.)
    parser.add_argument("--full-bet-edge", type=float, default=.01)
    parser.add_argument("--thresholds", type=int, nargs="+", choices=(26, 52, 104, 156), default=[26, 52])
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(args.shoes, args.seed, args.output, args.min_bet, args.max_bet,
                                  args.full_bet_edge, args.thresholds), indent=2))
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        parser.error(str(exc))
