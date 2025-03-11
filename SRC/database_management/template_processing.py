# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from typing import List, Callable, Literal, Tuple, Dict, get_args, Optional, Any
from abc import ABC, abstractmethod
from database_management import db_manager as db, string_helper as sh
from database_management.db_manager import Metrics as M
import re

# the following sections and variables refer to those described in data_base/prompt_templates/template_demo.md
SECTION = Literal["user_prompt", "metric", "few_shots", "one_shot", "chain_context"]
GENERAL_VARS = Literal["m_id", "m_name"]
METRIC_VARS = Literal["m_id", "m_name", "m_definition", "m_rating"]
ONE_SHOT_VARS = Literal["os_id", "os_rating", "os_req", "os_eval"]
CHAIN_CONTEXT_VARS = Literal["cc_id", "cc_metric", "cc_req", "cc_eval", "cc_prop"]
VARIABLES = Literal[GENERAL_VARS, METRIC_VARS, ONE_SHOT_VARS, CHAIN_CONTEXT_VARS]

VAR_TO_VAL = Dict[VARIABLES, str]

class VarToVal(ABC):
    """
    Abstract class for mapping variables of a section to their corresponding values.
    Some template sections are supposed to be multiplied for a specific list of items, e.g. metrics.
    Therefore the get method is called for each item in the list and the corresponding variable-to-value mapping is returned.
    """
    @staticmethod
    @abstractmethod
    def get(i:int, item:Any) -> VAR_TO_VAL:
        """
        Retrieves the variable-to-value mapping for a specific item in the list.

        Args:
            i (int): The index of the item in the list.
            item (Any): The item for which to retrieve the variable-to-value mapping.

        Returns:
            VAR_TO_VAL: The variable-to-value mapping for the specified item.
        """
        raise NotImplementedError

def escape_curly_braces(
    content: str, 
    excepted_placeholders:List[str]=["query", "context"]
) -> str:
    """
    Escapes all curly braces in the given content string except for the specified placeholders.

    Args:
        content (str): The string in which to escape curly braces.
        excepted_placeholders (List[str], optional): A list of placeholder strings that should not have their curly braces escaped. Defaults to ["query", "context"].

    Returns:
        str: The content string with curly braces escaped, except for the specified placeholders.
    """
    parse_ph:Callable[[str], str] = lambda s: "".join(
        [s.format(ph=ph) for ph in excepted_placeholders]
    )
    pattern = re.compile(
        r"(?<!{){(?!{)" + parse_ph("(?!{ph}}})") + r"|(?<!})" + parse_ph("(?<!{{{ph})") + r"}(?!})"
    )
    escaped_string = pattern.sub(lambda m: m[0]*2, content)
    return escaped_string

def remove_comments(template:str):
    """
    Removes all Markdown comments except for the relevant [section/...] markers from the template.

    Args:
        template (str): The template string content.

    Returns:
        str: The template string content without irrelevant comments.
    """
    template = re.sub(r"(\[(comment|var)\/?\w*\]:# \([^\n]+\n?)+", "", template)
    return template

def remove_irrelevant_new_lines(content: Optional[str]):
    """
    Reduces multiple consecutive new lines (three or more) 
    to a maximum of two new lines and strips any leading or trailing new lines.

    Args:
        content (str | None): The input string from which to remove irrelevant new lines.

    Returns:
        (str | None): The modified string with irrelevant new lines removed, or None if the input is None.
    """
    if content:
        return re.sub(r"\n{3,}", "\n\n", content).strip("\n")

def get_formatted_definition(m:M._single, type:Literal["metric", "rating"], version:int=1):
    """
    Retrieve and format the definition of a specified metric or rating.

    Args:
        m (str): The specific metric or rating to retrieve the definition for.
        type (Literal["metric", "rating"]): The type of definition to retrieve, either "metric" or "rating".
        version (int, optional): The version of the definition to retrieve. Defaults to 1.

    Returns:
        str: The formatted definition as a string with bullet points.
    """
    metric_descr = db.load_metric_descriptions(type)
    return sh.bullet_points(metric_descr[m][version-1])

def get_rating_expression(evaluation:dict, rating_scale:int) -> Literal["Poor", "Average", "Excellent"]:
    """
    Calculates a rating expression as "Poor", "Average", or "Excellent" based on the evaluation and rating scale.

    Args:
        evaluation (dict): must adhere to a format specified as dummy in one of the sub classes in `evaluation_wrapper.py`  
        rating_scale (int): The scale of the rating, e.g., 5 for a 1-5 rating scale.

    Returns:
        str: The rating expression as a string.
    """
    if "evaluation" in evaluation:
        evals = evaluation["evaluation"]
        rating = sum(e["rating"] for e in evals.values()) / len(evals)
    else:
        rating = evaluation["rating"]
    rating_level = int((rating - 1) * (3 - 1) / (rating_scale - 1) + 1)
    return ["Poor", "Average", "Excellent"][rating_level-1]

