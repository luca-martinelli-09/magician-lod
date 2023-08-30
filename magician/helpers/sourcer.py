from pathlib import Path
import polars as pl

class Sourcer():
    """
    This class get the data from the different sources specified in the schema.
    """

    __abs_path = None

    def __init__(self, abs_path: Path):
        self.__abs_path = abs_path

    def get_data(self, data: dict) -> list:
        """
        Download the data and uniform it, using different sources types (json, text, csv, online or offline data).
        """

        source: str = data.get("source")
        format: str = data.get("format")

        if not source or not format:
            return []

        online = source.startswith("http")

        if not online:
            source = self.__abs_path.joinpath(source)
        
        try:
            df = pl.read_csv(source, infer_schema_length=0)
        except:
            return None

        return df.to_dicts()
