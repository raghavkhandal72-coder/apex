#!/usr/bin/env python3
"""
Apex-Sovereign: Guava Resilient Utilities Engine
Inspired by google/guava (Google Core Java Utilities translated to Pure Python)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import collections
import dataclasses
import threading
import time
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Set, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class Preconditions:
    """Defensive assertions inspired by com.google.common.base.Preconditions."""

    @staticmethod
    def check_argument(expression: bool, error_message: str = "Invalid argument") -> None:
        if not expression:
            raise ValueError(error_message)

    @staticmethod
    def check_state(expression: bool, error_message: str = "Illegal state") -> None:
        if not expression:
            raise RuntimeError(error_message)

    @staticmethod
    def check_not_null(reference: Optional[Any], error_message: str = "Reference cannot be null") -> Any:
        if reference is None:
            raise ValueError(error_message)
        return reference

    @staticmethod
    def check_element_index(index: int, size: int, desc: str = "index") -> int:
        if index < 0 or index >= size:
            raise IndexError(f"{desc} ({index}) must not be negative and must be less than size ({size})")
        return index


@dataclasses.dataclass
class CacheStats:
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return (self.hit_count / total) if total > 0 else 0.0


class GuavaCache(Generic[K, V]):
    """
    Resilient in-memory LRU cache with TTL expiration.
    Inspired by com.google.common.cache.CacheBuilder.
    """

    def __init__(
        self,
        max_size: int = 1000,
        expire_after_write_s: Optional[float] = None,
        loader_fn: Optional[Callable[[K], V]] = None,
    ) -> None:
        self.max_size = max_size
        self.expire_after_write_s = expire_after_write_s
        self.loader_fn = loader_fn
        self._lock = threading.Lock()
        # key -> (value, write_time)
        self._cache: collections.OrderedDict[K, Tuple[V, float]] = collections.OrderedDict()
        self._stats = CacheStats()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        now = time.time()
        with self._lock:
            if key in self._cache:
                val, write_time = self._cache[key]
                if self.expire_after_write_s and (now - write_time > self.expire_after_write_s):
                    del self._cache[key]
                    self._stats.eviction_count += 1
                    self._stats.miss_count += 1
                else:
                    self._cache.move_to_end(key)
                    self._stats.hit_count += 1
                    return val
            else:
                self._stats.miss_count += 1

            if self.loader_fn is not None:
                computed_val = self.loader_fn(key)
                self.put(key, computed_val)
                return computed_val

            return default

    def put(self, key: K, value: V) -> None:
        now = time.time()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, now)
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
                self._stats.eviction_count += 1

    def invalidate(self, key: K) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def stats(self) -> CacheStats:
        with self._lock:
            return dataclasses.replace(self._stats)


class RateLimiter:
    """
    Token bucket rate limiter.
    Inspired by com.google.common.util.concurrent.RateLimiter.
    """

    def __init__(self, permits_per_second: float) -> None:
        Preconditions.check_argument(permits_per_second > 0, "permits_per_second must be positive")
        self.permits_per_second = permits_per_second
        self.max_permits = max(1.0, permits_per_second)
        self.stored_permits = self.max_permits
        self.last_update = time.time()
        self._lock = threading.Lock()

    def _sync(self, now: float) -> None:
        elapsed = now - self.last_update
        if elapsed > 0:
            self.stored_permits = min(self.max_permits, self.stored_permits + elapsed * self.permits_per_second)
            self.last_update = now

    def acquire(self, permits: int = 1) -> float:
        """Blocks until the requested number of permits is available."""
        Preconditions.check_argument(permits > 0, "permits must be > 0")
        while True:
            with self._lock:
                now = time.time()
                self._sync(now)
                if self.stored_permits >= permits:
                    self.stored_permits -= permits
                    return 0.0
                needed = permits - self.stored_permits
                wait_time = needed / self.permits_per_second
            time.sleep(min(0.05, wait_time))

    def try_acquire(self, permits: int = 1) -> bool:
        """Acquires permits if available immediately, returning False otherwise."""
        Preconditions.check_argument(permits > 0, "permits must be > 0")
        with self._lock:
            now = time.time()
            self._sync(now)
            if self.stored_permits >= permits:
                self.stored_permits -= permits
                return True
            return False


class BiMap(Generic[K, V]):
    """
    Bidirectional map guaranteeing 1-to-1 uniqueness between keys and values.
    Inspired by com.google.common.collect.BiMap.
    """

    def __init__(self) -> None:
        self._forward: Dict[K, V] = {}
        self._inverse: Dict[V, K] = {}

    def put(self, key: K, value: V) -> None:
        if value in self._inverse and self._inverse[value] != key:
            raise ValueError(f"Value '{value}' already bound to key '{self._inverse[value]}'")
        if key in self._forward:
            del self._inverse[self._forward[key]]
        self._forward[key] = value
        self._inverse[value] = key

    def force_put(self, key: K, value: V) -> None:
        if value in self._inverse:
            old_key = self._inverse[value]
            del self._forward[old_key]
        if key in self._forward:
            old_val = self._forward[key]
            del self._inverse[old_val]
        self._forward[key] = value
        self._inverse[value] = key

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self._forward.get(key, default)

    def get_by_value(self, value: V, default: Optional[K] = None) -> Optional[K]:
        return self._inverse.get(value, default)

    def inverse(self) -> Dict[V, K]:
        return dict(self._inverse)

    def __len__(self) -> int:
        return len(self._forward)

    def __contains__(self, key: K) -> bool:
        return key in self._forward


class Multimap(Generic[K, V]):
    """
    Multimap mapping each key to a list of values.
    Inspired by com.google.common.collect.Multimap.
    """

    def __init__(self) -> None:
        self._data: Dict[K, List[V]] = collections.defaultdict(list)

    def put(self, key: K, value: V) -> None:
        self._data[key].append(value)

    def get(self, key: K) -> List[V]:
        return list(self._data.get(key, []))

    def remove(self, key: K, value: V) -> bool:
        if key in self._data and value in self._data[key]:
            self._data[key].remove(value)
            if not self._data[key]:
                del self._data[key]
            return True
        return False

    def keys(self) -> List[K]:
        return list(self._data.keys())

    def values(self) -> List[V]:
        out = []
        for vals in self._data.values():
            out.extend(vals)
        return out

    def size(self) -> int:
        return sum(len(vals) for vals in self._data.values())
