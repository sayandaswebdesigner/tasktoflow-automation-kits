#!/usr/bin/env python3
"""Live runnable demo comparing the 3 Levels of AI Systems:
Level 1: Raw LLM Prompt (unvalidated)
Level 2: Deterministic Workflow Router (fast, cheap, predictable)
Level 3: Autonomous AI Agent with HITL Guardrails
"""
from __future__ import annotations
import json
import time


def level_1_chatbot(user_text: str) -> dict:
    # Single-shot prompt: no schema guarantee, fails silently on malformed payloads
    if "refund" in user_text.lower():
        return {"level": 1, "action": "guessed_reply", "safe_execution": False, "cost_ms": 420}
    return {"level": 1, "action": "text_only", "safe_execution": True, "cost_ms": 380}


def level_2_workflow(event: dict) -> dict:
    # Fixed deterministic branches: ideal for repeatable API routing
    t0 = time.perf_counter()
    routes = {"invoice": "sync_erp", "csv": "clean_pandas", "ticket": "notify_slack"}
    target = routes.get(event.get("type"), "dead_letter_queue")
    ms = round((time.perf_counter() - t0) * 1000, 2)
    return {"level": 2, "route": target, "deterministic": True, "cost_ms": ms}


def level_3_guarded_agent(goal: str, amount_usd: float, max_steps: int = 3) -> dict:
    # Bounded tool-calling loop with policy gate before mutating state
    trace = []
    for step in range(1, max_steps + 1):
        trace.append(f"step_{step}:plan_check")
        if "delete" in goal.lower() or "drop table" in goal.lower():
            return {"level": 3, "status": "BLOCKED_BY_GUARD", "steps": len(trace), "db_writes": 0}
        if amount_usd > 500:
            return {"level": 3, "status": "PAUSED_FOR_HUMAN", "steps": len(trace), "amount_usd": amount_usd}
    return {"level": 3, "status": "AUTONOMOUS_COMPLETE", "steps": len(trace), "db_writes": 1}


if __name__ == "__main__":
    print("[LEVEL 1 PROMPT] ", json.dumps(level_1_chatbot("issue $900 refund now")))
    print("[LEVEL 2 WORKFLOW] ", json.dumps(level_2_workflow({"type": "csv", "rows": 10000})))
    print("[LEVEL 3 AGENT SAFE] ", json.dumps(level_3_guarded_agent("reconcile invoice", 120.0)))
    print("[LEVEL 3 AGENT GUARD] ", json.dumps(level_3_guarded_agent("drop table users", 0.0)))
