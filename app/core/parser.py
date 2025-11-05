import yaml
import json


def parse_yaml(content: str) -> dict:
    return yaml.load(content, Loader=yaml.SafeLoader)


def parse_json(content: str) -> dict:
    return json.loads(content)
