import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryPolicy:
    prompt_window_turns: int
    compaction_window_turns: int
    uses_summary: bool = True


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


_POLICIES: dict[str, MemoryPolicy] = {
    "supervisor": MemoryPolicy(
        prompt_window_turns=_env_int("HF_MEMORY_SUPERVISOR_TURNS", 2),
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
    "triage_router": MemoryPolicy(
        prompt_window_turns=_env_int("HF_MEMORY_TRIAGE_TURNS", 1),
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
    "conversation_agent": MemoryPolicy(
        prompt_window_turns=_env_int("HF_MEMORY_CONVERSATION_TURNS", 2),
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
    "remedy_agent": MemoryPolicy(
        prompt_window_turns=_env_int("HF_MEMORY_REMEDY_TURNS", 2),
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
    "medical_rag": MemoryPolicy(
        prompt_window_turns=_env_int("HF_MEMORY_RAG_TURNS", 1),
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
    "appointment_booker": MemoryPolicy(
        prompt_window_turns=_env_int("HF_MEMORY_BOOKING_TURNS", 1),
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
    "memory_compactor": MemoryPolicy(
        prompt_window_turns=0,
        compaction_window_turns=_env_int("HF_RECENT_TURNS", 5),
    ),
}


def get_memory_policy(agent_name: str) -> MemoryPolicy:
    return _POLICIES.get(agent_name, MemoryPolicy(prompt_window_turns=1, compaction_window_turns=_env_int("HF_RECENT_TURNS", 5)))
