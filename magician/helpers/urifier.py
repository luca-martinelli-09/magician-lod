from rdflib import Namespace, URIRef
from typing import Dict, Tuple, Generator, List


class Urifier:
    """
    This class generate URIs expanding namespaces bindings and adding the default namespace.
    """

    __namespaces: Dict[str, str] = {}
    __namespace: Namespace | None = ""

    def __init__(self, namespaces: Generator[Tuple[str, URIRef], None, None] | List[Tuple[str, URIRef | str]], namespace: str | None) -> None:
        # Add bindings
        for binding, bind_namespace in namespaces:
            self.__namespaces[binding] = str(bind_namespace)

        # Set namespace
        if namespace:
            if not namespace.endswith("/"):
                namespace += "/"

            self.__namespace = Namespace(namespace)

    def __expand_ns(self, uri: str) -> str:
        """
        Expand URIs with namespace bindings.
        """

        binding = uri[slice(0, uri.find(":"))]
        if binding in self.__namespaces:
            uri = uri.replace(f"{binding}:", self.__namespaces.get(binding))

        return uri

    def get_uri(self, uri: str) -> URIRef:
        """
        Generate URIRef.
        """

        uri = self.__expand_ns(uri)

        if uri.startswith("http"):
            return URIRef(uri)

        if uri.startswith("/") or uri.startswith(":"):
            uri = uri[1:]

        return URIRef(self.__namespace + uri)
