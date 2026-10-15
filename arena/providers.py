"""Deterministic fixtures, never API calls or measured model token usage."""
from __future__ import annotations

import copy
from .core import ROOT, ArenaError, digest, read_json

PROFILES = {"single-shot", "repair-and-submit", "invalid", "empty", "malformed", "timeout", "rate-limit", "budget"}


class MockProvider:
    def __init__(self, profile="single-shot"):
        self.profile = profile

    def payload(self, history, tools, output_limit):
        return {"profile": self.profile,
                "messages": [{k: copy.deepcopy(v) for k, v in item.items() if k != "sent_parameters"} for item in history],
                "tools": copy.deepcopy(tools), "max_output_tokens": output_limit}

    def respond(self, history, tools, output_limit):
        request = self.payload(history, tools, output_limit)
        history, profile = request["messages"], self.profile
        if profile not in PROFILES:
            raise ArenaError("Unknown mock profile")
        from .api_providers import ProviderFailure
        if profile in {"timeout", "rate-limit"}:
            raise ProviderFailure("Simulated " + profile, uncertain=profile == "timeout",
                                  retryable=profile == "rate-limit")
        marker = max((i for i, message in enumerate(history)
                      if message["role"] == "user" and message.get("generation", 0) > 0), default=-1)
        step = sum(message["role"] == "assistant" for message in history[marker + 1:])
        improving = marker >= 0
        condition = history[marker].get("condition") if improving else None
        source = (ROOT / "examples/strategies" /
                  ("rush" if profile == "repair-and-submit" or condition == "feedback" else "single-shot") /
                  "main.leek").read_text(encoding="utf-8")
        scripts = {
            "single-shot": [
                [("read_docs", {"path": "authoring.md"}), ("write_file", {"path": "main.leek", "content": source})],
                [("analyze", {})], [("submit", {})]],
            "repair-and-submit": [
                [("write_file", {"path": "main.leek", "content": "var = ???"})],
                [("analyze", {})],
                [("write_file", {"path": "main.leek", "content": source})],
                [("analyze", {}), ("test", {})],
                [("read_replay", {"test_id": "call-4-tool-1", "section": "team_metrics", "limit": 2000})],
                [("submit", {})]],
            "invalid": [[("write_file", {"path": "main.leek", "content": "var = ???"})], [("submit", {})]],
            "empty": [[]],
            "malformed": [[("write_file", {"path": "../other/main.leek", "content": source})], []],
        }
        sequence = scripts.get(profile, [[]])
        calls = sequence[step] if step < len(sequence) else []
        if improving:
            sequence = [[("write_file", {"path": "main.leek", "content": source})],
                        [("analyze", {})], [("submit", {})]]
            calls = sequence[step] if step < len(sequence) else []
        if profile == "budget":
            calls = [("write_file", {"path": "main.leek", "content": source})]
        scenario = history[0].get("scenario", {})
        if scenario.get("team_selection") and any(name == "write_file" for name, _ in calls):
            rules = scenario["team_selection"]
            # Fixtures exercise the same tool as native providers without API calls.
            members = [{"entrypoint": "main.leek",
                        "weapons": scenario["entity"].get("weapons", [])[:rules.get("max_weapons", 3)],
                        "chips": scenario["entity"].get("chips", [])[:rules.get("max_chips", 12)]}
                       for _ in range(scenario["team_size"])]
            for member in members:
                for kind in ("weapons", "chips"):
                    if "allowed_" + kind in rules:
                        member[kind] = [item for item in member[kind] if item in rules["allowed_" + kind]]
                        if not member[kind] and rules.get("max_" + kind, 3 if kind == "weapons" else 12):
                            from .equipment import catalog as equipment_catalog
                            catalog = equipment_catalog(ROOT / "docs/leekscript-v1", kind)
                            eligible = [item for item in rules["allowed_" + kind]
                                        if str(item) in catalog and catalog[str(item)].get("level", 1) <= scenario["entity"]["level"]]
                            member[kind] = eligible[:1]
            calls = [*calls, ("configure_team", {"members": members})]
        return {"role": "assistant", "provider": "mock", "simulated": True, "sent_parameters": request, "request_sha256": digest(request),
                "tool_calls": [{"name": name, "arguments": args} for name, args in calls],
                "stop_reason": "tool_calls" if calls else "end",
                "usage": {"input_tokens": None, "output_tokens": None, "raw": None},
                "cost_usd": "0", "cost_status": "simulation"}
