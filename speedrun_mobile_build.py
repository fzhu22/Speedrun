#!/usr/bin/env python3
"""Speedrun: drive the WSL Android backend rebuild without the PowerShell->wsl.exe
quoting/backslash mangling. Normalizes the four build scripts to LF (reading bytes
directly from disk), then runs the requested phase's scripts via bash.

Usage (from WSL): python3 speedrun_mobile_build.py {sync|build|all}
"""
import subprocess
import sys

ROOT = "/mnt/c/Users/frank/Documents/Alpha/Speedrun"
ALL = ["backend_fixanki.sh", "mobile_sync.sh", "backend_build.sh", "backend_wire.sh"]
PHASES = {
    "sync": ["backend_fixanki.sh", "mobile_sync.sh"],
    "build": ["backend_build.sh", "backend_wire.sh"],
    "all": ALL,
}


def normalize(path):
    with open(path, "rb") as fh:
        data = fh.read()
    fixed = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if fixed != data:
        with open(path, "wb") as fh:
            fh.write(fixed)


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    scripts = PHASES.get(phase, ALL)
    for f in ALL:
        normalize(f"{ROOT}/{f}")
    print(f"== normalized; phase={phase} ==", flush=True)
    for f in scripts:
        print(f"== running {f} ==", flush=True)
        rc = subprocess.run(["bash", f], cwd=ROOT).returncode
        if rc != 0:
            print(f"== FAILED {f} rc={rc} ==", flush=True)
            sys.exit(rc)
    print("== PHASE_DONE ==", flush=True)


if __name__ == "__main__":
    main()
