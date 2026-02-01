import asyncio
import copy
import csv
import os
import re
import time
from collections import defaultdict
from datetime import datetime, UTC
from pprint import pprint

import json
import xml.etree.ElementTree as ET

import pandas as pd
import tiktoken
from langchain.agents import AgentType
from typing import TypedDict, Annotated, Literal

from langchain_anthropic.chat_models import ChatAnthropic
from langchain_community.tools import ShellTool
from langchain_core.callbacks import CallbackManager
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import trim_messages, HumanMessage
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_experimental.utilities import PythonREPL
from langgraph.constants import END
from langgraph.graph import START, MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langmem import create_search_memory_tool, create_manage_memory_tool
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langchain_core.tools import tool

from typing import List

from services.cache.memory_cache import initialize_memory_cache
from services.customer.personalization import get_project_config
from services.utils.agent_tools.callback_hander import FileLoggingCallbackHandler
from services.utils.logger import logger, CustomMessageFormatter, StreamlitLogHandler
from services.utils.tools import run_rag, extract_json_from_response
from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v4 import initialize_brewsearch_state_workflow


class PlanExecute(TypedDict):
    mapping: List[dict]
    mapping_file: str
    code_file: str
    output_code: str
    output_file: str
    tools: List[str]
    mapping_only: bool
    response: str
    question: str
    data_mapping_summary: dict
    query_vars: dict
    session_id: str
    code_rerun: bool
    validation_passed: bool
    validation_message: str
    stdout_err_details: str
    is_code_issue: bool
    agent_response: str
    response: str


class Map(BaseModel):
    """Plan to follow in future"""

    list: dict[str, List[str]] = Field(
        description="mapping dictionary"
    )


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Response = Field(
        description="Action to perform. If you want to respond to user, use Response. "
                    "If you need to further use tools to get the answer, use Plan."
    )

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
MODEL = os.environ.get("MODEL", "gpt-4o")
MINI_MODEL = os.environ.get("MINI_MODEL", "gpt-4o-mini")
REASONING_MODEL = os.environ.get("REASONING_MODEL", "o3-mini")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "chatgpt-4o-latest")
SEED = int(os.environ.get("SEED", "101"))

checkpoint_memory, vector_store, mem_store = initialize_memory_cache(EMBEDDING_MODEL)

def should_replan(state: PlanExecute):
    if "response" in state and state["response"]:
        return "planner"
    else:
        return "coder"

def read_csv(csv_path):
    """Read the CSV file and return a list of catalog entries."""
    catalog_entries = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            catalog_entries.append(row)
    return catalog_entries

def handle_agent_error(error):
    if isinstance(error, str):
        return {"error": error}
    return {"error": str(error)}

class State(MessagesState):
    messages: list
    next: str
    writer_ran_once: bool

