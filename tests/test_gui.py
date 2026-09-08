import random
import unittest

from blackjack.gui import Application, InputError
from blackjack.counting_methods import ResearchModels, METHODS
from blackjack.solver import Hand


class FixedHole(random.Random):
    def __init__(self, hole):
        super().__init__(1)
        self.hole = hole

    def choice(self, population):
        return self.hole if self.hole in population else population[-1]


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = ResearchModels()

    def app(self, hole=10):
        return Application(FixedHole(hole), self.models)

    def test_baseline_matches_exact_solver_and_legality(self):
        app = self.app()
        for cards in ([5, 5], [8, 8], [1, 7], [2, 3, 4]):
            result = app.analyze(dict(cards=cards, upcard=6, method="baseline"))
            expected = app.solver.actions(Hand(tuple(cards)), 6)
            self.assertEqual({v['action']: v['ev'] for v in result['analysis']['actions']},
                             {a: float(v) for a, v in expected.items()})

    def test_hidden_hole_cannot_change_recommendations(self):
        for method in METHODS:
            p = dict(cards=[8, 8], upcard=6, method=method)
            first, second = self.app(9).analyze(p), self.app(10).analyze(p)
            self.assertEqual(first['analysis'], second['analysis'])
            self.assertEqual(first['count'], second['count'])
            self.assertEqual(first['dealer']['cards'], [6])
            self.assertIsNone(first['dealer']['total'])
            self.assertNotIn('hole', first)
            self.assertNotIn('deck', first)
            self.assertEqual(first['count']['visible'], 3)

    def test_method_switch_preserves_dealer_and_resolve_is_idempotent(self):
        app = self.app(6)
        p = dict(cards=[10, 7], upcard=1)
        first = app.analyze(p)
        token = first['dealer_id']
        changed = app.analyze(dict(p, dealer_id=token, method='baseline'))
        self.assertEqual(changed['dealer_id'], token)
        resolved = app.resolve_stand(dict(dealer_id=token))
        self.assertEqual(resolved['dealer']['cards'], [1, 6])
        self.assertEqual(resolved['settlement']['profit'], 0)
        self.assertEqual(resolved['count'], first['count'])
        self.assertEqual(resolved, app.resolve_stand(dict(dealer_id=token)))
        with self.assertRaises(InputError):
            app.analyze(dict(p, cards=[10, 8], dealer_id=token))

    def test_counting_can_change_action(self):
        history = [rank for rank, n in enumerate([0,6,10,6,10,9,10,12,8,8,31]) for _ in range(n)]
        result = self.app().analyze(dict(cards=[5,5], upcard=10, history=history))
        self.assertEqual(result['analysis']['baseline_actions'], ['hit'])
        self.assertEqual(result['analysis']['optimal_actions'], ['double'])

    def test_terminal_and_split_aces(self):
        app = self.app()
        self.assertEqual(app.analyze(dict(cards=['A',10], upcard=6))['settlement']['profit'], 1.5)
        self.assertEqual(app.analyze(dict(cards=[10,6,10], upcard=6))['status'], 'bust')
        self.assertEqual(app.analyze(dict(cards=[10,6], upcard='A'))['status'], 'dealer_blackjack')
        result = app.analyze(dict(cards=['A',6], history=['A'], origin='split-aces', upcard=6))
        self.assertEqual([v['action'] for v in result['analysis']['actions']], ['stand'])

    def test_invalid_and_impossible_cards(self):
        app = self.app()
        for p in (dict(cards=[8]), dict(cards=['X',8]), dict(cards=['A',10,2]),
                  dict(cards=[8,8], history=[2]*25), dict(cards=[8,8], origin='split')):
            with self.assertRaises(ValueError):
                app.analyze(p)


if __name__ == '__main__':
    unittest.main()
