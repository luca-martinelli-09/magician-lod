import yaml
from jsonmerge import merge
from pathlib import Path

from .templater import Templater
from .grapher import Grapher
from .urifier import Urifier
from .object_parser import ObjectParser
from .sourcer import Sourcer


def loadSchema(path: str | Path) -> dict:
    """
    Load a schema yaml file, extending the imported files defined into the schema.

    When patterns are joined, arrays are added, objects are overwritten.
    """

    # Convert the path into an absolute path
    path = Path(path).absolute() if path else None

    # If the file not exists, return None
    if path is None or not path.exists():
        return None

    # Load the schema
    schema: dict = yaml.full_load(path.open())

    # Check if the schema needs to be extended
    if schema.get('extends'):
        # Get the path
        extends_path = Path(schema.get('extends'))

        # And convert it to absolute path if it is not absolute
        if not extends_path.is_absolute():
            extends_path = path.parent.joinpath(extends_path)

        # Recursively load the schema and merge it with the first one
        extends_schema = loadSchema(extends_path)
        schema: dict = merge(extends_schema, schema)

        # Remove the extend property
        del schema['extends']

    return schema
