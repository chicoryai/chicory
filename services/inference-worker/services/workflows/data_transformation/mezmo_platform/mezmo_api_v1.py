import operator
import os
from pprint import pprint

import streamlit as st
import re

from langchain.globals import set_llm_cache
from langchain_community.agent_toolkits.openapi.spec import reduce_openapi_spec
from langchain_core.caches import InMemoryCache
from langchain_core.documents import Document
from langchain_community.utilities.openapi import OpenAPISpec
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from datetime import datetime, UTC
import yaml
from typing import TypedDict, List, Annotated, Tuple, Union

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import START
from pydantic.v1 import BaseModel, Field
from langchain_community.agent_toolkits import NLAToolkit
from langchain_openai import ChatOpenAI
from langchain_community.utilities import Requests, RequestsWrapper
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langgraph.graph import Graph, StateGraph
from langchain_community.agent_toolkits.openapi import planner

from services.workflows.const import route_prompt_system_v4, route_prompt_system_api
from services.utils.graphrag.graphrag_query_local import ainvoke_graphrag_search_local
from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v4 import initialize_brewsearch_state_workflow
from services.workflows.data_understanding.hybrid_rag.model.data import RouteQueryV4, RouteQueryAPI
from services.customer.personalization import get_project_config


class PlanExecute(TypedDict):
    question: str
    plan: List[str]
    tools: List[str]
    context: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    attributes: str

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

