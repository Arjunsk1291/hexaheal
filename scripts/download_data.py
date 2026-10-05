"""Download the FlyWire v783 tables used by NeuroWalker and verify SHA-256 checksums (data/checksums.json).
Data license: FlyWire public release CC BY-NC 4.0 (https://flywire.ai/guidelines). Never commit these files."""
import hashlib, json, os, sys, urllib.request

meta = json.load(open("data/checksums.json"))
os.makedirs("data/raw", exist_ok=True)
for name, m in meta.items():
    path = f"data/raw/{name}"
    if not os.path.exists(path):
        print("downloading", name); urllib.request.urlretrieve(m["url"], path)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    print(name, "OK" if h == m["sha256"] else "CHECKSUM MISMATCH")
    if h != m["sha256"]: sys.exit(1)
print("now run: python -m neurowalker.connectome")
