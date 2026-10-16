import asyncio
import importlib.util
import json
import os
import sys
import unittest
from datetime import timedelta
from arena.core import ROOT, read_json, scratch_directory
from arena.experiment import run


@unittest.skipUnless(importlib.util.find_spec("mcp") and (ROOT / ".arena/engine.json").exists(),
                     "Install pinned MCP SDK and build engine")
class MCPIntegrationTests(unittest.TestCase):
    def test_stdio_handshake_tools_budget_and_submission(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def client(out):
            parameters = StdioServerParameters(command=sys.executable,
                args=["-m", "arena", "mcp", "serve", "--experiment", str(out), "--session", "mock-single-r0"],
                cwd=str(ROOT))
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=120)) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    self.assertEqual(len(listing.tools), 11)
                    self.assertIn("configure_team", {tool.name for tool in listing.tools})
                    forbidden = await session.call_tool("list_past_fights", {})
                    self.assertIn("forbidden", json.loads(forbidden.content[0].text)["error"])
                    result = await session.call_tool("write_file", {"path": "main.leek", "content": "var a = 1"})
                    self.assertIn("sha256", json.loads(result.content[0].text))
                    result = await session.call_tool("read_file", {"path": "main.leek"})
                    self.assertEqual(json.loads(result.content[0].text)["content"], "var a = 1")
                    result = await session.call_tool("read_file", {})
                    self.assertIn("error", json.loads(result.content[0].text))
                    result = await session.call_tool("read_file", {"path": "../mock-repair-r0/main.leek"})
                    self.assertIn("error", json.loads(result.content[0].text))
                    result = await session.call_tool("analyze", {})
                    self.assertEqual(json.loads(result.content[0].text)["status"], "valid")
                    result = await session.call_tool("submit", {})
                    self.assertIn("submission", json.loads(result.content[0].text))
                    result = await session.call_tool("write_file", {"path": "main.leek", "content": "var b = 2"})
                    self.assertIn("error", json.loads(result.content[0].text))
        with scratch_directory() as tmp:
            config = read_json(ROOT / "configs/offline-demo.json")
            run(config, tmp / "experiment", prepare_only=True)
            asyncio.run(client(tmp / "experiment"))
