"""Helper functions and classes for managing and moving RO-Crate ingestible dataclasses.
"""

from typing import Any, Dict, List

from slugify import slugify


def convert_to_property_value(
    json_element: Dict[str, Any] | Any, name: str
) -> Dict[str, Any]:
    """convert a json element into property values for compliance with RO-Crate

    Args:
        json_element (Dict[str, Any] | Any): the json to turn into a Property value
        name (str): the name for the partent json

    Returns:
        Dict[str, Any]: the input as a property value
    """
    if not isinstance(json_element, Dict) and not isinstance(json_element, List):
        return {"@type": "PropertyValue", "name": name, "value": json_element}
    if isinstance(json_element, List):
        return {
            "@type": "PropertyValue",
            "name": name,
            "value": [
                convert_to_property_value(item, slugify(f"{name}-{index}"))
                for index, item in enumerate(json_element)
            ],
        }
    json_element["@type"] = "PropertyValue"
    json_element["name"] = name
    for key, value in json_element.items():
        if isinstance(value, (Dict, List)):
            json_element[key] = convert_to_property_value(value, key)
    return json_element
