# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

import database_management.db_manager as db
from database_management.db_manager import Metrics as M
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import seaborn as sns
from typing import Literal, List, get_args, Dict, Optional, Union, Tuple
import numpy as np

EVAL_TYPE = Literal["successive", "iterative"]
PLOT_METRIC = Literal[M._single, "Overall", "Worst Metric", "Overall Difference", "Metric Difference", "Proposed Requirement"]

def plot_evaluation_rating_distribution(
    datasets: List[db.TEST_DATA], eval_approaches: List[db.EVAL_APPROACH], evaluators: List[db.EVALUATOR],
    plot_metrics: PLOT_METRIC = M.all, difference_to: Tuple[db.EVAL_APPROACH, db.EVALUATOR] = ("successive", "human"),
    merge_datasets: bool = False, cut_to_equal_length: int = 0
):
    """
    Plots the distribution of evaluation ratings for given datasets, evaluation approaches, and evaluators.
    
    Args:
        datasets (List[db.TEST_DATA]): refers to dataset names in the `data_base/test_data` directory.
        eval_approaches (List[db.EVAL_APPROACH]): List of evaluation approaches to consider.
        evaluators (List[db.EVALUATOR]): List of evaluators to consider.
        plot_metrics (PLOT_METRIC, optional): Metrics to plot. Defaults to M.all.
        difference_to (Tuple[db.EVAL_APPROACH, db.EVALUATOR], optional): Reference approach and evaluator for difference calculations. Defaults to ("successive", "human").
        merge_datasets (bool, optional): Whether to merge the different datasets in the plot. Defaults to False.
        cut_to_equal_length (int, optional): Cut ratings to specific equal length . If 0, no cutting is applied. If -1, cut to the minimum length. Defaults to 0.
    """
    def get_ratings_of_dataset(
        dataset:db.TEST_DATA, eval_approach:db.EVAL_APPROACH, evaluator:db.EVALUATOR
    ) -> Optional[Dict[PLOT_METRIC, List[int]]]:
        file_name = db.get_dataset_file_name(dataset, evaluator, "evaluations", eval_approach)
        if not (eval_dict := db.load_dict_from_json_file(file_name, db.test_data)):
            return None
        evaluations:List[Dict[str, Union[dict, any]]] = eval_dict["evaluations"]
        rating_dict:Dict[PLOT_METRIC, List[int]] = {
            metric: [d["rating"] for e in evaluations for m, d in e["evaluation"].items() if m == metric] 
            for metric in list(set(plot_metrics).intersection(M.all))
        }
        if "Overall" in plot_metrics:
            rating_dict["Overall"] = [e["overall_rating"] for e in evaluations]
        if "Worst Metric" in plot_metrics:
            rating_dict["Worst Metric"] = [min([d["rating"] for d in e["evaluation"].values()]) for e in evaluations]
        if set(["Overall Difference", "Metric Difference"]) & set(plot_metrics):
            ref_approach, ref_evaluator = difference_to
            ref_eval_file = db.get_dataset_file_name(dataset, ref_evaluator, "evaluations", ref_approach)
            if not (ref_eval_dict := db.load_dict_from_json_file(ref_eval_file, db.test_data)):
                return None
            ref_evals = ref_eval_dict["evaluations"]
            if "Overall Difference" in plot_metrics:
                rating_dict["Overall Difference"] = [
                    np.abs(ev["overall_rating"] - ref["overall_rating"]) for ev, ref in zip(evaluations, ref_evals)
                ]
            else: # if "Metric Difference" in plot_metrics
                r = lambda e, m: e["evaluation"][m]["rating"]
                rating_dict["Metric Difference"] = [
                    np.abs(r(ev, m) - r(ref, m)) for m in M.all for ev, ref in zip(evaluations, ref_evals)
                ]
        if "Proposed Requirement" in plot_metrics:
            file_name = db.get_dataset_file_name(dataset, evaluator, "judgements", eval_approach)
            if not (judgement_dict := db.load_dict_from_json_file(file_name, db.test_data)):
                return None
            judgements = judgement_dict["judgements"]
            rating_dict["Proposed Requirement"] = [
                j["Assessment_of_proposed_requirement"]["overall_alignment_with_metrics"] for j in judgements
            ]
        return rating_dict
    
    def plot_rating_distribution(ax:Axes, ratings:Dict[str, List[int]], min_val:int=1, max_val:int=5):
        data = list(ratings.values())
        print("Sum:", sum([sum(d) for d in data]))
        weights = [np.ones(len(d)) / len(d) for d in data]
        ax.hist(data, histtype="bar", weights=weights, range=[min_val,max_val+1], label=ratings.keys(), align="left")
        ax.set_xticks(range(min_val, max_val+1))
        ax.set_ylim(0, 1)
    
    ratings:Dict[PLOT_METRIC, Dict[str, List[int]]] = {}
    for evaluator in evaluators:
        for eval_approach in eval_approaches:
            for dataset in datasets:
                if not (d_ratings := get_ratings_of_dataset(dataset, eval_approach, evaluator)):
                    continue
                label = eval_approach[:4] if merge_datasets else f"{eval_approach[:4]}/{dataset[:-13]}"
                label = f"{label}/{evaluator}"
                for metric, d_r in d_ratings.items():
                    if metric not in ratings:
                        ratings[metric] = {}
                    ratings[metric][label] = ratings[metric].get(label, []) + d_r if merge_datasets else d_r
    
    if (num_plots:=len(ratings)) <= 4:
        nrows, ncols = num_plots, 1
    else:
        ncols = 2
        nrows = int(num_plots / 2 + 0.5)
    _, axs = plt.subplots(nrows, ncols)
    axs:List[Axes] = np.array(axs).flatten().tolist()
    for ax, (metric, m_ratings) in zip(axs, ratings.items()):
        if cut_to_equal_length:
            min_len = min([len(d) for d in m_ratings.values()])
            if cut_to_equal_length > 0:
                min_len = min(min_len, cut_to_equal_length)
            m_ratings = {k: v[:min_len] for k, v in m_ratings.items()}
        if metric in ("Overall", "Overall Difference"):
            for label, data in m_ratings.items():
                sns.kdeplot(data, ax=ax, label=label, bw_adjust=0.5)
            ax.set_xlim(0, 1)
        else: 
            range_vals = (0, 4) if metric == "Metric Difference" else (1, 5)
            plot_rating_distribution(ax, m_ratings, *range_vals)
        title = metric
        xlabel = "Rating"
        if "Difference" in metric:
            title += f" to {'/'.join(difference_to)}"
            xlabel = r"$\Delta$ " + xlabel
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.legend()
    plt.tight_layout()
    plt.show()



