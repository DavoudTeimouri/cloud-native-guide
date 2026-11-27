import re
import sys
import os
os.chdir('/workspace/project/github/public-repository/cloud-native-guide')
HEADING = re.compile(r'^#{1,6}\s+(.*)$')
EXPLICIT_ID = re.compile(r'<a\s+(?:id|name)="([^"]+)"', re.I)

def slug(text):
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[\*_]{1,2}([^*_]+)[\*_]{1,2}', r'\1', text)
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'\s+', '-', text)

def anchors(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    found, seen = set(), {}
    for match in HEADING.finditer(text):
        base = slug(match.group(1))
        n = seen.get(base, 0)
        seen[base] = n + 1
        found.add(base if n == 0 else f'{base}-{n}')
    found.update(EXPLICIT_ID.findall(text))
    return found

print(anchors('storage/pvc-lifecycle.md'))