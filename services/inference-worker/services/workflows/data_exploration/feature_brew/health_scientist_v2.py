import operator
import os

import pandas as pd
from langchain.agents import AgentType
from typing import TypedDict, List, Annotated, Tuple, Union

from langchain.globals import set_llm_cache
from langchain_community.llms.bedrock import Bedrock
from langchain_community.chat_models import BedrockChat
from langchain_core.caches import InMemoryCache
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.agents import create_pandas_dataframe_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import START
from pydantic.v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langchain_core.tools import tool


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

def initialize_feature_brew_workflow_agent(user = None, project = None):
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
        max_tokens=127000,
        strategy="last",
        token_counter=llm,
        include_system=True,
    )

    planner_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """As a world class ML Scientist/Researcher with expertise in healthcare data, for the given objective, come up with a simple step by
step analysis and finally provide instructions for extracting/transforming features from the given dataset.
The goal of the tasks/steps are to get insight about the dataset to make preprocessing and feature engineering decisions.
This plan should involve individual tasks (strictly, in the scope of data analysis), that if executed correctly will yield the correct understanding of the dataset
and final answer. Do not add any superfluous steps.
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Note:
* should include analysis action hints for analyst to refer; be as detailed as possible
* do not include steps to perform any transformation
* do not include steps to perform any feature engineering
* the overall goal is strictly data analysis, for the original question and context shared by user
* MUST: conduct (statistical) visualization analysis for each of the steps, if applicable
* MUST: filter irrelevant columns for any analysis

Hints:
* Consider evaluating each existing column for potential new feature, against each step.
* Given the goal, make sure you re-orient the dataset to patient_id from having multiple claims for each patient; do the needful as per your analysis.
* If the goal is to predict outcomes based on temporal events leading to a treatment, use the chronological sliding window approach.
* If the goal is to predict outcomes based on a comprehensive overview of patient data, use the aggregated approach.
* Use the metadata/schema to understand all the existing column for better analysis.

=====
Example:

Question - Does this patient have ALK+ NSCLC?
Plan -
* Step 1: Label requirement analysis: Check if the target class label (ALK+ NSCLC) exists within the dataset or if it can be derived. Identify relevant columns (ndc_cd, prev_ndc_cd) and filter for codes related to ALK+ NSCLC drugs (69814120, 69814020, 50242013001). Generate a count plot of ndc_cd to verify if there are occurrences of these codes.
* Step 2: Missing value analysis: Analyze null values to identify data completeness and potential preprocessing requirements, for each and every column. Use data.isnull().sum() to compute the total missing values for each column. Create a heatmap using sns.heatmap(data.isnull(), cbar=False) to visualize missing data patterns.
* Step 3: Data aggregation analysis: Evaluate if aggregating data by 'patient_id' is needed. If yes, ensure data is aggregated at the patient_id level to reflect a comprehensive history per patient. Group data by patient_id and aggregate claim_id, svc_dt, diagnosis_code, and ndc_cd columns. Plot the distribution of the number of claims per patient using plt.hist(data.groupby('patient_id').size()).
* Step 4: Chronological Event Analysis: Understand the sequence of events leading up to treatment. Create a column representing days_since_first_claim per patient_id by calculating the difference between svc_dt and the earliest svc_dt. Generate a time-series plot to observe claim timelines per patient.
* Step 5: Demographic Distribution: Analyze the demographic attributes (e.g., patient_birth_year, patient_gender, zipcode) to identify patterns that may affect diagnosis or treatment. Filter relevant columns and generate age from patient_birth_year. Analyze gender distribution using data['patient_gender'].value_counts(). Plot histograms for age distribution and bar plots for gender distribution.
* Step 6: Drug Code Trend Analysis: Track trends in drug prescription codes to understand when ALK+ NSCLC-related treatments appear in the timeline. Filter and plot the ndc_cd column to identify occurrences and temporal trends for relevant drug codes. Plot a time-series chart displaying occurrences of ALK+ drugs over time.
* Step 7: Source of Business (SOB) Analysis. Evaluate the source of business (sob) field to understand patient claim origin (e.g., new therapy start, refill). Analyze the frequency of different SOB values per patient. Generate a pie chart or bar plot to represent the distribution of SOB categories.
* Step 8: Diagnosis Code Analysis: Review the range and frequency of diagnosis codes (diagnosis_code, diagnosis_code_1 to diagnosis_code_8) to find patterns indicative of ALK+ NSCLC. Count unique diagnosis codes per patient using data.groupby('patient_id')['diagnosis_code'].nunique(). Create a bar plot showing the number of unique diagnosis codes for patients.
* Step 9: Feature Importance Indicators. Correlate features that could be relevant for future feature extraction, such as diagnosis_code and ndc_cd, against known patient attributes. Use correlation matrices to observe relationships between numerical attributes and drug code flags. Plot a heatmap of feature correlations.
* . . . <more steps to get insight about the dataset to make preprocessing and feature engineering decisions>

    """,
            ),
            ("placeholder", "{messages}"),
        ]
    )
    planner_chain = planner_prompt | trimmer | llm.with_structured_output(Plan)

    replanner_prompt = ChatPromptTemplate.from_template(
        """As a world class ML Scientist/Researcher with expertise in healthcare data, for the given objective, validate the response from the pat steps run. The goal of the tasks/steps are to get insight about the dataset to make preprocessing and feature engineering decisions. Finally provide insight about the tasks and the dataset. The goal is the execute each step, upon validating the response of the last run, modify the steps to move to the next tasks. Do not add any superfluous steps. The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Note:
* Should include analysis action hints for analyst; be as detailed as possible
* do not include steps to perform any transformation or any feature engineering
* the overall goal is strictly data analysis, for the original question/context shared by user
* MUST: conduct (statistical) visualization analysis for each of the steps, if applicable
* MUST: Do not go over 20 total steps; try to cover every aspect in that list, across each column attribute
* MUST: Evaluate every existing column for potential new feature, and suggest reorientation needed for feature extraction, accordingly

=====
Example:

Question - Does this patient have ALK+ NSCLC?
Past Steps - [Step 1: Label requirement analysis: Check if the target class label (ALK+ NSCLC) exists within the dataset or if it can be derived. Identify relevant columns (ndc_cd, prev_ndc_cd) and filter for codes related to ALK+ NSCLC drugs (69814120, 69814020, 50242013001). Generate a count plot of ndc_cd to verify if there are occurrences of these codes.]
Response Plan -
* Step 2: Missing value analysis: Analyze null values to identify data completeness and potential preprocessing requirements, for each and every column. Use data.isnull().sum() to compute the total missing values for each column. Create a heatmap using sns.heatmap(data.isnull(), cbar=False) to visualize missing data patterns.
* Step 3: Data aggregation analysis: Evaluate if aggregating data by 'patient_id' is needed. If yes, ensure data is aggregated at the patient_id level to reflect a comprehensive history per patient. Group data by patient_id and aggregate claim_id, svc_dt, diagnosis_code, and ndc_cd columns. Plot the distribution of the number of claims per patient using plt.hist(data.groupby('patient_id').size()).
* Step 4: Chronological Event Analysis: Understand the sequence of events leading up to treatment. Create a column representing days_since_first_claim per patient_id by calculating the difference between svc_dt and the earliest svc_dt. Generate a time-series plot to observe claim timelines per patient.
* Step 5: Demographic Distribution: Analyze the demographic attributes (e.g., patient_birth_year, patient_gender, zipcode) to identify patterns that may affect diagnosis or treatment. Filter relevant columns and generate age from patient_birth_year. Analyze gender distribution using data['patient_gender'].value_counts(). Plot histograms for age distribution and bar plots for gender distribution.
* Step 6: Drug Code Trend Analysis: Track trends in drug prescription codes to understand when ALK+ NSCLC-related treatments appear in the timeline. Filter and plot the ndc_cd column to identify occurrences and temporal trends for relevant drug codes. Plot a time-series chart displaying occurrences of ALK+ drugs over time.
* Step 7: Source of Business (SOB) Analysis. Evaluate the source of business (sob) field to understand patient claim origin (e.g., new therapy start, refill). Analyze the frequency of different SOB values per patient. Generate a pie chart or bar plot to represent the distribution of SOB categories.
* Step 8: Diagnosis Code Analysis: Review the range and frequency of diagnosis codes (diagnosis_code, diagnosis_code_1 to diagnosis_code_8) to find patterns indicative of ALK+ NSCLC. Count unique diagnosis codes per patient using data.groupby('patient_id')['diagnosis_code'].nunique(). Create a bar plot showing the number of unique diagnosis codes for patients.
* Step 9: Feature Importance Indicators. Correlate features that could be relevant for future feature extraction, such as diagnosis_code and ndc_cd, against known patient attributes. Use correlation matrices to observe relationships between numerical attributes and drug code flags. Plot a heatmap of feature correlations.
* . . . <more steps which original plan might have missed or could be result of some analysis>

Question - Does this patient have ALK+ NSCLC?
Past Steps - [Step 1: Missing value analysis, Step 2: Demographic Distribution, Step 3: Prescription and Label Analysis, Step 4: Claim Count Distribution, Step 5: Diagnosis Code Analysis, Step 6: Temporal Trends]
Response Plan -
This dataset comprises payer claims data, including patient demographics, diagnoses, drug information, and temporal details. It is used for predictive analysis to identify patients likely to have ALK+ NSCLC before treatment prescription.
The task is to engineer features from the claims data to build a Patient Predictor model that can identify ALK+ NSCLC patients based on their medical history, including diagnoses, comorbidities, and treatments.

======
Your objective, for feature engineering, was this:
{question}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Metadata
{metadata}

Extracted Schema:
{schema}

Domain Hints, for researcher to come up with more thoughts:
* Evaluate each existing column for potential new feature, against each step.
* Given the goal, make sure you re-orient the dataset to patient_id from having multiple claims for each patient; do the needful as per your analysis.
* If the goal is to predict outcomes based on temporal events leading to a treatment, use the chronological sliding window approach.
* If the goal is to predict outcomes based on a comprehensive overview of patient data, use the aggregated approach. never aggregate to reduce rows but suggested to add more aggr columns 
* Use the metadata/schema to understand all the existing column for better analysis.

Update your plan accordingly. If the last run RESPONSE is correct and no more steps are needed and you can return last output to the user, for addressing the original question. 
Otherwise, fill out the new plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
    )

    replanner_chain = replanner_prompt | trimmer | llm.with_structured_output(Act)

    synthesize_prompt = ChatPromptTemplate.from_template(
        """As a world class ML Scientist/Researcher with expertise in healthcare data, for the given objective, come up with the final answer.
    Use the following pieces of retrieved answer from executed steps to consolidate and return the best response for the question.
    Do not omit any information. Do not make up any information, the final answer should be based on the provided context STRICTLY.

    Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach.
    If the information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.
    Ensure that your final response is in json format.

    The output should be a valid JSON object with the following structure:
    {{
        "dataset_description": Description of the dataset along with insights
        "task": Describe the complete understanding of the task including all the relevant information required to solve it
        "analysis": [
            {{
                "<statistical_analysis>": Detailed report of the analysis. Insights from the analysis and what are the learnings which a data scientist can use to perform the final goal of feature engineering. This could also include use of visualization and insight from that. It should not only be summary but suggestions deduced from it.
                "steps": [Steps List for the above analysis result]
            }},
            ...
        ]
    }}

    Note:
    * the overall goal is strictly data analysis, for the original question and context shared by user
    * make a calculated judgement on adding new analysis steps; refer the dataset and use-case to determine analysis steps

    =====
    Example:
    Question - Does this patient have ALK+ NSCLC?
    Response -
    {{
    "description": "This dataset comprises payer claims data, including patient demographics, diagnoses, drug information, and temporal details. It is used for predictive analysis to identify patients likely to have ALK+ NSCLC before treatment prescription.",
    "task": "The task is to engineer features from the claims data to build a Patient Predictor model that can identify ALK+ NSCLC patients based on their medical history, including diagnoses, comorbidities, and treatments.",
    "analysis": [
      {{
        "Missing Value Analysis": "Initial exploration showed missing values in columns such as `svc_dt` and `diagnosis_code_x`. We used forward fill and imputation strategies to address these gaps, ensuring the dataset is suitable for feature engineering.",
        "steps": [
          "Analyzed null values using `data.isnull().sum()`.",
          "Used `fillna()` and forward fill methods to fill gaps where applicable."
        ]
      }},
      {{
        "Demographic Distribution": "The distribution of patient ages and genders was reviewed, revealing a higher number of patients between the ages of 40 and 60. Female patients made up approximately 55% of the dataset.",
        "steps": [
          "Generated age distribution using `data['age'].hist()`.",
          "Calculated gender percentages using `data['gender'].value_counts(normalize=True)`."
        ]
      }},
      {{
        "Prescription and Label Analysis": "Approximately 15% of patients in the dataset had prescriptions for drugs like Alecensa, Xalkori, or Zykadia, indicating the potential proxy label for ALK+ NSCLC.",
        "steps": [
          "Filtered the `ndc_product_df` for the target drugs.",
          "Matched these drug codes with `synthetic_data_df` and counted occurrences."
        ]
      }},
      {{
        "Claim Count Distribution": "Claim counts varied widely, with an average of 8 claims per patient and a maximum of 50 claims for some patients. Higher claim counts were associated with older patients and those with chronic conditions.",
        "steps": [
          "Calculated claim counts using `data.groupby('patient_id').size()`.",
          "Analyzed distributions using `plt.hist(claim_counts)`."
        ]
      }},
      {{
        "Diagnosis Code Analysis": "Patients with more than 5 unique diagnosis codes often showed a higher likelihood of being prescribed the key drugs. This insight supports the use of diagnosis diversity as a predictive feature.",
        "steps": [
          "Aggregated diagnosis codes for each patient using `nunique()`.",
          "Correlated the count of diagnosis codes with `key_drug_flag` using `data.corr()`."
        ]
      }},
      {{
        "Temporal Trends": "Patients with a longer history (days since the first claim) were more likely to have complex medical profiles, as seen in data segments with `days_since_first_claim` > 1000.",
        "steps": [
          "Calculated the days since the first claim for each patient.",
          "Reviewed patient segments with extended histories using `data[data['days_since_first_claim'] > 1000]`."
        ]
      }},
      . . .
     ]

    ======
    Your objective was this:
    {question}

    You have currently done the follow steps:
    {past_steps}

    Data Analysis Response:
    {response}

    If some information is missing from the original query, or have some ambiguity; and could have been successful if provided, 
    please mention that as required information back to the user."""
    )

    synthesize_chain = synthesize_prompt | trimmer | chat_llm | StrOutputParser()

    def handle_agent_error(error):
        if isinstance(error, str):
            return {"error": error}
        return {"error": str(error)}

    @tool
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

    @tool
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
        df = [pd.read_csv(path) for path in state["data"]]
        task = plan[0]

        task_formatted = f"""You are tasked with executing step and share the analysis report - {task}. \n\n
Note: 
* Goal for feature engineering - {query}. Analysis should be across all the data and not just sample size.
* OUTCOME for each task is to leverage the analysis for some action towards feature engineering goal.
* MUST: Validate before sharing final analysis.
* Data (dataframe) is in memory and not supposed to be fetched from any file.
* For any syntax error, make sure to fix/modify to code and then try again.

=====
Metadata, for insight:
{metadata}
"""

        agent_max_iterations = 30
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
        hints = DOMAIN_HINTS
        additional_context = state["additional_context"]
        metadata = load_metadata(work_dir)
        schema = load_schema(work_dir)
        plan = await planner_chain.ainvoke({
            "messages": [
                ("user", query),  # User's message or query
                ("user", f"""\nAdditional Context:\n\n {additional_context}"""),
                ("user", f"""\nMetadata:\n\n {metadata}"""),
                ("assistant", f"""\nExtracted Schema:\n\n {schema}"""),
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
        """As a world class Data Scientist with expertise in healthcare data, for the given objective, come up with the final answer.
Use the following pieces of retrieved answer from data analysis step to decide whether we need labeling of the data or not.
Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach.
If the information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.

The output should be a valid JSON object with the following structure:
{{
    "instructions": Label instructions for having classes 
    "analysis": Analysis of data to justify the above labeling
    "code": Code to perform such label transformation in markdown ```...```
}}

Note: If labeling is not required, return empty instructions

=====
Example:
Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history (diagnoses, comorbidity, hospital/medical history, Rx, etc.).
* For label creation - Consider 'ndc_cd' or 'prev_ndc_cd' that starts with '69814120', '69814020', or '50242013001'.
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
{{
    "instructions": "The target variable (label) is whether the patient is ALK+ NSCLC positive. The label is determined by checking if a patient was prescribed any of the drugs 'ALECENSA', 'XALKORI', or 'ZYKADIA' (using 'ndc_cd' or 'prev_ndc_cd' starting with '69814120', '69814020', or '50242013001'), which corresponds to lung cancer diagnoses.",
    "analysis": "The new criteria for labeling directly link drug prescriptions for ALK-positive NSCLC treatment and corresponding diagnosis codes indicative of non-small cell lung cancer. Analysis of `synthetic_data_df` shows that patients meeting these criteria can be labeled as ALK+ NSCLC positive, ensuring accurate identification for model training.",
    "code": "synthetic_data_df['label'] = ((synthetic_data_df['ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001')) | synthetic_data_df['prev_ndc_cd'].astype(str).str.startswith(('69814120', '69814020', '50242013001')))"
}}


======
Your objective was this:
{question}

Additional Context:
{additional_context}

Data Analysis:
{data_analysis}

If some information is missing from the original query, or have some ambiguity; and could have been successful if provided, 
please mention that as required information back to the user."""
    )

    label_chain = label_prompt | trimmer | chat_llm | StrOutputParser()

    wrangling_prompt = ChatPromptTemplate.from_template(
        """As a world class Data Engineer with expertise in healthcare data, for the given objective, come up with the final answer.
Use the following pieces of retrieved answer from data analysis step to decide what preprocessing/wrangler is needed for preparing the dataset for the goal of feature engineering.
Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach.
If the information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.

The output should be a valid JSON object with the following structure:
  {{
    "instructions": Data wrangling/processing instructions 
    "analysis": Analysis of the original dataset backing the above instructions
    "code": Code to perform such instructed transformation in markdown ```...```
  }}

Note: The goal here is to provide instructions for preparing the dataset for feature engineering next.

=====
Example:
Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history (diagnoses, comorbidity, hospital/medical history, Rx, etc.).
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
{{
    "instructions": "Clean up missing values, ensure data types are consistent, preprocess date columns, and aggregate data to the patient level to summarize medical history.",
    "analysis": "Aggregating the data by `patient_id` helps summarize patients' entire medical history, which is critical for patient-level predictions. Analysis of the original dataset showed that data points related to claims (e.g., `claim_id`, `svc_dt`) are repeated for patients. Aggregating ensures that information like `claim_count` and diagnosis diversity is represented in one row per patient.",
    "code": "patient_level_df = synthetic_data_df.groupby('patient_id').agg({{\n    'age': 'first',\n    'gender': 'first',\n    'key_drug_flag': 'max',\n    'claim_count': 'sum',\n    'days_since_first_claim': 'max',\n    'diagnosis_code_count': 'max',\n    'comorbidity_flag': 'max',\n    'longitudinal_flag': 'first',\n    'first_claim_year': 'min',\n    'days_to_adjudicate': 'mean'\n}}).reset_index()"

}}

======
Your objective was this:
{question}

Additional Context:
{additional_context}

Data Analysis:
{data_analysis}

Labeling:
{labeling}

If some information is missing from the original query, or have some ambiguity; and could have been successful if provided, 
please mention that as required information back to the user."""
    )

    wrangling_chain = wrangling_prompt | trimmer | chat_llm | StrOutputParser()

    feature_engg_prompt = ChatPromptTemplate.from_template(
        """As a world class ML Engineer with expertise in healthcare data, for the given objective, come up with the final answer.
Use the following pieces of retrieved answer from data analysis step to decide what features is needed for preparing the dataset for the goal of feature engineering. Feel free to suggest any relevant features given the dataset 
Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach.
If the information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.

The output should be a valid JSON object with the following structure:
[
    {{
        "feature_name": Feature Name,
        "data_type": Data type like integer, string, etc.,
        "category": Suggested feature category, like demographic, temporal, diagnosis, etc.,
        "description": Description of the extracted feature,
        "range": Value range,
        “code”: Code to perform such instructed feature extraction,
        “useful_ness”: Provide statistical justification about the feature,
        “analysis”: Analysis of the original dataset backing the above instructions,
        “input_samples”: Example samples of such feature including inputs and generated output to create the feature,
    }}
    . . .
]


Note: 
* Make sure the distribution among different categories are covered in the suggested features
* MUST: Number of suggested feature categories should not be less than {feature_num}

=====
Example:
Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history (diagnoses, comorbidity, hospital/medical history, Rx, etc.).
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

Domain Hints, for coming up with feature ideas:
{hints}

If some information is missing from the original query, or have some ambiguity; and could have been successful if provided, 
please mention that as required information back to the user."""
    )

    feature_engg_chain = feature_engg_prompt | trimmer | chat_llm | StrOutputParser()

    scientist_prompt = ChatPromptTemplate.from_template(
        """As a world class ML Engineer with expertise in healthcare data, for the given objective, come up with the final answer.
Use the following pieces of retrieved analysis, wrangling and feature engineering results to decide the final list of detailed instructions as result. 
Make sure to remove ambiguity/generalization and convert into specific answer with data driven approach.
If the information is not available in the context or cannot be deduced directly from it, clearly state that you don't know.

The output should be a valid JSON object with the following structure:
  [
    {{
        "instructions": Detailed list of instructions, providing information about the dataset, goal for the task.
        "analysis: Analysis of the original dataset backing the above instructions and usefulness of the features in this instruction set
        "code": Code to perform such instructed feature extraction, in markdown ```...```
        "category": Combined feature category, like demographic, temporal, diagnosis, etc.,
    }},
    ...
  ]

Note: 
* MUST: Number of suggested features should not be less than {feature_num}, mapping to the feature_engineering output list.
* Combine instructions from labeling, wrangling and feature engineering as batch instructions, for each suggested feature.
* Make sure the distribution among different categories are covered in the suggested features.
* For each entry in the feature_engineering results list, have a corresponding item in this final list, grouped by category.
* Each instruction set, in the final list, should include preprocessing/cleaning as prefix steps before actual feature extraction.

=====
Example:
Question - Does this patient have ALK+ NSCLC?
Addition Context - 
* This is a payer claims data with patient information, diagnoses, and drug details. The drugs 'ALECENSA', 'XALKORI', and 'ZYKADIA' are for treating adult patients with ALK-positive metastatic non-small cell lung cancer(NSCLC).
* For this, use the input payer claims data to build patient attributes by looking at patients’ medical history (diagnoses, comorbidity, hospital/medical history, Rx, etc.).
* The goal is to extract features for building a Patient Predictor model to identify ALK+ NSCLC patients prior to treatment being prescribed.
Response -
[
    {{
        "instructions": 
          - This is a time-series healthcare data. Your task is to transform the claims data to a longitudinal patient-level data.
          - Sort the data by patient ID and ‘service_from_date’ to establish the correct temporal sequence.
          - Apply transformation logic to convert claims information into structured patient-level data.
          - Standardize the data format to ensure consistency across all records. - Calculate  time_since_last_service, cumulative_days_supply, cumulative_quantity, cumulative_svc_bill_amt, service_month , treatment_gap
          - Ensure to retain all the input columns and rows along with the task output columns.
        "analysis": Time-based aggregation and event sequences → 1. Rolling aggregation of data (e.g., last 30 days, 6 months) 2. Event sequence encoding. 3. Trends over time in diagnoses and drug claims 4. Clinical relevance of event ordering
        "category": "temporal"
        "code": ```...```
    }},
    {{
        "instructions": 
          - Your task is to analyze the longitudinal journey of patients based on drug claims, diagnoses, and procedures.
          - The input has been sorted by patient ID and ‘service_from_date’ to establish the correct temporal sequence. Take care to keep this information.
          - Map the 'procedure_code' with the file 2 to find the procedure mapping.
          - Identify which claims correspond to primary care visits, specialist consultations, and hospitalizations. Look into procedure_code, claim_type, service_nbr, and diagnosis_code to categorize the type of visit.
          - Track the sequence of provider interactions, including primary care visits, specialist consultations, and hospitalizations over time.
          - Replace 'nan' values with 0 during data cleaning. Ensure to retain all the input rows and columns along with the task output columns.
          - Ensure to group the interactions in chronological order.
        "analysis": Provider Interaction and Patient Journey - mapping with external procedure file
        "category": "treatment"
        "code": ```...```
    }},
    . . .
]

======
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

Feature Engineering:
{feature_engineering}


If some information is missing from the original query, or have some ambiguity; and could have been successful if provided, 
please mention that as required information back to the user."""
    )

    scientist_chain = scientist_prompt | trimmer | chat_llm | StrOutputParser()

    workflow = StateGraph(PlanExecute)

    # Add the plan node
    workflow.add_node("researcher", plan_step)

    # Add the execution step
    workflow.add_node("analyst", execute_step)

    # Add a replan node
    workflow.add_node("again_researcher", replan_step)

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
    workflow.add_edge("analyst", "again_researcher")

    workflow.add_conditional_edges(
        "again_researcher",
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