def scatter_evaluation_and_judgement_ratings(
    datasets:List[db.TEST_DATA], 
    eval_approches:List[db.EVAL_APPROACH], 
    evaluators:List[db.EVALUATOR]
):
    """
    The function retrieves judgements for each combination of evaluation approach and evaluator,
    then plots scatter plots and regression lines for the overall requirement rating versus the 
    overall evaluation rating. It also prints the requirements of the best and worst evaluations based on the ratings.

    Args:
        datasets (List[db.TEST_DATA]): List of datasets to be evaluated.
        eval_approches (List[db.EVAL_APPROACH]): List of evaluation approaches.
        evaluators (List[db.EVALUATOR]): List of evaluators.

    """
    def get_judgements(eval_approach:db.EVAL_APPROACH, dataset:db.TEST_DATA, evaluator:db.EVALUATOR) -> Optional[List[dict]]:
        return db.load_dict_from_json_file(
            file_name=db.get_dataset_file_name(dataset, evaluator, "judgements", eval_approach),
            subdir=db.test_data
        ).get("judgements", [])
    
    def get_data_points(eval_approach:db.EVAL_APPROACH, evaluator:db.EVALUATOR) -> Tuple[List[dict], np.ndarray]:
        judgements = [j for d in datasets for j in get_judgements(eval_approach, d, evaluator)]
        return judgements, np.array([(j["overall_requirement_rating"], j["overall_evaluation_rating"]) for j in judgements])
    
    for evaluator in evaluators:
        for eval_approach in eval_approches:
            judgements, data = get_data_points(eval_approach, evaluator)
            if len(data) != 0:
                label = f"{eval_approach}/{evaluator}"
                x, y = data[:, 0], data[:, 1]
                sns.regplot(x=x, y=y, order=2, scatter=True)
                plt.scatter(x, y, label=label)
                for np_func, type in zip([np.argmax, np.argmin], ["best", "worst"]):
                    print(f"{label} {type} Evaluation: {judgements[np_func(y)]['original_requirement']}")

    plt.ylim(0, 1.1)
    plt.xlabel("Evaluation")
    plt.ylabel("Judgement")
    plt.title("Evaluation and Judgement Ratings")
    plt.legend()
    plt.show()


def plot(plot_type:Literal["evaluation_rating_distribution", "evaluation_judgement_scatter"]):
    if plot_type == "evaluation_rating_distribution":
        plot_evaluation_rating_distribution(
            datasets=["average_requirements"], 
            eval_approaches=["iterative"],
            evaluators=["llama-3.1-8b-instant"],
            plot_metrics=["Metric Difference"],
            difference_to=("successive", "claude-3-5-haiku-latest"),
            merge_datasets=True,
            cut_to_equal_length=-1
        )
    elif plot_type == "evaluation_judgement_scatter":
        scatter_evaluation_and_judgement_ratings(
            datasets=get_args(db.TEST_DATA),
            eval_approches=get_args(db.EVAL_APPROACH),
            evaluators=["llama-3.1-8b-instant", "claude-3-5-haiku-latest"]
        )

    
    
    
# Call the function to plot the data
if __name__ == "__main__":
    plot("evaluation_rating_distribution")