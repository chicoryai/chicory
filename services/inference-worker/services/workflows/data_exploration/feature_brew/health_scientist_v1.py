import pandas as pd
import os

from typing import Annotated, TypedDict, List, Union
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_experimental.tools import PythonAstREPLTool


class State(TypedDict):
    messages: Annotated[List[Union[HumanMessage, AIMessage]], "The conversation history"]
    data: Annotated[List[pd.DataFrame], "List of dataframes"]
    label_column: Annotated[str, "Name of the label column"]
    has_label: Annotated[bool, "Whether data has the label column"]
    label_instructions: Annotated[str, "Instructions for computing the label"]
    work_dir: Annotated[str, "Working directory for output"]


model = os.getenv('MODEL_NAME')
llm = ChatOpenAI(temperature=0, model=model)
python_repl = PythonAstREPLTool()


def clean_merge_code(code):
    """
    Clean the merge code by removing unwanted elements.
    """
    cleaned_lines = [line for line in code.split('\n') if '```' not in line and 'python' not in line.lower()]
    return '\n'.join(cleaned_lines)

def data_loader(state):
    messages = state["messages"]
    data = state["data"]
    label_column = state["label_column"]

    merge_prompt = f"""
    Analyze the following datasets and provide Python code to merge them:
    {[df.head().to_string() for df in data]}

    Please provide only the Python code to merge the datasets, no explanations.
    Use pandas and assume the datasets are in a list called 'data_list'.
    The final merged dataframe should be called 'merged_data'.
    Example:
    merged_data = pd.concat(data_list, ignore_index=True)
    # or
    merged_data = data_list.merge(data_list, on='common_column', how='outer')
    """

    response = llm.invoke([HumanMessage(content=merge_prompt)])

    merge_code = response.content
    print("LLM-generated merge code:")

    # Clean the merge code
    cleaned_merge_code = clean_merge_code(merge_code)
    print("Cleaned merge code:")
    final_code = f"import numpy as np\n\ndata_list = {[df.to_dict() for df in data]}\n{cleaned_merge_code}\nmerged_data.to_dict()"

    try:
        # Try to execute the cleaned LLM-generated code
        merged_data = python_repl.run(final_code)
        merged_df = pd.DataFrame(eval(merged_data))
    except Exception as e:
        print(f"Error executing cleaned LLM-generated code: {str(e)}")
        print("Falling back to simple concatenation merge.")
        # Fallback: simple concatenation of all dataframes
        merged_df = pd.concat(data, ignore_index=True)

    has_label = label_column in merged_df.columns

    return {
        "messages": messages + [
            AIMessage(content=f"Data merged using the following cleaned code:\n{cleaned_merge_code}")],
        "data": [merged_df],
        "label_column": label_column,
        "has_label": has_label,
        "label_instructions": state["label_instructions"],
        "work_dir": state["work_dir"]
    }


async def label_creator(state):
    messages = state["messages"]
    data = state["data"][0]
    label_column = state["label_column"]
    label_instructions = state["label_instructions"]

    if state["has_label"]:
        return state

    response = llm.invoke(
        messages + [HumanMessage(
            content=f"Create a new '{label_column}' column based on these instructions: {label_instructions}\nCurrent data:\n{data.head().to_string()}")]
    )

    labeling_code = response.content
    labeled_data = python_repl.run(f"data = {data.to_dict()}\n{labeling_code}\ndata")
    labeled_df = pd.DataFrame(eval(labeled_data))

    return {
        "messages": messages + [AIMessage(content=f"Label column '{label_column}' created:\n{labeling_code}")],
        "data": [labeled_df],
        "label_column": label_column,
        "has_label": True,
        "label_instructions": label_instructions,
        "work_dir": state["work_dir"]
    }