@st.cache_resource
def initialize_memzo_api_workflow_agent(user, project):

    if project.lower() == "Mezmo".lower():
        rag_app = initialize_brewsearch_state_workflow(user, "Mezmo")
    else:
        rag_app = None

    # Initialize OpenAI components
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    llm_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    reasoning_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chat_llm = ChatOpenAI(model="chatgpt-4o-latest", temperature=0)

    # Mezmo API authentication
    MEZMO_AUTH_TOKEN = os.getenv("MEZMO_AUTH_TOKEN")

    os.environ["LANGCHAIN_PROJECT"] = "Mezmo-API-Engineer"

    # Step 1:
    project_config = get_project_config(project)
    if not project_config:
        return None

    # Load OpenAPI spec
    openapi_spec_path = os.path.join(project_config["code_docs_path"], "openapi.yml")
    with open(openapi_spec_path, 'r') as file:
        openapi_spec_yaml = yaml.safe_load(file)
    # Create an OpenAPISpec instance from the local file
    # openapi_spec_path = Path("openapi.yml")
    openapi_spec = OpenAPISpec.model_validate(openapi_spec_yaml)
    mezmo_openai_api_spec = reduce_openapi_spec(openapi_spec_yaml)

    # Setup vector database for context retrieval
    def setup_vector_db(persist_path):
        vectorstore = Chroma(
            persist_directory=persist_path,
            embedding_function=OpenAIEmbeddings(),
            collection_name="unified_context_collection"
        )

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        store_context = vectorstore.get()
        all_docs_str = store_context['documents'] if 'documents' in store_context else []
        all_docs = [Document(page_content=t, metadata={"index": i}) for i, t in enumerate(all_docs_str)]
        # consolidating vector search with keyword search
        try:
            keyword_retriever = BM25Retriever.from_documents(all_docs)
            keyword_retriever.k = 3
            ensemble_retriever = EnsembleRetriever(retrievers=[retriever,
                                                               keyword_retriever],
                                                   weights=[0.3, 0.7])
            retriever = ensemble_retriever
        except Exception as e:
            print(e)

        return retriever

    context_retriever = setup_vector_db(project_config["persist_directory"])

    # Load OpenAPI spec and create NLAToolkit
    def load_mezmo_toolkit(openapi_spec):
        requests = Requests(headers={"Authorization": f"Token {MEZMO_AUTH_TOKEN}"})

        mezmo_toolkit = NLAToolkit.from_llm_and_spec(
            llm,
            openapi_spec,
            verbose=True,
            requests=requests,
            max_text_length=1800,
        )

        return mezmo_toolkit

    mezmo_toolkit = load_mezmo_toolkit(openapi_spec)
    mezmo_tools = mezmo_toolkit.get_tools()

    headers = {
        "Authorization": f"Token {MEZMO_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    requests_wrapper = RequestsWrapper(headers=headers)
    ALLOW_DANGEROUS_REQUEST = True

    agent_max_iterations = 5
    mezmo_kl_agent = planner.create_openapi_agent(
        mezmo_openai_api_spec,
        requests_wrapper,
        llm,
        agent_executor_kwargs={
            "return_intermediate_steps": True,
            "handle_parsing_errors": True,
            "max_iterations": agent_max_iterations,
            "early_stopping_method": "generate"
        },
        verbose=True,
        allow_dangerous_requests=ALLOW_DANGEROUS_REQUEST,
        handle_parsing_errors=True,
        max_iterations=agent_max_iterations,
        allowed_operations=("GET", "POST", "PUT", "DELETE"),
    )

    planner_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""As a world class Mezmo (logdna) platform expert, for the given objective, come up with a simple step by step plan. \
        This plan should involve individual tasks (strictly, in the scope of API call), that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
        The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

        Note:
        * If a step involves running an API command, always have a follow up validation step to make sure the completion of the previous step
        * ALWAYS validate if all the required attributes are provided in the user query, if not respond with asking for more information
        * The plan steps for execution should be very specific and not vague, for the executor to take proper action on
        * Please DO NOT answer the user questions without the memzo apis execution
        * Existing scope is to leverage api calls for any Mezmo account related question; so plan should be finalizing the endpoint to call, no pre step of setting up authentication with the server is required

        ======
        Examples:
        Question. What all pipelines I have in my Mezmo account?
        Hint. Would require to fetch data from GET https://api.mezmo.com/v3/pipeline

        Question. Give me all the details about the data sources for pipeline e8c7b20c-7f6b-11ef-9b08-d2803c0b88a1?"
        Hint. Would require to fetch/parse data from GET 'https://api.mezmo.com/v3/pipeline/e8c7b20c-7f6b-11ef-9b08-d2803c0b88a1'

        Question. How can I reduce the data volume without loosing data fidelity?
        Hint. Would require to fetch mezmo documentation context
        Ans. Use these three processors from our offering (like deduplicate using these regexps, turn these log lines into metrics using this processor, etc.)
        
        Question. Create a new pipeline (name - carbonara sqs pipeline) with aws sqs as source with these attributes:
        Hint. Would require to create a pipeline POST and then apply the source configuration changes to it by updating the created pipeline
        
        Question. Create a new pipeline to push the data from a spark custom app into datadog and store the HTTP logs in S3
        Hint. Breakdown of the above would be: * Create a new pipeline id xyz * Update pipeline id xyz to add spark custom app logs as source * Update pipeline id xyz to add datadog as destination * Update pipeline id xyz to add s3 as destination and have filtered HTTP logs move to s3
        
        Question. Export pipeline to terraform
        Hint. Steps: 
        * Initiate Export: POST /pipeline/<pipeline_id>/export
        * After initiating the export, you'll receive an export ID. Use this ID to retrieve the exported Terraform configuration: GET /pipeline/<pipeline_id>/export/<export_id>


        ======
        Available Tools:
        {", ".join([tool.name for tool in mezmo_tools])}

        """,
            ),
            ("placeholder", "{messages}"),
        ]
    )
    planner_chain = planner_prompt | llm.with_structured_output(Plan)

    replanner_prompt = ChatPromptTemplate.from_template(
        """As a world class Mezmo platform expert, for the given objective, come up with a simple step by step plan. \
    This plan should involve individual tasks (strictly, in the scope of API call), that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
    The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

    Note:
    * If a step involves running an API command, always have a follow up validation step to make sure the completion of the previous step
    * DO NOT repeat steps specially like creation, deletion or modification of resources, without validating the previous steps
    * ALWAYS refer to the past steps results to make sure the actions are not repeated, specially if related to creation, update or delete of resources
    * If an action has been executed successfully, make sure to build on top of previous results; for example, if pipeline has been created and requires some updates, do not create a new pipeline with each step, rather use the existing one
    * The plan steps for execution should be very specific and not vague, for the executor to take proper action on
    * ALWAYS validate if all the required attributes are provided in the user query, if not respond with asking for more information
    * Please DO NOT answer the user questions without the memzo apis execution
    * Existing scope is to leverage api calls for any Mezmo account related question; so plan should be finalizing the endpoint to call, no pre step of setting up authentication with the server is required

    ======
    Examples:
    Question. What all pipelines I have in my Mezmo account?
    Hint. Would require to fetch data from GET https://api.mezmo.com/v3/pipeline

    Question. Give me all the details about the data sources for pipeline e8c7b20c-7f6b-11ef-9b08-d2803c0b88a1?"
    Hint. Would require to fetch/parse data from GET 'https://api.mezmo.com/v3/pipeline/e8c7b20c-7f6b-11ef-9b08-d2803c0b88a1'

    Question. How can I reduce the data volume without loosing data fidelity?
    Hint. Would require to fetch mezmo documentation context
    Ans. Use these three processors from our offering (like deduplicate using these regexps, turn these log lines into metrics using this processor, etc.)
    
    Question. Create a new pipeline (name - carbonara sqs pipeline) with aws sqs as source with these attributes:
    Hint. Would require to create a pipeline POST and then apply the source configuration changes to it by updating the created pipeline
    
    Question. Create a new pipeline to push the data from a spark custom app into datadog and store the HTTP logs in S3
    Hint. Breakdown of the above would be: * Create a new pipeline id xyz * Update pipeline id xyz to add spark custom app logs as source * Update pipeline id xyz to add datadog as destination * Update pipeline id xyz to add s3 as destination and have filtered HTTP logs move to s3
    
    Question. Export pipeline to terraform
    Hint. Steps: 
    * Initiate Export: POST /pipeline/<pipeline_id>/export
    * After initiating the export, you'll receive an export ID. Use this ID to retrieve the exported Terraform configuration: GET /pipeline/<pipeline_id>/export/<export_id>

    ======
    Available Tools:
    {tools}

    Your objective was this:
    {question}
    
    Validation of the user query, for all required information:
    {attributes}

    Context:
    {context}

    Your original plan was this:
    {plan}

    You have currently done the follow steps:
    {past_steps}

    Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
    )

    replanner_chain = replanner_prompt | llm.with_structured_output(Act)

    # Prompt
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", route_prompt_system_api),
            ("human", "{question}"),
        ]
    )

    structured_llm_router = llm_mini.with_structured_output(RouteQueryAPI)
    question_router = route_prompt | structured_llm_router

    def handle_agent_error(error):
        if isinstance(error, str):
            return {"error": error}
        return {"error": str(error)}

    async def execute_step(state: PlanExecute):
        query = state["question"]
        plan = state["plan"]
        past_steps = state["past_steps"]
        plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
        task = plan[0]
        response_txt = ""
        if len(past_steps):
            last_step = past_steps[-1]
            if isinstance(last_step, tuple):
                dictt = last_step[1]
                if isinstance(dictt, dict):
                    if "output" in dictt:
                        response_txt += dictt["output"]
                    elif "error" in dictt:
                        response_txt += dictt["error"]
                else:
                    response_txt = str(dictt)
            else:
                response_txt = str(last_step)

    #     task_formatted = f"""For the following plan:
    #     {plan_str}\n\nYou are tasked with executing step {1}, {task}.
    #
    # =====
    # Additional Context:
    # {context}"""

        task_formatted = f"""As a part of ongoing plan execution. You are tasked with executing step - {task}.
\nPlease note, you have the confirmation and authorization from the user for this task."""

        if response_txt:
            task_formatted += f"""\n\nResponse of last run:\n{response_txt}\n\n"""
        if query:
            task_formatted += f"""Original Question:\n{query}\n\n"""
        if plan_str:
            task_formatted += f"""Overall plan:\n{plan_str}"""
        try:
            agent_response = await mezmo_kl_agent.ainvoke(task_formatted)
        except Exception as e:
            agent_response = handle_agent_error(e)
        return {
            "past_steps": [(agent_response)],
        }

    async def plan_step(state: PlanExecute):
        query = state["question"]
        contexts = context_retriever.invoke(query)
        state["context"] = [c.page_content for c in contexts]
        state["tools"] = ", ".join([tool.name for tool in mezmo_tools])
        context_message = "\n\n ".join([doc for doc in state["context"]])

        DEFAULT_RESPONSE_TYPE = """Respond as a json, with success flag, details, and requirement list as attributes"""
        response, _ = await ainvoke_graphrag_search_local(f"""For the given user query, does it include all the required information for a successful API call?\n Query: {query}""", DEFAULT_RESPONSE_TYPE,
                                                                "Mezmo")
        pattern = r'\[Data: .*?\]'
        attributes = re.sub(pattern, '', response)

        plan = await planner_chain.ainvoke({
            "messages": [
                ("user", query),  # User's message or query
                ("assistant", f"""\nContext:\n\n {context_message}"""),
                ("assistant", f"""\nQuery Validation:\n\n {attributes}"""),
            ],
        })
        return {"plan": plan.steps, "context": state["context"], "tools": state["tools"], "attributes": attributes}

    async def rag_store(state: PlanExecute):
        query = state["question"]
        inputs = {
            "question": query,
            "breakdown": False,
            "load_data": True,  # defaults to data validation rn
            "concise": False
        }
        config = {
            "recursion_limit": 20,
            "configurable": {
                "thread_id": "chicory-ui-discovery",
                "thread_ts": datetime.now(UTC).isoformat(),
                "client": "brewmind",
                "user": "user",
                "project": "Mezmo",
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

    async def replan_step(state: PlanExecute):
        output = await replanner_chain.ainvoke(state)
        if isinstance(output.action, Response):
            return {"response": output.action.response}
        else:
            return {"plan": output.action.steps}

    async def route_question(state):
        """
        Route question to api call or RAG.

        Args:
            state (dict): The current graph state

        Returns:
            str: Next node to call
        """

        print("---ROUTE QUESTION---")
        question = state["question"]
        source = question_router.invoke({"question": question})
        if source.datasource == "api_agent":
            print("---ROUTE QUESTION TO API Agent---")
            return "api_agent"
        elif source.datasource == "rag_store":
            print("---ROUTE QUESTION TO RAG---")
            return "rag_store"

    def should_end(state: PlanExecute):
        if "response" in state and state["response"]:
            return END
        else:
            return "agent"

    workflow = StateGraph(PlanExecute)

    # Add the plan node
    workflow.add_node("platform_expert", rag_store)

    # Add the plan node
    workflow.add_node("planner", plan_step)

    # Add the execution step
    workflow.add_node("agent", execute_step)

    # Add a replan node
    workflow.add_node("replan", replan_step)

    # workflow.add_edge(START, "planner")
    workflow.add_conditional_edges(
        START,
        route_question,
        {
            "api_agent": "planner",
            "rag_store": "platform_expert",
        },
    )

    # From plan we go to agent
    workflow.add_edge("planner", "agent")

    # From agent, we replan
    workflow.add_edge("agent", "replan")

    workflow.add_conditional_edges(
        "replan",
        # Next, we pass in the function that will determine which node is called next.
        should_end,
        ["agent", END],
    )

    # From SME we go to agent
    workflow.add_edge("platform_expert", END)

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    app = workflow.compile(checkpointer=memory)

    return app