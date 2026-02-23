"""Claude Agent SDK wrapper for persona LLM verification.

Provides async and sync interfaces for querying Claude via the local CLI.
Includes retry with exponential backoff and a synchronous wrapper for
thread-pool contexts.
"""

from __future__ import annotations

import asyncio
import os
import logging

logger = logging.getLogger(__name__)


async def async_persona_query(
    prompt: str,
    system_prompt: str,
    model: str | None = None,
    max_turns: int = 1,
    timeout_sec: float = 30.0,
) -> str | None:
    """Query Claude via local CLI for persona LLM verification.

    Args:
        prompt: The user prompt to send.
        system_prompt: System prompt defining persona behaviour.
        model: Claude model identifier. Falls back to CLAUDE_MODEL env var
               or ``claude-sonnet-4-6``.
        max_turns: Maximum conversation turns (default 1 for single-shot).
        timeout_sec: Per-message timeout in seconds.

    Returns:
        Response text or None on failure / empty response.
    """
    try:
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
    except ImportError:
        logger.warning("claude-agent-sdk not installed. LLM features disabled.")
        return None

    stderr_lines: list[str] = []
    options = ClaudeAgentOptions(
        model=model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        system_prompt=system_prompt,
        permission_mode="default",
        max_turns=max_turns,
        cli_path=os.environ.get("CLAUDE_CLI_PATH", "~/.local/bin/claude"),
        stderr=lambda line: stderr_lines.append(line),
        env={"NODE_TLS_REJECT_UNAUTHORIZED": "0"},
    )

    response_text = ""
    aiter = query(prompt=prompt, options=options).__aiter__()
    while True:
        try:
            message = await asyncio.wait_for(aiter.__anext__(), timeout=timeout_sec)
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError:
            logger.warning(f"SDK query timeout after {timeout_sec}s")
            return None
        except Exception as e:
            # Skip unknown message types from SDK evolution
            if "Unknown message type" in str(e):
                continue
            raise

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text

    return response_text if response_text else None


async def async_persona_query_with_retry(
    prompt: str,
    system_prompt: str,
    max_retries: int = 3,
    **kwargs,
) -> str | None:
    """Retry wrapper with exponential backoff.

    Args:
        prompt: The user prompt to send.
        system_prompt: System prompt defining persona behaviour.
        max_retries: Maximum number of attempts (default 3).
        **kwargs: Forwarded to :func:`async_persona_query`.

    Returns:
        Response text from the first successful attempt, or None.
    """
    best_response: str | None = None
    for attempt in range(max_retries):
        try:
            result = await async_persona_query(prompt, system_prompt, **kwargs)
            if result is not None:
                return result
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            continue
    return best_response


def sync_persona_query(prompt: str, system_prompt: str, **kwargs) -> str | None:
    """Synchronous wrapper for thread pool contexts.

    Creates a new event loop via :func:`asyncio.run`.  Safe only when no
    event loop is already running.

    Args:
        prompt: The user prompt to send.
        system_prompt: System prompt defining persona behaviour.
        **kwargs: Forwarded to :func:`async_persona_query_with_retry`.

    Returns:
        Response text or None.
    """
    return asyncio.run(async_persona_query_with_retry(prompt, system_prompt, **kwargs))
