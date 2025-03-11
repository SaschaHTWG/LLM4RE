# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from evaluation_chain.evaluation_chain import ChainLink as Link, EvaluationChain as Chain
from database_management.db_manager import Metrics as M, EVAL_CHAINS, ChainLinkOutput as LinkOutput
from database_management import string_helper as sh
from evaluation_wrapper import evaluation_wrapper as ew
from evaluation_wrapper.evaluation import Evaluation
from typing import List, Dict, Callable

def get_basic_output_parser(metrics:M._list):
    def parse_output(outputs:List[LinkOutput], input:str) -> Evaluation:
        eval_content:dict = outputs.pop().evaluation.content
        eval_content["proposed_requirement"] = {
            "text": eval_content["proposed_requirement"],
            "justification": eval_content.pop("justification")
        }
        eval_content["evaluation"] = {
            metrics[i]: {
                "rating": out.evaluation["rating"], 
                "comment": out.evaluation["justification"]
            } for i, out in enumerate(outputs)
        }
        return ew.GeneralEval()(eval_content, input)
    return parse_output

def basic(metrics:M._list=M.all) -> Chain:
    return (
        Link("evaluation_chain_step", ew.MetricEval()).iterate_metrics(metrics, initial_memory_reset=True)
        | Link("evaluation_chain_end", ew.ProposedReqEval(), prev_output_indices=slice(None))
    ).with_parsed_output(get_basic_output_parser(metrics))

def refined_chain_end(metrics:M._list=M.all) -> Chain:
    def filter_prev_outputs(prev_outputs:List[LinkOutput]) -> List[LinkOutput]:
        def is_relevant(output:LinkOutput) -> bool:
            if not (rating := output.evaluation.parse_rating()):
                return False
            return rating < M.offsets[output.metrics[0]]
        outputs = [output for output in prev_outputs if is_relevant(output)]
        if not outputs:
            outputs = [LinkOutput(eval=ew.MetricEval()({
                 "requirement": "",
                 "rating": 0,
                 "justification": "no improvement required",
                 "proposed_requirement": None
            }, ""), metrics=["Evaluation"])]
        return outputs
    
    return (
        Link("evaluation_chain_step", ew.MetricEval()).iterate_metrics(metrics, initial_memory_reset=True)
        | Link("evaluation_chain_end_2", ew.ProposedReqEval(), prev_output_indices=filter_prev_outputs)
    ).with_parsed_output(get_basic_output_parser(metrics))

def judge_chain(metrics:M._list=M.all) -> Chain:
    def metric_input_parser(_, metrics:M._list, input:Evaluation) -> str:
        m_eval:dict = input["evaluation"][metrics[0]]
        m_eval["justification"] = m_eval.pop("comment")
        return sh.format_dict({
            "requirement": input["requirement"],
            f"{metrics[0]}_Evaluation": m_eval
        }, escape_brackets=False)
    
    def proposed_req_input_parser(_, __, input:Evaluation) -> str:
        return sh.format_dict({
            "original_requirement": input["requirement"],
            "improved_requirement": input.get_proposed_requirement()
        }, escape_brackets=False)
    
    def output_parser(outputs:List[LinkOutput], input:Evaluation) -> Evaluation:
        response:dict = {
            "original_requirement": input["requirement"],
            "evaluation": {}
        }
        for i, metric in enumerate(metrics):
            outputs[i].evaluation.parse_rating()
            response["evaluation"][metric] = outputs[i].evaluation.content

        response["Assessment_of_proposed_requirement"] = outputs[-1].evaluation.content
        return ew.GeneralJudgement(metrics, metric_wrapper=lambda m: m)(response, parse_rating_on_init=True)
    
    return (
        Link("judge_chain_step", ew.MetricJudgement(), input_parser=metric_input_parser).iterate_metrics(metrics)
        | Link("judge_chain_end", ew.ProposedReqJudgement(), input_parser=proposed_req_input_parser)
    ).with_parsed_output(output_parser)

def RAG_successive_data(metrics:M._list=M.all) -> Chain:
    def output_parser(outputs:List[LinkOutput], input:str) -> Evaluation:
        return ew.RAGEvaluation(ew.GeneralEval(metrics))({
            "requirement": input,
            "evaluation": outputs[0].evaluation.content,
        })
    return Chain([Link("successive_approach_r5", ew.GeneralEval(metrics), metrics)], output_parser)

def RAG_iterative_data(metrics:M._list=M.all) -> Chain:
    def output_parser(outputs:List[LinkOutput], input:str) -> Evaluation:
        return ew.RAGEvaluation(ew.MetricEval(), metrics)({
            "requirement": input,
            "evaluation": {metrics[i]: out.evaluation.content for i, out in enumerate(outputs)},
        })
    return Link("evaluation_chain_step", ew.MetricEval()).iterate_metrics(metrics).with_parsed_output(output_parser)
# define new evaluation chain callables here (orient on basic)

evaluation_chains:Dict[EVAL_CHAINS, Callable[[M._list], Chain]] = {
    # link new evaluation chain callable here
    # add key to EVAL_CHAINS in content_manager/content_manager.py
    "basic": basic,
    "refined_chain_end": refined_chain_end,
    "judge_chain": judge_chain,
    "RAG_successive_data": RAG_successive_data,
    "RAG_iterative_data": RAG_iterative_data
}




