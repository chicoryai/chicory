import os
import json
import logging
import pika
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pika.exceptions import AMQPConnectionError, StreamLostError

# Configure logging
logger = logging.getLogger(__name__)

# Global connection variable for reuse
_connection = None
_channel = None


def get_rabbitmq_connection(retry_count=3, retry_delay=1.0):
    """
    Get a reusable RabbitMQ connection with retry logic
    
    Args:
        retry_count: Number of connection attempts before giving up
        retry_delay: Delay in seconds between retry attempts
        
    Returns:
        A RabbitMQ connection that can be reused across calls
        
    Raises:
        AMQPConnectionError: If all connection attempts fail
    """
    global _connection
    
    # If we have an existing connection and it's open, return it
    if _connection is not None and _connection.is_open:
        try:
            # Verify the connection is actually usable
            _connection.process_data_events()
            return _connection
        except (AMQPConnectionError, StreamLostError):
            # Connection is broken, set to None and try to reconnect
            _connection = None
            logger.warning("Detected broken RabbitMQ connection, reconnecting...")
    
    # Get RabbitMQ connection details from environment variables with defaults
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbitmq_vhost = os.getenv("RABBITMQ_VHOST", "/")
    rabbitmq_username = os.getenv("RABBITMQ_USERNAME", "guest")
    rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    # Check if we need SSL (port 5671 is the standard SSL port for RabbitMQ)
    use_ssl = rabbitmq_port == 5671
    
    # Set up SSL context if needed
    ssl_options = None
    if use_ssl:
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_options = pika.SSLOptions(ssl_context)
        logger.info("Using SSL for RabbitMQ connection")
    
    # Connect to RabbitMQ with appropriate SSL settings and enable heartbeats
    connection_params = pika.ConnectionParameters(
        host=rabbitmq_host,
        port=rabbitmq_port,
        virtual_host=rabbitmq_vhost,
        credentials=pika.PlainCredentials(
            rabbitmq_username, 
            rabbitmq_password
        ),
        ssl_options=ssl_options,
        heartbeat=30,  # Send heartbeat every 30 seconds to detect broken connections
        blocked_connection_timeout=10,  # Timeout for blocked connections
        connection_attempts=2,  # Try to connect twice initially
        retry_delay=0.5  # Half second delay between initial connection attempts
    )
    
    # Try to connect with retry logic
    last_exception = None
    for attempt in range(retry_count):
        try:
            logger.info(f"Connecting to RabbitMQ at {rabbitmq_host}:{rabbitmq_port} (attempt {attempt+1}/{retry_count})")
            _connection = pika.BlockingConnection(connection_params)
            logger.info("Successfully connected to RabbitMQ")
            return _connection
        except Exception as e:
            last_exception = e
            logger.warning(f"RabbitMQ connection attempt {attempt+1} failed: {str(e)}")
            if attempt < retry_count - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase delay for subsequent retries (backoff)
                retry_delay = min(retry_delay * 1.5, 5.0)
    
    # If we get here, all retries failed
    logger.error(f"Failed to connect to RabbitMQ after {retry_count} attempts")
    raise last_exception or AMQPConnectionError("Failed to connect to RabbitMQ")


def get_rabbitmq_channel(retry_count=3):
    """
    Get a reusable RabbitMQ channel with retry logic
    
    Args:
        retry_count: Number of channel creation attempts before giving up
        
    Returns:
        A RabbitMQ channel that can be reused across calls
        
    Raises:
        Exception: If all channel creation attempts fail
    """
    global _channel, _connection
    
    # Check if we have a valid channel
    if _channel is not None and _channel.is_open:
        try:
            # Verify channel is actually usable
            _channel.basic_qos(prefetch_count=1)
            return _channel
        except Exception as e:
            logger.warning(f"Existing RabbitMQ channel is broken: {str(e)}")
            _channel = None
    
    # Try to create a new channel with retry logic
    last_exception = None
    for attempt in range(retry_count):
        try:
            # Always get a fresh connection if we need a new channel
            connection = get_rabbitmq_connection()
            _channel = connection.channel()
            logger.info("Successfully created RabbitMQ channel")
            return _channel
        except Exception as e:
            last_exception = e
            logger.warning(f"RabbitMQ channel creation attempt {attempt+1} failed: {str(e)}")
            # Clear the broken connection and try again
            close_rabbitmq_connection()
            if attempt < retry_count - 1:
                time.sleep(0.5)
    
    # If we get here, all retries failed
    logger.error(f"Failed to create RabbitMQ channel after {retry_count} attempts")
    raise last_exception or Exception("Failed to create RabbitMQ channel")


