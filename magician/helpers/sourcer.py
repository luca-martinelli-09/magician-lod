from pathlib import Path
import polars as pl


class Sourcer():
    """
    This class get the data from the different sources specified in the schema.
    """

    __abs_path = None

    def __init__(self, abs_path: Path):
        self.__abs_path = abs_path

    def get_data(self, data: dict, as_df: bool = False) -> list | pl.DataFrame | None:
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

        # Join the dataframe with other data
        joins_info = data.get("join")
        if not isinstance(joins_info, list):
            joins_info = [joins_info]

        for join_info in joins_info:
            if join_info and isinstance(join_info, dict) and join_info.get("left_on") and join_info.get("right_on"):
                join_data = self.get_data(join_info, True)

                if not join_data is None:
                    try:
                        df = df.join(
                            join_data,
                            how="left",
                            left_on=join_info.get("left_on"),
                            right_on=join_info.get("right_on")
                        )
                    except:
                        pass

        return df.to_dicts() if not as_df else df
