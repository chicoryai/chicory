# Chicory Worker Common

Shared utilities for Chicory worker services (inference-worker and training-worker).

## Overview

This package consolidates shared code between the inference and training workers,
eliminating ~90% code duplication and providing consistent patterns.

## Installation

```bash
pip install -e packages/worker-common
```

Or add to your service's `pyproject.toml`:

```toml
dependencies = [
    "chicory-worker-common @ file:../../packages/worker-common",
]
```

## Modules

### `cache` - Memory and Redis Caching

```python
from chicory_worker_common.cache import MemoryCache, RedisMemoryCache, get_memory_cache

# Simple in-memory cache
cache = MemoryCache()
cache.set("key", {"data": "value"})

# Redis-backed cache for distributed workers
cache = RedisMemoryCache(redis_url="redis://localhost:6379")
```

### `loaders` - Document Loading (replaces LangChain)

```python
from chicory_worker_common.loaders import (
    Document,
    get_loader,
    load_document,
    PDFLoader,
    UnstructuredLoader,
    TextLoader,
)

# Auto-detect loader based on file extension
docs = load_document("report.pdf")

# Or use specific loaders
loader = PDFLoader("report.pdf", strategy="hi_res")
docs = loader.load()

# Universal loader using unstructured
loader = UnstructuredLoader("document.docx")
docs = loader.load()
```

### `agent` - Claude Agent SDK Utilities

```python
from chicory_worker_common.agent import (
    AgentOptionsBuilder,
    ClaudeAgentRunner,
    AgentRunConfig,
)

# Build options using the builder pattern
builder = AgentOptionsBuilder(working_directory="/tmp/workspace")
builder.with_mcp_servers({"db-mcp": {"type": "sse", "url": "http://..."}})
builder.with_system_prompt("You are a helpful assistant...")
options = builder.build()

# Run agent
config = AgentRunConfig(project_id="proj", agent_id="agent")
runner = ClaudeAgentRunner(config)
await runner.initialize(options)

result = await runner.run("What is 2+2?")
print(result.generation)

# Or stream (LangGraph-compatible interface)
async for event in runner.astream({"question": "..."}, config):
    print(event["agent_node"]["generation"])
```

## Migration from LangChain

### Document Loaders

Before (LangChain):
```python
from langchain_community.document_loaders import PyPDFLoader, TextLoader
loader = PyPDFLoader("doc.pdf")
```

After (worker-common):
```python
from chicory_worker_common.loaders import PDFLoader, TextLoader
loader = PDFLoader("doc.pdf")
```

### LangGraph Workflows

Before (LangGraph):
```python
from langgraph.graph import StateGraph
workflow = StateGraph(MyState)
workflow.add_node("agent", agent_action)
app = workflow.compile()
async for event in app.astream(input, config):
    ...
```

After (ClaudeAgentRunner):
```python
from chicory_worker_common.agent import ClaudeAgentRunner, AgentRunConfig
runner = ClaudeAgentRunner(AgentRunConfig(...))
await runner.initialize(options)
async for event in runner.astream(input, config):
    ...  # Same event format!
```

## Optional Dependencies

Install specific features:

```bash
# Cache support
pip install chicory-worker-common[cache]

# Document loaders
pip install chicory-worker-common[loaders]

# Claude Agent SDK
pip install chicory-worker-common[claude]

# Everything
pip install chicory-worker-common[all]
```