def setup_rabbitmq_resources(queue_type='training', retry_count=3):
    """
    Set up RabbitMQ resources (exchange, queue, binding) if they don't exist
    
    Args:
        queue_type: Type of queue to set up ('training' or 'task')
        retry_count: Number of setup attempts before giving up
        
    Returns:
        Dict containing exchange, queue, and routing key names
    """
    # Try to set up resources with retry logic
    last_exception = None
    for attempt in range(retry_count):
        try:
            channel = get_rabbitmq_channel()
            
            # Define exchange, queue and routing key names based on queue type
            if queue_type == 'agent':
                # Agent message queue configuration
                exchange_name = os.getenv("AGENT_EXCHANGE_NAME", "task_exchange")
                queue_name = os.getenv("AGENT_QUEUE_NAME", "agent_tasks_queue")
                routing_key = os.getenv("AGENT_ROUTING_KEY", "agent.task")
            else:
                # Default to training queue configuration
                exchange_name = os.getenv("TRAINING_EXCHANGE_NAME", "training_exchange")
                queue_name = os.getenv("TRAINING_QUEUE_NAME", "training_queue")
                routing_key = os.getenv("TRAINING_ROUTING_KEY", "training.job")
            
            # Ensure the exchange exists
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='direct',
                durable=True  # Survive broker restarts
            )
            
            # Ensure the queue exists
            channel.queue_declare(
                queue=queue_name, 
                durable=True  # Survive broker restarts
            )
            
            # Bind the queue to the exchange
            channel.queue_bind(
                queue=queue_name,
                exchange=exchange_name,
                routing_key=routing_key
            )
            
            logger.info(f"Successfully set up RabbitMQ resources for {queue_type} (exchange: {exchange_name}, queue: {queue_name})")
            
            return {
                "exchange": exchange_name,
                "queue": queue_name,
                "routing_key": routing_key
            }
        except Exception as e:
            last_exception = e
            logger.warning(f"Failed to set up RabbitMQ resources (attempt {attempt+1}): {str(e)}")
            # Clear connections and try again
            close_rabbitmq_connection()
            if attempt < retry_count - 1:
                time.sleep(0.5)
    
    # If we get here, all retries failed
    logger.error(f"Failed to set up RabbitMQ resources after {retry_count} attempts")
    raise last_exception or Exception("Failed to set up RabbitMQ resources")


async def queue_training_job(training_id: str, project_id: str, project_name: str, data_source_ids: list, max_retries=3):
    """
    Queue a training job for processing using RabbitMQ with retry logic
    
    Args:
        training_id: ID of the training job
        project_id: ID of the project
        project_name: Name of the project
        data_source_ids: List of data source IDs to include in training
        max_retries: Maximum number of publish attempts before giving up
    """
    # The training service expects the PROJECT environment variable
    # and converts project names to lowercase for consistent directory naming
    project_name_lower = project_name.lower()
    os.environ["PROJECT"] = project_name_lower
    
    # Prepare message payload
    message = {
        "training_id": training_id,
        "project_id": project_id,
        "project_name": project_name_lower,
        "data_source_ids": data_source_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "start_training"
    }
    
    # Convert message to JSON string
    message_body = json.dumps(message)
    
    # Get queue configuration without setting up resources (they should already exist)
    # Define exchange, queue and routing key names for training
    exchange_name = os.getenv("TRAINING_EXCHANGE_NAME", "training_exchange")
    queue_name = os.getenv("TRAINING_QUEUE_NAME", "training_queue")
    routing_key = os.getenv("TRAINING_ROUTING_KEY", "training.job")
    
    rabbitmq_config = {
        "exchange": exchange_name,
        "queue": queue_name,
        "routing_key": routing_key
    }
    
    # Try to publish with retry logic
    last_exception = None
    for attempt in range(max_retries):
        try:
            channel = get_rabbitmq_channel()
            
            # Publish message
            channel.basic_publish(
                exchange=rabbitmq_config["exchange"],
                routing_key=rabbitmq_config["routing_key"],
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published training job {training_id} for project {project_id} to RabbitMQ")
            return  # Success, exit the function
            
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt+1} to queue training job failed: {str(e)}")
            
            # If this is the first attempt and the error might be due to missing queues,
            # try to set them up as a fallback
            if attempt == 0 and ("NOT_FOUND" in str(e) or "404" in str(e)):
                try:
                    logger.info("Queue might not exist, attempting to create it as fallback...")
                    setup_rabbitmq_resources(queue_type='training')
                    continue  # Retry immediately after creating the queue
                except Exception as setup_error:
                    logger.warning(f"Failed to create queue as fallback: {str(setup_error)}")
            
            # Reset connection on failure
            close_rabbitmq_connection()
            
            # If we have more retries, wait before trying again
            if attempt < max_retries - 1:
                wait_time = 0.5 * (attempt + 1)  # Progressive backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
    
    # If we get here, all retries failed
    error_msg = f"Failed to queue training job after {max_retries} attempts: {str(last_exception)}"
    logger.error(error_msg)
    
    # Import here to avoid circular imports
    from app.models.training import Training
    
    # Update training job status to failed
    training = await Training.get(training_id)
    if training:
        await training.update({
            "$set": {
                "status": "failed",
                "error": error_msg,
                "updated_at": datetime.now(timezone.utc)
            }
        })
    
    # Re-raise the exception for the caller to handle
    raise last_exception or Exception("Failed to queue training job")


