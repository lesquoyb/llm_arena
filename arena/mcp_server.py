"""Pinned MCP SDK transport over the same journaled, budgeted service."""
from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from .core import ArenaError, read_json
from .engine import Engine
from .experiment import Journal, experiment_lock, execute_tool, verify_workspace, _finish
from .preparation import Preparation
from .feedback import access_for, available_tools


def serve(out: Path, sid: str):
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    out = out.resolve()
    config = read_json(out / "experiment.json")["config"]
    with experiment_lock(out):
        journal = Journal(out)
        try:
            journal.verify()
            state = journal.state(sid)
            if state is None or state["status"] != "running" or state.get("pending"):
                raise ArenaError("MCP requires an initialized, open session without a pending provider response")
            from .submitted_versions import OwnSubmissions
            tools = Preparation(out / "sessions" / sid, out / "corpus", Engine(), config["scenario"], feedback=access_for(out, state),
                                allowed_tools=state.get('calibration',{}).get('tools'), versions=OwnSubmissions(out,state))
            verify_workspace(state, tools)
            server = Server("llm-arena-preparation")
            started, previous = time.monotonic(), state["wall_seconds"]

            @server.list_tools()
            async def list_tools():
                return [types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"]) for t in available_tools(state)]

            @server.call_tool(validate_input=False)
            async def call_tool(name, arguments):
                state["wall_seconds"] = previous + time.monotonic() - started
                try:
                    if state["wall_seconds"] >= config["budget_per_session"].get("max_wall_seconds", float("inf")):
                        _finish(sid, state, tools, journal, "budget_exhausted")
                        raise ArenaError("Wall budget exhausted")
                    identifier = f"call-0-tool-{state['steps']}"
                    result = execute_tool(sid, state, tools, journal, {"name": name, "arguments": arguments},
                                          identifier, config["budget_per_session"])
                except ArenaError as error:
                    if str(error) == "Tool budget exhausted":
                        _finish(sid, state, tools, journal, "budget_exhausted")
                    result = {"error": str(error)}
                from .model_content import compact, visible
                return [types.TextContent(type="text", text=compact(visible(result)))]

            async def run_server():
                async with stdio_server() as (reader, writer):
                    await server.run(reader, writer, server.create_initialization_options())
            asyncio.run(run_server())
        finally:
            journal.db.close()
