import unittest
import random
from blackjack.gui import Application
from blackjack.counting_methods import ResearchModels


class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = ResearchModels()

    def setUp(self):
        self.app = Application(random.Random(42), self.models)

    def start(self, cards='5 5', **kw):
        self.r = self.app.live(dict(cards=cards, upcard=6, **kw))
        return self.r

    def act(self, action, **kw):
        self.r = self.app.live(dict(game_id=self.r['game_id'], revision=self.r['revision'], action=action, **kw))
        return self.r

    def test_hit_manual_and_random_preserve_dealer(self):
        self.start()
        self.act('hit')
        self.assertEqual(self.r['pending'], 'hit')
        self.act('card', card=2)
        self.assertEqual(self.r['hands'][0]['cards'], [5,5,2])
        self.assertEqual(self.r['dealer'], [6])
        self.assertEqual(self.r['count']['visible'], 4)
        self.assertEqual(self.r['dealt'], 5)
        self.assertEqual({a['action'] for a in self.r['analysis']['actions']}, {'hit','stand'})
        self.act('hit')
        self.act('card', card='random')
        self.assertEqual(len(self.r['hands'][0]['cards']), 4)

    def test_double_bust_loses_two_and_mucks_hole(self):
        self.start('10 6')
        self.act('double')
        self.act('card', card=10)
        self.assertEqual(self.r['result']['profit'], -2)
        self.assertEqual(self.r['dealer'], [6])
        self.assertEqual(self.r['count']['visible'], 4)
        self.assertEqual(self.r['dealt'], 5)

    def test_split_sequential_and_double_after_split(self):
        self.start('8 8')
        self.act('split')
        self.assertEqual([h['cards'] for h in self.r['hands']], [[8],[8]])
        self.act('card', card=3)
        self.assertNotIn('split', [a['action'] for a in self.r['analysis']['actions']])
        self.act('double')
        self.act('card', card=10)
        self.assertEqual(self.r['active'], 1)
        self.assertEqual(self.r['hands'][0]['wager'], 2)
        self.assertEqual(self.r['pending'], 'split-card')
        self.act('card', card=10)
        self.act('stand')
        self.assertEqual(self.r['status'], 'settled')
        self.assertTrue(self.r['revealed'])
        self.assertEqual(self.r['dealt'], self.r['count']['visible'])

    def test_split_aces_one_card_no_blackjack_payout(self):
        self.start('A A')
        self.act('split')
        self.act('card', card=10)
        self.assertEqual(self.r['active'], 1)
        self.act('card', card=10)
        self.assertEqual(self.r['status'], 'settled')
        self.assertIn(self.r['result']['profit'], (0,2))

    def test_rounds_and_reshuffle(self):
        for threshold in (None,26,52,104,156):
            self.start('10 6', threshold=threshold)
            self.act('hit'); self.act('card',card=10)
            dealt = self.r['dealt']
            self.act('next', cards='5 5', upcard=6)
            self.assertEqual(self.r['dealt'], 4 if threshold is None else dealt+4)
            self.assertEqual(self.r['profit'], -1)
            self.assertEqual(self.r['round'], 2)
        # Reach threshold during a round: reset only when the next starts.
        self.start('10 6')
        game = self.app.games[self.r['game_id']]
        for _ in range(22):
            game.exposed(game.draw())
        self.act('hit'); self.act('card',card=10)
        self.assertEqual(self.r['dealt'],27)
        self.act('next',cards='5 5',upcard=6)
        self.assertEqual(self.r['dealt'],4)
        self.assertEqual(self.r['count']['visible'],3)

    def test_invalid_atomic_and_duplicate_action(self):
        self.start('5 4')
        original=self.r
        with self.assertRaises(ValueError): self.act('split')
        self.assertEqual(self.app.games[self.r['game_id']].revision,original['revision'])
        self.act('hit')
        with self.assertRaises(ValueError): self.act('card',card='X')
        self.assertEqual(self.app.games[self.r['game_id']].pending,'hit')
        with self.assertRaises(ValueError):
            self.app.live(dict(game_id=self.r['game_id'],revision=0,action='hit'))

    def test_shuffle_setting_changes_without_replacing_round(self):
        self.start('10 6', threshold=156)
        before = self.r
        self.act('settings', threshold=None)
        self.assertEqual(self.r['hands'], before['hands'])
        self.assertEqual(self.r['dealt'], before['dealt'])
        self.assertEqual(self.r['threshold'], None)
        self.act('hit'); self.act('card', card=10)
        self.assertEqual(self.r['dealt'], 5)
        self.act('next', cards='5 4', upcard=6)
        self.assertEqual(self.r['dealt'], 4)
        self.assertTrue(self.r['reshuffled'])

    def test_manual_can_use_hidden_rank_without_leak(self):
        self.start()
        game=self.app.games[self.r['game_id']]
        # The only unseen ace is the hidden card. It must remain enterable.
        game.deck=[2,3,4,5,6,7,8,9,10]
        game.hole=1
        self.act('hit'); self.act('card',card='A')
        self.assertEqual(self.r['hands'][0]['cards'],[5,5,1])
        self.assertNotIn('hole',self.r)

    def test_suggestions_independent_of_private_hole_and_future(self):
        self.start()
        game=self.app.games[self.r['game_id']]
        for method in ('baseline','hilo','composition'):
            before=game.public(method)['analysis']
            game.hole=9
            game.deck.reverse()
            self.assertEqual(before,game.public(method)['analysis'])


if __name__ == '__main__':
    unittest.main()
