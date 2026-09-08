import json
from pathlib import Path
from random import Random
import shutil
import subprocess
import tempfile
import unittest

from blackjack.counting import Approximation, BASE, BettingPolicy, Counter, Observation
from blackjack.counting_methods import (ACTIONS, METHODS, TAGS, ResearchModels, ResearchPolicy,
                                        features, hand_index, projected_gradient, state_index)
from blackjack.counting_research import compile_evaluator, paired_from_moments, process_outputs
from blackjack.evaluation import PairedStatistics, Statistics
from blackjack.finite import FULL_SHOE, RoundResult, Shoe, play_round


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = ResearchModels()

    def test_published_tags_and_projection(self):
        self.assertEqual(TAGS["halves"], (-1,.5,1,1,1.5,1,.5,0,-.5,-1))
        self.assertEqual(TAGS["hiopt2-ace"], (0,1,1,2,2,1,1,0,0,-2))
        self.assertEqual(TAGS["omega2-ace"], (0,1,1,2,2,2,1,0,-1,-2))
        for name in METHODS[2:]:
            for row in features(name):
                self.assertAlmostEqual(sum(x*p for x,p in zip(row,BASE[1:])), 0, places=14)
        for name in ("hiopt2-ace", "omega2-ace"):
            a,b=features(name)
            self.assertAlmostEqual(sum(x*y*p for x,y,p in zip(a,b,BASE[1:])),0,places=14)
        # KO must remove its expected +4 per full-deck drift before inference.
        ko=features("ko-centered")[0]
        self.assertAlmostEqual(ko[1], 1-1/13)
        self.assertAlmostEqual(ko[0], -1-1/13)
        g=[.2,-.1,.3,.7,.5,-.2,.4,-.3,.8,-.9]
        counts=(0, 2,3,1,2,0,1,4,0,2,8)
        obs=Observation(counts,26)
        f=self.models.observation_features("composition",obs)
        n=sum(counts)
        for c in range(10):
            self.assertAlmostEqual(f[c], (312*BASE[c+1]-counts[c+1])/(312-n)-BASE[c+1])
        self.assertEqual(projected_gradient("composition",g),g)

    def test_gradients_against_independent_direction(self):
        # A new direction, not one of the coordinate directions used to build tables.
        direction=(0., -.3,.2,.1,-.1,.2,.15,-.1,.05,.1,-.3)
        self.assertAlmostEqual(sum(direction),0)
        h=1e-6
        b=self.models.legacy.baseline
        plus=Approximation(tuple(p+h*d for p,d in zip(BASE,direction)),b)
        minus=Approximation(tuple(p-h*d for p,d in zip(BASE,direction)),b)
        expected=(plus.edge-minus.edge)/(2*h)
        actual=sum(g*d for g,d in zip(self.models.edge_gradient,direction[1:]))
        self.assertAlmostEqual(actual,expected,places=8)
        for key in ((10,16,False,0),(6,11,False,1),(1,16,False,2),(6,8,False,2)):
            i=state_index(*key)
            for name in plus.state_action_values[key]:
                expected=(plus.state_action_values[key][name]-minus.state_action_values[key][name])/(2*h)
                actual=sum(g*d for g,d in zip(self.models.gradients[i][ACTIONS.index(name)],direction[1:]))
                self.assertAlmostEqual(actual,expected,places=8)

    def test_ace_side_count_adds_information(self):
        # Ace and eight are both zero in Hi-Opt II, but have different side counts.
        a=Observation((0,1,0,0,0,0,0,0,0,0,0),1)
        b=Observation((0,0,0,0,0,0,0,0,1,0,0),1)
        for name in ("hiopt2-ace","omega2-ace"):
            fa=self.models.observation_features(name,a)
            fb=self.models.observation_features(name,b)
            self.assertEqual(fa[0],fb[0])
            self.assertNotEqual(fa[1],fb[1])
            self.assertNotEqual(self.models.estimate(name,a),self.models.estimate(name,b))

    def test_reference_adapters_match_legacy(self):
        from blackjack.counting import Counting
        rng=Random(214)
        for _ in range(300):
            counter=Counter()
            for _ in range(rng.randrange(60)):
                counter.observe(rng.choice(FULL_SHOE))
            obs=counter.snapshot()
            c,d,up=[rng.randrange(1,11) for _ in range(3)]
            if {c,d}=={1,10}:
                continue
            for origin in ("original", "split-aces" if c==1 else "split"):
                if origin=="split-aces":
                    continue
                for name, legacy in (("baseline",self.models.legacy.baseline),("hilo",Counting(self.models.legacy))):
                    self.assertEqual(self.models.choose(name,(c,d),up,origin,obs),legacy.choose((c,d),up,origin,obs))

    @unittest.skipUnless(shutil.which("g++"), "Optional accelerator requires g++")
    def test_accelerator_matches_python_on_complete_shoes(self):
        rng=Random(77123)  # Validation only; independent of final evaluation seed.
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);model=tmp/"model.bin";binary=tmp/"evaluate";decks=tmp/"decks.txt"
            self.models.export(model)
            compile_evaluator(binary)
            cards=[]
            for _ in range(150):
                deck=list(FULL_SHOE);rng.shuffle(deck);cards.append(deck)
            decks.write_text(str(len(cards))+"\n"+"\n".join(str(len(d))+" "+" ".join(map(str,d)) for d in cards))
            for threshold in (26,52,104,156):
                run=subprocess.run([str(binary),str(model),"trace",str(decks),str(threshold)],check=True,capture_output=True,text=True)
                expected=[]
                for shoe_index,deck in enumerate(cards):
                    for m,name in enumerate(METHODS):
                        shoe=Shoe(deck);counter=Counter();policy=ResearchPolicy(self.models,name);round_index=0
                        while shoe.dealt<threshold:
                            r=play_round(shoe,counter,policy,BettingPolicy(),lambda obs:self.models.estimate(name,obs))
                            expected.append([shoe_index,m,round_index,r.unit_profit,r.estimated_edge,r.cards_dealt,r.visible_cards,
                                             1,BettingPolicy(bounded=True).choose(r.estimated_edge),4 if r.estimated_edge>0 else 1])
                            round_index+=1
                actual=[list(map(float,line.split())) for line in run.stdout.splitlines()]
                self.assertEqual(len(actual),len(expected))
                for x,y in zip(actual,expected):
                    for a,b in zip(x,y):
                        self.assertAlmostEqual(a,b,places=12)
            # Repeat a small independent compiled run; all sums except timing match.
            command=[str(binary),str(model),"20","413","26"]
            a,b=[json.loads(subprocess.check_output(command,text=True)) for _ in range(2)]
            self.assertEqual(a["stats"],b["stats"])
            self.assertEqual(a["pairs"],b["pairs"])
            report=process_outputs({"26":a},{})
            self.assertEqual(len(report["results"]),21)
            for r in report["results"]:
                self.assertGreaterEqual(r["observed_bet_range"][0],1)
                self.assertLessEqual(r["observed_bet_range"][1],4)

    def test_cross_moment_uncertainty_matches_explicit_pairs(self):
        left,right=Statistics(),Statistics();paired=PairedStatistics();cross=[0.]*9
        for aa,bb in (([1,-1],[2]),([1],[1,-2]),([-1,1,1],[-1,-1])):
            a=[RoundResult(v,1,0,4,4,0) for v in aa]
            b=[RoundResult(v,2,0,4,4,0) for v in bb]
            left.add_cycle(a);right.add_cycle(b)
            x=(sum(v.profit for v in a),len(a),sum(v.initial_bet for v in a))
            y=(sum(v.profit for v in b),len(b),sum(v.initial_bet for v in b))
            paired.cycles.append((x,y))
            for i in range(3):
                for j in range(3):
                    cross[3*i+j]+=x[i]*y[j]
        for denominator in (1,2):
            a=paired_from_moments(left,right,cross,denominator,3.5)
            b=paired.report(left.report(),right.report(),denominator)
            self.assertAlmostEqual(a["difference"],b["difference"])
            self.assertAlmostEqual(a["se"],b["se"])
            self.assertLess(a["family_ci95"][0],a["ci95"][0])


if __name__=="__main__":
    unittest.main()
