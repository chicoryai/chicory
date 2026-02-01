from typing import Literal, List, Dict

from pydantic.v1 import BaseModel, Field
from typing_extensions import TypedDict


# Data model
class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["vectorstore", "cot_search"] = Field(
        ...,
        description="Given a user question choose to route it to cot search or a vectorstore.",
    )

class PythonREPLInput(BaseModel):
    command: str = Field(description="The Python command to execute")

class RouteQueryV4(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["rag_store", "bi_search"] = Field(
        ...,
        description="Given a user question choose to route it to bi_search or a rag_store.",
    )

class RouteQueryAPI(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["rag_store", "api_agent"] = Field(
        ...,
        description="Given a user question choose to route it to rag_store or api_agent.",
    )


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

## Graph state

class GraphStateHybrid(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        messages: list of messages
        context: full context required for llm to understand
    """

    question: str
    generation: str
    messages: List[str]
    context: str
    context_flag: bool
    output_format: str
    user: str
    project: str
    agent_id: str

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
        output_format: format for the agent's output (e.g., 'text', 'json', 'markdown')
    """

    project: str
    question: str
    breakdown: bool
    load_data: bool
    concise: bool
    generation: str
    global_flag: bool
    extracted_questions: List[str]
    documents: List[str]
    related_context: List[str]
    data_summary: str
    suggested_questions: Dict[str, List[str]]
    output_format: str


# Data model
class GradeAnswer(BaseModel):
    """Binary score to assess answer addresses question."""

    binary_score: str = Field(
        description="Answer addresses the question, 'yes' or 'no'"
    )

# Data model
class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: str = Field(
        description="Answer is grounded in the facts, 'yes' or 'no'"
    )