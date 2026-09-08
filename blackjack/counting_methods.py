"""Research count adapters: common analytic action sensitivities, no outcome fitting.

Named methods use published tags, not proprietary published index tables.
The composition method is a first-order policy, not an exact finite-shoe bound.
"""
from pathlib import Path
import struct

from .counting import Approximation, BASE, StrategyTables, state
from .solver import Solver

ACTIONS = ("stand", "hit", "double", "split")
STATE_COUNT = 10 * 22 * 2 * 3
TAGS = {
    "halves": (-1, .5, 1, 1, 1.5, 1, .5, 0, -.5, -1),
    "hiopt2-ace": (0, 1, 1, 2, 2, 1, 1, 0, 0, -2),
    "omega2-ace": (0, 1, 1, 2, 2, 2, 1, 0, -1, -2),
    "ko-centered": (-1, 1, 1, 1, 1, 1, 1, 0, 0, -1),
}
METHODS = ("baseline", "hilo", *TAGS, "composition")


def state_index(up, raw, ace, kind):
    return (((up - 1) * 22 + raw) * 2 + int(ace)) * 3 + kind


def hand_index(cards, up, origin):
    raw, ace = state(cards)
    kind = 0 if len(cards) > 2 else 2 if origin == "original" and cards[0] == cards[1] else 1
    return state_index(up, raw, ace, kind)


def features(name):
    """Rows applied to visible rank counts, then divided by the unseen pool."""
    p = BASE[1:]
    if name == "composition":
        return [[p[c] - float(c == d) for d in range(10)] for c in range(10)]
    t = TAGS[name]
    mean = sum(a * b for a, b in zip(t, p))
    rows = [[x - mean for x in t]]
    if name.endswith("-ace"):
        rows.append([float(c == 0) - p[0] for c in range(10)])
    return rows


def projected_gradient(name, gradient):
    """Weighted least-squares projection onto count and optional ace information."""
    if name == "composition":
        return list(gradient)
    out = []
    # The ace-neutral balanced tag and centered ace count are orthogonal under BASE.
    for row in features(name):
        variance = sum(p * t * t for p, t in zip(BASE[1:], row))
        out.append(-sum(g * p * t for g, p, t in zip(gradient, BASE[1:], row)) / variance)
    return out


class ResearchModels:
    def __init__(self, epsilon=1e-5):
        if not 0 < epsilon < .01:
            raise ValueError("epsilon must lie in (0, .01)")
        self.epsilon = epsilon
        self.legacy = StrategyTables()
        baseline = self.legacy.baseline
        center = Approximation(BASE, baseline)
        self.edge = center.edge
        self.base = [[-1e90] * 4 for _ in range(STATE_COUNT)]
        self.exact_choices = [0] * STATE_COUNT
        s = Solver()
        for (up, raw, ace, kind), a in center.state_action_values.items():
            i = state_index(up, raw, ace, kind)
            t = raw + 10 if ace and raw <= 11 else raw
            soft = ace and raw <= 11
            exact = {"stand": s.stand(t, up), "hit": s._hit(t, soft, up)}
            if kind:
                exact["double"] = s._double(t, soft, up)
            if kind == 2:
                exact["split"] = s._split(raw // 2, up)
            self.exact_choices[i] = ACTIONS.index(max(exact, key=exact.get))
            for name, v in a.items():
                self.base[i][ACTIONS.index(name)] = v
        gradients = [[[0.0] * 10 for _ in range(4)] for _ in range(STATE_COUNT)]
        edge_grad = []
        for c in range(1, 11):
            direction = [float(r == c) - BASE[r] for r in range(11)]
            plus = Approximation(tuple(p + epsilon * d for p, d in zip(BASE, direction)), baseline)
            minus = Approximation(tuple(p - epsilon * d for p, d in zip(BASE, direction)), baseline)
            edge_grad.append((plus.edge - minus.edge) / (2 * epsilon))
            for key, a in center.state_action_values.items():
                i = state_index(*key)
                for name in a:
                    gradients[i][ACTIONS.index(name)][c - 1] = (
                        plus.state_action_values[key][name] - minus.state_action_values[key][name]) / (2 * epsilon)
        self.edge_gradient = edge_grad
        self.gradients = gradients
        self.coefficients = {}
        self.edge_coefficients = {}
        for name in METHODS[2:]:
            self.coefficients[name] = [[projected_gradient(name, g) for g in row] for row in gradients]
            self.edge_coefficients[name] = projected_gradient(name, edge_grad)
        self.legacy_choices = []
        for index in range(-48, 49):
            table = self.legacy.optimized[index]
            choices = [0] * STATE_COUNT
            for key, a in table.state_action_values.items():
                choices[state_index(*key)] = ACTIONS.index(max(a, key=a.get))
            self.legacy_choices.append(choices)

    def observation_features(self, name, observation):
        counts = observation.visible_counts[1:]
        unseen = 312 - sum(counts)
        return [sum(x * y for x, y in zip(row, counts)) / unseen for row in features(name)]

    def estimate(self, name, observation):
        if name in ("baseline", "hilo"):
            return self.legacy.estimate(observation, "baseline" if name == "baseline" else "counting")
        f = self.observation_features(name, observation)
        return self.edge + sum(g * v for g, v in zip(self.edge_coefficients[name], f))

    def choose(self, name, cards, upcard, origin, observation):
        i = hand_index(cards, upcard, origin)
        if name == "baseline":
            return ACTIONS[self.exact_choices[i]]
        if name == "hilo":
            return ACTIONS[self.legacy_choices[self.legacy.index(observation) + 48][i]]
        f = self.observation_features(name, observation)
        values = [v + sum(g * x for g, x in zip(coef, f))
                  for v, coef in zip(self.base[i], self.coefficients[name][i])]
        return ACTIONS[max(range(4), key=values.__getitem__)]

    def export(self, path):
        """Portable little-endian coefficients for the optional C++ evaluator."""
        with Path(path).open("wb") as stream:
            stream.write(b"BJCOUNT1")
            def doubles(values):
                values = list(values)
                stream.write(struct.pack("<" + "d" * len(values), *values))
            stream.write(struct.pack("<II", STATE_COUNT, len(METHODS)))
            stream.write(bytes(self.exact_choices))
            for row in self.base:
                doubles(row)
            for row in self.legacy_choices:
                stream.write(bytes(row))
            doubles(self.legacy.baseline_edges[i] for i in range(-48, 49))
            doubles(self.legacy.optimized[i].edge for i in range(-48, 49))
            for name in METHODS[2:]:
                rows = features(name)
                encoded = name.encode("ascii")
                stream.write(struct.pack("<I", len(encoded)))
                stream.write(encoded)
                stream.write(struct.pack("<I", len(rows)))
                for row in rows:
                    doubles(row)
                doubles([self.edge, *self.edge_coefficients[name]])
                for state_row in self.coefficients[name]:
                    for action_row in state_row:
                        doubles(action_row)


class ResearchPolicy:
    def __init__(self, models, name):
        if name not in METHODS:
            raise ValueError("Unknown counting method")
        self.models, self.name = models, name

    def choose(self, cards, upcard, origin, observation):
        return self.models.choose(self.name, cards, upcard, origin, observation)
