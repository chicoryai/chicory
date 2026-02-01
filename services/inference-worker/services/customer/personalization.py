import os


def fetch_from_file(file_name):
    """
    Read URLs from a file and return them as a list.
    Each URL should be on a separate line in the file.

    Args:
        file_name (str): Path to the file containing URLs

    Returns:
        list: List of URLs read from the file
    """
    url_list = None
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            # Strip whitespace and newlines from each line
            url_list = [line.strip() for line in file if line.strip()]

    return url_list if url_list else []


def get_project_config(project):
    HOME_PATH = os.getenv("HOME_PATH", "/home/ubuntu/brewsearch")
    project = project.lower()
    data_path = f"{HOME_PATH}/data/{project}/raw/data"
    code_docs_path = f"{HOME_PATH}/data/{project}/raw/code"
    tbls_docs_path = f"{HOME_PATH}/data/{project}/preprocessed/data"
    persist_directory = f"{HOME_PATH}/data/{project}/vector.db"
    schema_file_path = f"{HOME_PATH}/data/{project}/preprocessed/data/schema.json.txt"
    metadata_file_path = f"{HOME_PATH}/data/{project}/preprocessed/data/metadata.json.txt"
    relation_file_path = f"{HOME_PATH}/data/{project}/preprocessed/data/relation.json.txt"
    data_source = f"{HOME_PATH}/data/{project}/raw/data/database.sqlite"
    graph_rag_source = f"{HOME_PATH}/data/{project}/graphrag/output"
    graph_rag_root = f"{HOME_PATH}/data/{project}/graphrag"
    api_dir = f"{HOME_PATH}/data/{project}/raw/api"
    work_directory = f"{HOME_PATH}/data/{project}/wd"
    runbook_directory = f"{HOME_PATH}/data/{project}/raw/documents/runbooks"
    catalog = f"{HOME_PATH}/data/{project}/wd/{project}_catalog.csv"
    url_list = fetch_from_file(f"{HOME_PATH}/data/{project}/raw/web/url.md")
    return {    "code_docs_path": code_docs_path,
                "tbls_docs_path": tbls_docs_path,
                "data_path": data_path,
                "url_list": url_list,
                "persist_directory": persist_directory,
                "schema_file_path": schema_file_path,
                "metadata_file_path": metadata_file_path,
                "relation_file_path": relation_file_path,
                "runbook_directory": runbook_directory,
                "data_source": data_source,
                "graph_rag_source": graph_rag_source,
                "graph_rag_root": graph_rag_root,
                "work_directory": work_directory,
                "api_directory": api_dir,
                "catalog": catalog,
            }


