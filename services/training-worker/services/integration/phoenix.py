import os

from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor

from phoenix.otel import register
from services.utils.logger import logger


def initialize_phoenix():
    """Initialize Phoenix OpenTelemetry integration if enabled."""
    enable_phoenix = os.getenv("ENABLE_PHOENIX_TRACING", "False").lower() == "true"

    if enable_phoenix:
        phoenix_project = os.getenv("PHOENIX_PROJECT_NAME", "BrewSearch-Inference")
        phoenix_endpoint = f"{os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")}/v1/traces"

        tracer_provider = register(
            project_name=phoenix_project,
            endpoint=phoenix_endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info(f"Phoenix tracing enabled for project: {phoenix_project}")
    else:
        logger.info("Phoenix tracing disabled")
