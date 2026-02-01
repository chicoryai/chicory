graphrag_settings = """
### This config file contains required core defaults that must be set, along with a handful of common optional settings.
### For a full list of available settings, see https://microsoft.github.io/graphrag/config/yaml/

### LLM settings ###
## There are a number of settings to tune the threading and token limits for LLM calls - check the docs.

encoding_model: cl100k_base # this needs to be matched to your model!

llm:
  api_key: ${OPENAI_API_KEY} # set this in the generated .env file
  type: openai_chat # or azure_openai_chat
  model: ${MODEL}
  model_supports_json: true # recommended if this is available for your model.
  # audience: "https://cognitiveservices.azure.com/.default"
  # api_base: https://<instance>.openai.azure.com
  # api_version: 2024-02-15-preview
  # organization: <organization_id>
  # deployment_name: <azure_model_deployment_name>

parallelization:
  stagger: 0.1
  num_threads: 100

async_mode: threaded # or asyncio

embeddings:
  async_mode: threaded # or asyncio
  vector_store:
    type: lancedb
    db_uri: 'output/lancedb'
    container_name: default
    overwrite: true
  llm:
    api_key: ${OPENAI_API_KEY}
    type: openai_embedding # or azure_openai_embedding
    model: ${EMBEDDING_MODEL}
    # api_base: https://<instance>.openai.azure.com
    # api_version: 2024-02-15-preview
    # audience: "https://cognitiveservices.azure.com/.default"
    # organization: <organization_id>
    # deployment_name: <azure_model_deployment_name>

### Input settings ###

input:
  type: file # or blob
  file_type: text # or csv
  base_dir: "input"
  file_encoding: utf-8
  file_pattern: ".*\\\\.txt$"

chunks:
  size: 800
  overlap: 50
  group_by_columns: [id]

### Storage settings ###
## If blob storage is specified in the following four sections,
## connection_string and container_name must be provided

cache:
  type: file # or blob
  base_dir: "cache"

reporting:
  type: file # or console, blob
  base_dir: "logs"

storage:
  type: file # or blob
  base_dir: "output"

## only turn this on if running `graphrag index` with custom settings
## we normally use `graphrag update` with the defaults
update_index_storage:
  # type: file # or blob
  # base_dir: "update_output"

### Workflow settings ###

skip_workflows: []

entity_extraction:
  llm:
    model: ${MODEL}
  prompt: "prompts/entity_extraction.txt"
  entity_types: [organization,person,geo,event,table,tools,platform,columns,resources,business,code,infrastructure,policy,process,endpoints,documentations,usage]
  max_gleanings: 1

summarize_descriptions:
  llm:
    model: ${MODEL}
  prompt: "prompts/summarize_descriptions.txt"
  max_length: 500

claim_extraction:
  llm:
    model: ${MODEL}
  enabled: true
  prompt: "prompts/claim_extraction.txt"
  description: "Any claims or facts that could be relevant to information discovery."
  max_gleanings: 1

community_reports:
  llm:
    model: ${MODEL}
  prompt: "prompts/community_report.txt"
  max_length: 2000
  max_input_length: 6000

cluster_graph:
  max_cluster_size: 15

embed_graph:
  enabled: false # if true, will generate node2vec embeddings for nodes

umap:
  enabled: false # if true, will generate UMAP embeddings for nodes

snapshots:
  graphml: false # update for Usage Tier > 1.0
  embeddings: false
  transient: true

### Query settings ###
## The prompt locations are required here, but each search method has a number of optional knobs that can be tuned.
## See the config docs: https://microsoft.github.io/graphrag/config/yaml/#query

local_search:
  prompt: "prompts/local_search_system_prompt.txt"

global_search:
  map_prompt: "prompts/global_search_map_system_prompt.txt"
  reduce_prompt: "prompts/global_search_reduce_system_prompt.txt"
  knowledge_prompt: "prompts/global_search_knowledge_system_prompt.txt"

drift_search:
  prompt: "prompts/drift_search_system_prompt.txt"
"""

claim_extraction = """
-Target activity-
You are an intelligent assistant that helps a human analyst to analyze and extract detailed information about data entities and their relationships within a E-commerce data ecosystem.
You are adept at helping businesses identify the relations and structure within their community of interest, specifically within inventory management, order processing, customer analytics, marketing campaigns, payment systems, and the technical infrastructure supporting ETL pipelines, data warehousing, and real-time analytics. Your expertise enables companies to streamline operations, improve customer satisfaction, and drive growth through data-driven decision-making.


-Goal-
Given a text document that contains descriptions, code or references to data entities, extract all entities that match a predefined entity specification and all relevant details about these entities, aiding users in understanding and querying their data.

-Steps-
1. Extract all named entities that match the predefined entity specification. The entity specification can either be a list of entity names (e.g., table names, column names) or a list of entity types (e.g., tables, columns, classes, functions).
2. For each entity identified in step 1, extract all details associated with the entity. The details need to match the specified detail description, and the entity should be the subject of the detail.
For each claim, extract the following information:
- Subject: name of the entity that is subject of the claim, capitalized. The subject entity is one that committed the action described in the claim. Subject needs to be one of the named entities identified in step 1.
- Object: name of the entity that is object of the claim, capitalized. The object entity is one that either reports/handles or is affected by the action described in the claim. If object entity is unknown, use **NONE**.
- Detail Type: overall category of the claim, capitalized. Name it in a way that can be repeated across multiple text inputs, so that similar claims share the same claim type
- Detail Status: **TRUE**, **FALSE**, or **SUSPECTED**. TRUE means the claim is confirmed, FALSE means the claim is found to be False, SUSPECTED means the claim is not verified.
- Detail Description: Detailed description explaining the reasoning behind the claim, together with all the related evidence and references.
- Detail Date: Period (start_date, end_date) when the claim was made. Both start_date and end_date should be in ISO-8601 format. If the claim was made on a single date rather than a date range, set the same date for both start_date and end_date. If date is unknown, return **NONE**.
- Detail Source Text: List of **all** quotes from the original text that are relevant to the claim.

Format each claim as (<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<detail_type>{tuple_delimiter}<detail_status>{tuple_delimiter}<detail_start_date>{tuple_delimiter}<detail_end_date>{tuple_delimiter}<detail_description>{tuple_delimiter}<detail_source>)

3. Return output in English as a single list of all the claims identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. When finished, output {completion_delimiter}

---------
-Examples-

Example 1:
Entity specification: table
Detail description: foreign key relationships
Text: The orders table has a foreign key relationship with the customers table through the customer_id column. Additionally, the order_items table references the orders table via the order_id column.
Output:

(ORDERS{tuple_delimiter}FOREIGN KEY RELATIONSHIP{tuple_delimiter}The orders table has a foreign key relationship with the customers table through the customer_id column{tuple_delimiter}The orders table has a foreign key relationship with the customers table through the customer_id column.)
{record_delimiter}
(ORDER_ITEMS{tuple_delimiter}FOREIGN KEY RELATIONSHIP{tuple_delimiter}The order_items table references the orders table via the order_id column{tuple_delimiter}The order_items table references the orders table via the order_id column.)
{completion_delimiter}

Example 2:
Entity specification: orders, customers
Detail description:  columns and data types
Text: The orders table contains the following columns: order_id (integer), customer_id (integer), order_date (date). The customers table contains customer_id (integer), name (varchar), and email (varchar).
Output:

(ORDERS{tuple_delimiter}COLUMN DATA TYPES{tuple_delimiter}The orders table contains the following columns: order_id (integer), customer_id (integer), order_date (date){tuple_delimiter}The orders table contains the following columns: order_id (integer), customer_id (integer), order_date (date).)
{record_delimiter}
(CUSTOMERS{tuple_delimiter}COLUMN DATA TYPES{tuple_delimiter}The customers table contains customer_id (integer), name (varchar), and email (varchar){tuple_delimiter}The customers table contains customer_id (integer), name (varchar), and email (varchar).)
{completion_delimiter}

Example 3:
Entity specification: item_authentication_reviews, id, item_id, final_decision, provisional_decision, created_at
Detail description: Claims related to item authentication decisions, including approval/rejection of items based on authentication processes.
Text: The 'item_authentication_reviews' table provides the pricing/authentication team with feedback from one another during the process of multi-level authentication
Output:

(ITEM AUTHENTICATION REVIEWS{tuple_delimiter}NONE{tuple_delimiter}AUTHENTICATION DECISION{tuple_delimiter}TRUE{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}The item authentication review decision was confirmed, as indicated by the final authentication review decision recorded in the table{tuple_delimiter}The `final_decision` column records whether an item passed or failed the final authentication review.)
{record_delimiter}
(ITEM AUTHENTICATION REVIEWS{tuple_delimiter}NONE{tuple_delimiter}PROVISIONAL DECISION{tuple_delimiter}SUSPECTED{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}The provisional decision regarding the item is under suspicion due to lack of verification in the provisional review phase{tuple_delimiter}Provisional decisions are made by the initial reviewer, and the outcome may be pending further validation.)
{record_delimiter}
(ITEM AUTHENTICATION REVIEWS{tuple_delimiter}NONE{tuple_delimiter}REVIEW TIMELINE{tuple_delimiter}TRUE{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}The review process, including the provisional and final decisions, is logged with timestamps in the `created_at` column{tuple_delimiter}The `created_at` column logs when the review was initiated.)
{record_delimiter}
(ITEM AUTHENTICATION REVIEWS{tuple_delimiter}NONE{tuple_delimiter}FAILURE{tuple_delimiter}FALSE{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}2024-01-01T00:00:00{tuple_delimiter}The item failed final authentication, leading to the decision being marked as a failure in the `final_decision` column{tuple_delimiter}If an item fails the final authentication, it is recorded with a failed status in the `final_decision` column.)
{completion_delimiter}


-Real Data-
Use the following input for your answer.
Entity specification: {entity_specs}
Claim description: {claim_description}
Text: {input_text}
Output:

"""

