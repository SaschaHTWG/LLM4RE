# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from __future__ import annotations
from LLM4RE import Evaluator
from database_management import db_manager as db
from database_management.db_manager import ChainLinkOutput as LinkOutput, Metrics as M
from evaluation_wrapper.evaluation_wrapper import Evaluation, EvalWrapper
from typing import Union, List, Any, Callable, Optional

PREV_OUTPUT_INDICES = Optional[Union[List[int], slice, Callable[[List[LinkOutput]], List[LinkOutput]]]]

class ChainLink:
    """
    A class representing a link in an evaluation chain.
    A link can be seen as a single input and output of an LLM, which can be combined with other links to realize a conversation.
    It uses an Evaluator instance, whose input and output processing is defined according to the ChainLink's attributes.
    
    Attributes
    ==========

        prompt_version (db.PROMPT_VERSION): 
            refers to a file name in `data_base/prompt_templates` 
        eval_wrapper (EvalWrapper): 
            The evaluation wrapper to be used, depending on the desired output format.
        metrics (M._list): 
            The list of metrics to be used for template processing.
        step (int): 
            The step number to be used for template processing.
        reset_memory (bool): 
            Whether to reset the memory of the evaluator before this step. Defaults to False.
        update_model_schema (bool): 
            Whether to update the model schema. Defaults to True.
        prev_output_indices (PREV_OUTPUT_INDICES): 
            which previous outputs to be included in the current input. Defaults to None. 
        parse_input (Callable[[List[LinkOutput], M._list, Any], Any]): 
            Function to parse input based on previous outputs and metrics. Defaults to no parsing.
    
    Key Methods
    ===========
    
        **__or__**
            Connects the current ChainLink with another ChainLink or EvaluationChain to form a new EvaluationChain.
        
        **slice_prev_outputs**
            Slices the previous outputs based on the provided indices.
        
        **update_evaluator**
            Updates the evaluator's I/O parsing with the current ChainLink's attributes and previous outputs.
        
        **iterate_metrics**
            Forms an EvaluationChain that repeats the current ChainLink configuration for each metric in the given list.
        
        **invoke**
            Updates and invokes the evaluator with the ChainLink's configuration, input and previous outputs.
        
        **copy**
            Returns an independent copy of the current ChainLink.
    """
    def __init__(
        self, prompt_version:db.PROMPT_VERSION, eval_wrapper:EvalWrapper, 
        metrics:M._list=M.all, step:int=1,
        prev_output_indices:PREV_OUTPUT_INDICES=None,
        input_parser:Callable[[List[LinkOutput], M._list, Any], Any]=lambda prev_outputs, metrics, input: input,
        reset_memory:bool=False,
        update_model_schema:bool=True
    ):
        self.prompt_version = prompt_version
        self.eval_wrapper = eval_wrapper
        self.metrics = metrics
        self.step = step
        self.reset_memory = reset_memory
        self.update_model_schema = update_model_schema
        self.prev_output_indices = prev_output_indices
        self.parse_input = input_parser
        self._slice_prev_outputs = self._get_list_slicer(prev_output_indices)

    def __or__(self, extension:Union[ChainLink, EvaluationChain]):
        if not isinstance(extension, Union[EvaluationChain, ChainLink]):
            raise TypeError("Expected object of type 'EvaluationChain' or 'Extension'")
        if isinstance(extension, ChainLink):
            return EvaluationChain([self, extension])
        else:
            return EvaluationChain([self] + extension.links)
        
    def _get_list_slicer(self, prev_output_indices:PREV_OUTPUT_INDICES) -> Callable[[List[LinkOutput]], List[LinkOutput]]:
        if not prev_output_indices:
            return lambda _: []
        if callable(prev_output_indices):
            return prev_output_indices
        if isinstance(prev_output_indices, slice):
            return lambda ls: ls[prev_output_indices]
        if isinstance(prev_output_indices, list):
            return lambda ls: [ls[i] for i in prev_output_indices]
        raise TypeError(f"Expected object of type {PREV_OUTPUT_INDICES}")
    
    def slice_prev_outputs(self, prev_outputs:List[LinkOutput]) -> List[LinkOutput]:
        return self._slice_prev_outputs(prev_outputs)
    
    def update_evaluator(self, evaluator:Evaluator, prev_outputs:List[LinkOutput]):
        evaluator.update(
            prompt_version=self.prompt_version,
            eval_wrapper=self.eval_wrapper,
            metrics=self.metrics,
            step=self.step,
            prev_outputs=self.slice_prev_outputs(prev_outputs)
        )
    
    def iterate_metrics(self, metrics:db.Metrics._list, initial_memory_reset:bool=False):
        return EvaluationChain([self]).iterate_metrics(metrics, initial_memory_reset)
    
    def invoke(self, evaluator:Evaluator, input:Any, prev_outputs:List[LinkOutput]=[]):
        self.update_evaluator(evaluator, prev_outputs)
        if self.reset_memory:
            evaluator.reset_memory()
        if self.update_model_schema:
            evaluator.llm.update_schema(self.eval_wrapper.schema)
        eval = evaluator.invoke(self.parse_input(prev_outputs, self.metrics, input))
        return LinkOutput(eval, self.metrics, self.step)
    
    def copy(self):
        return ChainLink(
            self.prompt_version, self.eval_wrapper, self.metrics, self.step, self.prev_output_indices, 
            self.parse_input, self.reset_memory, self.update_model_schema
        )