async def data_analyst(state):
    messages = state["messages"]
    data = state["data"][0]

    response = llm.invoke(
        messages + [
            HumanMessage(content=f"Analyze the following data and suggest next steps:\n{data.head().to_string()}")]
    )

    return {
        "messages": messages + [AIMessage(content=response.content)],
        "data": [data],
        "label_column": state["label_column"],
        "has_label": state["has_label"],
        "label_instructions": state["label_instructions"],
        "work_dir": state["work_dir"]
    }


async def data_cleaner(state):
    messages = state["messages"]
    data = state["data"][0]

    response = llm.invoke(
        messages + [HumanMessage(content="Suggest and implement data cleaning steps.")]
    )

    cleaning_code = response.content
    cleaned_data = python_repl.run(f"data = {data.to_dict()}\n{cleaning_code}\ndata")

    return {
        "messages": messages + [AIMessage(content=f"Cleaning steps executed:\n{cleaning_code}")],
        "data": [pd.DataFrame(eval(cleaned_data))],
        "label_column": state["label_column"],
        "has_label": state["has_label"],
        "label_instructions": state["label_instructions"],
        "work_dir": state["work_dir"]
    }


async def feature_engineer(state):
    messages = state["messages"]
    data = state["data"][0]

    response = llm.invoke(
        messages + [HumanMessage(content="Suggest and implement feature engineering steps.")]
    )

    engineering_code = response.content
    engineered_data = python_repl.run(f"data = {data.to_dict()}\n{engineering_code}\ndata")

    return {
        "messages": messages + [AIMessage(content=f"Feature engineering steps executed:\n{engineering_code}")],
        "data": [pd.DataFrame(eval(engineered_data))],
        "label_column": state["label_column"],
        "has_label": state["has_label"],
        "label_instructions": state["label_instructions"],
        "work_dir": state["work_dir"]
    }


async def summarizer(state):
    messages = state["messages"]
    data = state["data"][0]
    work_dir = state["work_dir"]

    summary = llm.invoke(
        messages + [HumanMessage(content=f"Summarize the current state of the data:\n{data.head().to_string()}")]
    )

    output_path = os.path.join(work_dir, "processed_data.csv")
    data.to_csv(output_path, index=False)

    return {
        "messages": messages + [AIMessage(content=f"{summary.content}\n\nProcessed data saved to {output_path}")],
        "data": [data],
        "label_column": state["label_column"],
        "has_label": state["has_label"],
        "label_instructions": state["label_instructions"],
        "work_dir": work_dir
    }


# Define the conditional edge function
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1].content.lower()

    if "task completed" in last_message or "analysis finished" in last_message:
        return "summarizer"
    elif not state["has_label"]:
        return "label_creator"
    elif "need cleaning" in last_message:
        return "data_cleaner"
    elif "feature engineering required" in last_message:
        return "feature_engineer"
    else:
        return "data_analyst"


workflow = StateGraph(State)

workflow.add_node("data_loader", data_loader)
workflow.add_node("label_creator", label_creator)
workflow.add_node("data_analyst", data_analyst)
workflow.add_node("data_cleaner", data_cleaner)
workflow.add_node("feature_engineer", feature_engineer)
workflow.add_node("summarizer", summarizer)

workflow.set_entry_point("data_loader")

# Add conditional edges
workflow.add_conditional_edges(
    "data_loader",
    should_continue,
    {
        "label_creator": "label_creator",
        "data_analyst": "data_analyst",
        "summarizer": "summarizer"
    }
)

workflow.add_conditional_edges(
    "label_creator",
    should_continue,
    {
        "data_analyst": "data_analyst",
        "label_creator": "label_creator",
        "summarizer": "summarizer"
    }
)

workflow.add_conditional_edges(
    "data_analyst",
    should_continue,
    {
        "data_analyst": "data_analyst",
        "data_cleaner": "data_cleaner",
        "feature_engineer": "feature_engineer",
        "summarizer": "summarizer"
    }
)

workflow.add_edge("data_cleaner", "data_analyst")
workflow.add_edge("feature_engineer", "data_analyst")
workflow.add_edge("summarizer", END)

data_wrangler_app = workflow.compile()
