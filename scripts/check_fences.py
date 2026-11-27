import re

path = "/workspace/project/github/public-repository/cloud-native-guide/storage/ceph/auto-test-ceph-performance.md"
with open(path) as f:
    content = f.read()

fences = re.findall(r"^```", content, re.M)
print(f"Code fence count: {len(fences)}")

lines = content.split("\n")
for i, line in enumerate(lines[-25:], start=len(lines)-24):
    print(f"{i}: {repr(line)}")
