from typing import Union, Sequence
import uuid
import os
import time
import add_packages

import streamlit as st
from streamlit_feedback import streamlit_feedback

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable

from toolkit.langchain import (
  chat_models, agent_tools, prompts, agents, smiths, runnables
)

from toolkit.streamlit import utils
from toolkit.streamlit.utils import CHAT_ROLE, MSG_ITEM

#*==============================================================================

st.set_page_config(
  layout="wide",
)

# st.sidebar.page_link(f"pages/1_general_chat.py", label="General Chat")

#*==============================================================================