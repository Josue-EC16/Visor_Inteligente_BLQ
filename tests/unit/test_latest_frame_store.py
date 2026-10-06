from threading import Event, Thread

import numpy as np
import pytest

from blanquita_vision.application.latest_frame_store import LatestFrameStore
from blanquita_vision.domain.models.frame import Frame
from tests.fixtures.fake_camera import make_frame


def test_tc_010_latest_frame_and_coalesced_notification():
    store = LatestFrameStore()
    assert [store.publish(make_frame(i)) for i in (1, 2, 3)] == [True, False, False]
    assert store.latest().sequence == 3
    assert store.consume().sequence == 3
    assert store.metrics().stale_frames_replaced == 2
    assert store.publish(make_frame(4)) is True


def test_tc_017_snapshot_is_independent_and_ephemeral(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = LatestFrameStore()
    frame = make_frame(7)
    store.publish(frame)
    snapshot = store.snapshot()
    store.publish(make_frame(8))
    assert snapshot.source_sequence == 7
    assert snapshot.captured_at == frame.captured_at
    assert np.all(snapshot.image_copy == 7)
    snapshot.image_copy[:] = 42
    assert np.all(frame.image == 7)
    assert not list(tmp_path.iterdir())


def test_tc_018_snapshot_without_frame():
    store = LatestFrameStore()
    assert store.snapshot() is None
    store.publish(make_frame())
    store.clear()
    assert store.snapshot() is None


def test_frame_rejects_empty_image():
    frame = make_frame()
    with pytest.raises(ValueError):
        Frame(0, frame.captured_at, 16, 12, np.empty((0, 0, 3)))


def test_concurrent_producer_keeps_latest_without_queue():
    store = LatestFrameStore()
    notifications = []

    def produce():
        for index in range(500):
            notifications.append(store.publish(make_frame(index)))

    thread = Thread(target=produce)
    thread.start()
    while thread.is_alive():
        snapshot = store.snapshot()
        if snapshot is not None:
            assert np.all(snapshot.image_copy == snapshot.source_sequence % 256)
    thread.join()
    assert store.latest().sequence == 499
    assert sum(notifications) == 1
    assert store.metrics().stale_frames_replaced == 499


def test_vision_cursor_is_independent_of_ui_consumption_and_sequence_reset():
    store = LatestFrameStore()
    cancellation = Event()
    store.publish(make_frame(10))
    revision, frame = store.wait_next(-1, cancellation)
    assert frame.sequence == 10
    store.consume()
    store.publish(make_frame(11))
    store.consume()
    new_revision, frame = store.wait_next(revision, cancellation)
    assert frame.sequence == 11
    assert new_revision > revision
    store.clear()
    store.publish(make_frame(0))
    reset_revision, frame = store.wait_next(new_revision, cancellation)
    assert reset_revision > new_revision
    assert frame.sequence == 0


def test_waiting_vision_cursor_can_be_cancelled_without_new_frame():
    store = LatestFrameStore()
    cancellation = Event()
    revision, _ = store.wait_next(-1, cancellation)
    results = []
    thread = Thread(target=lambda: results.append(store.wait_next(revision, cancellation)))
    thread.start()
    cancellation.set()
    store.wake_consumers()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert results == [(revision, None)]
