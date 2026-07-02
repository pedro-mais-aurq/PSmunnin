
from typing import Callable, List, Dict, Any


class TypedEventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable[[Any], None]):
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: Any):
        for handler in self._handlers.get(event_type, []):
            handler(payload)
