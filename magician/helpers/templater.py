import re
from typing import Dict
from slugify import slugify
import urllib.parse
import hashlib
import uuid
from datetime import datetime


class Templater:
    """
    This class is used to fill templates with data. See fill() method for the usage.
    """

    def __get_from_dict(self, data: Dict[str, str | dict], key: str, default: str = '') -> str:
        keys = key.split('.')

        current = data
        for key in keys:
            if not isinstance(current, dict):
                return current

            current = current.get(key, default)

        if isinstance(current, dict):
            return default

        if not current:
            return ""

        return current

    def __remove_suffixes(self, txt: str) -> str:
        return re.sub("[^A-Za-z0-9]+$", "", txt).strip()

    def __exec_func(self, func: str, txt: str) -> str:
        match func:
            case "lower":
                return txt.lower()
            case "upper":
                return txt.upper()
            case "ucfirst":
                return txt.capitalize()
            case "ucword":
                return txt.title()
            case "slug":
                return slugify(txt)
            case "stripall":
                return self.__remove_suffixes(txt)
            case "replace":
                vals = txt.split(";")
                if vals and len(vals) == 3:
                    return re.sub(vals[0].strip(), vals[1].strip(), vals[2].strip()).replace("\\s", " ")
            case "int":
                return str(int(txt))
            case "number":
                return str(int(txt))
            case "float":
                return str(float(txt))
            case "urlencode":
                return urllib.parse.quote(txt)
            case "padright":
                vals = txt.split(";")
                if vals and len(vals) == 3:
                    return vals[2].strip().ljust(int(vals[0].strip()), vals[1].strip())
            case "padleft":
                vals = txt.split(";")
                if vals and len(vals) == 3:
                    return vals[2].strip().rjust(int(vals[0].strip()), vals[1].strip())
            case "md5":
                return hashlib.md5(txt.encode()).hexdigest()
            case "eval":
                return str(eval(txt))
            case "or":
                vals = txt.split(";")
                if vals and len(vals) == 2:
                    if vals[0] and len(vals[0].strip()) > 0:
                        return vals[0].strip()
                    else:
                        return vals[1].strip()
            case _:
                return txt

        return txt

    def __get_special(self, type: str) -> str:
        match type:
            case "uuid":
                return str(uuid.uuid4())
            case "timestamp":
                return str(int(datetime.now().timestamp()))
            case "datetime":
                return datetime.now().isoformat(timespec="seconds")
            case "date":
                return datetime.now().date().isoformat()
            case "time":
                return datetime.now().time().isoformat(timespec="seconds")
            case _:
                return ""

    def fill(self, txt: str, data: Dict[str, str | dict]) -> str:
        """
        Generate a string from a template, also supporting basic function and special variables.

        Data variables:
        - {{key}} -> data[key]
        - {{key.subkey}} -> data[key][subkey]

        Functions:
        - $lower{{string}} -> lowercase
        - $upper{{string}} -> uppercase
        - $ucfirst{{string}} -> uppercase only first letter
        - $ucword{{string}} -> uppercase only the first letter of each word

        - $replace{{target ; replacement ; text}} -> replace target with replacement in text
        - $padright{{length ; fill ; text}} -> pad text on right, using length and fill
        - $padleft{{string}} -> same as padright, but on left

        - $number{{string}} -> convert to number

        - $or{{option1 ; option2}} -> if option1 is void, use option2

        - $slug{{string}} -> create slug

        - $md5{{string}} -> generate md5

        Special variables:
        - {% uuid %} -> generate a random uuid
        - {% timestamp %} -> current timestamp
        - {% datetime %} -> current datetime in ISO format
        - {% date %} -> current date in format YYYY-MM-DD
        - {% time %} -> current time in format HH:mm

        Special variables passed by the Predicator:
        - {{__split}} -> when using iterate_on_attribute or split_on
        - {{__property}} -> any other property passed in the schema
        - {{__index}} -> the index in an array (eg. when creating objects by sources)
        """

        # Variables
        txt = re.sub("{{([^}{$]+)}}",
                     lambda match: self.__get_from_dict(data, match.group(1).strip()).strip(), txt)

        # Special variables
        txt = re.sub("{%([^}{$%]+)%}",
                     lambda match: self.__get_special(match.group(1).strip()).strip(), txt)

        # Functions
        while re.search("\$(\w+){{([^}{$]+)}}", txt):
            txt = re.sub("\$(\w+){{([^}{$]+)}}",
                         lambda match: self.__exec_func(match.group(1), match.group(2).strip()), txt)

        return txt.strip()
