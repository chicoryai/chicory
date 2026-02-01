SELECTOR_NAME = 'Selector'
DECOMPOSER_NAME = 'Decomposer'
REFINER_NAME = 'Refiner'
SYSTEM_NAME = 'System'

MAX_ROUND = 3  # max try times of one agent talk

concise_template = """
As an experienced and professional data scientist, your task is to analyze user question, provided schema and selected tables 
to provide relevant information. The database schema consists of table descriptions, each containing multiple column 
descriptions. Your goal is to identify the metadata of each columns and represent all in a dictionary format.

Make sure to return complete response. start with ```json and ending with ```

Here is a typical example:

==========
【Schema】
# Table: account
[
  (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].),
  (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].),
  (frequency, frequency of the account. Value examples: ['POPLATEK MESICNE', 'POPLATEK TYDNE', 'POPLATEK PO OBRATU'].),
  (date, the creation date of the account. Value examples: ['1997-12-29', '1997-12-28'].)
]
# Table: client
[
  (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].),
  (gender, gender. Value examples: ['M', 'F']. And F：female . M：male ),
  (birth_date, birth date. Value examples: ['1987-09-27', '1986-08-13'].),
  (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].)
]
【Foreign keys】
client.`district_id` = district.`district_id`
【Relevant DB Schema】
```
{{
    "client": ["client_id", "gender", "date", "district_id"],
}}
```
【Question】
What is the gender of the youngest client who opened account in the lowest average salary branch?
【Evidence】
Later birthdate refers to younger age; A11 refers to average salary
【Answer】
```json
{{
  "client_id": "the id of the client (identifier)",
  "gender": "gender of the client",
  "birth_date": "birth date of the client",
  "district_id": "the id of the district (identifier)",
}}
```
Question Solved.

==========

Here is a new example, please start answering:

【Schema】
{desc_str}
【Foreign keys】
{fk_str}
【Relevant DB Schema】
{chosen_db_schem_dict}
【Question】
{query}
【Evidence】
{evidence}
【Answer】
"""

