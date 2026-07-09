"""Tests for the lightweight Prometheus-format metrics."""
from __future__ import annotations

from app.services.metrics_service import Counter, Histogram, MetricsRegistry


class TestCounter:
    def test_inc_default(self):
        c = Counter("test_counter", "A test counter")
        c.inc()
        assert "test_counter 1" in c.collect()

    def test_inc_multiple(self):
        c = Counter("test_counter", "A test counter")
        c.inc(value=3)
        c.inc(value=2)
        assert "test_counter 5" in c.collect()

    def test_with_labels(self):
        c = Counter("test_counter", "A test counter", ("method", "path"))
        c.inc({"method": "GET", "path": "/api"})
        c.inc({"method": "GET", "path": "/api"})
        c.inc({"method": "POST", "path": "/api"})
        output = c.collect()
        assert 'test_counter{method="GET",path="/api"} 2' in output
        assert 'test_counter{method="POST",path="/api"} 1' in output

    def test_help_and_type(self):
        c = Counter("test_counter", "A test counter")
        output = c.collect()
        assert "# HELP test_counter A test counter" in output
        assert "# TYPE test_counter counter" in output


class TestHistogram:
    def test_observe_single(self):
        h = Histogram("test_duration", "Test duration")
        h.observe(0.1)
        output = h.collect()
        assert "test_duration_count" in output
        assert "test_duration_sum" in output

    def test_observe_in_bucket(self):
        h = Histogram("test_duration", "Test duration", buckets=(0.05, 0.1, 0.5))
        h.observe(0.1)
        output = h.collect()
        assert 'test_duration_bucket{,le="0.05"} 0' in output
        assert 'test_duration_bucket{,le="0.1"} 1' in output
        assert 'test_duration_bucket{,le="0.5"} 1' in output
        assert 'test_duration_bucket{,le="+Inf"} 1' in output
        assert 'test_duration_count 1' in output

    def test_observe_with_labels(self):
        h = Histogram("test_duration", "Test duration", ("method",))
        h.observe(0.2, {"method": "GET"})
        output = h.collect()
        assert 'test_duration_count{method="GET"} 1' in output

    def test_sum_and_count(self):
        h = Histogram("test_duration", "Test duration")
        h.observe(1.0)
        h.observe(2.0)
        output = h.collect()
        assert "test_duration_count 2" in output
        assert "test_duration_sum 3.0" in output


class TestMetricsRegistry:
    def test_counter_singleton(self):
        r = MetricsRegistry()
        c1 = r.counter("dup", "help")
        c2 = r.counter("dup", "help")
        assert c1 is c2

    def test_histogram_singleton(self):
        r = MetricsRegistry()
        h1 = r.histogram("dup", "help")
        h2 = r.histogram("dup", "help")
        assert h1 is h2

    def test_collect_all(self):
        r = MetricsRegistry()
        r.counter("c1", "counter one")
        r.histogram("h1", "histogram one")
        output = r.collect_all()
        assert "# HELP c1 counter one" in output
        assert "# HELP h1 histogram one" in output
