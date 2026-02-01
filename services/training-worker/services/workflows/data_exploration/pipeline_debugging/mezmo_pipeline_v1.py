import operator
import os

import streamlit as st
import re

from langchain_community.tools import ShellTool
from datetime import datetime, UTC
from typing import TypedDict, List, Annotated, Tuple, Union, Dict

from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.tools import tool
from langchain.agents import Tool
from langgraph.constants import END
from langgraph.graph import START
from langgraph.prebuilt import create_react_agent
from langmem import create_manage_memory_tool, create_search_memory_tool
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph

from services.cache.memory_cache import initialize_memory_cache
from services.utils.logger import logger
from services.utils.graphrag.graphrag_query_local import GraphRAGLocalSearch
from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v4 import initialize_brewsearch_state_workflow
from services.customer.personalization import get_project_config


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: Dict[str, List[str]] = Field(
        description="different steps to follow, should be in sorted order. Each step should be consolidated as array element."
    )

class Task(BaseModel):
    """Task Information"""

    type: str = Field(
        description="task type",
    )
    metadata: List[str] = Field(
        description="extracted attributes from the task alert"
    )

class Response(BaseModel):
    """Response to user."""

    response: str

class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )

class PlanExecute(TypedDict):
    question: str
    plan: List[str]
    tools: List[str]
    context: List[str]
    hint_content: str
    task_info: Task
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    attributes: str
    user_hints: str
    extracted_values: str

async def ainvoke_graphrag_search_local_cache(question, response_type, project):
    global graph_rag_local
    graph_rag_local = GraphRAGLocalSearch(project)
    if graph_rag_local:
        return await graph_rag_local.search(question, response_type)
    else:
        raise IndexError("GraphRag resource not setup correctly or not available.")

MAX_TOKENS = 100000  # Adjusted to stay well within limits # OR 124000
RETRIES = 5 # In case any llm cals failes
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
MODEL = os.environ.get("MODEL", "gpt-4o")
MINI_MODEL = os.environ.get("MINI_MODEL", "gpt-4o-mini")
REASONING_MODEL = os.environ.get("REASONING_MODEL", "o3-mini")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "chatgpt-4o-latest")
SEED = int(os.environ.get("SEED", "101"))

checkpoint_memory, vector_store, mem_store = initialize_memory_cache(EMBEDDING_MODEL)
graph_rag_local = None

@st.cache_resource
def initialize_memzo_api_workflow_agent(user, project):
    if project.lower() == "Mezmo".lower():
        rag_app = initialize_brewsearch_state_workflow(user, project, False, False)
    else:
        rag_app = None

    # Initialize OpenAI components
    llm = ChatOpenAI(model=MODEL, temperature=0, seed=SEED) # update to (model="gpt-4o"), for Usage Tier > 1.0
    llm_mini = ChatOpenAI(model=MINI_MODEL, temperature=0, seed=SEED)
    # reasoning_llm = ChatOpenAI(model=MODEL, temperature=0)
    reasoning_llm = ChatOpenAI(model=REASONING_MODEL, seed=SEED) # update to (model="o3-mini"), for Usage Tier > 1.0
    chat_llm = ChatOpenAI(model=CHAT_MODEL, temperature=0, seed=SEED) # update to (model="chatgpt-4o-latest"), for Usage Tier > 1.0

    trimmer = trim_messages(
        max_tokens=MAX_TOKENS,
        strategy="last",
        token_counter=llm_mini,
        include_system=True,
    )

    # Step 1:
    project_config = get_project_config(project)
    if not project_config:
        return None

    task_expert_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert at deciding the correct type of the incident/task for the incoming question/topic/alert.
The task could be related to pipeline debugging or log analysis issue or more, specific to mezmo platform.

Note: 
* Goal is to provide the right type of the task.
* Include all extracted information from input (issue/ticket) body.

===
Example:
Task: Consumer group lag over 2M
type - pipeline_source_lag
extracted metadata -
* consumer_group = ""
* pagerduty_task_id = ""
* kube_cluster_name = ""
* metrics = ""
* metric_value = ""
* severity = ""
* ...

Task: Unhealthy Kafka Consumer Group
Response Hint: 
type - pipeline_source_lag
extracted metadata -
* consumer_group = ""
* pagerduty_task_id = ""
* kube_cluster_name = ""
* metrics = ""
* metric_value = ""
* severity = ""
* ...

