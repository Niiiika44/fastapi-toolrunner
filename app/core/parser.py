import yaml
import json


class YAMLLoader(yaml.SafeLoader):
    pass


YAMLLoader.add_constructor('!JetMemoryBlock', yaml.SafeLoader.construct_mapping)
YAMLLoader.add_constructor('!PartitionMemoryBlocks', yaml.SafeLoader.construct_mapping)
YAMLLoader.add_constructor('!JetMemoryBlockSharing', yaml.SafeLoader.construct_mapping)
YAMLLoader.add_constructor('!JetMemoryBlockRef', yaml.SafeLoader.construct_mapping)
YAMLLoader.add_constructor('!AMP_PhysMemoryBlockGroupRef', yaml.SafeLoader.construct_mapping)
YAMLLoader.add_constructor('!float', yaml.SafeLoader.construct_yaml_float)
YAMLLoader.add_constructor('!double', yaml.SafeLoader.construct_yaml_float)


def parse_yaml(content: str) -> dict:
    return yaml.load(content, Loader=YAMLLoader)


def parse_json(content: str) -> dict:
    return json.loads(content)
