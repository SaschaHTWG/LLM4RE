# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from langchain_groq import ChatGroq
from groq import BadRequestError
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, ValidationError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.outputs import ChatGeneration
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains.conversation.base import ConversationChain
from langchain_core.output_parsers import BaseLLMOutputParser
from langchain_core.runnables.base import Runnable
from typing import Literal, Union, get_args, List, Callable
import json
from database_management import db_manager as db, string_helper as sh

LLM_INPUT = Union[str, BaseMessage, List[BaseMessage], PromptValue]
LLM_OUTPUT = Union[BaseMessage, dict]

LLM_TYPE = Runnable[LLM_INPUT, LLM_OUTPUT]

class ConversationOutputParser(BaseLLMOutputParser):
    def parse_result(self, result, *, partial = False):
        if type(output:=result[-1]) == ChatGeneration:
            return repr(output.message)
        else:
            return output.text

class LLMwithJsonStrOutput(Runnable):
    """
    Wrapper for a BaseChatModel that returns a structured output in form of a `dict` object as a json string.
    This is required, when using an LLM with Memory, as the ConversationChain expects a string as output.
    """
    def __init__(self, llm:BaseChatModel):
        self.llm = llm
    
    def invoke(self, input:str, config=None, **kwargs):
        return json.dumps(self.llm.invoke(input, config, **kwargs), indent=4)
    
class LLMwithMemory(Runnable):
    def __init__(self, llm:BaseChatModel, memory_size:int=0, structured_output:bool=False):
        self.structured_output = structured_output
        self.conversation = ConversationChain(
            llm=LLMwithJsonStrOutput(llm) if structured_output else llm,
            memory=ConversationBufferWindowMemory(k=memory_size),
            output_parser=ConversationOutputParser()
        )
    
    def invoke(self, input:str, config=None, **kwargs) -> Union[AIMessage, dict]:
        # when using structured output, the output will be a json string (due to the LLMwithJsonStrOutput wrapper),
        # so we need to parse it back to a dict object
        parse_output = json.loads if self.structured_output else eval
        return parse_output(self.conversation.predict(input=input))
    
    def reset_memory(self):
        self.conversation.memory.clear()

class LLMGroq(Runnable):
    """Wrapper for Groq Language Models"""
    def __init__(self, model:db.GROQ_MODEL, structured_output=False):
        self.model = model
        self.structured_output = structured_output
        llm = ChatGroq(
            model=self.model,
            temperature=0.0,
            api_key=db.GROQ_API_KEY
        )
        if structured_output:
            llm = llm.with_structured_output(None, method="json_mode")
        self.llm = llm
    
    def invoke(self, input:str, config=None, **kwargs):
        try:
            return self.llm.invoke(input, config, **kwargs)
        except BadRequestError as e:
            return e.message

class LLMAnthropic(Runnable):
    """Wrapper for Anthropic Language Models, that supports schema based structured output"""
    def __init__(self, model:db.ANTHROPIC_MODEL, structured_output:bool=True, schema:BaseModel=None):
        self.llm = ChatAnthropic(
            model=model,
            temperature=0.0,
            api_key=db.ANTHROPIC_API_KEY,
            #max_tokens=1024 #might make sense to enable this for testing purposes
        )
        if structured_output:
            self.output_parser:Callable[
                [Union[BaseModel, any]], Union[dict, any]
            ] = lambda output: output.model_dump()
            self.llm = self.llm.with_structured_output(schema, include_raw=False)
        else:
            self.output_parser = lambda output: output
    
    def invoke(self, input:str, config=None, **kwargs):
        try:
            return self.output_parser(self.llm.invoke(input, config, **kwargs))
        except ValidationError as e:
            return json.loads(e.json())

class LLM(Runnable):
    """General Wrapper for Language Models, that supports both Anthropic and Groq models, structured output and a variable memory size"""
    def __init__(self, model:db.MODEL, structured_output=True, schema:BaseModel=None, memory_size:int=0):
        self.invoke_count = 0
        self.model = model
        self.structured_output = structured_output
        self.memory_size = memory_size
        self.schema = schema
        self.llm = self._init_llm()

    def _init_llm(self) -> LLM_TYPE:
        if self.model in get_args(db.ANTHROPIC_MODEL):
            llm = LLMAnthropic(self.model, self.structured_output, self.schema)
        elif self.model in get_args(db.GROQ_MODEL):
            llm = LLMGroq(self.model, self.structured_output)
        else:
            raise ValueError(f"Model {self.model} not supported")
        if self.memory_size > 0:
            llm = LLMwithMemory(llm, self.memory_size, self.structured_output)
        return llm

    def _save_message(self, message: Union[LLM_INPUT, LLM_OUTPUT], type:Literal["prompt", "response"]):
        if isinstance(message, PromptValue):
            content = message.to_string()
        elif isinstance(message, list):
            content = sh.double_new_lines([m.content for m in message])
        elif isinstance(message, BaseMessage):
            content:str = message.content
        elif isinstance(message, dict):
            content = sh.format_dict(message, escape_brackets=False)
        else:
            content = message
        db.save_last_message(content, type, self.invoke_count)
        return message
    
    def invoke(self, input:LLM_INPUT, config = None, **kwargs) -> LLM_OUTPUT:
        """Invoke the Language Model and save the last 20 prompts and responses to `database/last_message`"""
        if self.invoke_count > 20:
            self.invoke_count = 0
        self.invoke_count += 1
        return self._save_message(self.llm.invoke(
            self._save_message(input, "prompt"), 
            config, **kwargs
        ), "response")
    
    def reset_memory(self):
        if isinstance(self.llm, LLMwithMemory):
            self.llm.reset_memory()

    def update_schema(self, schema:BaseModel):
        """Interface to the `EvaluationChain` Module to adapt the output schema for different prompt steps"""
        self.schema = schema
        self.llm = self._init_llm()
