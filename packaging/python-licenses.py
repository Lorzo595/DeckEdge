"""Export package versions and full licenses, without local build paths."""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import sys

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
packages = []
for dist in sorted(metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
    name, version = dist.metadata['Name'], dist.version
    folder = out / f'{name}-{version}'
    folder.mkdir(exist_ok=True)
    (folder / 'METADATA.txt').write_text(dist.read_text('METADATA') or '', encoding='utf-8')
    for file in dist.files or []:
        if '.dist-info' in str(file) and any(part.lower().startswith(('license', 'licence', 'copying', 'notice', 'authors', 'copyright')) for part in file.parts):
            source = dist.locate_file(file)
            if source.is_file():
                target = folder.joinpath(*file.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    packages.append({'name': name, 'version': version, 'license': dist.metadata.get('License-Expression') or dist.metadata.get('License'), 'project_urls': dist.metadata.get_all('Project-URL', [])})
(out.parent.parent / 'PYTHON-PACKAGES.json').write_text(json.dumps(packages, ensure_ascii=False, indent=2), encoding='utf-8')
