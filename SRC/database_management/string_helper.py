import re
import json
from typing import List, Callable

def remove_non_utf_8_characters(s:str):
    """
    Remove non-UTF-8 characters from a given string.

    Args:
        s (str): The input string from which non-UTF-8 characters need to be removed.

    Returns:
        str: A new string with all non-UTF-8 characters removed.
    """
    non_utf8_pattern = re.compile(r'[^\x00-\x7F]')
    return non_utf8_pattern.sub("", s)

def normalize_string(s: str) -> str:
    """
    Normalize a string by removing non-alphanumeric characters, converting to lowercase, and stripping leading/trailing whitespace.

    Args:
        s (str): The input string to be normalized.

    Returns:
        str: The normalized string.

    Raises:
        TypeError: If the input is not a string.
    """
    try:
        return re.sub(r'\W+', ' ', s).strip().lower()
    except TypeError:
        return s
    
def format_dict(d:dict, escape_brackets:bool=True):
    """
    Converts a dictionary to an indented JSON string.

    Args:
        d (dict): The dictionary to format.
        escape_brackets (bool, optional): If True, escapes curly brackets by doubling them. Defaults to True.

    Returns:
        str: The formatted JSON string.
    """
    json_str = json.dumps(d, indent=4)
    if escape_brackets:
        json_str = json_str.replace("{", "{{").replace("}", "}}")
    return json_str

def format_str_list(items:List[str], separator:str="\n", item_wrapper:Callable[[str], str]=lambda x: x, indent:int=0):
    """
    Formats a list of strings into a single string with specified formatting options.

    Args:
        items (List[str]): The list of strings to format.
        separator (str, optional): The separator to use between items. Defaults to "\\n".
        item_wrapper ((str) -> str, optional): A function to wrap each item. Default: returns the item unchanged.
        indent (int, optional): The number of spaces to indent each item. Defaults to 0.

    Returns:
        str: The formatted string.
    """
    return separator.join(" "*indent + item_wrapper(item) for item in items if item)

def double_new_lines(items:List[str]):
    """
    Takes a list of strings and returns a single string with each item separated by double new lines.

    Args:
        items (List[str]): A list of strings to be formatted.

    Returns:
        str: A single string with each item from the list separated by double new lines.
    """
    return format_str_list(items, "\n\n")

def bullet_points(items: List[str], indent: int = 0):
    """
    Formats a list of strings into a bullet-point list with optional indentation.

    Args:
        items (List[str]): The list of strings to be formatted as bullet points.
        indent (int, optional): The number of spaces to indent each bullet point. Defaults to 0.

    Returns:
        str: A formatted string with each item in the list as a bullet point, indented as specified.
    """
    
    return format_str_list(
        items, 
        item_wrapper=lambda x: f"- {x}",
        indent=indent
    )