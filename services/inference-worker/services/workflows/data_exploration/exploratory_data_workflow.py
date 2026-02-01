import operator
import os
import re
from datetime import datetime, UTC
from typing import TypedDict, List, Annotated, Tuple, Union, Dict, Any, Optional

import streamlit as st
import pandas as pd

from langchain.agents import AgentType, Tool
from langchain_community.tools import ShellTool
from langchain_core.callbacks import CallbackManager, BaseCallbackHandler
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import JsonOutputParser
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_experimental.utilities import PythonREPL
from langgraph.constants import END
from langgraph.graph import START
from langgraph.prebuilt import create_react_agent
from langmem import create_manage_memory_tool, create_search_memory_tool
from matplotlib import pyplot as plt
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph

from services.cache.memory_cache import initialize_memory_cache
from services.utils.graphrag.graphrag_query_local import GraphRAGLocalSearch
from services.utils.logger import logger
from services.workflows.data_exploration.chicory_agent import ChicoryAgent, ChicoryProjectTask
from services.workflows.data_exploration.prompt import TASK_EXPERT_PROMPT_CONST, ANALYSIS_PLANNER_PROMPT_CONST, \
    ANALYSIS_REPLANNER_PROMPT_CONST, ANALYSIS_SYNTHESIZE_PROMPT_CONST
from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v4 import initialize_brewsearch_state_workflow


# Common State Classes
class ExplorationState(TypedDict):
    """State for Analysis stage"""
    query: str
    domain: str  # e.g., "mezmo", "feature_engineering", etc.
    runbooks: Dict[str, Any]  # Loaded runbooks
    templates: Dict[str, Any]  # Response templates
    work_dir: str  # Working directory
    additional_context: str  # Any additional context
    task_info: Optional[Dict[str, Any]]  # Task information from task expert
    user_hints: str
    hint_content: Optional[str]  # Hint content from hint agent
    env_vars: Optional[Dict[str, str]]  # Environment variables
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    analysis_report: Dict[str, Any]
    agent_description: str
    user_response_template: str
    # Domain-specific fields
    data: Optional[List[pd.DataFrame]]  # For feature engineering
    api_responses: Optional[Dict[str, Any]]  # For API workflows like Mezmo
    # Results
    extracted_values: Optional[str]  # Extracted values from analysis
    response: str
    final_response: str
    summary_report: str


# Data model for task type
class Task(BaseModel):
    """Task Information"""
    type: str = Field(
        description="task type",
    )
    enhanced_query: str = Field(
        description="detailed/enhanced version of the query",
    )
    required_attributes: str = Field(
        description="comma separated list of missing attributes, if any, otherwise none (str)",
    )
    metadata: List[str] = Field(
        description="extracted attributes from the task"
    )
    scope: str = Field(
        description="task exploration scope, as per the context, for the target objective",
    )
    data_type: str = Field(
        description="data type, as per the context, for the target objective",
    )


# Pydantic Models for Response Structure
class Plan(BaseModel):
    """Plan to follow in future"""
    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
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


class AnalysisReport(BaseModel):
    """Analysis report structure."""
    summary: str = Field(description="Summary of the analysis")
    findings: Dict[str, Any] = Field(description="Key findings from the analysis")
    data_points: List[Dict[str, Any]] = Field(description="Important data points or metrics")
    context: Dict[str, Any] = Field(description="Contextual information gathered")

MAX_TOKENS = 100000  # Adjusted to stay well within limits # OR 124000
RETRIES = 5 # In case any llm cals failes
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
MODEL = os.environ.get("MODEL", "gpt-4.1")
MINI_MODEL = os.environ.get("MINI_MODEL", "gpt-4o-mini")
REASONING_MODEL = os.environ.get("REASONING_MODEL", "o4-mini")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "chatgpt-4o-latest")
SEED = int(os.environ.get("SEED", "101"))
RECURSION_LIMIT = int(os.environ.get("RECURSION_LIMIT", "75"))

checkpoint_memory, vector_store, mem_store = initialize_memory_cache(EMBEDDING_MODEL)
graph_rag_local = None

