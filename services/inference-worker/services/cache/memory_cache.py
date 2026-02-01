import os

from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore


def initialize_memory_cache(embedding_model, set_llm_cache_flag=True):
    # Set up paths using environment variables
    home_path = os.getenv("HOME_PATH", "/app")
    data_path = os.getenv("BASE_DIR", os.path.join(home_path, "data"))
    project_name = os.environ.get('PROJECT', 'default').lower()
    cache_dir_path = os.environ.get("LLM_CACHE_PATH", os.path.join(data_path, project_name, ".cache"))

    # Create directory if it doesn't exist
    os.makedirs(cache_dir_path, exist_ok=True)

    if set_llm_cache_flag:
        # Setting cache file path
        llm_cache_path = os.path.join(cache_dir_path, "llm_cache.db")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(llm_cache_path), exist_ok=True)
        # SQLite cache for persistence
        set_llm_cache(SQLiteCache(database_path=llm_cache_path))

    # memory store setup for agents
    embedding_function = OpenAIEmbeddings(model=embedding_model)
    vector_store = Chroma(
        collection_name="memories",
        persist_directory=os.path.join(cache_dir_path, "mem_chroma_store"),
        embedding_function=embedding_function,
    )

    # TODO: replace this with AsyncSqliteSaver: https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver
    memory = MemorySaver()

    # LangGraph store for agent state
    langgraph_store = InMemoryStore()

    return memory, vector_store, langgraph_store
