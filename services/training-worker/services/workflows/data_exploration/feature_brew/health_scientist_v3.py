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


def initialize_feature_brew_workflow_agent(user = None, project = None, response_container = None, file_loader = False):
    # Initialize OpenAI components
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

    DOMAIN_HINTS = """
* Assess each existing column for potential new features in every step.
* Ensure the dataset is re-oriented to `patient_id` when dealing with multiple claims per patient, if necessary.
* For outcome prediction based on temporal events, apply a chronological sliding window approach.
* For outcome prediction based on an overall patient view, use an aggregated approach (add aggregate columns rather than reducing rows).
* Use the metadata/schema to fully understand the columns and inform analysis decisions.
* Recommendation: For temporal/longitudinal datasets, focus on creating features that capture:
- Time between key events: How long after an initial diagnosis or treatment certain codes appear.
- Sequence of claims and events: Order and timing of drug codes, diagnoses, and procedures.
- Cumulative metrics: Running counts of unique codes, financial accumulations, and frequency of events.
- Lagged features: Historical values as features for predictive modeling.
* Practical Steps to Prevent Leakage and Use Anchor Dates:
- Set Anchor Dates: Choose or create an anchor date column for each patient (e.g., anchor_date or svc_dt for service date).
- Preprocess Data: Filter data to only include records up to the anchor date for each patient when generating features.
- Create Temporal Windows: Engineer features that are time-bound, such as "number of relevant drug codes in the past 6 months" or "average cost per claim up to the anchor date."
- Avoid Future Data: Ensure that any columns or derived features that use data beyond the anchor date are excluded during the feature engineering process.
"""

    FEATURE_HINTS = """
* Combined Feature Engineering Tips for Temporal and Non-Temporal Data:
- Rolling and Window-Based Features: Use rolling windows (e.g., 30-day, 90-day) for averages, counts, and trends to capture short-term changes.
- Lag Features: Include past values of metrics (e.g., lagged diagnoses) to understand prior states.
- Event-Based Features: Track time since significant events or frequency of specific events to capture patient history.
- Cumulative and Aggregated Features: Calculate cumulative sums, averages, or counts to summarize overall activity.
- Seasonality and Time of Year: Extract features for season or quarter, and create weekday/weekend indicators.
- Statistical Features: Include standard deviation, variance, and skewness to capture data spread and shape.
- Categorical Feature Engineering: Use one-hot encoding, frequency encoding, and target encoding for categorical variables.
- Interaction Features: Combine features through addition, multiplication, or conditional interactions to uncover non-linear relationships.
- Ratio and Group Features: Create ratios (e.g., claim amount/number of visits) and calculate group statistics (e.g., mean per patient).
- Imputation Indicators: Add binary flags for missing values to highlight potential data gaps.
- Clustering Features: Use clustering algorithms (e.g., K-Means) to create group labels and distance metrics as features.
- Binning: Discretize continuous variables into bins (e.g., age groups) or use quantile binning for balanced representations.
- Log and Power Transformations: Apply log or power transformations to handle skewed data distributions.
- Outlier Treatment: Cap and floor extreme values or use Winsorizing to limit outliers' effects.
- Boolean Flags: Add binary flags for specific conditions or interactions (e.g., age > 50 with specific diagnoses).
- Trend and Decay Features: Capture trends in rolling windows or use decay functions for recent data emphasis.
- Pattern Recognition: Identify and create features for recurring or common sequences in the data.
- Dimensionality Reduction: Use PCA or clustering-based features for high-dimensional data.
- Text-Based Features: Extract sentiment, keywords, or embeddings from textual data.
- Temporal Aggregation and Hierarchies: Aggregate data by time buckets (e.g., month, quarter) and create temporal features like month-over-month change.
- Autoregressive Features: Use past values to inform future predictions in time-series data.
- Feature Selection and Correlation Checks: Regularly review feature importance and correlations to avoid multicollinearity.
- Cross-Validation Strategy: Use time-based cross-validation for temporal data and stratified methods for non-temporal data.
- Preserve Time Order: Always keep the chronological order in temporal data to prevent data leakage.
* Sample code non-temporal data:
```
import pandas as pd
import numpy as np

# One-Hot Encoding for categorical variables
encoded_df = pd.get_dummies(data['categorical_feature'], prefix='cat')

# Interaction feature between age and claim count
data['age_claim_interaction'] = data['age'] * data['claim_count']

# Binning a continuous variable (e.g., age)
data['age_bin'] = pd.cut(data['age'], bins=[0, 18, 35, 50, 65, 80, 100], labels=['0-18', '19-35', '36-50', '51-65', '66-80', '81-100'])

# Log transformation to handle skewed data
data['log_claim_amount'] = np.log1p(data['claim_amount'])
```
* Sample code temporal data:
```
# Rolling window feature for 90-day claim count
synthetic_data_df['90_day_claim_count'] = synthetic_data_df.groupby('patient_id')['claim_id'].rolling('90D').count().reset_index(level=0, drop=True)

# Lag feature for diagnosis within 30 days before the event
synthetic_data_df['diagnosis_lag_30'] = synthetic_data_df.groupby('patient_id')['diagnosis_code'].shift(30)

# Time since last diagnosis event
synthetic_data_df['days_since_last_diagnosis'] = synthetic_data_df.groupby('patient_id')['svc_dt'].diff().dt.days
```
""" # expert hints

    trimmer = trim_messages(
        max_tokens=124000,
        strategy="last",
        token_counter=llm_mini,
        include_system=True,
    )

    planner_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """As a world-class ML Scientist/Researcher with expertise in healthcare data, for the given objective, come up with a detailed, step-by-step analysis plan and provide comprehensive learnings for extracting/transforming features from the given dataset.
The goal of the tasks/steps is to gain insights about the dataset to make preprocessing and feature engineering decisions. This plan should cover individual tasks strictly within the scope of data analysis, ensuring that, if executed correctly, they yield a thorough understanding of the dataset and final insights. 
Ensure each step is self-contained with all necessary information and avoid skipping steps.

**Note:**
* ALWAYS start with candidate feature & details, and then define the analysis plan to validate them.
* Make sure candidate features are well thought of, as per the use-case.
* Include analysis action hints for analysts to refer to; be as detailed as possible.
* Do not include steps to perform data transformations or feature engineering.
* The overall goal is strictly data analysis for the given question and context.
* MUST: Conduct (statistical) visualization analysis for each step, if applicable. Extract learnings from every analysis.
* MUST: Filter irrelevant columns for any analysis.
* MUST: Summarize and describe every field, including data types, allowed values, and potential connections with other fields.
* MUST: Investigate and handle missing values, ensuring data cleanup is mentioned where necessary.
* MUST: Propose feature suggestions, including discrete features, temporal features, and sequence features.
* MUST: Identify suitable methods of encoding for features, such as one-hot encoding, binary encoding, and n-gram encoding, and suggest when applicable.

=====
**Example Analysis Plan:**

Question - Does this patient have ALK+ NSCLC?
Plan -
* Step 1: Candidate Features: . . . (with justification)
* Step 2: Label requirement analysis: Check if the target class label (ALK+ NSCLC) exists within the dataset or if it can be derived. Identify relevant columns (ndc_cd, prev_ndc_cd) and filter for codes related to ALK+ NSCLC drugs. Generate a count plot of ndc_cd to verify if there are occurrences of these codes.
* Step 3: Field Description and Summary Analysis: Review each field in the dataset, documenting the data type, allowed values, and potential connections with other fields. Identify key columns for further analysis. Use `data.info()` and `data.describe()` to gather an overview.
* Step 4: Missing Value Analysis and Data Cleanup: Investigate missing data in every column using `data.isnull().sum()`. Create a heatmap with `sns.heatmap(data.isnull(), cbar=False)` to visualize missing patterns. Recommend strategies for filling missing values or removing incomplete columns where needed. Identify columns with high percentages of missing values and suggest appropriate imputation methods. Check for inconsistencies or errors in data entries and propose cleanup strategies.
* Step 5: Data Aggregation and Patient-Centric Analysis: Evaluate if data should be aggregated at the `patient_id` level to construct a comprehensive patient history. Use `groupby('patient_id')` to aggregate key columns (`claim_id`, `svc_dt`, `diagnosis_code`, etc.). Visualize the distribution of claims per patient with a histogram.
* Step 6: . . .
. . .
* Step 9: Temporal Event Analysis: Analyze the sequence of events by creating features such as `days_since_first_claim` per `patient_id` and examining claim timelines. Generate a time-series plot for a visual representation of the temporal distribution.
* Step 10: Demographic Distribution Analysis: Investigate demographic attributes (e.g., `patient_birth_year`, `patient_gender`) and analyze their distribution. Create features like age from `patient_birth_year` and plot histograms and bar charts.
* Step 11: Diagnosis and Drug Code Analysis: Review the frequency and types of diagnosis codes (`diagnosis_code`) and drug codes (`ndc_cd`) to find relevant patterns. Filter for ALK+ NSCLC drug codes and plot their occurrences.
* Step 12: Feature Encoding Strategy Identification: Identify the best encoding methods for categorical and text-based features. Recommend one-hot encoding for categorical data, binary encoding for ordinal fields, and n-gram encoding for text features where applicable.
* Step 13: Source of Business (SOB) Analysis: Evaluate the `sob` field to understand patient claim origins. Plot a pie chart or bar chart to represent the distribution of different `sob` values.
* Step 14: Feature Suggestions Analysis: Identify potential new features that could be extracted from existing data. Consider discrete features (e.g., binning continuous variables), temporal features (e.g., time since last event), and sequence features (e.g., order of events). For each suggested feature, provide rationale and potential impact on the analysis. Visualize relationships between existing features and proposed new features using scatter plots or pair plots where appropriate.
* Step 15: Correlation and Feature Importance: Correlate columns that could indicate feature importance, such as `diagnosis_code` and `ndc_cd`, against patient attributes. Use correlation matrices and plot heatmaps.
* . . . <more steps to ensure insights into the dataset for preprocessing and feature engineering decisions>

    """,
            ),
            ("placeholder", "{messages}"),
        ]
    )
    planner_chain = planner_prompt | trimmer | reasoning_llm.with_structured_output(Plan)

    replanner_prompt = ChatPromptTemplate.from_template(
        """As a world-class ML Scientist/Researcher with expertise in healthcare data, for the given objective, validate the response from the previous steps run. The goal of the tasks/steps is to gain insights into the dataset for making preprocessing and feature engineering decisions. Provide a thorough analysis of the tasks and the dataset. Execute each step, validate the response of the last run, and modify the steps as needed to proceed to the next task. Do not include any superfluous steps. Ensure the final step yields the complete answer. Ensure each step has all the necessary details and avoid skipping any essential information.

**Note:**
* Each step will be assigned to an executor agent to perform analysis on, so be as descriptive as possible.
* Make sure candidate features are well thought of, as per the use-case.
* Include detailed analysis action hints for the analyst.
* Do not include steps to perform data transformations or feature engineering.
* Focus strictly on data analysis for the provided question/context. It should based on the candidate features.
* Do not exceed 20 (prefix: Step 20) total (current + past plan) steps or even fewer, as required for the validation of the candidate features; ensure coverage of every column attribute across these steps.
* MUST: Conduct (statistical) visualization analysis for each applicable step.
* MUST: Evaluate each existing column for its potential as a new feature and suggest any needed reorientation for feature extraction.
* MUST: Summarize each field, including data type, allowed values, and potential connections to other fields.
* MUST: Investigate and handle missing values, ensuring data cleanup suggestions are mentioned where necessary.
* MUST: Propose potential discrete, temporal, and sequence features.
* MUST: Identify and suggest appropriate methods for encoding features (e.g., one-hot, binary, n-gram).

=====
**Example Analysis Plan:**

Question - Does this patient have ALK+ NSCLC?
Past Steps - [* Step 1: Candidate Features: . . . (with justification), Step 1: Label requirement analysis: Check if the target class label (ALK+ NSCLC) exists within the dataset or if it can be derived. Identify relevant columns (ndc_cd, prev_ndc_cd) and filter for codes related to ALK+ NSCLC drugs. Generate a count plot of ndc_cd to verify if there are occurrences of these codes., Step 2: Field Description and Summary Analysis: Review each field in the dataset, documenting the data type, allowed values, and potential connections with other fields. Identify key columns that are relevant for further analysis. Use `data.info()` and `data.describe()` to gather an overview.]
Response Plan -
* Step 3: Field Description and Summary Analysis: Review each field in the dataset, documenting the data type, allowed values, and potential connections with other fields. Identify key columns for further analysis. Use `data.info()` and `data.describe()` to gather an overview.
* Step 4: Missing Value Analysis and Data Cleanup: Investigate missing data in every column using `data.isnull().sum()`. Create a heatmap with `sns.heatmap(data.isnull(), cbar=False)` to visualize missing patterns. Recommend strategies for filling missing values or removing incomplete columns where needed. Identify columns with high percentages of missing values and suggest appropriate imputation methods. Check for inconsistencies or errors in data entries and propose cleanup strategies.
* Step 5: Data Aggregation and Patient-Centric Analysis: Evaluate if data should be aggregated at the `patient_id` level to construct a comprehensive patient history. Use `groupby('patient_id')` to aggregate key columns (`claim_id`, `svc_dt`, `diagnosis_code`, etc.). Visualize the distribution of claims per patient with a histogram.
* Step 6: . . .
. . .
* Step 9: Temporal Event Analysis: Analyze the sequence of events by creating features such as `days_since_first_claim` per `patient_id` and examining claim timelines. Generate a time-series plot for a visual representation of the temporal distribution.
* Step 10: Demographic Distribution Analysis: Investigate demographic attributes (e.g., `patient_birth_year`, `patient_gender`) and analyze their distribution. Create features like age from `patient_birth_year` and plot histograms and bar charts.
* Step 11: Diagnosis and Drug Code Analysis: Review the frequency and types of diagnosis codes (`diagnosis_code`) and drug codes (`ndc_cd`) to find relevant patterns. Filter for ALK+ NSCLC drug codes and plot their occurrences.
* Step 12: Feature Encoding Strategy Identification: Identify the best encoding methods for categorical and text-based features. Recommend one-hot encoding for categorical data, binary encoding for ordinal fields, and n-gram encoding for text features where applicable.
* Step 13: Source of Business (SOB) Analysis: Evaluate the `sob` field to understand patient claim origins. Plot a pie chart or bar chart to represent the distribution of different `sob` values.
* Step 14: Feature Suggestions Analysis: Identify potential new features that could be extracted from existing data. Consider discrete features (e.g., binning continuous variables), temporal features (e.g., time since last event), and sequence features (e.g., order of events). For each suggested feature, provide rationale and potential impact on the analysis. Visualize relationships between existing features and proposed new features using scatter plots or pair plots where appropriate.
* Step 15: Correlation and Feature Importance: Correlate columns that could indicate feature importance, such as `diagnosis_code` and `ndc_cd`, against patient attributes. Use correlation matrices and plot heatmaps.
* . . . <more steps to ensure insights into the dataset for preprocessing and feature engineering decisions>

Question - Does this patient have ALK+ NSCLC?
Past Steps - [Step 1: Missing value analysis, Step 2: Demographic Distribution, Step 3: Prescription and Label Analysis, Step 4: Claim Count Distribution, Step 5: Diagnosis Code Analysis, Step 6: Temporal Trends]
Response Plan -
This dataset comprises payer claims data, including patient demographics, diagnoses, drug information, and temporal details. It is used for predictive analysis to identify patients likely to have ALK+ NSCLC before treatment prescription.
The task is to engineer features from the claims data to build a Patient Predictor model that can identify ALK+ NSCLC patients based on their medical history, including diagnoses, comorbidities, and treatments.

=====
**Context**
Your objective, for feature engineering, was this:
{question}

Additional Context:
{additional_context}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Metadata:
{metadata}

Extracted Schema:
{schema}

Update your plan accordingly. If the last run RESPONSE is correct and no more steps are needed and you can return last output to the user, for addressing the original question. 
Otherwise, fill out the new plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
    )

    replanner_chain = replanner_prompt | reasoning_llm.with_structured_output(Act)

    synthesize_prompt = ChatPromptTemplate.from_template(
        """As a world-class ML Scientist/Researcher with expertise in healthcare data, consolidate all the analysis results  for the given objective using the provided pieces of retrieved answers from executed steps. Ensure that the response strictly reflects the provided context without omitting any information or adding unsubstantiated content.

Ensure your response:
- Removes ambiguity/generalization and provides a specific, data-driven answer.
- Clearly states if information is not available or cannot be directly deduced from the context.
- Outputs the response in valid JSON format as per the following structure:

    {{
        "dataset_description": Description of the dataset along with insights. Overall goal including Data Characteristics.
        "task": Complete understanding of the task, including all relevant information required to solve it. Overall goal including Data Characteristics.
        "analysis": [
            {{
                "<statistical_analysis>": Detailed report of the analysis, insights, and learnings for feature engineering, including visualization insights and suggestions.
                "recommended_features": List of recommended features directed by the above analysis 
                "steps": [ {{ "description": "Explanation of the step", "code": "Sample code snippet used for this step", "sample_result": "Example output or description of findings" }}, ... ]
            }},
            ...
        ],
        "suggested_approach": List of Recommended approach to prepare this dataset and perform feature engineering on. It could be mix of various data-driven approaches.
    }}
    
**Data Analysis Steps:**
{past_steps}

**Note:**
* STRICTLY: final list should be atleast 20 analysis results
* the overall goal is strictly data analysis, for the original question and context shared by user
* make a calculated judgement on adding new analysis steps; refer the dataset and use-case to determine analysis steps

=====
**Example:**
Question - Does this patient have ALK+ NSCLC?
Response -
{{
    "description": "This dataset comprises payer claims data, including patient demographics, diagnoses, drug information, and temporal details. It is used for predictive analysis to identify patients likely to have ALK+ NSCLC before treatment prescription.",
    "task": "The task is to engineer features from the claims data to build a Patient Predictor model that can identify ALK+ NSCLC patients based on their medical history, including diagnoses, comorbidities, and treatments.",
    "analysis": [
      {{
        "Missing Value Analysis": "Initial exploration showed missing values in columns such as `svc_dt` and `diagnosis_code_x`. We used forward fill and imputation strategies to address these gaps, ensuring the dataset is suitable for feature engineering.",
        "recommended_features": []
        "steps": [
            {{
                "description": "Analyzed null values in the dataset to understand data completeness",
                "code": "data.isnull().sum()",
                "sample_result": "svc_dt: 100 nulls, diagnosis_code_x: 50 nulls"
            }},
            {{
                "description": "Applied forward fill method to handle missing values where applicable",
                "code": "data['svc_dt'].fillna(method='ffill', inplace=True)",
                "sample_result": "Nulls in svc_dt reduced to 0"
            }}
        ]
      }},
      {{
        "Demographic Distribution": "The distribution of patient ages and genders was reviewed, revealing a higher number of patients between the ages of 40 and 60. Female patients made up approximately 55% of the dataset.",
        "recommended_features": ["ages", "gender"]
        "steps": [
            {{
                "description": "Generated age distribution and visualized it",
                "code": "plt.hist(data['age'], bins=20); plt.xlabel('Age'); plt.ylabel('Frequency'); plt.title('Age Distribution')",
                "sample_result": "Histogram showing a peak in the 40-60 age range"
            }},
            {{
                "description": "Calculated gender distribution percentages",
                "code": "data['gender'].value_counts(normalize=True)",
                "sample_result": "Female: 55%, Male: 45%"
            }}
        ]
      }},
      {{
        "Prescription and Label Analysis": "Approximately 15% of patients in the dataset had prescriptions for drugs like Alecensa, Xalkori, or Zykadia, indicating the potential proxy label for ALK+ NSCLC.",
        "recommended_features": ["key_drug_flag", "days_since_first_claim", "prescription_count"]
        "steps": [
            {{
                "description": "Filtered for relevant drug codes in `ndc_cd`",
                "code": "data[data['ndc_cd'].isin(['69814120', '69814020', '50242013001'])]",
                "sample_result": "200 rows matching the target drug codes"
            }},
            {{
                "description": "Counted occurrences of target drug prescriptions",
                "code": "data['ndc_cd'].value_counts()",
                "sample_result": "Drug code 69814120: 80 occurrences, Drug code 69814020: 70 occurrences"
            }}
        ]
      }},
      {{
        "Diagnosis Code Analysis": "Patients with more than 5 unique diagnosis codes often showed a higher likelihood of being prescribed the key drugs. This insight supports the use of diagnosis diversity as a predictive feature.",
        "recommended_features": ["diagnosis_code_count", "days_since_first_claim", "diagnosis_diversity"]
        "steps": [
            {{
                "description": "Counted the number of unique diagnosis codes per patient",
                "code": "data.groupby('patient_id')['diagnosis_code'].nunique()",
                "sample_result": "Patients with more than 5 unique diagnosis codes: 150"
            }},
            {{
                "description": "Correlated diagnosis code count with drug prescriptions",
                "code": "data[['diagnosis_count', 'key_drug_flag']].corr()",
                "sample_result": "Correlation coefficient: 0.45"
            }}
        ]
      }},
      . . .
    ],
    "suggested_approach": [
        "Data Preparation: Clean data, handle missing values, and convert date columns for temporal analysis.",
        "Label Creation: Create a binary label based on prescriptions ('ALECENSA', 'XALKORI', 'ZYKADIA').",
        "Temporal Features: Use sliding windows, time since last event, and trend analysis to capture short-term patterns.",
        "Lag Features: Create lagged diagnosis and treatment features for understanding prior patient states.",
        "Cumulative Features: Calculate cumulative counts for diagnoses, treatments, and claims over time.",
        "Frequency Features: Count occurrences of key diagnoses and treatments within defined periods.",
        "Interaction Features: Combine features (e.g., age * claim count) to capture non-linear relationships.",
        "Seasonal Features: Add season or quarter indicators to identify time-of-year patterns.",
        "Patient-Level Aggregation: Summarize temporal data to create patient-level rows capturing overall history.",
        "Feature Scaling: Standardize numerical features for consistent model training.",
        "Feature Selection: Use correlation and feature importance to select top predictive features.",
        "Validation Strategy: Implement time-based cross-validation for robust model evaluation.",
        "Analysis and Iteration: Perform exploratory analysis, adjust features based on model feedback, and iterate.".
        ...
    ]
}}

=====
**Context**
Your objective was this:
{question}

Additional Context:
{additional_context}

Data Analysis Final Response:
{response}

If any required information is missing from the context or there is ambiguity that needs to be addressed for a successful response, clearly state this in your feedback."""
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
        metadata = state["metadata"]
        work_dir = state["work_dir"]
        df = [pd.read_csv(path) for path in state["data"]]
        task = plan[0]

        task_formatted = f"""You are tasked with executing the step and sharing the analysis report for: {task}.

Note:
* The goal is to perform analysis that supports the feature engineering objective: {query}.
* Ensure the analysis covers the entire dataset, not just a sample.
* Make sure to consider all dataframes for analysis, as applicable.
* Make sure to consider any preprocessing/enriching/merging/cleaning of the data for each analysis, as required.
* OUTCOME: Each task should provide insights that can be used for feature engineering.
* MUST: Validate the analysis before sharing the final report.
* HINT: The data is in-memory as a DataFrame and should not be read from any file.
* HINT: If any syntax errors occur, modify and re-execute the code to ensure correctness.

=====
Metadata for context:
{metadata}
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
            prefix=prefix,
            callback_manager=callback_manager,
        )
        try:
            result = await pandas_agent.ainvoke(task_formatted)
        except Exception as e:
            result = handle_agent_error(e)
        return {
            "past_steps": [(task, result["output"] if "output" in result else result)],
        }

    async def plan_step(state: PlanExecute):
        query = state["question"]
        work_dir = state["work_dir"]
        hints =  DOMAIN_HINTS + "\n\n" + FEATURE_HINTS
        additional_context = state["additional_context"]
        metadata = load_metadata(work_dir)
        schema = load_schema(work_dir)
        feature_num = state["feature_num"]
        plan = await planner_chain.ainvoke({
            "messages": [
                ("user", query),  # User's message or query
                ("user", f"""\nAdditional Context:\n\n {additional_context}"""),
                ("user", f"""\nMetadata:\n\n {metadata}"""),
                ("assistant", f"""\nExtracted Schema:\n\n {schema}"""),
                ("assistant", f"""\nDomain Hints:\n\n {hints}"""),
                ("assistant", f"""\nCandidate Features:\n\n Consider candidate features which are feasible, also must not be fewer than {feature_num}.""")
            ],
        })
        return {"plan": plan.steps, "metadata": metadata, "schema": schema, "hints": hints}

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

    label_prompt = ChatPromptTemplate.from_template(
        """As a world-class Data Scientist with expertise in healthcare data, determine what data labeling is required for the given objective. 
Use the provided data analysis to decide whether labeling is necessary. Ensure that your answer is specific and data-driven, removing any ambiguity or generalizations. 
If information is not available or cannot be deduced from the context, state that you don't know.

The output should be a valid JSON object in the following structure:
{{
    "instructions": Labeling instructions for the classes (if applicable)
    "analysis": Detailed analysis of data justifying the labeling decision
    "code": Code block in markdown to perform the label transformation, if labeling is needed
}}

**Note**: 
* If labeling is not required, return empty instructions.
* Keep in mind, if user has asked for labeling, it should have required data in the dataset or prompt.

**Hints**:
* If specific labeling required attributes doesn't allow direct match, be creative and look for patterns like start_with, end_with, contains or more.

=====
**Example**:
Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history.
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
{{
    "instructions": "Label the dataset with a target variable indicating ALK+ NSCLC positivity. This label should be determined by checking if a patient was prescribed 'ALECENSA', 'XALKORI', or 'ZYKADIA' using 'ndc_cd' or 'prev_ndc_cd' that starts with '69814120', '69814020', or '50242013001'.",
    "analysis": "The analysis of synthetic_data_df confirms that patients prescribed these drugs align with the treatment for ALK-positive NSCLC. Labeling based on these prescriptions ensures accurate patient identification for model training.",
    "code": "synthetic_data_df['label'] = ((synthetic_data_df['ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001')) | synthetic_data_df['prev_ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001')))"
}}


======
**Context**
Your objective was this:
{question}

Additional Context:
{additional_context}

Data Analysis:
{data_analysis}

Metadata:
{metadata}

Extracted Schema:
{schema}

If information is missing or ambiguous, mention what additional data would be needed for successful labeling."""
    )

    label_chain = label_prompt | trimmer | chat_llm | StrOutputParser()

    wrangling_prompt = ChatPromptTemplate.from_template(
        """As a world-class Data Engineer with expertise in healthcare data, determine the necessary preprocessing/wrangling steps required to prepare the dataset for feature engineering based on the data analysis provided. Ensure the answer is specific and data-driven, removing any ambiguity or generalizations. If information is not available or cannot be directly deduced from the context, clearly state that you don't know.

The output should be a valid JSON object in the following structure:
  {{
    "instructions": Data wrangling/processing instructions 
    "analysis": Detailed analysis of the original dataset backing the instructions
    "code": Code block in markdown for the instructed transformation
  }}

**Note**: The goal is to outline data wrangling steps that prepare the dataset for feature engineering.

**Hints**:
* MUST: Consider all the attributes/columns for this
* MUST: Make sure to clean the dataset
* MUST: Make sure to standardize/normalize the dataset
* MUST: Make sure to handle missing data and/or NaNs
* Refer the below analysis and labeling context, as precursors, for your result

=====
**Example**:
Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history.
* For label creation - Consider 'ndc_cd' or 'prev_ndc_cd' that starts with (ALECENSA),  (XALKORI), or  (ZYKADIA).
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
{{
    "instructions": "Handle missing values, ensure consistent data types, preprocess date columns, and aggregate data at the patient level to provide a summarized view of medical history.",
    "analysis": "The original dataset contains repeated entries for claims (e.g., claim_id, svc_dt) for the same patient. Aggregating by patient_id is essential for consolidating information, such as claim counts and diagnosis diversity, into one comprehensive row per patient.",
    "code": "patient_level_df = synthetic_data_df.groupby('patient_id').agg({{\n 'age': 'first',\n 'gender': 'first',\n 'key_drug_flag': 'max',\n 'claim_count': 'sum',\n 'days_since_first_claim': 'max',\n 'diagnosis_code_count': 'max',\n 'comorbidity_flag': 'max',\n 'longitudinal_flag': 'first',\n 'first_claim_year': 'min',\n 'days_to_adjudicate': 'mean'\n}}).reset_index()"

}}

======
**Context**
Your objective was this:
{question}

Additional Context:
{additional_context}

Data Analysis:
{data_analysis}

Labeling, to keep in mind:
{labeling}

Metadata:
{metadata}

Extracted Schema:
{schema}

If information is missing or ambiguous, mention what additional data would be needed for successful labeling."""
    )

    wrangling_chain = wrangling_prompt | trimmer | chat_llm | StrOutputParser()

    feature_engg_prompt = ChatPromptTemplate.from_template(
        """As a world-class ML Engineer with expertise in healthcare data, determine the features required for preparing the dataset for feature engineering based on the provided data analysis. Suggest relevant features given the dataset context and ensure your answer is specific and data-driven. If information is not available or cannot be directly deduced from the context, clearly state that you don't know.

The output should be a valid JSON array with the following structure:
[
    {{
        "feature_name": Feature Name,
        "data_type": Data type like integer, string, etc.,
        "category": Feature category, like demographic, temporal, diagnosis, etc.,
        "description": Description of the feature,
        "range": Value range,
        “code”: Code block in markdown for feature extraction,
        “useful_ness”: Statistical justification for the feature,
        “analysis”: Detailed analysis of the dataset backing the feature selection,
        “input_samples”: Example inputs and generated outputs for the feature,
    }}
    . . .
]


**Note**:
* Ensure the suggested features cover various categories and align with the analysis context.
* Ensure balanced feature distribution across different categories.
* The number of suggested feature must not be fewer than {feature_num}.
* Refer the below analysis, labeling and preprocessing/wrangling context, as precursors, for your result.

=====
**Example**:

Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history.
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
[
    {{
      "feature_name": "age",
      "data_type": "integer",
      "category": "demographic",
      "description": "Age of the patient at the time of service.",
      "range": "0-120",
      "code": "patient_level_df['age'] = 2024 - patient_level_df['patient_birth_year']",
      "usefulness": "High. Age often indicates the risk factor for various medical conditions. In our analysis, we found that patients above 50 showed higher claim counts and were more likely to have chronic diagnoses. This information can help predict the likelihood of severe conditions like NSCLC.",
      "analysis": "From the synthetic data, patients aged 50+ had higher counts of associated diagnoses and were more often prescribed treatments indicative of severe conditions.",
      "input_samples": "['1991', '1972', '2003']"
    }},
    {{
      "feature_name": "key_drug_flag",
      "data_type": "binary",
      "category": "treatment",
      "description": "Indicates if the patient was prescribed Alecensa, Xalkori, or Zykadia.",
      "range": "0 or 1",
      "code": "patient_level_df['key_drug_flag'] = patient_level_df['key_drug_flag'].apply(lambda x: 1 if x > 0 else 0)",
      "usefulness": "Very High. This feature directly reflects whether the patient is receiving targeted treatment for ALK+ NSCLC. Our analysis showed that this flag is present for about 15% of patients in the dataset, correlating strongly with patients with severe medical histories.",
      "analysis": "Reviewing the prescription data in `ndc_product_df` and matching it with `synthetic_data_df` confirmed that patients with this flag had higher numbers of chronic and severe diagnosis codes.",
      "input_samples": "[0, 1, 0, 0, 1]"
    }},
    {{
      "feature_name": "days_since_first_claim",
      "data_type": "integer",
      "category": "temporal",
      "description": "Number of days since the patient's first claim to the current claim.",
      "range": "0-5000",
      "code": "patient_level_df['days_since_first_claim'] = (synthetic_data_df['svc_dt'] - synthetic_data_df.groupby('patient_id')['svc_dt'].transform('min')).dt.days.max()",
      "usefulness": "High. Indicates how long the patient has been tracked in the system. Analysis showed that patients with more extended histories in the system had complex medical conditions.",
      "analysis": "Patients with over 1000 days since the first claim were likely to have multiple diagnoses and treatments, providing insights into their long-term health management.",
      "input_samples": "[300, 120, 45]"
    }},
    {{
      "feature_name": "diagnosis_code_count",
      "data_type": "integer",
      "category": "diagnosis",
      "description": "Count of unique diagnosis codes associated with a patient.",
      "range": "1-50",
      "code": "patient_level_df['diagnosis_code_count'] = synthetic_data_df.groupby('patient_id')[['diagnosis_code_1', 'diagnosis_code_2', ..., 'diagnosis_code_8']].nunique().sum(axis=1)",
      "usefulness": "Medium. The diversity of diagnosis codes indicates the complexity of the patient's medical history. Patients with more than 5 unique codes were found to have more severe health profiles.",
      "analysis": "Patients in the dataset with a higher diagnosis code count often had a history of chronic or complex conditions, aligning with potential ALK+ NSCLC indicators.",
      "input_samples":
    }}
    . . .
  ]

======
**Context**
Your objective was this:
{question}

Required feature Count:
{feature_num}

Additional Context:
{additional_context}

Data Analysis:
{data_analysis}

Labeling:
{labeling}

Preprocessing:
{wrangling}

Metadata:
{metadata}

Extracted Schema:
{schema}

Domain Hints, for coming up with feature ideas:
{hints}

If information is missing or ambiguous, mention what additional data would be needed for successful labeling."""
    )

    feature_engg_chain = feature_engg_prompt | trimmer | chat_llm | StrOutputParser()

    scientist_prompt = ChatPromptTemplate.from_template(
        """As a world-class ML Engineer with expertise in healthcare data, consolidate the final list of detailed step-by-step instructions based on the provided analysis, wrangling, and feature engineering results. 
Each set of instructions should comprehensively guide the user from raw input data through labeling, preprocessing, and feature extraction for each individual feature. 
Ensure the answer is specific, data-driven, and removes any ambiguity or generalization. If information is not available or cannot be deduced directly from the context, clearly state that you don't know.

The number of suggested instructions set, in the output list, must not be less than {feature_num}, in count. The output should be a valid (strictly) JSON array with the following structure:
  [
    {{
        "dataset_description": "Detailed Description of the dataset along with insights"
        "task": "Complete understanding of the task, including all relevant information required to solve it",
        "details": "Usefulness and justification of the feature(s) included in this instructions set, for the above task",
        "labeling_instructions": "Step-by-step instructions for necessary labeling, as per the dataset, for the goal of feature engineering",
        "preprocessing_instructions": "Step-by-step instructions for necessary preprocessing, cleaning, and preparation for feature extraction.",
        "feature_instructions": "Step-by-step instructions for feature extraction.",
        "analysis": "Analysis of the original dataset that justifies the instructions and the USEFULNESS of the feature(s) in this instruction set.",
        "code": "Code block in markdown for the entire labeling, preprocessing and feature extraction steps. Entire code that converts raw dataset into having this new feature.",
        "category": "Feature category (e.g., demographic, temporal, diagnosis, treatment, etc.).",
        "features": ["List of features extracted in these instructions."]
    }},
    ... <{feature_num} element count>
  ]

**Note**:
* MUST: Each output JSON object should correspond to one feature in the feature engineering results, with detailed end-to-end instructions.
* Ensure each instruction set includes comprehensive preprocessing and labeling steps before feature extraction.
* The goal is for each instruction set to be applicable to raw datasets and create new labeled and processed features.
* Each instruction set must refer to relevant analysis insights to back up why certain preprocessing or features are necessary.

=====
**Example**:

Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history.
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
```json
[    
    {{
        "description": "This dataset comprises payer claims data, including patient demographics, diagnoses, drug information, and temporal details. It is used for predictive analysis to identify patients likely to have ALK+ NSCLC before treatment prescription.",
        "task": "The task is to engineer features from the claims data to build a Patient Predictor model that can identify ALK+ NSCLC patients based on their medical history, including diagnoses, comorbidities, and treatments.",
        "details": "This is a time-series healthcare data. Your task is to transform the claims data to a longitudinal patient-level data."
            "`age` - High. Age often indicates the risk factor for various medical conditions. In our analysis, we found that patients above 50 showed higher claim counts and were more likely to have chronic diagnoses. This information can help predict the likelihood of severe conditions like NSCLC."
        "labeling_instructions": "Label the data by checking if `ndc_cd` or `prev_ndc_cd` indicates ALK+ NSCLC drug prescriptions (e.g., starts with '69814120', '69814020', '50242013001')."
        "preprocessing_instructions":
            "- Start by loading the payer claims data."
            "- Sort the dataset by `patient_id` and `svc_dt` to maintain the temporal sequence."
            "- Clean the dataset by handling missing values and standardizing data types. Use forward fill for missing `svc_dt` and replace 'nan' values with 0 in numerical columns." 
        "feature_instructions":
            "- Create the `age` feature by calculating the patient's age at the time of service using the `patient_birth_year` column.",
        "analysis": "The data analysis indicated that age and drug prescription data are crucial for identifying ALK+ NSCLC patients. Sorting by `svc_dt` ensures that features are built in chronological order, and handling missing values improves data integrity.",
        "code": "```python\n# Load and preprocess the data\nsynthetic_data_df['svc_dt'] = pd.to_datetime(synthetic_data_df['svc_dt'])\nsynthetic_data_df.sort_values(by=['patient_id', 'svc_dt'], inplace=True)\nsynthetic_data_df.fillna({{'svc_dt': method='ffill'}}, inplace=True)\nsynthetic_data_df.fillna(0, inplace=True)\n\n# Label creation\nsynthetic_data_df['label'] = ((synthetic_data_df['ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001')) | synthetic_data_df['prev_ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001'))).astype(int))\n\n# Feature extraction\nsynthetic_data_df['age'] = 2024 - synthetic_data_df['patient_birth_year']\n```",
        "category": "demographic",
        "features": ["age"]
    }},
    {{
        "description": "This dataset comprises payer claims data, including patient demographics, diagnoses, drug information, and temporal details. It is used for predictive analysis to identify patients likely to have ALK+ NSCLC before treatment prescription.",
        "task": "The task is to engineer features from the claims data to build a Patient Predictor model that can identify ALK+ NSCLC patients based on their medical history, including diagnoses, comorbidities, and treatments.",
        "details": "This is a time-series healthcare data. Your task is to transform the claims data to a longitudinal patient-level data."
            "`days_since_first_claim` - High. Indicates how long the patient has been tracked in the system. Analysis showed that patients with more extended histories in the system had complex medical conditions."
        "labeling_instructions": "Label the data by checking if `ndc_cd` or `prev_ndc_cd` indicates ALK+ NSCLC drug prescriptions (e.g., starts with '69814120', '69814020', '50242013001')."
        "preprocessing_instructions":
          "- Start by loading the payer claims data.\n"
          "- Sort the dataset by `patient_id` and `svc_dt` to maintain the temporal sequence.\n"
          "- Clean the dataset by handling missing values and standardizing data types. Use forward fill for missing `svc_dt` and replace 'nan' values with 0 in numerical columns.\n"
        "feature_instructions":
          "- Create the `age` feature by calculating the patient's age at the time of service using the `patient_birth_year` column."
          "- Aggregate data at the patient level to calculate `days_since_first_claim` as the difference between the earliest and current claim dates."
        "analysis": "Analysis showed that patients with more days since their first claim often have more complex medical profiles. Counting unique diagnosis codes helps indicate the severity of a patient's condition.",
        "code": "```python\n# Load and preprocess the data\nsynthetic_data_df['svc_dt'] = pd.to_datetime(synthetic_data_df['svc_dt'])\nsynthetic_data_df.sort_values(by=['patient_id', 'svc_dt'], inplace=True)\nsynthetic_data_df.fillna({{'svc_dt': method='ffill'}}, inplace=True)\nsynthetic_data_df.fillna(0, inplace=True)\n\n# Label creation\nsynthetic_data_df['label'] = ((synthetic_data_df['ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001')) | synthetic_data_df['prev_ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001'))).astype(int))\n\n# Feature extraction\nsynthetic_data_df['days_since_first_claim'] = (synthetic_data_df['svc_dt'] - synthetic_data_df.groupby('patient_id')['svc_dt'].transform('min')).dt.days\n```",
        "category": "temporal",
        "features": ["days_since_first_claim"]
    }},
    . . .
]
```

======
**Context**
Your objective was this:
{question}

Required instructions Count:
{feature_num}

Additional Context:
{additional_context}

Data Analysis:
{data_analysis}

Labeling Instructions:
{labeling}

Wrangling Instructions:
{wrangling}

Feature Engineering Instructions:
{feature_engineering}

Metadata:
{metadata}

Extracted Schema:
{schema}

If any required information is missing from the context or there is ambiguity that needs to be addressed for a successful response, clearly state this in your feedback."""
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

    # Add the plan node
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

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    app = workflow.compile(checkpointer=memory)
    # app = workflow.compile()

    return app

# if __name__ == "__main__":
#     app = initialize_feature_brew_workflow_agent()
#     human_message = ""
#     csv_paths = [
#         "/Users/sarkarsaurabh.27/Documents/Projects/FeatureBrew/data/persist/datasets/genentech-feat-dataset/source/synthetic_data_featurebyte_sampled_2000.csv"]
#     work_dir = "/Users/sarkarsaurabh.27/Documents/Projects/FeatureBrew/data/persist/datasets/genentech-feat-dataset"
#     additional_context = """
# * This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
# * For this, use the input payer claims data to build patient attributes by looking at patients’ medical history (diagnoses, comorbidity, hospital/medical history, Rx, etc.).
# * We need to map NSCLC+ALK-positive cases and the drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' to create the 'Label' column.
# * Use this logic to create the label - Set the 'Label' column to '1' if any 'ndc_cd' or 'prev_ndc_cd' starts with '69814120', '69814020', or '50242013001' and at least one 'diagnosis_code*' column starts with 'C34'. Both conditions must be met to set the label.
# * The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
#     """
#     initial_state = {
#         "question": "Does this patient have ALK+ NSCLC?",
#         "data": [pd.read_csv(path) for path in csv_paths],
#         "work_dir": work_dir,
#         "additional_context": additional_context,
#     }
