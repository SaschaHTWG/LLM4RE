# LLM4RE: LLM-based Requirements Engineering Assistant
## Overview 
This is an application for automatically evaluating the quality of requirements based on several quality metrics and associated ratings. By leveraging the capabilites of large language models, its purpose is to uncover potential shortcomings in requirements and thus assissting in the development process. The code was developed as part of the Master's project at HTWG Konstanz, supervised by Prof. Dr.-Ing. Christopher Knievel.

## Functional scope
This tool offers several features such as:
- evaluate individual requirements in a chatbot interface or iterate through dataset
     ![grafik](https://github.com/user-attachments/assets/b758a9a1-39d3-431e-8eba-7744af410cf3) 
- possibilty of using numerous models (e.g. llama3.1, llama3.3)
- different prompt-approaches for evaluating
- judge the quality of generated evaluations with built-in function
- display distribution of evaluations and judgements graphically
  
     ![grafik](https://github.com/user-attachments/assets/47d5079d-ffdf-499e-b093-a9e297276a3b)


## Installation
To install all necessary dependencies, just run the following:
```bash
pip install -r requirements.txt
```

## VS Code Setup
To run streamlit in debug mode add the following configuration to `launch.json`:
```json
{
    "name": "Python:Streamlit",
    "type": "debugpy",
    "request": "launch",
    "module": "streamlit",
    "args": [
        "run",
        "SRC/main.py",
    ]
}
```

# Model Management
At the current development state, LLM4RE enables models provided by the Groq API as well as (chargeable) Anthropic models, which can be found in `SRC\database_management\db_manager.py`:
```bash
ANTHROPIC_MODEL = Literal[
    "claude-3-5-sonnet-latest", 
    "claude-3-5-haiku-latest"
]

GROQ_MODEL = Literal[
    "llama3-8b-8192",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]
```
As groq recently updates their models, the currently used models may be discarded in the future. Therefore, it might be required to update the models in the aforementioned file according to the overview of [supported models](https://console.groq.com/docs/models) by groq.

## Configuration Setup
The user can choose between different options in `main.py`:
```bash
main(
        mode="dataset",                            #choose between evaluation by chatbot or dataset
        eval_model="llama-3.1-8b-instant",         #choose between previously set large language models
        evaluation_mode="iterative",               #choose between iterative and successive mode
        judge_evaluation=False,                    #enable or disable judge evaluation
        judgement_mode="iterative"                 #choose between iterative and successive judge
    )
```
Evaluations can be created by either using a chatbot-interface or iterating through a dataset. If the latter is chosen, the name of the dataset as well as the number of evaluations need to be chosen in `main.py`:
```bash
return evaluate_dataset(
            generate_response, 
            model=eval_model,
            dataset_name="bad_requirements",         #choose dataset to be evaluated
            eval_approach=evaluation_mode,
            eval_type="judgements" if judge_evaluation else "evaluations",
            judge_approach=judgement_mode,
            field_name="Requirement",
            stop_idx=1                               #choose number of evaluations
        )
```

## Usage
After configurating the desired functionality, the program can be executed according to the users choice:
- To run the chatbot within the streamlit framework, execute from project directory:
    ```bash
    streamlit run SRC/main.py
    ```
- To iterate through the dataset, `main.py` can be debugged as a normal python file.

### Analysis
In order to interpret the results, evaluations as well as judgements can be displayed visually. The respective adjustments can be modified in `evaluation_plotter.py`:

```bash
def plot(plot_type:Literal["evaluation_rating_distribution", "evaluation_judgement_scatter"]):
    if plot_type == "evaluation_rating_distribution":
        plot_evaluation_rating_distribution(
            datasets=["average_requirements"],                                 #choose dataset to be displayed
            eval_approaches=["iterative"],                                       #choose between apporaches
            evaluators=["llama-3.1-8b-instant", "claude-3-5-haiku-latest"],      #choose between evaluations by model
            plot_metrics=["Metric Difference"],                                  #choose metric to be displayed
            difference_to=("successive", "human"),                               #choose reference
            merge_datasets=True,
            cut_to_equal_length=-1
        )
    elif plot_type == "evaluation_judgement_scatter":
        scatter_evaluation_and_judgement_ratings(
            datasets=get_args(db.TEST_DATA),
            eval_approches=get_args(db.EVAL_APPROACH),
            evaluators=["llama-3.1-8b-instant", "claude-3-5-haiku-latest"]        #choose between evaluations by model
        )
```
The type of plot can be set in the same file. To generate the plots, debug `evaluation_plotter.py`.

### Tracing with [Langsmith](https://smith.langchain.com/)
To enable Tracing with Langsmith, generate an own API key from the link above and use `enable_tracing()` from `langsmith_tracing.py`

## License
This project is licensed under the MIT License - see the [LICENSE](https://github.com/SaschaHTWG/LLM_for_RE/blob/development/LICENCE) file for details.