async def queue_agent_task(task_id: str, assistant_task_id: str, agent_id: str, project_id: str, content: str, metadata: Dict[str, Any], max_retries=3):
    """
    Queue a task message for processing using RabbitMQ with retry logic
    
    Args:
        task_id: ID of the user task
        assistant_task_id: ID of the assistant task to be filled
        agent_id: ID of the task
        project_id: ID of the project
        content: Content of the task
        metadata: Additional metadata for the task. If it contains 'override_project_id', it will be propagated in the message
        max_retries: Maximum number of publish attempts before giving up
    """
    # Prepare message payload
    message = {
        "task_id": task_id,
        "assistant_task_id": assistant_task_id,
        "agent_id": agent_id,
        "project_id": project_id,
        "content": content,
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "process_task_message"
    }
    
    # If a project override is provided in metadata, include it in the message
    try:
        override_project_id = metadata.get("override_project_id") if isinstance(metadata, dict) else None
        if isinstance(override_project_id, str) and override_project_id.strip():
            message["override_project_id"] = override_project_id.strip()
            logger.debug(f"Including override_project_id in message: {override_project_id}")
    except Exception as e:
        logger.warning(f"Unable to read override_project_id from metadata: {e}")
    
    # Convert message to JSON string
    message_body = json.dumps(message)
    
    # Get queue configuration without setting up resources (they should already exist)
    # Define exchange, queue and routing key names for agent tasks
    exchange_name = os.getenv("AGENT_EXCHANGE_NAME", "task_exchange")
    queue_name = os.getenv("AGENT_QUEUE_NAME", "agent_tasks_queue")
    routing_key = os.getenv("AGENT_ROUTING_KEY", "agent.task")
    
    rabbitmq_config = {
        "exchange": exchange_name,
        "queue": queue_name,
        "routing_key": routing_key
    }
    
    # Try to publish with retry logic
    last_exception = None
    for attempt in range(max_retries):
        try:
            channel = get_rabbitmq_channel()
            
            # Use the queue name from the config
            queue_name = rabbitmq_config["queue"]
            
            # Publish message
            channel.basic_publish(
                exchange=rabbitmq_config["exchange"],
                routing_key=rabbitmq_config["routing_key"],
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published task message {task_id} for task {agent_id} to RabbitMQ")
            return  # Success, exit the function
            
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt+1} to queue task message failed: {str(e)}")
            
            # If this is the first attempt and the error might be due to missing queues,
            # try to set them up as a fallback
            if attempt == 0 and ("NOT_FOUND" in str(e) or "404" in str(e)):
                try:
                    logger.info("Queue might not exist, attempting to create it as fallback...")
                    setup_rabbitmq_resources(queue_type='agent')
                    continue  # Retry immediately after creating the queue
                except Exception as setup_error:
                    logger.warning(f"Failed to create queue as fallback: {str(setup_error)}")
            
            # Reset connection on failure
            close_rabbitmq_connection()
            
            # If we have more retries, wait before trying again
            if attempt < max_retries - 1:
                wait_time = 0.5 * (attempt + 1)  # Progressive backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
    
    # If we get here, all retries failed
    error_msg = f"Failed to queue task message after {max_retries} attempts: {str(last_exception)}"
    logger.error(error_msg)
    
    # Import here to avoid circular imports
    from app.models.tasks import Task, TaskStatus
    
    # Update message status to failed
    user_message = await Task.get(task_id)
    if user_message:
        user_message.metadata["error"] = error_msg
        user_message.status = TaskStatus.FAILED
        await user_message.save()
    
    assistant_message = await Task.get(assistant_task_id)
    if assistant_message:
        assistant_message.status = TaskStatus.FAILED
        await assistant_message.save()
    
    # Re-raise the exception for the caller to handle
    raise last_exception or Exception("Failed to queue task message")


def initialize_rabbitmq_queues():
    """
    Initialize all RabbitMQ queues on service startup
    This should be called during application startup to ensure all queues exist
    """
    try:
        logger.info("Initializing RabbitMQ queues on startup...")
        
        # Initialize training queue
        setup_rabbitmq_resources(queue_type='training')
        logger.info("Training queue initialized successfully")
        
        # Initialize agent task queue
        setup_rabbitmq_resources(queue_type='agent')
        logger.info("Agent task queue initialized successfully")
        
        logger.info("All RabbitMQ queues initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ queues on startup: {str(e)}")
        # Don't raise the exception - let the service start even if RabbitMQ is temporarily unavailable
        # The queues will be created when first message is sent if they don't exist


def close_rabbitmq_connection():
    """
    Close the RabbitMQ connection if it exists and is open
    """
    global _connection, _channel
    
    if _channel is not None and _channel.is_open:
        _channel.close()
        _channel = None
        
    if _connection is not None and _connection.is_open:
        _connection.close()
        _connection = None
