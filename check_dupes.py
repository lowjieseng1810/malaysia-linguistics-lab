import pathlib, re, collections
text = pathlib.Path('c:/Users/ADMIN/Desktop/malaysian_minority_languages_explorer/static/js/earth-globe.js').read_text(encoding='utf-8')
counts = collections.Counter(re.findall(r'\b(?:let|const|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\b', text))
for name, count in sorted(counts.items()):
    if count > 1:
        print(name, count)