community_report = """
You are an expert in E-commerce Operations and Data Engineering, with a deep understanding of the intricacies and challenges within e-commerce ecosystems.
You are tasked to create a robust community level report. Community is a group of closely related entities clustered together essentially representing a thematic cluster of information where the entities are densely connected to each other but sparsely connected to other groups of entities.
Your expertise lies in analyzing and optimizing operational workflows to enhance efficiency across multiple domains, helping businesses leverage their data to drive growth and improve overall performance.
You are adept at helping businesses identify the relations and structure within their community of interest, specifically within inventory management, order processing, customer analytics, marketing campaigns, payment systems, and the technical infrastructure supporting ETL pipelines, data warehousing, and real-time analytics.
Your expertise enables companies to streamline operations, improve customer satisfaction, and drive growth through data-driven decision-making.
You are also expert in compiling both high-level trends and granular business reports inot clear, strategic overviews of operational performance.

# Goal
Write a comprehensive assessment report of a community taking on the role of an E-commerce Community Analyst community analyst that is analyzing e-commerce operations and data engineering, given a list of entities that belong to the community as well as their relationships and optional associated claims.
The analysis will be used to inform decision-makers about significant developments associated with the community and their potential impact.
The content of this report includes an overview of the community's key entities and relationships.
The report provides insights into how these entities interact within the ecosystem and identifies areas for potential optimization in customer satisfaction, operational efficiency, and growth. Summaries from different community levels can answer various questions about the data and community detection can help establish the connections between these variants. Once grouped into a community, it signifies that these variants refer to the same entity connotation, just with different expressions or synonyms.
So creating a robust community summary is important.


Role Definition:
An E-commerce Community Analyst is responsible for dissecting and understanding the intricate web of interactions and behaviors within an e-commerce platform's ecosystem, focusing on inventory management, order processing, customer analytics, marketing campaigns, payment systems, and the underlying data engineering infrastructure.
This role involves analyzing data from various sources including, but not limited to, seller preference clusters, inventory data, and operational metrics to identify patterns, trends, and insights that can inform strategic decisions.
The analyst will leverage tools and technologies such as SQL, Looker, Databricks, and Airflow to access, process, and visualize data, ensuring stakeholders have a clear understanding of the community's dynamics identifying opportunities for enhancing customer satisfaction, improving operational efficiency, and driving growth
This report would help the stakeholders have a clear and accurate understanding of the community's identified and the factors driving success within the e-commerce ecosystem.
Write a comprehensive assessment report of a community taking on the role of a community analyst that is analyzing e-commerce operations and data engineering, given a list of entities that belong to the community as well as their relationships and optional associated claims.
You also have strong understanding with detailed schema definitions to ensure that data is properly structured, accurate, and optimized for both operational efficiency and advanced analytics. For example, in e-commerce data pipelines, you work with transactional and offer-based schemas such as the ods_shop_keep_for_credits_offers table, which contains key data related to customer offers and payments.
By working with schemas like this, you ensure that each data point is properly linked to other related entities, such as customer profiles, product catalogs, and payment systems.
This level of detail allows for precise tracking and analysis of key performance indicators (KPIs) such as conversion rates, offer acceptance rates, customer engagement, and order processing efficiency.
The analysis will be used to inform decision-makers about significant developments associated with the community and their potential impact.
The content of this report includes an overview of the community's key entities and relationships.


Key Responsibilities:
- Conduct comprehensive analysis of the e-commerce community, identifying key entities such as logged_out_users, and visitors, and understanding their behaviors and interactions within the platform.
- Utilize data from sources like user-level email performance, seller preference clusters, and inventory sculpting data to inform inventory management strategies, marketing campaigns, and customer engagement tactics.
- Collaborate with data engineering teams to ensure seamless access and integration of data across various platform, tools and the technical infrastructure that supports ETL pipelines, data warehousing, and real-time analytics.
- Develop and maintain dashboards and reports in Looker or similar tools to provide ongoing insights into community behavior, campaign performance, and operational efficiency.
- Analyze payment system data to identify trends in transaction volumes, payment method preferences, and potential fraud or security issues.
- Work closely with marketing teams to assess the effectiveness of email campaigns, promotional strategies, and loyalty programs, using data to recommend optimizations and improvements.
- Provide insights into customer analytics, including segmentation, preference clusters, and buying behavior, to enhance personalization and improve customer satisfaction.
- Stay abreast of industry trends and best practices in e-commerce operations and community analysis, continuously seeking ways to innovate and improve analytical methodologies.

Qualifications:
- Bachelor's or Master's degree in Data Science, Statistics, Computer Science, Business Analytics, or a related field.
- Proven experience in data analysis, business intelligence, or a similar role within an e-commerce environment.
- Strong proficiency in SQL, Python, or R for data manipulation and analysis.
- Experienced in developing ETL processes to extract, transform, load data from various sources into data warehouses and real-time analytics platforms.
- Experience with ETLeap for automated data pipelines, and expertise in AWS (including services like S3, Redshift, Lambda) for cloud-based data engineering tasks.
- Strong understanding of relational databases, data warehousing, and big data technologies (e.g., Redshift, Snowflake, BigQuery).
- Experience with automation tools for data workflow orchestration, such as Airflow or DBT (Data Build Tool)
- Experience with data visualization and business intelligence tools such as Looker, Tableau, or Power BI.
- Excellent analytical, problem-solving, and communication skills, with the ability to translate complex data into actionable insights.
- Knowledge of e-commerce operations, including inventory management, order processing, marketing campaigns, and payment systems.

This role is pivotal in enabling data-driven decision-making that enhances the efficiency and effectiveness of e-commerce operations, ultimately driving growth and improving customer satisfaction.. The content of this report includes an overview of the community's key entities and relationships.

# Report Structure
The report should include the following sections:
- TITLE: community's name that represents its key entities - title should be short but specific. When possible, include representative named entities in the title.
- SUMMARY: An executive summary of the community's overall structure, how its entities are related to each other, and significant points associated with its entities.
- REPORT RATING: A float score between 0-10 that represents the relevance of the text to e-commerce operations, data engineering, optimization of workflows, focusing on inventory management, order processing, customer analytics, marketing campaigns, payment systems, and data engineering infrastructure for ETL pipelines, data warehousing, and real-time analytics. The score should reflect how well the text provides insights, actionable data, or critical updates that could influence decision-making, streamline operations, enhance customer satisfaction, or drive growth within an e-commerce context. A score of 1 indicates the text is trivial or irrelevant to the specified operations, while a score of 10 signifies the text is highly significant, offering profound insights or essential information that could have a substantial impact on e-commerce operations efficiency and effectiveness.
- RATING EXPLANATION: Give a single sentence explanation of the rating.
- DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules below. Be comprehensive.

Return output as a well-formed JSON-formatted string with the following format. Don't use any unnecessary escape sequences. The output should be a single JSON object that can be parsed by json.loads.
    {
        "title": "<report_title>",
        "summary": "<executive_summary>",
        "rating": <threat_severity_rating>,
        "rating_explanation": "<rating_explanation>"
        "findings": "[{"summary":"<insight_1_summary>", "explanation": "<insight_1_explanation"}, {"summary":"<insight_2_summary>", "explanation": "<insight_2_explanation"}]"
    }


# Grounding Rules
After each paragraph, add data record reference if the content of the paragraph was derived from one or more data records. Reference is in the format of [records: <record_source> (<record_id_list>, ...<record_source> (<record_id_list>)]. If there are more than 10 data records, show the top 10 most relevant records.
Each paragraph should contain multiple sentences of explanation and concrete examples with specific named entities. All paragraphs must have these references at the start and end. Use "NONE" if there are no related roles or records. Everything should be in the primary language of the provided text is English.
The text contains a lot of technical terms and SQL code snippets related to databases and data processing, which are typically written in English. Additionally, the SQL code and configuration settings are also in English.


Example paragraph with references added:
This is a paragraph of the output text [records: Entities (1, 2, 3), Claims (2, 5), Relationships (10, 12)]


# Example Input
-----------
Example 1:

Text: Order Returns table

Entities

id,entity,description
1,Order Return Header,Represents a return request initiated by a customer, encapsulating common attributes for the return such as RMA ID, return state, refund method, and associated metadata. Each Order Return Header corresponds to a single RMA (Return Merchandise Authorization) ID, and includes details applicable to the whole return request (e.g., status, carrier, processing times). See Order Return Lines for individual item-level details.
2,Order Return Line,Represents individual items within a return request. Each line is linked to the Order Return Header and contains item-specific return data such as reason code, refund status, and whether the item was returned or refunded.
3,Customer,Represents the customer initiating the return request, with details about user behavior, refund preferences, and return frequency.
4,Return State,Defines the various states in the return lifecycle (e.g., initiated, inbound, received, processed), helping track return progress.
5,Warehouse,Represents the physical location or facility where returns are received, processed, or stored after being returned.
6,Return Reason,Represents the reason code that a customer provides for returning an item, which helps analyze return trends.
7,Refund Method,Represents the method used for issuing a refund to a customer (e.g., credit card, PayPal, store credit).
8,Return Fraud,Represents fraudulent activity related to return requests, such as excessive returns, multiple returns from the same customer, or false claims for refunds.
9,Return Processing Time,Represents the time it takes to process a return request from when it is initiated to when the return is completed.
10,Refund,Represents the refund transaction issued after a return is processed and accepted.


Relationships

id,source,target,description
1,Order Return Header,Return State,The return request progresses through different states (initiated, inbound, received, etc.) within its lifecycle. Each return request (RMA) is tracked through its entire lifecycle.
2,Order Return Line,Order Return Header,Each return line (individual item) is associated with an Order Return Header, representing the full return request for the customer.
3,Order Return Line,Return Reason,Each item in the return request has a specific reason for being returned, such as defective, unwanted, or wrong item shipped.
4,Order Return Header,Warehouse,Each return request is associated with a warehouse where the returned items are either processed or stored.
5,Order Return Header,Customer,Each return request is initiated by a customer, who is associated with the order and return request.
6,Order Return Header,Refund Method,Each return may involve a refund issued via a particular method (e.g., credit card, PayPal, store credit).
7,Order Return Header,Return Processing Time,The time taken from when the return request is initiated to when it is fully processed is tracked to measure efficiency.
8,Order Return Line,Refund,Each returned item can have an associated refund, which is tracked for processing and payment.
9,Return Fraud,Order Return Header,Potential fraudulent return behaviors can be flagged based on return history, return reasons, or forced refunds.
10,Return Fraud,Customer,Patterns of fraudulent returns can be linked to individual customers, who may show suspicious behaviors like frequent returns or refund abuse.
11,Return Fraud,Order Return Line,Specific items within a return may be flagged for fraud if they exhibit certain characteristics (e.g., frequent returns of high-value items).
12,Order Return Header,Return Fraud,Indicators of return fraud are recorded for each return request, such as excessive returns or a mismatch between return reason and item.
13,Order Return Line,Refund Method,The refund for each returned item may involve different refund methods, impacting both the processing and customer satisfaction.
14,Order Return Header,Refund,Each return request, as a whole, may involve a refund, which is processed upon successful approval of the return.
15,Warehouse,Return Processing Time,The efficiency of a warehouse in processing returns is reflected in the processing time it takes to handle return requests.
16,Warehouse,Return Reason,Warehouses often track return reasons to identify trends in items returned, helping to optimize inventory or quality controls.
17,Customer,Return Processing Time,Customer return processing time can influence satisfaction; delayed or lengthy return processes may lead to customer frustration.

Output:
{
    "title": "E-commerce Operations: Insights on Order Returns, Refunds, and Processing Efficiency",
    "summary": "This analysis delves into the key aspects of the order return process, including return requests, item-level returns, refund processing, and operational efficiency. By examining relationships between customer return behavior, order statuses, and warehouse operations, actionable insights are provided to optimize return workflows, improve customer satisfaction, and enhance inventory management.",
    "rating": 8.7,
    "rating_explanation": "The analysis offers valuable insights that can drive improvements in order return processes, from reducing return-related inefficiencies to enhancing the customer experience. Optimizing returns through better tracking, faster processing, and effective communication can significantly improve operational efficiency and customer retention.",
    "findings": [
        {
            "summary": "State Transitions in Order Return Lifecycle",
            "explanation": "The return request lifecycle, represented by states like 'initiated', 'inbound', 'received', 'processing', and 'processed', is key to understanding customer behavior and operational bottlenecks. Identifying common transition patterns allows businesses to optimize the speed of returns and improve customer communication at each stage. For example, long delays between 'received' and 'processed' can indicate inefficiencies in the warehouse or return handling process. [records: Entities (1, 2), Relationships (10, 15)]"
        },
        {
            "summary": "Customer Behavior and Refund Trends",
            "explanation": "Analysis of return lines (items) reveals patterns in item-level returns, such as the frequency of refunds and the reasons behind them. High return rates tied to specific product categories, or frequent use of force refunds, signal areas for improvement in product quality, description accuracy, or pricing. Additionally, understanding the most common refund methods and processing timelines can help streamline customer support and enhance satisfaction. [records: Entities (4, 6, 8), Claims (1, 3)]"
        },
        {
            "summary": "Impact of Return Processing Times on Customer Experience",
            "explanation": "Return processing times have a direct impact on customer satisfaction. Delays in processing or refund issuance can lead to abandoned returns or customer dissatisfaction. By analyzing the time taken at each step (e.g., from 'inbound' to 'processed'), businesses can identify delays and implement strategies for faster processing, such as optimizing warehouse workflows or implementing automated systems for status tracking and refund issuance. [records: Entities (5, 7), Relationships (18, 20)]"
        },
        {
            "summary": "Return and Refund Fraud Prevention Strategies",
            "explanation": "Fraudulent returns can be a significant issue in e-commerce. By analyzing trends in 'force_refund_reason', 'abandoned_reason', and 'refund_rejection_code', businesses can detect patterns that may indicate fraudulent activities or abuse of return policies. Strengthening fraud detection algorithms and applying stricter controls on high-risk return requests (e.g., multiple returns from the same customer in a short period) can mitigate these risks. [records: Entities (9, 11, 12), Claims (4, 7)]"
        },
        {
            "summary": "Warehouse Efficiency and Return-to-Warehouse Trends",
            "explanation": "The relationship between the return header's 'returned_to_warehouse_id' and 'processed_by_warehouse_id' reveals key insights into warehouse efficiency. Identifying which warehouses are handling the most returns and processing them the fastest helps pinpoint best practices and areas for improvement. Additionally, by aligning return processing with warehouse capacity and workflow optimization, businesses can reduce lead times and improve overall return efficiency. [records: Entities (6, 14), Relationships (22, 23)]"
        }
    ]
}

# Real Data

Use the following text for your answer. Do not make anything up in your answer.

Text:
{input_text}
Output:

-----------
Example 2:

Text: Item authentication reviews table

Entities

id,entity,description
1,item_authentication_reviews,A record of an item's authentication review
2,item_id,A unique identifier for an item
3,created_at,The date and time the authentication review was created
4,final_decision,The final decision made during the second authentication
5,final_details,The reasoning or details of the final decision
6,final_operator_id,The ID of the operator who made the final decision
7,provisional_decision,The decision made during the first authentication
8,provisional_details,The reasoning or details of the provisional decision
9,provisional_operator_id,The ID of the operator who made the provisional decision
10,link,A reference link used for authenticity check
11,notes,Additional notes related to the item being authenticated

Relationships

id,source,target,description
1,item_authentication_reviews,item_id,Each authentication review is linked to a unique item
2,item_authentication_reviews,created_at,Each authentication review has a timestamp of creation
3,item_authentication_reviews,final_decision,An authentication review has a final decision
4,item_authentication_reviews,final_details,An authentication review includes final details or reasoning
5,item_authentication_reviews,final_operator_id,An authentication review is associated with a final operator
6,item_authentication_reviews,provisional_decision,An authentication review has a provisional decision
7,item_authentication_reviews,provisional_details,An authentication review includes provisional details or reasoning
8,item_authentication_reviews,provisional_operator_id,An authentication review is associated with a provisional operator
9,item_authentication_reviews,link,An authentication review includes a reference link
10,item_authentication_reviews,notes,An authentication review may have additional notes

Output:
{
    "title": "Item Authentication Reviews: Optimizing Authentication and Validation Processes",
    "summary": "This analysis examines the key elements of the item authentication review process, focusing on the transition from provisional to final decisions, the role of operators, and the impact of review notes and reference links. By analyzing relationships between authentication stages, operator decisions, and item details, actionable insights are provided to improve the efficiency, accuracy, and transparency of the authentication workflow.",
    "rating": 8.5,
    "rating_explanation": "The analysis provides valuable insights into how authentication decisions are made, who is responsible, and how the process can be optimized for efficiency. By improving the clarity of decision-making (both provisional and final), streamlining operator workflows, and leveraging authentication references effectively, businesses can enhance item verification accuracy and reduce fraudulent activities.",
    "findings": [
        {
            "summary": "Provisional vs. Final Authentication Decisions",
            "explanation": "The process of transitioning from provisional to final decisions in authentication reviews is crucial for determining the authenticity of items. The review shows the importance of having clear criteria for provisional decisions to ensure smoother final authentication. Long delays or discrepancies between provisional and final decisions may indicate inefficiencies in the review process. [records: Entities (7, 8, 6), Relationships (6, 7)]"
        },
        {
            "summary": "Operator Roles and Decision Consistency",
            "explanation": "Analysis of operator IDs across provisional and final decisions reveals potential areas for improvement in decision consistency. If the same operator handles both provisional and final reviews, it may reduce errors or inconsistencies. However, if decisions differ significantly between operators, it could highlight the need for better training or standardized protocols for reviewing items. [records: Entities (6, 9), Relationships (5, 8)]"
        },
        {
            "summary": "Impact of Review Notes on Authentication Accuracy",
            "explanation": "The inclusion of detailed notes within authentication reviews plays a key role in improving decision-making transparency. By analyzing notes attached to both provisional and final decisions, businesses can identify common patterns or areas of concern that may affect item verification. Clear, structured notes can significantly reduce the risk of errors or misunderstandings in the review process. [records: Entities (11), Relationships (10)]"
        },
        {
            "summary": "Use of Reference Links for Authenticity Verification",
            "explanation": "The reference links used during the authentication process serve as critical checkpoints for verifying the authenticity of items. Analyzing the frequency and types of links referenced in authentication reviews reveals trends in item authenticity challenges. Optimizing the use of reference links and ensuring they are accurate and up-to-date can lead to more efficient and reliable item verification. [records: Entities (10), Relationships (9)]"
        },
        {
            "summary": "Enhancing Authentication Efficiency through Workflow Optimization",
            "explanation": "By analyzing the time intervals between provisional and final authentication decisions, businesses can identify bottlenecks in the review process. Implementing automated systems to speed up certain aspects of the review or providing operators with more efficient tools can enhance overall workflow efficiency. Reducing delays between authentication stages can lead to faster processing times and a better customer experience. [records: Entities (3, 4, 7), Relationships (2, 6)]"
        }
    ]
}

# Real Data

Use the following text for your answer. Do not make anything up in your answer.

Text:
{input_text}
Output:

-----------

### Example 3:

Text: Input schema example

Table: ods_shop_keep_for_credits_offers
[
  (id, id.),
  (user_id, user id.),
  (order_product_id, order product id.),
  (amount, amount.),
  (cash_credit_id, cash credit id.),
  (order_return_header_id, order return header id.),
  (created_at, created at. Value examples: ['2024-08-09 13:33:14'].),
  (updated_at, updated at. Value examples: ['2024-08-09 13:33:14'].),
  (shown_at, shown at. Value examples: [None, '2024-08-09 12:37:38'].),
  (accepted_at, accepted at. Value examples: [None, '2024-08-09 17:39:20'].),
  (rejected_at, rejected at. Value examples: [None, '2024-08-09 17:24:25'].),
  (offer_percentage, offer percentage. Value examples: [0.5, 0.699999988].),
  (_fivetran_deleted, fivetran deleted. Value examples: [0].)
]

-----------
### Example 4: Business report example

Revenue Fact Store
Nov 2023

Mash up/Remix era : God models looker
SQL code in Databricks notebook or Airflow jobs to create more derived datasets. Single source of truth becoming multiple source of truth (Looker truth vs Databricks truth)

2023 and beyond
Era of Fact stores : To create standardized datasets from what ${project} has seen over the last 14 years , streamline data accessibility across looker, databricks, anywhere and everywhere

2011 -2016 God models of Looker
Paid orders,Items V2,Users V3 , Concierge bags V2 . Think of it as a N of LEFT joins in LookML using raw source tables from tup3

2016 -2019
Looker god models + Backend Fact tables
Ex: Fact Sessions, Logistics master

Evolution of Datasets

What are Fact stores?
Fact stores are a repository of facts or metrics of an entity that can be sliced by “n” of dimensions. In short, Fact is a
data about an entity at a given point in time
Think of what all entities together encompassed our business i.e ${project} marketplace: Bags, Items, Seller, Buyers,
Orders, Shipments
Imagine a big wide table . For instance, Fact sessions having 40 -50 cols (measures and dimensions) each capturing
data at a granular level of session
Two frameworks used to create Fact stores depending upon data volumes + complexity + maintainability
dbt framework  -
Orchestration on top of Lakehouse + Modularity + Clean code
Custom scala fact store framework -
Test driven development approach + Inbuilt -Data quality checks

Revenue Fact Store
Order
Discounts
UserItemProduct
Shipments
LoyaltyPromoSurcharges
Brand/Category
Bags
ReturnsSequences
RefundsKFC
PDT ->
BI -> Accounting Paid Orders | Marketing Paid Orders
Notebook | EDA | ML

Fact Store Approach
ETL ->
edw.revenue_metrics ->
Revenue Fact Store | BI
Notebook | EDA | ML

WHAT’S CHANGING
- Table
finance.revenue_live  →  edw.revenue_metrics
- Explore
Accounting Paid Orders  →  Revenue Fact Store
- Ownership
Fintech  →  DEWHAT’S CHANGING

WHY
- Better alignment with accounting books
- - Payouts
- - Discounts -Merch / New / Returning / Loyalty
- Legacy logic replaced with more reliable data points
- - rev_rec_date → revenue_entry_at
- - Item_price, surcharge
- Wider denormalized table encapsulating most joins and PDT usage
- Better for DS/DA to have a flat table rather than heavy multi -join query
- Fact store framework developed is testable by design and allows us to
developer better units testsWHY

Benefits and Add-Ons
- Speed -new explore works much faster
- Cleaner Looker experience -single flat table, better metric grouping
- Order Metrics introduced with symmetric aggregates [Looker feature]
- - Site credits, promo credits, seller credits
- Exclusive KFC metrics introduced
- - Revised Net Revenue calculation
- - Halo RevenueBenefits and Add -Ons

Benefits and Add-Ons
- Pre computed metrics like Gross Rev, Net Rev, Net2 etc available in table.
Formulae need not applied in downstream exploratory use cases.
- New fields added to tableBenefits and Add -Ons
concierge_bag_id | supplier_user_id | product_name
brand_id | rma_shipping_revenue | title_reason
category_id | potential_returned_price | title_at
listed_at | promo_name | title_ref_txn_type
returned_at | promo_cohort | original_concierge_bag_id
payout_policy | promo_type | reclaimed_items_in_order
final_sale | employee_type | user_created_at
brand_tier_id | merch_order_ind | user_first_login_at
adult_brand_tier_id | merch_2_0_order_ind | user_email
partner_type | bag_received_at | brand_name
listed_age | bag_processed_at | Service_level
listed_price | bag_type | Loyalty Points Awarded
paid_at | partner_campaign_description | Loyalty_tier_at_time_of_order
title_at | partner_campaign_code | Merch Categories L1 -L3
item_number | is_final_sale | User TP at time of Order
original_item_number | item_state |

Example
- See orders where KFC credits are redeemed -pullExample

Revenue Fact Store - What’s Next
Nov’23 - Decommission old table and explores
Oct’23 - Extended to core Marketing Metrics
Nov’23 - Enable Delivery Promise tracking (coming soon)
Sept’23 - Revenue Fact Store Launched
Future - Integrate with Ops Cost calculations

----------

### Example 5: SQL queries example input -

Text: SQL to check table completeness

Code:
{% macro check_table_completeness(schema, table, dt_column, run_date) -%}
WITH table_summary AS (
    SELECT
            MAX({{dt_column}}) AS last_updated_at
        FROM
            {{ schema }}.{{ table }}
            WHERE {{ dt_column }} >= DATE('{{ var("run_date") }}') - 10

)
SELECT last_updated_at
FROM table_summary
GROUP BY 1
HAVING NOT last_updated_at >= ({{ end_of_day(var('run_date')) }})
{%- endmacro %}

----------

### Example 6: SQL queries example input -

Text: SQL for end of the day anlaysis

Code:
{% macro end_of_day(iso_date) -%}
(SELECT
    MAKE_TIMESTAMP(curr_year, curr_month, curr_day, 23, 59, 59,'America/Los_Angeles') AS endofday_datetime_utc
    FROM (
    SELECT DATE_FORMAT(DATE('{{ iso_date }}'),'y') AS curr_year,
    DATE_FORMAT(DATE('{{ iso_date }}'),'MM') AS curr_month,
    DATE_FORMAT(DATE('{{ iso_date }}'),'dd') AS curr_day
    ))
{%- endmacro %}

----------

### Example 7: SQL queries example input -

Text: Active buyer SQL code

Code:
{{ config(
  schema = 'interim',
  materialized = 'table'
) }}

WITH active_buyer_stg01 AS (

  SELECT
    calendar_date,
    user_id
  FROM
    (
      SELECT
        DISTINCT orders.user_id user_id,
        C.calendar_date
      FROM
        {{ ref('users') }} AS users_v3
        LEFT JOIN {{ ref('orders') }} AS orders
        ON orders.user_id = users_v3.id
        AND orders.state = 'paid'
        LEFT JOIN {{ ref('order_products') }} AS order_products
        ON orders.id = order_products.order_id
        LEFT JOIN {{ ref('products') }} AS products
        ON order_products.product_id = products.id
        LEFT JOIN {{ ref('partitioned_item_orders_by_users_stg01') }} AS pseq_first_item_order
        ON users_v3.id = pseq_first_item_order.user_id
        AND pseq_first_item_order.item_order_sequence = 1
        LEFT JOIN {{ ref('orders') }} AS first_item_order
        ON pseq_first_item_order.order_id = first_item_order.id
        AND pseq_first_item_order.item_order_sequence = 1
        RIGHT JOIN {{ ref('calendar_days') }} C
        ON  from_utc_timestamp(to_utc_timestamp(first_item_order.purchased_at, 'UTC'), 'America/Los_Angeles') >= C.calendar_date - 365
        AND from_utc_timestamp(to_utc_timestamp(first_item_order.purchased_at, 'UTC'), 'America/Los_Angeles') < C.calendar_date
      WHERE
        LOWER(
          products.purchase_type
        ) LIKE LOWER('singleitem')
        AND (LOWER(orders.state) LIKE LOWER('paid'))
        AND first_item_order.id IS NOT NULL
        AND C.calendar_date BETWEEN date_add( CURRENT_TIMESTAMP, -1 ) AND CURRENT_TIMESTAMP
    ) --AND c.calendar_date BETWEEN '2020-02-01' and '2020-02-11');
),
FINAL AS (
  SELECT
    *
  FROM
    active_buyer_stg01
)
SELECT
  *
FROM
  FINAL

--------

### Example 8: SQL queries example input -

Text: Session utlis SQL

Code:

{% macro get_session_browser_device_struct() %}
    STRUCT(
        device_family,
        device_brand,
        device_name,
        device_version,
        device_class,
        device_category,
        screen_resolution,
        br_lang,
        br_renderengine
    ) AS browser_device
{% endmacro %}

{% macro get_first_page_url_struct() %}
    STRUCT(
        first_page_url,
        first_page_urlpath,
        first_page_urlquery,
        first_page_urlscheme,
        first_page_urlhost,
        first_page_urlfragment
    ) AS first_page_url
{% endmacro %}

{% macro get_last_page_url_struct() %}
    STRUCT(
        last_page_url,
        last_page_urlpath,
        last_page_urlquery,
        last_page_urlscheme,
        last_page_urlhost,
        last_page_urlfragment
    ) AS last_page_url
{% endmacro %}

{% macro get_first_deep_link_url_struct() %}
    STRUCT(
        first_deep_link_url,
        first_deep_link_urlpath,
        first_deep_link_urlquery,
        first_deep_link_urlfragment,
        first_deep_link_urlscheme
    ) AS first_deep_link_url
{% endmacro %}

{% macro get_last_deep_link_url_struct() %}
    STRUCT(
        last_deep_link_url,
        last_deep_link_urlpath,
        last_deep_link_urlquery,
        last_deep_link_urlfragment,
        last_deep_link_urlscheme
    ) AS last_deep_link_url
{% endmacro %}

{% macro get_session_referrer_struct() %}
    STRUCT(
        referrer AS refr_url,
        refr_urlpath,
        refr_urlquery,
        refr_urlscheme,
        refr_urlhost,
        refr_urlfragment,
        refr_medium,
        refr_source,
        refr_term
    ) AS session_referrer
{% endmacro %}

{% macro stitch_anonymous_sessions(
        relation = this
    ) %}
    MERGE INTO {{ relation }} AS s USING {{ ref('dim_anonymous_user_mapping') }} AS d_aum
    ON s.anonymous_id = d_aum.anonymous_id
    AND s.stitched_user_id = s.anonymous_id
    WHEN matched THEN
UPDATE
    SET s.stitched_user_id = d_aum.user_id
{% endmacro %}


{% macro get_session_user_struct() %}
    STRUCT(
        user_active_promotion,
        user_first_item_order_purchase_at,
        user_item_order_count,
        user_last_item_order_purchase_at,
        user_requested_bag_order_count,
        user_warehouse_id
    ) AS ctx_user
{% endmacro %}

{% macro get_session_marketing_query_params_struct() %}
    STRUCT(
        mkt_referral_code,
        mkt_referral_bucket,
        mkt_link_name,
        mkt_medium,
        mkt_source,
        mkt_campaign,
        mkt_term,
        mkt_content,
        mkt_clickid,
        mkt_network
    ) AS mkt
{% endmacro %}

-----------

### Example 8: Databricks document example -

Databricks Governance - Chicory
This article describes how to the Data Engineering team should fulfill different kinds of data access requests. It explains the general approach to governing assets on Databricks in the post Unity Catalog world and provides links to relevant Databricks documentation
Governance Overview - Unity Catalog works on the Identity Federation model, which means that any identity is maintained centrally at the account level and can be provisioned into the desired workspaces. Entities may be created in either workspace is automatically synced to the account and available to be added into other workspaces.

Some important things to note are :
* All access should be provisioned only through groups ( do NOT grant access to individual entities )
* Write access to production assets should be granted to Service Principal groups only
* Read access to production assets may be granted to user groups as needed

On-Boarding New Teams
Follow these steps to onboard a new team/group onto Databricks :
* Create these groups in prod Databricks workspace -
* * <Team-name>-grp
* * * This is the group for users which will have read-only access to prod assets.
* * * Add this group to the DE workspace as well.
* * * Add this group into the general-reader-group to provision :
* * * * Basic read access
* * * * Access to shared sandbox clusters
* * <Team-name>-sp-grp
* * * This group will hold the Service Principal which would be the Run As identity on production jobs.
* * * This group will have write access to prod assets.
* * * This group should NOT be exposed in the DE Workspace.
* * * This group is needed only if the team plans to schedule production jobs

-----------

# Real Data

Use the following text for your answer. Do not make anything up in your answer.

Text:
{input_text}
Output:

-----------

"""

