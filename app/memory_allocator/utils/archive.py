import zipfile
from pathlib import PurePosixPath

MEMIN_FILENAME = "memin.yaml"


def find_root(archive: zipfile.ZipFile) -> str | None:
    candidates = [
        entry.filename
        for entry in archive.infolist()
        if not entry.is_dir() and PurePosixPath(entry.filename).name == MEMIN_FILENAME
    ]
    if not candidates:
        return None
    shallowest = min(candidates, key=lambda name: (name.count("/"), name))
    return shallowest[: -len(MEMIN_FILENAME)]


def members_under(archive: zipfile.ZipFile, root: str) -> list[tuple[str, str]]:
    return [
        (entry.filename, entry.filename[len(root):])
        for entry in archive.infolist()
        if not entry.is_dir() and entry.filename.startswith(root) and entry.filename != root
    ]
