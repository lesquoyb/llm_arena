import copy
import os
import unittest
from unittest import mock
from arena.api_providers import APIProvider, ProviderFailure, list_models, request_snapshot
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

    def test_gemini_native_tools_signatures_usage_and_seed(self):
        descriptor = model("gemini")
        descriptor["model"] = "models/gemini-fixture"
        descriptor["parameters"] = {"seed":42, "temperature":0}
        response = {"candidates":[{"content":{"role":"model", "parts":[
                    {"thoughtSignature":"signature-must-survive", "functionCall":{"id":"g1", "name":"list_files", "args":{}}}]},
                    "finishReason":"STOP"}], "usageMetadata":{"promptTokenCount":100,"candidatesTokenCount":10,
                    "thoughtsTokenCount":5,"cachedContentTokenCount":40}}
        sent = []
        def transport(url, payload, headers, timeout):
            sent.append((url,copy.deepcopy(payload),headers))
            return response, "request-fixture"
        history = [{"role":"user", "content":"unique-conversation"}]
        frozen = copy.deepcopy(history)
        with mock.patch.dict(os.environ, {"ARENA_TEST_KEY":"test-only"}):
            provider = APIProvider(descriptor, transport)
            answer = provider.respond(history,TOOLS,100)
        self.assertEqual(history,frozen)
        self.assertEqual(sent[0][0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-fixture:generateContent")
        self.assertEqual(sent[0][2]["x-goog-api-key"],"test-only")
        self.assertEqual(sent[0][1]["generationConfig"]["seed"],42)
        self.assertEqual(answer["usage"]["output_tokens"],15)
        self.assertEqual(answer["cost_usd"],"0.00026")
        payload = provider.payload([*history,answer,{"role":"tool", "name":"list_files", "provider_call_id":"g1", "result":{"files":[]}}],TOOLS,100)
        self.assertEqual(payload["contents"][1]["parts"][0]["thoughtSignature"],"signature-must-survive")
        self.assertEqual(payload["contents"][2]["parts"][0]["functionResponse"]["id"],"g1")
        self.assertEqual(payload["tools"][0]["functionDeclarations"][0]["parametersJsonSchema"],TOOLS[0]["input_schema"])
        snapshot = request_snapshot(descriptor,history,TOOLS,100)
        self.assertEqual(snapshot["body"],sent[0][1])
        self.assertNotIn("test-only",str(snapshot))
        self.assertEqual(snapshot["body_sha256"], request_snapshot(descriptor,frozen,TOOLS,100)["body_sha256"])

    def test_catalog_pages_filter_gemini_embeddings_and_keep_keys_out_of_urls(self):
        calls = []
        def transport(url, payload, headers, timeout):
            calls.append((url,payload,headers))
            if len(calls) == 1:
                return {"models":[{"name":"models/chat-a", "supportedGenerationMethods":["generateContent"]},
                                   {"name":"models/embed", "supportedGenerationMethods":["embedContent"]}],
                        "nextPageToken":"page-2"},None
            return {"models":[{"name":"models/chat-b", "supportedGenerationMethods":["generateContent"]}]},None
        result = list_models("gemini","secret-fixture",transport=transport)
        self.assertEqual([m["id"] for m in result["models"]],["models/chat-a","models/chat-b"])
        self.assertIn("pageToken=page-2",calls[1][0])
        self.assertTrue(all(payload is None for _,payload,_ in calls))
        self.assertTrue(all("secret-fixture" not in url for url,_,_ in calls))
        self.assertNotIn("secret-fixture",str(result))
        calls.clear()
        def anthropic(url,payload,headers,timeout):
            calls.append(url)
            return ({"data":[{"id":"claude-a"}],"has_more":True,"last_id":"claude-a"} if len(calls)==1
                    else {"data":[{"id":"claude-b"}],"has_more":False}),None
        self.assertEqual(len(list_models("anthropic","fixture",transport=anthropic)["models"]),2)
        self.assertIn("after_id=claude-a",calls[-1])
        seen = []
        def compatible(url,*args):
            seen.append(url)
            return {"data":[{"id":"custom-model"}]},None
        list_models("openai-compatible","fixture","https://example.test/v1/chat/completions",transport=compatible)
        self.assertEqual(seen,["https://example.test/v1/models"])

    def test_seeds_rejected_for_anthropic_and_invalid_types(self):
        config = read_json(ROOT / "configs/offline-demo.json")
        config["spending"] = {"allow_paid_calls":True,"max_total_usd":"1"}
        config["budget_per_session"].update(max_input_tokens=1000000,max_output_tokens=1000,max_cost_usd="1")
        for provider in ("openai","gemini","openai-compatible","anthropic"):
            descriptor = model(provider)
            if provider == "openai-compatible":
                descriptor["endpoint"] = "https://example.test/v1/chat/completions"
            config["models"] = [descriptor]
            descriptor["parameters"] = {"seed":42}
            if provider == "anthropic":
                with self.assertRaises(ArenaError): validate_config(config)
            else:
                validate_config(config)
                for invalid in (True,-1,"42",1.5):
                    descriptor["parameters"]["seed"] = invalid
                    with self.assertRaises(ArenaError): validate_config(config)

    def test_mock_receives_prompts_and_tools_and_journals_request_before_responding(self):
        config = read_json(ROOT / "configs/offline-demo.json")
        descriptor = config["models"][0]
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            try:
                state = initial_state("mock-r0",descriptor,config)
                prompt = copy.deepcopy(state["history"][0])
                response = provider_response("mock-r0",state,descriptor,config,journal)
                sent = response["sent_parameters"]
                self.assertEqual(sent["messages"],[prompt])
                self.assertEqual(sent["tools"],TOOLS)
                row = journal.db.execute("SELECT payload FROM events WHERE kind='model_intent'").fetchone()
                import json
                ref = json.loads(row[0])
                event = read_json(tmp/ref["artifact"])
                self.assertEqual(event["request"]["body"],sent)
            finally:
                journal.db.close()

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
