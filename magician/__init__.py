from jsonmerge import merge
from pathlib import Path
from .helpers import loadSchema, Grapher, Urifier, Templater, ObjectParser, Sourcer
from alive_progress import alive_bar


def parse_schema(schema_file):
    # Load the schema
    print("\n\n🔬 LOADING SCHEMA: " + schema_file)

    schema_parent = Path(schema_file).parent.absolute()
    schema = loadSchema(schema_file)

    # Export information
    export: dict = schema.get('export', {})

    # Merge export information with the default one
    export = merge({
        'parent': './',
        'name': 'export',
        'formats': ['xml']
    }, export)
    export_path = schema_parent.joinpath(export.get("parent"))
    export_filename = export_path.joinpath(export.get('name'))
    export_formats = export.get('formats')

    # Initialize the templater
    templater = Templater()

    # Initialize the grapher
    grapher = Grapher(
        namespace=schema.get('namespace'),
        bindings=schema.get('prefixes'),
        filename=export_filename,
        formats=export_formats,
    )

    # Create the graph
    g = grapher.create()

    # Initialize the urifier
    urifier = Urifier(g.namespaces(), schema.get('namespace'))

    # Predicator
    predicator = ObjectParser(
        g,
        schema.get("predicates_map", {}),
        templater,
        urifier,
        schema.get("object_templates")
    )

    # Parse individuals
    print("\n🦠 PARSING INDIVIDUALS")

    individuals: dict = schema.get('individuals', {})
    for individual_uri, individual in individuals.items():
        if isinstance(individual, dict):
            individual["uri"] = individual.get("uri", individual_uri)

            print("\t🦠 Adding object: " + individual_uri)
            predicator.add_object(individual)

    # Parse sources
    sourcer = Sourcer(schema_parent)

    print("\n\n📜 CREATING FROM SOURCES")
    for source in schema.get("sources", []):
        # If not map specified or source is not a dict, go on
        if not isinstance(source, dict) or not source.get("object"):
            continue

        # Get the data from the sourcer, passing all except for the object map
        print("\n📜 Loading data from source: " + source.get("source"))
        source_objects = None
        source_objects = sourcer.get_data(
            {k: source[k] for k in source if not k == "object"}
        )

        object_schemas = source.get("object")
        if isinstance(object_schemas, dict):
            object_schemas = [object_schemas]

        # Create the objects passing the map and the data
        if source_objects is not None and isinstance(source_objects, list):
            total_objects = len(source_objects) * len(object_schemas)
            with alive_bar(total_objects, title="⚗️ Adding objects") as bar:
                for object_schema in object_schemas:
                    for i, source_object in enumerate(source_objects):
                        source_object["__index"] = i

                        predicator.add_object(
                            object_schema, source_object
                        )

                        # Update progress bar
                        bar()
        else:
            print(f"\t😱 Oh no! Cannot get data!")

    # Save the graph
    print("💾 Saving the RDF graph")
    grapher.save(g)
