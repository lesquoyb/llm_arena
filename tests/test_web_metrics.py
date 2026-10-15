import unittest
from arena_web.metrics import combat_stats, competition_stats


def outcome(instrumented=False):
    data = {"fight": {"leeks": [{"id":0,"team":1,"name":"A"},{"id":1,"team":2,"name":"B"}],
            "ops":{"0":500,"1":20},
            "actions":[[0],[7,0],[10,0,3,[1,2,3]],[16,1,1],[101,1,20,2],[8,0,8,2],[6,2],[7,1],[103,1,5],[8,1,9,5]]}}
    if instrumented:
        data["operations_limit_per_turn"] = 20_000_000
        data["turn_metrics"] = [dict(turn=1,entity=0,side=0,operations=500,ai_turns=1,damage_dealt=20,damage_taken=0,erosion_dealt=2,erosion_taken=0,healing_given=0,healing_received=0,errors=0,operation_limit_hits=0,stack_overflows=0),
                                dict(turn=1,entity=1,side=1,operations=0,ai_turns=0,damage_dealt=0,damage_taken=20,erosion_dealt=0,erosion_taken=2,healing_given=0,healing_received=0,errors=0,operation_limit_hits=0,stack_overflows=0),
                                dict(turn=2,entity=1,side=1,operations=20,ai_turns=1,damage_dealt=0,damage_taken=0,erosion_dealt=0,erosion_taken=0,healing_given=5,healing_received=5,errors=0,operation_limit_hits=0,stack_overflows=0)]
    return data


class CombatMetricsTests(unittest.TestCase):
    def test_archived_totals_do_not_invent_turn_ops_or_damage_source(self):
        stats = combat_stats(outcome())
        a,b = stats["entities"]
        self.assertEqual((a["operations"],a["actions"],a["cells_moved"]),(500,2,3))
        self.assertEqual((b["damage_taken"],b["healing_received"],b["erosion_taken"]),(20,5,2))
        self.assertIsNone(a["damage_dealt"])
        self.assertTrue(all(r["operations"] is None for r in stats["turns"]))

    def test_measured_damage_is_attributed_to_attacker_not_current_actor(self):
        data = outcome(True)
        data["turn_metrics"][-1]["damage_dealt"] = 7
        stats = combat_stats(data)
        self.assertEqual(stats["entities"][0]["damage_dealt"],20)
        self.assertEqual(stats["entities"][1]["damage_dealt"],7)
        self.assertEqual(sum(r["operations"] for r in stats["turns"]),520)
        self.assertEqual(stats["operations_limit_per_turn"],20_000_000)

    def test_matrix_orients_results_and_keeps_failures_mirrors_stages_separate(self):
        matches = [dict(stage="G0",path="a",sides=["A","B"],result=dict(status="completed",winner_side=0)),
                   dict(stage="G0",path="b",sides=["B","A"],result=dict(status="completed",winner_side=-1)),
                   dict(stage="G0",path="c",sides=["B","A"],result=dict(status="timeout")),
                   dict(stage="G0",path="d",sides=["A","A"],mirror=True,result=dict(status="completed",winner_side=0)),
                   dict(stage="G1",path="e",sides=["A","B"],result=dict(status="completed",winner_side=1))]
        groups = competition_stats(matches, lambda _:outcome(True))["stages"]
        self.assertEqual(groups[0]["matrix"]["A"]["B"],dict(wins=1,draws=1,losses=0,failures=1))
        self.assertEqual(groups[0]["matrix"]["B"]["A"]["losses"],1)
        self.assertNotIn("A",groups[0]["matrix"]["A"])
        self.assertEqual(groups[1]["matrix"]["B"]["A"]["wins"],1)
