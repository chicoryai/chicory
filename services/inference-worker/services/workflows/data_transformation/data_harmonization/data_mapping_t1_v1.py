import asyncio
import operator
import os
from datetime import datetime, UTC, time
from pprint import pprint

import streamlit as st

import pandas as pd
from langchain.agents import AgentType
from typing import TypedDict, Annotated, Tuple

from langchain.globals import set_llm_cache
from langchain_core.caches import InMemoryCache
from langchain_core.callbacks import CallbackManager
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_experimental.utilities import PythonREPL
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import START
from matplotlib import pyplot as plt
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langchain_core.tools import Tool

import sys
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List, Union
from langchain.schema import AgentAction, AgentFinish

from services.customer.personalization import get_project_config
from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v4 import initialize_brewsearch_state_workflow
from services.integration.phoenix import initialize_phoenix


class PlanExecute(TypedDict):
    question: str
    data: List[pd.DataFrame]
    plan: str
    tools: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    schema: str
    data_mapping_summary: dict


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

    action: Response = Field(
        description="Action to perform. If you want to respond to user, use Response. "
                    "If you need to further use tools to get the answer, use Plan."
    )


memory = MemorySaver()
set_llm_cache(InMemoryCache())


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

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        self.log_to_file(f"Error: {error}")

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        self.log_to_file("Chain started...")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        self.log_to_file("Chain ended.")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        self.log_to_file(f"Using tool: {serialized['name']}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        self.log_to_file("Tool execution completed.")

    def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        self.log_to_file(f"Agent action: {action}")

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        self.log_to_file("Agent finished.")

    def handle_plt_show(self):
        self.figure_counter += 1
        # Get the current time formatted to include milliseconds
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"figure_{current_time}.png"
        filepath = os.path.join(self.image_dir, filename)

        plt.savefig(filepath)
        plt.close()
        self.log_to_file(f"Figure saved: {filename}")


class VanillaStreamingCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.text = ""
        self.figure_counter = 0

    def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        print("LLM started...")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        sys.stdout.write(token)
        sys.stdout.flush()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        print("\nLLM finished.")

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        print(f"\nError: {error}")

    def on_chain_start(
            self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        print("Chain started...")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        print("Chain ended.")

    def on_tool_start(
            self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        print(f"Using tool: {serialized['name']}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        print("Tool execution completed.")

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        print(f"Agent action: {action.tool}")

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        print("Agent finished.")

    def handle_plt_show(self):
        self.figure_counter += 1
        filename = f"figure_{self.figure_counter}.png"
        plt.savefig(filename)
        plt.close()  # Close the figure to free up memory
        print(f"Figure saved as {filename}")


class StreamlitCallbackHandler(BaseCallbackHandler):
    def __init__(self, container: st.delta_generator.DeltaGenerator):
        self.container = container
        self.text = ""
        self.figure_counter = 0

    def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        self.container.write("LLM started...")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.text += token
        self.container.markdown(self.text)

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self.container.write("LLM finished.")

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        self.container.error(f"Error: {error}")

    def on_chain_start(
            self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        self.container.write("Chain started...")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        self.container.write("Chain ended.")

    def on_tool_start(
            self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        self.container.write(f"Using tool: {serialized['name']}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        self.container.write("Tool execution completed.")

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        self.container.write(f"Agent action: {action.tool}")

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        self.container.write("Agent finished.")

    def handle_plt_show(self):
        self.figure_counter += 1
        filename = f"figure_{self.figure_counter}.png"
        plt.savefig(filename)
        plt.close()  # Close the figure to free up memory
        self.container.write(f"Figure generated:")
        self.container.image(filename)
        os.remove(filename)  # Remove the file after displaying


def initialize_harmonization_workflow_agent(user=None, project=None, response_container=None, file_loader=False):
    phoenix_project_name = f"brewhub-workflow-mapping{f"-{user}" if user else "-dev"}{f"-{project}" if project else "-default"}"
    os.environ["PHOENIX_PROJECT_NAME"] = phoenix_project_name
    initialize_phoenix()

    # Initialize OpenAI components
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    llm_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    reasoning_llm = ChatOpenAI(model="gpt-4o", temperature=0) # TODO: convert to o3
    chat_llm = ChatOpenAI(model="chatgpt-4o-latest", temperature=0)

    if project.lower() == "PDM".lower():
        rag_app = initialize_brewsearch_state_workflow(user, project, phoenix_project_name)
    else:
        rag_app = None

    # Step 1:
    project_config = get_project_config(project)
    if not project_config:
        return None

    trimmer = trim_messages(
        max_tokens=124000,
        strategy="last",
        token_counter=llm,
        include_system=True,
    )

    planner_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """As a world-class Data analyst/engineer and BI specialist with expertise in e-commerce data, for the given objective,
come up with a detailed, step-by-step execution plan and provide comprehensive learnings for extracting/transforming attributes from the given dataset.
The goal of the tasks/steps is to modify the dataset to make successful transformation/harmonization of the passed dataset for agreed upon outcome.
This plan should cover individual tasks strictly within the scope of data analysis, ensuring that, if executed correctly, they yield a thorough transformation of the dataset and final mapping.
Ensure each step is self-contained with all necessary information and avoid skipping steps.

**Note:**
* Make sure to expand user's original question for a detailed planning.
* Include analysis action hints for analysts/execution to refer to; be as detailed as possible.
* The overall goal is strictly data transformation/harmonization for the given question and context.
* Make sure to consider all dataframes for analysis, as applicable.
* Make sure to consider any preprocessing/enriching/merging/cleaning of the data for each analysis, as required.
* Elaborate on user's question to more clarity
* MUST: Conduct (statistical) visualization analysis for each step, if applicable. Extract learnings from every analysis.
* MUST: Summarize and describe every field, including data types, allowed values, and potential connections with other fields.
* OUTCOME: Each task should task should provide modified dataframe that can be used by the next step.
* VALIDATION: If the replanner/validator is not satisfied with the last plan/result, it will send it back for replanning.
* MUST: Investigate and handle missing values, ensuring data cleanup is mentioned where necessary.
* FINAL: Final step should ALWAYS be writing the output dataframe into a data file and persist in the working directory.

**Hints:**
* if preparation not possible or needed, then respond accordingly
* always remember, data wrangling includes discovery, structuring, cleaning, enriching and transforming data
* never apply any direct transformation to the source file or any file which you have not created
* in case of xlsx, treat every sheet as a separate table

=====
**Example Analysis Plan:**

Question - ```Provide me a code and final data, where you can add more categorization to the data from the source table: durobumps_load_sheet_excel_05_24_1_product_data
Consider a scenario where for Product Name, example: `Durobumps Front Premium off road Bump Stops for 98-21 Lexus LX, 00-06 Tundra, 00-23 Sequoia, 98-21 Land Cruiser. No Lift Required - DBF17T`
it can be split into multiple years/model/note for the existing row as
1998     Lexus   LX           Note:No Lift Required
1999     Lexus   LX           Note:No Lift Required
2000     Lexus   LX           Note:No Lift Required
. . .
2005     Tundra                Note:No Lift Required
. . .
2020     Land Cruiser    Note:No Lift Required

so it would have multiple versions of each existing row with new columns as above years/model/note as per the product name```
Plan -
* Step 1: Extract the Year Ranges:
- Identify year ranges in the `Product_Name` column (e.g., `"98-21"` means model years from 1998 to 2021).
- Convert two-digit years into full four-digit years based on context (`98 → 1998`, `21 → 2021`).
* Step 2: Extract Vehicle Make and Model:
- Identify vehicle makes and models in the `Product_Name` column (`Lexus`, `Toyota`, `Tundra`, `Sequoia`, etc.).
- Assign the correct make and model values to each row.
* Step 3: Extract Additional Notes:
- Identify any additional information, such as `"No Lift Required"`, and store it as a separate column.
* Step 4: Expand the Data:
- For each product, generate multiple rows covering each year in the identified range.
- Maintain the original `Product_Name` field for reference.
* Step 5: Validate generated code:
- Validate on rows count.
- Validate on columns count.
- Validate on data quality and accuracy.
- The transformed data should be stored in a new sheet with the additional following format:
+ `Part_Number` (String)
+ `Year` (String)
+ `Make` (String)
+ `Model` (String)
+ `Brand` (String)
+ `UPC_TIN_GTIN` (String)
+ `Product_Name` (String)
+ `eCommerce` (String)
+ `MSRP` (Float)
+ `MAP` (Float)
+ `Marketing_Description` (String)
+ `Features_Benefits` (String)
+ `Whats_Included` (String)
+ `Vehicle_Applications` (String)
+ `Lift_Height_Required` (String)
+ `Deflection_Compression` (String)
+ `Disclaimer` (String)
+ `Install_Instructions_Link` (String)
+ `Install_Instructions` (String)
+ `Color` (String)
+ `Main_Photo` (String)
+ `Bottom_Photo` (String)
+ `Top_Photo` (String)
+ `Installed_Photo` (String)
+ `Feature_Video` (String)
+ `Shipping_Length_in` (Float)
+ `Shipping_Width_in` (Float)
+ `Shipping_Height_in` (Float)
+ `Shipping_Weight_oz` (Float)
+ `Note` (String)

With such additional structure:
| Year | Make   | Model      | Note               | Product_Name  | ...
|------|--------|-----------|--------------------|---------------| ...
| 1998 | Lexus  | LX        | No Lift Required  | Durobumps...  | ...
| 1999 | Lexus  | LX        | No Lift Required  | Durobumps...  | ...
| 2000 | Toyota | Tundra    | No Lift Required  | Durobumps...  | ...
| ...  | ...    | ...       | ...                | ...           | …

* Step 7: Persist final result:
- Write a Python Code to create the transformed table.
- persist the python code and final resultant dataframe into data sheet, in working-directory. Share the file location.

* . . . <more steps to ensure insights into the dataset for preprocessing and transformation decisions>

===
Update your plan accordingly.

    """,
            ),
            ("placeholder", "{messages}"),
        ]
    )
    planner_chain = planner_prompt | trimmer | llm.with_structured_output(Act)

    replanner_prompt = ChatPromptTemplate.from_template(
        """As a world-class Data analyst/engineer and BI specialist with expertise in e-commerce data, for the given objective, validate the response from the previous step.
The goal of the tasks/steps is to gain insights into the dataset for making preprocessing and transformation decisions. Provide a thorough validations of the tasks and the dataset.
Execute each step, validate the response of the last run, and provide insight into modifying the steps as needed to proceed to the next task.
Do not include any superfluous feedback. Ensure the final step yields the complete answer. Ensure each step has all the necessary details and avoid skipping any essential information.
The goal of the tasks/steps is to modify the dataset to make successful transformation/harmonization of the passed dataset for agreed upon outcome.
This plan should cover individual tasks strictly within the scope of data analysis, ensuring that, if executed correctly, they yield a thorough transformation of the dataset and final mapping.
Ensure each step is self-contained with all necessary information and avoid skipping steps.

**Planner Notes:**
* Make sure to expand user's original question for a detailed planning.
* Include analysis action hints for analysts/execution to refer to; be as detailed as possible.
* The overall goal is strictly data transformation/harmonization for the given question and context.
* Make sure to consider all dataframes for analysis, as applicable.
* Make sure to consider any preprocessing/enriching/merging/cleaning of the data for each analysis, as required.
* MUST: Conduct (statistical) visualization analysis for each step, if applicable. Extract learnings from every analysis.
* MUST: Summarize and describe every field, including data types, allowed values, and potential connections with other fields.
* OUTCOME: Each task should task should provide modified dataframe that can be used by the next step.
* VALIDATION: If the replanner/validator is not satisfied with the last plan/result, it will send it back for replanning.
* MUST: Investigate and handle missing values, ensuring data cleanup is mentioned where necessary.
* FINAL: Final step should ALWAYS be writing the output dataframe into a data file and persist in the working directory.

**Hints:**
* if preparation not possible or needed, then respond accordingly
* always remember, data wrangling includes discovery, structuring, cleaning, enriching and transforming data
* never apply any direct transformation to the source file or any file which you have not created
* in case of xlsx, treat every sheet as a separate table

=====
**Context**
Your objective, for feature engineering, was this:
{question}

Your current plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Extracted Schema:
{schema}

Validate the plan/code accordingly. If the last run RESPONSE is correct/validated and no more iterations are needed and
you can return last output to the user, for addressing the original question. Include plan summary, expected outcome,
validation criteria and success rate.
Otherwise, include a suffix RETRY in the response. Explicitly mention each step, add approved to steps otherwise feedback."""
    )

    replanner_chain = replanner_prompt | trimmer | reasoning_llm.with_structured_output(Act)

    synthesize_prompt = ChatPromptTemplate.from_template(
        """As a world-class Data analyst/engineer and BI specialist with expertise in e-commerce data, for the given objective, validate and consolidate all the analysis results the previous planning/execution.


Ensure your response:
- Removes ambiguity/generalization and provides a specific, data-driven answer.
- Clearly states if information is not available or cannot be directly deduced from the context.
- Outputs the response in valid JSON format:

    {{
        "planning": Final plan executed.
        "code": Code executed.
        "output": [
            {{
                "file_path": file path of the output file.
                "success_rate": output quality/validation check.
                "validation": pass or fail.
            }},
            ...
        ]
        "result": RETRY or DONE.,
    }}

**Final Plan:**
{plan}

**Execution Outcome:**
{data_summary}

**Note:**
* the overall goal is code and output, for the original question and context shared by user

=====
**Context**
Your objective was this:
{question}

Planning Validation Final Response:
{response}

If any required information is missing from the context or there is ambiguity that needs to be addressed for a successful response, clearly state this in your feedback."""
    )

    synthesize_chain = synthesize_prompt | trimmer | reasoning_llm | StrOutputParser()

    async def rag_store(query: str):
        inputs = {
            "question": query,
            "breakdown": False,
            "load_data": True,  # defaults to data validation rn
            "concise": True
        }
        config = {
            "recursion_limit": 20,
            "configurable": {
                "thread_id": "chicory-ui-discovery",
                "thread_ts": datetime.now(UTC).isoformat(),
                "client": "brewmind",
                "user": "user",
                "project": "PDM",
            }
        }
        response = ""
        if rag_app:
            async for event in rag_app.astream(
                    inputs, config=config):
                for key, value in event.items():
                    pprint(f"Node '{key}':")
                    pprint(f"{value}'")
            if 'generation' in value:
                response = value["generation"]
            elif 'data_summary' in value:
                response = value["data_summary"]
            else:
                response = value
        return {"response": response}


    async def rag_store_tool(query: str):
        return await rag_store(query)

    python_repl = PythonREPL()
    tools = [
        rag_store_tool,
        Tool(
            name="rag_store_tool",
            description="An inference tool based on adaptive-hybrid-rag llm. Use this to extract any subject information/context for understanding the question or its components. It can provide you background context, insight about data models and also BI questions.",
            func=rag_store_tool,
        ),
        Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=python_repl.run,
        )
    ]

    def handle_agent_error(error):
        if isinstance(error, str):
            return {"error": error}
        return {"error": str(error)}

    def load_schema(work_dir: str) -> str:
        """
        Load the schema from the given work directory path, for given dataset to analyze.
        :param work_dir:
        :return: schema_content_str
        """
        schema = ""
        schema_path = os.path.join(work_dir, 'schema.json')
        with open(schema_path, 'r') as f:
            schema = f.read()
        return schema

    def read_file(path):
        if path.endswith('.csv'):
            return pd.read_csv(path)
        elif path.endswith(('.xls', '.xlsx')):
            return pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported file format: {path}")

    async def execute_step(state: PlanExecute):
        query = state["question"]
        plan = state["plan"]
        response = state["response"]
        schema = state["schema"]
        work_dir = project_config["work_directory"]
        df = [read_file(path) for path in state["data"]]
        task_formatted = f"""You are tasked with executing the step and transformation of the input dataset for: \n
**Plan:**
{plan}

**Plan Summary:**
{response}

Note:
* The goal is to write a python transformation code and successfully execute, with overall objective: {query}.
* Ensure the transformation & validation covers the entire dataset, not just a sample.
* Make sure to consider all dataframes for analysis, as applicable.
* Make sure to consider any preprocessing/enriching/merging/cleaning of the data for each analysis, as required.
* OUTCOME: Each task should task should provide modified dataframe that can be used by the next step.
* MUST: Validate the outcome before sharing the final report.
* HINT: The data is in-memory as a DataFrame and should not be read from any file.
* HINT: If any syntax errors occur, modify and re-execute the code to ensure correctness.
* FINAL: Final step should ALWAYS be writing the output dataframe into a data file and persist in the working directory.

Respond with:
* code executed
* final execution result - output data snippet
* summary of the outcome - statistics about output data
* file path of the output file.

=====
Schema for input data:
{schema}
"""

        prefix = """
        import pandas as pd
        import seaborn as sns
        import matplotlib.pyplot as plt

        # You can add any other setup code or hints here
        # HINT: The data is in-memory as a DataFrame and should not be read from any file.
        # Look for the correct dataframe variable `df1`

        """
        agent_max_iterations = 30
        callback_manager = None

        import matplotlib
        import matplotlib.pyplot as plt
        if file_loader:
            matplotlib.use('Agg')  # Set the backend to non-interactive Agg
            file_log_handler = FileLoggingCallbackHandler(os.path.join(work_dir, "output.txt"), work_dir)
            callback_manager = CallbackManager([file_log_handler])
            # Override plt.show() to use our custom method
            plt.show = lambda: file_log_handler.handle_plt_show()
        if response_container:
            matplotlib.use('Agg')  # Set the backend to non-interactive Agg
            streamlit_handler = StreamlitCallbackHandler(response_container)
            callback_manager = CallbackManager([streamlit_handler])
            # Override plt.show() to use our custom method
            plt.show = lambda: StreamlitCallbackHandler(response_container).handle_plt_show()
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
            extra_tools=tools,
            prefix=prefix,
            callback_manager=callback_manager,
        )
        try:
            result = await pandas_agent.ainvoke(task_formatted)
        except Exception as e:
            result = handle_agent_error(e)
        return {
            "data_summary": result["output"] if "output" in result else result,
        }

    async def plan_step(state: PlanExecute):
        query = state["question"]
        work_dir = project_config["work_directory"]
        schema = load_schema(work_dir)
        if "response" in schema:
            response = state["response"]
        else:
            response = ""

        if "plan" in schema:
            prev_plan = state["plan"]
        else:
            prev_plan = ""

        planner_input = {
            "messages": [
                ("user", query),  # User's message or query
                ("assistant", f"""\nExtracted Schema:\n\n {schema}"""),
                ("assistant", f"""\nPrevious plan + feedback:\n\n {prev_plan} : {response}"""),
            ],
        }

        result = { "schema": schema }

        try:
            output = await planner_chain.ainvoke(planner_input)
            if isinstance(output.action, Response):
                result["plan"] = output.action.response
        except Exception as e:
            output = handle_agent_error(e)
        result["plan"] = output

        if response and prev_plan:
            result["past_steps"].append((prev_plan, response))
        return result

    async def replan_step(state: PlanExecute):
        try:
            output = await replanner_chain.ainvoke(state)
            if isinstance(output.action, Response):
                return {"response": output.action.response}
        except Exception as e:
            output = handle_agent_error(e)
        return {"response": output}

    async def finalize(state):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        print("---SYNTHESIZE---")
        final_response = synthesize_chain.invoke(state)
        return {"data_summary": final_response}

    def wait_for_user_feedback(state: PlanExecute):
        """
        This function pauses execution and waits for user feedback.
        User input should be set in the state by an external interface.
        """
        print("Waiting for user feedback...")

        # Simulate waiting for external input (polling or event-driven approach)
        while "user_approved" not in state:
            time.sleep(2)  # Polling interval
            print("Still waiting for user feedback...")

        print(f"User feedback received: {'Approved' if state['user_approved'] else 'Rejected'}")
        return state  # Return updated state with user response

    def should_proceed_with_plan(state: PlanExecute):
        if state.get("user_approved", False):  # User confirmed the plan
            return "executor"
        else:  # User wants to modify the plan
            return "replanner"

    def should_replan(state: PlanExecute):
        if "response" in state and state["response"]:
            return "planner"
        else:
            return "coder"

    workflow = StateGraph(PlanExecute)

    # Add the plan node
    workflow.add_node("planner", plan_step)

    # Add the pause_for_review node
    # workflow.add_node("pause_for_review", wait_for_user_feedback)

    # Add a replan node
    workflow.add_node("replanner", replan_step)

    workflow.add_node("coder", plan_step)

    workflow.add_node("validator", replan_step)

    # Add the execution step
    workflow.add_node("executor", execute_step)

    # Add the plan node
    workflow.add_node("synthesize", finalize)

    workflow.add_edge(START, "planner")

    # From plan we go to agent
    workflow.add_edge("planner", "replanner")

    workflow.add_conditional_edges(
        "replanner",
        # Next, we pass in the function that will determine which node is called next.
        should_replan,
        ["planner", "executor"],
    )

    # From code we go to validator
    workflow.add_edge("executor", "synthesize")

    workflow.add_edge("synthesize", END)

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    app = workflow.compile(checkpointer=memory)
    # app = workflow.compile()

    return app


async def run(question: str, data, app):
    # Run
    initial_state = {
        "question": question,
        "data": data,
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
        print(e)
        return f"Try again. {str(e)}"

if __name__ == "__main__":
    from services.utils.schema_selector import generate_schema

    project = "PDM"
    # Get the dataset folder path from the session state
    dataset_folder = "/Users/sarkarsaurabh.27/Documents/Projects/Customer/PDM/data"
    # Recursively collect all file paths in the dataset folder and its subdirectories
    uploaded_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(dataset_folder)
        for file in files
    ]

    project_config = get_project_config(project)
    app = initialize_harmonization_workflow_agent(project="PDM")
    human_message = """Provide me a code and final data, where you can add more categorization to the data from the source table: durobumps_load_sheet_excel_05_24_1_product_data
    Consider a scenario where for Product Name, example: `Durobumps Front Premium off road Bump Stops for 98-21 Lexus LX, 00-06 Tundra, 00-23 Sequoia, 98-21 Land Cruiser. No Lift Required - DBF17T`
    it can be split into multiple years/model/note for the existing row as
    1998     Lexus   LX           Note:No Lift Required
    1999     Lexus   LX           Note:No Lift Required
    2000     Lexus   LX           Note:No Lift Required
    . . .
    2005     Tundra                Note:No Lift Required
    . . .
    2020     Land Cruiser    Note:No Lift Required

    so it would have multiple versions of each existing row with new columns as above years/model/note as per the product name"""

    generate_schema(dataset_folder, project.lower(),
                    project_config["work_directory"], metadata_flag=True,
                    feature_flag=False, query=human_message)

    asyncio.run(run(human_message, uploaded_files, app))
    pprint("DONE")
