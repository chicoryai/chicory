import operator
import operator
import os
from datetime import datetime
import streamlit as st
import pandas as pd

from langchain.agents import AgentType
from typing import TypedDict, List, Annotated, Tuple, Union
from langchain.globals import set_llm_cache
from langchain_core.caches import InMemoryCache
from langchain_core.callbacks import CallbackManager, BaseCallbackHandler
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.agents import create_pandas_dataframe_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import START
from matplotlib import pyplot as plt
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langchain_core.tools import tool

import sys
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List, Union
from langchain.schema import AgentAction, AgentFinish
from services.workflows.data_exploration.feature_brew.features_hints import load_prompts

class PlanExecute(TypedDict):
    question: str
    data: List[pd.DataFrame]
    plan: List[str]
    additional_context: str
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    work_dir: str
    schema: str
    metadata: str
    data_analysis: dict
    labeling: dict
    wrangling: dict
    feature_engineering: dict
    feature_num: int
    hints: str

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
        plt.savefig(filepath, bbox_inches='tight')
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
        try: 
            plt.savefig(filename, bbox_inches='tight')
            plt.close()  # Close the figure to free up memory
            self.container.write(f"Figure {self.figure_counter} generated:")
            self.container.image(filename)
        except Exception as e:
            self.container.error(f"Error displaying plot: {e}")
        
        os.remove(filename)  # Remove the file after displaying