entity_extraction = """
-Goal-
Given a text document that is relevant to E-commerce operations and data engineering aspects, identify all the entities required from the text to capture the key information and activities.
You are tasked in extracting entities and their relationships from each text or code chunk.
You specialize in identifying and visualizing relationships between entities within a business's ecosystem, helping companies uncover the hidden structure in their operations to drive smarter, data-backed decision-making
Next, define and report all relationships between the identified entities.
The dataset has customer return requests, capturing information on the overall return request, individual return items, and the logistics and financial aspects of the return process, including the refund method, warehouse operations.
The tables help track the return process and support refund processing, warehouse operations, and fraud detection.
Some entities example can look like -- visitors, logged-out users, transaction clusters, and other relevant groups, each of which plays a critical role in inventory management, customer behavior, order processing, and data-driven decision-making.
The report will focus on how these entities interact and where opportunities for optimization exist—whether through improvements in customer satisfaction, operational efficiency, or business growth.


-Qualifications-
You are an experienced professional within the e-commerce environment having the following knowledge.
- Strong proficiency in SQL, Python, or R for data manipulation and analysis.
- Experienced in developing ETL processes to extract, transform, load data from various sources into data warehouses and real-time analytics platforms.
- Experience with ETLeap for automated data pipelines, and expertise in AWS (including services like S3, Redshift, Lambda) for cloud-based data engineering tasks.
- Strong understanding of relational databases, data warehousing, and big data technologies (e.g., Redshift, Snowflake, BigQuery).
- Experience with automation tools for data workflow orchestration, such as Airflow or DBT (Data Build Tool)

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, capitalized
- entity_type: Suggest several labels or categories for the entity. The categories should not be specific, but should be as general as possible.
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: a clear explanation of how the source and target entities are related, specific to the eCommerce operations.
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity (scale from 1 to 10)
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)

3. Return output. Provide the list of all entities and relationships in the primary language of the provided text (English) as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. Translate, if needed. If you have to translate into The primary language of the provided text is English., just translate the descriptions, nothing else!

5. Completion. Once the entities and relationships are identified and formatted correctly, output {completion_delimiter} to signify completion.

######################
-Examples-
######################
Example 1:
Entity_types: ORGANIZATION,PERSON
Text:
The Verdantis's Central Institution is scheduled to meet on Monday and Thursday, with the institution planning to release its latest policy decision on Thursday at 1:30 p.m. PDT, followed by a press conference where Central Institution Chair Martin Smith will take questions. Investors expect the Market Strategy Committee to hold its benchmark interest rate steady in a range of 3.5%-3.75%.
######################
Output:
("entity"{tuple_delimiter}CENTRAL INSTITUTION{tuple_delimiter}ORGANIZATION{tuple_delimiter}The Central Institution is the Federal Reserve of Verdantis, which is setting interest rates on Monday and Thursday)
{record_delimiter}
("entity"{tuple_delimiter}MARTIN SMITH{tuple_delimiter}PERSON{tuple_delimiter}Martin Smith is the chair of the Central Institution)
{record_delimiter}
("entity"{tuple_delimiter}MARKET STRATEGY COMMITTEE{tuple_delimiter}ORGANIZATION{tuple_delimiter}The Central Institution committee makes key decisions about interest rates and the growth of Verdantis's money supply)
{record_delimiter}
("relationship"{tuple_delimiter}MARTIN SMITH{tuple_delimiter}CENTRAL INSTITUTION{tuple_delimiter}Martin Smith is the Chair of the Central Institution and will answer questions at a press conference{tuple_delimiter}9)
{completion_delimiter}

######################
Example 2:
Entity_types: ORGANIZATION
Text:
TechGlobal's (TG) stock skyrocketed in its opening day on the Global Exchange Thursday. But IPO experts warn that the semiconductor corporation's debut on the public markets isn't indicative of how other newly listed companies may perform.

TechGlobal, a formerly public company, was taken private by Vision Holdings in 2014. The well-established chip designer says it powers 85% of premium smartphones.
######################
Output:
("entity"{tuple_delimiter}TECHGLOBAL{tuple_delimiter}ORGANIZATION{tuple_delimiter}TechGlobal is a stock now listed on the Global Exchange which powers 85% of premium smartphones)
{record_delimiter}
("entity"{tuple_delimiter}VISION HOLDINGS{tuple_delimiter}ORGANIZATION{tuple_delimiter}Vision Holdings is a firm that previously owned TechGlobal)
{record_delimiter}
("relationship"{tuple_delimiter}TECHGLOBAL{tuple_delimiter}VISION HOLDINGS{tuple_delimiter}Vision Holdings formerly owned TechGlobal from 2014 until present{tuple_delimiter}5)
{completion_delimiter}

######################
Example 3:
Entity_types: ORGANIZATION,GEO,PERSON
Text:
Five Aurelians jailed for 8 years in Firuzabad and widely regarded as hostages are on their way home to Aurelia.

The swap orchestrated by Quintara was finalized when $8bn of Firuzi funds were transferred to financial institutions in Krohaara, the capital of Quintara.

The exchange initiated in Firuzabad's capital, Tiruzia, led to the four men and one woman, who are also Firuzi nationals, boarding a chartered flight to Krohaara.

They were welcomed by senior Aurelian officials and are now on their way to Aurelia's capital, Cashion.

The Aurelians include 39-year-old businessman Samuel Namara, who has been held in Tiruzia's Alhamia Prison, as well as journalist Durke Bataglani, 59, and environmentalist Meggie Tazbah, 53, who also holds Bratinas nationality.
######################
Output:
("entity"{tuple_delimiter}FIRUZABAD{tuple_delimiter}GEO{tuple_delimiter}Firuzabad held Aurelians as hostages)
{record_delimiter}
("entity"{tuple_delimiter}AURELIA{tuple_delimiter}GEO{tuple_delimiter}Country seeking to release hostages)
{record_delimiter}
("entity"{tuple_delimiter}QUINTARA{tuple_delimiter}GEO{tuple_delimiter}Country that negotiated a swap of money in exchange for hostages)
{record_delimiter}
{record_delimiter}
("entity"{tuple_delimiter}TIRUZIA{tuple_delimiter}GEO{tuple_delimiter}Capital of Firuzabad where the Aurelians were being held)
{record_delimiter}
("entity"{tuple_delimiter}KROHAARA{tuple_delimiter}GEO{tuple_delimiter}Capital city in Quintara)
{record_delimiter}
("entity"{tuple_delimiter}CASHION{tuple_delimiter}GEO{tuple_delimiter}Capital city in Aurelia)
{record_delimiter}
("entity"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}PERSON{tuple_delimiter}Aurelian who spent time in Tiruzia's Alhamia Prison)
{record_delimiter}
("entity"{tuple_delimiter}ALHAMIA PRISON{tuple_delimiter}GEO{tuple_delimiter}Prison in Tiruzia)
{record_delimiter}
("entity"{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}PERSON{tuple_delimiter}Aurelian journalist who was held hostage)
{record_delimiter}
("entity"{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}PERSON{tuple_delimiter}Bratinas national and environmentalist who was held hostage)
{record_delimiter}
("relationship"{tuple_delimiter}FIRUZABAD{tuple_delimiter}AURELIA{tuple_delimiter}Firuzabad negotiated a hostage exchange with Aurelia{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}QUINTARA{tuple_delimiter}AURELIA{tuple_delimiter}Quintara brokered the hostage exchange between Firuzabad and Aurelia{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}QUINTARA{tuple_delimiter}FIRUZABAD{tuple_delimiter}Quintara brokered the hostage exchange between Firuzabad and Aurelia{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}ALHAMIA PRISON{tuple_delimiter}Samuel Namara was a prisoner at Alhamia prison{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}Samuel Namara and Meggie Tazbah were exchanged in the same hostage release{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}Samuel Namara and Durke Bataglani were exchanged in the same hostage release{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}Meggie Tazbah and Durke Bataglani were exchanged in the same hostage release{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}FIRUZABAD{tuple_delimiter}Samuel Namara was a hostage in Firuzabad{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}FIRUZABAD{tuple_delimiter}Meggie Tazbah was a hostage in Firuzabad{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}FIRUZABAD{tuple_delimiter}Durke Bataglani was a hostage in Firuzabad{tuple_delimiter}2)
{completion_delimiter}

######################
Example 4:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text:
High-level description:
This table is used to track customer order returns. It includes information on order IDs, customer details, items purchased, quantities, prices, payment methods, shipping status, and delivery dates.
It stores return requests from customers. The header represents one RMA (Return Merchandise Authorization) ID, containing common attributes applied to the entire return. Refer to the order_return_lines table for a list of items.
Ways to access the data:
- Table: mysql_xxx_order_returns.order_return_headers
- Looker explore: Order Dataset
Sample Looker pulls:
- Order details dashboard
Most important fields:
- Data dictionary with all column definitions
ETL databricks notebook: redshift, lakehouse
Airflow DAG: redshift, lakehouse
Tips, gotchas, and FAQs:
import s3fs
fs = s3fs.S3FileSystem(anon=False)
files = fs.ls('s3://../..')
df_orders_all = sqlContext.read.parquet('s3://../..')
######################
Output:
("entity"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}DATA STRUCTURE{tuple_delimiter}A table used to track customer return requests, including RMA ID, order IDs, user information, return status, refund details, and return processing history.)
{record_delimiter}
("entity"{tuple_delimiter}ORDER RETURN LINE{tuple_delimiter}DATA STRUCTURE{tuple_delimiter}Represents individual items within a return request, linked to the order return header. It includes details such as reason code, refund status, and whether the item was returned or refunded.)
{record_delimiter}
("entity"{tuple_delimiter}CUSTOMER{tuple_delimiter}CATEGORY{tuple_delimiter}Represents the customer initiating the return request. Includes customer behavior, refund preferences, and return history.)
{record_delimiter}
("entity"{tuple_delimiter}RETURN STATE{tuple_delimiter}CATEGORY{tuple_delimiter}Defines the various stages in the return lifecycle (e.g., initiated, inbound, received, processed), helping track return progress.)
{record_delimiter}
("entity"{tuple_delimiter}RETURN REASON{tuple_delimiter}CATEGORY{tuple_delimiter}Represents the reason for the return (e.g., defective item, unwanted product), helping analyze trends and optimize customer service or inventory management.)
{record_delimiter}
("entity"{tuple_delimiter}REFUND METHOD{tuple_delimiter}CATEGORY{tuple_delimiter}Represents the method used for issuing a refund (e.g., credit card, PayPal, store credit).)
{record_delimiter}
("entity"{tuple_delimiter}WAREHOUSE{tuple_delimiter}CATEGORY{tuple_delimiter}Represents a physical location or facility where returns are received, processed, or stored after being returned.)
{record_delimiter}
("entity"{tuple_delimiter}RETURN FRAUD{tuple_delimiter}CATEGORY{tuple_delimiter}Indicates potential fraudulent return behaviors such as excessive returns or false claims. Patterns of fraud are tracked and analyzed to prevent loss.)
{record_delimiter}
("entity"{tuple_delimiter}RETURN PROCESSING TIME{tuple_delimiter}CATEGORY{tuple_delimiter}Represents the time taken to process a return request from initiation to completion, helping to measure operational efficiency.)
{record_delimiter}
("entity"{tuple_delimiter}REFUND{tuple_delimiter}CATEGORY{tuple_delimiter}Represents the financial transaction issued after a return is processed and accepted, reimbursing the customer for the returned item(s).)
{record_delimiter}

("relationship"{tuple_delimiter}ORDER RETURN LINE{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}Each order return line (individual item) is linked to a specific order return header, which represents the full return request for the customer.{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}CUSTOMER{tuple_delimiter}Each order return header is associated with a customer, who initiates the return request. The customer’s history, preferences, and return frequency can impact return handling.{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}RETURN STATE{tuple_delimiter}The order return header tracks the state of the return request, which progresses through various stages such as initiated, inbound, and received.{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN LINE{tuple_delimiter}RETURN REASON{tuple_delimiter}Each item in the return request has a specific return reason, such as defective or unwanted item, which helps businesses understand customer motivations and improve inventory management.{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}REFUND METHOD{tuple_delimiter}The order return header specifies the method for issuing a refund to the customer, whether through a credit card, PayPal, or store credit.{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}WAREHOUSE{tuple_delimiter}Each return request is linked to a warehouse, which receives, processes, or stores returned items. The warehouse plays a crucial role in handling returns and restocking items.{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}RETURN FRAUD{tuple_delimiter}Each order return header may be flagged for potential fraud based on suspicious activity, such as excessive returns from a single customer or false claims.{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN LINE{tuple_delimiter}REFUND{tuple_delimiter}Each return line can have an associated refund, which is processed once the return is accepted. The refund is issued based on the value of the returned item.{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER RETURN HEADER{tuple_delimiter}RETURN PROCESSING TIME{tuple_delimiter}The time it takes to process a return is measured at the order return header level, providing insights into return processing efficiency.{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}RETURN FRAUD{tuple_delimiter}CUSTOMER{tuple_delimiter}Fraudulent return patterns are tracked at the customer level, helping to identify suspicious return behaviors such as multiple returns or false claims.{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}RETURN FRAUD{tuple_delimiter}ORDER RETURN LINE{tuple_delimiter}Items in a return may be flagged for fraud if the return behavior or return reason is unusual or inconsistent with expected patterns.{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}RETURN PROCESSING TIME{tuple_delimiter}ORDER RETURN LINE{tuple_delimiter}The time to process individual items in a return is tracked at the order return line level, contributing to overall return processing time.{tuple_delimiter}6)
{completion_delimiter}

######################
Example 5:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text:
To provide the pricing/authentication team with feedback from one another during the process of multi-level authentication, ensuring a rigorous review for item authenticity.
The `item_authentication_reviews` table stores detailed records of multi-level authentication decisions made for items during the authentication process. Each record includes provisional and final authentication decisions, the associated operators, reasoning for decisions, and a reference link for verifying item authenticity.
"source.${project}_operations.item_authentication_reviews"
code: sql queries
<table>
< returns>
######################
Output:
("entity"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}DATABASE TABLE{tuple_delimiter}A table storing item authentication review details)
{record_delimiter}
("entity"{tuple_delimiter}id{tuple_delimiter}COLUMN{tuple_delimiter}Unique identifier for the authentication review record)
{record_delimiter}
("entity"{tuple_delimiter}item_id{tuple_delimiter}COLUMN{tuple_delimiter}Unique identifier for the item being authenticated)
{record_delimiter}
("entity"{tuple_delimiter}created_at{tuple_delimiter}COLUMN{tuple_delimiter}Date and time when the authentication review was created)
{record_delimiter}
("entity"{tuple_delimiter}final_decision{tuple_delimiter}COLUMN{tuple_delimiter}Final decision of the second authentication stage)
{record_delimiter}
("entity"{tuple_delimiter}final_details{tuple_delimiter}COLUMN{tuple_delimiter}Reasoning or details for the final authentication decision)
{record_delimiter}
("entity"{tuple_delimiter}final_operator_id{tuple_delimiter}COLUMN{tuple_delimiter}ID of the operator who made the final authentication decision)
{record_delimiter}
("entity"{tuple_delimiter}provisional_decision{tuple_delimiter}COLUMN{tuple_delimiter}Decision made during the first (provisional) authentication stage)
{record_delimiter}
("entity"{tuple_delimiter}provisional_details{tuple_delimiter}COLUMN{tuple_delimiter}Reasoning or details for the provisional authentication decision)
{record_delimiter}
("entity"{tuple_delimiter}provisional_operator_id{tuple_delimiter}COLUMN{tuple_delimiter}ID of the operator who made the provisional authentication decision)
{record_delimiter}
("entity"{tuple_delimiter}link{tuple_delimiter}COLUMN{tuple_delimiter}Reference link used for authenticity verification)
{record_delimiter}
("entity"{tuple_delimiter}notes{tuple_delimiter}COLUMN{tuple_delimiter}Additional notes about the item being authenticated)
{record_delimiter}
("entity"{tuple_delimiter}${project}_operations{tuple_delimiter}SCHEMA{tuple_delimiter}The database schema where the item_authentication_reviews table is stored)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}id{tuple_delimiter}item_authentication_reviews is identified by the id column{tuple_delimiter}1)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}item_id{tuple_delimiter}Each authentication review is linked to a unique item via item_id{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}created_at{tuple_delimiter}Each authentication review has a creation timestamp stored in created_at{tuple_delimiter}3)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}final_decision{tuple_delimiter}An authentication review includes a final decision made during the second authentication stage{tuple_delimiter}4)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}final_details{tuple_delimiter}Final decision reasoning is stored in final_details{tuple_delimiter}5)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}final_operator_id{tuple_delimiter}Final authentication decision is made by the operator identified by final_operator_id{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}provisional_decision{tuple_delimiter}Each review includes a provisional decision made during the first authentication stage{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}provisional_details{tuple_delimiter}Provisional decision reasoning is stored in provisional_details{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}provisional_operator_id{tuple_delimiter}Provisional authentication decision is made by the operator identified by provisional_operator_id{tuple_delimiter}9)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}link{tuple_delimiter}Each review may include a reference link for authenticity check stored in link{tuple_delimiter}10)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}notes{tuple_delimiter}Each review may include additional notes about the item stored in notes{tuple_delimiter}11)
{record_delimiter}
("relationship"{tuple_delimiter}item_authentication_reviews{tuple_delimiter}${project}_operations{tuple_delimiter}The item_authentication_reviews table is part of the ${project}_operations schema{tuple_delimiter}12)
{completion_delimiter}

######################
Example 6:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text:
Item order details

SQL Code:
{{ config(
    materialized = 'table',
    post_hook="ALTER TABLE {{ this }} SET TBLPROPERTIES ( 'redshift_table' = 'item_order_details' ,'redshift_schema' = 'mysql_${project}_v2_production', 'lh_ready' = 'true' )",
) }}


WITH item_order_details AS (
    SELECT
        o.id as order_id,
        COUNT(DISTINCT(i.id)) as item_count,
        COUNT(DISTINCT(CASE WHEN lower(i.gender) = 'women'  THEN i.id ELSE NULL END)) as womens_item_count,
        COUNT(DISTINCT(CASE WHEN lower(i.gender) = 'boys'   THEN i.id ELSE NULL END)) as boys_item_count,
        COUNT(DISTINCT(CASE WHEN lower(i.gender) = 'girls'  THEN i.id ELSE NULL END)) as girls_item_count,
        COUNT(DISTINCT(CASE WHEN lower(i.gender) = 'unisex' THEN i.id ELSE NULL END)) as unisex_item_count,
        COUNT(DISTINCT(s.id)) as shipment_count,
        current_timestamp() as utc_load_dt,
        from_utc_timestamp(to_utc_timestamp(current_timestamp(), 'UTC'), 'America/Los_Angeles') as pst_load_dt
      FROM {{ ref('orders') }} o
INNER JOIN {{ ref('order_products') }} op
        on op.order_id = o.id
INNER JOIN {{ ref('products') }} p
        on p.id = op.product_id
INNER JOIN {{ ref('shop_items') }} i
        on i.id = op.item_id
 LEFT JOIN {{ ref('shop_shipments') }} s
        on s.order_id = o.id
     WHERE lower(p.purchase_type) = 'singleitem'
       AND lower(o.state) = 'paid'
  GROUP BY o.id
),
FINAL AS (
  SELECT
    *
  FROM
    item_order_details
)
SELECT
  *
FROM
  FINAL

######################
Output:
("entity"{tuple_delimiter}ITEM_ORDER_DETAILS{tuple_delimiter}TABLE{tuple_delimiter}A materialized table that tracks order details including item counts by gender, shipment counts, and timestamps in UTC and PST)
{record_delimiter}
("entity"{tuple_delimiter}ORDERS{tuple_delimiter}TABLE{tuple_delimiter}A table containing order data used in the item order details calculation)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_PRODUCTS{tuple_delimiter}TABLE{tuple_delimiter}A table linking orders and products, used to calculate item order details)
{record_delimiter}
("entity"{tuple_delimiter}PRODUCTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing product information used to filter purchase types and determine item counts)
{record_delimiter}
("entity"{tuple_delimiter}SHOP_ITEMS{tuple_delimiter}TABLE{tuple_delimiter}A table containing shop items data used to calculate item counts by gender)
{record_delimiter}
("entity"{tuple_delimiter}SHOP_SHIPMENTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing shipment data used to calculate shipment counts)
{record_delimiter}
("entity"{tuple_delimiter}MATERIALIZED TABLE{tuple_delimiter}RESOURCES{tuple_delimiter}A table configured with TBLPROPERTIES for Redshift and Lakehouse readiness)
{record_delimiter}
("entity"{tuple_delimiter}SQL CODE{tuple_delimiter}CODE{tuple_delimiter}SQL script used to create and configure the materialized table item_order_details)
{record_delimiter}
("entity"{tuple_delimiter}POST_HOOK{tuple_delimiter}CODE{tuple_delimiter}A post-hook operation that configures table properties for Redshift)
{record_delimiter}
("relationship"{tuple_delimiter}ITEM_ORDER_DETAILS{tuple_delimiter}ORDERS{tuple_delimiter}The item_order_details table aggregates data from the orders table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ITEM_ORDER_DETAILS{tuple_delimiter}ORDER_PRODUCTS{tuple_delimiter}The item_order_details table aggregates data from the order_products table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ITEM_ORDER_DETAILS{tuple_delimiter}PRODUCTS{tuple_delimiter}The item_order_details table aggregates data from the products table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ITEM_ORDER_DETAILS{tuple_delimiter}SHOP_ITEMS{tuple_delimiter}The item_order_details table aggregates data from the shop_items table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ITEM_ORDER_DETAILS{tuple_delimiter}SHOP_SHIPMENTS{tuple_delimiter}The item_order_details table aggregates data from the shop_shipments table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}SQL CODE{tuple_delimiter}POST_HOOK{tuple_delimiter}The SQL code contains a post-hook operation to set TBLPROPERTIES for the materialized table{tuple_delimiter}6)
{completion_delimiter}

######################
Example 7:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text:

Text: Order metrics
SQL code:

{{
  config(
    schema = 'edw',
    materialized='table',
    tags = ["revenue_metrics","pdt_converted_model","order_promos_pdt","acctg_paid_orders_merch_orders_pdt","mktg_item_order_details.pdt"]
  )
}}

WITH temp AS(
		   SELECT o.id AS order_id,
		   		  o.user_id,
		   		  o.purchased_at,
                  COUNT(DISTINCT CASE WHEN p.purchase_type ILIKE 'singleitem' AND o.state ILIKE 'paid' THEN op.item_id END) AS item_count,
                  COUNT(DISTINCT op.id) AS op_count,
          		  COUNT(DISTINCT CASE WHEN p.name = 'Reclaimed Item' AND o.state ILIKE 'paid' THEN op.item_id END) AS reclaimed_item_count,
          		  MAX(CASE WHEN new_promo.revenue_category = 'MERCH' THEN 1
                           ELSE CASE WHEN ((dt.name = 'merch') OR (COALESCE(new_promo.name, pr.name) ILIKE 'merch_%') AND op.discount > 0) THEN 1
                                ELSE 0 END
                      END) AS is_merch_order,
                  MAX(CASE WHEN new_promo.type = 'COUPON_ADVERTISED' THEN 1 ELSE 0 END) AS is_merch_2_0_order,
          		  MAX(COALESCE(new_promo.name, pr.name)) AS promo_name,
          		  MAX(COALESCE(new_promo.cohort, pr.cohort)) AS promo_cohort,
                  MAX(new_promo.promotion_group) AS promotion_group,
          		  MAX(new_promo.type) AS promo_type,
          		  MAX(CASE WHEN p.purchase_type ilike '%shipping%' AND opt.type_name <> 'refund' THEN p.name END) AS shipping_product_name,
				  SUM(CASE WHEN p.purchase_type ilike '%shipping%' AND opt.type_name <> 'refund'
           				   THEN (COALESCE(op.price,0) + COALESCE(op.shipping,0)) / 100e0
       				  ELSE 0 END) AS order_shipping_total,
          		  MAX(CASE WHEN e.operator_id IS NOT NULL THEN 'DC'
               		   WHEN e.promotion_id IS NOT NULL THEN 'Corporate'
               	       ELSE NULL END ) AS employee_type,
               	  MAX(sio.item_order_seq) AS user_tp_at_purchase
             FROM {{ ref('orders') }} o
        LEFT JOIN {{ ref('order_products') }} op
               ON op.order_id = o.id
        LEFT JOIN {{ ref('products') }} p
               ON p.id = op.product_id
        LEFT JOIN {{ ref('coupons') }} c
        	   ON c.id = op.coupon_id AND op.coupon_id IS NOT NULL
        LEFT JOIN {{ ref('legacy_promotions') }} pr
        	   ON pr.id = c.promotion_id
        LEFT JOIN {{ ref('promotions') }} new_promo
        	   ON c.cohort = new_promo.cohort
        LEFT JOIN {{ ref('employee_promotions') }} e
        	   ON (c.promotion_id = e.promotion_id AND c.user_id = e.user_id)
		LEFT JOIN {{ ref('order_product_discounts') }} opd
       		   ON op.id = opd.order_product_id
		LEFT JOIN {{ ref('discount_types')}} dt
       		   ON opd.discount_type_id = dt.id
       	LEFT JOIN {{ ref('seq_item_order')}} sio
       	       ON o.id = sio.order_id
		LEFT JOIN {{ ref('order_product_types') }} opt
       		   ON op.order_product_type_id = opt.id
         GROUP BY 1,2,3
         ),
ncct AS (		  SELECT cash_credits.order_id AS order_id,
                    	 SUM(CASE WHEN cash_credits_via_ccd.credit_type IN ('Non-Cashoutable Order Refund', 'Non-Cashoutable Order Refund of Items Kept For Credit')
                    	 THEN cash_credit_debits.amount ELSE 0 END) AS non_cash_credits_from_order_refund
             		FROM {{ ref('cash_credits') }} AS cash_credits
               LEFT JOIN {{ ref('cash_credit_debits') }} AS cash_credit_debits
                      ON cash_credits.id = cash_credit_debits.debit_id
                     AND cash_credit_debits._fivetran_deleted = false
               LEFT JOIN {{ ref('cash_credits') }} AS cash_credits_via_ccd
                      ON cash_credits_via_ccd.id = cash_credit_debits.credit_id
                     AND cash_credits_via_ccd._fivetran_deleted = false
             	   WHERE cash_credits_via_ccd.credit_type IN ('Non-Cashoutable Order Refund','Non-Cashoutable Order Refund of Items Kept For Credit')
             	     AND cash_credits._fivetran_deleted = false
                GROUP BY 1
),
kfc_redeem AS (		  SELECT
							 COALESCE(debits.order_id,cch.order_id) AS order_id,
							 SUM(COALESCE(ccd.amount/ 100e0,0e0)) AS kfc_amount_used_from_prev_order

						FROM {{ ref('keep_for_credits_offers') }} kfco
				  INNER JOIN {{ ref('cash_credits') }} credits ON credits.id = kfco.cash_credit_id
						 AND credits.credit_type = 'Non-Cashoutable Order Refund of Items Kept For Credit'
				  INNER JOIN {{ ref('cash_credit_debits') }} ccd
						  ON ccd.credit_id = credits.id AND credits.state = 'active'
				  INNER JOIN {{ ref('cash_credits') }} debits
						  ON ccd.debit_id = debits.id AND debits.state = 'active'
				  LEFT JOIN {{ ref('cash_credit_holds') }} cch
						  ON cch.item_debit_id = debits.id OR cch.shipping_debit_id = debits.id
					   WHERE kfco.state != 'never_shown'
						 AND debits.credit_type != 'Expiration'
					GROUP BY 1
),
ord_pymt AS (
				SELECT
					  order_id,
					  SUM(coalesce(capture_amount / 100e0,0e0)) AS capture_amount,
					  SUM(coalesce(cashoutable_credits_amount/ 100e0,0e0)) AS cashoutable_credits_amount,
					  SUM(coalesce(noncashoutable_credits_amount / 100e0,0e0)) AS noncashoutable_credits_amount,
					  SUM(coalesce(settled_amount / 100e0,0e0)) AS settled_amount,
					  SUM(coalesce(site_credits_amount / 100e0,0e0)) AS site_credits_amount,
					  SUM(coalesce(seller_credits_amount / 100e0,0e0)) AS seller_credits_amount,
					  SUM(coalesce(promo_credits_amount / 100e0,0e0)) AS promo_credits_amount
                FROM {{ ref('order_payments') }} opymt
            GROUP BY 1
),
loyalty_ncc_pymt AS (
                SELECT
                       orders.id as order_id,
                       SUM(ccd.amount) / 100e0 AS loyalty_credits_amount
                  FROM {{ ref('cash_credits') }} as cc
                  JOIN {{ ref('cash_credit_debits') }} as ccd
                    ON ccd.credit_id = cc.id
                  JOIN {{ ref('cash_credits') }} as dd
                    ON dd.id = ccd.debit_id
             LEFT JOIN {{ ref('orders') }} AS orders
                    ON orders.id = dd.order_id
                 WHERE cc.credit_type IN ('Loyalty Earned Reward Credit', 'Loyalty Earned Reward Credit Refund')
                   AND from_utc_timestamp(orders.purchased_at, 'America/Los_Angeles') >= '2024-01-01'
                   AND from_utc_timestamp(ccd.created_at, 'America/Los_Angeles') >= '2024-01-01'
              GROUP BY 1
),
t_mobile_credits AS (
                SELECT
                    cte.order_id,
                    SUM(cte.amount_applied) / 100e0 as t_mobile_credits_amount
                  FROM (
                    SELECT
                           COALESCE(cch.order_id, dd.order_id) as order_id,
                           dd.credit_type as debit_type,
                           CASE WHEN cch.id IS NOT NULL THEN 'cch' ELSE 'debit.order_id' END as order_id_source,
                           FROM_UTC_TIMESTAMP(ccd.created_at,'America/Los_Angeles') as redemption_date,
                           SUM(ccd.amount) as amount_applied
                      FROM {{ ref('cash_credits') }} as cc
                      JOIN {{ ref('cash_credit_debits') }} as ccd
                        ON ccd.credit_id = cc.id
                      JOIN {{ ref('cash_credits') }} as dd
                        ON ccd.debit_id = dd.id
                       AND dd.state = 'active'
                 LEFT JOIN {{ ref('cash_credit_holds') }} as cch
                        ON cch.item_debit_id = dd.id OR cch.shipping_debit_id = dd.id
                     WHERE cc.credit_type = 'Promotional Credit'
                       AND cc.description IN ('T-Mobile Tuesday promotional credit (Expires 4/30/24)')
                GROUP BY 1, 2, 3, 4
            ) as cte
                LEFT JOIN {{ ref('orders') }} as orders
                       ON orders.id = cte.order_id
                    WHERE from_utc_timestamp(orders.purchased_at, 'America/Los_Angeles') >= '2024-01-01'
                      AND cte.redemption_date >= '2024-01-01'
                      AND orders.state = 'paid'
                 GROUP BY 1
),

FINAL AS (
SELECT
t.order_id,
t.user_id,
t.purchased_at,
t.item_count,
t.op_count,
t.reclaimed_item_count,
t.is_merch_order,
t.is_merch_2_0_order,
CASE WHEN kr.order_id IS NOT NULL THEN 1 ELSE 0 END AS is_kfc_redeem_order,
coalesce(kr.kfc_amount_used_from_prev_order, 0e0) as kfc_amount_used_from_prev_order,
t.promo_name,
t.promo_cohort,
t.promotion_group,
t.promo_type,
t.shipping_product_name,
t.order_shipping_total,
t.employee_type,
t.user_tp_at_purchase,
ord_pymt.capture_amount,
ord_pymt.cashoutable_credits_amount,
ord_pymt.noncashoutable_credits_amount,
coalesce(n.non_cash_credits_from_order_refund, 0e0) as non_cash_credits_from_order_refund,
ord_pymt.settled_amount,
ord_pymt.site_credits_amount,
ord_pymt.seller_credits_amount,
ord_pymt.promo_credits_amount,
coalesce(loyalty_ncc_pymt.loyalty_credits_amount, 0e0) as loyalty_credits_amount,
coalesce(t_mobile_credits.t_mobile_credits_amount, 0e0) as t_mobile_credits_amount
FROM temp t
LEFT JOIN ncct n ON (t.order_id = n.order_id)
LEFT JOIN kfc_redeem kr ON (t.order_id = kr.order_id)
LEFT JOIN ord_pymt ON (ord_pymt.order_id = t.order_id)
LEFT JOIN loyalty_ncc_pymt on (loyalty_ncc_pymt.order_id=t.order_id)
LEFT JOIN t_mobile_credits on (t_mobile_credits.order_id=t.order_id)
)

SELECT
order_id,
user_id,
purchased_at,
item_count,
op_count,
reclaimed_item_count,
is_merch_order,
is_merch_2_0_order,
is_kfc_redeem_order,
kfc_amount_used_from_prev_order,
promo_name,
promo_cohort,
promotion_group,
promo_type,
shipping_product_name,
order_shipping_total,
employee_type,
user_tp_at_purchase,
capture_amount,
cashoutable_credits_amount,
noncashoutable_credits_amount,
non_cash_credits_from_order_refund,
settled_amount,
site_credits_amount,
seller_credits_amount,
promo_credits_amount,
loyalty_credits_amount,
t_mobile_credits_amount,
current_user AS audit_created_by,
current_timestamp() AS audit_created_at
FROM FINAL

######################
Output:
("entity"{tuple_delimiter}ORDER_METRICS{tuple_delimiter}TABLE{tuple_delimiter}A materialized table in the schema 'edw' that tracks metrics related to orders, promotions, and payments)
{record_delimiter}
("entity"{tuple_delimiter}ORDERS{tuple_delimiter}TABLE{tuple_delimiter}A table containing order details used in metrics calculations)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_PRODUCTS{tuple_delimiter}TABLE{tuple_delimiter}A table linking orders and products for metrics calculations)
{record_delimiter}
("entity"{tuple_delimiter}PRODUCTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing product information used for filtering and aggregation in order metrics)
{record_delimiter}
("entity"{tuple_delimiter}COUPONS{tuple_delimiter}TABLE{tuple_delimiter}A table containing coupon data linked to orders and promotions)
{record_delimiter}
("entity"{tuple_delimiter}LEGACY_PROMOTIONS{tuple_delimiter}TABLE{tuple_delimiter}A table containing historical promotion data used in metrics calculations)
{record_delimiter}
("entity"{tuple_delimiter}PROMOTIONS{tuple_delimiter}TABLE{tuple_delimiter}A table containing current promotions data for aggregation and filtering in order metrics)
{record_delimiter}
("entity"{tuple_delimiter}EMPLOYEE_PROMOTIONS{tuple_delimiter}TABLE{tuple_delimiter}A table linking employees and promotions for determining employee-related metrics)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_PRODUCT_DISCOUNTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing discount information linked to order products)
{record_delimiter}
("entity"{tuple_delimiter}DISCOUNT_TYPES{tuple_delimiter}TABLE{tuple_delimiter}A table containing discount type metadata for filtering order metrics)
{record_delimiter}
("entity"{tuple_delimiter}SEQ_ITEM_ORDER{tuple_delimiter}TABLE{tuple_delimiter}A table linking sequential item order data for purchase analysis)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_PRODUCT_TYPES{tuple_delimiter}TABLE{tuple_delimiter}A table containing product type data linked to order products for metrics calculations)
{record_delimiter}
("entity"{tuple_delimiter}CASH_CREDITS{tuple_delimiter}TABLE{tuple_delimiter}A table containing cash credit data for calculating metrics like loyalty credits and non-cash credits)
{record_delimiter}
("entity"{tuple_delimiter}CASH_CREDIT_DEBITS{tuple_delimiter}TABLE{tuple_delimiter}A table linking cash credit debits to orders for payment metrics)
{record_delimiter}
("entity"{tuple_delimiter}CASH_CREDIT_HOLDS{tuple_delimiter}TABLE{tuple_delimiter}A table containing data on cash credit holds for order metrics)
{record_delimiter}
("entity"{tuple_delimiter}KEEP_FOR_CREDITS_OFFERS{tuple_delimiter}TABLE{tuple_delimiter}A table linking promotional credits to orders for metrics calculations)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_PAYMENTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing payment details linked to orders for calculating payment metrics)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER_METRICS{tuple_delimiter}ORDERS{tuple_delimiter}The order_metrics table aggregates data from the orders table for calculating metrics{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER_METRICS{tuple_delimiter}ORDER_PRODUCTS{tuple_delimiter}The order_metrics table aggregates data from the order_products table for calculating item-related metrics{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER_METRICS{tuple_delimiter}PROMOTIONS{tuple_delimiter}The order_metrics table integrates promotion data from the promotions table to calculate metrics related to discounts and promotions{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER_METRICS{tuple_delimiter}CASH_CREDITS{tuple_delimiter}The order_metrics table aggregates data from cash_credits to calculate metrics like loyalty and non-cash credits{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}ORDER_METRICS{tuple_delimiter}ORDER_PAYMENTS{tuple_delimiter}The order_metrics table aggregates payment details from order_payments for financial metrics{tuple_delimiter}6)
{completion_delimiter}

######################
Example 8:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text: Concierge Bag Processing Fee

Table:
Data | Model | functional area
concierge_bag_processing_fees  | parnter_id |
concierge_bag_processing_fees | concierge_bag_id | the bag that the fee is applied on
concierge_bag_processing_fees | partner_ap_invoice_id | if the fee is batched for an invoice this is the foreign key used
concierge_bag_processing_fees | state | pending/canceled/batched/invoiced
concierge_bag_processing_fees | amount | amount in centsTable Name Column Description

Code:
{{
  config(
    schema = 'edw',
    materialized='table',
    tags = ["pdt_converted_model","bag_attributes_v"]
  )
}}

WITH bag_attr AS
(
        SELECT
          concierge_bag_id,
          MAX(CASE WHEN trim(attribute_label) = 'donation' THEN 1 ELSE 0  END) AS is_donation,
          MAX(CASE WHEN trim(attribute_label) = 'online_label' THEN 1 ELSE 0  END) AS is_online_label,
          MAX(CASE WHEN trim(attribute_label) = 'scheduled_pickup' THEN 1 ELSE 0  END) AS is_scheduled_pickup,
          MAX(CASE WHEN trim(attribute_label) = 'express_cleanout' THEN 1 ELSE 0  END) AS is_express_cleanout,
          MAX(CASE WHEN trim(attribute_label) = 'checkout' THEN 1 ELSE 0  END) AS is_checkout,
          MAX(CASE WHEN trim(attribute_label) = 'multiple_quantity' THEN 1 ELSE 0  END) AS is_multiple_quantity,
          MAX(CASE WHEN trim(attribute_label) = 'cs_bag' THEN 1 ELSE 0  END) AS is_cs_bag,
          MAX(CASE WHEN trim(attribute_label) = 'free_ra_experiment' THEN 1 ELSE 0  END) AS is_free_ra_experiment,
          MAX(CASE WHEN trim(attribute_label) = 'payout_bonus_experiment' THEN 1 ELSE 0  END) AS is_payout_bonus_experiment,
          MAX(CASE WHEN trim(attribute_label) = 'free_vip_processing_experiment' THEN 1 ELSE 0  END) AS is_free_vip_processing_experiment,
          MAX(CASE WHEN trim(attribute_label) = 'selling_guide_schedule_bonus' THEN 1 ELSE 0  END) AS is_selling_guide_schedule_bonus,
          MAX(CASE WHEN trim(attribute_label) = 'promo_credit_experiment' THEN 1 ELSE 0  END) AS is_promo_credit_experiment,
          MAX(CASE WHEN trim(attribute_label) = 'cleanout_subscription' THEN 1 ELSE 0  END) AS is_cleanout_subscription
        FROM {{ ref('bag_attributes') }}
    	GROUP BY concierge_bag_id
),

orig_attr AS (
SELECT
  main.id
  ,CASE WHEN COALESCE(orig_bags.received_at,main.received_at) < main.created_at THEN COALESCE(orig_bags.created_at,main.created_at) ELSE main.created_at END AS created_at
  ,CASE WHEN main.user_id = 1 THEN orig_bags.user_id ELSE main.user_id END AS user_id
  ,COALESCE(orig_bags.concierge_bag_request_id,main.concierge_bag_request_id) AS concierge_bag_request_id
  ,COALESCE(orig_bags.received_at,main.received_at) AS received_at
  ,COALESCE(orig_bags.processed_at,main.processed_at) AS processed_at
  ,COALESCE(main.original_concierge_bag_id,main.id) AS original_concierge_bag_id
FROM {{ ref('concierge_bags') }} main
LEFT JOIN {{ ref('concierge_bags') }} orig_bags ON main.original_concierge_bag_id = orig_bags.id
),

bag_wh AS  (
    SELECT
        bi.bag_id
        ,MAX(from_w.code) AS bag_ship_from_dc
        ,MAX(from_w.state) AS bag_ship_from_dc_state
        ,MAX(from_w.postal_code) AS bag_ship_from_dc_zip_code
        ,MAX(to_w.code) AS bag_ship_to_dc
        ,MAX(to_w.state) AS bag_ship_to_dc_state
        ,MAX(to_w.postal_code) AS bag_ship_to_dc_zip_code
    FROM {{ ref('item_bags') }} bi
    LEFT JOIN {{ ref('warehouses') }} from_w ON from_w.id = bi.fulfill_from_warehouse_id
    LEFT JOIN {{ ref('warehouses') }} to_w ON to_w.id = bi.received_at_warehouse_id
    GROUP BY 1
),

order_addr AS (
   SELECT order_id,zip5,state,city,country_id
   FROM
   (
     SELECT order_id,zip5,state,city,country_id,
          row_number() OVER (PARTITION BY order_id ORDER BY updated_at DESC, concierge_bag_request_id ) rnk
     FROM {{ ref('order_addresses') }}
   ) a
   WHERE rnk = 1
),

bag_req_addr AS (
   SELECT concierge_bag_request_id,zip5,state,city,country_id
   FROM
   (
     SELECT concierge_bag_request_id,zip5,state,city,country_id,
          row_number() OVER (PARTITION BY concierge_bag_request_id ORDER BY updated_at DESC ) rnk
     FROM {{ ref('order_addresses') }}
   ) a
   WHERE rnk = 1
),

acc_rej_items AS (
SELECT
    cb.id AS concierge_bag_id
    ,COUNT(DISTINCT si.original_item_number ) + COUNT(DISTINCT CASE WHEN (ri.item_id  IS NULL) THEN ri.id END) AS total_item_cnt
    ,COUNT(DISTINCT ri.id) AS rejected_item_cnt
    ,COUNT(DISTINCT CASE WHEN COALESCE(si.state,'NA') NOT LIKE 'destroyed_processing' THEN si.original_item_number END) accepted_item_cnt
    ,COUNT(DISTINCT CASE WHEN UPPER(partners.name) = UPPER(brands.name) THEN si.original_item_number END) partner_brand_item_cnt

FROM {{ ref('concierge_bags') }} cb
LEFT JOIN {{ ref('item_bags') }} AS ib ON ib.bag_id = cb.id
LEFT JOIN {{ ref('rejected_items') }} AS ri ON ib.id = ri.item_bag_id
LEFT JOIN {{ ref('shop_items') }}  AS si ON cb.id = si.original_concierge_bag_id
LEFT JOIN {{ ref('partners') }}  AS partners ON partners.id=cb.partner_id
LEFT JOIN {{ ref('shop_brands') }}  AS brands ON brands.id = si.brand_id
GROUP BY 1

),
final AS (
 SELECT
     orig_bags.user_id  bag_user_id
    ,cb.id  AS bag_id
    ,orig_bags.concierge_bag_request_id  bag_request_id
    ,COALESCE(cb.original_concierge_bag_id,cb.id)  AS original_concierge_bag_id
    ,cb.bag_number  bag_number
    -- ,COALESCE(concierge_bag_requests.created_at,orig_bags.created_at) requested_at
    ,concierge_bag_requests.created_at requested_at
    ,CASE WHEN orig_bags.received_at IS NOT NULL THEN orig_bags.received_at
          WHEN cb.state in ('received','no_process','processed','processing','received','received_no_process')
            THEN COALESCE(orig_bags.received_at ,cb.updated_at)
     ELSE NULL END AS received_at
    ,CASE WHEN orig_bags.processed_at IS NOT NULL THEN orig_bags.processed_at
          WHEN cb.state = 'processed'
            THEN  COALESCE(orig_bags.processed_at,cb.updated_at)
     ELSE NULL END AS processed_at
    ,cb.acceptance_rate  bag_acceptance_rate_score
    ,cb.partner_id  partner_id
    ,partners.name AS partner_name
    ,business.id AS business_id
    ,business.key AS business_key
    ,partners.partner_type partner_type
    ,cb.state
    ,original_cb.state  AS original_bag_state
    ,cb.amount_awarded
    ,COALESCE(COALESCE(COALESCE(addr.zip5,orig_addr.zip5),bag_addr.zip5),'UNKNOWN') AS bag_zip
    ,COALESCE(SUBSTR(COALESCE(COALESCE(addr.zip5,orig_addr.zip5),bag_addr.zip5), 1, 5),'UNKNOWN') AS bag_zip5
    ,COALESCE(TRIM(COALESCE(COALESCE(addr.state,orig_addr.state),bag_addr.state)),'UNKNOWN') AS bag_from_state
    ,COALESCE(COALESCE(COALESCE(addr.city,orig_addr.city),bag_addr.city),'UNKNOWN') AS bag_from_city
    ,COALESCE(COALESCE(COALESCE(COALESCE(addr.country_id,orig_addr.country_id),bag_addr.country_id),country.country_id),'UNKNOWN') AS bag_user_country_id
    ,COALESCE(COALESCE(og_bag_attributes.is_donation,bag_attributes.is_donation),0) is_donation
    ,COALESCE(COALESCE(og_bag_attributes.is_online_label,bag_attributes.is_online_label),0) is_online_label
    ,COALESCE(COALESCE(og_bag_attributes.is_scheduled_pickup,bag_attributes.is_scheduled_pickup),0) is_scheduled_pickup
    ,COALESCE(COALESCE(og_bag_attributes.is_express_cleanout,bag_attributes.is_express_cleanout),0) is_express_cleanout
    ,COALESCE(COALESCE(og_bag_attributes.is_checkout,bag_attributes.is_checkout),0) is_checkout
    ,COALESCE(COALESCE(og_bag_attributes.is_multiple_quantity,bag_attributes.is_multiple_quantity),0) is_multiple_quantity
    ,COALESCE(COALESCE(og_bag_attributes.is_cs_bag,bag_attributes.is_cs_bag),0) is_cs_bag
    ,COALESCE(COALESCE(og_bag_attributes.is_free_ra_experiment,bag_attributes.is_free_ra_experiment),0) is_free_ra_experiment
    ,COALESCE(COALESCE(og_bag_attributes.is_payout_bonus_experiment,bag_attributes.is_payout_bonus_experiment),0) is_payout_bonus_experiment
    ,COALESCE(COALESCE(og_bag_attributes.is_free_vip_processing_experiment,bag_attributes.is_free_vip_processing_experiment),0) is_free_vip_processing_experiment
    ,COALESCE(COALESCE(og_bag_attributes.is_selling_guide_schedule_bonus,bag_attributes.is_selling_guide_schedule_bonus),0) is_selling_guide_schedule_bonus
    ,COALESCE(COALESCE(og_bag_attributes.is_promo_credit_experiment,bag_attributes.is_promo_credit_experiment),0) is_promo_credit_experiment
    ,COALESCE(COALESCE(og_bag_attributes.is_cleanout_subscription,bag_attributes.is_cleanout_subscription),0) is_cleanout_subscription
    ,original_cb.user_id  AS original_bag_user_id
    ,original_cb.partner_id  AS original_partner_id
    ,partners_original.partner_type  AS original_partner_type
    ,CASE --WHEN cb.id = cb.original_concierge_bag_id THEN 'Original'
        WHEN (cb.original_concierge_bag_id IS NOT NULL
             AND  cb.id <> cb.original_concierge_bag_id)
        THEN 'Transfer'
        ELSE  'Original'
    END Master_Status
    ,camp.description AS campaign_description
    ,camp.campaign_type  AS campaign_type
    ,camp.campaign_code
    ,cb.partner_campaign_id  AS partner_campaign_id
    ,CASE  WHEN  orders.user_agent IN ('iPhone', 'iPad') THEN  'iOS'
           WHEN  orders.user_agent IN  ('android_tablet', 'android_smartphone', 'android_app') THEN 'Android'
           WHEN  orders.user_agent IN  ('ios_browser', 'ipad_browser', 'android_browser','android_tablet_browser') THEN 'Mobile Web'
           ELSE 'Web'
     END  bag_user_order_platform_type
    ,orders.id order_id
    ,orders.original_order_id
	,req.fulfillment_request_type AS bag_ship_from_fulfillment_request_type
	,COALESCE(w.code,bag_wh.bag_ship_from_dc) AS bag_ship_from_dc
    ,COALESCE(w.state,bag_wh.bag_ship_from_dc_state) AS bag_ship_from_dc_state
    ,COALESCE(w.postal_code,bag_wh.bag_ship_from_dc_zip_code) AS bag_ship_from_dc_zip_code
    ,COALESCE(COALESCE(vblw.code,vblw2.code),bag_wh.bag_ship_to_dc) AS bag_ship_to_dc
	,COALESCE(COALESCE(vblw.state,vblw2.state),bag_wh.bag_ship_to_dc_state) AS bag_ship_to_dc_state
    ,COALESCE(COALESCE(vblw.postal_code,vblw2.postal_code),bag_wh.bag_ship_to_dc_zip_code) AS bag_ship_to_dc_zip_code
    ,ari.accepted_item_cnt
    ,ari.rejected_item_cnt
    ,ari.total_item_cnt
    ,ari.partner_brand_item_cnt
    ,bag_activations.created_at as activation_at

FROM {{ ref('concierge_bags') }} cb
LEFT JOIN orig_attr AS orig_bags ON cb.id = orig_bags.id
LEFT JOIN {{ ref('partners') }}  AS partners ON cb.partner_id = partners.id
LEFT JOIN {{ ref('concierge_bag_requests') }} AS concierge_bag_requests ON (orig_bags.concierge_bag_request_id  = concierge_bag_requests.id )
LEFT JOIN {{ ref('concierge_bags') }}  AS original_cb ON (original_cb.id = COALESCE(cb.original_concierge_bag_id,cb.id))
LEFT JOIN {{ ref('partners') }} AS partners_original ON original_cb.partner_id  = partners_original.id
LEFT JOIN bag_attr AS bag_attributes ON bag_attributes.concierge_bag_id=cb.id
LEFT JOIN bag_attr AS og_bag_attributes ON og_bag_attributes.concierge_bag_id=cb.original_concierge_bag_id
LEFT JOIN {{ ref('partner_campaigns') }} camp ON camp.id = cb.partner_campaign_id
LEFT JOIN {{ ref('order_products') }}  AS order_products ON order_products.concierge_bag_id = COALESCE(cb.original_concierge_bag_id,cb.id)
LEFT JOIN {{ ref('orders') }}  AS orders ON orders.id=order_products.order_id
LEFT JOIN order_addr AS addr ON (orders.id = addr.order_id)
LEFT JOIN order_addr AS orig_addr ON (orders.original_order_id = orig_addr.order_id)
LEFT JOIN bag_req_addr AS bag_addr ON (orig_bags.concierge_bag_request_id = bag_addr.concierge_bag_request_id)
LEFT JOIN {{ ref('user_countries') }} AS country ON country.user_id = orig_bags.user_id AND country.country_id = 1 AND country.state = 'active' AND usage = 'primary'
LEFT JOIN {{ ref('fulfillment_request_lines') }} AS req_line ON (orig_bags.original_concierge_bag_id = req_line.concierge_bag_id AND  req_line.item_number IS NULL)
LEFT JOIN {{ ref('fulfillment_requests') }} AS req ON (req.id = req_line.fulfillment_request_id)
LEFT JOIN {{ ref('warehouses') }} AS w ON w.id = req.warehouse_id
LEFT JOIN bag_wh AS bag_wh ON bag_wh.bag_id = orig_bags.original_concierge_bag_id
LEFT JOIN {{ ref('valid_bag_labels') }} vbl ON (cb.bag_number = vbl.bag_number)
LEFT JOIN {{ ref('warehouses') }} AS vblw ON (vblw.id = vbl.warehouse_id)
LEFT JOIN {{ ref('valid_bag_labels') }} vbl2 ON (orig_bags.original_concierge_bag_id = vbl2.item_bag_id)
LEFT JOIN {{ ref('warehouses') }} AS vblw2 ON (vblw2.id = vbl2.warehouse_id)
LEFT JOIN {{ ref('business_programs') }} bp ON (bp.partner_id=cb.partner_id)
LEFT JOIN {{ ref('businesses') }} business ON (business.id = bp.business_id)
LEFT JOIN acc_rej_items ari ON (ari.concierge_bag_id = cb.id)
LEFT JOIN {{ ref('partner_bag_activations') }} as bag_activations  ON (bag_activations.bag_number = cb.bag_number)
)

SELECT
bag_id
,bag_number
,bag_request_id
,original_concierge_bag_id
,COALESCE(original_bag_user_id,bag_user_id) AS bag_user_id
,order_id
,original_order_id
,requested_at
,received_at
,processed_at
,bag_acceptance_rate_score
,amount_awarded
,partner_id
,partner_name
,business_id
,business_key
,partner_type
,partner_campaign_id
,campaign_description
,campaign_type
,campaign_code
,f.state
,original_bag_state
,original_bag_user_id
,original_partner_id
,original_partner_type
,master_status
,bag_user_order_platform_type
,is_donation
,is_online_label
,is_scheduled_pickup
,is_express_cleanout
,is_checkout
,is_multiple_quantity
,is_cs_bag
,is_free_ra_experiment
,is_payout_bonus_experiment
,is_free_vip_processing_experiment
,is_selling_guide_schedule_bonus
,is_promo_credit_experiment
,is_cleanout_subscription
,bag_zip
,bag_zip5
,bag_from_state
,bag_from_city
,bag_user_country_id
,bag_ship_from_fulfillment_request_type
,bag_ship_from_dc
,bag_ship_from_dc_state
,bag_ship_from_dc_zip_code
,bag_ship_to_dc
,bag_ship_to_dc_state
,bag_ship_to_dc_zip_code
,COALESCE(bag_msa.msa_group_name,'UNKNOWN') AS msa_group_name
,accepted_item_cnt
,rejected_item_cnt
,total_item_cnt
,partner_brand_item_cnt
,CASE WHEN trim(COALESCE(original_partner_type,COALESCE(partner_type,'regular'))) = 'charity' THEN 'donation'
          WHEN is_donation = 1 THEN  'donation'
          WHEN trim(COALESCE(original_partner_type,COALESCE(partner_type,'regular'))) = 'regular' THEN 'regular'
          WHEN trim(COALESCE(original_partner_type,COALESCE(partner_type,'regular'))) = 'complimentary' THEN 'regular'
          WHEN (trim(COALESCE(original_partner_type,COALESCE(partner_type,'regular'))) = 'internal'
          AND trim(master_status) = 'Transfer') THEN 'regular'
    ELSE trim(COALESCE(original_partner_type,COALESCE(partner_type,'regular'))) END  bag_partner_type
,CASE
	WHEN (is_donation = 1) THEN 'Donation'
	WHEN (is_online_label = 1) THEN 'Online'
 ELSE 'Regular' END AS bag_type
 ,activation_at
,current_user AS audit_created_by
,current_timestamp() AS audit_created_at
FROM final f
LEFT JOIN {{ source( 'edw', 'msa_mappings') }} AS bag_msa ON SUBSTR(f.bag_zip5, 1, 5) = bag_msa.zip_code

######################
Output:
("entity"{tuple_delimiter}CONCIERGE_BAG_PROCESSING_FEES{tuple_delimiter}TABLE{tuple_delimiter}A table containing details about processing fees for concierge bags, including states, amounts, and associated partner and bag IDs)
{record_delimiter}
("entity"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}TABLE{tuple_delimiter}A table tracking information about concierge bags, including their state, processing details, and user associations)
{record_delimiter}
("entity"{tuple_delimiter}PARTNERS{tuple_delimiter}TABLE{tuple_delimiter}A table storing information about business partners linked to concierge bags and fees)
{record_delimiter}
("entity"{tuple_delimiter}WAREHOUSES{tuple_delimiter}TABLE{tuple_delimiter}A table storing warehouse information for shipping and receiving concierge bags)
{record_delimiter}
("entity"{tuple_delimiter}BAG_ATTRIBUTES{tuple_delimiter}TABLE{tuple_delimiter}A table containing attributes of concierge bags, such as donation status, online labels, and experimental processing types)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_ADDRESSES{tuple_delimiter}TABLE{tuple_delimiter}A table containing address details for orders linked to concierge bags)
{record_delimiter}
("entity"{tuple_delimiter}SHOP_ITEMS{tuple_delimiter}TABLE{tuple_delimiter}A table containing shop items associated with concierge bags and their processing state)
{record_delimiter}
("entity"{tuple_delimiter}REJECTED_ITEMS{tuple_delimiter}TABLE{tuple_delimiter}A table tracking items rejected during concierge bag processing)
{record_delimiter}
("entity"{tuple_delimiter}PARTNER_CAMPAIGNS{tuple_delimiter}TABLE{tuple_delimiter}A table storing details of campaigns run by partners, linked to concierge bags)
{record_delimiter}
("entity"{tuple_delimiter}BUSINESSES{tuple_delimiter}TABLE{tuple_delimiter}A table containing details about businesses linked to concierge bags and their processing fees)
{record_delimiter}
("entity"{tuple_delimiter}BAG_SHIP_FROM_DC{tuple_delimiter}RESOURCES{tuple_delimiter}The distribution center from which concierge bags are shipped)
{record_delimiter}
("entity"{tuple_delimiter}BAG_SHIP_TO_DC{tuple_delimiter}RESOURCES{tuple_delimiter}The distribution center to which concierge bags are shipped)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAG_PROCESSING_FEES{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}Processing fees are applied to concierge bags through a foreign key association{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}PARTNERS{tuple_delimiter}Concierge bags are linked to partners who manage their processing and shipping{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}BAG_ATTRIBUTES{tuple_delimiter}Bag attributes provide metadata for concierge bags, such as donation or experimental status{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}WAREHOUSES{tuple_delimiter}Concierge bags are processed and shipped from and to warehouses{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}SHOP_ITEMS{tuple_delimiter}Shop items are linked to concierge bags for tracking and processing{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}ORDER_ADDRESSES{tuple_delimiter}Order addresses provide location details for concierge bag delivery and pickup{tuple_delimiter}5)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}REJECTED_ITEMS{tuple_delimiter}Rejected items from concierge bags are tracked for processing status{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}PARTNER_CAMPAIGNS{tuple_delimiter}Partner campaigns are linked to concierge bags to track promotional activities{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}CONCIERGE_BAGS{tuple_delimiter}BUSINESSES{tuple_delimiter}Concierge bags are linked to businesses managing their processing and associated campaigns{tuple_delimiter}6)
{completion_delimiter}

######################
Example 9:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text:
Text: Business context

Model Overview: Supplier Bag Items

Conﬁdential 2￼The main objectives of Supplier Bag Items Model are: 1. T rack WHEN  we obtain  “title”  for an item and WHY 2. T rack WHEN  we payout  an item and WHY *”Title ” is deﬁned as we have physical possession  of the item and  it has been paid out  (IF it needs to be paid out ) ** Only exception is Goody Box items. W e consider to have title for these because we pay out on ship, even though we do not have physical possession while it has been sent to the customer . Supplier Bag Items Main Objectives

Conﬁdential 3￼UPDATE Supplier Bag Item Record Supplier Bag Items In Practice Events Include: - Upfront Payout Bag Completed Processing : we take title af ter paying out for those items - Consignment Payout is issued : W e track paid_at timestamp - Paid out Item is returned - Etc. - (for full list of scenarios see here (LINK TBD) Title/Payout Event CREATE Supplier Bag Item Record Item Created

Conﬁdential 4￼Item item_number: 1 Orig_item_number: 1 State: Returned Supplier Bag Items Relationship to Items All generations of an Item will have a single shared SupplierBagItem (referenced by original_item_number ) Supplier Bag Item Orig_item_num: 1 Item item_num: 2 Orig_item_num: 1 State: Order Cancelled Item Item_num: 3 Orig_item_num: 1 State: Packed

Conﬁdential 5￼Supplier Bag Items A closer look 👀 original_item_number 111 original_concierge_bag_id 222 original_payout_policy estimated_payout (in cents) actual_payout (in cents) user_id 456 paid_at (timestamp) paid_reason title_at (timestamp) title_reason title_ref_txn_type (CashCredit or PartnerAward) title_ref_txn_id ID of respsective record

Conﬁdential 6￼Supplier Bag Items Item Purchased (not yet paid) original_item_number 111 original_concierge_bag_id 222 original_payout_policy consignment estimated_payout 50 actual_payout user_id 333 paid_at paid_reason title_at title_reason title_ref_txn_type title_ref_txn_id

Conﬁdential 7￼Supplier Bag Items Consignment Payout original_item_number 111 original_concierge_bag_id 222 original_payout_policy consignment estimated_payout 50 actual_payout 50 user_id 333 paid_at 2020-07-01 10:00 paid_reason consignment_payout title_at title_reason title_ref_txn_type CashCredit/PartnerAward title_ref_txn_id 444

Conﬁdential 8￼Supplier Bag Items Consignment EXPIRED original_item_number 111 original_concierge_bag_id 222 original_payout_policy consignment estimated_payout actual_payout user_id 333 paid_at paid_reason title_at 2020-07-01 10:00 title_reason consignment_expired title_ref_txn_type title_ref_txn_id

Conﬁdential 9￼Supplier Bag Item Reasons list / explanation consignment_expired Title due to consignment listing expiring consignment_lost Payout due to item lost, no title consignment_payout Payout issued for consignment item (excludes store buyout, lost) consignment_payout_goody_box Payout + Title because item was shipped in goody box. destroyed_processing Title because item was accepted but then destroyed_processing. No payout. donation Title because item was in donation bag, no payout. internal  Title, no payout. Internal bags belong to ${project}. See here for more reasons relisted Title because the item was returned via RMA after a payout already happened. transfer_incorrect_place ment Title because item was incorrectly placed in someone’s bag. transfer_admin Title due to a CS Admin action. (when item is moved out of customer consignment_store_buy outWe buyout an item to send to a store (${project} Retail Store or Retail Partner) unidentified_bag Title when unknown sender of bag. upfront_payout_policy Title and payout when item has upfront payout policy.

Conﬁdential 10￼Supplier Bag Items: Examples See more examlples here https: / / app.lucidchar t.com/ publicSegments/ view/43809698-4b83-4114-8f13-5d022d1d4d96/image.pdf

######################
Output:
("entity"{tuple_delimiter}SUPPLIER BAG ITEMS{tuple_delimiter}TABLE{tuple_delimiter}A model tracking supplier bag items, including item title, payout events, and related reasons for state changes)
{record_delimiter}
("entity"{tuple_delimiter}ITEM{tuple_delimiter}TABLE{tuple_delimiter}A table capturing individual items linked to supplier bag items with states such as returned, packed, or canceled)
{record_delimiter}
("entity"{tuple_delimiter}ORIGINAL_ITEM_NUMBER{tuple_delimiter}COLUMNS{tuple_delimiter}A unique identifier shared across all generations of an item, linking it to its supplier bag item record)
{record_delimiter}
("entity"{tuple_delimiter}ORIGINAL_CONCIERGE_BAG_ID{tuple_delimiter}COLUMNS{tuple_delimiter}A foreign key linking supplier bag items to their associated concierge bags)
{record_delimiter}
("entity"{tuple_delimiter}ESTIMATED_PAYOUT{tuple_delimiter}COLUMNS{tuple_delimiter}The estimated payout amount (in cents) for an item in the supplier bag)
{record_delimiter}
("entity"{tuple_delimiter}ACTUAL_PAYOUT{tuple_delimiter}COLUMNS{tuple_delimiter}The actual payout amount (in cents) issued for an item in the supplier bag)
{record_delimiter}
("entity"{tuple_delimiter}PAID_AT{tuple_delimiter}COLUMNS{tuple_delimiter}The timestamp when a payout was issued for an item in the supplier bag)
{record_delimiter}
("entity"{tuple_delimiter}PAID_REASON{tuple_delimiter}COLUMNS{tuple_delimiter}The reason for a payout, such as consignment or goody box)
{record_delimiter}
("entity"{tuple_delimiter}TITLE_AT{tuple_delimiter}COLUMNS{tuple_delimiter}The timestamp when the title was obtained for an item in the supplier bag)
{record_delimiter}
("entity"{tuple_delimiter}TITLE_REASON{tuple_delimiter}COLUMNS{tuple_delimiter}The reason for obtaining the title, such as consignment expired or donation)
{record_delimiter}
("entity"{tuple_delimiter}TITLE_REF_TXN_TYPE{tuple_delimiter}COLUMNS{tuple_delimiter}The transaction type linked to obtaining the title, such as CashCredit or PartnerAward)
{record_delimiter}
("entity"{tuple_delimiter}TITLE_REF_TXN_ID{tuple_delimiter}COLUMNS{tuple_delimiter}The transaction ID of the respective record linked to obtaining the title)
{record_delimiter}
("entity"{tuple_delimiter}GOODY_BOX_ITEMS{tuple_delimiter}RESOURCES{tuple_delimiter}Items shipped in a goody box, where title is granted upon shipment despite lack of physical possession)
{record_delimiter}
("entity"{tuple_delimiter}SUPPLIER BAG ITEMS REASONS{tuple_delimiter}RESOURCES{tuple_delimiter}A list of reasons for title and payout events, such as consignment_expired, destroyed_processing, or donation)
{record_delimiter}
("relationship"{tuple_delimiter}SUPPLIER BAG ITEMS{tuple_delimiter}ITEM{tuple_delimiter}Supplier bag items are linked to individual items and track their lifecycle and states{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}SUPPLIER BAG ITEMS{tuple_delimiter}ORIGINAL_ITEM_NUMBER{tuple_delimiter}Supplier bag items are referenced by their original item number across generations of the item{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}SUPPLIER BAG ITEMS{tuple_delimiter}ORIGINAL_CONCIERGE_BAG_ID{tuple_delimiter}Supplier bag items are linked to concierge bags using the original concierge bag ID{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}SUPPLIER BAG ITEMS{tuple_delimiter}SUPPLIER BAG ITEMS REASONS{tuple_delimiter}The reasons list explains various events and states associated with supplier bag items{tuple_delimiter}5)
{record_delimiter}
("relationship"{tuple_delimiter}SUPPLIER BAG ITEMS{tuple_delimiter}GOODY_BOX_ITEMS{tuple_delimiter}Goody box items are an exception where title is granted upon shipment{tuple_delimiter}6)
{completion_delimiter}

######################
Example 10:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text: SQL to check table completeness

WITH table_summary AS (
    SELECT
            MAX({{dt_column}}) AS last_updated_at
        FROM
            {{ schema }}.{{ table }}
            WHERE {{ dt_column }} >= DATE('{{ var("run_date") }}') - 10

)
SELECT last_updated_at
FROM table_summary
GROUP BY 1
HAVING NOT last_updated_at >= ({{ end_of_day(var('run_date')) }})

######################
Output:
("entity"{tuple_delimiter}CHECK_TABLE_COMPLETENESS{tuple_delimiter}CODE{tuple_delimiter}A SQL macro to verify the completeness of a table by checking if the most recent update is within a defined timeframe)
{record_delimiter}
("entity"{tuple_delimiter}SCHEMA{tuple_delimiter}PARAMETER{tuple_delimiter}The schema containing the table to be checked for completeness)
{record_delimiter}
("entity"{tuple_delimiter}TABLE{tuple_delimiter}PARAMETER{tuple_delimiter}The table whose completeness is being checked)
{record_delimiter}
("entity"{tuple_delimiter}DT_COLUMN{tuple_delimiter}PARAMETER{tuple_delimiter}The date column used to determine the last update time for the table)
{record_delimiter}
("entity"{tuple_delimiter}RUN_DATE{tuple_delimiter}PARAMETER{tuple_delimiter}The reference date for the check, used to compute the timeframe)
{record_delimiter}
("entity"{tuple_delimiter}LAST_UPDATED_AT{tuple_delimiter}COLUMNS{tuple_delimiter}The timestamp of the most recent update in the table being checked)
{record_delimiter}
("relationship"{tuple_delimiter}CHECK_TABLE_COMPLETENESS{tuple_delimiter}SCHEMA{tuple_delimiter}The schema is a required input for the SQL macro to locate the table{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CHECK_TABLE_COMPLETENESS{tuple_delimiter}TABLE{tuple_delimiter}The table is a required input for the SQL macro to perform completeness checks{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CHECK_TABLE_COMPLETENESS{tuple_delimiter}DT_COLUMN{tuple_delimiter}The date column is used by the SQL macro to filter records for the completeness check{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}CHECK_TABLE_COMPLETENESS{tuple_delimiter}RUN_DATE{tuple_delimiter}The run_date parameter is used as the reference date for calculating the completeness timeframe{tuple_delimiter}7)
{completion_delimiter}

######################
Example 12:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text: What is bundled shipping?
Important update about our holiday hours
Read More
Help Center
Shopping on ${project}
Search:
What is bundled shipping?
It's the best way to reduce packaging, and save on shipping! Our bundled shipping option lets you pay shipping once and then make as many orders as you like over seven days. Once your week is up, your orders will be combined and shipped together.
${project}
has only one of every item, so things get scooped up quickly. With Bundling you can act fast to make purchase without generating extra waste if you find something else you want to scoop up a few days later.
Here’s how it works:
1. Choose the bundled shipping option at checkout for $8.99. We can’t retroactively bundle your orders, so make sure you pick the option below! If your initial order totals less than your free shipping threshold, you will be charged a one-time $8.99 shipping fee.
2. The clock starts now! Shop for up to seven days. Any orders you make will be added to your bundle, no extra shipping fee applied! If your entire bundle totals more than your free shipping threshold, we’ll refund the original $8.99 shipping fee to your original form of payment after the bundle has been closed.
3. You can choose to close and ship your bundle at any time, or we will automatically start processing it seven days after your first bundle order is placed. You can do that by visiting My Bundle under your Account.
Please note: All bundled orders will ship at the same time and must be shipped to the same address. To reduce packaging, items located in different warehouses will be consolidated in the warehouse closest to you before being shipped. All standard return policies apply. Promotional codes may only be used on a single order, not your entire bundle. However, you can apply different promo codes on orders you place later in the week (e.g. you can use one promo code on your first order and if there's a sale later in the week you can apply the new promo code to another order in your bundle). If you would like for the order to ship out before the seven day period, Please head over to the
order
details page here. From here click on the order you wish. There will then be a "ship now" button in the top right. Once selected the order will begin to be processed and shipped out as soon as possible! For information about all our shipping options, please visit our FAQs.

######################
Output:
("entity"{tuple_delimiter}BUNDLED SHIPPING{tuple_delimiter}SERVICE{tuple_delimiter}A shipping option that allows customers to combine multiple orders over seven days into one shipment, reducing packaging and shipping costs)
{record_delimiter}
("entity"{tuple_delimiter}THRESHOLD FOR FREE SHIPPING{tuple_delimiter}POLICY{tuple_delimiter}The minimum total amount required for a bundle to qualify for free shipping and a refund of the $8.99 shipping fee)
{record_delimiter}
("entity"{tuple_delimiter}BUNDLE CLOCK{tuple_delimiter}PROCESS{tuple_delimiter}The seven-day timeframe during which customers can add orders to their bundle)
{record_delimiter}
("entity"{tuple_delimiter}PROMOTIONAL CODES{tuple_delimiter}POLICY{tuple_delimiter}Customers can use different promotional codes on separate orders within the same bundle, but not across the entire bundle)
{record_delimiter}
("entity"{tuple_delimiter}MY BUNDLE{tuple_delimiter}PLATFORM{tuple_delimiter}The account section where customers can manage their bundled orders and choose to close and ship the bundle)
{record_delimiter}
("entity"{tuple_delimiter}SHIP NOW{tuple_delimiter}OPTION{tuple_delimiter}A feature that allows customers to process and ship their bundle before the seven-day period ends)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLED SHIPPING{tuple_delimiter}THRESHOLD FOR FREE SHIPPING{tuple_delimiter}The bundled shipping service offers a refund of the $8.99 shipping fee if the total exceeds the free shipping threshold{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLED SHIPPING{tuple_delimiter}BUNDLE CLOCK{tuple_delimiter}Bundled shipping operates within a seven-day clock to add orders without additional shipping fees{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLED SHIPPING{tuple_delimiter}PROMOTIONAL CODES{tuple_delimiter}Promotional codes can be applied to individual orders in a bundle, enhancing the bundled shipping experience{tuple_delimiter}5)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLED SHIPPING{tuple_delimiter}MY BUNDLE{tuple_delimiter}The "My Bundle" section allows customers to track, manage, and ship their bundled orders{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLED SHIPPING{tuple_delimiter}SHIP NOW{tuple_delimiter}The "Ship Now" option provides flexibility for customers to process and ship their bundles earlier than the default seven-day period{tuple_delimiter}6)
{completion_delimiter}

######################
Example 13:
Entity_types: TABLE,TOOLS,PLATFORM,COLUMNS,RESOURCES,BUSINESS,CODE,INFRASTRUCTURE
Text: Bundle Metrics SQL
Code:

{{
  config(
    schema = 'edw',
    materialized='table',
    tags = ["revenue_metrics"]
  )
}}

WITH temp AS (
    SELECT
        fact_order_batch_products.order_batch_id,
        fact_order_batch_creation_extract.latest_order_created_at,
        COUNT(DISTINCT op.order_id) AS order_count
    FROM {{ ref('order_products') }} op
    LEFT JOIN {{ ref('shop_shipments') }} s
        ON op.shipment_id = s.id
    LEFT JOIN {{ ref('ops_shipments') }} AS ops_shipments
        ON ops_shipments.shipment_number = s.shipment_number
    INNER JOIN (
        SELECT fop.order_id,
            fop.order_batch_id
        FROM {{ ref('fact_order_products') }} fop
        WHERE is_bnb=1
    ) fact_order_batch_products
    ON fact_order_batch_products.order_id = op.order_id
    INNER JOIN (
        SELECT fop.order_batch_id,
            MAX(fop.created_at) AS latest_order_created_at
        FROM {{ ref('fact_order_products') }} fop
        WHERE is_bnb=1
        GROUP BY fop.order_batch_id
    ) fact_order_batch_creation_extract
    ON fact_order_batch_creation_extract.order_batch_id = fact_order_batch_products.order_batch_id
    GROUP BY 1,2
),
FINAL AS (
    SELECT
        t.order_batch_id,
        t.latest_order_created_at,
        t.order_count
    FROM temp t
)

SELECT
    order_batch_id,
    latest_order_created_at,
    order_count,
    CURRENT_USER AS audit_created_by,
    CURRENT_TIMESTAMP () AS audit_created_at
FROM FINAL;

######################
Output:
("entity"{tuple_delimiter}BUNDLE METRICS{tuple_delimiter}TABLE{tuple_delimiter}A materialized table capturing metrics for order batches related to bundling, including order counts and creation timestamps)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_BATCH_ID{tuple_delimiter}COLUMNS{tuple_delimiter}A unique identifier for an order batch included in the bundle metrics)
{record_delimiter}
("entity"{tuple_delimiter}LATEST_ORDER_CREATED_AT{tuple_delimiter}COLUMNS{tuple_delimiter}The most recent creation timestamp for an order within a batch)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_COUNT{tuple_delimiter}COLUMNS{tuple_delimiter}The count of distinct orders within a batch for bundle processing)
{record_delimiter}
("entity"{tuple_delimiter}FACT_ORDER_PRODUCTS{tuple_delimiter}TABLE{tuple_delimiter}A table storing details about fact-level order products, filtered to include only BnB (Buy Now Bundle) orders for metrics calculation)
{record_delimiter}
("entity"{tuple_delimiter}ORDER_PRODUCTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing details of individual order products used to link shipment and batch data)
{record_delimiter}
("entity"{tuple_delimiter}SHOP_SHIPMENTS{tuple_delimiter}TABLE{tuple_delimiter}A table containing shipment data linked to order products for batch metrics)
{record_delimiter}
("entity"{tuple_delimiter}OPS_SHIPMENTS{tuple_delimiter}TABLE{tuple_delimiter}A table capturing operational shipment details for further validation and metrics)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLE METRICS{tuple_delimiter}FACT_ORDER_PRODUCTS{tuple_delimiter}The fact_order_products table provides order and batch details for calculating bundle metrics{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLE METRICS{tuple_delimiter}ORDER_PRODUCTS{tuple_delimiter}The order_products table links orders to batches and shipments for bundling metrics{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLE METRICS{tuple_delimiter}SHOP_SHIPMENTS{tuple_delimiter}The shop_shipments table provides shipment data for orders in the bundle metrics{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLE METRICS{tuple_delimiter}OPS_SHIPMENTS{tuple_delimiter}The ops_shipments table validates shipment details linked to orders in the bundle metrics{tuple_delimiter}6)
{record_delimiter}
("relationship"{tuple_delimiter}BUNDLE METRICS{tuple_delimiter}ORDER_BATCH_ID{tuple_delimiter}The bundle metrics are grouped and identified by order_batch_id for analysis{tuple_delimiter}8)
{completion_delimiter}

######################
-Real Data-
######################
Entity_types: {entity_types}
Text: {input_text}
######################
Output:

"""


