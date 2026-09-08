"""Local browser interface for the exact solver and observable counting adapters.

Run with ``python3 -m blackjack gui``. No web framework or external assets.
Private shoes and dealer cards live on the server. The playable table supports
consecutive rounds, random or entered player draws, and observable strategy EVs.
"""
import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import random
import re
import secrets
import threading
from time import monotonic
from urllib.parse import urlsplit
import webbrowser

from .counting import Observation
from .counting_methods import ACTIONS, METHODS, ResearchModels, hand_index
from .solver import Hand, Solver, add_card, parse_card

ASSETS = Path(__file__).with_name("web")
METHOD_LABELS = {
    "baseline": "Infinite-deck baseline",
    "hilo": "Hi-Lo",
    "halves": "Wong Halves",
    "hiopt2-ace": "Hi-Opt II + ace count",
    "omega2-ace": "Omega II + ace count",
    "ko-centered": "KO, centered",
    "composition": "Full-rank counting",
}
ORIGINS = {"original", "split", "split-aces"}
CAPACITY = (0,) + (24,) * 9 + (96,)


class InputError(ValueError):
    pass


def card_list(value, label, allow_empty=False):
    if isinstance(value, str):
        tokens = [c for c in re.split(r"[\s,;]+", value.strip()) if c]
    elif isinstance(value, list):
        tokens = value
    else:
        raise InputError(f"{label} must be card text or a list of cards.")
    if len(tokens) > 312:
        raise InputError(f"{label} cannot contain more than 312 cards.")
    try:
        cards = tuple(parse_card(c) for c in tokens)
    except ValueError as exc:
        raise InputError(f"{label}: {exc}") from exc
    if not cards and not allow_empty:
        raise InputError("Enter at least two player cards, for example A 7 or 8,8.")
    return cards


@dataclass
class Scenario:
    created: float
    hand: Hand
    history: tuple
    dealer_selection: str
    upcard: int
    hole: int
    deck: list
    observation: Observation
    dealer_cards: list
    status: str = "decision"
    profit: float | None = None
    reason: str | None = None


