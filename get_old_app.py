import codecs

with codecs.open('old_app.py', 'r', encoding='utf-16') as f:
    lines = f.readlines()

start = -1
for i, l in enumerate(lines):
    if 'def _render_multi_comparison' in l:
        start = i
        break

if start != -1:
    end = len(lines)
    for i, l in enumerate(lines[start+1:]):
        if 'def ' in l:
            end = start + 1 + i
            break
    
    with open('temp.py', 'w', encoding='utf-8') as f:
        f.writelines(lines[start:end])
