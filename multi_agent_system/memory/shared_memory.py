"""
Shared memory module for inter-agent communication and context sharing.
"""
import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class MemoryEntry:
    key: str
    value: Any
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    ttl: Optional[float] = None  # Time-to-live in seconds; None = forever

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.timestamp + self.ttl


class SharedMemory:
    """
    Thread-safe shared memory store for multi-agent systems.
    Agents read/write task context, intermediate results, and messages here.
    """

    def __init__(self):
        self._store: Dict[str, MemoryEntry] = {}
        self._message_queue: List[Dict[str, Any]] = []
        self._task_results: Dict[str, Any] = {}

    # ── Key-value store ──────────────────────────────────────────────────────

    def set(
        self,
        key: str,
        value: Any,
        agent_id: str,
        tags: Optional[List[str]] = None,
        ttl: Optional[float] = None,
    ) -> None:
        self._store[key] = MemoryEntry(
            key=key,
            value=value,
            agent_id=agent_id,
            tags=tags or [],
            ttl=ttl,
        )

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return default
        if entry.is_expired():
            del self._store[key]
            return default
        return entry.value

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def search_by_tag(self, tag: str) -> List[MemoryEntry]:
        return [
            e for e in self._store.values()
            if tag in e.tags and not e.is_expired()
        ]

    # ── Message bus ──────────────────────────────────────────────────────────

    def send_message(self, from_agent: str, to_agent: str, content: Any) -> None:
        self._message_queue.append({
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "timestamp": time.time(),
            "read": False,
        })

    def get_messages(self, agent_id: str, mark_read: bool = True) -> List[Dict]:
        messages = [m for m in self._message_queue if m["to"] == agent_id and not m["read"]]
        if mark_read:
            for m in messages:
                m["read"] = True
        return messages

    # ── Task result store ─────────────────────────────────────────────────────

    def store_result(self, task_id: str, agent_id: str, result: Any) -> None:
        self._task_results[task_id] = {
            "agent_id": agent_id,
            "result": result,
            "timestamp": time.time(),
        }

    def get_result(self, task_id: str) -> Optional[Dict]:
        return self._task_results.get(task_id)

    def get_all_results(self) -> Dict[str, Any]:
        return dict(self._task_results)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict:
        """Return a JSON-serialisable snapshot of the entire memory state."""
        return {
            "store": {
                k: {
                    **asdict(v),
                    "expired": v.is_expired(),
                }
                for k, v in self._store.items()
            },
            "task_results": self._task_results,
            "pending_messages": [m for m in self._message_queue if not m["read"]],
        }

    def clear(self) -> None:
        self._store.clear()
        self._message_queue.clear()
        self._task_results.clear()

    def __repr__(self) -> str:
        return (
            f"SharedMemory(keys={len(self._store)}, "
            f"results={len(self._task_results)}, "
            f"messages={len(self._message_queue)})"
        )
