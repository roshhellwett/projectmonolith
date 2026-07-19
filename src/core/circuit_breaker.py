"""
Circuit breaker pattern for external service calls.

Prevents cascading failures by short-circuiting calls to services
that are consistently failing, and returning fallback data instead.

States:
  CLOSED  → Normal operation, requests pass through
  OPEN    → Service is down, return fallback immediately
  HALF_OPEN → Testing if service recovered (allow 1 request through)
"""

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum

from core.logger import setup_logger

logger = setup_logger("CIRCUIT_BREAKER")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    name: str
    failure_threshold: int = 3  # failures before opening
    recovery_timeout: float = 60.0  # seconds to wait before half-open
    success_threshold: int = 2  # successes in half-open before closing
    window_size: float = 120.0  # failure counting window in seconds


class CircuitBreaker:
    """
    Circuit breaker for an external service.

    Usage:
        breaker = CircuitBreaker(CircuitBreakerConfig("coingecko"))

        async def get_prices():
            if not breaker.can_execute():
                return cached_prices  # fallback

            try:
                result = await fetch_prices()
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                return cached_prices  # fallback
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_times: deque[float] = deque()
        self.success_count = 0
        self.half_open_in_flight = 0
        self.last_failure_time: float = 0
        self.last_state_change: float = time.monotonic()

    def can_execute(self) -> bool:
        """Check if a request should be allowed through."""
        now = time.monotonic()

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if now - self.last_state_change >= self.config.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
                self.half_open_in_flight += 1
                return True
            return False

        # HALF_OPEN — allow limited requests through to test recovery
        if self.half_open_in_flight >= self.config.success_threshold:
            return False
        self.half_open_in_flight += 1
        return True

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_in_flight = max(0, self.half_open_in_flight - 1)
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            # Clean old failures from the window
            self._clean_old_failures()

    def record_failure(self) -> None:
        """Record a failed call."""
        now = time.monotonic()
        self.last_failure_time = now

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test — go back to open
            self.half_open_in_flight = max(0, self.half_open_in_flight - 1)
            self._transition(CircuitState.OPEN)
            return

        # CLOSED state — track failure
        self.failure_times.append(now)
        self._clean_old_failures()

        if len(self.failure_times) >= self.config.failure_threshold:
            self._transition(CircuitState.OPEN)

    def _clean_old_failures(self) -> None:
        """Remove failures outside the counting window."""
        now = time.monotonic()
        cutoff = now - self.config.window_size
        while self.failure_times and self.failure_times[0] < cutoff:
            self.failure_times.popleft()

    def _transition(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.monotonic()

        if new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
            self.half_open_in_flight = 0
        elif new_state == CircuitState.CLOSED:
            self.failure_times.clear()
            self.success_count = 0
            self.half_open_in_flight = 0

        if old_state != new_state:
            logger.info(
                f"⚡ [{self.config.name}] Circuit breaker: "
                f"{old_state.value} → {new_state.value}"
            )

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def status(self) -> dict:
        return {
            "name": self.config.name,
            "state": self.state.value,
            "recent_failures": len(self.failure_times),
            "threshold": self.config.failure_threshold,
        }


# ==========================================================
# Pre-configured breakers for each external service
# ==========================================================
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(service_name: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a service."""
    if service_name not in _breakers:
        configs = {
            "coingecko": CircuitBreakerConfig("coingecko", failure_threshold=3, recovery_timeout=60),
            "goplus": CircuitBreakerConfig("goplus", failure_threshold=3, recovery_timeout=120),
            "etherscan": CircuitBreakerConfig("etherscan", failure_threshold=3, recovery_timeout=60),
            "groq": CircuitBreakerConfig("groq", failure_threshold=5, recovery_timeout=30),
            "serper": CircuitBreakerConfig("serper", failure_threshold=3, recovery_timeout=60),
            "eth_rpc": CircuitBreakerConfig("eth_rpc", failure_threshold=3, recovery_timeout=45),
        }
        config = configs.get(service_name, CircuitBreakerConfig(service_name))
        _breakers[service_name] = CircuitBreaker(config)
    return _breakers[service_name]


def get_all_breaker_statuses() -> list[dict]:
    """Get status of all circuit breakers (for health endpoint)."""
    return [b.status for b in _breakers.values()]
