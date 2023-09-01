from pathlib import Path
import polars as pl
import requests
import xml.etree.ElementTree as ET
from typing import Dict
import re


class Sourcer():
    """
    This class get the data from the different sources specified in the schema.
    """

    __abs_path = None
    __df_formats = ["csv", "excel"]

    def __init__(self, abs_path: Path):
        self.__abs_path = abs_path

    def __get_string(self, source: str, offline: bool):
        if offline:
            return open(source).read()

    def __xml_to_dict(self, xml_element: ET.Element, namespaces: Dict[str, str] = {}) -> dict:
        result = {}

        # Invert namespace mapping
        inverted_namespaces = {v: k for k, v in namespaces.items()}

        for child in xml_element:
            child_tag = child.tag

            # Replace namespaces
            try:
                match = re.search("^{(\S+)}", child_tag)
                if match and match.group(1) and match.group(1) in inverted_namespaces:
                    child_tag = re.sub("^{(\S+)}",
                                       lambda match: (
                                           inverted_namespaces[
                                               match.group(1)
                                           ] + ":"
                                       ),
                                       child_tag
                                       )
            except:
                pass

            # Three possibilities: no children, multiple children, one child
            if len(child) == 0:
                result[child_tag] = child.text
            else:
                if child_tag in result and isinstance(result[child_tag], dict):
                    result[child_tag] = [result[child_tag]]
                elif not child_tag in result:
                    result[child_tag] = self.__xml_to_dict(child, namespaces)

                if isinstance(result[child_tag], list):
                    result[child_tag].append(
                        self.__xml_to_dict(child, namespaces))

        return result

    def __parse_xml(self, source: str, schema: dict) -> dict:
        """
        Load an XML
        """

        data = self.__xml_to_dict(
            ET.fromstring(source),
            schema.get('namespaces', {})
        )

        return data

    def __parse_df(self, source: str, format: str, schema: dict, as_df: bool = False) -> dict | pl.DataFrame | None:
        """
        Load a DataFrame
        """

        if format == "csv":
            df = pl.read_csv(source, infer_schema_length=0)
        elif format == "xls":
            df = pl.read_excel(source)

        # Join with other dataframes
        joins_info = schema.get("join")
        if not isinstance(joins_info, list):
            joins_info = [joins_info]

        for join_info in joins_info:
            if join_info and isinstance(join_info, dict) and join_info.get("left_on") and join_info.get("right_on"):

                # Get the dataframe to join
                join_data = None
                try:
                    join_data = self.get_data(join_info, True)
                except:
                    pass

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

        if schema.get("group_by") is not None and schema.get("group_agg") is not None:
            group_by = schema.get("group_by")
            group_agg: dict = schema.get("group_agg")

            if not isinstance(group_by, list):
                group_by = [group_by]

            aggregations = []

            for col, func in group_agg.items():
                pl_col = pl.col(col)

                if func == "sum":
                    pl_col = pl_col.cast(pl.Float64).sum().cast(str)
                elif func == "count":
                    pl_col = pl_col.count().cast(str)
                elif func == "avg":
                    pl_col = pl_col.cast(pl.Float64).mean().cast(str)

                aggregations.append(pl_col)

                print(func)

            df = df.groupby(group_by).agg(aggregations)

        print(df)

        return df if as_df else df.to_dicts()

    def get_data(self, schema: dict, as_df: bool = False) -> list | pl.DataFrame | None:
        """
        Download the data and uniform it, using different sources types (json, text, csv, kml, online or offline data).
        """

        source: str = schema.get("source")
        format: str = schema.get("format")

        if not source or not format:
            return None

        online = source.startswith("http")
        offline = not online

        if offline:
            source = self.__abs_path.joinpath(source)

        # Initialize data
        data = None

        # Format is a DataFrame format (csv, excel)
        if format in self.__df_formats:
            return self.__parse_df(source, format, schema, as_df)

        if as_df:
            return None

        # Get the string to parse
        source_string = self.__get_string(source, offline)

        # Format is XML
        if format == "xml":
            data = self.__parse_xml(source_string, schema)

        # Get the point where the list start (subkeys can be used, eg. key.subkey)
        if schema.get("root"):
            root: str = schema.get("root", '')
            roots = root.split(".")

            for root in roots:
                if isinstance(data, dict):
                    data = data.get(root)

        return data
