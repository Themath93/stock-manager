#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


DONE_TOKEN = "[GUIDELINE_DOUBLE_CHECK_DONE]"
MAX_BLOCKS_PER_SESSION = 1

_CONFIG_FILENAME = "quality-checklist.json"

_DEFAULT_CONFIG: dict[str, object] = {
    "done_token": DONE_TOKEN,
    "max_blocks_per_session": MAX_BLOCKS_PER_SESSION,
    "header_message": (
        "개발 완료 전 품질 체크리스트를 확인해주세요.\n"
        "다음 항목을 점검한 뒤 다시 완료 응답하세요:"
    ),
    "checklist": [
        "TDD 방식의 테스트코드 구성은 했나요? (새 기능 → 테스트 추가, 버그 수정 → 재현 테스트 작성)",
        "지식맵(AGENTS.md, CLAUDE.md, docs/)은 변경사항에 맞게 최신화 했나요?",
        "요구사항을 모두 만족했나요? 원래 요청 대비 누락 항목이 없는지 확인",
        "검증(ruff check, mypy, pytest)을 실행했고 모두 통과했나요?",
    ],
    "show_done_token_instruction": True,
    "show_change_count": True,
}


def _load_config() -> dict[str, object]:
    config_path = Path(__file__).resolve().parent / _CONFIG_FILENAME
    try:
        parsed = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_CONFIG)
    if not isinstance(parsed, dict):
        return dict(_DEFAULT_CONFIG)
    merged = dict(_DEFAULT_CONFIG)
    if isinstance(parsed.get("done_token"), str) and parsed["done_token"].strip():
        merged["done_token"] = parsed["done_token"]
    if isinstance(parsed.get("max_blocks_per_session"), int) and parsed["max_blocks_per_session"] >= 1:
        merged["max_blocks_per_session"] = parsed["max_blocks_per_session"]
    if isinstance(parsed.get("header_message"), str):
        merged["header_message"] = parsed["header_message"]
    if isinstance(parsed.get("checklist"), list) and all(isinstance(i, str) for i in parsed["checklist"]):
        merged["checklist"] = parsed["checklist"]
    if isinstance(parsed.get("show_done_token_instruction"), bool):
        merged["show_done_token_instruction"] = parsed["show_done_token_instruction"]
    if isinstance(parsed.get("show_change_count"), bool):
        merged["show_change_count"] = parsed["show_change_count"]
    return merged


def _load_payload() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _git_change_count(cwd: Path) -> int:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return 0

    if result.returncode != 0:
        return 0

    return sum(1 for line in result.stdout.splitlines() if line.strip())


def _build_block_output(change_count: int, config: dict[str, object]) -> dict[str, str]:
    parts: list[str] = [str(config["header_message"])]
    checklist = config["checklist"]
    if not isinstance(checklist, list):
        checklist = []
    for i, item in enumerate(checklist, start=1):
        parts.append(f"{i}) {item}")
    if config.get("show_done_token_instruction"):
        parts.append(f"{len(checklist) + 1}) 응답 마지막에 {config['done_token']} 토큰을 추가")
    if config.get("show_change_count"):
        parts.append(f"(현재 변경 파일 감지: {change_count})")
    return {"decision": "block", "reason": "\n".join(parts)}


def _latest_assistant_text(transcript_path: Path) -> str:
    latest = ""
    try:
        with transcript_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                if message.get("role") != "assistant":
                    continue
                content = message.get("content")
                text_parts: list[str] = []
                if isinstance(content, str):
                    if content.strip():
                        text_parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if isinstance(text, str) and text.strip():
                                text_parts.append(text)
                if text_parts:
                    latest = "\n".join(text_parts)
    except OSError:
        return ""
    return latest


def _double_check_is_confirmed(payload: dict[str, object], done_token: str) -> bool:
    transcript_path_value = payload.get("transcript_path")
    if not isinstance(transcript_path_value, str) or not transcript_path_value:
        return False
    latest_text = _latest_assistant_text(Path(transcript_path_value))
    return done_token in latest_text


def _state_dir_path() -> Path:
    configured = os.getenv("CLAUDE_GUIDELINE_HOOK_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / "claude-guideline-stop-hook"


def _session_state_path(session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return _state_dir_path() / f"{digest}.json"


def _session_block_count(session_id: str) -> int:
    if not session_id:
        return 0
    path = _session_state_path(session_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return 0
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    value = payload.get("block_count")
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _set_session_block_count(session_id: str, count: int) -> None:
    if not session_id:
        return
    if count < 0:
        return
    path = _session_state_path(session_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps({"block_count": count}, ensure_ascii=True), encoding="utf-8"
        )
        temp_path.replace(path)
    except OSError:
        return


def _should_block_this_stop(payload: dict[str, object], max_blocks: int) -> bool:
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return True
    current_count = _session_block_count(session_id)
    if current_count >= max_blocks:
        return False
    _set_session_block_count(session_id, current_count + 1)
    return True


def main() -> int:
    if os.getenv("CLAUDE_DISABLE_GUIDELINE_STOP_HOOK") == "1":
        return 0

    payload = _load_payload()

    hook_event_name = str(payload.get("hook_event_name", ""))
    if hook_event_name not in {"Stop", "SubagentStop"}:
        return 0

    if bool(payload.get("stop_hook_active")):
        return 0

    cwd_value = payload.get("cwd")
    cwd = Path(str(cwd_value)).resolve() if isinstance(cwd_value, str) and cwd_value else Path.cwd()

    change_count = _git_change_count(cwd)
    if change_count <= 0:
        return 0

    config = _load_config()

    if _double_check_is_confirmed(payload, str(config["done_token"])):
        return 0

    if not _should_block_this_stop(payload, int(config["max_blocks_per_session"])):  # type: ignore[arg-type]
        return 0

    print(json.dumps(_build_block_output(change_count, config), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
