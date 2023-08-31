from rdflib import Graph
from rdflib.namespace import DCTERMS
from typing import Dict
from pathlib import Path


class Grapher:
    """
    This class initialize and save the graph with all the binding specified in the schema, and the default ones.
    """

    __namespace = None
    __bindings = None
    __filename = None
    __formats = None

    def __init__(self,
                 namespace: str,
                 bindings: Dict[str, str],
                 filename: str = "export",
                 formats: list[str] = ["xml"]
                 ):
        self.__bindings = bindings

        # Set namespace
        if namespace is not None:
            if not namespace.endswith("/"):
                namespace += "/"

            self.__namespace = namespace

        # Set export info
        self.__filename = filename
        self.__formats = formats

    def create(self) -> Graph:
        """
        Initialize a graph with all default and required bindings.
        """

        # Initialize graph
        g = Graph(bind_namespaces="rdflib")

        if self.__namespace:
            g.bind("", self.__namespace)

        # Bindings
        g.bind("dct", DCTERMS)
        if self.__bindings:
            for binding, namespace in self.__bindings.items():
                g.bind(binding, namespace)

        return g

    def save(self, g: Graph) -> None:
        """
        Serialize the graph and save it in different formats
        """

        # Map the extension from the format
        extensions = {
            "turtle": "ttl",
            "xml": "rdf",
        }

        # Create folder if not exists
        Path(self.__filename).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        for format in self.__formats:
            extension = extensions.get(format, "xml")

            with open("{}.{}".format(self.__filename, extension), "w", encoding="utf-8") as fp:
                fp.write(g.serialize(format=format))
