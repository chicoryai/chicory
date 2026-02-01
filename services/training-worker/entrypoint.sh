#!/bin/bash
set -e

# Define training type using environment variable with default
training_type=${TRAINING_TYPE:-"standalone"}

# Start the appropriate service based on TRAINING_TYPE
if [ "$training_type" = "standalone" ]; then
    echo "Starting standalone training service (one-time execution)"
    exec python main.py
else
    echo "Starting training service in managed mode (RabbitMQ consumer)"
    exec python managed.py
fi
