"""Best-effort OS-reported hardware inventory; unknown values stay null."""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

from salt import parameters, write_json


def command(*args: str) -> str | None:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def sysctl(key: str) -> int | str | None:
    value = command("sysctl", "-n", key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def linux_cache() -> dict:
    entries = []
    root = Path("/sys/devices/system/cpu/cpu0/cache")
    for item in sorted(root.glob("index*")):
        try:
            entries.append({name: (item / name).read_text().strip() for name in
                            ("level", "type", "size", "coherency_line_size", "shared_cpu_list")})
        except OSError:
            pass
    return {"entries": entries, "source": "Linux sysfs", "L1_data_bytes": None,
            "L2_bytes": None, "L3_bytes": None, "line_bytes": None}


def hardware_profile() -> dict:
    system = platform.system()
    cache = {"entries": [], "source": None, "L1_data_bytes": None,
             "L2_bytes": None, "L3_bytes": None, "line_bytes": None}
    model = None
    physical = None
    logical = os.cpu_count()
    frequency_hz = None
    memory_bytes = None
    evidence = []
    if system == "Darwin":
        model = sysctl("machdep.cpu.brand_string") or sysctl("hw.model")
        physical = sysctl("hw.physicalcpu")
        logical = sysctl("hw.logicalcpu") or logical
        frequency_hz = sysctl("hw.cpufrequency")
        memory_bytes = sysctl("hw.memsize")
        cache["L1_data_bytes"] = sysctl("hw.l1dcachesize")
        cache["L2_bytes"] = sysctl("hw.l2cachesize")
        cache["L3_bytes"] = sysctl("hw.l3cachesize")
        cache["line_bytes"] = sysctl("hw.cachelinesize")
        cache["source"] = "macOS sysctl"
        overview = command("system_profiler", "SPHardwareDataType")
        if overview:
            chip = re.search(r"^\s*Chip:\s*(.+)$", overview, re.M)
            cores = re.search(r"^\s*Total Number of Cores:\s*(\d+)(.*)$", overview, re.M)
            mem = re.search(r"^\s*Memory:\s*(\d+) GB", overview, re.M)
            if chip and (model is None or str(model).startswith("Mac")):
                model = chip.group(1)
            if cores and physical is None:
                physical = int(cores.group(1))
            if mem and memory_bytes is None:
                memory_bytes = int(mem.group(1)) * 1024**3
            if cores:
                evidence.append("system_profiler core description: " + cores.group(0).strip())
            evidence.append("model/core/memory fallback: system_profiler")
    elif system == "Linux":
        try:
            cpuinfo = Path("/proc/cpuinfo").read_text()
            found = re.search(r"^(?:model name|Hardware)\s*:\s*(.+)$", cpuinfo, re.M)
            model = found.group(1) if found else None
        except OSError:
            pass
        try:
            ids = set()
            for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
                topo = cpu / "topology"
                ids.add(((topo / "physical_package_id").read_text().strip(),
                         (topo / "core_id").read_text().strip()))
            physical = len(ids) or None
        except OSError:
            pass
        cache = linux_cache()
        for entry in cache["entries"]:
            unit = entry["size"][-1]
            multiplier = {"K": 1024, "M": 1024**2, "G": 1024**3}.get(unit)
            size = int(entry["size"][:-1]) * multiplier if multiplier else None
            key = {"1": "L1_data_bytes", "2": "L2_bytes", "3": "L3_bytes"}.get(entry["level"])
            if key and (entry["level"] != "1" or entry["type"] == "Data"):
                cache[key] = size
            cache["line_bytes"] = int(entry["coherency_line_size"])
        try:
            memory_bytes = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        except (ValueError, OSError):
            pass
    unknown_fields = {}
    if frequency_hz is None:
        unknown_fields["base_frequency_hz"] = "OS did not expose a reliable base frequency"
    if cache["L1_data_bytes"] is None:
        unknown_fields["L1_data_bytes"] = "OS cache query unavailable"
    if cache["L2_bytes"] is None:
        unknown_fields["L2_bytes"] = "OS cache query unavailable"
    if cache["L3_bytes"] is None:
        unknown_fields["L3_bytes"] = "No reliably reported shared L3 cache size"
    if cache["line_bytes"] is None:
        unknown_fields["cache_line_bytes"] = "OS cache-line query unavailable"
    unknown_fields["microarchitecture"] = "No reliable OS microarchitecture identifier available"
    smt = logical > physical if isinstance(logical, int) and isinstance(physical, int) else None
    if smt is None:
        unknown_fields["smt"] = "Physical or logical count unavailable"
    return {"student_id": "230103024", "salting_id": "30103024",
            "cpu_model": model, "architecture": platform.machine(),
            "microarchitecture": None, "base_frequency_hz": frequency_hz,
            "physical_cores": physical, "logical_cores": logical,
            "logical_threads": logical, "cache_line_bytes": cache["line_bytes"], "smt": smt,
            "cache": cache, "memory_bytes": memory_bytes,
            "os": system, "os_version": platform.version(), "kernel_release": platform.release(),
            "python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
            "python_executable": sys.executable, "numpy_version": np.__version__,
            "evidence": evidence, "unknown_fields": unknown_fields,
            "unknown_means": "OS did not expose a reliable value; no estimate substituted"}


def main() -> None:
    write_json("host_profile.json", hardware_profile())
    write_json("salted_params.json", parameters())
    print("M0: hardware and salted JSON written")


if __name__ == "__main__":
    main()
