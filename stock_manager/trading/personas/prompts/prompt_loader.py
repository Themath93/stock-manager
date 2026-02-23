"""Load and assemble persona system prompts from YAML files.

Each persona has a YAML file in this directory containing its philosophy,
evaluation criteria, and expected output format -- all in Korean (한국어).
Prompts are cached via :func:`functools.lru_cache` for performance.
"""

from __future__ import annotations

import functools
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
        import yaml
    except ImportError:
        raise ImportError("pyyaml required for LLM prompts: pip install pyyaml")

    yaml_path = PROMPTS_DIR / f"{persona_name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Persona prompt not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    criteria = "\n".join(f"- {c}" for c in data.get("evaluation_criteria", []))
    return (
        f"{data['philosophy']}\n\n"
        f"## 평가 기준\n{criteria}\n\n"
        f"## 응답 형식\n{data['output_format']}"
    )
