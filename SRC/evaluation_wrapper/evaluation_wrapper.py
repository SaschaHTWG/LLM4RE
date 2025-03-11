# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from evaluation_wrapper.evaluation import Evaluation
from abc import abstractmethod
from typing import Union, Optional, get_args, Callable
from database_management.db_manager import Metrics as M
from pydantic import create_model

class EvalWrapper:
    """
    A wrapper class for evaluating content based on a given format schema.
    
    Attributes
    ==========

        format_dummy (dict): 
            A dictionary defining the desired format (keys and value types)
        limit_schema_layers (int, optional): 
            The maximum number of nested layers to be considered in an auto-generated schema model.
    
    Key Methods
    ===========
        **__call__**
            Wrapps and parses the given content into an Evaluation object.
        **schema**
            Generates a schema model based on the format_dummy attribute.
        **_rating_parser**
            Abstract method to parse and extract the rating from the evaluation. Must be implemented by subclasses.
        **_proposed_req_parser**
            If exists, extracts the proposed requirement from the evaluation.
        **_no_proposal_condition**
            Checks if there is no proposed requirement in the evaluation.
    """
    def __init__(self, format_dummy:dict, limit_schema_layers:int=None):
        self.format_dummy = format_dummy
        self.limit_schema_layers = limit_schema_layers

    def __call__(self, content:dict, input_requirement:Optional[str]=None, parse_rating_on_init:bool=False) -> Evaluation:
        eval = Evaluation(
            content, input_requirement, self.format_dummy, 
            self._rating_parser, self._proposed_req_parser, self._no_proposal_condition
        )
        if parse_rating_on_init:
            eval.parse_rating()
        return eval
    
    @property
    def schema(self):
        def create_model_from_dict(d:dict, name:str="EvaluationSchema", doc:str=None, layer:int=1):
            field_definitions = {}
            for k, v in d.items():
                if args := get_args(v):
                    if type(None) in args:
                        field_definitions[k] = args
                    else:
                        field_definitions[k] = (*args, ...)
                if isinstance(v, dict):
                    if self.limit_schema_layers is None or layer < self.limit_schema_layers:
                        field_definitions[k] = (create_model_from_dict(v, f"{k}_SubSchema", layer=layer+1), ...)
                    else:
                        field_definitions[k] = (dict, ...)
                else:
                    field_definitions[k] = (v, ...)
            return create_model(name, **field_definitions, __doc__=doc)
        return create_model_from_dict(self.format_dummy, doc=self.__doc__)

    @abstractmethod
    def _rating_parser(self, eval:Evaluation) -> Union[float, int]:
        raise NotImplementedError("Rating parser not implemented")
    
    def _proposed_req_parser(self, eval:Evaluation) -> str:
        return eval.get("proposed_requirement", "no proposal")
    
    def _no_proposal_condition(self, eval:Evaluation) -> bool:
        return not self._proposed_req_parser(eval)


class GeneralEval(EvalWrapper):
    """justified requirement evaluation based on different metrics"""
    def __init__(self, metrics:M._list=M.all):
        format_dummy = {
            "requirement": str,
            "evaluation": {
                m: {
                    "rating": int,
                    "comment": str
                } for m in metrics
            },
            "proposed_requirement": {
                "text": Optional[str],
                "justification": Optional[Union[str, dict]]
            },
        }
        super().__init__(format_dummy)

    def _rating_parser(self, eval:Evaluation):
           
        max_rating, min_rating = [sum(i - mo for mo in M.offsets.values()) for i in [5, 1]]

        cumulative_rating = 0
        for m, d in eval.content["evaluation"].items():
            d["rating_threshold"] = M.offsets[m]
            cumulative_rating += d["rating"] - M.offsets[m]

        # Normalize the cumulative rating to the scale [0, 1]
        eval.content["overall_rating"] = (cumulative_rating - min_rating) / (max_rating - min_rating)
        eval.content["overall_rating_threshold"] = (0 - min_rating) / (max_rating - min_rating) 
        return eval.content["overall_rating"]
    
    def _proposed_req_parser(self, eval:Evaluation) -> str:
        return eval["proposed_requirement"]["text"]
    
    def _no_proposal_condition(self, eval:Evaluation):
        p = self._proposed_req_parser(eval)
        return p is None or p.lower().startswith("no proposal")
    

