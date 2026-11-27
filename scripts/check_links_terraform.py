import re, os

BASE = '/workspace/project/github/public-repository/cloud-native-guide'
LINK = re.compile(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HEADING = re.compile(r'^#{1,6}\s+(.*)$', re.M)
EXPLICIT_ID = re.compile(r'<a\s+(?:id|name)="([^"]+)"', re.I)

def slug(text):
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'\s+', '-', text)

def anchors(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    found, seen = set(), {}
    for match in HEADING.finditer(text):
        base = slug(match.group(1))
        n = seen.get(base, 0)
        seen[base] = n + 1
        found.add(base if n == 0 else f'{base}-{n}')
    found.update(EXPLICIT_ID.findall(text))
    return found

# Check just the state-migration-procedure.md file
path = '/workspace/project/github/public-repository/cloud-native-guide/automation/terraform/state-migration-procedure.md'
text = open(path, encoding='utf-8', errors='replace').read()
text_no_fences = re.sub(r'^```.*?^```', '', text, flags=re.S | re.M)

print('=== Checking links in state-migration-procedure.md ===')
for match in LINK.finditer(text_no_fences):
    target = match.group(1)
    print(f'Link: {target}')
    
    if target.startswith(('http://', 'https://', 'mailto:', 'tel:')):
        print(f'  -> Skipping external URL')
        continue
    if '{' in target or target.startswith('#'):
        if target.startswith('#') and len(target) > 1:
            anchor_name = target[1:]
            dest_anchors = anchors(path)
            if anchor_name not in dest_anchors:
                print(f'  -> MISSING ANCHOR: {target}')
            else:
                print(f'  -> Anchor OK: {target}')
        else:
            print(f'  -> Anchor/empty: {target}')
        continue
    
    file_part, _, anchor = target.partition('#')
    dest = os.path.normpath(os.path.join(os.path.dirname(path), file_part))
    print(f'  -> File part: {file_part}, anchor: {anchor}, dest: {dest}')
    
    if not os.path.exists(dest):
        print(f'  -> MISSING FILE: {dest}')
    elif anchor and dest.endswith('.md') and anchor not in anchors(dest):
        print(f'  -> MISSING ANCHOR in target: {anchor}')
    else:
        print(f'  -> Link OK')

print()
print('=== Anchors in file ===')
print(anchors(path))