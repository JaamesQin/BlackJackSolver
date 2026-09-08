"""Exact six-deck dealing and settlement for experimental shallow-shoe games.

Only Observation snapshots cross into strategies. The shoe, hole-card rank,
shuffle RNG, and future cards stay in the engine. No mid-round reshuffling.
"""
from dataclasses import dataclass
from random import Random

from .counting import Counter, total

FULL_SHOE = tuple(c for c in range(1, 11) for _ in range(96 if c == 10 else 24))


class Shoe:
    def __init__(self, cards):
        self._cards = tuple(cards)
        self.dealt = 0

    @classmethod
    def shuffled(cls, rng: Random):
        cards = list(FULL_SHOE)
        rng.shuffle(cards)
        return cls(cards)

    def draw(self):
        if self.dealt == len(self._cards):
            raise RuntimeError("Shoe exhausted; refusing to reshuffle inside a round")
        c = self._cards[self.dealt]
        self.dealt += 1
        return c


@dataclass(frozen=True)
class RoundResult:
    unit_profit: float
    initial_bet: float
    estimated_edge: float
    cards_dealt: int
    visible_cards: int
    true_count_before: float

    @property
    def profit(self):
        return self.unit_profit * self.initial_bet


def play_round(shoe, counter, playing, betting, estimate):
    """Choose the bet before drawing any cards, then play a complete round.

    `estimate` and `playing.choose` receive public information exclusively.
    A hole card is shown on dealer blackjack or when resolving a live ordinary
    hand. It is mucked unseen on a player natural or if every player hand busts.
    All hole cards still consume shoe penetration, whether shown or mucked.
    """
    before = counter.snapshot()
    edge = estimate(before)
    bet = betting.choose(edge)
    dealt_before = shoe.dealt
    seen_before = sum(counter.counts)

    def draw(visible=True):
        card = shoe.draw()
        counter.dealt += 1
        if visible:
            counter.observe(card)
        return card

    c = draw()
    up = draw()
    d = draw()
    hole = draw(False)
    natural = {c, d} == {1, 10}

    def result(profit):
        return RoundResult(profit, bet, edge, shoe.dealt - dealt_before,
                           sum(counter.counts) - seen_before, before.true_count)

    if {up, hole} == {1, 10}:
        counter.observe(hole)
        return result(0.0 if natural else -1.0)
    if natural:
        return result(1.5)

    def play(cards, origin):
        raw = sum(cards)
        ace = 1 in cards
        if origin == "split-aces":
            return [(total(raw, ace), 1)]
        while raw <= 21:
            action = playing.choose(tuple(cards), up, origin, counter.snapshot())
            if action == "stand":
                return [(total(raw, ace), 1)]
            if action == "split":
                if origin != "original" or len(cards) != 2 or cards[0] != cards[1]:
                    raise ValueError("Illegal split requested by policy")
                retained = cards[0]
                child_origin = "split-aces" if retained == 1 else "split"
                # Complete the first hand before drawing the second child's card.
                first = play([retained, draw()], child_origin)
                second = play([retained, draw()], child_origin)
                return first + second
            if action not in ("hit", "double") or (action == "double" and len(cards) != 2):
                raise ValueError(f"Illegal action requested by policy: {action}")
            new = draw()
            cards.append(new)
            raw += new
            ace = ace or new == 1
            if action == "double":
                return [(total(raw, ace), 2)]
        return [(raw, 1)]

    hands = play([c, d], "original")
    if all(t > 21 for t, _ in hands):
        return result(-sum(wager for _, wager in hands))
    counter.observe(hole)
    raw = up + hole
    ace = up == 1 or hole == 1
    while total(raw, ace) < 17:
        new = draw()
        raw += new
        ace = ace or new == 1
    dealer = total(raw, ace)
    profit = sum(-wager if t > 21 else wager if dealer > 21 or t > dealer
                 else -wager if t < dealer else 0 for t, wager in hands)
    return result(float(profit))


def shoe_rounds(rng, threshold, playing, betting, estimate):
    """One independent regenerative cycle. None means reshuffle every round."""
    if threshold is not None and threshold not in (26, 52, 104, 156):
        raise ValueError("Supported card thresholds are 26, 52, 104, and 156, or None for every round")
    shoe = Shoe.shuffled(rng)
    counter = Counter()
    while True:
        yield play_round(shoe, counter, playing, betting, estimate)
        if threshold is None or shoe.dealt >= threshold:
            return