summarize_descriptions = """
You are an expert E-commerce Operations and Data Engineering related task. You are skilled at analyzing and optimizing e-commerce ecosystems, focusing on enhancing efficiency and effectiveness across various operational domains.
You are adept at helping businesses identify the relations and structure within their community of interest, specifically within inventory management, order processing, customer analytics, marketing campaigns, payment systems, and the technical infrastructure supporting ETL pipelines, data warehousing, and real-time analytics. Your expertise enables companies to streamline operations, improve customer satisfaction, and drive growth through data-driven decision-making.
E-commerce Business Ontology and Data Engineering Operations details-
- The business ontology for an eCommerce website defines the key entities, relationships,and processes within the online retail ecosystem.
- Some essential entities could be Products, Customers, Orders, Payments, and Inventory for building customer journey and efficient business operations. Using community detection algorithms, identify community structures within the graph, incorporating closely linked entities into the same community.
    - Products: Includes attributes like category, price, brand, and product stock levels.
    - Customers: Includes customer profiles, preferences, purchase history, and demographics.
    - Orders: Tracks customer purchases, order status, shipping, and delivery.
    - Payments: Manages payment methods, transactions, refunds, and financial reporting.
    - Inventory: Monitors product stock levels, warehouse data, and product availability.
- Data Engineering Operations in an eCommerce setting focuses on managing the vast amounts of transactional, customer, and product data generated by the website. This involves the following steps:
    - ETL (Extract, Transform, Load) pipelines to process data from different sources (e.g., website, third-party services, payment gateways).
    - Data Warehousing to store and organize large-scale datasets for analytics and reporting (using platforms like AWS Redshift or Snowflake).
    - Data Quality: Ensuring consistency, accuracy, and integrity of the data, especially when integrating multiple data sources.
    - Real-Time Data Processing for inventory management, customer behavior tracking, and dynamic pricing.
    - Analytics & Reporting: Creating dashboards and reports using BI tools like Tableau, Power BI, or Looker to track key business metrics.

Data format includes - text or pdf documents, schema, data model, SQL queries/codes for extracting relevant data from tables.
Using your expertise in performing ETL operations to extract, transform, load data from various sources into data warehouses, comprehend SQL queries and code in Python,R you're tasked to generate a comprehensive summary of the data provided.
Given one or two entities, and a list of descriptions, all related to the same entity or group of entities. Please concatenate all of these into a single, concise description. The primary language of the provided text is English.
Conduct comprehensive analysis of the e-commerce community, identifying key entities.
Enrich it as much as you can with relevant information from the nearby text, this is very important.
Make sure to include information collected from all the descriptions.If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity names so we have the full context.
If no answer is possible, or the description is empty, only convey information that is provided within the text.


#######

-Example Data-

Entities: {entity_name}
Description List: {description_list}

####

Table data example

Table name: ${project}_v2_production.total_control_items
This data model is for storing items total control information or hybrid resale project.
Table Name | Column | Description
total_control_items | bag_deduction_id  | joins to concierge_bag_deductions table
total_control_items | excluded_from_promo |
total_control_items | item_id | joins to items table
total_control_items | original_brand_id | joins to brands table
total_control_items | published_automatically |
total_control_items | seller_brand |
total_control_items | seller_info |
total_control_items | seller_name |
total_control_items | seller_price |
total_control_items | status | ‘active’ / 'inactive

#####

Text data example

The Data Inferno

Inspired by a cheeky white paper, “The R Inferno,” this article seeks to highlight risky pitfalls that may sidetrack your progress. The data of
${project} is complex with many caveats and subtleties in the way that data is defined. I hope this will serve as a helpful document to scan
and review periodically for anyone looking to doing data analysis!
* Split Monoliths
* * Item Number is not Item ID by a different name
* What is a product anyway?
* Spoofed Users
* Orders are overloaded

Split Monoliths
${project} data is split across two different databases, broadly called “tup3” and “operations”. In redshift, these are prefixed with
mysql_${project}_v2_production and mysql_${project}_operations. These two databases operate with different ids, and great care should
be taken when joining across these databases. That is not to say that you shouldn’t join across these databases; in fact, it is often the best
and easiest thing to do. It’s just to say that you must take care not to assume that IDs for any type of asset match across the two databases.

Item Number is not Item ID by a different name
The most widespread example of this difference is item_number vs item_id. item_number is widely populated across the front end and
logging, and is intended to be used as the proper unique identifier for a particular item. However, you should never join an item_number to
the id for the items table in either operations or production. Both of these tables will instead have an item_number, which allows for
joining across the two databases. It additionally makes it possible to identify an item without also specifying the database of origin. tl;dr:
Always use item_number, never use item_id.

What is a product anyway?
To join items to orders, the order_products table is used. However, this is not to be confused with the products table, which is
essentially a list of prices that are valid for rendering on the client. In most cases, the term “product” refers to the products table, however,
the order_products table has nothing to do with “products”, and simply serves as the many-to-one item-order link table.

#######
Databricks documentation example
- What is CI/CD on Databricks?
In this article: Development flow, Production job workflow
Option 1: Run jobs using notebooks in a remote repository
Option 2: Set up a production Git folder and Git automation
Use a service principal with Databricks Git folders
Terraform integration
Configure an automated CI/CD pipeline with Databricks Git folders
Development flow
Databricks Git folders have user-level folders. User-level folders are automatically created when users first clone a remote repository. You can think of Databricks Git folders in user folders as “local checkouts” that are individual for each user and where users make changes to their code.
In your user folder in Databricks Git folders, clone your remote repository. A best practice is to create a new feature branch or select a previously created branch for your work, instead of directly committing and pushing changes to the main branch. You can make changes, commit, and push changes in that branch. When you are ready to merge your code, you can do so in the Git folders UI.
Requirements
This workflow requires that you have already set up your Git integration
Note: Databricks recommends that each developer works on their own feature branch. For information about how to resolve merge conflicts, see
Resolve merge conflicts
- Collaborate in Git folders
The following workflow uses a branch called feature-b that is based on the main branch.
Clone your existing Git repository to your Databricks workspace
- Use the Git folders UI to create a feature branch from the main branch. This example uses a single feature branch
feature-b for simplicity. You can create and use multiple feature branches to do your work.
Make your modifications to Databricks notebooks and other files in the repo.
Commit and push your changes to your Git provider
-  Contributors can now clone the Git repository into their own user folder.
Working on a new branch, a coworker makes changes to the notebooks and other files in the Git folder. The contributor commits and pushes their changes to the Git provider
.To merge changes from other branches or rebase the feature-b branch in Databricks, in the Git folders UI use one of the following workflows:
Merge branches
. If there’s no conflict, the merge is pushed to the remote Git repository using git push
.Rebase on another branch

#######

Output:

"""


