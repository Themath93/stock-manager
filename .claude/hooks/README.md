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

## Configuration

체크리스트 항목과 동작을 `quality-checklist.json`으로 커스터마이징 가능.

| 필드 | 타입 | 설명 |
|------|------|------|
| `checklist` | string[] | 번호 매겨 표시할 체크리스트 항목 |
| `done_token` | string | 통과에 필요한 토큰 |
| `header_message` | string | 체크리스트 앞에 표시할 안내 메시지 |
| `max_blocks_per_session` | int | 세션당 최대 block 횟수 |
| `show_done_token_instruction` | bool | done token 안내 자동 추가 여부 |
| `show_change_count` | bool | 변경 파일 수 표시 여부 |

파일이 없거나 잘못된 JSON인 경우 내장 기본값을 사용합니다.

## Temporary Disable

Set environment variable:

`CLAUDE_DISABLE_GUIDELINE_STOP_HOOK=1`

Use only for emergency troubleshooting.

Optional state path override:

`CLAUDE_GUIDELINE_HOOK_STATE_DIR=/custom/state/path`
