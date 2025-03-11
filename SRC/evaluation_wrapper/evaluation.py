# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from __future__ import annotations
from collections.abc import Mapping
from typing import Callable, Union, Tuple, Literal, get_origin, get_args, Optional
import json
import database_management.string_helper as sh

class EvalError: 
    WRONG_REQ = "Wrong Requirement Evaluated"
    OK = "ok"
    NO_PROPOSAL = "No Proposed Requirement given"
    FORMAT_ERROR = "Wrong Format"


class Evaluation(Mapping):
    """
    Wrapper class to handle and validate requirement evaluations based on a desired format schema and parsing functions.
    The class behaves like a dictionary with additional features to validate and parse the evaluation content. 
    
    Attributes
    ==========

        content (dict): The evaluation content to be validated.
        dict (dict): A dictionary containing the content and validation error status.
        rating_parser (Callable[[Evaluation], Union[int, float]]): A function to parse the rating from the evaluation.
        proposed_req_parser (Callable[[Evaluation], str]): A function to parse the proposed requirement from the evaluation.
        no_proposal_condition (Callable[[Evaluation], bool]): A function to determine if there is no proposal condition.
    
    Key Methods
    ===========
        
        **_check_evaluation**
            Validates the evaluation content based on the format dummy, input requirement, and no proposal condition.
        **is_valid**
            Checks if the evaluation is valid, meaning the format is correct and the input requirement equals to the evaluated requirement.
        **is_complete**
            Checks if the evaluation is complete, meaning it is valid and a proposed requirement is given.
        **parse_rating**
            Parses and extracts the rating from the evaluation if it is valid.
        **get_proposed_requirement**
            Gets the proposed requirement if the evaluation is complete or valid.
    """
    def __init__(
        self, content:dict, input_requirement:Optional[str], format_dummy:dict,
        rating_parser:Callable[[Evaluation], Union[int, float]],
        proposed_req_parser:Callable[[Evaluation], str],
        no_proposal_condition:Callable[[Evaluation], bool]
    ):
        self.content:dict = content
        self.dict = {
            "message": content, 
            "error": self._check_evaluation(
                format_dummy, input_requirement, no_proposal_condition
            )
        }
        self.rating_parser = rating_parser
        self.proposed_req_parser = proposed_req_parser
        
        
    def _check_format_recursive(self, d:dict, dummy:dict, sub_key:str="top_level") -> Tuple[bool, Union[str, None]]:
        if not isinstance(d, dict):
            return False, f"Expected dict, got {type(d)} at {sub_key}"
        for key, value in dummy.items():
            if key not in d:
                return False, f"Key {key} not found at {sub_key}"
            if get_origin(value) is Union:
                value = get_args(value)
            if isinstance(value, dict):
                is_valid, msg = self._check_format_recursive(d[key], value, key)
                if not is_valid:
                    return False, msg
            elif not isinstance(d[key], value):
                return False, f"Expected {value}, got {type(d[key])} at {key}"
        return True, None
    
    def _check_evaluation(
        self, format_dummy:dict,
        input_requirement:Optional[str],
        no_proposal_condition:Callable[[Evaluation], bool]
    ) -> str:
        format_is_valid, info = self._check_format_recursive(self.content, format_dummy)
        if not format_is_valid:
            error = EvalError.FORMAT_ERROR
        elif input_requirement and (sh.normalize_string(input_requirement) != sh.normalize_string(self.get("requirement"))):
            error = EvalError.WRONG_REQ
        elif no_proposal_condition(self):
            error = EvalError.NO_PROPOSAL
        else:
            error = EvalError.OK    
        return {"type": error, "info": info}
    
    def is_valid(self):
        return self["error"]["type"] in [EvalError.OK, EvalError.NO_PROPOSAL]
    
    def is_complete(self) -> bool:
        return self["error"]["type"] == EvalError.OK

    def parse_rating(self):
        if not self.is_valid():
            return
        return self.rating_parser(self)

    def get_proposed_requirement(self, default:Literal["requirement", None]=None):
        if self.is_complete():
            return self.proposed_req_parser(self)
        if self.is_valid() and default:
            return self.content.get(default)
        return None
        
    def __getitem__(self, key):
        try:
            return self.dict[key]
        except (KeyError, AttributeError):
            return self.content[key]
    
    def __setitem__(self, key, value):
        self.dict[key] = value

    def __delitem__(self, key):
        del self.dict[key]

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def __str__(self):
        return json.dumps(self.dict, indent=4)
    
    def __repr__(self):
        return repr(self.dict)
    
    def items(self):
        return self.dict.items()
        
    

