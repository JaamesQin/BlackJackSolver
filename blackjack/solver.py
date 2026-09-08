"""All monetary values are net returns per original one-unit wager.

The public hand representation retains provenance. Internal continuation states
compress cards only because draws are independent and resplitting is prohibited.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from functools import cache
from typing import Protocol


class IndependentDrawModel(Protocol):
    """Stationary draw law; finite shoes require a richer state (see README)."""

    @property
    def outcomes(self) -> tuple[tuple[int, F], ...]: ...


@dataclass(frozen=True)
class InfiniteDeck:
    @property
    def outcomes(self) -> tuple[tuple[int, F], ...]:
        return tuple((c, F(4 if c == 10 else 1, 13)) for c in range(1, 11))


def parse_card(card: str | int) -> int:
    if isinstance(card, bool):
        raise ValueError("Invalid card")
    token = str(card).strip().upper()
    if token in {"A", "J", "Q", "K", "T"}:
        return 1 if token == "A" else 10
    try:
        value = int(token)
    except ValueError as exc:
        raise ValueError(f"Invalid card: {card!r}") from exc
    if not 1 <= value <= 10:
        raise ValueError(f"Card must be A, 2–10, J, Q, K: {card!r}")
    return value


def add_card(total: int, soft: bool, card: int) -> tuple[int, bool]:
    total += card
    if card == 1 and total + 10 <= 21:
        total += 10
        soft = True
    if total > 21 and soft:
        total -= 10
        soft = False
    return total, soft


@dataclass(frozen=True)
class Hand:
    cards: tuple[int, ...]
    origin: str = "original"

    def __post_init__(self):
        object.__setattr__(self, "cards", tuple(parse_card(c) for c in self.cards))
        if self.origin not in {"original", "split", "split-aces"}:
            raise ValueError("Origin must be original, split, or split-aces")
        if len(self.cards) < 2:
            raise ValueError("Provide at least two cards")
        if self.origin == "split-aces" and (len(self.cards) != 2 or self.cards[0] != 1):
            raise ValueError("A split-aces hand must be A plus exactly one card")
        if self.origin == "split" and self.cards[0] == 1:
            raise ValueError("Use split-aces for a hand split from aces")
        total, soft = 0, False
        for i, c in enumerate(self.cards):
            if i >= 2 and (total > 21 or (self.origin == "original" and i == 2
                                         and sorted(self.cards[:2]) == [1, 10])):
                raise ValueError("Cards cannot be added after bust or an original natural")
            total, soft = add_card(total, soft, c)

    @property
    def state(self) -> tuple[int, bool]:
        total, soft = 0, False
        for c in self.cards:
            total, soft = add_card(total, soft, c)
        return total, soft

    @property
    def natural(self) -> bool:
        return self.origin == "original" and len(self.cards) == 2 and sorted(self.cards) == [1, 10]


class Solver:
    def __init__(self, model: IndependentDrawModel | None = None):
        self.model = model or InfiniteDeck()
        self.draws = tuple(self.model.outcomes)
        if (len({c for c, _ in self.draws}) != len(self.draws)
                or any(c not in range(1, 11) or not isinstance(p, F) or p <= 0
                       for c, p in self.draws)
                or sum(p for _, p in self.draws) != 1):
            raise ValueError("Draw outcomes must be unique cards with positive Fraction probabilities summing to 1")

    def blackjack_probability(self, upcard: int) -> F:
        upcard = parse_card(upcard)
        complement = 10 if upcard == 1 else 1 if upcard == 10 else None
        return sum((p for c, p in self.draws if c == complement), F(0))

    @cache
    def _dealer(self, total: int, soft: bool) -> tuple[F, ...]:
        # Slots: bust, 17, 18, 19, 20, 21. Natural excluded by caller.
        if total > 21 or total >= 17:
            slot = 0 if total > 21 else total - 16
            return tuple(F(i == slot) for i in range(6))
        result = [F(0)] * 6
        for c, p in self.draws:
            for i, value in enumerate(self._dealer(*add_card(total, soft, c))):
                result[i] += p * value
        return tuple(result)

    @cache
    def dealer_distribution(self, upcard: int) -> tuple[F, ...]:
        """Distribution conditional on dealer having no natural."""
        upcard = parse_card(upcard)
        q = self.blackjack_probability(upcard)
        if q == 1:
            raise ValueError("Post-check event has zero probability")
        result = [F(0)] * 6
        start = add_card(0, False, upcard)
        for hole, p in self.draws:
            if {upcard, hole} == {1, 10}:
                continue
            for i, value in enumerate(self._dealer(*add_card(*start, hole))):
                result[i] += p * value / (1 - q)
        return tuple(result)

    @cache
    def stand(self, total: int, upcard: int) -> F:
        if total > 21:
            return F(-1)
        dist = self.dealer_distribution(upcard)
        return dist[0] + sum((p * ((total > d) - (total < d))
                             for d, p in zip(range(17, 22), dist[1:])), F(0))

    @cache
    def _hit(self, total: int, soft: bool, upcard: int) -> F:
        return sum((p * self._continuation(*add_card(total, soft, c), upcard)
                    for c, p in self.draws), F(0))

    @cache
    def _continuation(self, total: int, soft: bool, upcard: int) -> F:
        if total > 21:
            return F(-1)
        return max(self.stand(total, upcard), self._hit(total, soft, upcard))

    def _double(self, total: int, soft: bool, upcard: int) -> F:
        return 2 * sum((p * self.stand(add_card(total, soft, c)[0], upcard)
                        for c, p in self.draws), F(0))

    @cache
    def _split(self, card: int, upcard: int) -> F:
        single = F(0)
        for c, p in self.draws:
            total, soft = Hand((card, c), "split-aces" if card == 1 else "split").state
            value = self.stand(total, upcard)
            if card != 1:
                value = max(value, self._hit(total, soft, upcard), self._double(total, soft, upcard))
            single += p * value
        # Linearity holds even with a shared dealer outcome.
        return 2 * single

    def actions(self, hand: Hand, upcard: int) -> dict[str, F]:
        """Legal action EVs AFTER a negative dealer blackjack check."""
        upcard = parse_card(upcard)
        total, soft = hand.state
        if hand.natural or total > 21:
            return {}
        values = {"stand": self.stand(total, upcard)}
        if hand.origin == "split-aces":
            return values
        values["hit"] = self._hit(total, soft, upcard)
        if len(hand.cards) == 2:
            values["double"] = self._double(total, soft, upcard)
            if hand.origin == "original" and hand.cards[0] == hand.cards[1]:
                values["split"] = self._split(hand.cards[0], upcard)
        return values

    def value(self, hand: Hand, upcard: int) -> F:
        if hand.natural:
            return F(3, 2)
        if hand.state[0] > 21:
            return F(-1)
        return max(self.actions(hand, upcard).values())

    def query(self, hand: Hand, upcard: int) -> dict:
        upcard = parse_card(upcard)
        actions = self.actions(hand, upcard)
        value = self.value(hand, upcard)
        q = self.blackjack_probability(upcard)
        initial = hand.origin == "original" and len(hand.cards) == 2
        pre = None
        if initial:
            immediate = F(0) if hand.natural else F(-1)
            pre = {"value": q * immediate + (1 - q) * value,
                   "actions": {a: -q + (1 - q) * v for a, v in actions.items()}}
        return {"cards": list(hand.cards), "origin": hand.origin, "upcard": upcard,
                "total": hand.state[0], "soft": hand.state[1],
                "natural": hand.natural, "dealer_blackjack_probability": q,
                "post_check": {"value": value, "actions": actions,
                               "optimal_actions": [a for a, v in actions.items() if v == value],
                               "status": "natural" if hand.natural else "bust" if hand.state[0] > 21 else "decision"},
                "pre_check": pre}

    def initial_rows(self):
        """All 550 unordered initial hand / upcard combinations."""
        for c, p in self.draws:
            for d, r in self.draws:
                if d < c:
                    continue
                for up, s in self.draws:
                    row = self.query(Hand((c, d)), up)
                    row["deal_probability"] = p * r * s * (1 if c == d else 2)
                    yield row

    def overall(self) -> dict[str, F]:
        pre = F(0)
        post_weighted = F(0)
        no_blackjack = F(0)
        for row in self.initial_rows():
            p = row["deal_probability"]
            pre += p * row["pre_check"]["value"]
            weight = p * (1 - row["dealer_blackjack_probability"])
            no_blackjack += weight
            post_weighted += weight * row["post_check"]["value"]
        return {"pre_check_ev": pre,
                "post_check_ev_conditional": post_weighted / no_blackjack,
                "dealer_blackjack_probability": 1 - no_blackjack,
                "house_edge": -pre}