selector_template = """As an experienced and professional engineer, your task is to analyze database(s) schema to 
provide relevant information. The database schema consists of table descriptions, each containing multiple column 
descriptions. Your goal is to identify the relevant tables and columns based on the user question and evidence provided.

[Instruction]:
1. The output should be in JSON format.

Requirements:
1. If a table has less than or equal to 10 columns, mark it as "keep_all".
2. If a table is completely irrelevant to the user question and evidence, mark it as "drop_all".

Here is a typical example:

==========
【Schema】
# Table: heart
[
  (Age, age. Value examples: [40, 49, 37, 48, 54, 39].),
  (Sex, sex. Value examples: ['M', 'F'].),
  (ChestPainType, chestpaintype. Value examples: ['ATA', 'NAP', 'ASY', 'TA'].),
  (RestingBP, restingbp. Value examples: [140, 160, 130, 138, 150, 120].),
  (Cholesterol, cholesterol. Value examples: [289, 180, 283, 214, 195, 339].),
  (FastingBS, fastingbs. Value examples: [0, 1].),
  (RestingECG, restingecg. Value examples: ['Normal', 'ST', 'LVH'].),
  (MaxHR, maxhr. Value examples: [172, 156, 98, 108, 122, 170].),
  (ExerciseAngina, exerciseangina. Value examples: ['N', 'Y'].),
  (Oldpeak, oldpeak. Value examples: [0.0, 1.0, 1.5, 2.0, 3.0, 4.0].),
  (ST_Slope, st slope. Value examples: ['Up', 'Flat', 'Down'].),
  (HeartDisease, heartdisease. Value examples: ['no', 'yes'].)
]
# Table: myocardial
[
  (AGE, age. Value examples: [55.0, 64.0, 70.0, 77.0, 71.0, 50.0].),
  (SEX, sex. Value examples: ['male', 'female'].),
  (INF_ANAM, inf anam. Value examples: ['one', 'zero', 'two', 'three and more'].),
  (STENOK_AN, stenok an. Value examples: ['never', 'during the last year', 'more than 5 years ago', '4-5 years ago', 'one year ago', 'two years ago'].),
  (FK_STENOK, fk stenok. Value examples: ['there is no angina pectoris', 'II FC', 'IV FC', 'I FC', 'III FC.'].),
  (IBS_POST, ibs post. Value examples: ['there was no СHD', 'exertional angina pectoris', 'unstable angina pectoris'].),
  (GB, gb. Value examples: ['there is no essential hypertension', 'Stage 2', 'Stage 3', 'Stage 1'].),
  (SIM_GIPERT, sim gipert. Value examples: ['no', 'yes'].),
  (DLIT_AG, dlit ag. Value examples: ['there was no arterial hypertension', 'more than 10 years', '6-10 years', 'three years', 'two years', 'one year'].),
  (ZSN_A, zsn a. Value examples: ['there is no chronic heart failure', 'I stage', 'IIА stage', 'IIB stage'].),
  (fibr_ter_07, fibr ter 07. Value examples: ['no', 'yes'].),
  (fibr_ter_08, fibr ter 08. Value examples: ['no', 'yes'].),
  (ALT_BLOOD, alt blood. Value examples: [0.38, 0.45, 0.3, 0.15, 1.13, 0.23].),
  (AST_BLOOD, ast blood. Value examples: [0.18, 0.22, 0.11, 0.45, 0.6, 0.15].),
  (L_BLOOD, l blood. Value examples: [7.8, 7.2, 11.1, 6.9, 9.1, 9.6].),
  (ROE, roe. Value examples: [3.0, 2.0, 5.0, 30.0, 18.0, 15.0].),
  (TIME_B_S, time b s. Value examples: ['2-4 hours', 'less than 2 hours', '4-6 hours', '6-8 hours', '8-12 hours', 'more than 3 days'].),
  (NITR_S, nitr s. Value examples: ['no', 'yes'].),
  (LID_S_n, lid s n. Value examples: ['yes', 'no'].),
  (B_BLOK_S_n, b blok s n. Value examples: ['no', 'yes'].),
  (ANT_CA_S_n, ant ca s n. Value examples: ['yes', 'no'].),
  (GEPAR_S_n, gepar s n. Value examples: ['yes', 'no'].),
  (ASP_S_n, asp s n. Value examples: ['yes', 'no'].),
  (TIKL_S_n, tikl s n. Value examples: ['no', 'yes'].),
  (TRENT_S_n, trent s n. Value examples: ['yes', 'no'].),
  (ZSN, zsn. Value examples: ['no', 'yes'].)
]
# Table: diabetes
[
  (Pregnancies, pregnancies. Value examples: [6, 1, 8, 0, 5, 3].),
  (Glucose, glucose. Value examples: [148, 85, 183, 89, 137, 116].),
  (BloodPressure, bloodpressure. Value examples: [72, 66, 64, 40, 74, 50].),
  (SkinThickness, skinthickness. Value examples: [35, 29, 0, 23, 32, 45].),
  (Insulin, insulin. Value examples: [0, 94, 168, 88, 543, 846].),
  (BMI, bmi. Value examples: [33.6, 26.6, 23.3, 28.1, 43.1, 25.6].),
  (DiabetesPedigreeFunction, diabetespedigreefunction. Value examples: [0.627, 0.351, 0.672, 0.167, 2.288, 0.201].),
  (Age, age. Value examples: [50, 31, 32, 21, 33, 30].),
  (Outcome, outcome. Value examples: ['yes', 'no'].)
]
【Foreign keys】

【Question】
Does this patient have diabetes? Yes or no?
【Evidence】

【Answer】
```json
{{
  "heart": "keep_all",
  "myocardial": "keep_all",
  "diabetes": "keep_all",
  "xyz": ["district_id", "A11", "A2", "A4", "A6", "A7"]
}}
```
Question Solved.

==========

Here is a new example, please start answering:

【Schema】
{desc_str}
【Foreign keys】
{fk_str}
【Question】
{query}
【Evidence】
{evidence}
【Answer】
"""

