import time
from typing import Callable, TypeVar


T = TypeVar("T")


class RetryPolicy:
    def __init__(self, attempts: int = 2, backoff_seconds: float = 0.2):
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds

    def run(self, fn: Callable[[], T]) -> T:
        last_error = None
        for index in range(self.attempts):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if index < self.attempts - 1:
                    time.sleep(self.backoff_seconds * (index + 1))
        raise last_error
