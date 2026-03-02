"""Load and assemble persona system prompts from YAML files.

Each persona has a YAML file in this directory containing its philosophy,
evaluation criteria, and expected output format -- all in Korean (한국어).
Prompts are cached via :func:`functools.lru_cache` for performance.
"""

from __future__ import annotations

import functools
import importlib
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@functools.lru_cache(maxsize=16)
def load_persona_prompt(persona_name: str) -> str:
    """Load and assemble a system prompt from a persona YAML file.

    Args:
        persona_name: Lowercase persona identifier (e.g. ``"graham"``).
            Must match a ``{persona_name}.yaml`` file in the prompts directory.

    Returns:
        Assembled system prompt string combining philosophy, evaluation
        criteria, and output format.

    Raises:
        ImportError: If ``pyyaml`` is not installed.
        FileNotFoundError: If no YAML file exists for the given persona.
    """
    try:
        yaml_module = importlib.import_module("yaml")
    except ImportError:
        raise ImportError("pyyaml required for LLM prompts: pip install pyyaml")

    yaml_path = PROMPTS_DIR / f"{persona_name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Persona prompt not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml_module.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Persona prompt has invalid structure: {yaml_path}")

    payload = data

    criteria_items = payload.get("evaluation_criteria", [])
    if not isinstance(criteria_items, list):
        raise ValueError(f"evaluation_criteria must be a list: {yaml_path}")
    criteria = "\n".join(f"- {c}" for c in criteria_items)

    philosophy = payload.get("philosophy")
    output_format = payload.get("output_format")
    if not isinstance(philosophy, str) or not isinstance(output_format, str):
        raise ValueError(f"Persona prompt missing required text fields: {yaml_path}")

    return f"{philosophy}\n\n## 평가 기준\n{criteria}\n\n## 응답 형식\n{output_format}"
