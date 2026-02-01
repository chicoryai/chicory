# prompt hints for Rice and Genentech for feature engineering

def load_prompts(project):

    prompts = {}

    if (project) == "rice":

      domain_hints = """
    * A sequence of telemetry events, with each file capturing a different subsystem or aspect of the overall operation. 
    * Each file represents a subset of variables, capturing different dimensions of the data while maintaining consistency across records.  
    * Assess each existing column for potential new features in every step.
    * Ensure to use a time-based sequence modeling approach rather than treating data as independent rows.
    * Ensure that the dataset remains aligned by timestamp to maintain event chronology and prevent data leakage.
    * For outcome prediction based on temporal events, apply a chronological sliding window approach.
    * Leverage sliding window analysis to extract short-term and long-term trends that may influence AFM mode prediction.
    * In log_mc_fsw_sm_afm.csv, Column 5 appears to be the "AFM mode" - a discrete value indicating the operational mode of the system. Ensure AFM Mode is Treated as the Target Variable
    * Timestamp values (usually col2) that mark the precise time of each data point
    * Sequential indices (col1) that increment with each record
    * Synchronized collection across subsystems, allowing for correlation of events. 

    * Recommendation: For temporal/longitudinal datasets, focus on creating features that capture:
    - Time-Based Patterns: Compute the time between successive events to detect pacing irregularities or delays.
    - Merging all the files on column 1, it is important to ensure that the timestamp is aligned correctly.
    - Event Transition Analysis: Identify sequential changes in sensor readings that correlate with AFM mode shifts. Transitions through a sequence of operational modes (1, 2, 4, 5, 8, 9)
    - Cumulatve Metrics: Track cumulative sums, averages, and deviations over time for critical variables.
    - Lag Features: Use historical values as predictors (e.g., sensor readings at previous time steps).
    - Rolling Window Features: Compute rolling means, standard deviations, and trends over different time windows.
    - Spike and Anomaly Detection: Capture sudden changes in telemetry readings that may indicate shifts in AFM mode.


    * Practical Steps to Prevent Leakage and Use Anchor Dates:
    - Define Anchor Timestamps: Choose or create a reference timestamp for each record to avoid using future data.
    - Preprocess Data in a Time-Ordered Manner: When generating features, only use data available up to the given timestamp.
    - Avoid Future Data: Ensure that any columns or derived features that use data beyond the anchor date are excluded during the feature engineering process.

    """
      feature_hints = """
  * Combined Feature Engineering Tips for Temporal and Non-Temporal Data:
  * Feature Selection: Use statistical methods (e.g., correlation, mutual information) to identify and remove redundant or less informative features.
  * Rolling and Window-Based Features: Compute rolling averages and standard deviations of sensor readings over short (e.g., 5-step) and long (e.g., 50-step) windows to capture dynamic system changes.
  * Event-Based Features: Track the time since critical events, such as mode changes, thrust activations, or control adjustments, to detect dependencies in system behavior.
  * Cumulative and Aggregated Features: Maintain running sums, means, and counts of key telemetry parameters to assess system performance over time.
  * Statistical Features: Calculate standard deviation, variance, and skewness for control, propulsion, and navigation parameters to quantify system stability.
  * Categorical Feature Engineering: If necessary, perform One-hot encode discrete AFM modes and categorical control states for better predictive modeling.
  * Ratio and Group Features: Create ratios like thrust-to-weight, control-effort-to-mode-duration, or fuel-consumption-to-time to derive system efficiency metrics.
  * Outlier Treatment: Identify and handle extreme values in sensor readings, which may indicate system faults or incorrect telemetry data.
  * Trend and Decay Features: Capture exponential moving averages or decaying trends to give higher weight to recent system behavior.
  * Temporal Aggregation and Hierarchies: Wherever necessary, perform aggregation of telemetry data by operational phases (e.g., flight phases, maneuver execution) rather than static time bins.

  * Sample code 
  ```
  import pandas as pd
  import numpy as np

  # read afm data
  data = pd.read_csv("data_afm.csv")

  # Ensure timestamp column is in the correct format
  data['timestamp'] = pd.to_datetime(data['col2'], unit='s')

  # Sort the data by timestamp to preserve chronological order
  data = data.sort_values(by='timestamp')

  # Convert AFM mode (col5) to a categorical variable
  data['AFM_mode'] = data['col5'].astype('category')

  * Sample code temporal data: Temporal Feature Engineering

  # Rolling Window Features for key telemetry signals (adjust columns as needed)
  window_size = 5  # Define the rolling window size
  data['rolling_mean_col3'] = data['col3'].rolling(window=window_size, min_periods=1).mean()
  data['rolling_std_col3'] = data['col3'].rolling(window=window_size, min_periods=1).std()

  # Lag Features
  data['lag_1_col3'] = data['col3'].shift(1)  # Previous timestep value
  data['lag_2_col3'] = data['col3'].shift(2)  # Two steps before
  data['lag_1_AFM_mode'] = data['AFM_mode'].shift(1)  # Previous AFM mode
  data['lag_2_AFM_mode'] = data['AFM_mode'].shift(2)  # AFM mode two steps before

  # Rate of Change Features (Capturing system dynamics)
  data['rate_of_change_col3'] = data['col3'].diff()  # First derivative (velocity-like)
  data['acceleration_col3'] = data['rate_of_change_col3'].diff()  # Second derivative (acceleration-like)
  data['rate_of_change_col6'] = data['col6'].diff()  # Another key parameter for propulsion/control

  # Time Since Last AFM Mode Change
  data['time_since_last_mode_change'] = data['timestamp'].diff().dt.total_seconds().fillna(0)

  # Cumulative Features (Tracking total system behavior over time)
  data['cumulative_col3'] = data['col3'].cumsum()
  data['cumulative_col6'] = data['col6'].cumsum()

  # Detecting AFM Mode Stability (Checking how long system stays in one mode)
  data['mode_stability'] = data.groupby('AFM_mode')['timestamp'].diff().dt.total_seconds().fillna(0)

  ```
  """
      planner_prompt_template = """ 
  As a world-class ML Scientist/Researcher with expertise in aerospace telemetry and flight control data, your objective is to develop a detailed, step-by-step analysis and feature engineering plan for Attitude and Flight Mode (AFM) prediction using the given telemetry dataset.
  The goal is to extract, transform, and engineer features that capture temporal relationships, and non-trivial correlations in telemetry data. 
  The final objective is to enable accurate predictions of AFM mode transitions.
  Perform tasks to gain insights about the dataset to make preprocessing and feature engineering decisions. 
  This plan should cover individual tasks strictly within the scope of data analysis, ensuring that, if executed correctly, they yield a thorough understanding of the dataset and final insights. 
  Ensure each step is self-contained with all necessary information and avoid skipping steps.

  **Note:**
  * Include analysis action hints for analysts to refer to; be as detailed as possible.
  * Do not include steps to perform data transformations or feature engineering.
  * The overall goal is strictly data analysis for the given question and context.
  * MUST: Conduct (statistical) visualization analysis for each step, if applicable. Extract learnings from every analysis.
  * MUST: Filter irrelevant columns for any analysis.
  * MUST: Summarize and describe every field, including data types, allowed values, and potential connections with other fields.
  * MUST: Investigate and handle missing values, ensuring data cleanup is mentioned where necessary.
  * MUST: Propose feature suggestions, including discrete features, temporal features, and sequence features.
  * MUST: Identify suitable methods of encoding for features, such as one-hot encoding, binary encoding, and n-gram encoding, and suggest when applicable.
  * MUST: Stop replanning after 3 replans unless a critical step is still missing.

  =====
  **Example Analysis Plan:**

  Question -  What are the key features that can be used to predict AFM mode?
  Plan -
  * Step 1: Label requirement analysis: Verify if AFM mode (col5) is correctly recorded as the target label for prediction.Identify all possible AFM mode transitions through a sequence of operational modes (1, 2, 4, 5, 8, 9) and their frequency. Generate a transition matrix to analyze the probability of switching between modes
  * Step 2: Field Description and Summary Analysis: Review each field in the dataset, documenting the data type, allowed values, and potential connections with other fields. Identify key columns for further analysis. Use `data.info()` and `data.describe()` to gather an overview.
  * Step 4: Multi-File Merging & Data Synchronization: Merge all telemetry files on col1, align timestamps across subsystems, and remove duplicates or misaligned records.
  * Step 3: Missing Value Analysis and Data Cleanup: Investigate missing data in every column using `data.isnull().sum()`. Create a heatmap with `sns.heatmap(data.isnull(), cbar=False)` to visualize missing patterns.
  * Step 5: Temporal Event Analysis: Compute time since last AFM mode change, analyze AFM transition frequency, and detect anomalous mode shifts using time-series plots.
  * Step 6: Feature Encoding Strategy Identification: Encode AFM mode as categorical, normalize telemetry values, and create binary flags for AFM transitions.
  * Step 7: Rolling and Window-Based Feature Analysis: Compute rolling mean, standard deviation, and cumulative metrics for thrust, control effort, and key telemetry signals.
  * Step 8: Event-Based & Anomaly Detection Features: Identify outliers in telemetry data, detect sudden propulsion or control spikes, and apply Z-score-based anomaly detection.
  * Step 9: Feature Selection and Correlation Analysis: Generate correlation matrices, and remove redundant features to prevent multicollinearity.
  * . . . <more steps to ensure insights into the dataset for preprocessing and feature engineering decisions>
  """
      replanner_prompt_template = """As a world-class ML Scientist/Researcher with expertise in aerospace telemetry and flight control data, for the given objective, validate the response from the previous steps run. 
      Your goal is to provide a thorough analysis of the tasks and the dataset. Execute each step, validate the response of the last run, and modify the steps as needed to proceed to the next task, to reach a complete, actionable understanding of the dataset for preprocessing and feature engineering.
      Create a minimal, complete plan to guide analysts in understanding the dataset for feature engineering. Avoid loops or unnecessary refinements once the insights are sufficient.
      Provide a thorough analysis of the tasks and the dataset. Do not include any superfluous steps. 
      Execute each step, and ONLY modify the plan if the response was incomplete or inaccurate. Avoid making changes unless strictly necessary.
      Ensure the final step yields a satisfactory and complete answer, sufficient for making preprocessing and feature engineering decisions. Avoid further steps once that is achieved.
      Ensure each step has all the necessary details and avoid skipping any essential information.
      Before generating a new plan, check if a similar step already exists in `past_steps`. 
      Only add new steps if they cover *unexplored columns, missing evaluations, or clearly incomplete analyses*.
      
  **Constraints:**
  - Max 10 total steps across current and 'past_steps' for planning + replanning
  - Each step must be actionable, unique, and relevant, 
  - Ensure coverage of every column attribute across these steps.

  **Note:**
  * Each step will be assigned to an executor agent to perform analysis on, so be as descriptive as possible.
  * Include detailed analysis action hints for the analyst.
  * Do not include steps to perform data transformations or feature engineering.
  * Focus strictly on data analysis for the provided question/context.
  * MUST: Conduct (statistical) visualization analysis for each applicable step.
  * MUST: Evaluate each existing column for its potential as a new feature and suggest any needed reorientation for feature extraction.
  * MUST: Summarize each field, including data type, allowed values, and potential connections to other fields.
  * MUST: Investigate and handle missing values, ensuring data cleanup suggestions are mentioned where necessary.
  * MUST: Propose potential discrete, temporal, and sequence features.
  * MUST: Identify and suggest appropriate methods for encoding features (e.g., one-hot, binary, n-gram).

  =====
  **Example Analysis Plan:**

  Question - What are the key features that can be used to predict AFM mode?
  Past Steps - [Step 1: Label Requirement Analysis: Validate if col5 represents AFM mode and identify transition states, Step 2: Field Description and Summary Analysis: Review dataset structure, column descriptions, and identify key telemetry features for AFM prediction.]
  Response Plan -
  * Step 3: Missing Value Analysis and Data Cleanup: Investigate missing data in every column using `data.isnull().sum()`. Create a heatmap with `sns.heatmap(data.isnull(), cbar=False)` to visualize missing patterns.
  * Step 4: Multi-File Merging & Data Synchronization: Merge all telemetry files on col1, align timestamps across subsystems, and remove duplicates or misaligned records.
  * Step 5: Temporal Event Analysis: Compute time since last AFM mode change, analyze AFM transition frequency, and detect anomalous mode shifts using time-series plots.
  * Step 6: Feature Encoding Strategy Identification: Encode AFM mode as categorical, normalize telemetry values, and create binary flags for AFM transitions.
  * Step 7: Rolling and Window-Based Feature Analysis: Compute rolling mean, standard deviation, and cumulative metrics for thrust, control effort, and key telemetry signals.
  * Step 8: Event-Based & Anomaly Detection Features: Identify outliers in telemetry data, detect sudden propulsion or control spikes, and apply Z-score-based anomaly detection.
  * Step 9: Feature Selection and Correlation Analysis: Generate correlation matrices, and remove redundant features to prevent multicollinearity.
  * . . . <more steps to ensure insights into the dataset for preprocessing and feature engineering decisions>

  Question - What are the key features that can be used to predict AFM mode?
  Past Steps -  [Step 1: Missing value analysis, Step 2: Field Description and Summary Analysis, Step 3: Multi-File Merging & Data Synchronization, Step 4: Temporal Event Analysis, Step 5: AFM Mode Transition Patterns]
  Response Plan -
  This dataset comprises telemetry data from aerospace flight control systems, including attitude, propulsion, navigation, control, and guidance subsystems. It is used for predictive analysis to determine AFM mode transitions based on system behavior and telemetry readings.
  The task is to engineer features from the telemetry data to build an AFM Mode Predictor, identifying patterns in mode transitions, control responses, propulsion adjustments, and navigation stability to anticipate the system’s next operational state.
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


  Extracted Schema:
  {schema}

  Update your plan accordingly. If the last run RESPONSE is correct and no more steps are needed and you can return last output to the user, for addressing the original question. 
  Otherwise, fill out the new plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
      synthesize_prompt_template = """As a world-class ML Scientist/Researcher with expertise in aerospace telemetry and flight control data, consolidate all the analysis results for the given objective using the provided pieces of retrieved answers from executed steps. Ensure that the response strictly reflects the provided context without omitting any information or adding unsubstantiated content.
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
  Question -  What are the key features that can be used to predict AFM mode?
  Response - 

  {{ 
      
      "description": "This dataset consists of telemetry data from aerospace flight control systems, including attitude, propulsion, navigation, control, and guidance subsystems. It is used for predictive analysis to determine AFM mode transitions based on system behavior and telemetry readings.",
      "task": "The objective is to engineer features from the telemetry dataset to build an AFM Mode Predictor, identifying patterns in mode transitions, control responses, propulsion adjustments, and navigation stability to anticipate the system’s next operational state.",
      "analysis": [
              {{
                  "Missing Value Analysis": "Initial exploration identified missing values in telemetry parameters such as propulsion thrust and control effort. These gaps may impact AFM mode transition predictions, so interpolation and imputation strategies were applied.",
                  "recommended_features": [],
                  "steps": [
                      {{
                          "description": "Analyzed null values in the dataset to understand missing data distribution",
                          "code": "data.isnull().sum()",
                          "sample_result": "col6 (propulsion thrust): 120 nulls, col8 (control effort): 85 nulls"
                      }},
                      {{
                          "description": "Applied forward fill and linear interpolation to impute missing values",
                          "code": "data['col6'].interpolate(method='linear', inplace=True)",
                          "sample_result": "Nulls in propulsion thrust reduced to 0"
                      }}
                  ]
              }},
              {{
                  "AFM Mode Transition Analysis": "Examined mode transitions over time, identifying instances of rapid mode switching and stable periods. Time spent in each AFM mode was computed as a feature.Transitions through is usually a sequence of operational modes (1, 2, 4, 5, 8, 9)",
                  "recommended_features": ["mode_duration", "transition_count", "stability_flag"],
                  "steps": [
                      {{
                          "description": "Computed the duration spent in each AFM mode",
                          "code": "data['mode_duration'] = data.groupby('AFM_mode')['timestamp'].diff().dt.total_seconds().fillna(0)",
                          "sample_result": "Mode 1 duration: 240s, Mode 4 duration: 120s"
                      }},
                      {{
                          "description": "Created a flag for rapid AFM mode transitions",
                          "code": "data['transition_flag'] = (data['AFM_mode'] != data['AFM_mode'].shift(1)).astype(int)",
                          "sample_result": "Transition flag set for 30% of entries"
                      }}
                  ]
              }}
              {{
                  "Rolling Window & Lag Features": "To capture dynamic changes leading up to AFM transitions, rolling mean and lag features were generated for key telemetry variables.",
                  "recommended_features": ["rolling_mean_thrust", "lag_1_control_effort", "lag_2_navigation_error"],
                  "steps": [
                      {{
                          "description": "Computed rolling mean for propulsion thrust",
                          "code": "data['rolling_mean_thrust'] = data['col6'].rolling(window=5, min_periods=1).mean()",
                          "sample_result": "Rolling mean fluctuates before AFM mode transitions"
                      }},
                      {{
                          "description": "Created a lag feature for control effort",
                          "code": "data['lag_1_control_effort'] = data['col8'].shift(1)",
                          "sample_result": "Lagged control effort provides predictive signals before transitions"
                      }}
                  ]
              }},
          ],
          "suggested_approach": [
              "Data Preparation: Merge subsystem telemetry data on column 1, handle missing values, and align timestamps.",
              "Label Creation: Use AFM mode (`col5`) as the target label, encoding it for predictive modeling.",
              "Temporal Features: Compute mode duration, transition counts, and create event-based timestamps.",
              "Rolling Window Features: Use rolling statistics to analyze gradual state changes in the system.",
              "Cumulative Features: Generate cumulative propulsion thrust and control effort metrics.",
              "Anomaly Detection: Identify telemetry spikes and sudden parameter shifts that precede mode changes.",
              "Feature Selection: Apply correlation analysis and SHAP feature importance ranking.",
              "Analysis and Iteration: Perform exploratory analysis, refine features based on insights, and optimize model performance."
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
      label_prompt_template = """As a world-class Data Scientist with expertise in aerospace telemetry and flight control data, determine what data labeling is required for the given objective. 
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
  Question -  What are the key features that can be used to predict AFM mode?

  Addition Context - 
  * This dataset consists of aerospace telemetry data capturing subsystems such as attitude, propulsion, navigation, control, and guidance.
  * The AFM mode (col5) represents the system's operational state, transitioning between different flight modes. Transitions is usually through a sequence of operational modes (1, 2, 4, 5, 8, 9). Merging all the input files on column 1 since the input files represents a subset of variables, capturing different dimensions of the data while maintaining consistency across records.
  * The goal is to use the telemetry data to extract relevant features for building an AFM Mode Predictor, enabling early detection of mode transitions and improving flight system stability.
  * The telemetry shows a system that - initializes in a base state (AFM mode 0), transitions through a sequence of operational modes (1, 2, 4, 5, 8, 9), maintains specific modes for extended periods, has synchronized subsystems (control, propulsion, navigation, etc.) that work together, and exhibits both discrete mode changes and continuous parameter adjustments.

  Response -
  {{
      "instructions": "Label the dataset with a target variable representing AFM mode transitions. This label should be based on changes in 'col5' (AFM mode). Identify instances where mode transitions occur and create a binary indicator flag for state changes. Transitions is usually through a sequence of operational modes (1, 2, 4, 5, 8, 9)",
      "analysis": "The analysis of telemetry data confirms that AFM mode transitions correspond to variations in propulsion, control, and navigation signals. Labeling these transitions helps in understanding system behavior and developing predictive models for AFM mode forecasting.",
      "code": "data['AFM_transition_flag'] = (data['col5'] != data['col5'].shift(1)).astype(int)"
  }}


  ======
  **Context**
  Your objective was this:
  {question}

  Additional Context:
  {additional_context}

  Data Analysis:
  {data_analysis}

  Extracted Schema:
  {schema}

  If information is missing or ambiguous, mention what additional data would be needed for successful labeling."""
      wrangling_prompt_template = """As a world-class Data Engineer with expertise in aerospace telemetry and flight control data, determine the necessary preprocessing/wrangling steps required to prepare the dataset for feature engineering based on the data analysis provided. Ensure the answer is specific and data-driven, removing any ambiguity or generalizations. If information is not available or cannot be directly deduced from the context, clearly state that you don't know.

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
  Question -  What are the key features that can be used to predict AFM mode?
  Addition Context - 
  * This dataset consists of aerospace telemetry data capturing subsystems such as attitude, propulsion, navigation, control, and guidance.
  * The AFM mode (col5) represents the system's operational state, transitioning between different flight modes. Transitions is usually through a sequence of operational modes (1, 2, 4, 5, 8, 9). Merging all the input files on column 1 since the input files represents a subset of variables, capturing different dimensions of the data while maintaining consistency across records.
  * The goal is to use the telemetry data to extract relevant features for building an AFM Mode Predictor, enabling early detection of mode transitions and improving flight system stability.
  * The telemetry shows a system that - initializes in a base state (AFM mode 0), transitions through a sequence of operational modes (1, 2, 4, 5, 8, 9), maintains specific modes for extended periods, has synchronized subsystems (control, propulsion, navigation, etc.) that work together, and exhibits both discrete mode changes and continuous parameter adjustments.

  Response -
  {{
      "instructions": "Handle missing values, ensure consistent data types, preprocess timestamp columns, and merge telemetry logs to provide a consolidated view of system behavior across different subsystems.",
      "analysis": "The original telemetry dataset consists of multiple logs capturing different subsystems (e.g., propulsion, navigation, control). Merging all files on 'col1' (record index) is essential for aligning time-series data and ensuring a unified representation of system states and transitions.",
      "code": "merged_telemetry_df = dfs['log_mc_fsw_sm_afm.csv']\nfor file, df in dfs.items():\nif file != 'log_mc_fsw_sm_afm.csv':\nmerged_telemetry_df = merged_telemetry_df.merge(df, on='col1', how='left')\n\nmerged_telemetry_df['timestamp'] = pd.to_datetime(merged_telemetry_df['col2'], unit='s')"
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


  Extracted Schema:
  {schema}

  If information is missing or ambiguous, mention what additional data would be needed for successful labeling."""
      feature_engg_prompt_template = """As a world-class ML Engineer with expertise in aerospace telemetry and flight control data, determine the features required for preparing the dataset for feature engineering based on the provided data analysis. Suggest relevant features given the dataset context and ensure your answer is specific and data-driven. If information is not available or cannot be directly deduced from the context, clearly state that you don't know.

  The output should be a valid JSON array with the following structure:
  [
      {{
          "feature_name": Feature Name,
          "data_type": Data type like integer, string, etc.,
          "category": Feature category, like temporal,rolling-window, cumulative, etc.,
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

  Question -  What are the key features that can be used to predict AFM mode?
  Addition Context - 
  * This dataset consists of aerospace telemetry data capturing subsystems such as attitude, propulsion, navigation, control, and guidance.
  * The AFM mode (col5) represents the system's operational state, transitioning between different flight modes. Transitions is usually through a sequence of operational modes (1, 2, 4, 5, 8, 9). Merging all the input files on column 1 since the input files represents a subset of variables, capturing different dimensions of the data while maintaining consistency across records.
  * The goal is to use the telemetry data to extract relevant features for building an AFM Mode Predictor, enabling early detection of mode transitions and improving flight system stability.
  * The telemetry shows a system that - initializes in a base state (AFM mode 0), transitions through a sequence of operational modes (1, 2, 4, 5, 8, 9), maintains specific modes for extended periods, has synchronized subsystems (control, propulsion, navigation, etc.) that work together, and exhibits both discrete mode changes and continuous parameter adjustments.

  Response -
  [
      {{
        "feature_name": "AFM Mode Transition Flag",
        "data_type": "binary",
        "category": "event-based",
        "description": "Binary flag indicating whether an AFM mode transition occurred between consecutive time steps.",
        "range": "0 or 1",
        "code": "merged_telemetry_df['AFM_transition_flag'] = (merged_telemetry_df['col5'] != merged_telemetry_df['col5'].shift(1)).astype(int)",
        "usefulness": "High. Capturing AFM mode transitions allows the model to detect system state shifts and predict upcoming changes. This feature is critical for understanding how telemetry values influence mode changes.",
        "analysis": "Analysis of the AFM mode column revealed frequent transitions between operational states, with propulsion and control signals fluctuating before mode shifts.",
        "input_samples": "[0, 0, 1, 0, 1, 0]"
      }},
      {{
        "feature_name": "Time Since Last AFM Mode Change",
        "data_type": "float",
        "category": "temporal",
        "description": "Computes the time elapsed since the last AFM mode transition.",
        "range": "0 - max time in dataset",
        "code": "merged_telemetry_df['time_since_last_mode_change'] = merged_telemetry_df.groupby('AFM_mode')['timestamp'].diff().dt.total_seconds().fillna(0)",
        "usefulness": "High. This feature helps differentiate between stable and transient system states, enabling the prediction of future mode changes.",
        "analysis": "Time-series analysis showed that mode stability durations vary significantly. Periods of prolonged stability often precede abrupt transitions, making this a useful feature.",
        "input_samples": "[0, 5, 10, 120, 240]"
      }},
      {{
        "feature_name": "Rolling Mean of Control Effort",
        "data_type": "float",
        "category": "rolling-window",
        "description": "Rolling mean of control effort over a defined time window to smooth out fluctuations and capture trends.",
        "range": "Continuous values",
        "code": "merged_telemetry_df['rolling_mean_control'] = merged_telemetry_df['col8'].rolling(window=5, min_periods=1).mean()",
        "usefulness": "Medium. By smoothing control effort variations, the feature reduces noise and enhances the model’s ability to detect meaningful trends leading to AFM transitions.",
        "analysis": "Exploratory data analysis showed that sudden control effort changes correlate with AFM mode transitions, making rolling mean a useful predictive feature.",
        "input_samples": "[10, 15, 15, 18.75, 20, 26]"
      }},
      {{
        "feature_name": "Cumulative Sum of Propulsion Thrust",
        "data_type": "float",
        "category": "cumulative",
        "description": "Computes cumulative propulsion thrust over time to track total thrust applied.",
        "range": "0 - max cumulative thrust",
        "code": "merged_telemetry_df['cumulative_thrust'] = merged_telemetry_df['col6'].cumsum()",
        "usefulness": "Medium. Tracking cumulative thrust provides insight into the system’s energy expenditure and its impact on mode transitions.",
        "analysis": "Analysis showed that propulsion thrust accumulation is a key factor in triggering specific AFM modes, making it a valuable predictive feature.",
        "input_samples": "[5, 15, 30, 50, 75, 100]"
      }}
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


  Extracted Schema:
  {schema}

  Domain Hints, for coming up with feature ideas:
  {hints}

  If information is missing or ambiguous, mention what additional data would be needed for successful labeling."""
      scientist_prompt_template = """As a world-class ML Engineer with expertise in aerospace telemetry and flight control data, consolidate the final list of detailed step-by-step instructions based on the provided analysis, wrangling, and feature engineering results. 
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
          "category": "Feature category (e.g. temporal, cumulative, rolling-window  etc.).",
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

  Question -  What are the key features that can be used to predict AFM mode?
  Addition Context - 
  * This dataset consists of aerospace telemetry data capturing subsystems such as attitude, propulsion, navigation, control, and guidance.
  * The AFM mode (col5) represents the system's operational state, transitioning between different flight modes. Transitions is usually through a sequence of operational modes (1, 2, 4, 5, 8, 9). Merging all the input files on column 1 since the input files represents a subset of variables, capturing different dimensions of the data while maintaining consistency across records.
  * The goal is to use the telemetry data to extract relevant features for building an AFM Mode Predictor, enabling early detection of mode transitions and improving flight system stability.
  * The telemetry shows a system that - initializes in a base state (AFM mode 0), transitions through a sequence of operational modes (1, 2, 4, 5, 8, 9), maintains specific modes for extended periods, has synchronized subsystems (control, propulsion, navigation, etc.) that work together, and exhibits both discrete mode changes and continuous parameter adjustments.

  Response -
  ```json
  [
      {{
          "description": "This dataset comprises telemetry data from aerospace flight control systems, capturing subsystems such as propulsion, navigation, control, and attitude. It is used to predict AFM mode transitions based on system behavior and sensor readings.",
          "task": "The objective is to engineer features from the telemetry dataset to build an AFM Mode Predictor, identifying patterns in mode transitions, control responses, propulsion adjustments, and navigation stability.",
          "details": "This is a time-series telemetry dataset. Your task is to preprocess and extract relevant time-based features that can predict AFM mode changes.",
          "labeling_instructions": "Label the data by tracking changes in `col5` (AFM mode) and creating an indicator for AFM mode transitions.",
          "preprocessing_instructions": 
              "- Load the telemetry dataset."
              "- Merge all telemetry logs or files using `col1` to create a unified dataset."
              "- Convert `col2` (timestamp) to datetime format and ensure chronological sorting."
              "- Handle missing values by applying forward fill for time-series continuity and replacing 'nan' values with 0 for numerical columns.",
          "feature_instructions": 
              "- Create the `AFM_transition_flag` by comparing consecutive AFM mode values (`col5`).",
          "analysis": "Analysis of AFM mode transitions showed that certain propulsion and control patterns precede state changes. Identifying these transition points helps in predicting system behavior.",
          "code": "```python\n# Load and preprocess the telemetry data\nmerged_telemetry_df['timestamp'] = pd.to_datetime(merged_telemetry_df['col2'], unit='s')\nmerged_telemetry_df.sort_values(by='timestamp', inplace=True)\nmerged_telemetry_df.fillna(method='ffill', inplace=True)\nmerged_telemetry_df.fillna(0, inplace=True)\n\n# Feature extraction: AFM Mode Transition Flag\nmerged_telemetry_df['AFM_transition_flag'] = (merged_telemetry_df['col5'] != merged_telemetry_df['col5'].shift(1)).astype(int)\n```",
          "category": "event-based",
          "features": ["AFM_transition_flag"]
      }},
      {{
          "description": "This dataset comprises telemetry data from aerospace flight control systems, capturing subsystems such as propulsion, navigation, control, and attitude. It is used to predict AFM mode transitions based on system behavior and sensor readings.",
          "task": "The objective is to engineer features from the telemetry dataset to build an AFM Mode Predictor, identifying patterns in mode transitions, control responses, propulsion adjustments, and navigation stability.",
          "details": "This is a time-series telemetry dataset. Your task is to preprocess and extract relevant time-based features that can predict AFM mode changes.",
          "labeling_instructions": "Label the data by tracking changes in `col5` (AFM mode) and computing the time elapsed since the last mode change.",
          "preprocessing_instructions": 
              "- Load the telemetry dataset."
                  "- Merge all telemetry logs using `col1` to create a unified dataset.\n"
              "- Convert `col2` (timestamp) to datetime format and ensure chronological sorting.\n"
              "- Handle missing values by applying forward fill for time-series continuity and replacing 'nan' values with 0 for numerical columns.",
          "feature_instructions": 
              "- Compute `time_since_last_mode_change` by calculating the difference in timestamps between consecutive AFM mode changes.",
          "analysis": "Analysis of AFM mode durations showed that stability periods vary significantly across different flight states. Capturing this feature helps in modeling both steady-state and transient behaviors.",
          "code": "```python\n# Load and preprocess the telemetry data\nmerged_telemetry_df['timestamp'] = pd.to_datetime(merged_telemetry_df['col2'], unit='s')\nmerged_telemetry_df.sort_values(by='timestamp', inplace=True)\nmerged_telemetry_df.fillna(method='ffill', inplace=True)\nmerged_telemetry_df.fillna(0, inplace=True)\n\n# Feature extraction: Time Since Last AFM Mode Change\nmerged_telemetry_df['time_since_last_mode_change'] = merged_telemetry_df.groupby('AFM_mode')['timestamp'].diff().dt.total_seconds().fillna(0)\n```",
          "category": "temporal",
          "features": ["time_since_last_mode_change"]
      }},
  ]

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


  Extracted Schema:
  {schema}

  If any required information is missing from the context or there is ambiguity that needs to be addressed for a successful response, clearly state this in your feedback."""

    elif (project) == "genentech":

      domain_hints = """
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
      feature_hints = """
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


"""
      planner_prompt_template = """As a world-class ML Scientist/Researcher with expertise in healthcare data, for the given objective, come up with a detailed, step-by-step analysis plan and provide comprehensive learnings for extracting/transforming features from the given dataset.
The goal of the tasks/steps is to gain insights about the dataset to make preprocessing and feature engineering decisions. This plan should cover individual tasks strictly within the scope of data analysis, ensuring that, if executed correctly, they yield a thorough understanding of the dataset and final insights. Ensure each step is self-contained with all necessary information and avoid skipping steps.

**Note:**
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
* Step 1: Label requirement analysis: Check if the target class label (ALK+ NSCLC) exists within the dataset or if it can be derived. Identify relevant columns (ndc_cd, prev_ndc_cd) and filter for codes related to ALK+ NSCLC drugs. Generate a count plot of ndc_cd to verify if there are occurrences of these codes.
* Step 2: Field Description and Summary Analysis: Review each field in the dataset, documenting the data type, allowed values, and potential connections with other fields. Identify key columns for further analysis. Use `data.info()` and `data.describe()` to gather an overview.
* Step 3: Missing Value Analysis and Data Cleanup: Investigate missing data in every column using `data.isnull().sum()`. Create a heatmap with `sns.heatmap(data.isnull(), cbar=False)` to visualize missing patterns. Recommend strategies for filling missing values or removing incomplete columns where needed. Identify columns with high percentages of missing values and suggest appropriate imputation methods. Check for inconsistencies or errors in data entries and propose cleanup strategies.
* Step 4: Data Aggregation and Patient-Centric Analysis: Evaluate if data should be aggregated at the `patient_id` level to construct a comprehensive patient history. Use `groupby('patient_id')` to aggregate key columns (`claim_id`, `svc_dt`, `diagnosis_code`, etc.). Visualize the distribution of claims per patient with a histogram.
* Step 5: Temporal Event Analysis: Analyze the sequence of events by creating features such as `days_since_first_claim` per `patient_id` and examining claim timelines. Generate a time-series plot for a visual representation of the temporal distribution.
* Step 6: Demographic Distribution Analysis: Investigate demographic attributes (e.g., `patient_birth_year`, `patient_gender`) and analyze their distribution. Create features like age from `patient_birth_year` and plot histograms and bar charts.
* Step 7: Diagnosis and Drug Code Analysis: Review the frequency and types of diagnosis codes (`diagnosis_code`) and drug codes (`ndc_cd`) to find relevant patterns. Filter for ALK+ NSCLC drug codes and plot their occurrences.
* Step 8: Feature Encoding Strategy Identification: Identify the best encoding methods for categorical and text-based features. Recommend one-hot encoding for categorical data, binary encoding for ordinal fields, and n-gram encoding for text features where applicable.
* Step 9: Source of Business (SOB) Analysis: Evaluate the `sob` field to understand patient claim origins. Plot a pie chart or bar chart to represent the distribution of different `sob` values.
* Step 10: Feature Suggestions Analysis: Identify potential new features that could be extracted from existing data. Consider discrete features (e.g., binning continuous variables), temporal features (e.g., time since last event), and sequence features (e.g., order of events). For each suggested feature, provide rationale and potential impact on the analysis. Visualize relationships between existing features and proposed new features using scatter plots or pair plots where appropriate.
* Step 11: Correlation and Feature Importance: Correlate columns that could indicate feature importance, such as `diagnosis_code` and `ndc_cd`, against patient attributes. Use correlation matrices and plot heatmaps.
* . . . <more steps to ensure insights into the dataset for preprocessing and feature engineering decisions>

    """
      replanner_prompt_template = """As a world-class ML Scientist/Researcher with expertise in healthcare data, for the given objective, validate the response from the previous steps run. The goal of the tasks/steps is to gain insights into the dataset for making preprocessing and feature engineering decisions. Provide a thorough analysis of the tasks and the dataset. Execute each step, validate the response of the last run, and modify the steps as needed to proceed to the next task. Do not include any superfluous steps. Ensure the final step yields the complete answer. Ensure each step has all the necessary details and avoid skipping any essential information.

**Note:**
* Each step will be assigned to an executor agent to perform analysis on, so be as descriptive as possible.
* Include detailed analysis action hints for the analyst.
* Do not include steps to perform data transformations or feature engineering.
* Focus strictly on data analysis for the provided question/context.
* Do not exceed 20 total steps; ensure coverage of every column attribute across these steps.
* MUST: Conduct (statistical) visualization analysis for each applicable step.
* MUST: Evaluate each existing column for its potential as a new feature and suggest any needed reorientation for feature extraction.
* MUST: Summarize each field, including data type, allowed values, and potential connections to other fields.
* MUST: Investigate and handle missing values, ensuring data cleanup suggestions are mentioned where necessary.
* MUST: Propose potential discrete, temporal, and sequence features.
* MUST: Identify and suggest appropriate methods for encoding features (e.g., one-hot, binary, n-gram).

=====
**Example Analysis Plan:**

Question - Does this patient have ALK+ NSCLC?
Past Steps - [Step 1: Label requirement analysis: Check if the target class label (ALK+ NSCLC) exists within the dataset or if it can be derived. Identify relevant columns (ndc_cd, prev_ndc_cd) and filter for codes related to ALK+ NSCLC drugs. Generate a count plot of ndc_cd to verify if there are occurrences of these codes., Step 2: Field Description and Summary Analysis: Review each field in the dataset, documenting the data type, allowed values, and potential connections with other fields. Identify key columns that are relevant for further analysis. Use `data.info()` and `data.describe()` to gather an overview.]
Response Plan -
* Step 3: Missing Value Analysis and Data Cleanup: Investigate missing data in every column using `data.isnull().sum()`. Create a heatmap with `sns.heatmap(data.isnull(), cbar=False)` to visualize missing patterns. Recommend strategies for filling missing values or removing incomplete columns where needed. Identify columns with high percentages of missing values and suggest appropriate imputation methods. Check for inconsistencies or errors in data entries and propose cleanup strategies.
* Step 4: Data Aggregation and Patient-Centric Analysis: Evaluate if data should be aggregated at the `patient_id` level to construct a comprehensive patient history. Use `groupby('patient_id')` to aggregate key columns (`claim_id`, `svc_dt`, `diagnosis_code`, etc.). Visualize the distribution of claims per patient with a histogram.
* Step 5: Temporal Event Analysis: Analyze the sequence of events by creating features such as `days_since_first_claim` per `patient_id` and examining claim timelines. Generate a time-series plot for a visual representation of the temporal distribution.
* Step 6: Demographic Distribution Analysis: Investigate demographic attributes (e.g., `patient_birth_year`, `patient_gender`) and analyze their distribution. Create features like age from `patient_birth_year` and plot histograms and bar charts.
* Step 7: Diagnosis and Drug Code Analysis: Review the frequency and types of diagnosis codes (`diagnosis_code`) and drug codes (`ndc_cd`) to find relevant patterns. Filter for ALK+ NSCLC drug codes and plot their occurrences.
* Step 8: Feature Encoding Strategy Identification: Identify the best encoding methods for categorical and text-based features. Recommend one-hot encoding for categorical data, binary encoding for ordinal fields, and n-gram encoding for text features where applicable.
* Step 9: Source of Business (SOB) Analysis: Evaluate the `sob` field to understand patient claim origins. Plot a pie chart or bar chart to represent the distribution of different `sob` values.
* Step 10: Feature Suggestions Analysis: Identify potential new features that could be extracted from existing data. Consider discrete features (e.g., binning continuous variables), temporal features (e.g., time since last event), and sequence features (e.g., order of events). For each suggested feature, provide rationale and potential impact on the analysis. Visualize relationships between existing features and proposed new features using scatter plots or pair plots where appropriate.
* Step 11: Correlation and Feature Importance: Correlate columns that could indicate feature importance, such as `diagnosis_code` and `ndc_cd`, against patient attributes. Use correlation matrices and plot heatmaps.
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
      synthesize_prompt_template = """As a world-class ML Scientist/Researcher with expertise in healthcare data, consolidate all the analysis results  for the given objective using the provided pieces of retrieved answers from executed steps. Ensure that the response strictly reflects the provided context without omitting any information or adding unsubstantiated content.

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
      label_prompt_template = """As a world-class Data Scientist with expertise in healthcare data, determine what data labeling is required for the given objective. 
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
      wrangling_prompt_template = """As a world-class Data Engineer with expertise in healthcare data, determine the necessary preprocessing/wrangling steps required to prepare the dataset for feature engineering based on the data analysis provided. Ensure the answer is specific and data-driven, removing any ambiguity or generalizations. If information is not available or cannot be directly deduced from the context, clearly state that you don't know.

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
      feature_engg_prompt_template = """As a world-class ML Engineer with expertise in healthcare data, determine the features required for preparing the dataset for feature engineering based on the provided data analysis. Suggest relevant features given the dataset context and ensure your answer is specific and data-driven. If information is not available or cannot be directly deduced from the context, clearly state that you don't know.

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
      scientist_prompt_template = """As a world-class ML Engineer with expertise in healthcare data, consolidate the final list of detailed step-by-step instructions based on the provided analysis, wrangling, and feature engineering results. 
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

    else:  # support for other projects
        print(f"Warning: Unsupported project - {project}")
        return {}

    prompts = {
      "domain_hints": domain_hints,
      "feature_hints": feature_hints,
      "planner_prompt_template": planner_prompt_template,
      "replanner_prompt_template": replanner_prompt_template,
      "synthesize_prompt_template": synthesize_prompt_template,
      "label_prompt_template": label_prompt_template,
      "wrangling_prompt_template": wrangling_prompt_template,
      "feature_engg_prompt_template": feature_engg_prompt_template,
      "scientist_prompt_template": scientist_prompt_template,
      }
 
    return prompts