pacelabs_entity = """

-Goal-
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.

-Qualifications-
You are an experienced data professional within Laboratory Information Management Systems environment having the following knowledge.
- Strong proficiency in SQL, Python, or R for data manipulation and analysis/engineering.
- Experienced in developing ETL processes to extract, transform, load data from various sources into data warehouses and real-time analytics platforms.
- Strong understanding of relational databases, data warehousing, and big data technologies (e.g., Redshift, Snowflake, BigQuery).
- Experience with automation tools for data workflow orchestration, such as Airflow or DBT (Data Build Tool).
- Experience with data harmonization and mapping and any form of transformation.

-Instructions-
- Always give weightage to data and code over documents. Leverage documentations for fill in the gaps.
- Prioritize actual table that exists in the database (using schema information) over having just documentations about it.
- Identify entities in a data warehouse and create lineage/relationships between them.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, capitalized
- entity_type: One of the following types: [field, data_type, analytical_results, lims_user, message, segment, subcomponent, index, recurrence, analyte, instrument, detection_limit, unit_of_measure, container, preservative, sample, api_security, project, workorder, sample_type, submitter]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: an integer score between 1 to 10, indicating strength of the relationship between the source entity and target entity
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)

3. Return output in The primary language of the provided text is "English." as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. If you have to translate into The primary language of the provided text is "English.", just translate the descriptions, nothing else!

5. When finished, output {completion_delimiter}.

-Examples-
#############################


Example 1:

entity_types: [user, sample, flag, diagnostic, index, table, field, data type, result, batch, analyte, detection limit, report, workorder, context, client, profile, charge, error, command, marker]
text:
CREATE TABLE DMART_CUSTOMERS (
    SYSTEM_ID VARCHAR2 NOT NULL,
    CUST_ID VARCHAR2 NOT NULL,
    CUST_GROUP VARCHAR2 NULL,
    CUST_NAME VARCHAR2 NULL,
    CUST_SEQ NUMBER NULL,
    FLAGS VARCHAR2 NULL,
    ACTIVE VARCHAR2 NULL,
    CONSTRAINT PK_DMART_CUSTOMERS PRIMARY KEY (SYSTEM_ID, CUST_ID)
);

------------------------
output:
("entity"{tuple_delimiter}DMART_CUSTOMERS{tuple_delimiter}TABLE{tuple_delimiter}Table that stores customer-related data including system ID, customer ID, group, name, sequence, flags, and active status)
{record_delimiter}
("entity"{tuple_delimiter}SYSTEM_ID{tuple_delimiter}FIELD{tuple_delimiter}Primary system identifier for the customer, marked as NOT NULL)
{record_delimiter}
("entity"{tuple_delimiter}CUST_ID{tuple_delimiter}FIELD{tuple_delimiter}Customer identifier, marked as NOT NULL)
{record_delimiter}
("entity"{tuple_delimiter}CUST_GROUP{tuple_delimiter}FIELD{tuple_delimiter}Customer group, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUST_NAME{tuple_delimiter}FIELD{tuple_delimiter}Customer name, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUST_SEQ{tuple_delimiter}FIELD{tuple_delimiter}Customer sequence number, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}FLAGS{tuple_delimiter}FIELD{tuple_delimiter}Flags field for customer metadata, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}ACTIVE{tuple_delimiter}FIELD{tuple_delimiter}Indicates whether the customer is active, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}VARCHAR2{tuple_delimiter}DATA TYPE{tuple_delimiter}String data type used in Oracle databases)
{record_delimiter}
("entity"{tuple_delimiter}NUMBER{tuple_delimiter}DATA TYPE{tuple_delimiter}Numeric data type used in Oracle databases)
{record_delimiter}
("entity"{tuple_delimiter}PK_DMART_CUSTOMERS{tuple_delimiter}INDEX{tuple_delimiter}Primary key constraint for DMART_CUSTOMERS table on SYSTEM_ID and CUST_ID)
{record_delimiter}
("relationship"{tuple_delimiter}PK_DMART_CUSTOMERS{tuple_delimiter}SYSTEM_ID{tuple_delimiter}SYSTEM_ID is part of primary key PK_DMART_CUSTOMERS{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}PK_DMART_CUSTOMERS{tuple_delimiter}CUST_ID{tuple_delimiter}CUST_ID is part of primary key PK_DMART_CUSTOMERS{tuple_delimiter}7)
{completion_delimiter}
#############################


Example 2:

entity_types: [user, sample, flag, diagnostic, index, table, field, data type, result, batch, analyte, detection limit, report, workorder, context, client, profile, charge, error, command, marker]
text:
CREATE TABLE DMART_PROJECTS_SUMMARY (
    SYSTEM_ID VARCHAR2 NULL,
    PROJECT_SEQ NUMBER NULL,
    LAB_WO_ID VARCHAR2 NULL,
    REQNBR NUMBER NULL,
    PROJECT_ID VARCHAR2 NULL,
    ACODE VARCHAR2 NULL,
    CREATE_DATE DATE NULL,
    LEVEL2X NUMBER NULL,
    LEVEL3X NUMBER NULL,
    OPEN_WIP_STATUS VARCHAR2 NULL,
    PROJECT_DESC VARCHAR2 NULL,
    PROJECT_TYPE VARCHAR2 NULL,
    PURCHASE_ORDER VARCHAR2 NULL,
    WIP_STATUS VARCHAR2 NULL,
    CUST_ID VARCHAR2 NULL,
    MANAGER VARCHAR2 NULL,
    LAST_UPDATE DATE NULL
);

------------------------
output:
("entity"{tuple_delimiter}DMART_PROJECTS_SUMMARY{tuple_delimiter}TABLE{tuple_delimiter}Table that stores project summary information including project identifiers, status, customer, and management details)
{record_delimiter}
("entity"{tuple_delimiter}SYSTEM_ID{tuple_delimiter}FIELD{tuple_delimiter}System identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_SEQ{tuple_delimiter}FIELD{tuple_delimiter}Project sequence number, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LAB_WO_ID{tuple_delimiter}FIELD{tuple_delimiter}Laboratory work order identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}REQNBR{tuple_delimiter}FIELD{tuple_delimiter}Requisition number, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_ID{tuple_delimiter}FIELD{tuple_delimiter}Unique project identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}ACODE{tuple_delimiter}FIELD{tuple_delimiter}Code associated with project or customer, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CREATE_DATE{tuple_delimiter}FIELD{tuple_delimiter}Date the project summary record was created, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LEVEL2X{tuple_delimiter}FIELD{tuple_delimiter}Level 2 classification or category for the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LEVEL3X{tuple_delimiter}FIELD{tuple_delimiter}Level 3 classification or category for the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}OPEN_WIP_STATUS{tuple_delimiter}FIELD{tuple_delimiter}Status of open work in progress, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_DESC{tuple_delimiter}FIELD{tuple_delimiter}Description of the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_TYPE{tuple_delimiter}FIELD{tuple_delimiter}Type of the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PURCHASE_ORDER{tuple_delimiter}FIELD{tuple_delimiter}Purchase order number associated with the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}WIP_STATUS{tuple_delimiter}FIELD{tuple_delimiter}Work in progress status, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUST_ID{tuple_delimiter}FIELD{tuple_delimiter}Customer identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}MANAGER{tuple_delimiter}FIELD{tuple_delimiter}Manager responsible for the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LAST_UPDATE{tuple_delimiter}FIELD{tuple_delimiter}Date of the last update to the project summary, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}VARCHAR2{tuple_delimiter}DATA TYPE{tuple_delimiter}String data type used in Oracle databases)
{record_delimiter}
("entity"{tuple_delimiter}NUMBER{tuple_delimiter}DATA TYPE{tuple_delimiter}Numeric data type used in Oracle databases)
{record_delimiter}
("entity"{tuple_delimiter}DATE{tuple_delimiter}DATA TYPE{tuple_delimiter}Date data type used in Oracle databases)
{completion_delimiter}
#############################


Example 3:

entity_types: [user, sample, flag, diagnostic, index, table, field, data type, result, batch, analyte, detection limit, report, workorder, context, client, profile, charge, error, command, marker]
text:
Customers Table (CUSTOMERS)


# Customers Table (CUSTOMERS)

* [Fields](Customers_Table.htm#Fields_of_CUSTOMERS)
* [Flags](Customers_Table.htm#Flags_of_CUSTOMERS)
* [Indexes](Customers_Table.htm#Indexes_of_CUSTOMERS)

Dynamic table CUSTOMERS stores information related to the laboratoryâs
customers. There is one entry in this table per customer/client.

## Fields of CUSTOMERS



| Field | Data Type | Description |
| ACTIVE | Varchar2(1) | Whether or not the laboratory is actively doing business with this customer. Valid values are âYâ and âNâ. |
| ARCHIVE_VOL | Number(4) | Reserved for system use. |
| CUST_GROUP | Varchar2(40) | Free-text grouping for the client. |
| CUST_ID | Varchar2(12) | Unique code used to identify a client; laboratory assigned. Typically, this value is the same as Accounts Receivable client account number, a value which will be associated with each charge as it is exported from LIMS during the invoicing process. This value may be referenced by other tables, though it is not technically the primary key.  Unique key. |
| CUST_NAME | Varchar2(60) | Client's name as the laboratory knows it. |
| CUST_SEQ | Number(10) | Unique identifier for a client.  Primary key. Generated from the CUST_SEQ sequence. |
| FLAGS | Varchar2(20) | See the [Flags of CUSTOMERS](#flags) table. |

### Flags of CUSTOMERS

Flags indicate the existence
or status of a particular condition. In HORIZON, these conditions are
typically properties of clients, samples, and procedures. Flags are referred
to as "properties" in HORIZON.


| Flag | Description and Value |
| 1 | Type of account. Values are customizable through [FLAGS_VERIFY.FLAG_TYPE](../Control_Tables/Flags_Verify_Table.htm#flag_type) = â[ACCT](../Control_Tables/Flags_of_Flags_Verify.htm#ACCT).â |
| 2 | Sales Tax calculation. Values are customizable; sales tax G is provided as an example. After Invoicing gathers all the charges for an invoice, it attempts to call an exposed PL/SQL procedure using the naming convention âsales_tax_â[value] where [value] is substituted with this flagâs value for the customer receiving the invoice.    | Value | Details | | . (dot) | No sales tax calculation is executed during invoicing. | | G | General sales tax charged. | |
| 3 | Invoicing cycle. This value is not used for workorder-based invoicing.    | Value | Details | | 0 (zero) | Invoice all available charges each time invoicing is run. |   All other values come from INVOICE_CUTOFFS.ALGORITHM. |
| 4 | Available for laboratory use. |
| 5-6 | Reserved for system use. |
| 7 | Whether locations are required and what types of locations can be used. Validation means that HORIZON checks for a match in the LOCATIONS table.    | Value | Details | | G | When a location is entered, it's validated against the global list. | | g | If a location is present, it's validated against the global list. | | N | Not required. Locations are not required for these samples. | | R | Required, don't validate. Locations are required for these samples but don't validate them. | | S | Required, validate against all locations attached to the study. | | s | Not required, validate against all locations attached to the study. | | V | Required, validate. Locations are required for these samples and they're validated against the client. | | v | If a location is present, it's validated against the client. | |
| 8-10 | Reserved for system use. |

### Indexes of CUSTOMERS

Indexes are database features
that allow HORIZON to query tables quickly and run efficiently. Columns
that share the same indexes form a subset of the database, allowing HORIZON
to locate information quickly in large databases by searching the subsets.



| Index | Field | Position |
| CUSTOMERS_U | CUST_ID | 1 |
| CUSTOMERS_A | ARCHIVE_VOL | 1 |
| CUSTOMERS_INDEX_2 | CUST_NAME | 1 |
| CUSTOMERS_INDEX_3 | CUST_GROUP | 1 |

------------------------
output:
("entity"{tuple_delimiter}DMART_PROJECTS_SUMMARY{tuple_delimiter}TABLE{tuple_delimiter}Table that stores project summary information including project identifiers, status, customer, and management details)
{record_delimiter}
("entity"{tuple_delimiter}SYSTEM_ID{tuple_delimiter}FIELD{tuple_delimiter}System identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_SEQ{tuple_delimiter}FIELD{tuple_delimiter}Project sequence number, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LAB_WO_ID{tuple_delimiter}FIELD{tuple_delimiter}Laboratory work order identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}REQNBR{tuple_delimiter}FIELD{tuple_delimiter}Requisition number, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_ID{tuple_delimiter}FIELD{tuple_delimiter}Unique project identifier, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}ACODE{tuple_delimiter}FIELD{tuple_delimiter}Code associated with project or customer, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CREATE_DATE{tuple_delimiter}FIELD{tuple_delimiter}Date the project summary record was created, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LEVEL2X{tuple_delimiter}FIELD{tuple_delimiter}Level 2 classification or category for the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LEVEL3X{tuple_delimiter}FIELD{tuple_delimiter}Level 3 classification or category for the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}OPEN_WIP_STATUS{tuple_delimiter}FIELD{tuple_delimiter}Status of open work in progress, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_DESC{tuple_delimiter}FIELD{tuple_delimiter}Description of the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PROJECT_TYPE{tuple_delimiter}FIELD{tuple_delimiter}Type of the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}PURCHASE_ORDER{tuple_delimiter}FIELD{tuple_delimiter}Purchase order number associated with the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}WIP_STATUS{tuple_delimiter}FIELD{tuple_delimiter}Work in progress status, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUST_ID{tuple_delimiter}FIELD{tuple_delimiter}Customer identifier, links to CUSTOMERS and DMART_CUSTOMERS table, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}MANAGER{tuple_delimiter}FIELD{tuple_delimiter}Manager responsible for the project, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LAST_UPDATE{tuple_delimiter}FIELD{tuple_delimiter}Date of the last update to the project summary, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}DMART_CUSTOMERS{tuple_delimiter}TABLE{tuple_delimiter}Table that stores customer-related data including system ID, customer ID, group, name, sequence, flags, and active status)
{record_delimiter}
("entity"{tuple_delimiter}SYSTEM_ID{tuple_delimiter}FIELD{tuple_delimiter}Primary system identifier for the customer, marked as NOT NULL)
{record_delimiter}
("entity"{tuple_delimiter}CUST_ID{tuple_delimiter}FIELD{tuple_delimiter}Customer identifier, marked as NOT NULL)
{record_delimiter}
("entity"{tuple_delimiter}CUST_GROUP{tuple_delimiter}FIELD{tuple_delimiter}Customer group, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUST_NAME{tuple_delimiter}FIELD{tuple_delimiter}Customer name, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUST_SEQ{tuple_delimiter}FIELD{tuple_delimiter}Customer sequence number, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}FLAGS{tuple_delimiter}FIELD{tuple_delimiter}Flags field for customer metadata, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}ACTIVE{tuple_delimiter}FIELD{tuple_delimiter}Indicates whether the customer is active, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CUSTOMERS{tuple_delimiter}TABLE{tuple_delimiter}Dynamic table that stores customer-related information such as client ID, name, group, and various flags for laboratory business logic)
{record_delimiter}
("entity"{tuple_delimiter}CUSTOMERS_U{tuple_delimiter}INDEX{tuple_delimiter}Unique index on CUST_ID field in CUSTOMERS table)
{record_delimiter}
("entity"{tuple_delimiter}CUSTOMERS_A{tuple_delimiter}INDEX{tuple_delimiter}Index on ARCHIVE_VOL field in CUSTOMERS table)
{record_delimiter}
("entity"{tuple_delimiter}CUSTOMERS_INDEX_2{tuple_delimiter}INDEX{tuple_delimiter}Index on CUST_NAME field in CUSTOMERS table)
{record_delimiter}
("entity"{tuple_delimiter}CUSTOMERS_INDEX_3{tuple_delimiter}INDEX{tuple_delimiter}Index on CUST_GROUP field in CUSTOMERS table)
{record_delimiter}
("relationship"{tuple_delimiter}DMART_PROJECTS_SUMMARY.CUST_ID{tuple_delimiter}DMART_CUSTOMERS.CUST_ID{tuple_delimiter}CUST_ID in DMART_PROJECTS_SUMMARY references CUST_ID in DMART_CUSTOMERS{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}DMART_PROJECTS_SUMMARY.CUST_ID{tuple_delimiter}CUSTOMERS.CUST_ID{tuple_delimiter}CUST_ID in DMART_PROJECTS_SUMMARY also references CUST_ID in CUSTOMERS table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}DMART_CUSTOMERS.CUST_ID{tuple_delimiter}CUSTOMERS.CUST_ID{tuple_delimiter}CUST_ID in DMART_CUSTOMERS references CUST_ID in CUSTOMERS table{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}CUSTOMERS_U{tuple_delimiter}CUST_ID{tuple_delimiter}CUST_ID is part of CUSTOMERS_U unique index{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CUSTOMERS_A{tuple_delimiter}ARCHIVE_VOL{tuple_delimiter}ARCHIVE_VOL is part of CUSTOMERS_A index{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CUSTOMERS_INDEX_2{tuple_delimiter}CUST_NAME{tuple_delimiter}CUST_NAME is part of CUSTOMERS_INDEX_2 index{tuple_delimiter}7)
{record_delimiter}
("relationship"{tuple_delimiter}CUSTOMERS_INDEX_3{tuple_delimiter}CUST_GROUP{tuple_delimiter}CUST_GROUP is part of CUSTOMERS_INDEX_3 index{tuple_delimiter}7)
{completion_delimiter}
#############################


Example 4:

entity_types: [field, data_type, analytical_results, lims_user, message, segment, subcomponent, index, recurrence, analyte, instrument, detection_limit, unit_of_measure, container, preservative, sample, api_security, project, workorder, sample_type, submitter]
text:
 "DMART_CUSTOMERS": {{
 "DMART_CUSTOMERS": {{
 "SYSTEM_ID": "system id",
 "CUST_ID": "cust id",
 "CUST_GROUP": "cust group",
 "CUST_NAME": "cust name. Value examples: ['DO NOT USE', 'DNU', 'Olsson Associates', 'AECOM', 'AEI Consultants', 'Ryder_Terracon']",
 "CUST_SEQ": "cust seq. Value examples: [4096, 628, 858, 1199, 4166, 1234]",
 "FLAGS": "flags. Value examples: ['0T0N..N..', 'IT0N..N..', 'CT0N..N..', 'GT0N..N..', 'N.0NNNN.', 'I.0N..N..']",
 "ACTIVE": "active. Value examples: ['Y', 'N']"
 }}
 }},

------------------------
output:
("entity"{tuple_delimiter}LIMS_PERMANENT_IDS{tuple_delimiter}TABLE{tuple_delimiter}Table containing permanent identifiers for LIMS samples including system id, HSN, and sample IDs)
{record_delimiter}
("entity"{tuple_delimiter}SYSTEM_ID{tuple_delimiter}FIELD{tuple_delimiter}System identifier field for LIMS permanent IDs)
{record_delimiter}
("entity"{tuple_delimiter}HSN{tuple_delimiter}FIELD{tuple_delimiter}HSN (likely a sample or batch related identifier) field for LIMS permanent IDs)
{record_delimiter}
("entity"{tuple_delimiter}CUST_SAMPLE_ID{tuple_delimiter}FIELD{tuple_delimiter}Customer-provided sample ID field for LIMS permanent IDs)
{record_delimiter}
("entity"{tuple_delimiter}LAB_SAMPLE_ID{tuple_delimiter}FIELD{tuple_delimiter}Laboratory-assigned sample ID field for LIMS permanent IDs)
{completion_delimiter}
#############################


Example 5:

entity_types: [field, data_type, analytical_results, lims_user, message, segment, subcomponent, index, recurrence, analyte, instrument, detection_limit, unit_of_measure, container, preservative, sample, api_security, project, workorder, sample_type, submitter]
text:
 Airbills Table (AIRBILLS)


# Airbills Table (AIRBILLS)

* [Fields](#Fields_of_AIRBILLS)
* [Index](#Index_of_AIRBILLS)

Dynamic table AIRBILLS tracks the carrier, airbill, and its associated
chains (their permanent identifiers, not just the package number). This
assumes that the scanning operation takes place before login.

## Fields of AIRBILLS



| Field | Data Type | Description |
| AIRBILL | Varchar2(40) | Airbill identifier, not necessarily unique. There is no constraint on primary key, but for the purposes of reference, AIRBILL and CARRIER define a row in this table.  This field cannot be null. |
| CARRIER | Varchar2(20) | Carrier identifier, validated against LEGAL_VALUE in [CHOICE_LISTS.CODE_TYPE](../Control_Tables/Code_Types_of_Choice_Lists.htm) = '[SHIPMD](../Control_Tables/Code_Types_of_Choice_Lists.htm#SHIPMD)'. |
| ORIGINAL_COC | Varchar2(20) | External chain-of-custody document identifier. |
| RECEIVE_DATE | Date | Date received. |
| USER_NBR | Varchar2(4) | LIMS user identifier of the person who scanned the airbill and chain.  Links to [LIMS_USERS.USER_NBR](LIMS_Users_Table.htm). |

### Index of AIRBILLS

Indexes are database features
that allow HORIZON to query tables quickly and run efficiently. Columns
that share the same indexes form a subset of the database, allowing HORIZON
to locate information quickly in large databases by searching the subsets.



| Index | Field | Position |
| AIRBILLS_INDEX_1 | ORIGINAL_COC | 1 |

------------------------
output:
("entity"{tuple_delimiter}AIRBILLS{tuple_delimiter}TABLE{tuple_delimiter}Dynamic table that tracks the carrier, airbill, and associated chains. Used before login during scanning operations)
{record_delimiter}
("entity"{tuple_delimiter}AIRBILL{tuple_delimiter}FIELD{tuple_delimiter}Airbill identifier, not necessarily unique, non-nullable)
{record_delimiter}
("entity"{tuple_delimiter}CARRIER{tuple_delimiter}FIELD{tuple_delimiter}Carrier identifier, validated against LEGAL_VALUE where CODE_TYPE = 'SHIPMD' in CHOICE_LISTS)
{record_delimiter}
("entity"{tuple_delimiter}ORIGINAL_COC{tuple_delimiter}FIELD{tuple_delimiter}External chain-of-custody document identifier)
{record_delimiter}
("entity"{tuple_delimiter}RECEIVE_DATE{tuple_delimiter}FIELD{tuple_delimiter}Date when the airbill and chain were received)
{record_delimiter}
("entity"{tuple_delimiter}USER_NBR{tuple_delimiter}FIELD{tuple_delimiter}LIMS user number of the person who scanned the airbill and chain)
{record_delimiter}
("entity"{tuple_delimiter}AIRBILLS_INDEX_1{tuple_delimiter}INDEX{tuple_delimiter}Index on ORIGINAL_COC field in AIRBILLS table)
{record_delimiter}
("entity"{tuple_delimiter}DMART_CHOICE_LISTS{tuple_delimiter}TABLE{tuple_delimiter}Table that stores configurable choice list values with fields such as code type, legal value, and flags)
{record_delimiter}
("entity"{tuple_delimiter}CTAB_ID{tuple_delimiter}FIELD{tuple_delimiter}Unique table ID for choice list entries, non-nullable)
{record_delimiter}
("entity"{tuple_delimiter}CODE_TYPE{tuple_delimiter}FIELD{tuple_delimiter}Type of choice code, non-nullable, e.g., SHIPMD for shipping methods)
{record_delimiter}
("entity"{tuple_delimiter}CHOICE_SEQ{tuple_delimiter}FIELD{tuple_delimiter}Choice sequence, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}CHOICE_DESC{tuple_delimiter}FIELD{tuple_delimiter}Description of the choice list value, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}LEGAL_VALUE{tuple_delimiter}FIELD{tuple_delimiter}Legal value for choice list validation, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}FLAGS{tuple_delimiter}FIELD{tuple_delimiter}Flags associated with choice list entry, nullable field)
{record_delimiter}
("entity"{tuple_delimiter}SORT_ITEM{tuple_delimiter}FIELD{tuple_delimiter}Sorting order for choice list, nullable field)
{record_delimiter}
("relationship"{tuple_delimiter}CARRIER{tuple_delimiter}DMART_CHOICE_LISTS.LEGAL_VALUE{tuple_delimiter}CARRIER field in AIRBILLS validates against LEGAL_VALUE in DMART_CHOICE_LISTS where CODE_TYPE = 'SHIPMD'{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}AIRBILLS_INDEX_1{tuple_delimiter}ORIGINAL_COC{tuple_delimiter}ORIGINAL_COC is part of AIRBILLS_INDEX_1 index{tuple_delimiter}7)
{completion_delimiter}
#############################



-Real Data-
######################
entity_types: [field, data_type, analytical_results, lims_user, message, segment, subcomponent, index, recurrence, analyte, instrument, detection_limit, unit_of_measure, container, preservative, sample, api_security, project, workorder, sample_type, submitter]
text: {input_text}
######################
output:

"""