class Application:
    def __init__(self, rng=None, models=None):
        self.models = models if models is not None else ResearchModels()
        self.solver = Solver()
        self.rng = rng if rng is not None else random.Random()
        self.scenarios = {}
        self.games = {}
        self.lock = threading.RLock()

    @staticmethod
    def config():
        return {"methods": [{"id": name, "label": METHOD_LABELS[name]} for name in METHODS],
                "default_method": "composition", "default_dealer": "random",
                "rules": "6-deck dealer · S17 · 3:2 blackjack · dealer peek · double after split · one split"}

    def live(self, payload):
        from .live import LiveGame
        if not isinstance(payload, dict):
            raise InputError('Send a JSON object.')
        method = payload.get('method', 'composition')
        if not isinstance(method, str) or method not in METHODS:
            raise InputError('Choose an available strategy.')
        with self.lock:
            token = payload.get('game_id')
            if token is None:
                game = LiveGame(self, payload)
                token = secrets.token_urlsafe(24)
                if len(self.games) >= 256:
                    del self.games[next(iter(self.games))]
            else:
                if not isinstance(token, str) or token not in self.games:
                    raise InputError('Session expired. Start a new shoe.')
                game = self.games[token]
                if payload.get('action'):
                    if payload.get('revision') != game.revision:
                        raise InputError('The table changed. Refresh its state before acting again.')
                    game = game.clone()
                    game.act(payload)
                    game.revision += 1
            result = game.public(method)
            self.games[token] = game
            return dict(result, game_id=token)

    def _prune(self):
        cutoff = monotonic() - 7200
        for token in list(self.scenarios):
            if self.scenarios[token].created < cutoff:
                del self.scenarios[token]
        while len(self.scenarios) >= 256:
            del self.scenarios[next(iter(self.scenarios))]

    @staticmethod
    def _validate(payload):
        if not isinstance(payload, dict):
            raise InputError("Send a JSON object.")
        cards = card_list(payload.get("cards", ""), "Player cards")
        history = card_list(payload.get("history", ""), "Earlier visible cards", True)
        origin = payload.get("origin", "original")
        if not isinstance(origin, str) or origin not in ORIGINS:
            raise InputError("Choose an original hand, split hand, or split aces.")
        hand = Hand(cards, origin)
        method = payload.get("method", "composition")
        if not isinstance(method, str) or method not in METHODS:
            raise InputError("Choose one of the available strategies.")
        if origin != "original" and cards[0] not in history:
            raise InputError("For a split hand, include its sibling's retained card in earlier visible cards.")
        selection = payload.get("upcard", "random")
        if selection != "random":
            selection = str(parse_card(selection))
        return hand, history, selection, method

    def _new_scenario(self, hand, history, selection):
        counts = [0] * 11
        for c in (*history, *hand.cards):
            counts[c] += 1
        for c in range(1, 11):
            if counts[c] > CAPACITY[c]:
                raise InputError(f"Too many {'aces' if c == 1 else str(c) + '-valued cards'} for a six-deck shoe.")
        remaining = [c for c in range(1, 11) for _ in range(CAPACITY[c] - counts[c])]
        if len(remaining) < 2:
            raise InputError("Leave at least two unseen cards for the dealer.")
        if selection == "random":
            upcard = self.rng.choice(remaining)
        else:
            upcard = int(selection)
            if upcard not in remaining:
                raise InputError("The selected dealer upcard has already been completely removed from the shoe.")
        remaining.remove(upcard)
        counts[upcard] += 1
        # A split or multi-card hand necessarily exists after a negative peek.
        cleared = hand.origin != "original" or len(hand.cards) > 2
        holes = [c for c in remaining if not (cleared and {upcard, c} == {1, 10})]
        if not holes:
            raise InputError("This shoe cannot produce the clear dealer check required by that hand history.")
        hole = self.rng.choice(holes)
        remaining.remove(hole)
        self.rng.shuffle(remaining)
        observation = Observation(tuple(counts), len(history) + len(hand.cards) + 2)
        scenario = Scenario(monotonic(), hand, history, selection, upcard, hole, remaining,
                            observation, [upcard])
        if {upcard, hole} == {1, 10}:
            scenario.dealer_cards.append(hole)
            scenario.status = "dealer_blackjack"
            scenario.profit = 0.0 if hand.natural else -1.0
            scenario.reason = "Both have blackjack: push." if hand.natural else "Dealer blackjack: the initial wager loses."
        elif hand.natural:
            scenario.status, scenario.profit = "natural", 1.5
            scenario.reason = "Original blackjack pays 3:2 after the dealer check clears."
        elif hand.state[0] > 21:
            scenario.status, scenario.profit = "bust", -1.0
            scenario.reason = "Player busts. The dealer does not draw and its hole card stays unseen."
        return scenario

    def analyze(self, payload):
        hand, history, selection, method = self._validate(payload)
        with self.lock:
            self._prune()
            token = payload.get("dealer_id")
            if token is not None and not isinstance(token, str):
                raise InputError("Invalid dealer session. Deal a new dealer.")
            if token:
                scenario = self.scenarios.get(token)
                if scenario is None:
                    raise InputError("This dealer session expired. Deal a new dealer.")
                if (hand, history, selection) != (scenario.hand, scenario.history, scenario.dealer_selection):
                    raise InputError("The hand or visible history changed. Deal a new dealer for this scenario.")
            else:
                scenario = self._new_scenario(hand, history, selection)
                token = secrets.token_urlsafe(24)
                self.scenarios[token] = scenario
            return self._public(token, scenario, method)

    def _analysis(self, s, method):
        legal = self.solver.actions(s.hand, s.upcard)
        if not legal:
            return None
        values = {}
        if method == "baseline":
            values = {a: float(v) for a, v in legal.items()}
            best = max(legal.values())
            optimal = [a for a, v in legal.items() if v == best]
        elif method == "hilo":
            table = self.models.legacy.optimized[self.models.legacy.index(s.observation)]
            raw = sum(s.hand.cards)
            ace = 1 in s.hand.cards
            kind = 0 if len(s.hand.cards) > 2 else 2 if s.hand.origin == "original" and s.hand.cards[0] == s.hand.cards[1] else 1
            row = table.state_action_values[s.upcard, raw, ace, kind]
            values = {a: row[a] for a in legal}
            best = max(values.values())
            optimal = [a for a, v in values.items() if v == best]
        else:
            i = hand_index(s.hand.cards, s.upcard, s.hand.origin)
            features = self.models.observation_features(method, s.observation)
            for a in legal:
                j = ACTIONS.index(a)
                values[a] = self.models.base[i][j] + sum(g * f for g, f in zip(self.models.coefficients[method][i][j], features))
            best = max(values.values())
            optimal = [a for a, v in values.items() if v == best]
        base_best = max(legal.values())
        ordered = sorted(values.values(), reverse=True)
        return {"method": method, "label": METHOD_LABELS[method], "exact": method == "baseline",
                "value": float(best), "optimal_actions": optimal,
                "baseline_actions": [a for a, v in legal.items() if v == base_best],
                "baseline_value": float(base_best),
                "gap": ordered[0] - ordered[1] if len(ordered) > 1 else None,
                "actions": [{"action": a, "ev": values[a], "baseline_ev": float(legal[a]),
                             "delta": values[a] - float(legal[a]), "baseline_exact": str(legal[a]),
                             "exact_fraction": str(legal[a]) if method == "baseline" else None}
                            for a in ACTIONS if a in legal]}

    def _public(self, token, s, method):
        # Deliberately enumerate public fields. Never serialize Scenario itself.
        dealer_revealed = s.status in ("dealer_blackjack", "resolved")
        dealer_total = (0, False)
        for c in s.dealer_cards:
            dealer_total = add_card(*dealer_total, c)
        return {"dealer_id": token, "status": s.status,
                "hand": {"cards": list(s.hand.cards), "origin": s.hand.origin,
                         "total": s.hand.state[0], "soft": s.hand.state[1], "natural": s.hand.natural},
                "dealer": {"upcard": s.upcard, "selection": s.dealer_selection,
                           "cards": list(s.dealer_cards), "revealed": dealer_revealed,
                           "total": dealer_total[0] if dealer_revealed else None,
                           "soft": dealer_total[1] if dealer_revealed else None,
                           "check": "blackjack" if s.status == "dealer_blackjack" else "clear"},
                "count": {"running": s.observation.running_count, "true": s.observation.true_count,
                          "visible": sum(s.observation.visible_counts),
                          "unseen": 312 - sum(s.observation.visible_counts),
                          "counts": list(s.observation.visible_counts[1:])},
                "analysis": self._analysis(s, method) if s.status == "decision" else None,
                "settlement": {"profit": s.profit, "reason": s.reason} if s.profit is not None else None}

    def resolve_stand(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("dealer_id"), str):
            raise InputError("Analyze a hand before resolving the dealer.")
        method = payload.get("method", "composition")
        if not isinstance(method, str) or method not in METHODS:
            raise InputError("Choose one of the available strategies.")
        with self.lock:
            self._prune()
            token = payload["dealer_id"]
            s = self.scenarios.get(token)
            if s is None:
                raise InputError("This dealer session expired. Deal a new dealer.")
            if s.status == "decision":
                # Compute in local copies so an exhausted scenario cannot be half-resolved.
                deck = list(s.deck)
                cards = [s.upcard, s.hole]
                total, soft = 0, False
                for c in cards:
                    total, soft = add_card(total, soft, c)
                while total < 17:
                    if not deck:
                        raise InputError("The unseen pool ran out before the dealer could finish. Reduce the earlier-card history.")
                    c = deck.pop()
                    cards.append(c)
                    total, soft = add_card(total, soft, c)
                player_total = s.hand.state[0]
                s.profit = 1.0 if total > 21 or player_total > total else -1.0 if player_total < total else 0.0
                s.reason = "Dealer busts: standing wins." if total > 21 else "Standing wins." if s.profit > 0 else "Standing loses." if s.profit < 0 else "Equal totals: push."
                s.deck, s.dealer_cards, s.status = deck, cards, "resolved"
            return self._public(token, s, method)


