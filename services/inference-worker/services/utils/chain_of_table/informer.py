import os

import pandas as pd
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel

from operations import simple_query
from utils.chain import dynamic_chain_exec_one_sample, get_table_info, get_table_log
from utils.llm import ChatGPT
from utils.load_data import wrap_input_for_demo


MODEL = os.getenv("MODEL", 'gpt-4o')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def tab_file_to_array(file_path):
    # Determine the file extension
    _, file_extension = os.path.splitext(file_path)

    # Read the file based on its extension
    if file_extension.lower() == '.xlsx' or file_extension.lower() == '.xls':
        # Read Excel file
        df = pd.read_excel(file_path)
    elif file_extension.lower() == '.csv':
        # Read CSV file
        df = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file format. Only .xls, .xlsx and .csv are supported.")

    # Convert DataFrame to a list of lists (array of rows)
    table_text = [df.columns.tolist()] + df.values.tolist()
    return table_text


def get_filename_without_extension(file_path):
    # Extract the base name from the path
    base_name = os.path.basename(file_path)
    # Split the base name into name and extension, and return the name part
    file_name = os.path.splitext(base_name)[0]
    return file_name


# Define the input schema
class GetTableInsightInput(BaseModel):
    file_path: str
    question: str

@tool
def get_table_insight(input: str) -> str:
    """
    Get the result for an insight question about the passed tabular dataset file_path and question, wrapped in dict.
        Returns string result.
    :param input: String input with full/correct 'file_path' and 'question' separated by a colon.
    For example:
    "/Users/sarkarsaurabh.27/Documents/Projects/chicoryai/data/dh/pdm/DuroBumps Load Sheet Excel 05.24.xlsx:What
    are the columns in this dataset?"

    :usage:
    input_arr = input.split(":")
    file_path = input_arr[0]
    question = input_arr[1]

    :return: String result for any insight question asked about the passed table file
    """
    input_arr = input.split(":")
    file_path = input_arr[0]
    question = input_arr[1]
    table_caption = get_filename_without_extension(file_path)
    try:
        table_text = tab_file_to_array(file_path)
    except Exception as e:
        return f"Fetching failed. {e}"

    try:
        gpt_llm = ChatGPT(
            model_name=MODEL,
            key=OPENAI_API_KEY
        )

        demo_sample = wrap_input_for_demo(
            statement=question, table_caption=table_caption, table_text=table_text
        )
        proc_sample, dynamic_chain_log = dynamic_chain_exec_one_sample(
            sample=demo_sample, llm=gpt_llm
        )
        output_sample = simple_query(
            sample=proc_sample,
            table_info=get_table_info(proc_sample),
            llm=gpt_llm,
            use_demo=True,
            llm_options=gpt_llm.get_model_options(
                temperature=0.0, per_example_max_decode_steps=200, per_example_top_p=1.0
            ),
            insight_use=True,
        )
        cotable_log = get_table_log(output_sample)

        # print(f'Statements: {output_sample["statement"]}\n')
        # print(f'Table: {output_sample["table_caption"]}')
        # print(f"{pd.DataFrame(table_text[1:], columns=table_text[0])}\n")
        for table_info in cotable_log:
            if table_info["act_chain"]:
                table_text = table_info["table_text"]
                table_action = table_info["act_chain"][-1]
                if "skip" in table_action:
                    continue
                if "query" in table_action:
                    result = table_info["cotable_result"]
                    print(f"-> {table_action}\n RESULT: {result}\n")
                else:
                    print(f"-> {table_action}\n{pd.DataFrame(table_text[1:], columns=table_text[0])}")
                    if 'group_sub_table' in table_info:
                        group_column, group_info = table_info["group_sub_table"]
                        group_headers = ["Group ID", group_column, "Count"]
                        group_rows = []
                        for i, (v, count) in enumerate(group_info):
                            if v.strip() == "":
                                v = "[Empty Cell]"
                            group_rows.append([f"Group {i + 1}", v, str(count)])
                        # print(f"{pd.DataFrame(group_rows, columns=group_headers)}")
                    # print()

        return result
    except Exception as e:
        return f"Processing failed. {e}"