class MetricEval(EvalWrapper):
    """justified evaluation based on a single metric"""
    def __init__(self):
        format_dummy = {
            "requirement": str,
            "rating": int,
            "justification": str,
            "proposed_requirement": Optional[str]
        }
        super().__init__(format_dummy)

    def _rating_parser(self, eval:Evaluation):
        return eval["rating"]
    
class ProposedReqEval(EvalWrapper):
    """improved requirement suggestion"""
    def __init__(self):
        format_dummy = {
            "requirement": str,
            "proposed_requirement": Optional[str],
            "justification": Optional[Union[str, dict]]
        }
        super().__init__(format_dummy)

    def _rating_parser(self, eval:Evaluation):
        return 0
    
class GeneralJudgement(EvalWrapper):
    """judgement of a requirement evaluation"""
    def __init__(
        self, metrics:M._list=M.all, 
        metric_wrapper:Callable[[M._single], str]=lambda m: f"Assessment_of_{m}_Evaluation"
    ):
        format_dummy = {
            "original_requirement": str,
            "evaluation": {
                metric_wrapper(m): {
                    "rating": Union[int, float],
                } for m in metrics
            },
            "Assessment_of_proposed_requirement": dict
        }
        super().__init__(format_dummy, limit_schema_layers=1)

    def _rating_parser(self, eval:Evaluation):
        ratings = [m["rating"] for m in eval["evaluation"].values()]
        overall_rating = sum(ratings) / len(ratings)
        max_rating = 5
        normalized_rating = (overall_rating - 1) / (max_rating - 1)
        eval.content["overall_evaluation_rating"] = normalized_rating
        return normalized_rating
    
    def _no_proposal_condition(self, eval:Evaluation):
        return False
    
class MetricJudgement(EvalWrapper):
    """judgement of a single metric evaluation"""
    def __init__(self):
        format_dummy = {
            "accuracy_of_rating": int,
            "comment_on_accuracy": str,
            "quality_of_justification": int,
            "comment_on_quality": str
        }
        super().__init__(format_dummy)

    def _rating_parser(self, eval:Evaluation):
        rating = 0.6 * eval["accuracy_of_rating"] + 0.4 * eval["quality_of_justification"]
        eval.content["rating"] = rating
        return rating
    
    def _no_proposal_condition(self, eval:Evaluation):
        return False
    
class ProposedReqJudgement(EvalWrapper):
    """judgement of a proposed requirement"""
    def __init__(self):
        format_dummy = {
            "overall_alignment_with_metrics": int,
            "comment": str
        }
        super().__init__(format_dummy)

    def _rating_parser(self, eval:Evaluation):
        return eval["overall_alignment_with_metrics"]
    
    def _no_proposal_condition(self, eval:Evaluation):
        return False
    
class RAGEvaluation(EvalWrapper):
    """required format for an evaluation dataset used for the RAG module"""
    def __init__(self, target_eval_wrapper:EvalWrapper, expand_for_metrics:Optional[M._list]=None):
        if expand_for_metrics:
            # if the target evaluation is metric-specific, expand the format for each metric
            evaluation = {m: target_eval_wrapper.format_dummy for m in expand_for_metrics}
        else:
            evaluation = target_eval_wrapper.format_dummy
        format_dummy = {
            "requirement":str,
            "evaluation":evaluation,
        }
        super().__init__(format_dummy)
    
    def _rating_parser(self, _:Evaluation):
        return