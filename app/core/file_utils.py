from app.core.enums import InputType


def detect_file_type(filename: str) -> str:
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        return InputType.YAML
    if filename.endswith(".json"):
        return InputType.JSON
    return ""