Task: [CronJob][es-tamemappings-job] Has been active too long.
Response Hint: 
type - pipeline_source_lag
extracted metadata -
* consumer_group = ""
* pagerduty_task_id = ""
* pagerduty_assignees = ""
* ...

Task: Optimize pipeline id: <> or debug for inefficiencies in pipeline id: <>
Response Hint:
type - inefficient_pipeline_debugging 
extracted metadata -
* pipeline_id = ""
* ...
""",
            ),
            ("placeholder", "{messages}"),
        ]
    )

    task_expert_chain = task_expert_prompt | llm_mini.with_structured_output(Task)

    planner_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """As a world class Mezmo (logdna) platform expert and data engineer, for the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks (strictly, in the scope of API call), that if executed correctly will yield the correct answer. \
Do not add any superfluous steps. The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Note:
* MUST: Include as much as details, as needed, in each step; for an executor to pick up and execute
* Always validate an API call before execution
* AlWAYS validate if all the required attributes/headers are provided in the user query, if not respond with asking for more information
* The plan steps for execution should be very specific and not vague, for the executor to take proper action on
* Please DO NOT answer the user questions without the memzo apis execution
* Existing scope is to leverage api calls for any Mezmo system related question; so plan should be finalizing the endpoint to call.
* Any required attributes/headers can be expected to be available in environment variables and how to get those attributes/headers. If not, find it in the past steps results.
* ALWAYS explore all available APIs for any additional information which could be helpful for the investigation

======

Example:
Task: Consumer group lag over 2M
type: pipeline_source_lag
plan hint - details debugging steps for task type pipeline_source_lag

Task: Unhealthy Kafka Consumer Group
type: pipeline_source_lag
plan hint - details debugging steps for task type pipeline_source_lag

Task: Optimize/Debug pipeline
type: inefficient_pipeline_debugging
plan hint - details debugging steps for task type inefficient_pipeline_debugging
step_1: Retrieve the `log_analysis_id` so we can populate `x-auth-account-id` for all public API calls.
step_2: Fetch the latest pipeline revision to get component definitions.
step_3: Reconstruct the pipeline DAG in memory.
step_4: Fetch runtime metrics for each component.
step_5: Analyze metrics to pinpoint bottlenecks and high-drop areas.
step_6: Tap sample data from each flagged node to verify transform logic.
step_7: Compile and deliver the final optimization report.

======
Response:
[Strictly] Format - json:
a dict with key "steps" as per the planning decision. 
"steps" would have a list of (str) steps as an array value. "response" would have an string value.
```json
{{
    "steps": {{
        "step_1": [
            "Step 1. Retrieve the Log Analysis ID.",
            "Endpoint URL: {{PIPELINE_API_ENDPOINT}}/internal/source/8f09b3da-e57f-11ef-926a-c277425aded1.",
            "Expected Response: A JSON containing the log_analysis_id (for example, {{ 'log_analysis_id': 'YOUR_LOG_ANALYSIS_ID' }})."
        ],
        "step_2": [
            "Step 2. Retrieve the Latest Pipeline Revision.",
            "Endpoint URL: {{PIPELINE_API_ENDPOINT}}/v3/pipeline/22d1237e-e57f-11ef-8b79-c277425aded1/revision/latest.",
            "Expected Response: Pipeline configuration in JSON/TOML format."
        ],
        "step_3": [
            "Step 3. Analyze the Pipeline Configuration",
            . . .
        ]
        . . .
    }}
}}
```
        """,
            ),
            ("placeholder", "{messages}"),
        ]
    )
    # planner_chain = planner_prompt | trimmer | llm.with_structured_output(Plan)
    plan_parser = JsonOutputParser(pydantic_object=Plan)
    planner_chain = planner_prompt | trimmer | reasoning_llm | plan_parser

    replanner_prompt = ChatPromptTemplate.from_template(
        """As a world class Mezmo platform expert and data engineer, for the given objective, validate the response from the pat steps run. Review the result as per the original goal
