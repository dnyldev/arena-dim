import time

from app.events import EventStage, EventStatus
from app.events.bus import EventBus, JobReporter


def test_bus_records_history():
    bus = EventBus()
    r = JobReporter("job1", bus)
    r.started(EventStage.PROBE, "probing")
    r.completed(EventStage.PROBE, "done")
    history = bus.history("job1")
    assert len(history) == 2
    assert history[0].status == EventStatus.STARTED
    assert history[1].status == EventStatus.COMPLETED
    assert history[1].elapsed_ms is not None
    assert history[1].elapsed_ms >= 0


def test_bus_subscribers():
    bus = EventBus()
    received = []
    bus.subscribe(lambda e: received.append(e))
    JobReporter("j", bus).info(EventStage.SYSTEM, "hello")
    assert len(received) == 1
    assert received[0].message == "hello"


def test_bad_subscriber_does_not_crash():
    bus = EventBus()

    def bad(_):
        raise RuntimeError("boom")

    bus.subscribe(bad)
    # Should not raise:
    JobReporter("j", bus).info(EventStage.SYSTEM, "still works")
