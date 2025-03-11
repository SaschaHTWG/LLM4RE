# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from LLM4RE import ReqEvaluator, Judge
from LLMs import LLM
import database_management.db_manager as db
from database_management.db_manager import Metrics as M, PromptVersions
from evaluation_wrapper.evaluation_wrapper import GeneralEval, MetricEval, Evaluation, GeneralJudgement
from evaluation_chain.implementations import evaluation_chains
from typing import Union, Any

def init_response_generator(
        llm_model:db.MODEL,
        structured_output:bool,
        use_RAG:bool, 
        load_retriever:bool,
        RAG_dataset_name:str,
        n_shots:int,
        use_system_message:bool,
        memory_size:int,
        use_evaluation_chain:bool,
        metrics:M._list, 
        judge_evaluation:bool,
        individual_judgement:bool,
        judge_model:db.MODEL,
        prompt_versions:PromptVersions=PromptVersions(template="successive_approach_r5"),
):
    evaluation_wrapper=MetricEval() if use_evaluation_chain else GeneralEval(metrics)
    llm = LLM(llm_model, structured_output, evaluation_wrapper.schema, memory_size)
    
    if use_RAG:
        
        RAG_kwargs=dict(
            dataset_name=RAG_dataset_name,
            load_retriever=load_retriever,
            n_retrieved_docs=n_shots,
        )
    else:
        RAG_kwargs = None

    evaluator = ReqEvaluator(
        llm, 
        evaluation_wrapper=evaluation_wrapper,
        structured_output=structured_output,
        use_RAG=use_RAG, 
        n_shots=n_shots,
        RAG_kwargs=RAG_kwargs, 
        useSystemMessage=use_system_message,
        memory_size=memory_size,
        metrics=metrics,
        set_chain_on_init=not use_evaluation_chain,
        prompt_versions=prompt_versions
    )
    if use_evaluation_chain:
        eval_chain = evaluation_chains[prompt_versions.evaluation_chain](metrics).with_evaluator(evaluator)
        pre_generate_response = lambda prompt: eval_chain.invoke(prompt)
    else:
        pre_generate_response = lambda prompt: evaluator.invoke(prompt)

    def generate_response(prompt):
        if isinstance(response:=pre_generate_response(prompt), Evaluation) and not judge_evaluation:
            response.parse_rating()
        return response

    if judge_evaluation:
        judgement_wrapper=GeneralJudgement(metrics)
        judge_llm = LLM(judge_model, structured_output, judgement_wrapper.schema)
        one_step_judge = Judge(judge_llm, judgement_wrapper, not individual_judgement, prompt_versions)
        if individual_judgement:
            judge = evaluation_chains["judge_chain"](metrics).with_evaluator(one_step_judge)
        else:
            judge = one_step_judge
        def generate_judgement(input:Union[Any, Evaluation]):
            if isinstance(input, Evaluation):
                evaluation = input
            else:
                evaluation = generate_response(input)
            if not isinstance(evaluation, Evaluation):
                raise ValueError("Judge Input must be an instance of Evaluation")
            one_step_judge.llm.invoke_count = evaluator.llm.invoke_count
            judgement = judge.invoke(evaluation)
            if isinstance(input, Evaluation):
                return judgement
            evaluation.parse_rating()
            return (evaluation, judgement)
            
        return generate_judgement
    else:
        return generate_response
