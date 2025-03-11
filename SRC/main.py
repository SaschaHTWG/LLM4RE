# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

import streamlit as ui
from streamlit.runtime.scriptrunner import get_script_run_ctx
from response_generation import init_response_generator
from database_management import db_manager as db
from database_management.db_manager import PromptVersions, Metrics as M
from chatbot import chatbot
from dataset_evalation import evaluate_dataset
from langsmith_tracing import enable_tracing
from typing import Literal


def main(
    mode:Literal["chat_bot", "dataset"],
    eval_model:db.MODEL,
    evaluation_mode:db.EVAL_APPROACH,
    judge_evaluation:bool,
    judgement_mode:db.EVAL_APPROACH, 
    generate_RAG_data:bool=False
):
    enable_tracing("LLM4RE", False)

    run_with_streamlit = get_script_run_ctx() is not None and mode == "chat_bot"

    generate_response = None

    if run_with_streamlit:
        if (init := ui.session_state.get("init")) is not None:
            generate_response = init["generate_response"]
    if generate_response is None:
        generate_response = init_response_generator(
            llm_model=eval_model,
            structured_output=True,
            use_RAG=True,
            load_retriever=False, # only applied if useRAG=True
            RAG_dataset_name=db.get_dataset_file_name("average_requirements", "llama-3.1-8b-instant", "evaluations", evaluation_mode), # only applied if useRAG=True
            n_shots=3, # disable few shot prompting with n_shots=0
            use_system_message=False,
            memory_size=0,
            use_evaluation_chain=(evaluation_mode in ["iterative", "iterative_zero_shot"] or generate_RAG_data), 
            metrics=M.all,
            judge_evaluation=judge_evaluation,
            judge_model="llama-3.3-70b-versatile", 
            individual_judgement=(judgement_mode == "iterative"),
            prompt_versions=PromptVersions(
                metric_definitions=6, # refers to list index [i-1] of each metric in metric_description/metric_definitions.json
                rating_definitions=6, # refers to list index [i-1] of each metric in metric_description/rating_definitions.json
                static_few_shots="eval_rating_5", # refers to file name in data_base/static_few_shots/evaluator/<file>.json
                template="successive_approach_r5", # refers to template name in prompt_templates/<template>.md
                evaluation_chain="RAG_successive_data" # refers to callable chain in evaluation_chain/implementations.py
            )
        )
        if run_with_streamlit:
            ui.session_state["init"] = {"generate_response": generate_response}

    if mode == "dataset":
        return evaluate_dataset(
            generate_response, 
            model=eval_model,
            dataset_name="average_requirements", 
            eval_approach=evaluation_mode,
            eval_type="judgements" if judge_evaluation else "evaluations",
            judge_approach=judgement_mode,
            field_name="Requirement",
            stop_idx=10,
            database_subdir=db.RAG_data if generate_RAG_data else db.test_data,
            rating_scale=5
        )
    
    intro = "My purpose is to evaluate requirements. Please enter a requirement in order to learn how well it is constructed."
    input_hint = "Enter your requirement here"

    chatbot(
        generate_response=generate_response, 
        intro=intro,
        input_hint=input_hint,
        run_in_terminal=get_script_run_ctx() is None,
        history_length=8
    )


if __name__ == "__main__":
    main(
        mode="chat_bot",
        eval_model="llama-3.1-8b-instant",
        evaluation_mode="successive",
        judge_evaluation=False,
        judgement_mode="iterative",
        generate_RAG_data=True
    )
    