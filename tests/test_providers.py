import copy
import os
import unittest
from unittest import mock
from arena.api_providers import APIProvider, ProviderFailure
from arena.core import ROOT, ArenaError, read_json, scratch_directory
from arena.experiment import Journal, initial_state, provider_response, run_session, validate_config
from arena.tool_schemas import TOOLS
from arena.usage import cost, normalize


def model(provider="openai"):
    return {"id": "fixture", "provider": provider, "model": "fixture-exact-model",
            "api_key_env": "ARENA_TEST_KEY", "max_input_tokens_per_call": 50000,
            "max_output_tokens": 100, "parameters": {}, "max_retries": 1,
            "pricing": {"date": "2026-10-14", "currency": "USD",
                        "input_per_million": "2", "output_per_million": "8",
                        "cached_input_per_million": "0.5", "cache_creation_per_million": "3"}}


class ProviderContractTests(unittest.TestCase):
    def test_receipt_and_usage_are_atomic_when_interrupted_before_tool_execution(self):
        config = read_json(ROOT / "configs/offline-demo.json")
        config["models"] = [model()]
        config["spending"] = {"allow_paid_calls": True, "max_total_usd": "1"}
        config["budget_per_session"].update(max_input_tokens=1000000, max_output_tokens=1000, max_cost_usd="1")
        response = {"role": "assistant", "native": {"role": "assistant", "content": "done"},
                    "tool_calls": [], "usage": {"input_tokens": 1, "output_tokens": 1},
                    "cost_usd": "0.00001", "request_id": "fixture"}
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            original = journal.save
            def stop(sid, state, kind, payload=None):
                original(sid, state, kind, payload)
                if kind == "model_response":
                    raise KeyboardInterrupt
            try:
                state = initial_state("fixture-r0", config["models"][0], config)
                with mock.patch("arena.experiment.APIProvider") as provider, mock.patch.object(journal, "save", side_effect=stop):
                    provider.return_value.respond.return_value = response
                    with self.assertRaises(KeyboardInterrupt):
                        provider_response("fixture-r0", state, config["models"][0], config, journal)
                saved = journal.state("fixture-r0")
                self.assertFalse(saved["in_flight"])
                self.assertEqual(saved["money_reserved"], "0")
                self.assertEqual(saved["cost_spent"], "0.00001")
                self.assertEqual(saved["pending"]["request_id"], "fixture")
                with mock.patch("arena.experiment.APIProvider") as provider:
                    run_session("fixture-r0", config["models"][0], config, tmp, journal, None)
                    provider.assert_not_called()
            finally:
                journal.db.close()
    def test_openai_native_history_usage_and_reasoning_not_counted_twice(self):
        response = {"choices": [{"message": {"role": "assistant", "content": None,
                     "tool_calls": [{"id": "t1", "type": "function", "function": {
                         "name": "write_file", "arguments": '{"path":"main.leek","content":"var a = 1"}'}}]},
                     "finish_reason": "tool_calls"}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20,
                              "prompt_tokens_details": {"cached_tokens": 50},
                              "completion_tokens_details": {"reasoning_tokens": 15}}}
        captured = []
        def transport(url, payload, headers, timeout):
            captured.append(payload)
            return response, "request-fixture"
        with mock.patch.dict(os.environ, {"ARENA_TEST_KEY": "test-only"}):
            provider = APIProvider(model(), transport)
            answer = provider.respond([{"role": "user", "content": "fixture"}], TOOLS, 100)
        self.assertEqual(answer["cost_usd"], "0.000285")
        self.assertEqual(answer["usage"]["reasoning_tokens"], 15)
        history = [{"role": "user", "content": "fixture"}, answer,
                   {"role": "tool", "provider_call_id": "t1", "result": {"ok": True}}]
        frozen = copy.deepcopy(history)
        payload = provider.payload(history, TOOLS, 100)
        self.assertEqual(payload["messages"][-1]["tool_call_id"], "t1")
        self.assertNotIn("temperature", captured[0])
        self.assertEqual(history, frozen)

    def test_anthropic_cache_parts_and_native_blocks_are_preserved(self):
        response = {"content": [{"type": "thinking", "thinking": "fixture", "signature": "sig"},
                    {"type": "tool_use", "id": "t1", "name": "list_files", "input": {}}],
                    "stop_reason": "tool_use",
                    "usage": {"input_tokens": 10, "cache_read_input_tokens": 40,
                              "cache_creation_input_tokens": 20, "output_tokens": 5}}
        with mock.patch.dict(os.environ, {"ARENA_TEST_KEY": "test-only"}):
            provider = APIProvider(model("anthropic"), lambda *args: (response, "req"))
            answer = provider.respond([{"role": "user", "content": "fixture"}], TOOLS, 100)
        self.assertEqual(answer["usage"]["input_tokens"], 70)
        self.assertEqual(answer["cost_usd"], "0.00014")
        payload = provider.payload([{"role": "user", "content": "fixture"}, answer,
                                    {"role": "tool", "provider_call_id": "t1", "result": {"files": []}}], TOOLS, 100)
        self.assertEqual(payload["messages"][1]["content"][0]["signature"], "sig")
        self.assertEqual(payload["messages"][2]["content"][0]["tool_use_id"], "t1")

    def test_unknown_usage_and_prices_remain_unknown(self):
        usage = normalize("openai", {})
        self.assertIsNone(usage["input_tokens"])
        self.assertIsNone(cost(usage, model()["pricing"]))
        self.assertIsNone(cost({"input_tokens": 1, "output_tokens": 1}, None))
        self.assertIsNone(cost(normalize("openai", {"prompt_tokens": 10, "completion_tokens": 5}), model()["pricing"]))
        self.assertIsNone(normalize("anthropic", {"input_tokens": 10, "output_tokens": 5})["input_tokens"])

    def test_rate_limit_retry_bounded_timeout_never_retried(self):
        attempts = []
        def transport(*args):
            attempts.append(1)
            raise ProviderFailure("429", retryable=True)
        with mock.patch.dict(os.environ, {"ARENA_TEST_KEY": "test-only"}), mock.patch("arena.api_providers.time.sleep"):
            with self.assertRaises(ProviderFailure):
                APIProvider(model(), transport).respond([], TOOLS, 1)
        self.assertEqual(len(attempts), 2)
        attempts.clear()
        def unknown(*args):
            attempts.append(1)
            raise ProviderFailure("timeout", uncertain=True)
        with mock.patch.dict(os.environ, {"ARENA_TEST_KEY": "test-only"}):
            with self.assertRaises(ProviderFailure):
                APIProvider(model(), unknown).respond([], TOOLS, 1)
        self.assertEqual(len(attempts), 1)

    def test_global_ceiling_and_unknown_remote_state_preserve_reservation(self):
        config = read_json(ROOT / "configs/offline-demo.json")
        config["models"] = [model()]
        config["spending"] = {"allow_paid_calls": True, "max_total_usd": "0.2"}
        config["budget_per_session"].update(max_input_tokens=1000000, max_output_tokens=1000, max_cost_usd="1")
        validate_config(config)
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            try:
                state = initial_state("fixture-r0", config["models"][0], config)
                journal.save("other", {"money_reserved": "0.2"}, "fixture")
                with mock.patch("arena.experiment.APIProvider") as provider:
                    self.assertIsNone(provider_response("fixture-r0", state, config["models"][0], config, journal))
                    provider.assert_not_called()
                self.assertEqual(state["status"], "budget_exhausted")
                config["spending"]["max_total_usd"] = "1"
                state = initial_state("fixture-r0", config["models"][0], config)
                with mock.patch("arena.experiment.APIProvider") as provider:
                    provider.return_value.respond.side_effect = ProviderFailure("timeout", uncertain=True)
                    self.assertIsNone(provider_response("fixture-r0", state, config["models"][0], config, journal))
                self.assertEqual(state["status"], "needs_reconciliation")
                self.assertNotEqual(state["money_reserved"], "0")
                state["status"] = "running"
                with mock.patch("arena.experiment.APIProvider") as provider:
                    self.assertIsNone(provider_response("fixture-r0", state, config["models"][0], config, journal))
                    provider.assert_not_called()
            finally:
                journal.db.close()
