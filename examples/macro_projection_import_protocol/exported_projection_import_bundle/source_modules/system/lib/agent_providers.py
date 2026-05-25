"""
[PURPOSE]
- Teleology: Provide one ask_ai-compatible dispatch surface across bridge, Claude Code CLI, Codex CLI, NVIDIA NIM, and guarded OpenRouter so observe-group orchestration can swap providers without changing its control flow.
- Mechanism: Wraps subprocess-backed Claude/Codex executions behind the bridge.ask_ai signature and resolves provider names to the correct callable at runtime.

[INTERFACE]
- Exports: ask_claude, ask_codex, resolve_provider_callable.
- Reads: Caller-provided provider config, local CLI binaries, and system.core.bridge for bridge dispatches.
- Writes: None directly; subprocess providers may write their own external artifacts.

[FLOW]
- Orders: resolve_provider_callable() maps a provider token to one callable -> ask_claude() and ask_codex() build argv/config -> _run_subprocess() enforces timeout and cancellation.
- When-needed: Open when observe dispatches or pipeline compilers need the exact provider-to-callable mapping for bridge, Claude Code CLI, or Codex CLI.
- When-needed: Open when tracing which surface resolves or wraps `ask_ai` for a given provider token (bridge, claude, codex).
- Escalates-to: system/core/bridge.py::ask_ai; system/lib/bridge_routes.py::merge_bridge_config_with_route
- Navigation-group: kernel_lib

[DEPENDENCIES]
- subprocess + threading + time: Run CLI providers with timeout and cancellation semantics.
- system.core.bridge: Supplies the CDP-backed bridge ask_ai callable for bridge/chatgpt/gemini providers.

[CONSTRAINTS]
- Guarantee: Public provider helpers share the bridge.ask_ai signature `(prompt, config, cancel) -> str`.
- Non-goal: This module does not score bridge payloads or validate provider capability matrices.
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from system.lib import nvidia_nim, openrouter_free_runtime


_DEFAULT_CLAUDE_TOOLS = ("Read", "Glob", "Grep", "LS")


def _run_subprocess(
    cmd: list[str],
    *,
    timeout_s: int = 600,
    cwd: Optional[str] = None,
    cancel: Optional[threading.Event] = None,
) -> str:
    """Run a subprocess, respecting cancel event and timeout."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
    )
    try:
        deadline = time.monotonic() + timeout_s
        while proc.poll() is None:
            if cancel and cancel.is_set():
                proc.terminate()
                proc.wait(timeout=5)
                raise InterruptedError("Cancelled by stop event")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.terminate()
                proc.wait(timeout=5)
                raise TimeoutError(f"Provider timed out after {timeout_s}s")
            time.sleep(0.5)
        stdout = proc.stdout.read() if proc.stdout else ""
        stderr = proc.stderr.read() if proc.stderr else ""
        if proc.returncode != 0:
            raise RuntimeError(
                f"Provider exited with code {proc.returncode}: {stderr.strip()}"
            )
        return stdout.strip()
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)


def _normalize_claude_tools(value: Any) -> list[str]:
    """Normalize Claude CLI tool configuration into a flat argv list."""
    if value is None:
        return list(_DEFAULT_CLAUDE_TOOLS)
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return []
        if token.lower() == "default":
            return ["default"]
        if "," in token:
            return [part.strip() for part in token.split(",") if part.strip()]
        return [part.strip() for part in token.split() if part.strip()]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            token = str(item or "").strip()
            if token:
                out.append(token)
        return out
    token = str(value or "").strip()
    return [token] if token else []


def ask_claude(
    prompt: str,
    config: Optional[Dict[str, Any]] = None,
    cancel: Optional[threading.Event] = None,
) -> str:
    """
    [ACTION]
    - Teleology: Dispatch one prompt through the local Claude Code CLI worker path using the shared ask_ai-compatible signature.
    - Mechanism: Reads Claude-specific config keys, normalizes tool allowlists, builds a `claude -p` command, and delegates timeout/cancel handling to _run_subprocess().
    - Guarantee: Returns the stripped stdout text from Claude when the subprocess exits successfully.
    - Fails: Raises InterruptedError on cancellation, TimeoutError on timeout, and RuntimeError when the CLI exits non-zero.
    - When-needed: Open when a group is assigned to the Claude CLI path and the caller needs the exact argv, tool-default, or timeout behavior.
    - Escalates-to: system/lib/agent_providers.py::resolve_provider_callable
    """
    cfg = config or {}
    budget = cfg.get("max_budget_usd")
    timeout_s = cfg.get("timeout_s", 600)
    model = cfg.get("model", "sonnet")
    permission_mode = cfg.get("permission_mode", "bypassPermissions")
    tools = _normalize_claude_tools(cfg.get("tools"))
    cwd = cfg.get("cwd")

    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "text",
        "--permission-mode", permission_mode,
        "--model", model,
    ]
    if tools:
        cmd.extend(["--tools", ",".join(tools)])
    else:
        cmd.extend(["--tools", ""])
    if budget is not None:
        cmd.extend(["--max-budget-usd", str(budget)])

    return _run_subprocess(cmd, timeout_s=timeout_s, cwd=cwd, cancel=cancel)


