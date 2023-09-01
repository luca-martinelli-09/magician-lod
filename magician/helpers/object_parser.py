from jsonmerge import merge
from typing import Dict, Any
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from typing import Tuple

from . import Urifier, Templater


class ObjectParser():
    """
    This class is used to add to the graph objects and their predicates. It's the core of the program.
    """

    __predicates_map: Dict[str, dict] = None
    __templater: Templater = None
    __urifier: Urifier = None
    __object_templates: None | dict = None
    __g: Graph = None

    def __init__(self, g: Graph, predicates_map: Dict[str, dict] | None, templater: Templater, urifier: Urifier,
                 object_templates: dict = None) -> None:
        self.__g = g
        self.__predicates_map = predicates_map
        self.__templater = templater
        self.__urifier = urifier
        self.__object_templates = object_templates

    def __validate_condition(self, schema: dict, data: dict) -> bool:
        conditions = schema.get("if")

        if conditions is None:
            return True

        if not isinstance(conditions, list):
            conditions = [conditions]

        for condition in conditions:
            validation = self.__templater.fill(condition, data).strip()

            if len(validation) <= 0 or validation.lower() == 'false':
                return False

        return True

    def __parse_predicate(self, predicate_map: dict, predicate_subject: URIRef, data: dict) -> list[Tuple[
            URIRef, URIRef | Literal]]:
        predicate_object = None

        # Get the default value, if it's exists.
        default_value = predicate_map.get("default_value")

        # Get the key where the value was stored.
        value_key = {
            "literal": "value",
            "ref": "ref"
        }

        # Get the typology of the predicate to add
        predicate_type: str = predicate_map.get("type")

        # Get the value, (default one if not specified) and fill it with the data using the templator.
        value = self.__templater.fill(
            predicate_map.get(
                value_key.get(predicate_type, "value"),
                default_value
            ),
            data
        )

        # Create a list of values, in order to use also splits and iterators
        values = [value]

        # If split_on and split_by are specified, split the content and use it for the values.
        has_split = False
        if predicate_map.get("split_on") and predicate_map.get("split_by"):
            split_on = self.__templater.fill(
                predicate_map.get("split_on"), data
            )
            values = split_on.split(predicate_map.get("split_by"))
            has_split = True

        # Do the same if specified an iterate_on_attribute
        if predicate_map.get("iterate_on_attribute"):
            values = data.get(predicate_map.get("iterate_on_attribute"), [])
            has_split = True

        # Conditions to continue
        if not self.__validate_condition(predicate_map, data):
            return []

        # Store the list of tuples
        tuples = []

        # Iterate over the values
        for val in values:
            # Add the split information on the data dictionary, in order to use it in the templater
            # When using iterate_on_attribute, if "val" is a dictionary in the templater we can also use subkeys, like {{_split.subkey}}
            split_data = data.copy()
            if has_split:
                split_data["__split"] = val

            # TYPE IS LITERAL
            if predicate_type == "literal":
                # Get the language and the data type
                # The datatypes are the one specified in the XSD namespace
                datatype = predicate_map.get("datatype")
                language = predicate_map.get("language")

                # Create the literal
                if val is not None and val != '':
                    predicate_object = Literal(
                        val,
                        lang=language if not datatype else None,
                        datatype=self.__urifier.get_uri(
                            "xsd:" + datatype
                        ) if datatype and not language else None
                    )

            # TYPE IS A REFERENCE
            if predicate_type == "ref" or predicate_type == "reverse_ref":
                # Get the default prefix, if specified
                default_prefix = predicate_map.get("default_prefix")

                predicate_object = None
                # If the value is specified, create the URI using the templater, the urifier
                # Add the default prefix if noone is specified.
                if val is not None:
                    if default_prefix and not val.find(":") >= 0:
                        val = default_prefix + ":" + val

                    predicate_object = self.__urifier.get_uri(self.__templater.fill(
                        val, split_data
                    ))

            # TYPE IS AN OBJECT
            if predicate_type == "object" or predicate_type == "reverse_object":
                # Create an object and get its uri
                predicate_object = self.add_object(
                    predicate_map.get("object"), split_data
                )

            # Add the tuple of object and subject. If its reversed, reverse subject with object
            if predicate_type and predicate_type.startswith("reverse_"):
                tuples.append((predicate_object, predicate_subject))
            else:
                tuples.append((predicate_subject, predicate_object))

        return tuples

    def add_object(self, object: dict, data: dict = {}) -> URIRef | None:
        # Merge with templates
        if self.__object_templates is not None:
            object_templates = object.get("template")
            if object_templates and not isinstance(object_templates, list):
                object_templates = [object_templates]

            if object_templates:
                for object_template in object_templates:
                    object = merge(
                        self.__object_templates.get(
                            object_template, {}
                        ), object
                    )

        # Generate the URI using the templater and the urifier
        object_uri = self.__urifier.get_uri(self.__templater.fill(
            object.get("uri"), data
        ))

        # Check if can create the object or not
        if not self.__validate_condition(object, data):
            return None

        # Get the object types
        object_types = object.get("as")
        if object_types is not None:
            if not isinstance(object_types, list):
                object_types = [object_types]

            # And initialize the object
            for object_type in object_types:
                self.__g.add((
                    object_uri,
                    RDF.type,
                    self.__urifier.get_uri(
                        self.__templater.fill(object_type, data)
                    )
                ))

        # Add the predicates
        predicates: dict = object.get("predicates")
        if predicates is not None:
            for predicate, predicate_value in predicates.items():
                self.add_predicate(
                    predicate, predicate_value, object_uri, data
                )

        # return the object URI
        return object_uri

    def add_predicate(self, predicate: str, value: list | dict | Any, subject_uri: URIRef, data: dict = {}) -> None:
        # Make a list of values by default
        if not isinstance(value, list):
            value = [value]

        # Divide predicates by comma
        predicates = predicate.split(",")

        for predicate in predicates:
            # Merge with mapped predicates
            predicate_map: dict = merge(
                {
                    "default_value": "{{__value}}",
                    "type": "literal"
                },
                self.__predicates_map.get(predicate, {})
            )

            # Iterate over values
            for map in value:
                predicate_data = data.copy()

                # Enhance the data with other info, like the value and the other attributes
                if isinstance(map, dict):
                    for k, v in map.items():
                        predicate_data["__" + k] = v
                elif isinstance(map, str):
                    predicate_data["__value"] = self.__templater.fill(
                        map, predicate_data
                    )

                # Merge the map with the predicate_map
                if isinstance(map, dict):
                    map = merge(predicate_map, map)
                else:
                    map = predicate_map

                # Get the uri of the predicate
                predicate_uris = map.get("uri", predicate)
                if not isinstance(predicate_uris, list):
                    predicate_uris = [predicate_uris]

                # Add the tuple
                for predicate_uri in predicate_uris:
                    # Get the predicate uri
                    predicate_uri = self.__urifier.get_uri(
                        self.__templater.fill(predicate_uri, predicate_data)
                    )

                    # Get the tuples of subjects and objects
                    tuples = self.__parse_predicate(
                        map, subject_uri, predicate_data
                    )

                    # And add them to the graph
                    for predicate_subject, predicate_object in tuples:
                        if predicate_subject is not None and predicate_object is not None:
                            self.__g.add((
                                predicate_subject, predicate_uri, predicate_object
                            ))