def get_static_few_shots(metrics:M._list, n_shots:int, version:db.STATIC_FEW_SHOTS) -> Tuple[List[dict], int]:
    """
    Loads evaluations for the given metrics from the static few shots directory.

    Args:
        metrics (List[str]): if multiple metrics are given, General evaluations are loaded and optinally filtered for the given metrics. Otherwise, the individual evaluations for the single metric are loaded. 
        n_shots (int): The number of evaluations to load, starting from the first one.
        version (str): the file to load evaluations from, refers to `data_base/static_few_shots/evaluator/<version>.json`
    
    Returns:
        (List[dict], int): (evaluations, rating_scale)
    """
    evaluation_dict = db.load_static_few_shots(version)
    rating_scale = evaluation_dict["Rating_scale"]
    if individual_metric_evals := (len(metrics) == 1):
        evals = evaluation_dict[metrics[0]]
    else:
        evals = evaluation_dict["General"]
    evals = evals[:min(len(evals), n_shots)]
    if individual_metric_evals or version in get_args(db.JUDGE_FEW_SHOTS):
        return evals, rating_scale
    def filter_metrics(ex:dict, metrics=metrics):
        ev = ex["evaluation"]
        ex["evaluation"] = {m: ev[m] for m in metrics if m in ev}
        return ex
    return [filter_metrics(ex) for ex in evals], rating_scale

def get_sections(template:str, section:SECTION, only_content:bool=False):
    """
    Extracts sections (supports multiple appearences of the same section) from a template string based on the specified section type.

    Args:
        template (str): The template string containing sections.
        section (SECTION): The section type to search for within the template.
        only_content (bool, optional): If True, the string content within the sections is returned. Otherwise the match objects are returned. Defaults to False.

    Returns:
        list: A list of strings or match objects containing the content of the specified section.
    """
    matches = re.finditer(f"\[(?P<sec>section\/{section})\]:# \([^\n]+(?P<content>.*?)\[(?P=sec) end\]:# \([^\n]+\n?", template, re.DOTALL)
    if only_content:
        return [m["content"] for m in matches]
    return list(matches)

def process_section(template:str, section:SECTION, processor:Callable[[str], str]):
    """
    Processes a specific section of a template using a provided processor function.

    Args:
        template (str): The template string containing sections to be processed.
        section (SECTION): The section identifier to locate specific sections within the template.
        processor ((str) -> str): A function that processes the content of each matched section.

    Returns:
        str: The template string with the specified sections processed by the processor function.
    """
    if matches := get_sections(template, section):
        for m in matches:
            template = template.replace(m[0], processor(m["content"]))
        return template
    return template

def process_variables(section:str, var_to_val:VAR_TO_VAL):
    """
    Replaces placeholders in the given section with corresponding values from the var_to_val dictionary.
    Args:
        section (str): The text containing variables to be replaced.
        var_to_val (Dict[VARIABLES, str]): A dictionary mapping variables to their replacement values.
    Returns:
        str: The section with placeholders replaced by their corresponding values.
    """
    output = section
    for var, value in var_to_val.items():
        if (placeholder := (f"{{{var}}}")) in section:
            output = output.replace(placeholder, value)
    return output

def multiply_process_section(section:str, var_to_val:VarToVal, items:list):
    return sh.double_new_lines([
        process_variables(section, var_to_val.get(i, item))
        for i, item in enumerate(items)
    ])

def process_metric_section(section:str, metrics:M._list, step:Optional[int]=None, versions:db.PromptVersions=db.PromptVersions()):
    """
    Processes and multiplies the templates metric section for each given metric.

    Args:
        section (str): The template content of the metric section.
        metrics (M._list): A list of metrics.
        step (int | None, optional): The step number to use for the metric. Defaults to None.
        versions (cm.PromptVersions, optional): An instance of PromptVersions containing versions of metric and rating definition. Defaults to cm.PromptVersions().

    Returns:
        str: The processed and multiplied section.
    """
    class MetricVarToVal(VarToVal):
        @staticmethod
        def get(i:int, m:M._single) -> VAR_TO_VAL:
            return {
                "m_id": str(step if step else i+1), 
                "m_name": m, 
                "m_definition": get_formatted_definition(m, "metric", versions.metric_definitions),
                "m_rating": get_formatted_definition(m, "rating", versions.rating_definitions)
            }
    return multiply_process_section(section, MetricVarToVal(), metrics)

def process_one_shot_section(section:str, evaluations:List[dict], rating_scale:int):
    """
    Processes and multiplies the templates one-shot section for each given evaluation and returns the formatted output.

    Args:
        section (str): The template content of the one shot section.
        evaluations (List[dict]): A list of evaluations for wich the section will be processed and multiplied.
        rating_scale (int): The scale used for rating evaluations.

    Returns:
        str: The formatted output with double new lines separating each processed evaluation.
    """
    class OneShotVarToVal(VarToVal):
        @staticmethod
        def get(i:int, ev:dict) -> VAR_TO_VAL:
            return {
                "os_id": str(i+1), 
                "os_rating": get_rating_expression(ev, rating_scale), 
                "os_req": ev["requirement"], 
                "os_eval": sh.format_dict(ev, escape_brackets=True)
            }
    return multiply_process_section(section, OneShotVarToVal(), evaluations)

