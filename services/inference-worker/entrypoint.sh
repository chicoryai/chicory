#!/bin/sh
set -e  # Exit on error

# Define workers using environment variables with defaults
workers=${WORKERS:-"1"}

# Determine which service to run based on the SERVICE_TYPE environment variable
service_type=${SERVICE_TYPE:-"slack"}

# Start the appropriate service based on SERVICE_TYPE
if [ "$service_type" = "pagerduty" ]; then
    # Run startup for self-hosted modes
    echo "Running startup script..."
    python startup.py
    echo "Starting PagerDuty Integration Service..."
    exec uvicorn main_pagerduty:app --host 0.0.0.0 --port 8000 --workers $workers
elif [ "$service_type" = "managed" ]; then
    # Managed mode: Skip startup.py - no S3 sync or PROJECT env needed
    echo "Starting Managed Inference Service (RabbitMQ consumer)..."
    exec python main_managed.py
elif [ "$service_type" = "slack" ]; then
    # Run startup for self-hosted modes
    echo "Running startup script..."
    python startup.py
    echo "Starting Slack Integration Service..."
    exec uvicorn main_slack:app --host 0.0.0.0 --port 8000 --workers $workers
else
    echo "Unknown SERVICE_TYPE: $service_type. Defaulting to Slack Integration Service..."
    python startup.py
    exec uvicorn main_slack:app --host 0.0.0.0 --port 8000 --workers $workers
fi