class EvaluationChain:
    """
    A class to represent a Sequence of ChainLinks
    Uses an Evaluator instance to iterate over the list of ChainLinks to process the input and outputs for each step individually.
    
    The outputs
        - are consecutively provided as optional inputs for the following links
        - can be combined to a final evalution by a custom output parser. 

    Attributes
    ==========

    links (List[ChainLink]):
        A list of ChainLink objects that form the evaluation chain.
    parse_output (Callable[[List[LinkOutput], Any], Evaluation], optional):
        A callable to parse the output of the evaluation chain.
    evaluator (Evaluator, optional):
        An evaluator object to be used for invoking the chain.
    initial_memory_reset (bool):
        A flag to indicate if the memory should be reset for the first link in the chain.
    
    Key Methods
    ===========
    
        **__or__**
            Adds a new link or another evaluation chain to the current chain.

        **iterate_metrics**
            Repeats the current chain configuration for each metric in the given list to form a new EvaluationChain.
        
        **parse_output**
            Parses the list of outputs.
        
        **with_parsed_output**
            Sets a custom output parser for the evaluation chain and returns a new instance.
        
        **with_evaluator**
            Sets an evaluator for the evaluation chain and returns a new instance.
        
        **invoke**
            Invokes the evaluation chain with the given input by iterating over the links and parsing the output.
    """
    def __init__(
        self, links:List[ChainLink], 
        output_parser:Optional[Callable[[List[LinkOutput], Any], Evaluation]]=None,
        evaluator:Optional[Evaluator]=None,
        initial_memory_reset:bool=False
    ):
        self.links = links
        if output_parser:
            self.parse_output = output_parser
        self.evaluator = evaluator
        if initial_memory_reset:
            self.links[0].reset_memory = True

    def __or__(self, extension:Union[ChainLink, EvaluationChain]):
        if not isinstance(extension, (EvaluationChain, ChainLink)):
            raise TypeError("Expected object of type 'EvaluationChain' or 'Extension'")
        if isinstance(extension, ChainLink):
            return EvaluationChain(self.links + [extension])
        else:
            return EvaluationChain(self.links + extension.links)
        
    def __iter__(self):
        return iter(self.links)
        
    def iterate_metrics(self, metrics:db.Metrics._list, initial_memory_reset:bool=False):
        new_links:List[ChainLink] = []
        equal_schemas = len(set([link.eval_wrapper for link in self])) == 1
        for i, m in enumerate(metrics):
            for link in self:
                link.metrics = [m]
                link.step += 1 if i > 0 else 0
                if equal_schemas and i > 0:
                    link.update_model_schema = False
                new_links.append(link.copy())
        return EvaluationChain(new_links, initial_memory_reset)
    
    @staticmethod
    def parse_output(outputs:List[LinkOutput], input:Any) -> Evaluation:
        return outputs[-1].evaluation
    
    def with_parsed_output(self, output_parser:Callable[[List[LinkOutput], Any], Evaluation]):
        self.parse_output = output_parser
        return self
    
    def with_evaluator(self, evaluator:Evaluator):
        self.evaluator = evaluator
        return self
    
    def invoke(self, input):
        assert self.evaluator, "No Evaluator given"
        outputs = []
        for link in self:
            outputs.append(link.invoke(self.evaluator, input, outputs))
        return self.parse_output(outputs, input)