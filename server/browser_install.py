"""Deploy the extension bundled with the verified Windows executable."""
import json
from pathlib import Path
import shutil


def install_browser(source, state):
    source, state = Path(source), Path(state)
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('manifest_version') != 3:
        raise ValueError('Invalid bundled extension')
    target, staged, backup = (state / name for name in ('browser', 'browser.pending', 'browser.previous'))
    # Recover an interrupted directory swap before preparing another update.
    if backup.exists() and not target.exists():
        backup.rename(target)
    files = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    if target.exists() and all((target / name).is_file() and (target / name).read_bytes() == data for name, data in files.items()):
        if backup.exists(): shutil.rmtree(backup)
        return manifest['version']
    if staged.exists(): shutil.rmtree(staged)
    staged.mkdir(parents=True)
    try:
        for name, data in files.items(): (staged / name).write_bytes(data)
        if backup.exists(): shutil.rmtree(backup)
        if target.exists(): target.rename(backup)
        try:
            staged.rename(target)
        except OSError:
            if backup.exists(): backup.rename(target)
            raise
        if backup.exists(): shutil.rmtree(backup)
    finally:
        if staged.exists(): shutil.rmtree(staged)
    return manifest['version']
