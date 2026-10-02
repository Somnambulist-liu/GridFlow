"""Shared helpers for GridFlow performance benchmarks.

Run any bench script with the repository root as the working directory.
These scripts are development tooling only; they are never imported by the app.
"""
import ctypes
import ctypes.wintypes as wt
import gc
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def memory_mb() -> tuple:
    """Return (peak_working_set_mb, current_working_set_mb)."""
    counters = _PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
        wt.DWORD,
    ]
    handle = kernel32.GetCurrentProcess()
    ok = psapi.GetProcessMemoryInfo(
        handle, ctypes.byref(counters), counters.cb
    )
    if not ok:
        return (0.0, 0.0)
    return (
        counters.PeakWorkingSetSize / 1048576,
        counters.WorkingSetSize / 1048576,
    )


class Timer:
    """Context manager that records elapsed seconds into a dict."""

    def __init__(self, sink: dict, key: str):
        self._sink = sink
        self._key = key

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self._sink[self._key] = time.perf_counter() - self._t0
        return False


def report(name: str, timings: dict, peak_mb: float = None, current_mb: float = None):
    print(f"### {name}")
    for key, value in timings.items():
        print(f"  {key:<32} {value * 1000:9.1f} ms")
    if timings:
        total = sum(timings.values())
        print(f"  {'TOTAL':<32} {total * 1000:9.1f} ms")
    if peak_mb is not None:
        print(f"  {'peak working set':<32} {peak_mb:9.1f} MB")
    if current_mb is not None:
        print(f"  {'working set':<32} {current_mb:9.1f} MB")
    print()


def rss_after_gc() -> float:
    gc.collect()
    return memory_mb()[1]


def deep_size(obj, limit=4_000_000):
    """Best-effort deep size in bytes using sys.getsizeof + recursion."""
    seen = set()
    total = 0
    stack = [obj]
    visited = 0
    while stack:
        item = stack.pop()
        item_id = id(item)
        if item_id in seen:
            continue
        seen.add(item_id)
        visited += 1
        if visited > limit:
            break
        try:
            total += sys.getsizeof(item)
        except TypeError:
            continue
        if isinstance(item, dict):
            for key, value in list(item.items()):
                stack.append(key)
                stack.append(value)
        elif isinstance(item, (list, tuple, set, frozenset)):
            stack.extend(list(item))
    return total
