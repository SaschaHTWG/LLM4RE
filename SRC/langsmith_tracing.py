# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

import os

def enable_tracing(project_name:str="LLM4RE", enable:bool=True):
    if enable:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = "<insert your api key here>"
        os.environ["LANGCHAIN_PROJECT"] = project_name