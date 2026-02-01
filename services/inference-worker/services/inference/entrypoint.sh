#!/bin/sh
set -e  # Exit on error

# Define workers using environment variables with defaults
workers=${WORKERS:-"1"}

# Determine which service to run based on the SERVICE_TYPE environment variable
service_type=${SERVICE_TYPE:-"slack"}

# Run the startup script once
echo "Running startup script..."
python startup.py

# Start the appropriate service based on SERVICE_TYPE
if [ "$service_type" = "pagerduty" ]; then
    echo "Starting PagerDuty Integration Service..."
    exec uvicorn main_pagerduty:app --host 0.0.0.0 --port 8000 --workers $workers
elif [ "$service_type" = "managed" ]; then
    echo "Starting Managed Inference Service..."
    exec python main_managed.py
else
    echo "Starting Slack Integration Service..."
    exec uvicorn main_slack:app --host 0.0.0.0 --port 8000 --workers $workers
fi
