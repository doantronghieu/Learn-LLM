import add_packages
import asyncio
import os
from typing import Union
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from toolkit.langchain import (
  models, agents, prompts, runnables, smiths, memories, tools
)
#*==============================================================================

PROJECT_LS = "default" # LangSmith
ENDPOINT_LC = "https://api.smith.langchain.com" # LangChain
CLIENT_LC = smiths.Client(
  api_url=ENDPOINT_LC, api_key=os.getenv("LANGCHAIN_API_KEY")
)
TRACER_LS = smiths.LangChainTracer(project_name=PROJECT_LS, client=CLIENT_LC)
RUN_COLLECTOR = smiths.RunCollectorCallbackHandler()

callbacks = [TRACER_LS, RUN_COLLECTOR]

#*------------------------------------------------------------------------------

DEFAULT_USER_ID = "admin"
DEFAULT_SESSION_ID = "default"

#*------------------------------------------------------------------------------

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  expose_headers=["*"],
)

@app.get("/")
async def redirect_root_to_docs():
  return RedirectResponse("/docs")

#*------------------------------------------------------------------------------

my_llm = models.chat_openai
my_tools = [
	tools.TavilySearchResults(max_results=3)
]
my_prompt = prompts.create_prompt_tool_calling_agent()

my_agent = agents.MyStatelessAgent(
	llm=my_llm,
	tools=my_tools,
	prompt=my_prompt,
	agent_type='tool_calling',
	agent_verbose=False,
)

#*==============================================================================
@app.get("/health")
def health_check():
  return JSONResponse(content={"status": "healthy"})

@app.get('/langchain-chat-history')
async def get_langchain_chat_history(
  user_id: Union[str, None]  = DEFAULT_USER_ID,
  session_id: Union[str, None]  = DEFAULT_SESSION_ID,
):
  result = None
  if os.getenv("MSG_STORAGE_PROVIDER") == "dynamodb":
    langchain_session_dynamodb_table = memories.LangChainSessionDynamodbTable()
    result = langchain_session_dynamodb_table.get_session_ids(user_id)
  elif os.getenv("MSG_STORAGE_PROVIDER") == "mongodb":
    result = "TODO: get_langchain_chat_history for `mongodb`"
  return result

#*------------------------------------------------------------------------------

def stream_generator_chat_model(
  query: str,
  chat_model: runnables.Runnable,
):
  for token in chat_model.stream(query):
    yield(token.content)

@app.get("/stream-chat-model")
async def stream_chat_model(
  query: str = "Hello",
):
  return StreamingResponse(
    stream_generator_chat_model(query, models.chat_openai),
    media_type='text/event-stream',
  )

#*------------------------------------------------------------------------------

def stream_generator_agent(
  agent: agents.MyStatelessAgent,
  query: str,
	history_type: str=os.getenv("MSG_STORAGE_PROVIDER"),
  user_id=None,
	session_id: str=DEFAULT_SESSION_ID,
):
  return agent.astream_events_basic(
    input_message=query,
    history_type=history_type,
    user_id=user_id,
    session_id=session_id,
    show_tool_call=False if os.getenv("IN_PROD") else True,
  )

@app.get("/stream-agent")
async def stream_agent(
  request: Request,
  query: str="Hello",
  history_type: str=os.getenv("MSG_STORAGE_PROVIDER"),
  user_id=None,
  session_id: str=DEFAULT_SESSION_ID,
):
  return StreamingResponse(
    stream_generator_agent(
      agent=my_agent,
      query=query, 
      history_type=history_type,
      user_id=request.client.host if (user_id is None or user_id == "") 
        else user_id,
      session_id=session_id,
    ),
    media_type='text/event-stream',
  )

@app.get("/invoke-agent")
async def invoke_agent(
  request: Request,
  query: str="Hello",
  history_type: str=os.getenv("MSG_STORAGE_PROVIDER"),
  user_id=None,
  session_id: str=DEFAULT_SESSION_ID,
):
  return Response(
    content=await my_agent.invoke_agent(
      query,
      history_type=history_type,
      user_id=request.client.host if (user_id is None or user_id == "") 
        else user_id,
      session_id=session_id,
    ),
  )

@app.get("/agent-chat-history")
async def get_agent_chat_history(
  request: Request,
  history_type: str=os.getenv("MSG_STORAGE_PROVIDER"),
  user_id=None,
  session_id: str=DEFAULT_SESSION_ID,
):
  history = my_agent._create_chat_history(
    history_type=history_type,
    user_id=request.client.host if (user_id is None or user_id == "") 
        else user_id,
		session_id=session_id,
  )
  result = await history._get_chat_history()
  return result

@app.delete("/agent-chat-history")
async def clear_agent_chat_history(
  request: Request,
  history_type: str=os.getenv("MSG_STORAGE_PROVIDER"),
  user_id=None,
  session_id: str=DEFAULT_SESSION_ID,
):
  history = my_agent._create_chat_history(
    history_type=history_type,
    user_id=request.client.host if (user_id is None or user_id == "") 
        else user_id,
		session_id=session_id,
  )
  return await history.clear_chat_history()

#*==============================================================================

# uvicorn server:app --host=0.0.0.0 --port=8000