def get_project_instructions(project):
    if project.lower() == "ThredUp".lower():
        response_user_instructions = """
User Rules:
1. **Provide Only Factual Data**  
   The agent should **not** offer any **suggestions** unless specifically requested. The response must contain only **factual information**.
   - **Example of what should be avoided:**  
     "High levels of expired credits can indicate customer disengagement, which may impact loyalty and retention strategies. Businesses can address this by improving communication about credit offers or adjusting expiration policies to enhance customer satisfaction and retention."
2. **Reference Only Source or Target Tables**  
   Avoid mentioning **temporary, staging, or interim tables**. The response should reference only the **original source** or the **final target** table in any descriptions.
   - **Example:**  
     When describing refund orders in the `revenue_metrics` framework, do **not** mention tables like `REVENUE_METRICS_STG_REFUNDED_RETURNS`.
3. **Extract Key Formula Information**  
   If a metric's derivation is **not straightforward**, provide the **core logic** from the code as an additional note or explanation. This should give clarity on how the metric is calculated.
   - **Example:**  
     For a "net" column, you can explain:  
     "The 'net' value represents the net amount for order products or transactions after adjustments like discounts and taxes."  
     Additionally, you could include the formula logic:  
     `item_price + (surcharge - returned_surcharge) + per_item_shipping_revenue + per_item_rma_shipping_revenue - restocking_fee - total_discount - returned_price - per_item_nc_credit_expense + kfc_amount_expired - accounts_payable AS net_revenue`
4. **No Limit on Knowledge Extraction**  
   There is no limit to the amount of knowledge that can be extracted from the code. The more comprehensive and detailed the extraction, the **more valuable** the output will be.
   
=====
**Examples:**

Question: Describe the column ep_cohort in the edw.user_metrics table.
Answer: It categorizes users based on their purchase history. If the user's last purchase was more than 365 days ago, they are categorized as 'churned'. If it was within 180 to 365 days, they are categorized as 'pre-churned'. For purchases within the last 180 days, if the last order falls between the 1st and 3rd orders, the user is categorized as '1-3TP'. If the last order falls between the 4th and 9th orders, they are categorized as '4-9TP'. Finally, if the last order is the 10th or greater, the user is categorized as '10+TP'.
Hints: Column and table name need not be mentioned everytime, like "The 'ep_cohort' column in the edw.user_metrics table"

Question: Describe the column user_tp_bucket in the edw.user_metrics table.
Answer: It categorizes users based on their transaction patterns. Specifically, it assigns users to buckets according to the sequence of their last paid order. If the user's last order sequence is 1, they are categorized as '1TP.' If it is between 2 and 3, they are categorized as '2-3TP.' If it falls between 4 and 9, they are categorized as '4-9TP.' If it is greater than 10, they are categorized as '10+TP'.
Hints: Column and table name need not be mentioned everytime, like "The 'user_tp_bucket' column in the 'edw.user_metrics' table"
Omit general statement like: This categorization helps in understanding user engagement and transaction frequency, aiding in targeted marketing and customer relationship management.

Question: Describe the column ltm_grnd in the edw.user_metrics table.
Answer: It represents the total monetary amount paid by a user after applying discounts and adding surcharges (gross_revenue - total_discount + surcharge) in the last twelve months.
Hints: Column and table name need not be mentioned everytime, like "The ltm_grnd column"
Omit general statement like: This value is calculated as the gross revenue minus total discounts plus any applicable surcharges within the last twelve months. It provides insights into the net revenue generated from user activities over this period, which is crucial for understanding user spending behavior and the effectiveness of pricing strategies.

Question: Describe the column current_loyalty_tier in the edw.user_metrics table.
Answer: It represents the current active loyalty tier of a user. It is derived by merging data from the 'loyalty_accounts' and 'loyalty_account_tier_enrollments' tables. The logic involves selecting the most recent active tier for each user by ordering the enrollments by the 'started_at' date in descending order and taking the top-ranked tier. The tier names are mapped to user-friendly labels such as 'Star', 'Superstar', and 'VIT' based on the tier level.
Hints: Column and table name need not be mentioned everytime, like "The 'current_loyalty_tier' column in the edw.user_metrics table". It does not say tier_1 = Star, tier_2 = Supersdtar, tier_3 = VIT
Omit general statement like: This process ensures that the column reflects the latest loyalty status of the user, which is crucial for personalized marketing and engagement strategies.

"""
    else:
        response_user_instructions = ""

    response_system_hints = """
System Hints:
* Stick to the Context: Avoid providing speculative information or making assumptions. Base your answers strictly on the provided context.
* Direct and Contextual Responses: When the question is specific, ensure your answer is derived from the given context.
* Control SQL Queries: Avoid including excessive SQL queries or models in responses, unless asked for.
* Clarify with Background: Offering a brief introduction or background can help the user better understand the system or query.
* High-Level with Code/Data Support: Provide high-level explanations, but always back them up with actual code or data where relevant.
* Use GraphRAG as the Baseline: Treat GraphRAG outputs as the foundational truth to prevent hallucinations.
* Concise Summaries: Summarize responses clearly and concisely, avoiding detailed discussions about data models or tables unless specifically requested.
* Ensure Valid SQL Queries: If a SQL query is requested, ALWAYS return a valid query along with the data it retrieves from execution.
"""

    if project.lower() == "ThredUp".lower():
        response_system_detailed_template = """
Provide detailed responses with real examples, where applicable.

Ensure the following information is included, in any order or format as relevant:

1. Answer: A comprehensive summary addressing the question, including insights about all the entities involved.
2. Business Process Overview: Explain the complete business process and its relevance to the context.
3. Key Entities, Attributes, and Relationships: Identify and describe key entities, their attributes, and relationships within the given context.
4. Datapipeline Code Snippet: Include relevant code snippets or models based on the provided documents or context.
5. Database Data View: Present supporting data fetched from the source, if applicable, in a tabular format.
6. Reasoning: Provide an explanation of the logical flow leading to the conclusion.
7. Data Source References: Reference any data sources used to support the response.
8. Summary: Tailor the summary specifically to the business context, avoiding overly generic descriptions.
"""
    else:
        response_system_detailed_template = "" # Removing the default template here

    if project.lower() == "ThredUp".lower():
        response_system_concise_template = """
    Always aim for brevity and clarity.
    
    Strictly follow this response format:
    - Provide a single paragraph that delivers a concise, to-the-point answer, including supporting reasoning and evidence. 
    - Avoid including excessive SQL queries or raw data, but use insights derived from them to shape your response.
    - Most importantly, offer a broader perspective on how the question fits into the entire ecosystem.
    
    Additional Hints:
    - Always provide insights about all the entities mentioned in the question: what they are, how they are used, and why they are crucial for the business.
    - Tailor the response specifically to the business context, avoiding generic explanations applicable to any e-commerce business.
    """
    else:
        response_system_concise_template = ""

    response_validation_examples = """
    
    """

    return response_user_instructions, response_system_hints, response_system_detailed_template, response_system_concise_template


