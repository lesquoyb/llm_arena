import unittest
from arena.analysis import analyze_evolution
from arena.core import scratch_directory


class AnalysisTests(unittest.TestCase):
    def test_panel_membership_is_not_inferred_from_model_name_and_unknown_cost_is_excluded(self):
        initial = [{"id": "fixed-user-r0", "model": "fixed-user", "replicate": 0}]
        config = {"models": [{"id": "fixed-user", "provider": "openai"}], "replicates": 1}
        state = {"model": "fixed-user", "replicate": 0, "status": "needs_reconciliation",
                 "cost_spent": "0", "money_reserved": "1", "submission": {}}
        record = {"session": "fixed-user-r0", "opponent": "fixed-user-r0", "side": 0,
                  "result": {"status": "completed", "winner_side": -1,
                             "team_metrics": {"0": {"operations": 0, "errors": 0, "operation_limit_hits": 0}}}}
        with scratch_directory() as tmp:
            result = analyze_evolution(config, tmp, {"fixed-user-r0": state}, initial, [], {"a": record}, {}, None)
        rows = {row["panel"]: row for row in result["rows"]}
        self.assertEqual(rows["g0"]["completed"], 1)
        self.assertEqual(rows["controls"]["completed"], 0)
        self.assertIsNone(result["cost_usd"])
        self.assertEqual(result["pareto"], [])
        self.assertTrue(result["incomplete"])
        self.assertIsNone(result["interval_95_exploratory"])