and if it doesn't answer the user question, come up with a simple step by step plan, based on the original plan. 
This plan should involve individual tasks (strictly, in the scope of API call), that if executed correctly will yield the correct answer. Do not add any superfluous steps. 
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Note:
* MUST: Include as much as details, as needed, in each step; for an executor to pick up and execute
* MUST: Each execution step should be followed by an analysis/validation step, to fetch information/learning from the last step's results
* DO NOT repeat steps specially like creation, deletion or modification of resources, without validating the previous steps
* ALWAYS refer to the past steps results to make sure the actions are not repeated, specially if related to creation, update or delete of resources
* If an action has been executed successfully, make sure to build on top of previous results; for example, if pipeline has been created and requires some updates, do not create a new pipeline with each step, rather use the existing one
* ALWAYS validate if all the required attributes are provided in the user query, if not respond with asking for more information
* The plan steps for execution should be very specific and not vague, for the executor to take proper action on
* Please DO NOT answer the user questions without the memzo apis execution
* Existing scope is to leverage api calls for any Mezmo system related question; so plan should be finalizing the endpoint to call.
* Any required attributes/headers can be expected to be available in environment variables and how to get those attributes/headers. **If not, find it in the past steps results.**
* ALWAYS explore all available APIs for any additional information which could be helpful for the investigation
* If you see current steps in the past steps, then fail and cancel
* If any of the executor errors talk about wrong headers, check in the past steps again, for the correct value
* Even after multiple tries, if any resource is not available, inform the user and finish the planning iteration

======

{user_hints}

======

Example:
Task: Consumer group lag over 2M
type: pipeline_source_lag
plan hint - details debugging steps for task type pipeline_source_lag

Task: Unhealthy Kafka Consumer Group
type: pipeline_source_lag
plan hint - details debugging steps for task type pipeline_source_lag

Task: Optimize/Debug pipeline
type: inefficient_pipeline_debugging
plan hint - details debugging steps for task type inefficient_pipeline_debugging

======
Task Info:
{task_info}

Your original plan was this:
{plan}

Available Tools:
{tools}

[**MUST CONSIDER**] Knowledge Graph Response/Context:
{context}

Existing Runbook:
{hint_content}

Extracted Values so far:
{extracted_values}

**You have currently completed these steps, including responses:**
{past_steps}

=====
Update your plan accordingly. If the last run RESPONSE is correct and no more steps are needed and you can return last output to the user, for addressing the original question. 
Otherwise, fill out the new plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan.

======
Response:
[Strictly] Format - json:
a dict with key "steps" or "response" as per the routing decision and previous step's results. 
"steps" would have a list of (str) steps as an array value. "response" would have an string value.
```json
{{
    "steps": {{
        "step_1": [
            "Step 1. Retrieve the Log Analysis ID.",
            "Endpoint URL: {{PIPELINE_API_ENDPOINT}}/internal/source/8f09b3da-e57f-11ef-926a-c277425aded1.",
            "Expected Response: A JSON containing the log_analysis_id (for example, {{ 'log_analysis_id': 'YOUR_LOG_ANALYSIS_ID' }})."
        ],
        "step_2": [
            "Step 2. Retrieve the Latest Pipeline Revision.",
            "Endpoint URL: {{PIPELINE_API_ENDPOINT}}/v3/pipeline/22d1237e-e57f-11ef-8b79-c277425aded1/revision/latest.",
            "Expected Response: Pipeline configuration in JSON/TOML format."
        ],
        "step_3": [
            "Step 3. Analyze the Pipeline Configuration",
            . . .
        ]
        . . .
    }}
}}
```
or in case of `response`
```json
{{
    "response": "## Validation of Current Progress\n\nThe last executed step (retrieving pipeline health metrics) successfully identified the root cause of the consumer group lag: the connected sink \"A bad destination\" is returning a 405 Method Not Allowed error, indicating the destination endpoint does not accept POST requests. This is a direct and actionable finding. . . ."
}}
```
"""
    )

    # replanner_chain = replanner_prompt | trimmer | llm.with_structured_output(Act)
    act_parser = JsonOutputParser(pydantic_object=Act)
    replanner_chain = replanner_prompt | trimmer | reasoning_llm | act_parser

    synthesize_prompt = ChatPromptTemplate.from_template(
        """As a world class Mezmo (logdna) platform expert and data engineer, for the given objective, come up with the final answer.
Use the following pieces of retrieved answer from executed steps to consolidate and return the best response for the question.
Do not omit any information. Do not make up any information, the final answer should be based on the provided context STRICTLY.

Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach.
If the information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.
Ensure that your final response is in markdown format.
        As a world class Mezmo platform expert, for the given objective, validate the response from the pat steps run. Review the result as per the original goal
