# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from evaluation_wrapper.evaluation import Evaluation
from typing import Literal, List, Dict, get_args, Callable, Optional, Union, Mapping
from pathlib import Path
import json
import pandas as pd

ANTHROPIC_MODEL = Literal[
    "claude-3-5-sonnet-latest", 
    "claude-3-5-haiku-latest"
]

GROQ_MODEL = Literal[
    "llama3-8b-8192",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]

MODEL = Literal[ANTHROPIC_MODEL, GROQ_MODEL]

EVALUATOR = Literal[MODEL, "human"]

GROQ_API_KEY = "<insert your api key here>"

ANTHROPIC_API_KEY = "<insert your api key here>"

class Metrics:
    _single = Literal[
        "Correctness", 
        "Unambiguity", 
        "Completeness", 
        "Consistency", 
        "Precision", 
        "Verifiability", 
        "Atomicity"
    ]
    _list = List[_single]
    prefix = "Requirement "
    wrap_single:Callable[[_single], str] = lambda m: Metrics.prefix + m
    wrap:Callable[[_list], List[str]] = lambda metrics: [
        Metrics.wrap_single(m) for m in metrics
    ]
    unwrap:Callable[[str], _single] = lambda wm: wm.replace(Metrics.prefix, "")
    all = get_args(get_args(_list)[0])
    all_except:Callable[[_list], _list] = lambda excluded: [m for m in Metrics.all if m not in excluded]
    # acceptable ratings to be normalized
    offsets:Dict[_single, int] = {
        "Correctness": 5,
        "Unambiguity": 4,
        "Completeness": 3,
        "Consistency": 5,
        "Precision": 3,
        "Verifiability": 4,
        "Atomicity": 3
    }    

STREAMLIT_ROLE = Literal["user", "assistant"]

class StreamlitMessage:
    def __init__(self, content: Union[str, Mapping], role: STREAMLIT_ROLE):
        self.content = content
        self.role = role

    def to_dict(self):
        return {"content": self.content, "role": self.role}

class ChainLinkOutput:
    def __init__(self, eval:Evaluation, metrics:Metrics._list, step:int=1):
        self.evaluation = eval
        self.metrics = metrics
        self.step = step

PREV_OUTPUTS = List[ChainLinkOutput]

FIELD_NAME = Literal["Requirement", "Type", Metrics._single]

data_base_root = Path("data_base")
RAG_data = data_base_root / "RAG_data"
metric_description = data_base_root / "metric_description"
prompt_templates = data_base_root / "prompt_templates"
static_few_shots = data_base_root / "static_few_shots"
last_messages = data_base_root / "last_messages"
test_data = data_base_root / "test_data"

TEST_DATA = Literal[
    "bad_requirements", 
    "average_requirements"
]
EVAL_TYPE = Literal["evaluations", "judgements"]
EVAL_APPROACH = Literal["successive", "iterative", "iterative_zero_shot"]
LLM_ROLE = Literal["evaluator", "judge"]
    
PROMPT_VERSION = Literal[
    "template_demo", "only_query",
    "evaluation_chain_step", "evaluation_chain_step_zero_shot", "evaluation_chain_end", "evaluation_chain_end_2",
    "successive_approach_r3", "successive_approach_r5", 
    "judge_chain_step", "judge_chain_end", "judge_general"
]

EVAL_FEW_SHOTS = Literal["eval_rating_10", "eval_rating_5"]
JUDGE_FEW_SHOTS = Literal["judge_rating_10"]
STATIC_FEW_SHOTS = Literal[EVAL_FEW_SHOTS, JUDGE_FEW_SHOTS]

EVAL_CHAINS = Literal["basic", "refined_chain_end", "judge_chain", "RAG_successive_data", "RAG_iterative_data"]
class PromptVersions:
    def __init__(self, 
        metric_definitions:int=6, 
        rating_definitions:int=6,
        static_few_shots:STATIC_FEW_SHOTS="eval_rating_5",
        template:PROMPT_VERSION="template_demo",
        evaluation_chain:EVAL_CHAINS="basic"
    ):
        self.metric_definitions = metric_definitions
        self.rating_definitions = rating_definitions
        self.static_few_shots = static_few_shots
        self.template = template
        self.evaluation_chain = evaluation_chain

def data_base_file(name:str, ending:Literal["csv", "json", "md"], subdir:Path=data_base_root):
    return subdir / f"{name}.{ending}"

def csv_file(name:str, subdir:Path=data_base_root):
    return data_base_file(name, "csv", subdir)

def ragatouille_index_path(index_name:str):
    return Path(".ragatouille", "colbert", "indexes", index_name)

def chroma_index_path(index_name:str):
    return Path(".chroma", "indexes", index_name)

def json_file(name:str, subdir:Path=data_base_root):
    return data_base_file(name, "json", subdir)

def prompt_file(version:PROMPT_VERSION):
    return data_base_file(version, "md", prompt_templates)

def load_req_dict_from_csv_file(name:TEST_DATA, field_names:List[str]=["Type", "Requirement"], subdir:Path=data_base_root):
    df = pd.read_csv(csv_file(name, subdir), encoding="utf-8", encoding_errors="replace")
    requirements = {fn: df[fn].to_list() for fn in field_names}
    return requirements

def save_req_dict_to_csv_file(file_name:str, requirements:Dict[str, List[str]], subdir:Path=data_base_root):
    df = pd.DataFrame(requirements)
    df.to_csv(csv_file(file_name, subdir), encoding="utf-8")

def save_dict_to_json_file(obj:dict, name:str, subdir:Path=data_base_root):
    with open(json_file(name, subdir), "w") as f:
        json.dump(obj, f, indent=4)

def load_dict_from_json_file(file_name:str, subdir:Path=data_base_root) -> Optional[dict]:
    try:
        with open(json_file(file_name, subdir), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def load_static_few_shots(file_name:STATIC_FEW_SHOTS):
    llm_role = "evaluator" if file_name in get_args(EVAL_FEW_SHOTS) else "judge"
    return load_dict_from_json_file(
        file_name, 
        subdir=static_few_shots / llm_role 
    )

def load_metric_descriptions(type:Literal["metric", "rating"]="metric"):
    return load_dict_from_json_file(
        f"{type}_definitions",
        subdir=metric_description
    )

def load_prompt_template(version:PROMPT_VERSION):
    with open(prompt_file(version), "r") as f:
        return f.read()

def save_last_message(message:str, type:Literal["prompt", "response"], idx:int=1):
    last_messages.mkdir(parents=True, exist_ok=True)
    if idx == 1:
        for file in last_messages.glob(f"last_{type}_*.md"):
            file.unlink()
    with open(data_base_file(f"last_{type}_{idx}", "md", last_messages), "w", encoding="utf-8") as f:
        f.write(message)

def get_dataset_file_name(
    dataset:TEST_DATA, 
    evaluator:EVALUATOR,
    eval_type:EVAL_TYPE, 
    eval_approach:EVAL_APPROACH, 
    judge_approach:EVAL_APPROACH="iterative"
):
    evaluator = evaluator.replace("-", "_").replace(".", "_")
    eval_name = f"{eval_approach}_evaluations_of_{dataset}_by_{evaluator}"
    if eval_type == "judgements":
        eval_name = f"{judge_approach}_judgements_of_{eval_name}"
    return eval_name
    