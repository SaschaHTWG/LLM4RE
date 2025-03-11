# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from langchain_core.runnables import RunnableLambda, RunnableSerializable, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.base import Runnable
from database_management import db_manager as db, template_processing as tp, string_helper as sh
from database_management.db_manager import Metrics as M, PREV_OUTPUTS
from RAG import RAG
from evaluation_wrapper.evaluation_wrapper import EvalWrapper, GeneralEval
from LLMs import LLM
from typing import Optional, Dict

class Evaluator(Runnable):
    """Evaluator class for running and evaluating language model (LLM) chains.

    Attributes
    ==========

        session_count (int): Counter for the number of sessions.
        evaluation_wrapper (EvalWrapper): Wrapper for evaluation logic.
        llm (LLM): Language model instance.
        metrics (list): List of metrics for evaluation.
        pv (PromptVersions): Prompt versions configuration.
        n_shots (int): Number of shots for few-shot learning.
        useSystemMessage (bool): Flag to use system message in prompts.
        memory_size (int): Size of the memory for the LLM.
        structured_output (bool): Flag to determine if the output should be structured.
        llm_chain (RunnableSerializable): Chain of runnable components for the LLM.

    Key Methods
    ===========

        **invoke**
            Invokes the LLM chain with the given input and configuration.
        **update**
            Updates the LLM chain and evaluation wrapper with new parameters, used as Interface for the EvluationChain framework.
        **reset_memory**
            Resets the memory (history of last messages) of the LLM.
    """
    def __init__(
        self, llm:LLM=LLM("llama-3.1-8b-instant"), evaluation_wrapper:EvalWrapper=GeneralEval(),
        structured_output:bool=True, n_shots:int=1, useSystemMessage:bool=False, memory_size:int=0,
        metrics:M._list=M.all, set_chain_on_init:bool=True,
        prompt_versions:db.PromptVersions=db.PromptVersions()
    ):
        self.session_count = 0
        self.evaluation_wrapper = evaluation_wrapper
        self.llm = llm
        self.metrics = metrics
        self.pv = prompt_versions
        self.n_shots = n_shots
        self.useSystemMessage = useSystemMessage
        self.memory_size = memory_size
        self.structured_output = structured_output
        self.llm_chain:RunnableSerializable = None
        if set_chain_on_init:
            self.llm_chain = self._create_chain(prompt_versions.template, metrics)

    def _create_chain(
        self, prompt_version:db.PROMPT_VERSION, metrics:M._list, step:Optional[int]=None, prev_outputs:PREV_OUTPUTS=[]
    ):
        if not set(metrics) <= set(M.all):
            metrics = self.metrics
        template = db.load_prompt_template(prompt_version)
        return (
            self._get_inputs(template, metrics)
            | self._get_prompt_template(template, metrics, step, prev_outputs)
            | self.llm
        )
    
    def _get_inputs(self, template:str, metrics:M._list) -> Dict[str, Runnable]:
        return {"query": RunnablePassthrough()}
    
    def _process_template(self, template: str, metrics:M._list, step:Optional[int]=None, prev_outputs:PREV_OUTPUTS=[]):
        return tp.process_template(
            template, metrics, False, self.n_shots, step, prev_outputs, self.pv
        )
    
    def _get_prompt_template(self, template: str, metrics:M._list, step:Optional[int]=None, prev_outputs:PREV_OUTPUTS=[]):
            system_prompt, user_prompt_template = self._process_template(
                template, metrics, step, prev_outputs
            )
            make_user_prompt = lambda inputs: user_prompt_template.format(**inputs)
            if self.useSystemMessage:
                assert system_prompt is not None, "no system prompt found in template -> use user_prompt section marker to separate system and user prompts"
                def make_prompt(inputs):
                    self.session_count += 1
                    human_message = [HumanMessage(make_user_prompt(inputs))]
                    if (sc := self.session_count) > 1:
                        if sc == self.memory_size:
                            self.session_count = 0
                        return human_message
                    return [SystemMessage(system_prompt)] + human_message
            else:
                make_prompt = lambda inputs: sh.double_new_lines([
                    system_prompt, 
                    make_user_prompt(inputs)
                ])
            
            return RunnableLambda(make_prompt)
    
    def _parse_output(self, output, input):
        if self.structured_output:
            return self.evaluation_wrapper(output, input)
        return StrOutputParser().invoke(output)
    
    def invoke(self, input, config = None, **kwargs):
        return self._parse_output(
            self.llm_chain.invoke(input, config, **kwargs),
            input
        )
    
    def update(self, prompt_version:db.PROMPT_VERSION, eval_wrapper:EvalWrapper, metrics:M._list, step:Optional[int]=None, prev_outputs:PREV_OUTPUTS=[]):
        """
        Updates the LLM chain and evaluation wrapper with the provided parameters.

        Args:
            prompt_version (cm.PROMPT_VERSION): The version of the prompt template to be used.
            eval_wrapper (EvalWrapper): The evaluation wrapper instance.
            metrics (M._list): A list of metrics to be used for evaluation.
            step (Optional[int], optional): An optional Step Identifier. Defaults to None.
            prev_outputs (PREV_OUTPUTS, optional): A list of previous outputs. Defaults to an empty list.
        """
        self.llm_chain = self._create_chain(prompt_version, metrics, step, prev_outputs)
        self.evaluation_wrapper = eval_wrapper
    
    def reset_memory(self):
        self.llm.reset_memory()

class ReqEvaluator(Evaluator):
    def __init__(
        self, llm:LLM, evaluation_wrapper: EvalWrapper, structured_output:bool=True,
        use_RAG:bool=False, n_shots:int=1, RAG_kwargs:dict=None, useSystemMessage:bool=False, 
        memory_size:int=0, metrics:M._list=M.all, set_chain_on_init:bool=True,
        prompt_versions:db.PromptVersions=db.PromptVersions()
    ):
        self.use_RAG = use_RAG
        if use_RAG:
            self.RAG  = RAG(**RAG_kwargs)
        self.RAG_kwargs = RAG_kwargs
        super().__init__(
            llm, evaluation_wrapper, 
            structured_output, n_shots, useSystemMessage, memory_size, 
            metrics, set_chain_on_init, prompt_versions
        )

    def _get_inputs(self, template, metrics):
        if self.use_RAG and (one_shot_sections:=tp.get_sections(template, "one_shot", only_content=True)):
            return self.RAG.get_inputs(
                metrics=metrics,
                context_template=one_shot_sections[0]
            )
        else:
            return super()._get_inputs(template, metrics)
        
    def _process_template(self, template, metrics, step=None, prev_outputs=[]):
        return tp.process_template(
            template, metrics, self.use_RAG, self.n_shots, step, prev_outputs, self.pv
        )

class Judge(Evaluator):
    def __init__(
        self, llm: LLM, eval_wrapper:EvalWrapper, set_chain_on_init:bool=True,
        prompt_versions:db.PromptVersions=db.PromptVersions()
    ):
        super().__init__(
            llm, eval_wrapper, set_chain_on_init=set_chain_on_init, prompt_versions=db.PromptVersions(
                metric_definitions=prompt_versions.metric_definitions,
                rating_definitions=prompt_versions.rating_definitions,
                template="judge_general"
            )
        )

    def _parse_output(self, output, _):
        return self.evaluation_wrapper(output, parse_rating_on_init=True)