def initialize_harmonization_workflow_agent(user=None, input_project=None, output_project=None, response_container=None, file_loader=True):
    # Initialize OpenAI components
    llm = ChatOpenAI(
        model=MODEL,
        temperature=0,
        seed=SEED  # Fixed seed for deterministic outputs
    )
    llm_mini = ChatOpenAI(model=MINI_MODEL, temperature=0)
    reasoning_llm = ChatOpenAI(model=REASONING_MODEL, seed=SEED)
    chat_llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)

    # llm_regular = ChatAnthropic(
    #     model_name="claude-3-7-sonnet-latest",
    #     model_kwargs={"max_tokens": 3000, "thinking": {"type": "disabled"}},
    # )

    # reasoning_llm = ChatAnthropic(
    #     model_name="claude-3-7-sonnet-latest",
    #     model_kwargs={
    #         "max_tokens": 64000,
    #         "thinking": {"type": "disabled"},
    #         "temperature": 0,
    #         "system": "You are a deterministic mapping agent. Always provide the same output for the same input."
    #     },
    # )

    # reasoning_llm = ChatAnthropic(
    #     model_name="claude-3-7-sonnet-latest",
    #     model_kwargs={
    #         "max_tokens_to_sample": 100000,
    #         "thinking": {
    #             "type": "enabled",
    #             "budget_tokens": 4096
    #         },
    #     },
    # )

    input_rag_app = initialize_brewsearch_state_workflow(user, input_project)
    output_rag_app = initialize_brewsearch_state_workflow(user, output_project)

    # trimmer = trim_messages(
    #     max_tokens=124000,
    #     strategy="last",
    #     token_counter=llm_mini,
    #     include_system=True,
    # )

    input_project_config = get_project_config(input_project)
    output_project_config = get_project_config(output_project)

    callback_manager = None
    if file_loader:
        file_log_handler = FileLoggingCallbackHandler(
            os.path.join(output_project_config["work_directory"], "harmonization_wf_output.txt"),
            output_project_config["work_directory"])
        callback_manager = CallbackManager([file_log_handler])
        # Override plt.show() to use our custom method
    if response_container:
        # Streamlit container logger
        streamlit_handler = StreamlitLogHandler(response_container)
        # callback_manager = CallbackManager([streamlit_handler])
        streamlit_handler.setFormatter(
            CustomMessageFormatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.handlers = [streamlit_handler]

    # Warning: This executes code locally, which can be unsafe when not sandboxed

    # Define a safe token limit for GPT-4o
    MAX_TOKENS = 100_000  # Adjust based on application needs
    repl = PythonREPL()
    shell_tool = ShellTool()

    @tool
    def python_repl_tool(
            code: Annotated[str, "The python code to execute to generate your chart."],
    ):
        """Use this to execute python code. If you want to see the output of a value,
        you should print it out with `print(...)`. This is visible to the user."""
        try:
            result = repl.run(code)
            time.sleep(10)
        except BaseException as e:
            return f"Failed to execute. Error: {repr(e)}"
        return f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"

    @tool
    async def get_output_model_bi_result(query: str) -> str:
        """Use query to get sql execution answer for output data model."""
        async def _run():
            return await run_rag(
                output_rag_app,
                query,
                False,
                True,
                True,
                False,
                output_project
            )

        # Create or get event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # For cases where the loop is already running (e.g., Jupyter or Streamlit async context)
            # You can use asyncio.create_task() and manage the task externally if needed
            future = asyncio.ensure_future(_run())
            return asyncio.get_event_loop().run_until_complete(future)
        else:
            return asyncio.run(_run())

    @tool
    def fetch_input_data_schema(input: str):
        """Fetch schema for a table name from the input dataset schema file."""
        try:
            # Read the full schema content
            with open(input_project_config["schema_file_path"], 'r') as f:
                schema_content = f.read()

            # Find the schema for the specified table
            pattern = rf"# Table:\s*{re.escape(input)}\n(\[.*?\])"
            match = re.search(pattern, schema_content, re.DOTALL)

            if not match:
                return f"Error: Table '{input}' schema not found."

            table_schema = match.group(1)

            # Tokenize to check length
            encoding = tiktoken.encoding_for_model("gpt-4o")
            token_count = len(encoding.encode(table_schema))

            if token_count > MAX_TOKENS:
                return f"Error: Extracted schema exceeds token limit ({token_count} tokens)."

            return f"# Table: {input}\n{table_schema}"

        except Exception as e:
            return f"Error fetching schema: {str(e)}"

    @tool
    def fetch_input_data_relationship(input: str):
        """Fetch extracted table/column relationship from the dataset relationship file.

        Args:
            input (str): Any string.

        Returns:
            str: Relationship details or an error message.
        """
        try:
            # Read the full metadata content
            with open(input_project_config["relation_file_path"], 'r') as f:
                metadata_content = f.read()

            # Parse JSON
            metadata = json.loads(metadata_content)

            # Return the extracted metadata as a formatted JSON string
            return json.dumps({input: metadata}, indent=4)

        except Exception as e:
            return f"Error fetching metadata: {str(e)}"

    @tool
    def get_output_model_skeleton(query: str) -> str:
        """Use to get output model dummy output file content. No input needed."""
        dummy_xml_file_content = ""
        try:
            dummy_xml_file = os.path.join(output_project_config["data_path"], "dummy.xml")
            with open(dummy_xml_file, "r", encoding="utf-8") as dummy_file:
                dummy_xml_file_content = dummy_file.read()
        except Exception as e:
            logger.error(f"Error getting dummy output file: {str(e)}", exc_info=e)
        return dummy_xml_file_content

    @tool
    def get_input_model_bi_result(query: str) -> str:
        """Use query to get sql execution answer for input data model."""

        async def _run():
            return await run_rag(
                input_rag_app,
                query,
                False,
                True,
                True,
                False,
                input_project
            )

        # Create or get event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # For cases where the loop is already running (e.g., Jupyter or Streamlit async context)
            # You can use asyncio.create_task() and manage the task externally if needed
            future = asyncio.ensure_future(_run())
            return asyncio.get_event_loop().run_until_complete(future)
        else:
            return asyncio.run(_run())

    @tool
    def get_output_model_catalog_insight(query: str) -> str:
        """Use query to get insight about output data model from its catalog data."""

        result = "output model catalog not available!"
        try:
            mapping_file = os.path.join(output_project_config["work_directory"], f"{input_project}_{output_project}_data_catalog.json")
            df = pd.read_json(mapping_file)
            task_formatted = f"""You are tasked with searching through the catalog and share the insights. \n\n
                    Note: 
                    * Goal for data mapping - {query}. Analysis should be across all the data and not just sample size.
                    * MUST: Validate before sharing final analysis.
                    * Data (dataframe) is in memory and not supposed to be fetched from any file.
                    * For any syntax error, make sure to fix/modify to code and then try again.
                    """

            agent_max_iterations = 20
            pandas_agent = create_pandas_dataframe_agent(
                llm,
                df,
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
                callback_manager=callback_manager,
            )
            result = pandas_agent.invoke(task_formatted)
        except Exception as e:
            result = handle_agent_error(e)
        finally:
            return result

    @tool
    def get_input_model_catalog_insight(query: str) -> str:
        """Use query to get insight about input data model from its catalog data."""
        result = "input model catalog not available!"
        try:
            df = pd.read_json(input_project_config["catalog"])
            task_formatted = f"""You are tasked with searching through the catalog and share the insights. \n\n
                Note: 
                * Goal for data mapping - {query}. Analysis should be across all the data and not just sample size.
                * MUST: Validate before sharing final analysis.
                * Data (dataframe) is in memory and not supposed to be fetched from any file.
                * For any syntax error, make sure to fix/modify to code and then try again.
                """
            agent_max_iterations = 20
            pandas_agent = create_pandas_dataframe_agent(
                llm,
                df,
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
                callback_manager=callback_manager,
            )
            result = pandas_agent.invoke(task_formatted)
        except Exception as e:
            result = handle_agent_error(e)
        finally:
            return result

    # Teams
    def create_code_writer_team():
        def make_supervisor_node(llm: BaseChatModel, members: list[str]) -> str:
            options = ["FINISH"] + members
            system_prompt = (
                "You are a supervisor tasked with managing a conversation between the"
                f" following workers: {members}. Given the following user request,"
                " respond with the worker to act next. Each worker will perform a"
                " task and respond with their results and status. When finished,"
                " respond with FINISH."
            )

            class Router(TypedDict):
                """Worker to route to next. If no workers needed, route to FINISH."""

                next: Literal[*options]

            def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
                """An LLM-based router."""

                logger.info(f"===supervisor_node===")
                # Ensure it always goes to `code_generator` first
                if not state.get("writer_ran_once"):
                    return Command(
                        goto="code_generator",
                        update={"writer_ran_once": True, "next": "code_generator"}
                    )

                # Normal routing afterwards
                messages = [{"role": "system", "content": system_prompt}] + state["messages"]
                response = llm.with_structured_output(Router).invoke(messages)
                goto = response["next"]
                if goto == "FINISH":
                    goto = END

                return Command(goto=goto, update={"next": goto})

            return supervisor_node

        code_writer_agent = create_react_agent(
            reasoning_llm,
            tools=[create_manage_memory_tool(namespace=("memories",)),
                   create_search_memory_tool(namespace=("memories",)),
                   get_output_model_skeleton, ],
            prompt=(
                "You can understand, read, and write python codes based on target goal outlines or feedback shared. "
                "Don't ask follow-up questions."
                "Only focus on the previously provided feedback comments, if any."
                "Make sure to convert every non-code text as comments, with a prefix #"
            ),
            store=mem_store
        )

        code_validator_agent = create_react_agent(
            reasoning_llm,
            tools=[create_manage_memory_tool(namespace=("memories",)),
                   create_search_memory_tool(namespace=("memories",)),
                   python_repl_tool,
                   get_output_model_skeleton, ],
            prompt=(
                "You can review, test and validate python codes based on target goal outlines. "
                "Don't ask follow-up questions."
                "The goal is to make sure the coder is writing a sound/valid code and not missing any aspects."
                "Do not remove any existing logic from the existing code. Ensure the merged version is functional."
                "ALWAYS return the entire code, along with opinions like `#approved` or `#feedback` in the response. Provide feedback comments, in case."
                "Make sure to convert every non-code text as comments, with a prefix #"
            ),
            store=mem_store
        )

        def code_writer_node(state: State):
            logger.info(f"===code_writer_node===")
            result = code_writer_agent.invoke(state)
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=result["messages"][-1].content, name="code_generator")
                    ]
                },
                # We want our workers to ALWAYS "report back" to the supervisor when done
                goto="supervisor",
            )

        def code_executor_validator_node(state: State):
            logger.info(f"===code_executor_validator_node===")
            result = code_validator_agent.invoke(state)
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=result["messages"][-1].content, name="code_validator")
                    ]
                },
                # We want our workers to ALWAYS "report back" to the supervisor when done
                goto="supervisor",
            )

        coder_supervisor_node = make_supervisor_node(reasoning_llm, ["code_generator", "code_validator"])

        # Create the graph here
        code_writer_builder = StateGraph(State)
        code_writer_builder.add_node("supervisor", coder_supervisor_node)
        code_writer_builder.add_node("code_generator", code_writer_node)
        code_writer_builder.add_node("code_validator", code_executor_validator_node)

        code_writer_builder.add_edge(START, "supervisor")
        code_writer_builder_graph = code_writer_builder.compile()
        return code_writer_builder_graph

    async def process_last_code(code, feedback, work_directory, output_xml):
        """Process a single sql query."""
        conn_env_str = ""
        input_project_env_vars = {key: value for key, value in os.environ.items() if
                                  key.startswith(input_project.upper())}
        for k, v in input_project_env_vars.items():
            conn_env_str += f"{k},"

        logger.info(f"+++Feedback+++")
        query = f"""For the given feedback: \n\n{json.dumps(feedback, indent=4)}\n\n and existing Python code: \n\n```\n{code}\n```\n\n
The information pertains to destination elements, which are mapped to the source element(s).

* The goal is to fix the existing Python code that 
  1. Establishes a connection to the source database.
  2. Queries **all rows** from the relevant source columns for target entry element.
  3. Iteratively processes each row and maps the data to the appropriate nested XML structure, leveraging the mapping information.
  4. Writes the mapped data to a nested XML format, ensuring the hierarchy is maintained.
  5. Validate if the above element is added to the final code.
  6. Add validation checks for each element, as per the validation information.
* The destination/output should be a nested XML structure, saved to a file in the working directory: {work_directory}, as {output_xml}.
* The provided feedback is from last run, and leveraging traces to fix the code issue.
* MUST: Do not remove anything from the existing code. Ensure the modified version is functional.

Additional Instructions:
* Iteratively process each row from the query result:
  - For each row, map the source columns to the corresponding destination elements in the nested XML structure.
  - Ensure the hierarchy is preserved as defined in the dummy XML skeleton.
* ALWAYS use the provided dummy XML skeleton as a reference for the nested structure. But only code the target element.
* MUST: Always remember that the root element of the xml is always `Header`.
* MUST: Always provide error handling (try-catch) for any query, so that rest of the queries run and doesn't fail entire execution.
  * In case any element fails, MAKE SURE `finally` fills in a blank; and skip to next.

====
Here is the connection information available, for dependency. Use the values directly in the code, as required:
{conn_env_str}

Make sure to prefix the table name with owner, in case available.
====
For Database Connection, here is the recommended package to pick up:
ORABLE: oracledb
"""

        code_writer_team = create_code_writer_team()
        value = code_writer_team.invoke({"messages": [("user", query)], "iterations": 0, "error": ""})
        ret_code = value["messages"][-1].content
        if len(ret_code) < 50 and "messages" in value and len(value["messages"]) >= 2:
            return value["messages"][-2].content
        else:
            return ret_code

    async def process_sql_query(entries_with_mapping, code, output_xml, query_vars):
        """Process a single sql query."""
        conn_env_str = ""
        input_project_env_vars = {key: value for key, value in os.environ.items() if key.startswith(input_project.upper())}
        for k, v in input_project_env_vars.items():
            conn_env_str += f"{k},"

        query_vars_str = ""
        for query_var_key, query_var_val in query_vars.items():
            query_vars_str += f"{query_var_key}={query_var_val},"

        entry_elem_str = ""
        for entry in entries_with_mapping:
            logger.info(f"+++Element: {entry['element_name']}+++")
            entry_elem_str += f"{entry['element_name']}({entry['hierarchy_path'] if 'hierarchy_path' in entry else ''}), "
            if "mapping" in entry and "final_mapping" in entry:
                entry.pop("mapping")
        query = f"""For the given mapping elements: {entry_elem_str},

Here is the detail needed for each element: 
\n\n{json.dumps(entries_with_mapping, indent=4)}\n\n and existing Python code: \n\n```\n{code}\n```\n\n
The information pertains to destination elements, which are mapped to the source element(s).

Write Python code that:
1. Establishes a connection to the source database
2. Queries rows from relevant source fields for target entry elements, following hierarchy dependencies
3. Processes each row and maps data to the appropriate nested XML structure, respecting the hierarchy
4. Writes the mapped data to a nested XML format preserving hierarchy
5. Validates if all elements are added to the final code
6. Use this query dependency list:
{query_vars_str}
7. Make the code modularize and have `__name__` as entrypoint

====
### Requirements:
- **MUST**: Include all provided elements in the output code.
- **MUST**: Retain original mapping formulas — treat them as authoritative.
- **MUST**: Use `hierarchy_path`, `hierarchy_cardinality`, and `hierarchy_dependency` to correctly nest elements and accurate merge.
- **MUST**: ALWAYS Use `hierarchy_cardinality` to determine whether to repeat a parent block or nest multiple children.
- **MUST**: Preserve the root XML element as `<Header>`.
- **CRITICAL**: ONLY use element tags that already exist in the dummy XML skeleton. Verify all tags with the skeleton tool before implementation.
- **CRITICAL**: Query elements WITHIN the appropriate hierarchy loop, not all at the root level. Child queries should use values from parent queries when needed.
- **CRITICAL**: Structure the code to follow the exact hierarchy flow defined in the formula - never modify the query/formula logic. Implement loops, iterations, or recursion strictly according to the provided formulas. However, If the elements are in the same level and share similar dependency, feel free to merge them into one final sql call.
- **CRITICAL**: Never limit the results in the code.

### Error Handling:
- **CRITICAL**: Implement error handling for EACH INDIVIDUAL QUERY using separate try/except blocks
- On query failure, only reset the specific element's results to empty - DO NOT reset ALL query results
- Continue processing other elements even if one element's query fails
- **CRITICAL**: Each query must have its own error (try-catch block) recovery to ensure other elements are unaffected by individual failures

### XML Generation Rules:
- The output XML must be saved to `{output_xml}`.
- Reuse and extend the provided code — do not delete existing functionality.
- If an element has multiple values, **repeat the full parent block** rather than nesting multiple values under a single block, according to the cardinality information.

### Notes:
- If `final_mapping` is unavailable, select the mapping with the **highest confidence score**.
- Remove any trailing semicolons (`;`) from SQL queries.
- Always use the dummy XML skeleton for structure reference (only implement the target elements).
- Elements in the current batch exist at the **same hierarchy level** in XML.
- LINK all elements in the current batch to their parent hierarchy using appropriate identifiers. Structure your iteration logic to maintain these relationships.
- Always generate new/modified code via the **code generator** before using any validator.
- Always prefix table names with the owner, if available.
- Always make sure that each element has a str text; elem.text = str(value) if value is not None else ""

### Oracle Connection:
Use the following environment configuration in your code:
{conn_env_str}

====
For Database Connection, here is the recommended package to pick up:
ORABLE: `oracledb`

====
### XML Examples:
1. Each file will have 1 <Header> and each <Header> will always have only 1 <ClientID> and so forth.
2. If <LabSampleID> has multiple value
**Bad**:
```xml
<SamplePlusMethod>
        <LabSampleID>XYZ</LabSampleID>
        <LabSampleID>ABC</LabSampleID>
        <LabSampleID>DEF</LabSampleID>
</SamplePlusMethod>
```
**Correct**:
```xml
<SamplePlusMethod>
        <LabSampleID>XYZ</LabSampleID>
</SamplePlusMethod>
<SamplePlusMethod>
        <LabSampleID>ABC</LabSampleID>
</SamplePlusMethod>
<SamplePlusMethod>
        <LabSampleID>DEF</LabSampleID>
</SamplePlusMethod>
```

3. if <CASRegistryNumber> has multiple value
**Bad**:
```xml
<Analysis>
    <Analyte>
         <CASRegistryNumber>XYZ</CASRegistryNumber>
         <CASRegistryNumber>ABC</CASRegistryNumber>
    </Analyte>
</Analysis>
```
**Correct**:
```xml
<Analysis>
    <Analyte>
         <CASRegistryNumber>XYZ</CASRegistryNumber>
    </Analyte>
</Analysis>
<Analysis>
    <Analyte>
         <CASRegistryNumber>ABC</CASRegistryNumber>
    </Analyte>
</Analysis>
```

====
### Example Hierarchy-Based Query Approach:
```python
# Pseudocode showing correct hierarchy-based querying with element groups:

# 1. First query top-level elements
try:
    # Query for ClientID at root level
    client_query = "SELECT ..."
    cursor.execute(client_query)
    client_rows = cursor.fetchall()
except Exception as e:
    print(f"Error querying ClientID: {{e}}")
    client_rows = []  # Only reset this specific element

# 2. For each parent element, create its XML node
for client_row in client_rows:
    client_id = client_row[0]
    
    # Create Header element
    header = ET.Element('Header')
    
    # Add ClientID to Header
    client_id_elem = ET.SubElement(header, 'ClientID')
    client_id_elem.text = client_id
    
    # 3. Query for contact information group elements together
    try:
        # Query for all contact information fields at once
        contact_query = \"""
            SELECT lab_id, lab_name, lab_address1, lab_city, lab_state, lab_zipcode
            FROM lab_contact_info
            WHERE client_id = :client_id
        \"""
        cursor.execute(contact_query, {{'client_id': client_id}})
        contact_rows = cursor.fetchall()
    except Exception as e:
        print(f"Error querying ContactInformation: {{e}}")
        contact_rows = []  # Only reset this specific element group
    
    # 4. Process each contact information row as a complete group
    for contact_row in contact_rows:
        # Create ContactInformation group element that will contain all related fields
        contact_info = ET.SubElement(header, 'ContactInformation')
        
        # Add all contact info fields to the group element
        lab_id_elem = ET.SubElement(contact_info, 'LabID')
        lab_id_elem.text = contact_row[0]
        
        lab_name_elem = ET.SubElement(contact_info, 'LabName')
        lab_name_elem.text = contact_row[1]
        
        lab_address_elem = ET.SubElement(contact_info, 'LabAddress1')
        lab_address_elem.text = contact_row[2]
        
        # Add remaining elements...
        
    # 5. Query and process other element groups as needed...
```
"""

        code_writer_team = create_code_writer_team()
        value = code_writer_team.invoke({"messages": [("user", query)], "iterations": 0, "error": ""})
        ret_code = value["messages"][-1].content
        if len(ret_code) < 50 and "messages" in value and len(value["messages"]) >= 2:
            return value["messages"][-2].content
        else:
            return ret_code

    async def process_xml_catalog_mapping(xml_path, output_app, input_app, query_vars, existing_mapping=None):
        """Extract schema metadata from an XML file."""
        parser = ET.XMLParser(forbid_external=True)
        tree = ET.parse(xml_path, parser=parser)
        root = tree.getroot()
        catalog = []

        async def traverse_element(element, parent_path="", level=0, existing_mapping=None):
            """Recursive function to extract metadata from XML elements."""
            element_path = f"{parent_path}/{element.tag}" if parent_path else element.tag
            current_level = level
            logger.info(f"Processing element: {element_path} (Level: {current_level})")  # Debugging

            # If the element has children, do NOT catalog it (only traverse further)
            if len(element) > 0:
                # Process children in batches (configurable via environment variable)
                batch_size = int(os.environ.get("MAPPING_BATCH_SIZE", 20))
                children = list(element)
                for i in range(0, len(children), batch_size):
                    batch = children[i:i+batch_size]
                    tasks = [traverse_element(child, element_path, level=current_level + 1, existing_mapping=existing_mapping)
                             for child in batch]
                    await asyncio.gather(*tasks)
                return  # Exit early, do NOT catalog non-leaf nodes

            # Process all attributes as a single list (if any)
            attr_list = list(element.attrib.keys()) if element.attrib else []

            logger.info(f"+++Element: {element.tag}+++")

            catalog_entry = next(
                (entry for entry in existing_mapping if entry.get("element_name") == element.tag and entry.get("parent_path") == parent_path),
                None
            ) if existing_mapping else None

            if not catalog_entry:
                # Process element content (text)
                if element.tag and element.tag.strip() and not element.tag.strip().lower() == "header":
                    enrich_question = f"Provide detailed information about the element '{element.tag}' with element path: {element_path}. Please return the response in json format:" \
    """
    {
        "description": "Provide a detailed description for the XML element. Explain its purpose, expected values, and how it is used within the system. Include examples of common values if applicable.",
        "relation": "Provide relationships between this element and other elements within the document hierarchy. List any known related elements.",
        "cardinality": "Provide cardinality of this element. List any known elements.",
        "hierarchy_dependency": "Provide route to reach to this element from level 0. Include what all identifiers from previous level(s), it should consider for traversal and querying.",
        "hierarchy_cardinality": "Indicates whether the relationship between this element and its parent is 1:1 or 1:many. Use this to determine if the element should be nested within a single parent block or if the parent block needs to be repeated for each value during XML generation." 
        "validation_rules": "What are the validation rules for the element? Include constraints like data type, length restrictions, required fields, regex patterns, and business logic validations.",
        "category": "One Word. Classify the element into one of the following categories: Identifier, Measurement, Date/Time, Categorical, Metadata, Reference."
    }
    
    Note: Make sure to provide information only when you have actually get it from the source context.
    """
                    elem_response = await run_rag(output_app, enrich_question, True, True, True, False, output_project)
                    elem_data = extract_json_from_response(elem_response)
                    if not isinstance(elem_data, dict) or "description" not in elem_data:
                        logger.debug("Invalid table overview response format")
                        elem_response = await run_rag(output_app, enrich_question, True, True, True, False, output_project)
                        elem_data = extract_json_from_response(elem_response)
                        if not isinstance(elem_data, dict) or "description" not in elem_data:
                            logger.debug("Invalid table overview response format")
                            return

                    catalog_entry = {
                        "element_name": element.tag,
                        "attribute_names": attr_list,
                        "data_type": "string",
                        "default_value": element.text.strip() if element.text else "",
                        "relation": elem_data["relation"] if "relation" in elem_data else "",
                        "description": elem_data["description"] if "description" in elem_data else "",
                        "validation_rules": elem_data["validation_rules"] if "validation_rules" in elem_data else "",
                        "category": elem_data["category"] if "category" in elem_data else "",
                        "hierarchy_dependency": elem_data[
                            "hierarchy_dependency"] if "hierarchy_dependency" in elem_data else "",
                        "hierarchy_cardinality": elem_data[
                            "hierarchy_cardinality"] if "hierarchy_cardinality" in elem_data else "",
                        "hierarchy_path": element_path,
                        "parent_path": parent_path,
                        "level": current_level,
                        "source_type": "xml",
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

            if catalog_entry and "mapping" not in catalog_entry:
                query_vars_str = ""
                for query_var_key, query_var_val in query_vars.items():
                    query_vars_str += f"{query_var_key}={query_var_val},"

                map_enrich_question = f"""From the list of tables/column in context, help map the valid/correct table/column which the following output element should map to.\n
Here is the information about output element: \n\n{catalog_entry}\n\n
Respond with the appropriate table/column source from where this information can be obtained. The goal is to map and extract the correct value for all rows. 

**Note:**
* Make sure the primary_table/alternative_tables and source_column exists and valid for mapping.
* Make sure to run the queries, validate - primary_table/alternative_tables and source_column and the query needed to query it.
* **CRITICAL**: Remove any trailing semicolons (`;`) from SQL queries. Don't try query with semicolon (;) at the end.
* Make sure to provide information only when you have actually get it from the source context.
* MUST: Always give preference to actual data than business logic.

**CRITICAL JOIN REQUIREMENTS**
Include these elements in your traversal path and formula:
* Use appropriate primary/foreign key relationships for all joins
* Consider the primary keys and foreign keys for joins
* Incorporate all source tables from the query dependency list:
{query_vars_str}

=====
**(High Priority) System/User Hints:**
- For a target project, there will ALWAYS 1 customer information, not more than that
- Define elements mapping as per the hierarchy, for example: LabID at root level might mean different than LabID at child level
- Lab details are defined as Site information (where research was conducted or reported)
- Use all applicable persistent IDs for join traversal
- ALWAYS start with LIMS_PROJECTS to get all the information about the project and then join to the target table for getting the target field
- ALWAYS consult table LIMS_PERMANENT_IDS for all primary keys for JOIN
- ALWAYS consult table Auxiliary table like DMART_AUXILIARY_DATA for additional context
- MUST: When using a table to join, USE all its primary (composite) keys for JOIN

Please return the response in json format:\n
====
**Output**
[
    {{
        "source_column": "source column(s) for mapped attribute/element. make sure it exists in database",
        "primary_table": "source table for mapped attribute/element. make sure it exists in database",
        "alternative_tables": "alternate table for mapped source_column. make sure it exists in database",
        "join_path_traversal": [
            "list of traversals for join_path traversal from project id/seq: ({query_vars_str}) to source_column, with notes about efficiency. Something to be considered for `formula`",
            ...
        ],
        "description": "Provide a detailed description for the database column. Explain its purpose, expected values, and how it is used within the system. If relevant, include examples of common values and their meanings",
        "explanation": "Concise explanation of the source-to-destination mapping logic",
        "formula": "sql query for translating the input column to output attribute/element, keeping in mind the `join_path_traversal` (above mentioned conditions/filters) list",
        "validation_rules": "validation rules for the translated values",
        "cardinality": "Provide cardinality of this element",
        "is_primary_key": "True or False",
        "confidence_score": "confidence percentage score 1-100 about the mapping",
        "category": "One Word. Classify the column into one of the following categories: Identifier, Measurement, Date/Time, Categorical, Metadata, Reference. Explain the explanation for the chosen category"
    }},
    {{
        ... other source column candidates as per the confidence score
    }}
]
"""
                map_response = await run_rag(input_app, map_enrich_question, True, True, True, False, input_project)
                map_data = extract_json_from_response(map_response)
                output = map_data["output"] if "output" in map_data else map_data
                if not isinstance(output, List) or "formula" not in output[0]:
                    logger.debug("Invalid table overview response format")
                    map_response = await run_rag(input_app, map_enrich_question, True, True, True, False, input_project)
                    map_data = extract_json_from_response(map_response)
                    output = map_data["output"] if "output" in map_data else map_data
                    if not isinstance(output, List) or "formula" not in output[0]:
                        logger.debug("Invalid table overview response format")
                        output = None
                if output:
                    catalog_entry["mapping"] = output

            if catalog_entry:
                catalog.append(catalog_entry)
                logger.info(f"Added text content for element: {element.tag}")  # Debugging

            # Recursively process child elements
            for child in element:
                await traverse_element(child, element_path, level=current_level + 1, existing_mapping=existing_mapping)

        # Start traversal from the root element.
        await traverse_element(root, existing_mapping=existing_mapping)
        return catalog

    async def persist_catalog(file_path, catalog, output_format="csv"):
        """Save the catalog as CSV or JSON."""
        df = pd.DataFrame(catalog)
        if output_format == "csv":
            df.to_csv(file_path, index=False)
            return f"Catalog saved as {file_path}"
        elif output_format == "json":
            with open(file_path, "w") as f:
                json.dump(catalog, f, indent=4)
            return f"Catalog saved as {file_path}"

    async def persist_mapping(file_path, mappings, output_format="json"):
        """Save the mappings as CSV or JSON."""
        if output_format == "csv":
            df = pd.DataFrame(mappings)
            df.to_csv(file_path, index=False)
            return f"Mappings saved as {file_path}"
        elif output_format == "json":
            with open(file_path, "w") as f:
                json.dump(mappings, f, indent=4)
            return f"Mappings saved as {file_path}"

    async def persist_code(file_path, code, output_format="python"):
        """Save the mappings as CSV or JSON."""
        if output_format == "python":
            with open(file_path, "w") as f:
                f.write(code)
            return file_path
        return None

    # ----- Func ----- #

    async def mapping_step(state: PlanExecute):
        logger.info ("\n\n###### MAPPING ######\n\n")
        # Preserve the mapping_only flag if it exists in the state
        mapping_only = state.get("mapping_only", False)
        logger.info(f"Preserving mapping_only flag: {mapping_only}")
        
        # traverse on output_catalog_entries
        mapping_file = os.path.join(output_project_config["work_directory"],
                                    f"{input_project}_{output_project}_data_catalog_{state['session_id']}.json")
        mapping_default_file = os.path.join(output_project_config["work_directory"],
                                            f"{input_project}_{output_project}_data_catalog_default.json")
        og_mappings_dict = {}
        mappings = []
        try:
            if (os.path.exists(mapping_file)):
                with open(mapping_file, "r", encoding="utf-8") as file:
                    mappings = json.load(file)
            if (os.path.exists(mapping_default_file)):
                with open(mapping_default_file, "r", encoding="utf-8") as file:
                    # Create a dictionary for quick lookup using element_name as the key
                    og_mappings_dict = {item['element_name']: item for item in mappings}
            if og_mappings_dict and not mappings:
                mappings = og_mappings_dict
        except Exception as e:
            logger.error(e)
            mappings = []
        mappings = await process_xml_catalog_mapping(os.path.join(output_project_config["data_path"], "dummy.xml"), output_rag_app, input_rag_app, state["query_vars"], existing_mapping=mappings)
        sorted_mappings = sorted(mappings, key=lambda x: x.get('level', 0))
        await persist_mapping(mapping_file, sorted_mappings, output_format="json")

        # Update existing or add new elements
        for item in sorted_mappings:
            og_mappings_dict[item['element_name']] = item
        # Convert the dictionary back to a list
        og_mappings = []
        og_mappings[:] = list(og_mappings_dict.values())

        await persist_mapping(os.path.join(output_project_config["work_directory"],
                                           f"{input_project}_{output_project}_data_catalog_default.json"),
                              og_mappings, output_format="json")

        # Return the mapping_only flag in the result state
        result = {"mapping": sorted_mappings, "mapping_file": mapping_file}
        if mapping_only:
            result["mapping_only"] = mapping_only
        return result

    async def mapping_validation_step(state: PlanExecute):
        # Check if mapping_only flag is set in the state
        mapping_only = state.get("mapping_only", False)
        logger.info(f"Mapping only mode: {mapping_only}")
            
        # TODO: Refer to a ERD document directly
        # TODO: break the whole response into parts and ask about it; it will add accuracy
        local_id_mapping = {}
        mapping_file = state["mapping_file"]

        query_vars_str = ""
        for query_var_key, query_var_val in state["query_vars"].items():
            query_vars_str += f"{query_var_key}={query_var_val},"

        mapping = state["mapping"]
        logger.info("###### VALIDATING/FINALIZING MAPPING ######")

        # Process identifiers first to build local_id_mapping
        for entry in mapping:
            level = entry["level"]
            logger.info(f"+++Element: {entry['element_name']}+++")
            # collecting identifier mapping list (level wise) from existing catalog
            if "final_mapping" in entry:
                output = entry["final_mapping"]
                if entry["category"].lower() == "Identifier".lower():
                    if level in local_id_mapping:
                        local_id_mapping[level][f"{entry['element_name']}/{output['source_column']}"] = output["formula"]
                    else:
                        local_id_mapping[level] = {f"{entry['element_name']}/{output['source_column']}": output["formula"]}

        # Define a batch size for parallel processing
        batch_size = int(os.environ.get("MAPPING_VALIDATION_BATCH_SIZE", 20))

        # Define the function to process a single entry
        async def process_entry(entry):
            level = entry["level"]
            if "final_mapping" in entry:
                return entry  # Skip already processed entries

            input_entry = {
                "element_name": entry["element_name"],
                "description": entry["description"],
                "data_type": entry["data_type"],
                "category": entry["category"],
                "validation_rules": entry["validation_rules"],
                "relation": entry["relation"],
                "hierarchy_dependency": entry["hierarchy_dependency"],
                "hierarchy_cardinality": entry["hierarchy_cardinality"],
                "hierarchy_path": entry["hierarchy_path"],
                "parent_path": entry["parent_path"],
                "level": entry["level"],
                "mapping": entry["mapping"],
            }

            # Build conditions string using the current state of local_id_mapping
            conditions = query_vars_str + "\n"
            for i in range(0, level + 1):
                if i in local_id_mapping:
                    conditions += str(local_id_mapping[i]) + "\n"
            input_insight_question = f"""Help validate the SQL query and mapping for the following input entry:\n\n
{json.dumps(input_entry, indent=4)}
\n\n
Return the optimized final mapping with validated source table/column and formula. Your primary responsibility is ensuring the formula is correct and executable as written.
Your primary goal is to provide only one final mapping in the form of a JSON object. The formula should work end-to-end without errors.

**CRITICAL JOIN REQUIREMENTS**
Include these elements in your traversal path and formula:
* Use appropriate primary/foreign key relationships for all joins
* Incorporate all source tables from the query dependency list:
{conditions}
* Consider `hierarchy_path` + `hierarchy_cardinality` + `hierarchy_dependency` and incorporate identifiers from parent levels where feasible

**VALIDATION CHECKLIST:**
1. **BEGIN WITH SPECIFIED FILTERS** - Use provided filters as your starting point to identify correct source tables/columns
   - Confirm filters are accessible in the query or modify with appropriate joins to make them functional
2. **VERIFY DATABASE OBJECTS**
   - Confirm primary_table and ALL alternative_tables exist in source database
   - Verify source_column exists in the identified tables
3. **OPTIMIZE QUERY PATH** - Create comprehensive queries that include ALL relevant tables while prioritizing direct relationships
4. **MAINTAIN COVERAGE AND CONSISTENCY** - Ensure complete join paths with all required identifiers from the parent hierarchy to preserve data relationships and integrity
5. **INCLUDE ONLY VERIFIED DATA** - Return only information confirmed from source context
6. **TEST THOROUGHLY** - Provide only validated queries with efficiency notes compared to alternatives
7. **ENSURE COMPLETENESS** - Never return partial or invalid formulas
8. **VALIDATE EXECUTION** - Test and iterate on each formula until it executes without errors
9. **NO DUPLCIATES** - ALWAYS use no-duplicates and return unique/distinct values using DISTINCT keyword
10. **SINGLE RESULT** - Return exactly ONE final mapping as a JSON object
11. **VALIDATE QUERY RESULTS** - No. of rows returned by the query should honor the cardinality. For example: for 1:1 cardinality, the valid query would always generate 1 row; for 1:many, it would generate multiple rows 
12. **RESPECT HIERARCHY** - Ensure mappings follow the XML hierarchy - child elements should use identifiers from their parent elements when constructing queries

====
**Formula Validation Results/Hints:**

"element_name": "Header/ClientID",
"formula": "SELECT DISTINCT cust_id FROM dmart_projects_summary WHERE project_seq = :project_seq"
"hint": "Should return only 1 row for target project_seq, at level 1"

"element_name": "Header/ProjectID",
"formula": "SELECT DISTINCT project_id FROM lims_projects WHERE project_seq = :project_seq"
"hint": "Should return only 1 row for target project_seq, at level 1"

"element_name": "Header/LabID",
"formula": "SELECT DISTINCT lab_wo_id FROM lims_projects WHERE project_seq = :project_seq"
"hint": "Should return only 1 row for target project_seq, at level 1"

"element_name": "Header/MethodID",
"formula": "SELECT DISTINCT method FROM dmart_edd_results WHERE project_seq = :project_seq"
"hint": "Should return only 1 row for target project_seq, at level 1"

"element_name": "Header/SiteID",
"hint": Refer auxillary data to get the site id

"element_name": "Header/SamplePlusMethod/LabSampleID",
"formula": "SELECT DISTINCT lpi.lab_sample_id FROM dmart_edd_samples des JOIN lims_project_samples lps ON des.project_seq = lps.project_seq JOIN lims_permanent_ids lpi ON lps.hsn = lpi.hsn WHERE des.project_seq = :project_seq"
"hint": "<SamplePlusMethod> can have multiple rows"

"element_name": "Header/SamplePlusMethod/ClientSampleID",
"formula": "SELECT DISTINCT ps.cust_sample_id FROM lims_project_samples ps LEFT JOIN dmart_edd_samples de ON ps.project_seq = de.project_seq WHERE ps.project_seq = :project_seq"
"hint": "<SamplePlusMethod> can have multiple rows"

"element_name": "Header/SamplePlusMethod/ReportedResult/AnalysisGroupID",
"formula": "SELECT DISTINCT ds.schedule_seq FROM lims_projects lp JOIN lims_project_samples lps ON lp.project_seq = lps.project_seq JOIN dmart_edd_schedules ds ON lps.hsn = ds.hsn JOIN dmart_edd_results dr ON ds.schedule_seq = dr.schedule_seq WHERE lp.project_seq = :project_seq"
"hint": "<SamplePlusMethod> can have multiple rows"

"element_name": "Header/SamplePlusMethod/MethodID",
"formula": "SELECT DISTINCT der.method FROM dmart_edd_projects dep JOIN dmart_edd_results der ON dep.project_seq = der.project_seq JOIN dmart_edd_schedules des ON der.schedule_seq = des.schedule_seq WHERE dep.project_seq = :project_seq"
"hint": "<SamplePlusMethod> can have multiple rows"

=====
**Output Format:**
Return a JSON response with the following structure:
{{
    "source_column": "Source column(s) used for the mapped element (validated against actual data source)",
    "explanation": "Concise explanation of the source-to-destination mapping logic",
    "formula": "VERIFIED complete SQL query that properly translates input to output elements, incorporating all required join_path_traversal conditions. SQL must be executable on the target database",
    "query_result": [
        "Actual results from executing the formula query against the database (can be empty if no results, but must be real data, not examples)",
        "..."
        "**CRITICAL NOTE**: never hallucinate and make up any data here"
        "**CRITICAL NOTE**: if the formula failed and didn't generate any result, please feel free to point out that and share insight about whats missing"
        "**CRITICAL NOTE**: if the formula ran but returned empty result, then simply have <empty> in the list"
    ]
}}

=====
**Technical Implementation Guidelines:**
- When retrieving customer information from a project sequence, use direct project details as the primary source
- Use only direct relationships unless indirect ones are specifically required
- CRITICAL: Remove any trailing semicolons (`;`) from SQL queries. Don't try query with semicolon (;) at the end.
- CRITICAL: Follow the project data trail and leverage primary/foreign key relationships for all joins
- CRITICAL: If the initial formula (query) fails, immediately retry with a corrected version based on error diagnostics. Never leave a query in a failed state
- CRITICAL: For nested XML elements, use identifiers from parent elements to ensure hierarchical integrity

=====
**(HIGH PRIORITY) System Requirements:**
- Each target project MUST have EXACTLY ONE customer record associated with it
- Map elements according to their position in the hierarchy (e.g., LabID has different meanings at root vs. child levels)
- Utilize all applicable persistent IDs for join operations
- Use DISTINCT for getting reducing redundancy
- ALWAYS begin with LIMS_PROJECTS table to establish project context before joining to target tables
- ALWAYS reference LIMS_PERMANENT_IDS table for primary key JOIN operations
- ALWAYS check auxiliary tables (DMART_AUX_DATA, DMART_AUXILIARY_DATA) for contextual information such as lab/site details

=====
**IMPLEMENTATION EXAMPLES:**
1. **Customer ID Retrieval**
   When obtaining `cust_id` from a `project_seq`:
   - PRIORITIZE `LIMS_PROJECTS` and `DMART_PROJECTS_SUMMARY` tables (they directly contain `project_seq`, `system_id`, and `cust_id`)
   - JOIN using `project_seq` along with appropriate constraints/keys
   - EXAMPLE QUERY: 
     ```sql
     SELECT cust_id 
     FROM dmart_projects_summary 
     JOIN [additional_tables] ON [join_conditions] 
     WHERE project_seq = :project_seq_id
     ```
    - VALIDATE that exactly ONE `cust_id` record is returned
2. **Lab Information**
    - Always represent Lab details as Site information (research location)
3. **Hierarchical Element Mapping**
    - For nested elements like "Header/SamplePlusMethod/Analysis/LabAnalysisID", ensure the query uses identifiers from parent elements
    - Here, LabAnalysisID should have a dependency on Identifiers in <Analysis> level and also some Identifiers in the <SamplePlusMethod> level
continuing to some identifiers on the <Header> 0 level.
    - Same applies to all the leaf nodes of the <Analysis> level.
    - For all the other leaf nodes of the <SamplePlusMethod> level would have dependency on Identifiers in <Header> 0 level.
     ```
"""
            map_response = await run_rag(input_rag_app, input_insight_question, True, True, True, True, input_project)
            map_data = extract_json_from_response(map_response)
            output = map_data["output"] if "output" in map_data else map_data

            if not isinstance(output, dict) or "formula" not in output:
                logger.debug("Invalid table overview response format")
                map_response = await run_rag(input_rag_app, input_insight_question, True, True, True, True, input_project)
                map_data = extract_json_from_response(map_response)
                output = map_data["output"] if "output" in map_data else map_data
                if not isinstance(output, dict) or "formula" not in output:
                    logger.debug("Invalid table overview response format")
                    output = None

            # Update local_id_mapping: adding identifier for the same/next level to pick up
            if output:
                entry["final_mapping"] = output
                entry["mapping"].append(output)
                if entry["category"].lower() == "Identifier".lower():
                    if level in local_id_mapping:
                        local_id_mapping[level][f"{entry['element_name']}/{output['source_column']}"] = output["formula"]
                    else:
                        local_id_mapping[level] = {f"{entry['element_name']}/{output['source_column']}": output["formula"]}
            return entry

        # Group entries by their 'level' property
        grouped_entries = defaultdict(list)
        for entry in mapping:
            if "final_mapping" not in entry:
                level = entry.get('level')
                grouped_entries[level].append(entry)
        processed_entries = []
        for level, entries in grouped_entries.items():
            for i in range(0, len(entries), batch_size):
                batch = entries[i:i+batch_size]
                batch_results = await asyncio.gather(*[process_entry(entry) for entry in batch])
                processed_entries.extend(batch_results)

        # Update the mapping with processed entries
        for i, entry in enumerate(mapping):
            if "final_mapping" not in entry:
                for processed_entry in processed_entries:
                    if (processed_entry["element_name"] == entry["element_name"] and
                          processed_entry["hierarchy_path"] == entry["hierarchy_path"]):
                        mapping[i] = processed_entry
                        break
        
        # Save the updated mapping
        await persist_mapping(mapping_file, mapping, output_format="json")

        # Check if mapping_only flag is set in the state
        mapping_only = state.get("mapping_only", False)
        logger.info(f"Mapping only mode in validation step: {mapping_only}")

        # save general catalog
        mapping_default = copy.deepcopy(mapping)
        for entry in mapping_default:
            if "final_mapping" in entry:
                output = entry["final_mapping"]
                entry["mapping"].append(output)
                entry.pop("final_mapping", None)  # Safely remove 'mapping' if it exists

        mapping_default_file = os.path.join(output_project_config["work_directory"],
                                    f"{input_project}_{output_project}_data_catalog_default.json")
        if (os.path.exists(mapping_default_file)):
            with open(mapping_default_file, "r", encoding="utf-8") as file:
                mappings = json.load(file)
                # Create a dictionary for quick lookup using element_name as the key
                og_mappings_dict = {item['element_name']: item for item in mappings}

        # Update existing or add new elements
        for item in mapping_default:
            og_mappings_dict[item['element_name']] = item
        # Convert the dictionary back to a list
        og_mappings = []
        og_mappings[:] = list(og_mappings_dict.values())
        await persist_mapping(mapping_default_file, og_mappings, output_format="json")
        
        # If mapping_only flag is set, add a special key to indicate we should stop here
        result = {"mapping": mapping, "mapping_file": mapping_file, "code_rerun": False}
        if mapping_only:
            result["mapping_only"] = mapping_only  # Use the actual value, not just True
            logger.info("Mapping validation completed. Stopping workflow as mapping_only flag is set.")
        
        return result


    async def generating_step(state: PlanExecute):
        code_file = os.path.join(output_project_config["work_directory"],
                                    f"{input_project}_{output_project}_data_mapping_code_{state["session_id"]}.py")
        output_xml = os.path.join(output_project_config["work_directory"], f"output_{state["session_id"]}.xml")

        logger.info("###### CODING ######")
        mapping = state["mapping"]
        if not state["code_rerun"] and (os.path.exists(code_file)):
            with open(code_file, "r", encoding="utf-8") as file:
                code = file.read()
        else:
            feedback = {}
            if "output_code" in state:
                code = state["output_code"]
                if "validation_passed" in state:
                    feedback["validation_passed"] = state["validation_passed"]
                if "validation_message" in state:
                    feedback["validation_message"] = state["validation_message"]
                if "stdout_err_details" in state:
                    feedback["stdout_err_details"] = state["stdout_err_details"]
                if "agent_response" in state:
                    feedback["agent_response"] = state["agent_response"]
                if "is_code_issue" in state:
                    feedback["is_code_issue"] = state["is_code_issue"]
            else:
                code = ""

            if feedback:
                code = await process_last_code(code, feedback, output_project_config["work_directory"], output_xml)
            else:
                # Group entries by their 'level' property
                grouped_entries = defaultdict(list)
                for entry in mapping:
                    level = entry.get('level')
                    grouped_entries[level].append(entry)
                for level, entries in grouped_entries.items():
                    # for entry in entries:
                    try:
                        code = await process_sql_query(entries, code,
                                                       output_xml, state["query_vars"])  # map (get input source) -> sql (write sql query to extract that value) -> validate (run the query on input data and check)
                    except Exception as e:
                        logger.error(e, exc_info=True)

            if code:
                code = code.replace("#approved", "")
                code_file = await persist_code(code_file, code, output_format="python")

        # Check if mapping_only flag is set in the state
        mapping_only = state.get("mapping_only", False)
        logger.info(f"Mapping only mode in generating step: {mapping_only}")
        
        # Return the mapping_only flag in the result state
        result = {"output_code": code, "code_file": code_file, "mapping": mapping}
        if mapping_only:
            result["mapping_only"] = mapping_only
        return result


    async def validating_step(state: PlanExecute):
        output_code = state["output_code"]
        code_file = state["code_file"]
        output_xml = os.path.join(output_project_config["work_directory"], f"output_{state["session_id"]}.xml")

        logger.info("###### VALIDATING RESULT ######")

        conn_env_str = ""
        input_project_env_vars = {key: value for key, value in os.environ.items() if key.startswith(input_project.upper())}
        for k, v in input_project_env_vars.items():
            conn_env_str += f"{k},"
            
        # Create a validator agent with access to Python REPL and XML validation capabilities
        validator_agent = create_react_agent(
            llm,
            tools=[
                shell_tool,
                get_output_model_skeleton,
                create_manage_memory_tool(namespace=("memories",)),
                create_search_memory_tool(namespace=("memories",)),
            ],
            prompt = (
    "You are an expert XML validator and Python code executor/reviewer. Your task is to:\n"
    "1. **Review the provided Python code** using the shared output and ensure it runs without errors.\n"
    "2. **Validate the generated XML** using the expected output format, to ensure it is well-formed and valid.\n"
    "Provide detailed feedback on what needs to be fixed, if applicable.\n"
    "Be thorough in your analysis and provide actionable feedback.\n"
    """
    ## Required Response Format:
    Please return your response strictly in the following JSON format:
    ```json
    {
        "validation_passed": "True or False, based on the validation outcome.",
        "validation_message": "Summary and reason for the validation result.",
        "stdout_err_details": "Include stdout, stderr, and any stack traces.",
        "is_code_issue": "True if a code-level issue (execution or logic error) is detected, otherwise False.",
        "summary_response": "Concise summary of the validation results."
    }
    ```
    """
            ),
            store=mem_store,
        )

        code_output = python_repl_tool(output_code)

        # Prepare the validation task for the agent
        validation_task = f"""
Your task is to execute/validate a Python script and the XML output it generates.

## Python Code with Output:
```python
{code_output}
```

## Environment Variable for Execution:
{conn_env_str}
- Apply this environment variable before code execution to ensure successful connection.
- Make sure required ENV-Variables are set correctly, as required given {conn_env_str}"

## Task Instructions:
1. Execute the code from: `{code_file}` using the `python_repl` tool.
2. Confirm the code generates an XML file at: `{output_xml}`.
3. Compare the generated XML structure with a provided dummy XML using the `output` tool.
4. Assume all required dependencies (packages and environment variables) are available.
5. If any required packages are missing, install them using the `terminal` tool and rerun the code.

## Validation Criteria:
- Confirm successful generation of the output XML
- Ensure the output XML structure matches the dummy XML by validating:
    - Matching XML tags
    - Presence of all required attributes from the dummy XML. If no values, it could be empty tags
    - Preservation of the child element hierarchy

## If Validation Fails:
- Identify if the failure is due to:
    - Code execution errors (e.g., syntax, runtime errors)
    - XML structure mismatches
- Provide detailed findings:
    - Specifics on the issue
    - Clear recommendations on what needs to be fixed
"""
        
        # Invoke the validator agent
        try:
            validation_result = validator_agent.invoke({"messages": [HumanMessage(content=validation_task)]})
            agent_response = validation_result["messages"][-1].content
            agent_data = extract_json_from_response(agent_response)
            if not isinstance(agent_data, dict) or "validation_passed" not in agent_data:
                logger.debug("Invalid validation result overview response format")
                validation_result = validator_agent.invoke({"messages": [HumanMessage(content=validation_task)]})
                # validation_result = code_validator_team.invoke(
                    # {"messages": [("user", validation_task)], "iterations": 0, "error": ""})
                agent_response = validation_result["messages"][-1].content
                agent_data = extract_json_from_response(agent_response)
                if not isinstance(agent_data, dict) or "validation_passed" not in agent_data:
                    logger.debug("Invalid validation result overview response format")
                    return
            
            # # Parse the agent's response to extract structured information
            # validation_passed = "validation passed" in agent_response.lower()
            #
            # # Extract validation message and error details
            # validation_message = "Valid" if validation_passed else "Invalid XML structure"
            # error_details = ""
            #
            # if not validation_passed:
            #     # Try to extract specific error details from the agent's response
            #     error_pattern = r"(?:error|issue|problem|failed):\s*(.*?)(?:\n|$)"
            #     error_matches = re.findall(error_pattern, agent_response, re.IGNORECASE)
            #     if error_matches:
            #         error_details = " ".join(error_matches)
            #     else:
            #         error_details = "Unspecified validation error"
            #
            # # Determine if it's a code issue
            # is_code_issue = any(term in agent_response.lower() for term in
            #                    ["code issue", "code problem", "execution error", "syntax error",
            #                     "runtime error", "code fix", "modify the code"])
            
            # Check if mapping_only flag is set in the state
            mapping_only = state.get("mapping_only", False)
            logger.info(f"Mapping only mode in validating step: {mapping_only}")
            
            # Generate detailed validation report
            validation_report = {
                "output_file": output_xml if os.path.exists(output_xml) else None,
                "validation_passed": True if agent_data["validation_passed"] and os.path.exists(output_xml) else False,
                "validation_message": agent_data["validation_message"],
                "stdout_err_details": agent_data["stdout_err_details"],
                "is_code_issue": True if agent_data["is_code_issue"] else False,
                "agent_response": agent_data["summary_response"],
                "response": f"XML validation {'passed' if agent_data["validation_passed"] else 'failed: ' + agent_data["stdout_err_details"]}",
                "code_rerun": True,
                "mapping_file": state["mapping_file"],
                "code_file": state["code_file"],
                "mapping": state["mapping"],
            }
            
            # Preserve the mapping_only flag in the result
            if mapping_only:
                validation_report["mapping_only"] = mapping_only
            
            return validation_report
            
        except Exception as e:
            print(f"Error during agent-based validation: {str(e)}")
            # Check if mapping_only flag is set in the state
            mapping_only = state.get("mapping_only", False)
            logger.info(f"Mapping only mode in validating step (error case): {mapping_only}")
            
            error_report = {
                "output_file": output_xml if os.path.exists(output_xml) else None, 
                "validation_passed": False, 
                "error": str(e),
                "is_code_issue": True,  # Assume agent failure is a code issue
                "response": f"Error during validation: {str(e)}",
                "mapping_file": state["mapping_file"],
                "code_file": state["code_file"],
                "mapping": state["mapping"],
            }
            
            # Preserve the mapping_only flag in the result
            if mapping_only:
                error_report["mapping_only"] = mapping_only
                
            return error_report

    # Define a routing function
    async def route_after_validation(state: PlanExecute):
        if state.get("validation_passed") is False:
            # Create a detailed error message for the generation step
            error_message = state.get("stdout_err_details", state.get("validation_message", "Unknown error"))
            agent_feedback = state.get("agent_response", "")
            
            # Prepare a detailed question for the code generator
            if state.get("is_code_issue", True):
                state["question"] = f"""
                Fix the code to address the following XML validation issue:
                
                ERROR: {error_message}
                
                VALIDATOR FEEDBACK:
                {agent_feedback}
                
                Please correct the code to properly generate the XML with the expected structure.
                """

                # TODO: backing off last code file
                return "code_generation"
            else:
                # If it's a structural issue but not necessarily a code issue
                state["question"] = f"""
                The XML structure validation failed with the following issue:
                
                ERROR: {error_message}
                
                VALIDATOR FEEDBACK:
                {agent_feedback}
                
                Please modify the tools/environment to ensure the generated XML matches the expected structure.
                """
                return "code_validator"
        else:
            return "__end__"

    workflow = StateGraph(PlanExecute)

    # Add the nodes
    workflow.add_node("mapper", mapping_step)
    workflow.add_node("mapping_validator", mapping_validation_step)
    workflow.add_node("code_generation", generating_step)
    workflow.add_node("code_validator", validating_step)

    # Add the edges with conditional routing
    workflow.add_edge(START, "mapper")
    workflow.add_edge("mapper", "mapping_validator")
    
    # Define a routing function after mapping validation
    def route_after_mapping_validation(state):
        # Check if mapping_only flag is set in the state
        # Log the entire state for debugging
        logger.info(f"State in route_after_mapping_validation: {state}")
        
        # Check both the root state and the mapping_only flag that might be set in the mapping_validation_step
        if ("mapping_only" in state and state["mapping_only"]) or state.get("mapping_only", False):
            logger.info("Routing to END after mapping validation as mapping_only flag is set")
            return "__end__"  # Route to END if mapping_only is True
        else:
            logger.info("Routing to code_generation after mapping validation")
            return "code_generation"  # Continue with code generation otherwise
    
    # Add conditional edge from mapping_validator based on the mapping_only flag
    workflow.add_conditional_edges(
        "mapping_validator",
        route_after_mapping_validation,
        {
            "code_generation": "code_generation",
            "__end__": END
        }
    )
    
    # Add remaining edges for the workflow
    workflow.add_edge("code_generation", "code_validator")
    workflow.add_conditional_edges(
        "code_validator",
        route_after_validation,
        {
            "code_validator": "code_validator",
            "code_generation": "code_generation",
            "__end__": END
        }
    )

    # Finally, we compile it!
    app = workflow.compile(checkpointer=checkpoint_memory)

    return app


async def run(question: str, app):
    # Run
    initial_state = {
        "question": question,
        "query_vars": {
            "PROJECT_SEQ": "10686061"
        },
        "session_id": "8fe0c5a2-d2c9-47af-b273-ca58f199912a".replace("-", "_")
    }
    config = {
        "recursion_limit": 25,
        "handle_parsing_errors": True,
        "configurable": {
            "thread_id": "chicory-harmonization",
            "thread_ts": datetime.now(UTC).isoformat(),
            "client": "brewhub-wk",
        }
    }
    try:
        async for event in app.astream(initial_state, config=config):
            for key, value in event.items():
                pprint(f"Node '{key}':")
                # if key != "__end__":
                #     print(value)

        if 'generation' in value:
            pprint(value["generation"])
        elif 'data_summary' in value:
            pprint(value["data_summary"])
        else:
            pprint(value)
    except Exception as e:
        logger.error(e)
        return f"Try again. {str(e)}"
