import argparse
import csv
import json
from fractions import Fraction
from pathlib import Path

from .solver import Hand, Solver, parse_card


def serializable(value):
    if isinstance(value, Fraction):
        return {"decimal": float(value), "exact": str(value)}
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


def export(solver, destination):
    destination.mkdir(parents=True, exist_ok=True)
    rows = list(solver.initial_rows())
    (destination / "initial.json").write_text(json.dumps(serializable(rows), indent=2) + "\n")
    (destination / "overall.json").write_text(json.dumps(serializable(solver.overall()), indent=2) + "\n")
    fields = ["cards", "upcard", "total", "soft", "natural", "optimal_actions",
              "deal_probability", "pre_value", "post_value"]
    fields += [f"{phase}_{action}" for phase in ("pre", "post")
               for action in ("stand", "hit", "double", "split")]
    with (destination / "initial.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            row = {k: r[k] for k in ("upcard", "total", "soft", "natural")}
            row.update(cards=",".join(map(str, r["cards"])),
                       optimal_actions="|".join(r["post_check"]["optimal_actions"]) or r["post_check"]["status"],
                       deal_probability=float(r["deal_probability"]))
            for phase in ("pre", "post"):
                row[f"{phase}_value"] = float(r[f"{phase}_check"]["value"])
                for action, value in r[f"{phase}_check"]["actions"].items():
                    row[f"{phase}_{action}"] = float(value)
            writer.writerow(row)
    # Every reachable non-bust continuation state; no double or split after a hit.
    with (destination / "continuation.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["total", "soft", "upcard", "optimal_actions", "stand", "hit", "value"])
        for soft, totals in ((False, range(6, 22)), (True, range(13, 22))):
            for total in totals:
                for up in range(1, 11):
                    stand = solver.stand(total, up)
                    hit = solver._hit(total, soft, up)
                    best = max(stand, hit)
                    writer.writerow([total, soft, up,
                                     "|".join(a for a, v in (("stand", stand), ("hit", hit)) if v == best),
                                     float(stand), float(hit), float(best)])
    with (destination / "split_hands.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["split_card", "drawn_card", "upcard", "optimal_actions", "stand", "hit", "double", "value"])
        for card in range(1, 11):
            for drawn in range(1, 11):
                for up in range(1, 11):
                    r = solver.query(Hand((card, drawn), "split-aces" if card == 1 else "split"), up)["post_check"]
                    writer.writerow([card, drawn, up, "|".join(r["optimal_actions"]),
                                     *[float(r["actions"][a]) if a in r["actions"] else ""
                                       for a in ("stand", "hit", "double")], float(r["value"])])
    return {"directory": str(destination), "initial_rows": len(rows),
            "continuation_rows": 250, "split_hand_rows": 1000}


def main():
    parser = argparse.ArgumentParser(description="Exact infinite-deck S17, peek, DAS, one-split blackjack solver")
    sub = parser.add_subparsers(dest="command", required=True)
    query = sub.add_parser("query", help="Evaluate a hand; JSON includes exact and decimal EVs")
    query.add_argument("cards", nargs="+", help="Cards in deal order, e.g. A 7 or 10,6")
    query.add_argument("--upcard", required=True)
    query.add_argument("--origin", choices=["original", "split", "split-aces"], default="original")
    sub.add_parser("overall", help="Expected net profit per initial bet")
    exp = sub.add_parser("export", help="Write strategy and EV tables (overwrites named export files)")
    exp.add_argument("--output", type=Path, default=Path("exports"))
    from .evaluation import add_arguments, run as run_evaluation
    evaluation = sub.add_parser("evaluate", help="Compare finite six-deck counting and betting policies")
    add_arguments(evaluation)
    gui = sub.add_parser("gui", help="Open the local blackjack decision interface")
    gui.add_argument("--host", default="127.0.0.1")
    gui.add_argument("--port", type=int, default=8765)
    gui.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()
    if args.command == "gui":
        from .gui import serve
        serve(args.host, args.port, args.open_browser)
        return
    solver = Solver()
    try:
        if args.command == "query":
            cards = tuple(parse_card(c) for token in args.cards for c in token.split(","))
            result = solver.query(Hand(cards, args.origin), parse_card(args.upcard))
        elif args.command == "overall":
            result = solver.overall()
        elif args.command == "evaluate":
            result = run_evaluation(args)
        else:
            result = export(solver, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(serializable(result), indent=2))
