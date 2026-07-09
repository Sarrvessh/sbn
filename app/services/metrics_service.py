"""Lightweight Prometheus-format metrics — no external dependency."""

from __future__ import annotations

from threading import Lock


class Counter:
    def __init__(self, name: str, help_text: str, label_names: tuple[str, ...] = ()) -> None:
        self._name = name
        self._help = help_text
        self._label_names = label_names
        self._values: dict[tuple[str, ...], int] = {}
        self._lock = Lock()

    def inc(self, labels: dict[str, str] | None = None, value: int = 1) -> None:
        key = tuple(labels[k] for k in self._label_names) if labels else ()
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value

    def collect(self) -> str:
        lines = [f"# HELP {self._name} {self._help}", f"# TYPE {self._name} counter"]
        with self._lock:
            for key, val in self._values.items():
                if key:
                    labels = ",".join(f'{k}="{v}"' for k, v in zip(self._label_names, key))
                    lines.append(f"{self._name}{{{labels}}} {val}")
                else:
                    lines.append(f"{self._name} {val}")
        return "\n".join(lines) + "\n"


class Histogram:
    def __init__(self, name: str, help_text: str, label_names: tuple[str, ...] = (), buckets: tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)) -> None:
        self._name = name
        self._help = help_text
        self._label_names = label_names
        self._buckets = buckets
        self._values: dict[tuple[str, ...], dict[int | str, int]] = {}
        self._lock = Lock()

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        key = tuple(labels[k] for k in self._label_names) if labels else ()
        with self._lock:
            if key not in self._values:
                self._values[key] = {b: 0 for b in self._buckets}
                self._values[key]["+Inf"] = 0
                self._values[key]["_sum"] = 0
                self._values[key]["_count"] = 0
            for b in self._buckets:
                if value <= b:
                    self._values[key][b] += 1
            self._values[key]["+Inf"] += 1
            self._values[key]["_sum"] += value
            self._values[key]["_count"] += 1

    def collect(self) -> str:
        lines = [f"# HELP {self._name} {self._help}", f"# TYPE {self._name} histogram"]
        with self._lock:
            for key, buckets in self._values.items():
                suffix = ""
                if key:
                    labels = ",".join(f'{k}="{v}"' for k, v in zip(self._label_names, key))
                    suffix = f"{{{labels}}}"
                for b in self._buckets:
                    lines.append(f"{self._name}_bucket{{{suffix},le=\"{b}\"}} {buckets[b]}")
                lines.append(f"{self._name}_bucket{{{suffix},le=\"+Inf\"}} {buckets['+Inf']}")
                lines.append(f"{self._name}_count{suffix} {buckets['_count']}")
                lines.append(f"{self._name}_sum{suffix} {buckets['_sum']}")
        return "\n".join(lines) + "\n"


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._lock = Lock()

    def counter(self, name: str, help_text: str, label_names: tuple[str, ...] = ()) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, help_text, label_names)
            return self._counters[name]

    def histogram(self, name: str, help_text: str, label_names: tuple[str, ...] = ()) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, help_text, label_names)
            return self._histograms[name]

    def collect_all(self) -> str:
        lines: list[str] = []
        with self._lock:
            for c in self._counters.values():
                lines.append(c.collect())
            for h in self._histograms.values():
                lines.append(h.collect())
        return "\n".join(lines)


registry = MetricsRegistry()

http_requests_total = registry.counter("http_requests_total", "Total HTTP requests", ("method", "path", "status"))
http_request_duration_seconds = registry.histogram("http_request_duration_seconds", "HTTP request duration", ("method", "path"))
traces_ingested_total = registry.counter("traces_ingested_total", "Total traces ingested")
governance_flags_total = registry.counter("governance_flags_total", "Total governance flags", ("severity",))
alerts_fired_total = registry.counter("alerts_fired_total", "Total alerts fired", ("alert_type", "severity"))
