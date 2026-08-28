import zipfile
from pathlib import PurePosixPath

MEMIN_FILENAME = "memin.yaml"


def find_root(archive: zipfile.ZipFile) -> str | None:
    candidates = [
        name
        for name in archive.namelist()
        if PurePosixPath(name).name == MEMIN_FILENAME
    ]
    if not candidates:
        return None
    shallowest = min(candidates, key=lambda name: (name.count("/"), name))
    return shallowest[: -len(MEMIN_FILENAME)]


def members_under(archive: zipfile.ZipFile, root: str) -> list[tuple[str, str]]:
    return [
        (name, name[len(root):])
        for name in archive.namelist()
        if name.startswith(root)
    ]