and if it doesn't answer the user question, come up with a simple step by step plan, based on the original plan. 
This plan should involve individual tasks (strictly, in the scope of API call), that if executed correctly will yield the correct answer. Do not add any superfluous steps. 
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

======
Your objective was this:
{question}

You have currently done the follow steps:
{past_steps}

Executor Response:
{response}

Validation of the user query, for all required information:
{attributes}

Context:
{context}

Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach. If the 
information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.

If some information is missing from the original query and could have been successful if provided, please respond 
that as required information back to the user. If you see same Step getting executed again, then stop and respond to the user. 
In case, it doesn't succeed, please include the intermediate results to the final response, for transparency."""
    )

    synthesize_chain = synthesize_prompt | chat_llm | StrOutputParser()

    def _fetch_env_vars():
        try:
            env_vars = dict(os.environ)
            return env_vars
        except Exception as e:
            return {"error": f"Failed to fetch environment variables: {str(e)}"}

    @tool
    def fetch_env_vars(input: str = ""):
        """
        Fetch all available environment variables in the system.

        Args:
            input (str): This parameter is not used. It is required to match the tool signature.

        Returns:
            dict: A dictionary of all environment variables and their values.
        """
        return _fetch_env_vars()

    @tool
    def fetch_env_var_value(env_var_name: str):
        """
        Fetch the value of a specific environment variable.

        Args:
            env_var_name (str): The name of the environment variable to fetch.

        Returns:
            str: The value of the requested environment variable, or an error message if not found.
        """
        try:
            value = os.environ.get(env_var_name, "Environment variable not found")
            return value
        except Exception as e:
            return {"error": f"Failed to fetch environment variable '{env_var_name}': {str(e)}"}

    @tool
    def fetch_hint_files(input: str):
        """Fetch hint dir/files for a specific project in its runbook directory.

        Args:
            input (str): empty string.

        Returns:
            list (str): List of all available hint files for specific project.
        """
        file_paths = []
        try:
            for root, dirs, files in os.walk(project_config["runbook_directory"]):
                for file in files:
                    print (file)
                    # Get the file extension and path
                    file_path = os.path.join(root, file)
                    file_paths.append(file_path)
        except Exception as e:
            return f"Error fetching metadata: {str(e)}"
        finally:
            print (file_paths)
            if not file_paths:
                return "empty dir. no runbook files found. use context information."
            return file_paths

    @tool
    def fetch_hint_file(input: str):
        """Fetch hint file for a specific task type.

        Args:
            input (str): File path to fetch the content from.

        Returns:
            list (str): List the content of the passed hint file path.
        """
        hint_content = ""
        api_additional_information = ""
        parent_dir = os.path.dirname(input)
        try:
            api_file_path = os.path.join(parent_dir, "api.md")
            if parent_dir and os.path.exists(api_file_path):
                with open(api_file_path, "r") as f:
                    api_additional_information = f.read()

            with open(input, 'r') as f:
                hint_content = f.read()
        except Exception as e:
            return f"Error fetching metadata: {str(e)}"
        finally:
            if api_additional_information:
                hint_content = api_additional_information + "\n\n---\n\n" + hint_content
            return hint_content

    task_hint_tools = [
        # Memory tools use LangGraph's BaseStore for persistence (4)
        create_manage_memory_tool(namespace=("memories",)),
        create_search_memory_tool(namespace=("memories",)),
        Tool(
            name="HintFilesInRunbookDir",
            func=fetch_hint_files,
            description="Useful to get list of hint files in the project's runbook directory."
                        "Input: Empty String",
            handle_tool_error=lambda e: f"Error occurred: {e}"
        ),
        Tool(
            name="TaskSpecificHintFile",
            func=fetch_hint_file,
            description="Useful to get content of the target hint file in the project's runbook directory."
                        "Input: task type hint file path",
            handle_tool_error=lambda e: f"Error occurred: {e}"
        ),
    ]

    shell_tool = ShellTool()
    # python_repl = PythonREPL()
    execution_tools = [
        # Memory tools use LangGraph's BaseStore for persistence (4)
        create_manage_memory_tool(namespace=("memories",)),
        create_search_memory_tool(namespace=("memories",)),
        # Tool(
        #     name="python_repl",
        #     description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
        #     func=python_repl.run,
        #     args_schema=PythonREPLInput
        # ),
        Tool(
            name="FetchEnvVarsListAvailable",
            func=fetch_env_vars,
            description="Useful to fetch list fo env variables accessible in the environment."
                        "Input: empty string",
            handle_tool_error=lambda e: f"Error occurred: {e}"
        ),
        Tool(
            name="FetchEnvVarValue",
            func=fetch_env_var_value,
            description="Useful to fetch target env variable value."
                        "Input: env var name",
            handle_tool_error=lambda e: f"Error occurred: {e}"
        ),
        shell_tool
    ]

    async def rag_store(query, breakdown = False, load_data = False, concise = True):
        inputs = {
            "question": query,
            "breakdown": breakdown,
            "load_data": load_data,  # defaults to no data validation rn
            "concise": concise,
            "global_flag": load_data
        }
        config = {
            "recursion_limit": 20,
            "configurable": {
                "thread_id": "chicory-ui-discovery",
                "thread_ts": datetime.now(UTC).isoformat(),
                "client": "brewmind",
                "user": user,
                "project": project,
            }
        }
        response = ""
        if rag_app:
            async for event in rag_app.astream(
                    inputs, config=config):
                for key, value in event.items():
                    logger.info(f"Node '{key}':")
                    logger.info(f"{value}'")
            if 'generation' in value:
                response = value["generation"]
            elif 'data_summary' in value:
                response = value["data_summary"]
            else:
                response = value
        return {"response": response}

    def handle_agent_error(error):
        if isinstance(error, str):
            return {"error": error}
        return {"error": str(error)}

    async def task_expert_step(state: PlanExecute):
        query = state["question"]
        env_vars = _fetch_env_vars()
        env_vars_str = ",".join(env_vars)
        task_information = await task_expert_chain.ainvoke({
            "messages": [
                ("user", query),  # User's message or query
                ("assistant", env_vars_str),
            ],
        })
        return {"task_info": task_information}

    async def fetch_hint_step(state: PlanExecute):
        query = state["question"]
        task_info = state["task_info"]

        # Create an agent with memory capabilities (3)
        agent = create_react_agent(
            llm,
            tools=task_hint_tools,
            store=mem_store,
        )

        task_formatted = f"""You are tasked with finding the correct task hint for task - {query}.
First find the list of the runbook files and find the appropriate one for the target task.
Please note, this is the task info {task_info.type}. Fetch as much as details, as possible, including exact
commands to exec, if available."""

        try:
            # Store a new memory (1)
            response = agent.invoke(
                {"messages": [{"role": "user", "content": task_formatted}]}
            )
        except Exception as e:
            response = handle_agent_error(e)
        if "messages" in response:
            return {"hint_content": response["messages"][-1].content}
        else:
            return {"hint_content": response}

    async def plan_step(state: PlanExecute):
        query = state["question"]
        hint_content_str = state["hint_content"]
        user_hints = state["user_hints"]
        task_info_type = state["task_info"].type if state["task_info"].type else state["task_info"]
        tools = ", ".join([tool.name for tool in execution_tools])
        context = await rag_store(f"""As a world class Mezmo (logdna) platform expert and data engineer, for exploring the query: `{query}`,

Provide all details required to plan investigation for task type:
{task_info_type}

\n\n Make sure to include relevant context, detailed steps and correct target api endpoints the plan should execute, for the overall goal.""")
        # context = ""
        context_message = context["response"] if "response" in context else context
        state["context"] = context_message

        # openapi_tool = OpenAPIParserTool()
        # api_spec = openapi_tool.run(openapi_file) #TODO: make an agent to pick up the right file

        DEFAULT_RESPONSE_TYPE = """Respond as a json, with success flag, details, and requirement list as attributes"""
        response, _ = await ainvoke_graphrag_search_local_cache(f"""For the given user query, does it include all the required information for a successful debugging flow?\n Query: {query}""", DEFAULT_RESPONSE_TYPE,
                                                                "Mezmo")
        pattern = r'\[Data: .*?\]'
        attributes = re.sub(pattern, '', response)

        for retry in range(RETRIES):
            try:
                plan = await planner_chain.ainvoke({
                    "messages": [
                        ("user", query),  # User's message or query
                        ("assistant", f"""\nContext:\n\n {context_message}"""),
                        ("assistant",
                         f"""\nQuery Validation:\n\n {attributes}"""),
                        ("assistant", f"""\nTool Hints:\n\n {tools}"""),
                        ("assistant", f"""\nTask Type:\n\n {task_info_type}"""),
                        ("assistant", f"""\nRunbook/User Hints:\n\n {hint_content_str}"""),
                        ("assistant", f"""\nSystem Hints:\n\n {user_hints}""")
                    ]
                })

                plan_str_list = []
                for step_k, step_v in plan["steps"].items():
                    plan_str_list.append(f"{step_k}: {"\n".join(step_v)}")

                return {"plan": plan_str_list, "context": state["context"], "tools": tools, "attributes": attributes, "extracted_values": ""}
            except Exception as e:
                logger.error(f"Error planning: {str(e)}", exc_info=e)
                continue

        return {"plan": ["Validate environment variables. replan."], "tools": tools, "attributes": attributes, "extracted_values": ""}

    async def execute_step(state: PlanExecute):
        query = state["question"]
        plan = state["plan"]
        user_hints = state["user_hints"]
        tools_str = state["tools"]
        task = plan[0]
        extracted_values = state["extracted_values"]

        # extract output
        past_steps = state["past_steps"]
        last_step = None
        if past_steps:
            last_step = past_steps[-1]

        api_exec_steps_prompt = f"""As a world class Mezmo (logdna) platform expert and data engineer, provide the exact steps required to execute this task: {task}. "
\n\nMake sure to include: 
  * all validated target api endpoints,
  * include required headers and all information needed to extract the headers,
  * all parameters/queries required for the endpoint to be successful;
the plan should execute, for the overall goal,
  * *ALWAYS* return/explore all available APIs for any additional information which could be helpful for the investigation.

=====
{user_hints}
"""

        if last_step:
            api_exec_steps_prompt += f"""\n---\n\nLast Steps Execution & Result:\n\n{last_step}\n\n"""
        if extracted_values:
            api_exec_steps_prompt += f"""\n---\n\nExtracted Values so far:\n\n{extracted_values}\n\n"""

        api_str = await rag_store(api_exec_steps_prompt, load_data=True)

        task_formatted = f"""You are tasked with executing step - {task}.
\n\nPlease note, you have the confirmation and authorization from the user for this task. Any required attributes can be 
assumed to be found in environment variables, including target endpoint base url or execute the steps for fetching those headers/params.
* ALWAYS scope API calls to `GET` requests only. For other types, expect DENIED as a response from the user.
* ALWAYS fetch ENV Vars, using the given tool, for more information.
* ALWAYS explore all available APIs for any additional information which could be helpful for the investigation.

=====
{user_hints}
"""

        if api_str:
            task_formatted += f"""\n---\n\nAPI Hints:\n\n{api_str["response"] if "response" in api_str else api_str}\n\n"""
        if tools_str:
            task_formatted += f"""\n---\n\nTools:\n\n{tools_str}\n\n"""
        if last_step:
            task_formatted += f"""\n---\n\nLast Steps Execution & Result:\n\n{last_step}\n\n"""
        if extracted_values:
            task_formatted += f"""\n---\n\nExtracted Values so far:\n\n{extracted_values}\n\n"""

        try:
            agent_executor = create_react_agent(
                llm,
                tools=execution_tools,
                store=mem_store,
            )
            exec_agent_response = agent_executor.invoke(
                {"messages": [{"role": "user", "content": task_formatted}]}
            )
        except Exception as e:
            exec_agent_response = handle_agent_error(e)

        exec_agent_response_str = exec_agent_response["messages"][-1].content if "messages" in exec_agent_response else exec_agent_response["error"] if "error" in exec_agent_response else exec_agent_response

        try:
            val_extract_task = f"""
For exploring task: `{query}`

You are tasked with extracting the deduced value we extracted in this last step - {task};

Result -
{exec_agent_response_str}

Please return a dictionary of successful key value pair of the extracted attribute(s) and its value, in this last step result. Return empty dictionary if no values extracted.
**STRICTLY, no additional text.**
---
Example Format:
```json
{{
  "abc": "12323dfdasd",
  "xyz": "d2407ef8-dcc0-11ef-aee6-6aa248be2eb7",
  "efg": "8052491c-e8b6-11ef-bc4c-4e420c9b9fca",
}}
```
"""
            val_agent_executor = create_react_agent(
                llm_mini,
                tools=[
                    # Memory tools use LangGraph's BaseStore for persistence (4)
                    create_manage_memory_tool(namespace=("memories",)),
                    create_search_memory_tool(namespace=("memories",)),
                ],
                store=mem_store,
            )
            val_agent_response = val_agent_executor.invoke(
                {"messages": [{"role": "user", "content": val_extract_task}]}
            )
        except Exception as e:
            val_agent_response = handle_agent_error(e)

        val_agent_response_str = val_agent_response["messages"][-1].content if "messages" in val_agent_response else \
        val_agent_response["error"] if "error" in val_agent_response else val_agent_response

        result = { "past_steps": [(task, exec_agent_response_str)] }

        if val_agent_response_str and extracted_values != None:
                extracted_values += val_agent_response_str + "\n\n"

        if extracted_values:
            result["extracted_values"] = extracted_values

        return result

    async def replan_step(state: PlanExecute):
        # extract output
        plan = state["plan"]
        plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
        past_steps = state["past_steps"]
        last_step = None
        re_plan_context = f"""As a world class Mezmo (logdna) platform expert and data engineer, provide all details required to move investigation further for given task. 
        \n\n Make sure to include correct target api endpoints the plan should execute, for the overall goal.
        """
        if past_steps:
            last_step = past_steps[-1]
        if last_step:
            re_plan_context += f"""\n---\n\nLast Steps Execution & Result:\n\n{last_step}\n\n"""
        if plan_str:
            re_plan_context += f"""\n---\n\nYour original plan was:\n{plan_str}\n\n"""
        context = await rag_store(re_plan_context)
        context_message = context["response"] if "response" in context else context
        state["context"] = context_message

        for retry in range(RETRIES):
            try:
                output = await replanner_chain.ainvoke(state)

                if output and "response" in output:
                    return {"response": str(output["response"]), "context": state["context"]}
                elif output and "steps" in output:
                    plan_str_list = []
                    if isinstance(output["steps"], dict):
                        for step_k, step_v in output["steps"].items():
                            plan_str_list.append(f"{step_k}: {"\n".join(step_v)}")
                    elif isinstance(output["steps"], List):
                        for i, k in enumerate(output["steps"]):
                            step_str = []
                            if isinstance(k, dict):
                                for step_k, step_v in k.items():
                                    step_str.append(f"{step_k}: {step_v}")
                            elif isinstance(k, str):
                                step_str.append(k)
                            plan_str_list.append("\n".join(step_str))

                    return {"plan": plan_str_list, "context": state["context"]}
            except Exception as e:
                logger.error(f"Error planning: {str(e)}")
                continue

        return {"plan": state["plan"], "context": state["context"]}

    async def finalize(state):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        logger.info("---SYNTHESIZE---")
        for retry in range(RETRIES):
            try:
                final_response = synthesize_chain.invoke(state)
                return {"response": final_response}
            except Exception as e:
                logger.error(f"Error planning: {str(e)}")
                continue

        past_steps = state["past_steps"]
        past_steps_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(past_steps))
        return {"response": past_steps_str}


    def should_end(state: PlanExecute):
        if "response" in state and state["response"]:
            return "synthesize"
        else:
            return "agent"

    workflow = StateGraph(PlanExecute)

    workflow.add_node("task_expert", task_expert_step)
    workflow.add_node("hint_agent", fetch_hint_step)

    # Add the plan node
    workflow.add_node("planner", plan_step)

    # Add the execution step
    workflow.add_node("agent", execute_step)

    # Add a replan node
    workflow.add_node("replan", replan_step)

    # Add the plan node
    workflow.add_node("synthesize", finalize)

    # We start with planner
    workflow.add_edge(START, "task_expert")
    workflow.add_edge("task_expert", "hint_agent")
    workflow.add_edge("hint_agent", "planner")
    # From plan we go to agent
    workflow.add_edge("planner", "agent")
    # From agent, we replan
    workflow.add_edge("agent", "replan")
    workflow.add_conditional_edges(
        "replan",
        # Next, we pass in the function that will determine which node is called next.
        should_end,
        ["agent", "synthesize"],
    )
    workflow.add_edge("synthesize", END)

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    app = workflow.compile(checkpointer=checkpoint_memory)

    return app
