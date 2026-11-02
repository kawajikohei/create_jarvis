from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

EFFORTS = {"low", "medium", "high", "xhigh", "max"}


@dataclass(frozen=True)
class Config:
    model: str
    effort: str
    user_name: str
    max_tokens: int = 16000

    @classmethod
    def load(cls) -> "Config":
        load_dotenv()
        effort = os.getenv("JARVIS_EFFORT", "medium").strip().lower()
        if effort not in EFFORTS:
            raise ValueError(f"JARVIS_EFFORT は {sorted(EFFORTS)} のどれかにしてください: {effort}")
        return cls(
            model=os.getenv("JARVIS_MODEL", "claude-opus-5-5").strip(),
            effort=effort,
            user_name=os.getenv("JARVIS_USER_NAME", "").strip(),
        )