features_template = """
As an experienced and professional data scientist, your task is to analyze user question, provided schema and selected tables 
to provide relevant information. The database schema consists of table descriptions, each containing multiple column 
descriptions. Your goal is to identify the attributes needed for applying feature engineering and using the dataset
 for prediction as per user's objective and represent all in a dictionary format.

Here is a typical example:

==========
【Schema】
# Table: account
[
  (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].),
  (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].),
  (frequency, frequency of the account. Value examples: ['POPLATEK MESICNE', 'POPLATEK TYDNE', 'POPLATEK PO OBRATU'].),
  (date, the creation date of the account. Value examples: ['1997-12-29', '1997-12-28'].)
]
# Table: client
[
  (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].),
  (gender, gender. Value examples: ['M', 'F']. And F：female . M：male ),
  (birth_date, birth date. Value examples: ['1987-09-27', '1986-08-13'].),
  (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].)
]
【Foreign keys】
client.`district_id` = district.`district_id`
【Relevant DB Schema】
```
{{
    "client": ["client_id", "gender", "date", "district_id"],
}}
```
【Question】
What is the gender of the youngest client who opened account in the lowest average salary branch?
【Evidence】
Later birthdate refers to younger age; A11 refers to average salary
【Answer】
```json
{{
  "problem_type": <classification, regression, clustering,  anomaly detection, or more>
  "training_shot": <recommended training shots number; number of different patterns in the data, minimum 10%>,
  "seed": <recommended seed for the prediction>",
  "task_class": <sklearn.ensemble.RandomForestClassifier (current support is only classification)>,
  "features": [ list of the relevant attributes ],
  "target": <target_attribute>
}}
```
Question Solved.

==========

Here is a new example, please start answering:

【Schema】
{desc_str}
【Foreign keys】
{fk_str}
【Relevant DB Schema】
{chosen_db_schem_dict}
【Question】
{query}
【Evidence】
{evidence}
【Answer】
"""

relationship_template = """
As an experienced and professional data architect, your task is to analyze the database schema, user question, and available data to identify and define relationships between columns/tables, even when explicit foreign keys aren't defined. You'll need to examine schema definitions, column naming patterns, data samples, and given context to establish these implicit relationships.

Here is a typical example:

==========
【Schema】
# Table: account
[
  (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].),
  (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].),
  (frequency, frequency of the account. Value examples: ['POPLATEK MESICNE', 'POPLATEK TYDNE', 'POPLATEK PO OBRATU'].),
  (date, the creation date of the account. Value examples: ['1997-12-29', '1997-12-28'].)
]
# Table: client
[
  (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].),
  (gender, gender. Value examples: ['M', 'F']. And F：female . M：male ),
  (birth_date, birth date. Value examples: ['1987-09-27', '1986-08-13'].),
  (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].)
]
# Table: district
[
  (district_id, identifier of the district. Value examples: [1, 2, 3, 4, 5].),
  (A11, average salary in the district. Value examples: [10120, 9234, 11393, 8895, 10277].)
]
【Explicit Foreign Keys】
client.district_id = district.district_id
【Question】
How many clients are associated with each branch location?
【Data Sample】
account(1, 77, 'POPLATEK MESICNE', '1995-01-15')
account(2, 39, 'POPLATEK TYDNE', '1998-03-12')
client(1, 'M', '1962-10-05', 77)
client(2, 'F', '1975-06-19', 39)
client(3, 'M', '1980-11-25', 77)
district(77, 10120)
district(39, 8895)
【Answer】
```json
{{
  "identified_relationships": [
    {{
      "relationship_type": "explicit_foreign_key",
      "parent_table": "district",
      "parent_column": "district_id",
      "child_table": "client",
      "child_column": "district_id",
      "cardinality": "one-to-many",
      "confidence": "high",
      "evidence": "Explicit foreign key defined in schema"
    }},
    {{
      "relationship_type": "implicit_foreign_key",
      "parent_table": "district",
      "parent_column": "district_id",
      "child_table": "account",
      "child_column": "district_id",
      "cardinality": "one-to-many",
      "confidence": "high",
      "evidence": "Column name match and data sample shows district_id values in account table match with district table"
    }},
    {{
      "relationship_type": "implicit_relationship",
      "parent_table": "client",
      "parent_column": "client_id",
      "child_table": "account",
      "child_column": null,
      "cardinality": "one-to-many",
      "confidence": "medium",
      "evidence": "Given context suggests clients have accounts, but no clear linking column exists in the account table"
    }}
  ],
  "proposed_join_paths": [
    {{
      "query_goal": "clients per branch location",
      "tables": ["client", "district"],
      "join_conditions": ["client.district_id = district.district_id"],
      "group_by": ["district.district_id"],
      "aggregate": "COUNT(client.client_id)"
    }}
  ],
  "missing_relationship_recommendations": [
    {{
      "recommendation": "Add client_id column to account table to explicitly link accounts to clients",
      "benefit": "Would clarify ownership of accounts and enable direct client-account relationship queries"
    }}
  ]
}}
```

Question Solved.

==========

Here is a new example, please start answering:
【Schema】
{desc_str}
【Explicit Foreign Keys】
{fk_str}
【Relevant DB Schema】
{chosen_db_schem_dict}
【Question】
{query}
【Evidence】
{evidence}
【Answer】
"""