# Callback handlers
class StreamlitCallbackHandler(BaseCallbackHandler):
    def __init__(self, container: st.delta_generator.DeltaGenerator):
        self.container = container
        self.text = ""
        self.figure_counter = 0

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        self.container.write("LLM started...")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.text += token
        self.container.markdown(self.text)

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self.container.write("LLM finished.")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        self.container.write(f"Using tool: {serialized['name']}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        self.container.write("Tool execution completed.")

    def handle_plt_show(self):
        self.figure_counter += 1
        filename = f"figure_{self.figure_counter}.png"
        try:
            plt.savefig(filename, bbox_inches='tight')
            plt.close()
            self.container.write(f"Figure {self.figure_counter} generated:")
            self.container.image(filename)
        except Exception as e:
            self.container.error(f"Error displaying plot: {e}")

        os.remove(filename)  # Remove the file after displaying


class FileLoggingCallbackHandler(BaseCallbackHandler):
    def __init__(self, log_file: str, image_dir: str):
        self.log_file = log_file
        self.image_dir = image_dir
        self.figure_counter = 0
        os.makedirs(image_dir, exist_ok=True)

    def log_to_file(self, message: str) -> None:
        with open(self.log_file, 'a') as f:
            f.write(message + '\n')

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        self.log_to_file("LLM started...")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.log_to_file(token)

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self.log_to_file("LLM finished.")

    def handle_plt_show(self):
        self.figure_counter += 1
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"figure_{current_time}.png"
        filepath = os.path.join(self.image_dir, filename)
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        self.log_to_file(f"Figure saved: {filename}")


class Exploratory_Data_Workflow:
    """
    Main class for the Exploratory Chicory Agent that handles analysis workflows
    """

    def __init__(
            self,
            user: str,
            mezmo_project_agent: ChicoryAgent,
            response_container: st.delta_generator.DeltaGenerator = None,
            file_logging: bool = False
    ):
        """
        Initialize the Exploratory Chicory Agent.

        Args:
            user_query: User's query or request
            project: Project name
            response_container: Streamlit container for responses
            file_logging: Whether to enable file logging
            work_dir: Working directory
        """
        # Basic configuration
        self.user_query = mezmo_project_agent.task.query
        self.user_hints = mezmo_project_agent.task.user_hints
        self.user = user
        self.project = (mezmo_project_agent.project or os.getenv("PROJECT", "")).strip().lower()
        self.work_dir = mezmo_project_agent.config.work_directory or os.getcwd()
        self.agent_description = mezmo_project_agent.task.agent_description
        self.response_template = mezmo_project_agent.task.response_template
        self.response_container = response_container
        self.file_logging = file_logging

        # Detect domain from query
        self.domain = self._detect_domain()

        # Initialize OpenAI components
        self.llm = ChatOpenAI(model=MODEL, temperature=0, seed=SEED)
        self.llm_mini = ChatOpenAI(model=MINI_MODEL, temperature=0, seed=SEED)
        self.reasoning_llm = ChatOpenAI(model=REASONING_MODEL,
                                   seed=SEED)
        self.chat_llm = ChatOpenAI(model=CHAT_MODEL, temperature=0,
                              seed=SEED)

        # Set up trimmer for managing token lengths
        self.trimmer = trim_messages(
            max_tokens=124000,
            strategy="last",
            token_counter=self.llm_mini,
            include_system=True,
        )

        # Configure callback handlers
        self.callback_manager = self._setup_callbacks()

        # Load domain-specific resources
        self.runbooks = self._load_runbooks(mezmo_project_agent.config.runbook_directory)
        self.knowledge_context_app = self._load_knowledge_graph_app()

        # Configure tools
        self.tools_config = self._configure_tools()

        # Create chains
        self._create_analyze_chain()

        # Build the workflow
        self.analysis_chain = self._build_analysis_workflow()

        # Initialize base state
        self.base_state = self._init_base_state()

    def _detect_domain(self) -> str:
        """Detect the domain based on the user query."""
        return os.environ.get("EMBEDDING_DOMAIN", "data analytics and data engineering infrastructure")

    def _setup_callbacks(self) -> Optional[CallbackManager]:
        """Set up callback handlers for the agent."""
        callback_manager = None
        if self.response_container:
            streamlit_handler = StreamlitCallbackHandler(self.response_container)
            callback_manager = CallbackManager([streamlit_handler])
            # Override plt.show to use custom handler
            plt.show = streamlit_handler.handle_plt_show

        if self.file_logging:
            log_dir = os.path.join(self.work_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            file_log_handler = FileLoggingCallbackHandler(
                os.path.join(log_dir, "workflow.log"),
                os.path.join(log_dir, "figures")
            )
            handlers = [file_log_handler]
            if callback_manager:
                handlers.extend(callback_manager.handlers)
            callback_manager = CallbackManager(handlers)
            plt.show = file_log_handler.handle_plt_show

        return callback_manager

    def _load_runbooks(self, runbooks_dir) -> Dict[str, Any]:
        """Load runbooks for the specified domain and project."""
        # Check for project-specific runbooks directory

        steps = [
                    "Analyze the input query",
                    "Identify key parameters",
                    "Execute relevant operations",
                    "Synthesize findings"
                ]

        # If runbooks directory exists, return file listing for hint agent to use
        if os.path.exists(runbooks_dir):
            return {
                "directory": runbooks_dir,
                "files": self._fetch_hint_files(runbooks_dir),
                "steps": steps
            }

        # Fallback to default runbooks if no directory
        return {
            "steps": steps
        }

    def _fetch_hint_files(self, runbooks_dir: str) -> List[str]:
        """Fetch hint dir/files from a runbooks directory."""
        file_paths = []
        try:
            for root, dirs, files in os.walk(runbooks_dir):
                for file in files:
                    # Get the file path
                    file_path = os.path.join(root, file)
                    file_paths.append(file_path)
        except Exception as e:
            return [f"Error fetching runbooks: {str(e)}"]

        if not file_paths:
            return ["No runbook files found. Using context information only."]

        return file_paths

    def _fetch_hint_file(self, file_path: str) -> str:
        """Fetch content from a hint file."""
        hint_content = ""

        try:
            # Read the main hint file
            with open(file_path, 'r') as f:
                hint_content = f.read()
        except Exception as e:
            return f"Error fetching hint file: {str(e)}"
        return hint_content

    def _load_knowledge_graph_app(self) -> Dict[str, Any]:
        """Load and query the knowledge graph for the specified domain."""
        app = initialize_brewsearch_state_workflow(self.user, self.project)
        return [ app ]

    def _configure_tools(self) -> Dict[str, List[Tool]]:
        """Configure the tools for the agent based on domain."""
        common_tools = [
            # Memory tools use LangGraph's BaseStore for persistence (4)
            create_manage_memory_tool(namespace=("memories",)),
            create_search_memory_tool(namespace=("memories",)),
            Tool(
                name="FetchKnowledgeContext",
                func=lambda q: self._fetch_knowledge_context(q),
                description="Fetch relevant context from knowledge graph"
            ),
            Tool(
                name="FetchEnvVars",
                func=self._fetch_env_vars,
                description="Fetch all available environment variables"
            ),
            Tool(
                name="FetchEnvVarValue",
                func=self._fetch_env_var_value,
                description="Fetch the value of a specific environment variable"
            )
        ]

        # Configure hint agent tools
        hint_tools = [
            Tool(
                name="HintFilesInRunbookDir",
                func=lambda _: self._fetch_hint_files(self.runbooks.get("directory", "")),
                description="Useful to get list of hint files in the project's runbook directory"
            ),
            Tool(
                name="TaskSpecificHintFile",
                func=self._fetch_hint_file,
                description="Useful to get content of the target hint file in the project's runbook directory"
            )
        ]

        tools_config = {
            "common": common_tools,
            "hint": hint_tools,
            "domain_specific": []
        }

        shell_tool = ShellTool()
        python_repl = PythonREPL()
        # if self.domain == "mezmo":
        #     tools_config["domain_specific"] = [
        #         Tool(
        #             name="ExecuteAPICall",
        #             func=self._execute_api_call,
        #             description="Execute an API call to the specified endpoint"
        #         ),
        #         Tool(
        #             name="AnalyzeLogs",
        #             func=self._analyze_logs,
        #             description="Analyze log data to identify patterns and issues"
        #         )
        #     ]
        # elif self.domain == "feature_engineering":
        # Load data for feature engineering
        data = []
        if os.path.exists(self.work_dir):
            csv_files = [f for f in os.listdir(self.work_dir) if f.endswith('.csv')]
            for file in csv_files:
                try:
                    df = pd.read_csv(os.path.join(self.work_dir, file))
                    data.append(df)
                except Exception as e:
                    logger.error(f"Error loading {file}: {e}", exc_info=True)

        # Create pandas agent
        if data:
            prefix = """ 
                   import pandas as pd
                   import seaborn as sns
                   import matplotlib.pyplot as plt

                   # You can add any other setup code or hints here
                   # The list of DataFrames is called `df`. Access them like: df[0], df[1], df[2], etc. Use these directly. Call `plt.show()` after each plot. Merge the dataframes before plotting.
                   # HINT: The data is in-memory as a DataFrame and should not be read from any file
                   * HINT: If you are using matplotlib, use plt.show() to display the plot.

                   """
            agent_max_iterations = 30
            pandas_agent = create_pandas_dataframe_agent(
                self.llm,
                data,
                verbose=True,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                allow_dangerous_code=True,
                return_intermediate_steps=True,
                max_iterations=agent_max_iterations,
                number_of_head_rows=30,
                max_execution_time=240.0,
                agent_executor_kwargs={
                    "handle_parsing_errors": True,
                },
                prefix=prefix,
                callback_manager=self.callback_manager
            )

            tools_config["domain_specific"] = [
                    Tool(
                        name="PandasAnalysis",
                        func=pandas_agent.run,
                        description="Analyze data using pandas"
                    )
                ]
        else:
            tools_config["domain_specific"] = [
                shell_tool,
                Tool(
                    name="python_repl",
                    description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
                    func=python_repl.run,
                )
            ]
        # Store data for later use
        self.data = data

        return tools_config

    async def _ainvoke_graphrag_search_local_cache(self, question, response_type, project):
        global graph_rag_local
        self.graph_rag_local = GraphRAGLocalSearch(project)
        if self.graph_rag_local:
            return await self.graph_rag_local.search(question, response_type)
        else:
            raise IndexError("GraphRag resource not setup correctly or not available.")

    async def _rag_store(self, query, app, breakdown = False, load_data = False, concise = True):
        inputs = {
            "question": query,
            "breakdown": breakdown,
            "load_data": load_data,  # defaults to no data validation rn
            "concise": concise
        }
        config = {
            "recursion_limit": 20,
            "configurable": {
                "thread_id": f"chicory-inference-{self.project}",
                "thread_ts": datetime.now(UTC).isoformat(),
                "client": "brewmind",
                "user": self.user,
                "project": self.project,
            }
        }
        response = ""
        if app:
            async for event in app.astream(
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

    async def _fetch_knowledge_context(self, query: str, load_data: bool = False) -> str:
        """
        Fetch relevant context from the knowledge graph based on the query.
        """
        # Implementation would use vector search or other retrieval methods
        # This is a simplified placeholder
        context = ""
        for kgc_app in self.knowledge_context_app:
            response = await self._rag_store(query, kgc_app, load_data=load_data)
            context += "/n/n" + response['response']
        if context:
            return context
        return "Retrieved context based on query: " + context

    def _fetch_env_vars(self) -> Dict[str, str]:
        """
        Fetch all available environment variables in the system.
        """
        try:
            env_vars = dict(os.environ)
            return env_vars
        except Exception as e:
            return {"error": f"Failed to fetch environment variables: {str(e)}"}

    def _fetch_env_var_value(self, env_var_name: str) -> str:
        """
        Fetch the value of a specific environment variable.
        """
        try:
            value = os.environ.get(env_var_name, "Environment variable not found")
            return value
        except Exception as e:
            return {"error": f"Failed to fetch environment variable '{env_var_name}': {str(e)}"}

    def _execute_api_call(self, endpoint: str, params: Dict[str, Any], headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an API call to the specified endpoint.
        """
        # Simplified implementation - in real world, would use requests or other HTTP library
        return {"status": "success", "data": f"Response from {endpoint}"}

    def _create_analyze_chain(self):
        """Create the LLM chains for the workflow."""
        # Create task expert prompt
        task_expert_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    TASK_EXPERT_PROMPT_CONST,
                ),
                ("placeholder", "{messages}"),
            ]
        )

        self.task_expert_chain = task_expert_prompt | self.llm.with_structured_output(Task)

        # Define analysis prompt template
        analysis_prompt_template = [
                (
                    "system",
                    ANALYSIS_PLANNER_PROMPT_CONST,
                ),
                ("placeholder", "{messages}"),
            ]
        analysis_prompt = ChatPromptTemplate.from_messages(analysis_prompt_template)
        plan_parser = JsonOutputParser(pydantic_object=Plan)
        self.analysis_planner_chain = analysis_prompt | self.trimmer | self.reasoning_llm | plan_parser

        # Create replanner chain
        analysis_replanner_prompt = ChatPromptTemplate.from_template(
            ANALYSIS_REPLANNER_PROMPT_CONST
        )
        act_parser = JsonOutputParser(pydantic_object=Act)
        self.analysis_replanner_chain = analysis_replanner_prompt | self.trimmer | self.reasoning_llm | act_parser

        analysis_synthesize_prompt = ChatPromptTemplate.from_template(
            ANALYSIS_SYNTHESIZE_PROMPT_CONST
        )

        self.analysis_synthesize_chain = analysis_synthesize_prompt | self.reasoning_llm | JsonOutputParser()

    async def _task_expert_step(self, state: ExplorationState):
        """Classify the task type and extract metadata"""
        query = state["query"]
        user_hints = state["user_hints"]
        user_response_template = state["user_response_template"]
        agent_description = state["agent_description"]
        env_vars = self._fetch_env_vars()
        env_vars_str = ",".join([f"{k}={v}" for k, v in env_vars.items()])

        DEFAULT_RESPONSE_TYPE = """Respond in JSON format with the following fields:
        - `success` (boolean): Indicates whether all required information is present.
        - `details` (string): A brief explanation of the evaluation result.
        - `required_attributes` (list): List of attributes or details required from the original query, for solving this query.
        - `enhanced_query` (string): A revised version of the query that includes all necessary information for the target objective.
        Do not include any instruction steps, only goals."""

        response, _ = await self._ainvoke_graphrag_search_local_cache(
            f"""Evaluate the following user query for completeness in the context of initiating a investigation workflow:\n
        Query: 
```\n{query}\n```\n
        Determine whether the query contains all the necessary information. If it does not, identify the required elements and rewrite the query to be complete, clear, and actionable. Ensure the enhanced query includes any required context, fields, or parameters that would help provide a comprehensive response.""",
            DEFAULT_RESPONSE_TYPE,
            self.project
        )
        pattern = r'\[Data: .*?\]'
        attributes = re.sub(pattern, '', response)

        task_information = await self.task_expert_chain.ainvoke({
            "messages": [
                ("system", f"\nAgent Description:\n {agent_description}"),
                ("user", query),  # User's message or query
                ("user", f"Hints: {user_hints}"),
                ("assistant", f"Environment variables: {env_vars_str}"),
                ("assistant", f"\nAdditional Information:\n {attributes}"),
                ("user", f"\nResponse Template:\n {user_response_template}"),
            ],
        })

        return {
            "task_info": {
                "type": task_information.type,
                "data_type": task_information.data_type,
                "metadata": task_information.metadata,
                "scope": task_information.scope,
                "enhanced_query": task_information.enhanced_query,
                "required_attributes": task_information.required_attributes,
            },
            "env_vars": env_vars,
            # "query": task_information.enhanced_query if task_information and task_information.enhanced_query else state["query"],
            "attributes": attributes
        }

    async def _hint_agent_step(self, state: ExplorationState):
        """Find and load appropriate hint files based on a task type"""
        query = state["query"]
        task_info = state["task_info"]
        runbooks_dir = state["runbooks"].get("directory", "")

        # If no runbooks directory, use an empty hint
        if not runbooks_dir or not os.path.exists(runbooks_dir):
            return {"hint_content": "No domain-specific runbooks available."}

        # Create a hint agent to find the appropriate runbook
        hint_agent = create_react_agent(
            self.llm,
            tools=self.tools_config["hint"],
            store=mem_store,
        )

        hint_task = f"""
You are an intelligent agent assisting with task setup. Your objective is to identify the correct runbook files to assist with the following task:
```\n{query}\n```

Instructions:
1. First find the list of the runbook files and find the appropriate one for the target task.
1. Use the task type `{task_info['type']}` to find the most relevant runbook files.
2. Match the `task_type` semantically with the available runbook `file_name`s to find the most appropriate file(s).
3. Include any **common runbook files** that are generally required across all tasks.

**Important:**
- **ALWAYS** return the entire runbook file(s) content. Do not try to summarize it. Most importantly, the return content should not miss any important details. 
- **Only include runbooks** that are either general or specific to the current task type.
- **Do not include** runbooks intended for unrelated or different task types.

Expected Output:
Fetch as much as details, as possible, including exact commands to exec, if available.
Combined content from all the relevant runbook files, including generic and common system/execution level information needed for each step to be analyzed.
For example: include content from api.md + relevant task runbook.
**CRITICAL** Always return the file content as it is. Feel free to add more context, but never remove content from the runbook.

Be as specific and complete as possible.
"""

        try:
            # Invoke the hint agent
            hint_response = hint_agent.invoke({
                "messages": [{"role": "user", "content": hint_task}]
            })

            hint_content = hint_response["messages"][
                -1].content if "messages" in hint_response else "No specific hint found."
        except Exception as e:
            hint_content = f"Error fetching hint: {str(e)}"

        return {"hint_content": hint_content}

    async def _plan_step(self, state: ExplorationState):
        """Generate initial analysis plan"""
        query = state["query"]
        user_hints = state["user_hints"]
        agent_description = state["agent_description"]
        user_response_template = state["user_response_template"]
        domain = state["domain"]
        task_info = state["task_info"]
        knowledge_context = await self._fetch_knowledge_context(f"""
As a world-class {domain} expert, you are tasked with planning an investigation for the following query:
```\n{query}\n```

Please provide:
1. **Context** – Summarize all relevant background information, prior knowledge, and assumptions necessary to understand the task.
2. **Investigation Plan** – A clear, step-by-step outline of how to approach the query, including reasoning behind each step.
3. **Resources & Interfaces** – List any API endpoints, tools, data sources, methods, or functions that should be used, and describe how they will support the investigation.
4. **Objectives & Coverage** – Ensure the plan aligns with the main goal, includes all critical steps, and anticipates edge cases or blockers.

=====
Task Info:
{task_info}

=====
Additional Context or Hints:
{user_hints}

=====
Response Format:
```json
{{
  "context": "<Background details, assumptions, or relevant domain knowledge>",

  "investigation_plan": [
    "Step 1: <Description of the first action or analysis step>",
    "Step 2: <Next step, with justification>",
    "...",
    "Step N: <Final verification or synthesis step>"
  ],

  "resources": {{
    "apis": [
      {{
        "name": "<API name>",
        "endpoint": "<Endpoint URL or function>",
        "purpose": "<Why this API is used>"
      }}
    ],
    "tools": [
      {{
        "name": "<Tool or library name>",
        "purpose": "<What it helps with>"
      }}
    ],
    "data_sources": [
      {{
        "name": "<Dataset, table, or external source>",
        "description": "<Details or schema info>"
      }}
    ]
  }},
  "objectives_covered": [
    "<How the approach addresses key goals>",
    "<Consideration of edge cases or limitations>"
  ]
}}
```
""")
        context_message = knowledge_context["response"] if isinstance(knowledge_context, Dict) and "response" in knowledge_context else knowledge_context
        hint_content = state["hint_content"]
        user_hints = state["user_hints"]
        tools = ", ".join([tool.name for tool in self.tools_config.get("common", []) + self.tools_config.get("domain_specific", [])])

        # Extract task type and metadata
        # task_type = task_info.get("type", "general")
        # task_scope = task_info.get("scope", "analyze, recommend, instruct")
        # task_metadata = "\n".join(task_info.get("metadata", []))

        for retry in range(RETRIES):
            try:
                plan = await self.analysis_planner_chain.ainvoke({
                    "messages": [
                        ("system", f"\nAgent Description:\n {agent_description}"),
                        ("user", state["query"]),  # User's message or query
                        ("assistant", f"""\nDomain:\n {domain}"""),  # User's message or query
                        ("assistant", f"""\nContext:\n {context_message}"""),
                        ("assistant", f"""\nTool Hints:\n {tools}"""),
                        ("assistant", f"""\nTask Info:\n {task_info}"""),
                        ("assistant", f"""\n[High Priority] Runbook/User Hints:\n {hint_content}"""),
                        ("assistant", f"""\nSystem Hints:\n {user_hints}"""),
                        ("user", f"\nResponse Template:\n {user_response_template}"),
                    ]
                })

                plan_str_list = []
                for step_k, step_v in plan["steps"].items():
                    plan_str_list.append(f"{step_k}: {"\n".join(step_v)}")

                return {"plan": plan_str_list, "context": context_message, "tools": tools,
                        "extracted_values": "", "analysis_report": {}}
            except Exception as e:
                logger.error(f"Error planning: {str(e)}", exc_info=e)
                continue

        return {"plan": ["Validate environment variables. replan."], "context": context_message, "tools": tools,
                "extracted_values": ""}


    def _handle_agent_error(self, error):
        if isinstance(error, str):
            return {"error": error}
        return {"error": str(error)}

    async def _execute_step(self, state: ExplorationState):
        """Execute a step from the analysis plan"""
        plan = state["plan"]
        if not plan:
            return {"analysis_report": {"error": "No plan steps remaining"}}

        query = state["query"]
        # TODO: data = state["data"] # feature engg
        user_hints = state["user_hints"]
        domain = state["domain"]
        tools_str = ", ".join([tool.name for tool in self.tools_config.get("common", []) + self.tools_config.get("domain_specific", [])])
        extracted_values = state.get("extracted_values", "")

        task = plan[0]
        remaining_plan = plan[1:] if len(plan) > 1 else []

        past_steps = state["past_steps"]
        last_step = None
        if past_steps:
            last_step = past_steps[-1]

        exec_steps_prompt = f"""
As a world-class {domain} expert, provide the **exact steps required** to execute the following task: {task}.

Your response must include:
- All **validated target tool/api calls or data access points** relevant to the task.
- All **required headers, keys, or credentials**, and explain **how to retrieve or extract them** if not already provided.
- All **required parameters, query arguments, or payload details** to ensure successful execution.
- Any **post-call expectations or validations** to check if the call was successful.
- *ALWAYS* explore and suggest **additional available tools or methods** that could provide useful or complementary information for the investigation.

=====
Additional Context or Hints:
{user_hints}
"""

        if last_step:
            exec_steps_prompt += f"""
-----
Last Step Executed & Result:
{last_step}
"""

        if extracted_values:
            exec_steps_prompt += f"""
-----
Extracted Values So Far:
{extracted_values}
"""

        tool_call_str = await self._fetch_knowledge_context(exec_steps_prompt, load_data=True)
        if not self.data:
            # Format the task for execution
            task_formatted = f"""
As a world-class {domain} expert, For exploring task: 
```\n{query}\n```

You are tasked with executing the following step:
**Step:** {task}

Please note:
- You have **confirmation and authorization** from the user to execute this task.
- Any **required attributes (e.g., API keys, base URLs, credentials)** can be assumed to be available as environment variables or retrieved using the appropriate tools or prior steps.
- **ALWAYS** limit tool (API) requests to `GET` calls unless explicitly allowed; for other request types, expect a DENIED response from the user. No adverse impact commands should be permitted.
- **ALWAYS** use the available tools to fetch environment variables, headers, or parameters if needed.
- **ALWAYS** explore all available APIs, tools, or data sources that may provide additional helpful information for the investigation or analysis.

=====
Additional Context or Hints:
{user_hints}
"""
        else:
            # Data analysis mode prompt
            task_formatted = f"""
As a world-class {domain} expert, you are tasked with executing the step and sharing the analysis report for: {task}.

Note:
- The goal is to perform analysis that supports the feature engineering objective: 
```\n{query}\n```.
- Ensure the analysis samples cover a balanced pattern across all dataframes.
- Consider any preprocessing, enriching, merging, or cleaning of the data for each analysis step as required.
- OUTCOME: Each task should provide insights useful for feature engineering.
- MUST: Validate the analysis before sharing the final report.
- HINT: The data is in-memory as a list of DataFrames, named `df`.
- Access them using: df[0], df[1], df[2], etc. (do NOT use df0, df1…).
- HINT: If syntax errors occur, modify and re-execute the code to ensure correctness.

"""

        if tool_call_str:
            task_formatted += f"""
-----
Execution Hints:
{tool_call_str["response"] if isinstance(tool_call_str, Dict) and "response" in tool_call_str else tool_call_str}
"""

        if tools_str:
            task_formatted += f"""
-----
Tools:
{tools_str}
"""

        if last_step:
            task_formatted += f"""
-----
Last Step Executed & Result:
{last_step}
"""

        if extracted_values:
            task_formatted += f"""
-----
Extracted Values So Far:
{extracted_values}
"""

        # Create an execution agent with appropriate tools
        execution_agent = create_react_agent(
            self.llm,
            tools=self.tools_config.get("common", []) + self.tools_config.get("domain_specific", []),
            store=mem_store,
        )

        try:
            # Execute the task
            exec_response = execution_agent.invoke({
                "messages": [{"role": "user", "content": task_formatted}]
            })
        except Exception as e:
            exec_response = self._handle_agent_error(e)

        result_content = exec_response["messages"][
            -1].content if "messages" in exec_response else exec_response[
            "error"] if "error" in exec_response else exec_response

        # Extract values from the execution result
        value_extraction_prompt = f"""
For the executed task: "{task}"

Result, from last step:
{result_content}

Please extract any key-value pairs or important values extracted in this execution.
Return a json dictionary of extracted values, or return empty dictionary if no values were extracted.
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

        value_extraction_agent = create_react_agent(
            self.llm_mini,
            tools=self.tools_config.get("common", []),
            store=mem_store,
        )

        try:
            # Extract values
            extraction_response = value_extraction_agent.invoke({
                "messages": [{"role": "user", "content": value_extraction_prompt}]
            })

            extracted_result = extraction_response["messages"][
                -1].content if "messages" in extraction_response else "{}"

            # Update extracted values
            if extracted_result and extracted_result != "```json\n{}\n```":
                if extracted_values:
                    extracted_values += f"\n\n{extracted_result}"
                else:
                    extracted_values = extracted_result

        except Exception as e:
            extracted_values = self._handle_agent_error(e)

        # Add to past steps
        this_step = (task, result_content)
        if this_step:
            past_steps.append(this_step)

        result = {
            "plan": remaining_plan,
            "past_steps": past_steps,
        }

        if extracted_values:
            result["extracted_values"] = extracted_values

        return result

    async def _replan_step(self, state: ExplorationState):
        """Replan analysis steps based on execution results"""
        # Extract variables for replanning
        domain = state["domain"]
        plan = state["plan"]
        plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
        past_steps = state["past_steps"]

        extracted_values = state.get("extracted_values", "")

        re_plan_context = f"""
As a world-class {domain} expert, provide all necessary details required to advance the investigation for the given task.

Please make sure to:
- Include the correct **target API endpoints, tools, or data sources** that should be used to achieve the overall goal.
- Outline the next **detailed steps or actions** needed to move the investigation forward.
- Ensure the plan is actionable, complete, and avoids skipping critical details.
"""

        if past_steps:
            last_step = past_steps[-1]
        if last_step:
            re_plan_context += f"""
-----
Last Steps Execution & Result:
{last_step}
"""
        if plan_str:
            re_plan_context += f"""
-----
Your original plan was:
{plan_str}
"""
        context = await self._fetch_knowledge_context(re_plan_context)
        context_message = context["response"] if isinstance(context, Dict) and "response" in context else context

        for retry in range(RETRIES):
            try:
                state["context"] = context_message
                output = await  self.analysis_replanner_chain.ainvoke(state)

                if output and ("response" in output or isinstance(output.action, Response)):
                    return {"response": str(output["response"]), "context": context_message, "extracted_values": extracted_values}
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

                    return {"plan": plan_str_list, "context": context_message, "extracted_values": extracted_values}
            except Exception as e:
                logger.error(f"Error Re-planning: {str(e)}", exc_info=e)
                continue

        return {"plan": state["plan"], "context": context_message, "extracted_values": extracted_values}

    def _should_continue_analysis(self, state: ExplorationState):
        """Determine whether to continue analysis or end the workflow."""
        if "response" in state and state["response"]:
            return "complete"
        else:
            return "continue"

    def _synthesize_step(self, state: ExplorationState):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        logger.info("---ANALYSIS SYNTHESIZE---")
        past_steps = state["past_steps"]
        for retry in range(RETRIES):
            try:
                final_response = self.analysis_synthesize_chain.invoke(state)
                return {"response": final_response, "analysis_report": past_steps}
            except Exception as e:
                logger.error(f"Error Synthesizing: {str(e)}", exc_info=e)
                continue
        past_steps_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(past_steps))
        return {"response": past_steps_str, "analysis_report": past_steps}

    def _build_analysis_workflow(self):
        """Build the analysis workflow."""
        # Create the Analysis workflow
        analysis_workflow = StateGraph(ExplorationState)

        # Add nodes to the Analysis workflow
        analysis_workflow.add_node("task_expert", self._task_expert_step)
        analysis_workflow.add_node("hint_agent", self._hint_agent_step)
        analysis_workflow.add_node("planner", self._plan_step)
        analysis_workflow.add_node("executor", self._execute_step)
        analysis_workflow.add_node("replanner", self._replan_step)
        analysis_workflow.add_node("synthesize", self._synthesize_step)

        # Add edges to the Analysis workflow
        analysis_workflow.add_edge(START, "task_expert")
        analysis_workflow.add_edge("task_expert", "hint_agent")
        analysis_workflow.add_edge("hint_agent", "planner")
        analysis_workflow.add_edge("planner", "executor")
        analysis_workflow.add_edge("executor", "replanner")
        analysis_workflow.add_conditional_edges(
            "replanner",
            self._should_continue_analysis,
            {
                "continue": "executor",
                "complete": "synthesize"
            }
        )
        analysis_workflow.add_edge("synthesize", END)

        # Compile the workflow
        app = analysis_workflow.compile(checkpointer=checkpoint_memory)
        return app

    def _init_base_state(self):
        """Initialize the base state for the workflow."""
        base_state = {
            "query": self.user_query,
            "domain": self.domain,
            "runbooks": self.runbooks,
            "work_dir": self.work_dir,
            "context": "",
            "task_info": None,
            "hint_content": "",
            "user_hints": self.user_hints,
            "agent_description": self.agent_description,
            "user_response_template": self.response_template,
            "env_vars": None,
            "extracted_values": "",
            "plan": [],
            "past_steps": [],
            "analysis_report": {}
        }

        # Add domain-specific data if available
        if self.data:
            base_state["data"] = self.data
        else:
            base_state["api_responses"] = {}

        return base_state

    async def run_analysis_phase(self):
        """
        Run the analysis workflow and return the results.

        Returns:
            Dict: Analysis results
        """
        if self.response_container:
            self.response_container.write("## Analysis Stage")

        # Run the Analysis stage
        analysis_state = {**self.base_state}

        config = {
            "recursion_limit": RECURSION_LIMIT,
            "handle_parsing_errors": True,
            "configurable": {
                "thread_id": f"chicory-{self.project}",
                "thread_ts": datetime.now(UTC).isoformat(),
                "client": "brewmind",
                "user": self.user,
                "project": self.project,
            }
        }

        # Stream the results for UI feedback
        final_state = None
        async for event in self.analysis_chain.astream(analysis_state, config=config):
            final_state = event
            if self.response_container:
                # Clean response for display
                display_event = {k: v for k, v in event.items() if k not in ['env_vars']}
                self.response_container.write(f"State update: {display_event}")

        # Return the final analysis result
        return final_state

# Example usage function
async def run_exploratory_agent(
        agent_workflow,
        response_container=None,
):
    """
    Convenience function to run the Exploratory Chicory Agent.

    Args:
        user_query: User's query or request
        project: Project name
        response_container: Streamlit container for responses
        file_logging: Whether to enable file logging
        work_dir: Working directory

    Returns:
        Dict: Analysis results
    """

    # Run the analysis
    analysis_result = await agent_workflow.run_analysis_phase()

    # Display final response
    if response_container:
        response_container.write("## Analysis Complete")
        response_container.write("### Summary")
        if "analysis_report" in analysis_result:
            response_container.write(analysis_result["analysis_report"])

    return analysis_result["analysis_report"], analysis_result["summary_report"]


# Example Streamlit app implementation
def streamlit_app():
    st.title("Exploratory Chicory Agent")

    # Project selection
    project = st.selectbox("Select Project", ["Mezmo"])

    agent_desc = st.text_area("Agent Description", height=100)

    # Query input
    user_query = st.text_area("Enter your query", height=100)

    user="User"

    # Query input
    user_hints = st.text_area("Enter hints, if any", height=100)

    # Response Template
    response_format = st.text_area("Response Format, if any", height=100)


    # Submit button
    if st.button("Submit"):
        response_container = st.empty()

        task = ChicoryProjectTask(
            query=user_query,
            agent_description=agent_desc,
            runbook_dir="/home/ubuntu/brewsearch/data/mezmo/raw/documents/runbooks",
            user_hints=user_hints,
            response_template=response_format
        )

        # Create ChicoryProject instance
        mezmo_project_agent = ChicoryAgent(agent="exploratory_agent", project=project, task=task)

        # Initialize the workflow
        agent_workflow = Exploratory_Data_Workflow(
            user,
            mezmo_project_agent,
            None,
            True
        )

        # Run the workflow
        import asyncio
        analysis_result = asyncio.run(run_exploratory_agent(
            agent_workflow,
            response_container
        ))

        # Display final analysis result
        st.markdown("## Analysis Results")
        st.json(analysis_result)


if __name__ == "__main__":
    streamlit_app()
