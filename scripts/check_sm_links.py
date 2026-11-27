import re, os

path = '/workspace/project/github/public-repository/cloud-native-guide/automation/terraform/state-migration-procedure.md'
text = open(path, encoding='utf-8', errors='replace').read()

# Remove code fences
text_no_fences = re.sub(r'^```.*?^```', '', text, flags=re.S | re.M)

# Find markdown links
LINK = re.compile(r'\]\(([^)\s]+)(?:\s+\"[^\"]*\"\\))?\)')
print('All markdown links found:')
for match in LINK.finditer(text_no_fences):
    target = match.group(1)
    print(f'  {target}')

# Check anchors
HEADING = re.compile(r'^#{1,6}\s+(.*)$', re.M)
def slug(text):
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)
    text = text.strip().lower()
    text = re.sub(r'[^\\w\\s-]', '', text)
    return re.sub(r'\s+', '-', text)

headings = re.findall(HEADING, text, re.M)
print(f'\nHeadings in file: {headings}')