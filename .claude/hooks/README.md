# Agent Hook: Guideline Double-Check Gate

This project uses a Claude Code `Stop` hook to force one extra guideline verification pass before the agent completes while there are working-tree changes.

## Files

- `.claude/settings.json`: hook registration
- `.claude/hooks/agent_stop_guideline_gate.py`: gate script

## Behavior

- Trigger: `Stop` event.
- Condition: git working tree has pending changes.
- Action: blocks at most once per session and asks the agent to provide a guideline checklist.
- Pass condition: if the latest assistant response includes `[GUIDELINE_DOUBLE_CHECK_DONE]`, stop is allowed.
- Loop guard: respects `stop_hook_active` to avoid infinite continuation loops.

## Temporary Disable

Set environment variable:

`CLAUDE_DISABLE_GUIDELINE_STOP_HOOK=1`

Use only for emergency troubleshooting.

Optional state path override:

`CLAUDE_GUIDELINE_HOOK_STATE_DIR=/custom/state/path`
