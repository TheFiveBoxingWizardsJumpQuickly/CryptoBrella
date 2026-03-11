import importlib
import re


def convert_to_3wa(apikey, latitude, longitude, language):
    what3words = importlib.import_module("what3words")
    geocoder = what3words.Geocoder(apikey)
    return geocoder.convert_to_3wa(what3words.Coordinates(latitude, longitude), language=language)


def convert_to_coordinates(apikey, words):
    what3words = importlib.import_module("what3words")
    words = str(words).strip().replace(" ", ".").replace(",", ".").replace("・", ".").replace("。", ".").replace("、", ".").replace("　", ".")
    pattern = re.compile(r"^[^\.]+\.[^\.]+\.[^\.]+$")
    if pattern.search(words):
        geocoder = what3words.Geocoder(apikey)
        return geocoder.convert_to_coordinates(words)
    return {"format error": words + " is not W3W format."}