def make_handler(application):
    assets = {"/": ("index.html", "text/html; charset=utf-8"),
              "/index.html": ("index.html", "text/html; charset=utf-8"),
              "/app.js": ("app.js", "text/javascript; charset=utf-8"),
              "/style.css": ("style.css", "text/css; charset=utf-8")}

    class Handler(BaseHTTPRequestHandler):
        def send_data(self, status, content, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(content)

        def send_json(self, status, value):
            self.send_data(status, json.dumps(value, allow_nan=False).encode("utf-8"))

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/config":
                self.send_json(200, application.config())
            elif path in assets:
                filename, content_type = assets[path]
                self.send_data(200, (ASSETS / filename).read_bytes(), content_type)
            elif path == "/favicon.ico":
                self.send_data(204, b"", "image/x-icon")
            else:
                self.send_json(404, {"error": "Not found."})

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in ("/api/analyze", "/api/resolve", "/api/play"):
                self.send_json(404, {"error": "Not found."})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 32768:
                    raise InputError("The request is empty or too large.")
                payload = json.loads(self.rfile.read(size))
                result = application.live(payload) if path == '/api/play' else application.analyze(payload) if path == "/api/analyze" else application.resolve_stand(payload)
                self.send_json(200, result)
            except (ValueError, TypeError, UnicodeError) as exc:
                message = str(exc) if not isinstance(exc, json.JSONDecodeError) else "Invalid JSON request."
                self.send_json(400, {"error": message})

        def log_message(self, format, *args):
            pass

    return Handler


def serve(host="127.0.0.1", port=8765, open_browser=False):
    application = Application()
    with ThreadingHTTPServer((host, port), make_handler(application)) as server:
        url = f"http://{host}:{server.server_address[1]}"
        print(f"Blackjack decision lab: {url}\nPress Ctrl+C to stop.", flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()
    serve(args.host, args.port, args.open_browser)
