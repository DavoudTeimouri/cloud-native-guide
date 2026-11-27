import re

path = "/workspace/project/github/public-repository/cloud-native-guide/storage/rook-ceph/rook-ceph-deployment.md"
with open(path) as f:
    content = f.read()

fences = re.findall(r"^```", content, re.M)
print(f"Code fence count: {len(fences)} (should be even)")

lines = content.split("\n")
for i, line in enumerate(lines[-15:], start=len(lines)-14):
    print(f"{i}: {repr(line)}")
