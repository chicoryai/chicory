import os

from services.utils.logger import logger

# Try to import Phoenix/OpenInference - these are optional dependencies
try:
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from phoenix.otel import register
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    LangChainInstrumentor = None
    OpenAIInstrumentor = None
    register = None


def initialize_phoenix():
    """Initialize Phoenix OpenTelemetry integration if enabled."""
    enable_phoenix = os.getenv("ENABLE_PHOENIX_TRACING", "False").lower() == "true"

    if enable_phoenix:
        if not PHOENIX_AVAILABLE:
            logger.warning("Phoenix tracing requested but openinference/phoenix packages not installed. Skipping.")
            return

        phoenix_project = os.getenv("PHOENIX_PROJECT_NAME", "BrewSearch-Inference")
        phoenix_endpoint = f"{os.getenv('PHOENIX_ENDPOINT', 'http://localhost:6006')}/v1/traces"

        tracer_provider = register(
            project_name=phoenix_project,
            endpoint=phoenix_endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info(f"Phoenix tracing enabled for project: {phoenix_project}")
    else:
        logger.info("Phoenix tracing disabled")
