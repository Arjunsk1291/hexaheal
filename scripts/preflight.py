"""Phase 0 environment detection. Writes results/preflight.json."""
import json
import os
import platform
import shutil
import subprocess
import sys


def ver(cmd):
    if not shutil.which(cmd[0]):
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
    except Exception:
        return "present"

info = {"os": platform.platform(), "python": sys.version.split()[0], "cpus": os.cpu_count(),
        "docker": ver(["docker", "--version"]), "ffmpeg": ver(["ffmpeg", "-version"]),
        "node": ver(["node", "--version"]), "gh": ver(["gh", "--version"]),
        "nvidia_smi": ver(["nvidia-smi", "-L"])}
os.makedirs("results", exist_ok=True)
json.dump(info, open("results/preflight.json", "w"), indent=2)
print(json.dumps(info, indent=2))
