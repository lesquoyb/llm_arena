"""Deterministic fixtures, never API calls or measured model token usage."""
from __future__ import annotations

from .core import ROOT, ArenaError

PROFILES = {"single-shot", "repair-and-submit", "invalid", "empty", "malformed", "timeout", "rate-limit", "budget"}


class MockProvider:
    def respond(self, profile: str, history: list[dict]) -> dict:
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
                  "main.leek").read_text()
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
        return {"role": "assistant", "provider": "mock", "simulated": True,
                "tool_calls": [{"name": name, "arguments": args} for name, args in calls],
                "stop_reason": "tool_calls" if calls else "end",
                "usage": {"input_tokens": None, "output_tokens": None, "raw": None},
                "cost_usd": "0", "cost_status": "simulation"}
