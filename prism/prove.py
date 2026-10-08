"""Prove side: speak MCP stdio JSON-RPC to an axiom-mcp binary.

Binary resolution order:
  1. $PRISM_AXIOM_MCP (explicit path)
  2. ./axiom/target/debug/axiom-mcp (submodule build, debug first: faster CI)
  3. ./axiom/target/release/axiom-mcp
  4. ../axiom/target/{debug,release}/axiom-mcp (sibling checkout)
  5. ~/axiom/target/{debug,release}/axiom-mcp (dev phone)
  6. `axiom-mcp` on PATH

If no binary exists, prove()/prove_sat() return an honest
INCONCLUSIVE envelope (never a fabricated verdict). Stdlib only.
"""
import json
import os
import subprocess

_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CANDIDATES = [
    os.environ.get("PRISM_AXIOM_MCP", ""),
    os.path.join(_here, "axiom", "target", "debug", "axiom-mcp"),
    os.path.join(_here, "axiom", "target", "release", "axiom-mcp"),
    os.path.join(_here, "..", "axiom", "target", "debug", "axiom-mcp"),
    os.path.join(_here, "..", "axiom", "target", "release", "axiom-mcp"),
    os.path.expanduser("~/axiom/target/debug/axiom-mcp"),
    os.path.expanduser("~/axiom/target/release/axiom-mcp"),
    "axiom-mcp",
]


def binary_path():
    for cand in [c for c in _CANDIDATES if c]:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def available():
    return binary_path() is not None


def _run_session(requests, timeout=120):
    """Send a list of JSON-RPC request dicts, return list of raw response lines."""
    binpath = binary_path()
    if binpath is None:
        return None
    payload = "\n".join(json.dumps(r) for r in requests) + "\n"
    try:
        proc = subprocess.run([binpath], input=payload, capture_output=True,
                              text=True, timeout=timeout)
    except Exception as exc:
        return [f"__transport_error__: {exc}"]
    return [l for l in proc.stdout.splitlines() if l.strip()]


def _result_of(line):
    try:
        msg = json.loads(line)
    except Exception:
        return None
    return msg.get("result")


def _missing(op):
    return {"status": "inconclusive", "summary": f"axiom-mcp not built ({op} not attempted)",
            "steps": 0, "proof_present": False, "verified": False}


def prove(program, query_index=0, max_steps=1_000_000, timeout=120):
    """axiom_prove via MCP. Always returns a dict; inconclusive when no binary."""
    if binary_path() is None:
        return _missing("prove")
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "axiom_prove",
                    "arguments": {"program": program, "query_index": query_index,
                                  "max_steps": max_steps}}},
    ]
    lines = _run_session(reqs, timeout=timeout)
    if not lines or lines[0].startswith("__transport_error__"):
        return {"status": "inconclusive", "summary": lines[0] if lines else "no response",
                "steps": 0, "proof_present": False, "verified": False}
    res = _result_of(lines[-1]) or {}
    # MCP wraps tool output; axiom-mcp returns the verdict object directly.
    out = res.get("content", res) if isinstance(res, dict) else {}
    if isinstance(out, list) and out:
        out = out[0].get("text", "{}") if isinstance(out[0], dict) else "{}"
        try:
            out = json.loads(out)
        except Exception:
            out = {}
    if not isinstance(out, dict) or "status" not in out:
        out = {"status": "inconclusive", "summary": f"unparseable MCP reply: {lines[-1][:200]}",
               "steps": 0, "proof_present": False, "verified": False}
    out.setdefault("verified", bool(out.get("proof_present")) and out.get("status") in ("proved", "refuted", "impossible"))
    return out


def prove_sat(dimacs, max_steps=1_000_000, timeout=120):
    if binary_path() is None:
        return _missing("sat")
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "axiom_sat",
                    "arguments": {"dimacs": dimacs, "max_steps": max_steps}}},
    ]
    lines = _run_session(reqs, timeout=timeout)
    if not lines or lines[0].startswith("__transport_error__"):
        return {"status": "inconclusive", "summary": lines[0] if lines else "no response",
                "steps": 0, "proof_present": False, "verified": False}
    res = _result_of(lines[-1]) or {}
    out = res.get("content", res) if isinstance(res, dict) else {}
    if isinstance(out, list) and out:
        out = out[0].get("text", "{}") if isinstance(out[0], dict) else "{}"
        try:
            out = json.loads(out)
        except Exception:
            out = {}
    if not isinstance(out, dict) or "status" not in out:
        out = {"status": "inconclusive", "summary": f"unparseable MCP reply: {lines[-1][:200]}",
               "steps": 0, "proof_present": False, "verified": False}
    out.setdefault("verified", bool(out.get("proof_present")) and out.get("status") in ("proved", "refuted", "impossible"))
    return out


def version(timeout=30):
    if binary_path() is None:
        return {"name": "axiom-mcp", "present": False}
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "axiom_version", "arguments": {}}},
    ]
    lines = _run_session(reqs, timeout=timeout)
    if not lines:
        return {"name": "axiom-mcp", "present": False}
    res = _result_of(lines[-1]) or {}
    if isinstance(res, dict):
        res["present"] = True
        return res
    return {"name": "axiom-mcp", "present": False}