def process_few_shots_section(section:str, use_RAG:bool, n_shots:int, metrics:M._list, version:db.STATIC_FEW_SHOTS = "eval_rating_5"):
    """
    Processes the templates few shots section.

    Args:
        section (str): The section to be processed.
        use_RAG (bool): if True, the section is processed during the RAG chain invoke.
        n_shots (int): The number of shots (examples) to use for few-shot learning. If 0, the section is removed.
        metrics (M._list): A list of metrics to be used for the few shots.
        version (STATIC_FEW_SHOTS, optional): The few-shot version to use. Defaults to "eval_rating_5.

    Returns:
        str: The processed section.
    """
    if n_shots == 0:
        return ""
    if use_RAG:
        processor = lambda _: "{context}"
    else:
        processor = lambda s: process_one_shot_section(s, *get_static_few_shots(metrics, n_shots, version))
    return process_section(section, "one_shot", processor)

def process_chain_context_section(section:str, prev_outputs:db.PREV_OUTPUTS):
    """
    Processes and multiplies the templates chain context section for each previous output.
    Args:
        section (str): The template section content.
        prev_outputs (PREV_OUTPUTS): The previous outputs from the evaluation chain.
    Returns:
        str: The processed and multiplied section.
    """
    class ChainContextVarToVal(VarToVal):
        @staticmethod
        def get(_:int, prev_output:db.ChainLinkOutput) -> VAR_TO_VAL:
            eval = prev_output.evaluation
            if not eval.is_valid():
                content = eval.dict
                requirement = "error: invalid evaluation"
            else:
                content = eval.content
                requirement = content.get("requirement")
            return {
                "cc_id": str(prev_output.step),
                "cc_req": requirement,
                "cc_eval": sh.format_dict(content),
                "cc_prop": eval.get_proposed_requirement(default="requirement"),
                "cc_metric": prev_output.metrics[0],
                "cc_just": content.get("justification", "no justification")
            }
        
    return multiply_process_section(section, ChainContextVarToVal(), prev_outputs)

def separate_system_and_user_prompt(template:str):
    """
    Separates the system and user prompts from a given template string.
    if no user prompt section is found, the whole prompt is treated as user prompt.

    Args:
        template (str): The template string containing both system and user prompts.

    Returns:
        (str | None, str): (system prompt, user prompt)
    """
    if matches := get_sections(template, "user_prompt"):
        m = matches[0]
        user_prompt:str = m["content"]
        system_prompt = template.replace(m[0], "")
        return [system_prompt, user_prompt]
    return [None, template]

def process_template(
    template:str, metrics:M._list=M.all, use_RAG:bool=False, n_shots:int=0, step:Optional[int]=None, prev_outputs:db.PREV_OUTPUTS=[],
    versions:db.PromptVersions=db.PromptVersions()
):
    """
    The main function to process a template by calling the respective section processors.
    For detailed information on the template structure, see the documentation in `data_base/prompt_templates/template_demo.md`.
    Also see the `template_demo` function for a demonstration of the processing.

    Args:
        template (str): The template string to be processed.
        metrics (M._list, optional): A list of metrics to be used in the processing. Defaults to M.all.
        use_RAG (bool, optional): If True, the RAG chain is invoked. Defaults to False.
        n_shots (int, optional): The number of shots to use for few-shot learning. Defaults to 0.
        step (int, optional): The step number to use for the metric. Defaults to None.
        prev_outputs (PREV_OUTPUTS, optional): The previous outputs from the evaluation chain. Defaults to [].
        versions (cm.PromptVersions, optional): An instance of PromptVersions containing versions of metric and rating definition. Defaults to cm.PromptVersions().
    
    Returns:
        (str, str): The processed system and user prompt.
    """
    template = remove_comments(template)
    section_processors:Dict[SECTION, Callable[[str],str]] = {
        "metric": lambda s: process_metric_section(s, metrics, step, versions),
        "few_shots": lambda s: process_few_shots_section(s, use_RAG, n_shots, metrics, versions.static_few_shots),
        "chain_context": lambda s: process_chain_context_section(s, prev_outputs)
        # add more section processors here
    }
    for section, processor in section_processors.items():
        template = process_section(template, section, processor)
    
    system, user = separate_system_and_user_prompt(template)
    user = escape_curly_braces(user)
    system, user = [remove_irrelevant_new_lines(content) for content in [system, user]]
    return (system, user)
    
def template_demo():
    """
    Demonstrates the processing of a prompt template.
    This function loads the "template_demo.md" from database/prompt_templates/,
    processes the template with specified parameters, and saves the resulting prompt last_messages/last_prompt_1.md.
    """
    template = db.load_prompt_template("template_demo")
    prompt_parts = process_template(
        template, 
        metrics=["Atomicity"], 
        use_RAG=False,
        n_shots=3,
        step=1,
        versions=db.PromptVersions()
    )
    prompt = sh.double_new_lines(prompt_parts)
    db.save_last_message(prompt, "prompt")
    print("template processed and saved to database/last_messages/last_prompt_1.md")