thredup_questions_list = [
    # Data Perspective
    "How is the `order_id` used to link different tables such as `edw_fact_order_products` and `ods_shop_orders`?",
    "What are the key attributes of the `edw_dim_concierge_bags` table that contribute to understanding customer behavior?",
    "How does the `edw_order_metrics` table help in analyzing promotional effectiveness?",
    "What is the significance of the `is_vip_customer_bag` attribute in the `edw_dim_concierge_bags` table?",
    "How are timestamps like `created_at` and `purchased_at` used to track order lifecycles in `edw_fact_order_products`?",
    "What role does the `discount` attribute play in the `ods_shop_order_products` table?",
    "How is the `user_id` utilized across different tables to analyze customer interactions?",
    "What insights can be derived from the `promo_name` and `promo_type` attributes in the `edw_order_metrics` table?",
    "How does the `order_platform` attribute in `edw_seq_item_order` affect data analysis?",
    "What is the impact of `is_dropship` on order processing in the `edw_seq_paid_order` table?",
    "How does the `KFC_AMOUNT_EXPIRED` attribute contribute to net revenue calculations?",
    "What is the relationship between `item_order_sequence` and `paid_item_order_sequence` in tracking bundle orders?",
    "How does the `KFC_AMOUNT_ACCEPTED` attribute impact financial analysis?",
    "What is the role of the `KFC_AMOUNT_REJECTED` attribute in transaction analysis?",
    "How are `promo_credits` tracked and utilized in customer retention strategies?",
    "How does the `order_state` attribute in `edw_seq_paid_order` affect fulfillment processes?",
    "What is the significance of the `OBJECTIVE` attribute in the `FB_ADSET_INSIGHTS` table for campaign analysis?",
    "How does the `ORDER_ADDRESSES` table contribute to logistics and delivery analysis?",
    "How are `sales_source` and `order_platform` used to segment customer behavior?",
    "What are the key performance indicators derived from the `edw_order_metrics` table?",

    # Engineering Perspective
    "How are data integrity and consistency maintained across tables like `edw_fact_order_products` and `ods_shop_orders`?",
    "What are the challenges in integrating data from different sources like `edw_dim_concierge_bags` and `ods_shop_order_products`?",
    "How does the database schema support scalability for increasing data volumes?",
    "What are the best practices for managing timestamps in tables like `edw_seq_item_order`?",
    "How is data redundancy minimized in the database schema?",
    "What are the key considerations for optimizing query performance on large tables like `edw_fact_order_products`?",
    "How does the schema design support real-time data processing?",
    "What are the security considerations for handling sensitive data in tables like `ods_shop_orders`?",
    "How is data versioning managed in the database?",
    "What are the implications of schema changes on existing data models?",
    "How does the `DBT_UTILS.UNION_RELATIONS` function enhance data analysis in e-commerce?",
    "What role does the `CONTEXT` entity play in data processing tasks?",
    "How are source tables managed within the DBT framework?",
    "What are the dependencies of the `RAW_CODE` entity in SQL models?",
    "How does BigQuery handle large datasets in e-commerce operations?",
    "What are the key attributes of the `SOURCES` entity in data models?",
    "How is the `REF` function integrated with `DBT_UTILS.UNION_RELATIONS`?",
    "What configurations are necessary for BigQuery authentication?",
    "How does the `CONTEXT` entity affect event handling in data processing?",
    "What is the significance of the `RELATIONS` parameter in data union operations?",

    # Business Perspective
    "How does the analysis of `order_type` in `edw_seq_item_order` contribute to business strategy?",
    "What are the business implications of high `discount` values in `ods_shop_order_products`?",
    "How does customer segmentation based on `user_id` enhance marketing efforts?",
    "What is the role of `promo_credits` in customer retention strategies?",
    "How does the `order_state` attribute in `edw_seq_paid_order` affect fulfillment processes?",
    "What insights can be gained from analyzing `sales_source` in `edw_fact_order_products`?",
    "How does the `is_vip_customer_bag` attribute influence customer loyalty programs?",
    "What are the strategic benefits of understanding `order_platform` usage patterns?",
    "How does the `is_dropship` attribute impact supply chain management?",
    "What are the key performance indicators derived from `edw_order_metrics`?"
]
