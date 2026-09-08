"""Interactive rounds. Private shoe state never crosses the public API."""
from copy import deepcopy
from types import SimpleNamespace

from .counting import Observation
from .finite import FULL_SHOE
from .solver import Hand, parse_card


class LiveGame:
    def __init__(self, app, payload):
        self.app = app
        threshold = payload.get('threshold', 26)
        if threshold not in (None, 26, 52, 104, 156):
            raise ValueError('Choose a supported reshuffle threshold.')
        self.threshold = threshold
        self.round = 0
        self.profit = 0.0
        self.revision = 0
        self.shuffle()
        self.start(payload)

    def shuffle(self):
        self.deck = list(FULL_SHOE)
        self.app.rng.shuffle(self.deck)
        self.counts = [0] * 11
        self.dealt = 0
        self.mucked = []
        self.current_hidden = False

    def draw(self):
        if not self.deck:
            raise ValueError('Shoe exhausted; start a new shoe.')
        self.dealt += 1
        return self.deck.pop()

    def exposed(self, card):
        self.counts[card] += 1
        return card

    def take_initial(self, card):
        self.condition_card(card)
        self.dealt += 1
        return self.exposed(card)

    def condition_card(self, card):
        # Resample ALL latent cards, including previously mucked holes. This
        # prevents a manual-card availability error from revealing a hole rank.
        hidden = list(self.mucked)
        if self.current_hidden:
            hidden.append((self.hole, self.upcard))
        pool = self.deck + [c for c, _ in hidden]
        if card not in pool:
            raise ValueError('That rank is unavailable among the unseen cards.')
        pool.remove(card)
        if len(pool) < len(hidden):
            raise ValueError('No card remains to draw.')
        for _ in range(10000):
            self.app.rng.shuffle(pool)
            assigned = pool[:len(hidden)]
            if all({c, up} != {1, 10} for c, (_, up) in zip(assigned, hidden)):
                self.deck = pool[len(hidden):]
                self.mucked = [(c, up) for c, (_, up) in zip(assigned, hidden)][:len(self.mucked)]
                if self.current_hidden:
                    self.hole = assigned[-1]
                return
        raise ValueError('Cannot reconcile this card with prior dealer checks; try another card or start a new shoe.')

    def start(self, payload):
        if self.round and self.status != 'settled':
            raise ValueError('Finish this round first.')
        self.reshuffled = bool(self.round and (self.threshold is None or self.dealt >= self.threshold))
        if self.reshuffled:
            self.shuffle()
        from .gui import card_list
        entered = card_list(payload.get('cards', ''), 'Starting cards', True)
        if entered and len(entered) != 2:
            raise ValueError('Enter two starting cards, or leave blank for random cards.')
        up = payload.get('upcard', 'random')
        # Reserve specified exposed cards before sampling any unknown cards.
        cards = [self.take_initial(c) for c in entered]
        self.upcard = self.take_initial(parse_card(up)) if up != 'random' else None
        if not cards:
            cards = [self.exposed(self.draw()), self.exposed(self.draw())]
        if self.upcard is None:
            self.upcard = self.exposed(self.draw())
        self.hole = self.draw()
        self.current_hidden = True
        self.dealer = [self.upcard]
        self.hands = [dict(cards=cards, origin='original', wager=1, done=False)]
        self.active = 0
        self.pending = None
        self.status = 'playing'
        self.round += 1
        self.result = None
        natural = Hand(tuple(cards)).natural
        if {self.upcard, self.hole} == {1, 10}:
            self.dealer.append(self.exposed(self.hole))
            self.current_hidden = False
            self.finish(0 if natural else -1, 'Dealer blackjack')
        elif natural:
            self.finish(1.5, 'Blackjack pays 3:2')

    def finish(self, profit, message):
        if self.current_hidden:
            self.mucked.append((self.hole, self.upcard))
            self.current_hidden = False
        self.status = 'settled'
        self.pending = None
        self.hands[self.active]['done'] = True
        self.result = dict(profit=profit, message=message)
        self.profit += profit

    def receive(self, selection):
        if selection == 'random':
            return self.exposed(self.draw())
        card = parse_card(selection)
        self.condition_card(card)
        self.dealt += 1
        return self.exposed(card)

    def advance(self):
        hand = self.hands[self.active]
        if not hand['done']:
            return
        if self.active + 1 < len(self.hands):
            self.active += 1
            self.pending = 'split-card'
            return
        if all(Hand(tuple(h['cards']), h['origin']).state[0] > 21 for h in self.hands):
            self.finish(-sum(h['wager'] for h in self.hands), 'All hands bust')
            return
        self.dealer.append(self.exposed(self.hole))
        self.current_hidden = False
        from .counting import total
        while total(sum(self.dealer), 1 in self.dealer) < 17:
            self.dealer.append(self.exposed(self.draw()))
        dealer_total = total(sum(self.dealer), 1 in self.dealer)
        profit = 0
        for h in self.hands:
            t = Hand(tuple(h['cards']), h['origin']).state[0]
            profit += h['wager'] * (-1 if t > 21 else 1 if dealer_total > 21 or t > dealer_total else -1 if t < dealer_total else 0)
        self.finish(profit, 'Dealer busts' if dealer_total > 21 else f'Dealer stands on {dealer_total}')

    def act(self, payload):
        action = payload.get('action')
        if action == 'settings':
            threshold = payload.get('threshold')
            if threshold not in (None, 26, 52, 104, 156):
                raise ValueError('Choose a supported reshuffle threshold.')
            self.threshold = threshold
            return
        if action == 'next':
            self.start(payload)
            return
        if self.status != 'playing':
            raise ValueError('This round is finished. Deal the next round.')
        h = self.hands[self.active]
        if action == 'card':
            if not self.pending:
                raise ValueError('Choose hit, double or split before drawing a card.')
            kind = self.pending
            h['cards'].append(self.receive(payload.get('card', 'random')))
            self.pending = None
            t = Hand(tuple(h['cards']), h['origin']).state[0]
            h['done'] = kind == 'double' or h['origin'] == 'split-aces' or t >= 21
            self.advance()
            return
        if self.pending:
            raise ValueError('Supply the pending card first.')
        legal = self.app.solver.actions(Hand(tuple(h['cards']), h['origin']), self.upcard)
        if action not in legal:
            raise ValueError('That action is not legal for this hand.')
        if action == 'stand':
            h['done'] = True
            self.advance()
        elif action in ('hit', 'double'):
            if action == 'double':
                h['wager'] = 2
            self.pending = action
        elif action == 'split':
            rank = h['cards'][0]
            origin = 'split-aces' if rank == 1 else 'split'
            self.hands = [dict(cards=[rank], origin=origin, wager=1, done=False) for _ in range(2)]
            self.active = 0
            self.pending = 'split-card'

    def public(self, method):
        observation = Observation(tuple(self.counts), self.dealt)
        analysis = None
        if self.status == 'playing' and not self.pending:
            h = self.hands[self.active]
            analysis = self.app._analysis(SimpleNamespace(hand=Hand(tuple(h['cards']), h['origin']),
                                                         upcard=self.upcard, observation=observation), method)
        from .counting import total
        return dict(revision=self.revision, status=self.status, round=self.round,
                    hands=[dict(h, total=total(sum(h['cards']), 1 in h['cards'])) for h in self.hands],
                    active=self.active, pending=self.pending, dealer=list(self.dealer),
                    revealed=len(self.dealer) > 1, analysis=analysis, result=self.result,
                    profit=self.profit, dealt=self.dealt, threshold=self.threshold,
                    reshuffled=self.reshuffled, count=dict(running=observation.running_count,
                    true=observation.true_count, visible=sum(self.counts)),
                    next_edge=self.app.models.estimate(method, observation) if self.status == 'settled' and not (self.threshold is None or self.dealt >= self.threshold) else None)

    def clone(self):
        other = object.__new__(LiveGame)
        other.__dict__ = {k: v if k == 'app' else deepcopy(v) for k, v in self.__dict__.items()}
        return other