def initialize_feature_brew_workflow_agent(user = None, project = None, response_container = None, file_loader = False):    # Initialize OpenAI components
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    llm_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    reasoning_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chat_llm = ChatOpenAI(model="chatgpt-4o-latest", temperature=0)

    # session = boto3.Session(region_name='us-west-2')  # Replace with your AWS region
    # bedrock_runtime = session.client(service_name='bedrock-runtime')
    # sonnet_llm = ChatBedrock(
    #     model_id="anthropic.claude-3-sonnet-20241022-v2:0",
    #     client=bedrock_runtime,
    #     model_kwargs={
    #         "temperature": 0.0,
    #         "max_tokens": 127000
    #     }
    # )  

    project = (project or os.getenv("PROJECT", "")).strip().lower()
    PROMPTS = load_prompts(project)

    # DOMAIN_HINTS = PROMPTS[f"{domain}_domain_hints"]
    DOMAIN_HINTS = PROMPTS["domain_hints"]
    FEATURE_HINTS = PROMPTS["feature_hints"]

    trimmer = trim_messages(
        max_tokens=124000,
        strategy="last",
        token_counter=llm,
        include_system=True,
    )

    planner_prompt_template = PROMPTS["planner_prompt_template"]
    planner_prompt = ChatPromptTemplate.from_messages(
        [
            ( "system", planner_prompt_template),
            ("placeholder", "{messages}"),
        ]
    )   
    planner_chain = planner_prompt | trimmer | llm.with_structured_output(Plan)

    replanner_prompt_template = PROMPTS["replanner_prompt_template"]
    replanner_prompt = ChatPromptTemplate.from_template(
        replanner_prompt_template
    )
    replanner_chain = replanner_prompt | trimmer | llm.with_structured_output(Act)

    synthesize_prompt_template = PROMPTS["synthesize_prompt_template"]
    synthesize_prompt = ChatPromptTemplate.from_template(
        synthesize_prompt_template
    )
    synthesize_chain = synthesize_prompt | trimmer | chat_llm | StrOutputParser()

   
    def handle_agent_error(error):
        if isinstance(error, str):
            return {"error": error}
        return {"error": str(error)}

    def load_metadata(work_dir: str) -> str:
        """
        Load the passed metadata from the given work directory path, for given dataset to analyze.
        :param work_dir:
        :return: metadata_content_str
        """
        metadata = ""
        if project == "rice":
            metadata_path = os.path.join(work_dir, 'metadata.json')
            with open(metadata_path, 'r') as f:
                metadata = f.read()

        elif project == "genentech":
            metadata_path = os.path.join(work_dir, 'metadata.xlsx')
            df = pd.read_excel(metadata_path, sheet_name=None)  # Read all sheets
            for sheet_name, data in df.items():
                metadata += f"Sheet: {sheet_name}\n"
                metadata += data.to_csv(index=False)

        return metadata


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

    async def execute_step(state: PlanExecute):
        query = state["question"]
        plan = state["plan"]
        work_dir = state["work_dir"]
        project = (state.get("project") or os.getenv("PROJECT", "")).strip().lower()
        metadata = state.get("metadata", "") # metadata exists for genentech,use it here, for rice metadata is empty string
        if project == "rice":
            df = [pd.read_csv(path, nrows=20) for path in state["data"]]
        else: # other projects
            df = [pd.read_csv(path) for path in state["data"]]

        task = plan[0]
        task_formatted = f"""You are tasked with executing the step and sharing the analysis report for: {task}.

Note:
* The goal is to perform analysis that supports the feature engineering objective: {query}.
* Ensure the analysis samples cover balanced pattern for all the dataframes.
* Make sure to consider any preprocessing/enriching/merging/cleaning of the data for each analysis, as required.
* OUTCOME: Each task should provide insights that can be used for feature engineering.
* MUST: Validate the analysis before sharing the final report.
* HINT: The data is in-memory as a DataFrame and should not be read from any file.
* HINT: If any syntax errors occur, modify and re-execute the code to ensure correctness.
* The list of DataFrames is called `df`.
* Access them like: df[0], df[1], df[2], etc.
* HINT: Do not use df0, df1... Instead, use df[i] indexing for the list of DataFrames.

=====
If metadata is available, include that for context, else do not include: 
{metadata}
"""

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
        callback_manager = None

        import matplotlib
        import matplotlib.pyplot as plt

        if file_loader:  # file_loader = True for plots
            matplotlib.use('Agg')  # Set the backend to non-interactive Agg
            file_log_handler = FileLoggingCallbackHandler(os.path.join(work_dir, "output.txt"), work_dir)
            callback_manager = CallbackManager([file_log_handler])
            # Override plt.show() to use our custom method
            #plt.show = lambda: file_log_handler.handle_plt_show()
            plt.show = file_log_handler.handle_plt_show
        if response_container:
            matplotlib.use('Agg')  # Set the backend to non-interactive Agg
            streamlit_handler = StreamlitCallbackHandler(response_container)
            callback_manager = CallbackManager([streamlit_handler])
            # Override plt.show() to use our custom method
            plt.show = lambda: streamlit_handler.handle_plt_show()
            # streamlit_handler = StreamlitCallbackHandler(response_container)
            # plt.show = streamlit_handler.handle_plt_show()

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
            prefix=prefix,
            callback_manager=callback_manager,
        )
        result = None
        try:
            result = await pandas_agent.ainvoke(task_formatted)
            print("LLM Query Executed:", result.get("intermediate_steps", []))
        except Exception as e:
            result = handle_agent_error(e)

        if plt.get_fignums():
                plt.show()
        
        ##  To keep under token limit
        # max_past_steps = 3  
        # new_step = (task, result["output"] if "output" in result else result)
        # past_steps = state.get("past_steps", [])
        # past_steps.append(new_step)
        #return {past_steps": past_steps[-max_past_steps:],} 
        return {
            "past_steps": [(task, result["output"] if "output" in result else result)],
        }
    

    async def plan_step(state: PlanExecute):
        query = state["question"]
        work_dir = state["work_dir"]
        hints =  DOMAIN_HINTS + "\n\n" + FEATURE_HINTS
        additional_context = state["additional_context"]
        schema = load_schema(work_dir)
        feature_num = state["feature_num"]
        metadata = ""
        if project == "genentech":
            metadata = load_metadata(work_dir)
        
        messages = [
            ("user", query),  # User's message or query
            ("user", f"""\nAdditional Context:\n\n {additional_context}""")]
        
        if metadata:
            messages.append(("assistant", f"""\nMetadata:\n\n {metadata}"""))   

        messages.extend([
            ("assistant", f"""\nExtracted Schema:\n\n {schema}"""),
            ("assistant", f"""\nDomain Hints:\n\n {hints}"""),
            ("assistant", f"""\nCandidate Features:\n\n Consider candidate features which are feasible, also must not be fewer than {feature_num}.""")
        ])

        plan = await planner_chain.ainvoke({"messages": messages})
        response = {"plan": plan.steps, "schema": schema, "hints": hints}
        
        if metadata:
            response["metadata"] = metadata

        return response
    

    async def replan_step(state: PlanExecute):
        try:
            output = await replanner_chain.ainvoke(state)
        except Exception as e:
            output = handle_agent_error(e)
            return {"response": output}

        if isinstance(output.action, Response):
            return {"response": output.action.response}
        else:
            return {"plan": output.action.steps}

    async def label_step(state: PlanExecute):
        try:
            result = await label_chain.ainvoke(state)
        except Exception as e:
            result = handle_agent_error(e)

        return {"labeling": result}

    async def wrangle_step(state: PlanExecute):
        try:
            result = await wrangling_chain.ainvoke(state)
        except Exception as e:
            result = handle_agent_error(e)

        return {"wrangling": result}

    async def feature_engg_step(state: PlanExecute):
        try:
            result = await feature_engg_chain.ainvoke(state)
        except Exception as e:
            result = handle_agent_error(e)

        return {"feature_engineering": result}

    async def final_step(state: PlanExecute):
        try:
            result = await scientist_chain.ainvoke(state)
        except Exception as e:
            result = handle_agent_error(e)

        return {"response": result}

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
        return {"data_analysis": final_response}

    def should_end(state: PlanExecute):
        if "response" in state and state["response"]:
            return "synthesize"
        else:
            return "analyst"

     
    label_prompt_template = PROMPTS["label_prompt_template"]
    label_prompt = ChatPromptTemplate.from_template(
        label_prompt_template
    )
    label_chain = label_prompt | trimmer | chat_llm | StrOutputParser()

    wrangling_prompt_template = PROMPTS["wrangling_prompt_template"]
    wrangling_prompt = ChatPromptTemplate.from_template(
        wrangling_prompt_template
    )
    wrangling_chain = wrangling_prompt | trimmer | chat_llm | StrOutputParser()

    feature_engg_prompt_template = PROMPTS["feature_engg_prompt_template"]
    feature_engg_prompt = ChatPromptTemplate.from_template(
        feature_engg_prompt_template
    )
    feature_engg_chain = feature_engg_prompt | trimmer | chat_llm | StrOutputParser()

    scientist_prompt_template = PROMPTS["scientist_prompt_template"]
    scientist_prompt = ChatPromptTemplate.from_template(
        scientist_prompt_template
    )
    scientist_chain = scientist_prompt | trimmer | chat_llm | StrOutputParser()

    
    workflow = StateGraph(PlanExecute)

    # Add the plan node
    workflow.add_node("researcher", plan_step)
    # Add the execution step
    workflow.add_node("analyst", execute_step)
    # Add a replan node
    workflow.add_node("research_replanner", replan_step)
    workflow.add_node("labeler", label_step)
    workflow.add_node("wrangler", wrangle_step)
    workflow.add_node("feature_engineer", feature_engg_step)
    workflow.add_node("scientist", final_step)
    workflow.add_node("synthesize", finalize)
 
    workflow.add_edge(START, "researcher")
    # From plan we go to agent
    workflow.add_edge("researcher", "analyst")
    # From agent, we replan
    workflow.add_edge("analyst", "research_replanner")
    workflow.add_conditional_edges(
        "research_replanner",
        # Next, we pass in the function that will determine which node is called next.
        should_end,
        ["analyst", "synthesize"],
    )

    # workflow.add_node("supervisor", supervisor_agent)

    workflow.add_edge("synthesize", "labeler")
    workflow.add_edge("labeler", "wrangler")
    workflow.add_edge("wrangler", "feature_engineer")
    workflow.add_edge("feature_engineer", "scientist")
    workflow.add_edge("scientist", END)
    print("All workflow added successfully")

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    app = workflow.compile(checkpointer=memory)
    # app = workflow.compile()

    return app