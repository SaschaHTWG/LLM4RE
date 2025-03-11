# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from typing import Callable, Union
import streamlit as ui
from collections.abc import Mapping
from collections import deque
import json
from database_management.db_manager import StreamlitMessage as UIMessage, STREAMLIT_ROLE as ROLE

# define function to display messages of variable types
def display_single(message, role: ROLE, run_in_terminal=False, append_to_session=True):
    if not isinstance(message, UIMessage):
        message = UIMessage(message, role)
    content = message.content
    if run_in_terminal:
        print(f"{message.role}: \n{content}")
        return
    if isinstance(content, Mapping):
        if type(content) == dict:
            message_str = json.dumps(content, indent=4)
        else:
            message_str = str(content)
        display_message = lambda: ui.json(message_str)
    else:
        display_message = lambda: ui.markdown(content)
    with ui.chat_message(message.role):
        display_message()
    if append_to_session:
        # Add message to chat array
        ui.session_state["messages"].append(message.to_dict())
        
def display(message, role:ROLE="user", run_in_terminal=False, append_to_session=True):
    if isinstance(message, tuple) or isinstance(message, list):
        for m in message:
            display_single(m, role, run_in_terminal, append_to_session)
    else:
        display_single(message, role, run_in_terminal, append_to_session)

def chatbot(
    generate_response:Callable[[str], Union[tuple[Union[UIMessage, Mapping, str]], UIMessage, Mapping, str]], 
    intro:str="I am a chatbot",
    input_hint:str="Enter your message here",
    run_in_terminal=False,
    display_user_input=True,
    history_length=5
):
    if run_in_terminal:
        print(intro)
        while(True):
            prompt = input(input_hint + ": ")
            response = generate_response(prompt)
            display(response, "assistant", run_in_terminal)
    

    #define the assistants opening message
    Opening_message = ui.chat_message("assistant")
    Opening_message.write(intro)

    # Initialize empty chat array
    if "messages" not in ui.session_state:
        ui.session_state["messages"] = deque(maxlen=history_length)

    # Display previously sent chat messages
    for message in ui.session_state["messages"]:
        display(message["content"], message["role"], append_to_session=False)

    if prompt := ui.chat_input(input_hint):
        if display_user_input:
            display(prompt, "user")
        display(generate_response(prompt), "assistant")