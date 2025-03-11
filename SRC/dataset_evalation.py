# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from groq import RateLimitError, InternalServerError
import database_management.db_manager as db
from evaluation_wrapper.evaluation_wrapper import Evaluation, GeneralEval, GeneralJudgement
from typing import List, Callable, Union, Literal
from pathlib import Path


def evaluate_dataset(
    evaluator:Callable[[Union[str, Evaluation]], Evaluation], 
    model:db.MODEL,
    dataset_name:db.TEST_DATA, eval_approach:db.EVAL_APPROACH,
    eval_type:Literal["judgements", "evaluations"],
    judge_approach:db.EVAL_APPROACH,
    field_name:str, stop_idx:int=None,
    database_subdir:Path=db.test_data,
    rating_scale:int=5
):
    """
    This function loads the dataset, performs evaluations using the specified evaluator, and saves the results to a JSON file. 
    If evaluations already exist, it resumes from where it left off. It handles rate limit errors, internal server errors, 
    and other exceptions, and retries evaluations up to a specified recursion limit.
    
    Args:
        evaluator (Callable[[Union[str, Evaluation]], Evaluation]): The evaluator to be used.
        model (db.MODEL): The model to be used.
        dataset_name (db.TEST_DATA): The dataset to be evaluated.
        eval_approach (db.EVAL_APPROACH): The evaluation approach to be used.
        eval_type (Literal["judgements", "evaluations"]): The type of evaluation to be performed.
        judge_approach (db.EVAL_APPROACH): The judgement approach to be used.
        field_name (str): The field name in the dataset to be evaluated.
        stop_idx (int, optional): The index at which to stop the evaluation. Defaults to None.
        database_subdir (Path, optional): The directory in which the dataset is stored. Defaults to db.test_data.
        rating_scale (int, optional): The rating scale to be used. Defaults to 5.
    """
    if eval_type == "judgements":
        field_name = "evaluations"
        new_dataset_name = db.get_dataset_file_name(dataset_name, model, "evaluations", eval_approach)
        input_dict = db.load_dict_from_json_file(new_dataset_name, database_subdir)
        input_parser = lambda input: GeneralEval()(input)
    else:
        input_dict = db.load_req_dict_from_csv_file(
            dataset_name, [field_name], database_subdir
        )
        input_parser = lambda input: input
    dest_json_name = db.get_dataset_file_name(dataset_name, model, eval_type, eval_approach, judge_approach)
    if db.json_file(dest_json_name, database_subdir).exists():
        output_dict = db.load_dict_from_json_file(dest_json_name, database_subdir)
    else:
        output_dict = {
            "failed_generations":0,
            "rating_scale":rating_scale,
            eval_type:[]
        }
    outputs:list = output_dict[eval_type]
    start_idx = len(outputs) + output_dict["failed_generations"]
    
    inputs:List[Union[str, dict]] = input_dict[field_name][start_idx:stop_idx]

    def output_parser(eval:Evaluation, input:Union[str, Evaluation]):
        output = eval.content
        if isinstance(input, str):
            return output
        output["overall_requirement_rating"] = input["overall_rating"]
        return output

    def try_generate_evaluation(input:Union[str, Evaluation], recursion_count:int=0, recursion_limit:int=2):
        recursion_count += 1
        eval = evaluator(input)
        if eval.is_valid():
            return output_parser(eval, input)
        if recursion_count <= recursion_limit:
            return try_generate_evaluation(input, recursion_count, recursion_limit)
        print(f"Could not generate evaluation for input: {input}")
        return None
    
    for input in inputs:
        try:
            if evaluation := try_generate_evaluation(input_parser(input)):
                outputs.append(evaluation)
                print(f"Generated evaluation {len(outputs)}/{start_idx + len(inputs)}")
            else:
                output_dict["failed_generations"] += 1
            continue
        except RateLimitError:
            print("Rate limit error occurred.")
        except InternalServerError:
            print("Internal server error occurred.")
        except Exception as e:
            print(f"Unknown error occurred: {e}")
        break
    print("Saving generated evaluations.")
    db.save_dict_to_json_file(output_dict, dest_json_name, database_subdir)


def parse_ratings_of_dataset(dataset:db.TEST_DATA, evaluator:db.EVALUATOR, eval_approach:db.EVAL_APPROACH, eval_type:db.EVAL_TYPE):
    """
    Parses the ratings of a given dataset and saves the parsed evaluations back to the file.

    Args:
        dataset (db.TEST_DATA): The dataset to be evaluated.
        evaluator (db.EVALUATOR): The evaluator performing the evaluation.
        eval_approach (db.EVAL_APPROACH): The approach used for evaluation.
        eval_type (db.EVAL_TYPE): The type of evaluation to be performed.
    """
    file_name = db.get_dataset_file_name(dataset, evaluator, eval_type, eval_approach)
    evaluations = db.load_dict_from_json_file(file_name, db.test_data)[eval_type]
    eval_wrapper = GeneralEval() if eval_type == "evaluations" else GeneralJudgement()
    parsed_evaluations = [eval_wrapper(eval, parse_rating_on_init=True).content for eval in evaluations]
    db.save_dict_to_json_file({eval_type: parsed_evaluations}, file_name, db.test_data)


if __name__ == "__main__":
    # parse_ratings_of_dataset("benchmark_requirements", "human", "successive", "evaluations")
    ...