def ask_codex(
    prompt: str,
    config: Optional[Dict[str, Any]] = None,
    cancel: Optional[threading.Event] = None,
) -> str:
    """
    [ACTION]
    - Teleology: Dispatch one prompt through the local Codex CLI path using the same callable contract as bridge.ask_ai.
    - Mechanism: Reads Codex-specific config keys, builds a `codex exec` command with optional writable-root, and runs it through _run_subprocess().
    - Guarantee: Returns the stripped stdout text from Codex when the subprocess exits successfully.
    - Fails: Raises InterruptedError on cancellation, TimeoutError on timeout, and RuntimeError when the CLI exits non-zero.
    - When-needed: Open when a group is assigned to Codex CLI and the caller needs the concrete exec path or config-to-argv mapping.
    - Escalates-to: system/lib/agent_providers.py::resolve_provider_callable
    """
    cfg = config or {}
    timeout_s = cfg.get("timeout_s", 600)
    model = cfg.get("model", "o3")
    writable_root = cfg.get("writable_root")
    cwd = cfg.get("cwd")

    cmd = [
        "codex", "exec",
        "--config", f"model={model}",
    ]
    if writable_root:
        cmd.extend(["--writable-root", writable_root])
    cmd.append(prompt)

    return _run_subprocess(cmd, timeout_s=timeout_s, cwd=cwd, cancel=cancel)


def ask_nvidia(
    prompt: str,
    config: Optional[Dict[str, Any]] = None,
    cancel: Optional[threading.Event] = None,
) -> str:
    """
    [ACTION]
    - Teleology: Dispatch one prompt through NVIDIA's hosted NIM chat endpoint using the shared ask_ai-compatible callable contract.
    - Mechanism: Reads NVIDIA config/env defaults through system.lib.nvidia_nim and returns the normalized assistant text.
    - Guarantee: Returns plain assistant text for successful hosted NIM chat calls.
    - Fails: Raises InterruptedError on cancellation and RuntimeError on missing auth, transport failure, or malformed provider responses.
    - When-needed: Open when observe or local routing code wants a cheap hosted provider path without invoking the bridge or local CLIs.
    - Escalates-to: system/lib/nvidia_nim.py::chat_completion; system/lib/agent_providers.py::resolve_provider_callable
    """
    return nvidia_nim.chat_completion(prompt, config or {}, cancel)


def ask_openrouter(
    prompt: str,
    config: Optional[Dict[str, Any]] = None,
    cancel: Optional[threading.Event] = None,
) -> str:
    """
    [ACTION]
    - Teleology: Dispatch one prompt through OpenRouter's OpenAI-compatible chat endpoint using the shared ask_ai-compatible callable contract.
    - Mechanism: Reads OpenRouter config/env defaults through system.lib.openrouter_free_runtime and returns the normalized assistant text.
    - Guarantee: Defaults to `openrouter/free`; paid/unknown model ids are rejected unless the caller explicitly passes the paid-call gate.
    - Fails: Raises RuntimeError on missing auth, blocked paid call, transport failure, or malformed provider responses.
    - When-needed: Open when observe or local routing code wants a hosted OpenRouter model path without invoking browser bridge.
    - Escalates-to: system/lib/openrouter_free_runtime.py::chat_completion; system/lib/agent_providers.py::resolve_provider_callable
    """
    if cancel and cancel.is_set():
        raise InterruptedError("Cancelled by stop event")
    return openrouter_free_runtime.chat_completion(prompt, config or {})


def resolve_provider_callable(
    provider: str,
    repo_root: Optional[Path] = None,
) -> Callable:
    """
    [ACTION]
    - Teleology: Resolve one provider token into the callable that observe-group orchestration should execute.
    - Mechanism: Normalizes the provider string, returns the local Claude or Codex wrapper for CLI providers, or dynamically imports system.core.bridge.ask_ai for bridge/chatgpt/gemini providers.
    - Guarantee: Returns an ask_ai-compatible callable for supported provider names.
    - Fails: Raises ValueError when the provider name is unknown or when a bridge provider is requested without repo_root.
    - When-needed: Open when the orchestration layer needs the canonical mapping from provider name to executable callable.
    - Escalates-to: system/core/bridge.py::ask_ai; system/lib/bridge_routes.py::resolve_bridge_route_name
    """
    normalized = provider.lower().strip()

    if normalized in ("claude", "claude-code", "claude_code"):
        return ask_claude

    if normalized in ("codex", "codex-cli", "codex_cli"):
        return ask_codex

    if normalized in ("nvidia", "nvidia-nim", "nvidia_nim"):
        return ask_nvidia

    if normalized in ("openrouter", "openrouter-api", "openrouter_api", "openrouter-free", "openrouter_free"):
        return ask_openrouter

    if normalized in ("bridge", "chatgpt", "gemini", ""):
        # Bridge is loaded dynamically to avoid import-time CDP dependency
        if repo_root is None:
            raise ValueError("repo_root required for bridge provider")
        import sys
        root_str = str(repo_root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        from system.core.bridge import ask_ai as bridge_ask_ai
        return bridge_ask_ai

    raise ValueError(f"Unknown provider: {provider!r}")
