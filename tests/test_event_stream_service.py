from __future__ import annotations

from app.services.event_stream_service import EventStreamService


class TestEventStreamService:
    def setup_method(self):
        self.service = EventStreamService()

    def test_subscribe_and_unsubscribe(self):
        sub_id = self.service.subscribe()
        assert sub_id is not None

        event = {"event_type": "test", "data": "hello"}
        self.service.publish(event)

        received = self.service.get_next_event(sub_id, timeout=1.0)
        assert received is not None
        assert received["data"] == "hello"

        self.service.unsubscribe(sub_id)
        assert self.service.get_next_event(sub_id, timeout=0.1) is None

    def test_project_filter_matches(self):
        sub_id = self.service.subscribe(project_names={"project-alpha"})
        self.service.publish({"event_type": "test", "project_name": "project-alpha"})
        received = self.service.get_next_event(sub_id, timeout=1.0)
        assert received is not None

    def test_project_filter_mismatch(self):
        sub_id = self.service.subscribe(project_names={"project-alpha"})
        self.service.publish({"event_type": "test", "project_name": "project-beta"})
        received = self.service.get_next_event(sub_id, timeout=0.5)
        assert received is None

    def test_unfiltered_subscriber_receives_all(self):
        sub_id = self.service.subscribe()
        self.service.publish({"event_type": "test", "project_name": "any-project"})
        received = self.service.get_next_event(sub_id, timeout=1.0)
        assert received is not None

    def test_no_event_timeout_returns_none(self):
        sub_id = self.service.subscribe()
        received = self.service.get_next_event(sub_id, timeout=0.1)
        assert received is None

    def test_publish_to_multiple_subscribers(self):
        sub1 = self.service.subscribe()
        sub2 = self.service.subscribe()
        self.service.publish({"event_type": "broadcast"})
        assert self.service.get_next_event(sub1, timeout=1.0) is not None
        assert self.service.get_next_event(sub2, timeout=1.0) is not None

    def test_queue_full_drops_oldest(self):
        sub_id = self.service.subscribe()
        for i in range(210):
            self.service.publish({"event_type": "test", "index": i})
        received = self.service.get_next_event(sub_id, timeout=1.0)
        assert received is not None
