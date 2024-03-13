from langchain.agents import (
  create_openai_tools_agent, create_openai_functions_agent, 
  create_openapi_agent,
  AgentExecutor
)


def invoke_agent_executor(agent_executor: AgentExecutor, input_str):

    return agent_executor.invoke({
        "input": input_str
    })["output"]
