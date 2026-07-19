"""
Centralized Metrics & Observability Collector.

Tracks real-time telemetry across all bots:
- Request counts & success/failure rates
- Response latencies (p50, p95, average)
- Service circuit breaker & API error metrics
"""

import time
from collections import deque


class MetricCounter:
    def __init__(self):
        self.counts: dict[str, int] = {}

    def inc(self, key: str, amount: int = 1):
        self.counts[key] = self.counts.get(key, 0) + amount

    def get_all(self) -> dict[str, int]:
        return dict(self.counts)


class MetricHistogram:
    def __init__(self, max_samples: int = 2000):
        self.samples: dict[str, deque] = {}
        self.max_samples = max_samples

    def observe(self, key: str, value_ms: float):
        if key not in self.samples:
            self.samples[key] = deque(maxlen=self.max_samples)
        self.samples[key].append(value_ms)

    def get_stats(self, key: str) -> dict:
        if key not in self.samples or not self.samples[key]:
            return {"count": 0, "avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}

        sorted_vals = sorted(self.samples[key])
        n = len(sorted_vals)
        avg = sum(sorted_vals) / n
        p50 = sorted_vals[int(n * 0.5)]
        p95 = sorted_vals[int(n * 0.95) if n > 1 else 0]

        return {
            "count": n,
            "avg_ms": round(avg, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
        }

    def get_all_stats(self) -> dict[str, dict]:
        return {key: self.get_stats(key) for key in self.samples}


class MetricsCollector:
    """Singleton metrics registry for the monolithic platform."""

    def __init__(self):
        self.requests = MetricCounter()
        self.errors = MetricCounter()
        self.latencies = MetricHistogram()
        self.start_time = time.time()

    def record_request(self, bot_name: str, action: str, duration_ms: float, success: bool = True):
        self.requests.inc(f"{bot_name}.{action}")
        self.requests.inc(f"{bot_name}.total")
        if not success:
            self.errors.inc(f"{bot_name}.{action}.error")
            self.errors.inc(f"{bot_name}.total_errors")
        self.latencies.observe(f"{bot_name}.latency", duration_ms)

    def record_error(self, service: str, error_type: str):
        self.errors.inc(f"service.{service}.{error_type}")
        self.errors.inc("service.total_errors")

    def get_summary(self) -> dict:
        uptime = round(time.time() - self.start_time, 2)
        return {
            "uptime_seconds": uptime,
            "requests": self.requests.get_all(),
            "errors": self.errors.get_all(),
            "latencies": self.latencies.get_all_stats(),
        }


# Global singleton collector
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics
