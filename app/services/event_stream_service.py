"""In-process event stream broker for SSE subscribers."""

from __future__ import annotations

import queue
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4


@dataclass(slots=True)
class _Subscriber:
    """One event stream subscriber with optional project filter."""

    queue: queue.Queue[dict]
    project_names: set[str] | None


class EventStreamService:
    """Simple thread-safe pub/sub service for realtime telemetry updates."""

    def __init__(self) -> None:
        self._subscribers: dict[str, _Subscriber] = {}
        self._lock = Lock()
        self._event_counter = 0

    def subscribe(self, project_names: set[str] | None = None) -> str:
        """Register subscriber and return subscription ID."""

        subscriber_id = uuid4().hex
        subscriber = _Subscriber(queue=queue.Queue(maxsize=200), project_names=project_names)
        with self._lock:
            self._subscribers[subscriber_id] = subscriber
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove subscriber and free memory."""

        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def publish(self, event: dict) -> None:
        """Publish event to all subscribers that match project filter."""

        project_name = event.get("project_name")

        with self._lock:
            self._event_counter += 1
            event["event_id"] = self._event_counter
            subscribers = list(self._subscribers.items())

        for subscriber_id, subscriber in subscribers:
            if (
                subscriber.project_names is not None
                and project_name not in subscriber.project_names
            ):
                continue

            try:
                subscriber.queue.put_nowait(event)
            except queue.Full:
                try:
                    subscriber.queue.get_nowait()
                    subscriber.queue.put_nowait(event)
                except queue.Empty:
                    continue
                except queue.Full:
                    self.unsubscribe(subscriber_id)

    def get_next_event(self, subscriber_id: str, timeout: float = 15.0) -> dict | None:
        """Return next event for subscriber or None on timeout/missing subscriber."""

        with self._lock:
            subscriber = self._subscribers.get(subscriber_id)

        if subscriber is None:
            return None

        try:
            return subscriber.queue.get(timeout=timeout)
        except queue.Empty:
            return None


event_stream_service = EventStreamService()
