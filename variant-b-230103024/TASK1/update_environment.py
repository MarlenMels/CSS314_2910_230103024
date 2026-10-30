import os
import platform
import multiprocessing as mp
import subprocess
import re
from pathlib import Path


def get_cpu_model():
    if platform.system() == "Darwin":
        try:
            return subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                return subprocess.check_output(
                    ["sysctl", "-n", "hw.model"],
                    text=True
                ).strip()
            except Exception:
                return platform.processor()

    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass

    return platform.processor() or "Unknown"


def main():
    os_info = platform.platform()
    cpu = get_cpu_model()
    logical_cpus = os.cpu_count()
    python_version = platform.python_version()
    start_method = mp.get_start_method()

    environment = (
        f"OS: {os_info}\n"
        f"CPU: {cpu}\n"
        f"Logical CPUs: {logical_cpus}\n"
        f"Python: {python_version}\n"
        f"Start method: {start_method}"
    )

    print("\nDetected environment:\n")
    print(environment)

    report_path = Path("RESULTS.md")

    if not report_path.exists():
        print("\nERROR: RESULTS.md not found.")
        return

    content = report_path.read_text(encoding="utf-8")

    pattern = (
        r"OS:.*\n"
        r"CPU:.*\n"
        r"Logical CPUs:.*\n"
        r"Python:.*\n"
        r"Start method:.*"
        r"(?:\nNOTE:.*)?"
    )

    updated_content, count = re.subn(
        pattern,
        environment,
        content,
        count=1
    )

    if count == 0:
        print("\nERROR: Environment section not found.")
        return

    report_path.write_text(updated_content, encoding="utf-8")

    print("\nSUCCESS: RESULTS.md updated!")


if __name__ == "__main__":
    main()