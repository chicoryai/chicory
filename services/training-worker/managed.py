#!/usr/bin/env python
import os
import json
import time
import asyncio
import requests
import logging
import pika
import multiprocessing
import sys
import signal
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pika.exceptions import AMQPConnectionError, StreamLostError

from services.training.training_steps import run_preprocessing

# Set multiprocessing start method to spawn for better memory management
multiprocessing.set_start_method('spawn', force=True)

# Configure logging
logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=logging_format)
logger = logging.getLogger(__name__)

# Base API URL for backend service
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Global flag for graceful shutdown
shutdown_flag = False

# Global connection and channel for RabbitMQ
_connection = None
_channel = None


class TrainingJobManager:
    """Manager class for handling training jobs from RabbitMQ"""
    
    def __init__(self):
        self.api_base_url = API_BASE_URL
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals for graceful shutdown"""
        global shutdown_flag
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_flag = True
        # If we have an active connection, close it
        if _connection and _connection.is_open:
            _connection.close()
    
    def get_rabbitmq_connection(self, retry_count=3, retry_delay=1.0):
        """
        Get a RabbitMQ connection with retry logic
        
        Args:
            retry_count: Number of connection attempts before giving up
            retry_delay: Delay in seconds between retry attempts
            
        Returns:
            A RabbitMQ connection
        
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
    
    def setup_rabbitmq_consumer(self):
        """
        Set up RabbitMQ resources for consuming training job messages
        
        Returns:
            Tuple of (connection, channel)
        """
        global _connection, _channel
        
        # Get a connection
        connection = self.get_rabbitmq_connection()
        _connection = connection
        
        # Create a channel
        channel = connection.channel()
        _channel = channel
        
        # Set prefetch count - only process one message at a time
        # This ensures we don't take on too many training jobs simultaneously
        channel.basic_qos(prefetch_count=1)
        
        # Define exchange and queue names
        exchange_name = os.getenv("TRAINING_EXCHANGE_NAME", "training_exchange")
        queue_name = os.getenv("TRAINING_QUEUE_NAME", "training_queue")
        routing_key = os.getenv("TRAINING_ROUTING_KEY", "training.job")
        
        # Ensure the exchange exists
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type='direct',
            durable=True  # Survive broker restarts
        )
        
        # First check if queue exists to avoid modifying properties of existing queue
        try:
            # Check if queue exists using passive declaration
            channel.queue_declare(queue=queue_name, passive=True)
            logger.info(f"Queue {queue_name} already exists, using existing configuration")
        except pika.exceptions.ChannelClosedByBroker:
            # Queue doesn't exist, create with our desired properties
            # Reopen channel as it was closed by the exception
            connection = self.get_rabbitmq_connection()
            _connection = connection
            channel = connection.channel()
            _channel = channel
            
            # Set prefetch count again since we have a new channel
            channel.basic_qos(prefetch_count=1)
            
            # Declare exchange again on the new channel
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='direct',
                durable=True
            )
            
            # Using a high message TTL (4 hours) for long-running training jobs
            queue_args = {
                'x-message-ttl': 14400000,  # 4 hours in milliseconds
                'x-max-priority': 10        # Allow priority messages
            }
            
            # Now create the queue with our desired properties
            channel.queue_declare(
                queue=queue_name, 
                durable=True,  # Survive broker restarts
                arguments=queue_args
            )
            logger.info(f"Created new queue {queue_name} with TTL and priority settings")
        
        # Bind the queue to the exchange
        channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )
        
        logger.info(f"RabbitMQ consumer set up for queue: {queue_name}")
        
        return connection, channel
    
    async def get_training_job(self, training_id: str, project_id: str) -> Dict[str, Any]:
        """
        Get training job details from the API
        
        Args:
            training_id: The ID of the training job
            project_id: The ID of the project
            
        Returns:
            Training job details
        """
        url = f"{self.api_base_url}/projects/{project_id}/training/{training_id}"
        logger.info(f"Getting training job details from: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting training job: {str(e)}")
            raise
    
    async def get_data_sources(self, project_id: str, data_source_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get data sources from the API
        
        Args:
            project_id: The ID of the project
            data_source_ids: List of data source IDs to retrieve
            
        Returns:
            List of data source configurations
        """
        # First get the list of all data sources for the project
        url = f"{self.api_base_url}/projects/{project_id}/data-sources"
        logger.info(f"Getting all data sources from: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            all_data_sources = response.json()["data_sources"]
            
            # Filter to only the requested data sources
            requested_data_sources = [ds for ds in all_data_sources if ds["id"] in data_source_ids]
            
            if len(requested_data_sources) != len(data_source_ids):
                logger.warning(f"Not all requested data sources were found. Requested: {len(data_source_ids)}, Found: {len(requested_data_sources)}")
            
            return requested_data_sources
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting data sources: {str(e)}")
            raise
    
    async def update_training_job_status(self, training_id: str, project_id: str, status: str, 
                                          progress: Optional[Dict[str, Any]] = None, 
                                          error: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Update the status of a training job via API
        
        Args:
            training_id: The ID of the training job
            project_id: The ID of the project
            status: The new status of the job (in_progress, completed, failed)
            progress: Optional progress information
            error: Optional error message if status is 'failed'
            
        Returns:
            Updated training job details or None if update fails
        """
        url = f"{self.api_base_url}/projects/{project_id}/training/{training_id}"
        
        # Prepare update data
        update_data = {"status": status}
        if progress is not None:
            update_data["progress"] = progress
        
        # Handle error field
        if error is not None:
            update_data["error"] = error
        # Explicitly reset error field when status is not 'failed'
        elif status != "failed":
            update_data["error"] = None  # Reset error for non-error states
        
        try:
            # Direct update approach - simpler and more reliable
            logger.info(f"Updating training job {training_id} status to '{status}'")
            response = requests.put(url, json=update_data)
            response.raise_for_status()
            updated_job = response.json()
            logger.info(f"Successfully updated training job {training_id} status")
            return updated_job
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating training job: {str(e)}")
            # Include more error details if available
            if hasattr(e, 'response') and e.response:
                try:
                    error_details = e.response.json()
                    logger.error(f"Error details: {error_details}")
                except:
                    logger.error(f"Status code: {e.response.status_code}")
            # Return None instead of raising to allow training to continue
            return None
    
    async def process_training_message(self, ch, method, properties, body) -> None:
        """
        Process a training job message from RabbitMQ
        
        Args:
            ch: The channel object
            method: The method frame
            properties: The properties
            body: The message body
        """
        training_id = None
        project_id = None
        
        try:
            # Parse the message
            message = json.loads(body)
            training_id = message.get("training_id")
            project_id = message.get("project_id")
            project_name = message.get("project_name")
            data_source_ids = message.get("data_source_ids", [])
            
            # Validate all required fields are present
            if not all([training_id, project_id, project_name]):
                logger.error(f"Missing required fields in message: {message}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
                
            logger.info(f"Received training job: {training_id} for project: {project_name} ({project_id})")
            
            # Get training job details
            training_job = await self.get_training_job(training_id, project_id)
            if not training_job:
                logger.error(f"Could not retrieve training job {training_id}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Check if there's already a training job in progress for this project
            # This prevents multiple simultaneous training jobs for the same project
            if training_job.get("status") == "in_progress":
                error_message = f"Training job {training_id} is already in progress, cannot reprocess"
                logger.warning(error_message)
                
                # No need to update status as it's already in progress
                # Just acknowledge the message to remove it from queue
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
                
            # Also check for any other in-progress training jobs for this project
            url = f"{self.api_base_url}/projects/{project_id}/training"
            try:
                response = requests.get(url)
                response.raise_for_status()
                all_training_jobs = response.json().get("training_jobs", [])
                
                # Filter for in-progress jobs that aren't this one
                other_in_progress = [
                    job for job in all_training_jobs 
                    if job.get("status") == "in_progress" and job.get("id") != training_id
                ]
                
                if other_in_progress:
                    error_message = f"Cannot process training job: Another job is already in progress for project {project_id}"
                    logger.warning(error_message)
                    
                    # Update job status to failed with informative message
                    await self.update_training_job_status(
                        training_id=training_id,
                        project_id=project_id,
                        status="failed",
                        error=error_message
                    )
                    
                    # Acknowledge the message to remove it from the queue
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                    
                # Skip the check for recently completed jobs
                from datetime import datetime
                
                # Note: TRAINING_RATE_LIMIT_HOURS restriction has been removed,
                # keeping only the in-progress training restriction
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error checking for other training jobs: {str(e)}")
                # Continue anyway, better to potentially have duplicate training than none
                
            # Update training job status to in_progress
            initial_progress = {
                "current_step": "initializing",
                "steps_completed": 0,
                "total_steps": 8,  # Typical steps: init, data prep, embedding, indexing, finalization
                "percent_complete": 0
            }
            update_result = await self.update_training_job_status(
                training_id=training_id,
                project_id=project_id,
                status="in_progress",
                progress=initial_progress
            )
            
            if not update_result:
                logger.warning(f"Could not update training job {training_id} to in_progress status, continuing anyway")
                
            # Acknowledge the message once we've set the job to in_progress
            # This prevents the message from being redelivered if the worker crashes during training
            logger.info(f"Acknowledging message for training job {training_id} as in-progress")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            # Get data sources configuration
            data_sources = await self.get_data_sources(project_id, data_source_ids)
            
            # Set environment variables for training
            os.environ["PROJECT"] = project_id.lower()  # Always use lowercase for directory naming
            
            # Execute training process
            await self.run_training_job(training_id, project_id, project_name, data_sources)
            
            # Mark as complete
            final_progress = {
                "current_step": "completed",
                "steps_completed": 8,
                "total_steps": 8,
                "percent_complete": 100
            }
            update_result = await self.update_training_job_status(
                training_id=training_id,
                project_id=project_id,
                status="completed",
                progress=final_progress
            )
            
            if not update_result:
                logger.warning(f"Could not update training job {training_id} to completed status")
            else:
                logger.info(f"Successfully completed training job {training_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in message: {str(e)}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        except Exception as e:
            logger.error(f"Error processing training job: {str(e)}", exc_info=True)
            
            # Only try to update status if we have the training ID and project ID
            if training_id and project_id:
                # Update training job status to failed
                error_message = f"Training job failed: {str(e)}"
                update_result = await self.update_training_job_status(
                    training_id=training_id,
                    project_id=project_id,
                    status="failed",
                    error=error_message
                )
                
                if not update_result:
                    logger.error(f"Could not update training job {training_id} to failed status")
            
            # Always acknowledge the message to avoid blocking the queue
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    async def run_training_job(self, training_id: str, project_id: str, project_name: str, data_sources: List[Dict[str, Any]]) -> None:
        """
        Run the training job using the configured parameters
        
        Args:
            training_id: The ID of the training job
            project_id: The ID of the project
            project_name: The name of the project
            data_sources: List of data source configurations
        """
        # Import the modular training steps
        from services.training.training_steps import (
            setup_environment,
            run_data_scanning,
            run_code_scanning,
            run_document_scanning,
            run_preprocessing,
            run_s3_sync
        )
        import os
        # Ensure PROJECT environment variable is set and lowercase
        os.environ["PROJECT"] = project_id.lower()  # Use project_name, not project_id for directories
        logger.info(f"Setting PROJECT environment variable to {os.environ['PROJECT']}")

        # Define the progress stages
        total_steps = 7
        progress_stages = [
            {
                "current_step": "initialization",
                "message": "Setting up environment",
                "steps_completed": 1,
                "total_steps": total_steps,
                "percent_complete": int(1 / total_steps * 100)
            },
            {
                "current_step": "data_scanning",
                "message": "Scanning data sources",
                "steps_completed": 2,
                "total_steps": total_steps,
                "percent_complete": int(2 / total_steps * 100)
            },
            {
                "current_step": "code_scanning",
                "message": "Scanning code repositories",
                "steps_completed": 3,
                "total_steps": total_steps,
                "percent_complete": int(3 / total_steps * 100)
            },
            {
                "current_step": "document_scanning",
                "message": "Scanning documents",
                "steps_completed": 4,
                "total_steps": total_steps,
                "percent_complete": int(4 / total_steps * 100)
            },
            {
                "current_step": "context_preprocessing",
                "message": "Preprocessing context",
                "steps_completed": 5,
                "total_steps": total_steps,
                "percent_complete": int(5 / total_steps * 100)
            },
            {
                "current_step": "context_generation",
                "message": "Generating context",
                "steps_completed": 6,
                "total_steps": total_steps,
                "percent_complete": int(6 / total_steps * 100)
            },
            {
                "current_step": "finalization",
                "message": "Syncing results",
                "steps_completed": 7,
                "total_steps": total_steps,
                "percent_complete": 100
            }
        ]
        
        try:
            logger.info(f"Starting training for project {project_name} (ID: {project_id})")
            
            # Step 1: Initialize environment
            await self.update_progress(training_id, project_id, progress_stages[0])
            config, dev_mode, skip_s3_sync = await setup_environment()
            
            # Configure data sources in environment (after environment setup)
            self.configure_data_sources(data_sources)
            
            # Step 2: Data scanning
            await self.update_progress(training_id, project_id, progress_stages[1])
            await run_data_scanning(config)
            
            # Step 3: Code scanning
            await self.update_progress(training_id, project_id, progress_stages[2])
            await run_code_scanning(config)
            
            # Step 4: Document scanning
            await self.update_progress(training_id, project_id, progress_stages[3])
            await run_document_scanning(config)

            # Step 5: Preprocess above downloaded data for > 1MB file
            await self.update_progress(training_id, project_id, progress_stages[4])
            await run_preprocessing(config)

            # Copy training docs to inference folder BEFORE context generation (no progress monitoring)
            await self.copy_training_docs_to_inference(project_id)
            
            # Step 6: Generate project documentation (context generation)
            await self.update_progress(training_id, project_id, progress_stages[5])
            await self.generate_project_documentation(training_id, project_id)
            
            # Copy training docs to inference folder AFTER context generation (no progress monitoring)
            await self.copy_training_docs_to_inference(project_id)
            
            # Step 7: Finalization (Sync to S3)
            await self.update_progress(training_id, project_id, progress_stages[6])
            await run_s3_sync(dev_mode, skip_s3_sync)
                        # Complete the job
            final_progress = {
                "current_step": "completed",
                "message": "Training completed successfully",
                "steps_completed": total_steps,
                "total_steps": total_steps,
                "percent_complete": 100
            }
            await self.update_training_job_status(
                training_id=training_id,
                project_id=project_id,
                status="completed",
                progress=final_progress
            )
            logger.info(f"Training completed for project {project_name}")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error in training job: {error_message}", exc_info=True)
            
            # Update job with error status
            await self.update_training_job_status(
                training_id=training_id,
                project_id=project_id,
                status="failed",
                error=error_message
            )
            raise
    
    async def copy_training_docs_to_inference(self, project_id: str) -> None:
        """
        Copy all training documents to the inference folder before context generation
        
        Args:
            project_id: The ID of the project
        """
        try:
            import shutil
            import os.path
            
            logger.info(f"Starting copy of training docs to inference folder for project {project_id}")
            
            # Get base data directory from environment variable, default to /data
            base_dir = os.getenv("BASE_DIR", "/data")
            source_dir = os.path.join(base_dir, project_id.lower())
            inference_dir = os.path.join(base_dir, "inference/data", project_id.lower())
            
            # Create inference directory if it doesn't exist
            os.makedirs(inference_dir, exist_ok=True)
            
            if os.path.exists(source_dir):
                logger.info(f"Copying training docs from {source_dir} to {inference_dir}...")
                
                # Use copy_tree to copy all files including subdirectories
                if os.path.isdir(source_dir):
                    # Remove existing files in inference directory to avoid conflicts
                    if os.path.exists(inference_dir):
                        for item in os.listdir(inference_dir):
                            item_path = os.path.join(inference_dir, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                    
                    # Copy all files from source to inference directory
                    for item in os.listdir(source_dir):
                        source_item = os.path.join(source_dir, item)
                        dest_item = os.path.join(inference_dir, item)
                        if os.path.isdir(source_item):
                            shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(source_item, dest_item)
                    
                    logger.info(f"Successfully copied all training docs to inference directory: {inference_dir}")
                else:
                    logger.warning(f"Source directory {source_dir} is not a directory, skipping copy")
            else:
                logger.warning(f"Source directory {source_dir} does not exist, skipping copy to inference directory")
                
        except Exception as copy_error:
            logger.error(f"Error copying training docs to inference directory: {str(copy_error)}", exc_info=True)
            # Don't raise the exception to avoid failing the entire training job
            # Just log the error and continue
            logger.warning("Continuing training without copying docs to inference directory")

    async def generate_project_documentation(self, training_id: str, project_id: str) -> None:
        """
        Generate project documentation by calling the projectmd endpoint,
        waiting for completion, and downloading the result as CLAUDE.md
        
        Args:
            training_id: The ID of the training job
            project_id: The ID of the project
        """
        import os
        try:
            logger.info(f"Starting project documentation generation for training {training_id}")
            
            # Step 1: Call the projectmd endpoint to start generation
            projectmd_url = f"{self.api_base_url}/projects/{project_id}/training/{training_id}/projectmd"
            
            logger.info(f"Calling projectmd endpoint: {projectmd_url}")
            response = requests.post(projectmd_url, timeout=30)
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to start project documentation generation. Status: {response.status_code}, Response: {response.text}")
                raise Exception(f"Failed to start project documentation generation: {response.status_code}")
            
            logger.info("Project documentation generation started successfully")
            
            # Step 2: Poll for completion
            training_url = f"{self.api_base_url}/projects/{project_id}/training/{training_id}"
            max_polls = 1800  # 30 minutes with 1-second intervals
            poll_count = 0
            
            logger.info("Waiting for project documentation generation to complete...")
            
            while poll_count < max_polls:
                try:
                    # Check training status
                    status_response = requests.get(training_url, timeout=10)
                    if status_response.status_code == 200:
                        training_data = status_response.json()
                        projectmd_generation = training_data.get("projectmd_generation")
                        
                        if projectmd_generation:
                            status = projectmd_generation.get("status")
                            
                            if status == "completed":
                                s3_url = projectmd_generation.get("s3_url")
                                if s3_url:
                                    logger.info(f"Project documentation generation completed. S3 URL: {s3_url}")
                                    break
                                else:
                                    logger.error("Project documentation completed but no S3 URL found")
                                    raise Exception("Project documentation completed but no S3 URL found")
                            elif status == "failed":
                                error_message = projectmd_generation.get("error_message", "Unknown error")
                                logger.error(f"Project documentation generation failed: {error_message}")
                                raise Exception(f"Project documentation generation failed: {error_message}")
                            elif status in ["queued", "in_progress"]:
                                logger.debug(f"Project documentation generation status: {status}")
                            else:
                                logger.warning(f"Unknown project documentation status: {status}")
                        else:
                            logger.debug("No projectmd_generation data found in response")
                    
                    # Wait before next poll
                    await asyncio.sleep(5)
                    poll_count += 1
                    
                except Exception as poll_error:
                    logger.warning(f"Error polling for project documentation status: {poll_error}")
                    await asyncio.sleep(1)
                    poll_count += 1
            
            if poll_count >= max_polls:
                raise Exception("Project documentation generation timed out after 30 minutes")
            
            # Step 3: Download the project.md content directly from S3 URL
            logger.info("Downloading project documentation from S3...")
            
            # Get the final training status to extract S3 URL
            final_status_response = requests.get(training_url, timeout=10)
            if final_status_response.status_code != 200:
                raise Exception("Failed to get final training status for S3 URL")
            
            final_training_data = final_status_response.json()
            final_projectmd_generation = final_training_data.get("projectmd_generation", {})
            s3_url = final_projectmd_generation.get("s3_url")
            
            if not s3_url:
                raise Exception("No S3 URL found in completed project documentation")

            # Parse S3 URL to extract bucket and key
            # Supports both s3:// format and https:// format
            import re
            if s3_url.startswith('s3://'):
                # Format: s3://bucket-name/key/path
                s3_path = s3_url.replace('s3://', '')
                parts = s3_path.split('/', 1)
                if len(parts) != 2:
                    raise Exception(f"Invalid S3 URL format: {s3_url}")
                s3_bucket = parts[0]
                s3_key = parts[1]
            else:
                # Legacy format: https://bucket-name.s3.region.amazonaws.com/key/path
                s3_url_pattern = r'https://([^.]+)\.s3\.([^.]+)\.amazonaws\.com/(.+)'
                match = re.match(s3_url_pattern, s3_url)
                if not match:
                    raise Exception(f"Invalid S3 URL format: {s3_url}")
                s3_bucket = match.group(1)
                s3_key = match.group(3)

            logger.info(f"Downloading from S3: s3://{s3_bucket}/{s3_key}")

            # Initialize S3 client with proper endpoint configuration
            # Works for both MinIO (local) and AWS S3 (cloud)
            from services.integration.s3_sync import _get_s3_client
            s3_client = _get_s3_client()

            # Download the file content from S3
            try:
                response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                project_md_content = response['Body'].read().decode('utf-8')
            except Exception as s3_error:
                logger.error(f"Failed to download from S3: {str(s3_error)}")
                raise Exception(f"Failed to download project documentation from S3: {str(s3_error)}")
            logger.info(f"Successfully downloaded project documentation ({len(project_md_content)} characters)")
            
            # Step 4: Save as CLAUDE.md in the raw folder
            import os
            base_dir = os.getenv("BASE_DIR", "/data")
            raw_dir = os.path.join(base_dir, project_id.lower(), "raw")
            
            # Create raw directory if it doesn't exist
            os.makedirs(raw_dir, exist_ok=True)
            
            claude_md_path = os.path.join(raw_dir, "CLAUDE.md")
            
            with open(claude_md_path, 'w', encoding='utf-8') as f:
                f.write(project_md_content)
            
            logger.info(f"Successfully saved project documentation as CLAUDE.md: {claude_md_path}")
            
        except Exception as e:
            logger.error(f"Error in project documentation generation: {str(e)}", exc_info=True)
            # Don't raise the exception to avoid failing the entire training job
            # Just log the error and continue
            logger.warning("Continuing training without project documentation")
    
    async def _run_step_in_isolated_process(self, func, **kwargs):
        """
        Run a specific training step in an isolated process for better memory management
        
        Args:
            func: The function to run in isolation
            **kwargs: Arguments to pass to the function
            
        Returns:
            Tuple of (success, error_message)
        """
        # Create a queue for getting results back from the process
        result_queue = multiprocessing.Queue()
        
        try:
            
            # Start process with the worker function at module level
            process = multiprocessing.Process(
                target=training_step_worker,  # This function will be defined at module level
                args=(func, kwargs, result_queue)
            )
            process.daemon = True  # Make process exit when main process exits
            process.start()
            
            # Wait for the process to complete and get the result
            success, error = result_queue.get()
            
            # Wait for the process to fully terminate
            process.join()
            
            return success, error
            
        except Exception as e:
            error_msg = f"Error setting up isolated process: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def configure_data_sources(self, data_sources: List[Dict[str, Any]]) -> None:
        """
        Configure environment and settings for data sources
        
        Args:
            data_sources: List of data source configurations
        """
        # Get project name from environment variable for all data sources (in uppercase)
        project_upper = os.environ.get("PROJECT", "").upper()
        
        # Set environment variables based on data source types
        for ds in data_sources:
            ds_type = ds.get("type")
            ds_config = ds.get("configuration", {})
            
            if ds_type == "github":
                # Set GitHub access token with project-specific variable
                if "access_token" in ds_config:
                    access_token = ds_config["access_token"]
                    os.environ[f"{project_upper}_GITHUB_ACCESS_TOKEN"] = access_token

                # Set GitHub username with project-specific variable
                if "username" in ds_config:
                    username = ds_config["username"]
                    os.environ[f"{project_upper}_GITHUB_USERNAME"] = username

                # Set GitHub base URL with project-specific variable
                base_url = "https://api.github.com"
                os.environ[f"{project_upper}_GITHUB_BASE_URL"] = base_url

                logger.info("Configured GitHub credentials")
            
            elif ds_type == "databricks":
                if "access_token" in ds_config:
                    os.environ[f"{project_upper}_DATABRICKS_ACCESS_TOKEN"] = ds_config["access_token"]
                if "host" in ds_config:
                    os.environ[f"{project_upper}_DATABRICKS_HOST"] = ds_config["host"]
                if "schema" in ds_config:
                    os.environ[f"{project_upper}_DATABRICKS_SCHEMA"] = ds_config["schema"]
                if "http_path" in ds_config:
                    os.environ[f"{project_upper}_DATABRICKS_HTTP_PATH"] = ds_config["http_path"]
                if "catalog" in ds_config:
                    os.environ[f"{project_upper}_DATABRICKS_CATALOG"] = ds_config["catalog"]
                logger.info("Configured Databricks credentials")
            elif ds_type == "bigquery":
                # For Google BigQuery, we might need to create a service account JSON file
                if "project_id" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_PROJECT_ID"] = ds_config["project_id"]
                if "private_key_id" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_PRIVATE_KEY_ID"] = ds_config["private_key_id"]
                if "private_key" in ds_config:
                    # Ensure newlines are properly formatted
                    private_key = ds_config["private_key"].replace("\\n", "\n")
                    os.environ[f"{project_upper}_BIGQUERY_PRIVATE_KEY"] = private_key
                if "client_email" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_CLIENT_EMAIL"] = ds_config["client_email"]
                if "client_id" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_CLIENT_ID"] = ds_config["client_id"]
                if "client_cert_url" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_CLIENT_CERT_URL"] = ds_config["client_cert_url"]
                if "dataset_id" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_DATASET_ID"] = ds_config["dataset_id"]
                if "location" in ds_config:
                    os.environ[f"{project_upper}_BIGQUERY_LOCATION"] = ds_config["location"]

                # Create a credentials dictionary for the credentials file
                creds = {
                    "type": "service_account",
                    "project_id": ds_config.get("project_id", ""),
                    "private_key_id": ds_config.get("private_key_id", ""),
                    "private_key": ds_config.get("private_key", "").replace("\\n", "\n"),
                    "client_email": ds_config.get("client_email", ""),
                    "client_id": ds_config.get("client_id", ""),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": ds_config.get("client_cert_url", ""),
                    "universe_domain": "googleapis.com"
                }

                # For backward compatibility, still create the credentials file
                credentials_path = "/tmp/google_bq_credentials.json"
                with open(credentials_path, "w") as f:
                    json.dump(creds, f)
                os.environ[f"{project_upper}_GOOGLE_BIGQUERY_CREDENTIALS"] = credentials_path

                logger.info("Configured Bigquery credentials")
            elif ds_type == "redshift":
                if "host" in ds_config:
                    os.environ[f"{project_upper}_REDSHIFT_HOST"] = ds_config["host"]
                if "port" in ds_config:
                    os.environ[f"{project_upper}_REDSHIFT_PORT"] = str(ds_config["port"])
                if "database" in ds_config:
                    os.environ[f"{project_upper}_REDSHIFT_DATABASE"] = ds_config["database"]
                if "user" in ds_config:
                    os.environ[f"{project_upper}_REDSHIFT_USER"] = ds_config["user"]
                if "password" in ds_config:
                    os.environ[f"{project_upper}_REDSHIFT_PASSWORD"] = ds_config["password"]
                logger.info("Configured Redshift credentials")
            elif ds_type == "snowflake":
                if "username" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_USERNAME"] = ds_config["username"]
                if "password" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_PASSWORD"] = ds_config["password"]
                if "private_key" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_PRIVATE_KEY"] = ds_config["private_key"]
                if "private_key_passphrase" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"] = ds_config["private_key_passphrase"]
                if "account" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_ACCOUNT"] = ds_config["account"]
                if "role" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_ROLE"] = ds_config["role"]
                if "owner" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_OWNER"] = ds_config["owner"]
                if "warehouse" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_WAREHOUSE"] = ds_config["warehouse"]
                if "database" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_DATABASE"] = ds_config["database"]
                if "schema" in ds_config:
                    os.environ[f"{project_upper}_SNOWFLAKE_SCHEMA"] = ds_config["schema"]
                logger.info("Configured Snowflake credentials")

            elif ds_type == "glue":
                # AWS Glue with IAM role-based authentication
                if "customer_account_id" in ds_config:
                    os.environ[f"{project_upper}_GLUE_CUSTOMER_ACCOUNT_ID"] = ds_config["customer_account_id"]
                if "role_name" in ds_config:
                    os.environ[f"{project_upper}_GLUE_ROLE_NAME"] = ds_config["role_name"]
                if "external_id" in ds_config:
                    os.environ[f"{project_upper}_GLUE_EXTERNAL_ID"] = ds_config["external_id"]
                if "region" in ds_config:
                    os.environ[f"{project_upper}_GLUE_REGION"] = ds_config["region"]
                if "database_names" in ds_config:
                    os.environ[f"{project_upper}_GLUE_DATABASE_NAMES"] = ds_config["database_names"]
                logger.info("Configured AWS Glue credentials")

            elif ds_type == "google_drive":
                # For Google Drive, we might need to create a service account JSON file
                # Service account details
                if "private_key_id" in ds_config:
                    os.environ[f"{project_upper}_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID"] = ds_config["private_key_id"]
                if "private_key" in ds_config:
                    # Ensure newlines are properly formatted
                    private_key = ds_config["private_key"].replace("\\n", "\n")
                    os.environ[f"{project_upper}_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY"] = private_key
                if "client_id" in ds_config:
                    os.environ[f"{project_upper}_GOOGLE_SERVICE_ACCOUNT_CLIENT_ID"] = ds_config["client_id"]
                if "client_email" in ds_config:
                    os.environ[f"{project_upper}_GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL"] = ds_config["client_email"]
                if "client_cert_url" in ds_config:
                    os.environ[f"{project_upper}_GOOGLE_SERVICE_ACCOUNT_CLIENT_CERT_URL"] = ds_config["client_cert_url"]
                if "project_id" in ds_config:
                    os.environ[f"{project_upper}_GOOGLE_PROJECT_ID"] = ds_config["project_id"]
                if "folder_id" in ds_config:
                    os.environ[f"{project_upper}_GOOGLE_FOLDER"] = ds_config["folder_id"]
                
                # Create a credentials dictionary for the credentials file
                creds = {
                    "type": "service_account",
                    "project_id": ds_config.get("project_id", ""),
                    "private_key_id": ds_config.get("private_key_id", ""),
                    "private_key": ds_config.get("private_key", "").replace("\\n", "\n"),
                    "client_email": ds_config.get("client_email", ""),
                    "client_id": ds_config.get("client_id", ""),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": ds_config.get("client_cert_url", "")
                }
                
                # For backward compatibility, still create the credentials file
                credentials_path = "/tmp/google_credentials.json"
                with open(credentials_path, "w") as f:
                    json.dump(creds, f)
                os.environ[f"{project_upper}_GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                
                logger.info("Configured Google Drive credentials")
            
            elif ds_type == "webfetch":
                # Webfetch (Firecrawl) configuration
                if "api_key" in ds_config:
                    os.environ[f"{project_upper}_WEBFETCH_API_KEY"] = ds_config["api_key"]
                if "mode" in ds_config:
                    os.environ[f"{project_upper}_WEBFETCH_MODE"] = ds_config["mode"]
                if "url" in ds_config:
                    os.environ[f"{project_upper}_WEBFETCH_URL"] = ds_config["url"]
                if "start_url" in ds_config:
                    os.environ[f"{project_upper}_WEBFETCH_START_URL"] = ds_config["start_url"]
                if "max_pages" in ds_config:
                    # Safely convert max_pages to string with validation
                    try:
                        max_pages_value = int(ds_config["max_pages"])
                        os.environ[f"{project_upper}_WEBFETCH_MAX_PAGES"] = str(max_pages_value)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid max_pages value '{ds_config['max_pages']}', using default 100")
                        os.environ[f"{project_upper}_WEBFETCH_MAX_PAGES"] = "100"
                logger.info("Configured Webfetch (Firecrawl) credentials")

            elif ds_type == "atlan":
                # Atlan data catalog configuration
                if "tenant_url" in ds_config:
                    os.environ[f"{project_upper}_ATLAN_TENANT_URL"] = ds_config["tenant_url"]
                if "api_token" in ds_config:
                    os.environ[f"{project_upper}_ATLAN_API_TOKEN"] = ds_config["api_token"]
                # Optional configuration
                if "max_assets" in ds_config:
                    os.environ[f"{project_upper}_ATLAN_MAX_ASSETS"] = str(ds_config["max_assets"])
                if "include_lineage" in ds_config:
                    os.environ[f"{project_upper}_ATLAN_INCLUDE_LINEAGE"] = str(ds_config["include_lineage"]).lower()
                if "include_glossary" in ds_config:
                    os.environ[f"{project_upper}_ATLAN_INCLUDE_GLOSSARY"] = str(ds_config["include_glossary"]).lower()
                if "asset_types" in ds_config:
                    os.environ[f"{project_upper}_ATLAN_ASSET_TYPES"] = ds_config["asset_types"]
                logger.info("Configured Atlan data catalog credentials")

            # Handle all S3-based file uploads (CSV, Excel, and generic files)
            elif ds_type in ["csv_upload", "xlsx_upload", "generic_file_upload"]:
                # Download file from S3
                try:
                    if "configuration" in ds and "s3_bucket" in ds["configuration"] and "s3_key" in ds["configuration"]:
                        s3_bucket = ds["configuration"]["s3_bucket"]
                        s3_key = ds["configuration"]["s3_key"]
                        
                        # Set default filename based on data source type
                        default_filename = "file.bin"
                        if ds_type == "csv_upload":
                            default_filename = "file.csv"
                        elif ds_type == "xlsx_upload":
                            default_filename = "file.xlsx"
                            
                        original_filename = ds["configuration"].get("original_filename", default_filename)
                        
                        # Get AWS region from environment variables
                        s3_region = os.getenv("AWS_REGION", "us-west-2")
                        
                        # Create directory structure if it doesn't exist
                        project_lower = project_upper.lower()  # Always use lowercase for directory naming
                        base_dir = os.getenv("BASE_DIR", os.path.join("/app", "data"))
                        
                        # Determine target directory based on data source type and category
                        if ds_type == "generic_file_upload":
                            # For generic files, use category to determine directory
                            category = ds["configuration"].get("category", "document")
                            if category == "code":
                                data_dir = os.path.join(base_dir, project_lower, "raw", "code")
                            else:  # document or default
                                data_dir = os.path.join(base_dir, project_lower, "raw", "documents")
                        else:
                            # For CSV and Excel files, place in the data directory
                            data_dir = os.path.join(base_dir, project_lower, "raw", "data")
                        
                        os.makedirs(data_dir, exist_ok=True)
                        
                        # Define local file path
                        local_filename = os.path.join(data_dir, original_filename)
                        
                        # Initialize S3 client using default credential chain (IAM roles, env vars, etc.)
                        # This will automatically use IAM role credentials when running in AWS
                        s3_client = boto3.client('s3', region_name=s3_region)
                        
                        # Generate source type name for logging
                        source_type_names = {
                            "csv_upload": "CSV",
                            "xlsx_upload": "Excel",
                            "generic_file_upload": "generic file"
                        }
                        source_type_name = source_type_names.get(ds_type, ds_type)
                        
                        # Download the file from S3
                        logger.info(f"Downloading {source_type_name} from S3: s3://{s3_bucket}/{s3_key} to {local_filename}")
                        s3_client.download_file(s3_bucket, s3_key, local_filename)
                        logger.info(f"Successfully downloaded {source_type_name} data source: {ds.get('name')} to {local_filename}")
                    else:
                        logger.warning(f"{ds_type} data source {ds.get('name')} missing S3 configuration")
                except Exception as e:
                    logger.error(f"Error downloading {ds_type} from S3: {str(e)}")

            # Handle folder uploads - download all files in the folder
            elif ds_type == "folder_upload":
                try:
                    config = ds.get("configuration", {})
                    s3_prefix = config.get("s3_prefix")
                    category = config.get("category", "document")
                    root_folder_name = config.get("root_folder_name", "uploaded_folder")

                    if s3_prefix:
                        # Get S3 bucket from environment
                        s3_bucket = os.getenv("S3_BUCKET")
                        s3_region = os.getenv("AWS_REGION", "us-west-2")

                        if not s3_bucket:
                            logger.warning(f"S3_BUCKET not configured, skipping folder upload: {ds.get('name')}")
                            continue

                        # Determine target directory based on category
                        project_lower = project_upper.lower()
                        base_dir = os.getenv("BASE_DIR", os.path.join("/app", "data"))

                        if category == "code":
                            target_dir = os.path.join(base_dir, project_lower, "raw", "code", root_folder_name)
                        elif category == "data":
                            target_dir = os.path.join(base_dir, project_lower, "raw", "data", root_folder_name)
                        else:  # document or default
                            target_dir = os.path.join(base_dir, project_lower, "raw", "documents", root_folder_name)

                        os.makedirs(target_dir, exist_ok=True)

                        # Initialize S3 client
                        s3_client = boto3.client('s3', region_name=s3_region)

                        # The files are stored under s3_prefix/files/
                        normalized_prefix = s3_prefix if s3_prefix.endswith('/') else f"{s3_prefix}/"
                        files_prefix = f"{normalized_prefix}files/"

                        logger.info(f"Downloading folder upload from S3: s3://{s3_bucket}/{files_prefix} to {target_dir}")

                        # List and download all files under the prefix
                        paginator = s3_client.get_paginator('list_objects_v2')
                        files_downloaded = 0
                        files_failed = 0
                        total_size_downloaded = 0

                        # Limits to prevent resource exhaustion
                        MAX_FILES_DOWNLOAD = 10000
                        MAX_SIZE_DOWNLOAD = 10 * 1024 * 1024 * 1024  # 10GB

                        should_stop = False
                        for page in paginator.paginate(Bucket=s3_bucket, Prefix=files_prefix):
                            if 'Contents' not in page:
                                continue

                            for obj in page['Contents']:
                                # Check file count limit
                                if files_downloaded >= MAX_FILES_DOWNLOAD:
                                    logger.warning(f"Reached maximum file limit ({MAX_FILES_DOWNLOAD}), stopping download")
                                    should_stop = True
                                    break

                                # Check total size limit
                                file_size = obj.get('Size', 0)
                                if total_size_downloaded + file_size > MAX_SIZE_DOWNLOAD:
                                    logger.warning(f"Total size would exceed limit ({MAX_SIZE_DOWNLOAD / (1024**3):.1f}GB), stopping download")
                                    should_stop = True
                                    break

                                s3_key = obj['Key']
                                if not s3_key.startswith(files_prefix):
                                    logger.warning(f"Skipping S3 key with unexpected prefix: {s3_key}")
                                    continue
                                if '..' in s3_key or s3_key.startswith('/'):
                                    logger.warning(f"Skipping S3 key with suspicious path components: {s3_key}")
                                    continue
                                # Extract relative path from the S3 key
                                # s3_key format: artifacts/{project_id}/folders/{upload_id}/files/{relative_path}
                                relative_path = s3_key[len(files_prefix):]

                                if not relative_path:  # Skip if empty (directory marker)
                                    continue

                                # Validate path to prevent path traversal attacks
                                normalized_path = os.path.normpath(relative_path)
                                if normalized_path.startswith('..') or os.path.isabs(normalized_path):
                                    logger.warning(f"Skipping suspicious path: {relative_path}")
                                    continue

                                # Create local file path preserving folder structure
                                local_path = os.path.join(target_dir, normalized_path)
                                if not os.path.realpath(local_path).startswith(os.path.realpath(target_dir) + os.sep):
                                    logger.warning(f"Skipping path that escapes target directory: {relative_path}")
                                    continue
                                if os.path.realpath(local_path) == os.path.realpath(target_dir):
                                    logger.warning(f"Skipping path that resolves to target directory itself: {relative_path}")
                                    continue
                                local_dir = os.path.dirname(local_path)
                                os.makedirs(local_dir, exist_ok=True)

                                # Download the file
                                try:
                                    s3_client.download_file(s3_bucket, s3_key, local_path)
                                    files_downloaded += 1
                                    total_size_downloaded += file_size
                                    if files_downloaded % 100 == 0:
                                        logger.info(f"Download progress: {files_downloaded} files, {total_size_downloaded / (1024**2):.1f}MB")
                                except Exception as download_error:
                                    logger.error(f"Failed to download {relative_path}: {str(download_error)}")
                                    files_failed += 1
                                    continue

                                logger.debug(f"Downloaded: {relative_path}")

                            if should_stop:
                                break

                        logger.info(f"Successfully downloaded folder upload: {ds.get('name')} ({files_downloaded} files, {files_failed} failed) to {target_dir}")
                        if files_downloaded >= MAX_FILES_DOWNLOAD:
                            logger.warning(f"Download stopped: reached file limit ({MAX_FILES_DOWNLOAD} files)")
                        elif total_size_downloaded >= MAX_SIZE_DOWNLOAD:
                            logger.warning(f"Download stopped: reached size limit ({MAX_SIZE_DOWNLOAD / (1024**3):.1f}GB)")
                    else:
                        logger.warning(f"Folder upload data source {ds.get('name')} missing s3_prefix configuration")
                except (ClientError, BotoCoreError) as e:
                    logger.error(f"S3/Boto3 error downloading folder upload: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error downloading folder upload from S3: {str(e)}")

        logger.info(f"Configured {len(data_sources)} data sources for training")
    
    async def update_progress(self, training_id: str, project_id: str, progress: Dict[str, Any]) -> None:
        """
        Update the progress of a training job
        
        Args:
            training_id: The ID of the training job
            project_id: The ID of the project
            progress: Progress information to update
        """
        # Update the progress but don't let failure stop the training process
        result = await self.update_training_job_status(
            training_id=training_id,
            project_id=project_id,
            status="in_progress",
            progress=progress
        )
        
        if result:
            logger.info(f"Updated progress: {progress.get('message', 'unknown')} ({progress.get('percent_complete', 0)}%)")
        else:
            logger.warning(f"Failed to update progress for training job {training_id}")
            # Continue training despite the update failure
    
    def start_consumer(self):
        """
        Start consuming messages from the RabbitMQ queue
        """
        # Set up initial variables
        connection = None
        channel = None
        reconnect_delay = 5  # Start with 5 seconds delay
        max_reconnect_delay = 60  # Maximum delay of 60 seconds
        queue_name = os.getenv("TRAINING_QUEUE_NAME", "training_queue")
        
        # Set up message consumption
        # Set visibility timeout via consumer configuration
        # Consumer will have sole access to the message during processing
        visibility_timeout = int(os.getenv("RABBITMQ_VISIBILITY_TIMEOUT", "7200"))  # 2 hours default
        
        logger.info(f"Setting RabbitMQ message visibility timeout to {visibility_timeout} seconds")
        
        # Initial connection setup
        try:
            connection, channel = self.setup_rabbitmq_consumer()
        except Exception as e:
            logger.error(f"Failed to establish initial RabbitMQ connection: {str(e)}")
            # Let the exception propagate to trigger container restart
            raise
        
        def callback(ch, method, properties, body):
            # Run the coroutine in the event loop
            try:
                asyncio.run(self.process_training_message(ch, method, properties, body))
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Acknowledge the message even if processing fails, to avoid infinite retry loops
                # This is a safety measure since we should already be acknowledging in process_training_message
                try:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as ack_error:
                    logger.error(f"Failed to acknowledge message after error: {str(ack_error)}")
        
        # Start consuming messages with extended visibility timeout
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        
        logger.info(f"Started consuming messages from queue: {queue_name}")
        logger.info("Waiting for training job messages. Press CTRL+C to exit.")
        
        try:
            # Start consuming in a loop that checks for shutdown flag
            while not shutdown_flag:
                if not connection or not connection.is_open:
                    # If connection is not available, try to reconnect
                    try:
                        logger.info("Attempting to reconnect to RabbitMQ...")
                        # Close the old connection if it's still around
                        if connection and connection.is_open:
                            try:
                                connection.close()
                            except Exception as close_error:
                                logger.warning(f"Error closing old connection: {str(close_error)}")
                        
                        # Set up a fresh connection
                        connection, channel = self.setup_rabbitmq_consumer()
                        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
                        logger.info("Successfully reconnected to RabbitMQ")
                        reconnect_delay = 5  # Reset delay after successful reconnection
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect: {str(reconnect_error)}")
                        # Implement exponential backoff for reconnect attempts
                        logger.info(f"Waiting {reconnect_delay} seconds before trying again")
                        time.sleep(reconnect_delay)
                        # Increase delay for next attempt, up to max_reconnect_delay
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                        continue  # Skip to next iteration after reconnect attempt
                
                try:
                    # Process messages but don't block indefinitely
                    connection.process_data_events(time_limit=1.0)
                    time.sleep(0.1)
                except (pika.exceptions.AMQPError, KeyboardInterrupt, ConnectionError, OSError) as e:
                    logger.warning(f"Connection issue: {str(e)}")
                    if not shutdown_flag:
                        # Mark the connection as closed to trigger reconnect on next iteration
                        if connection and connection.is_open:
                            try:
                                connection.close()
                            except Exception as close_error:
                                logger.warning(f"Error closing problematic connection: {str(close_error)}")
                        connection = None
                        channel = None
                        # Wait before trying again, but don't increase delay yet
                        time.sleep(reconnect_delay)
        except KeyboardInterrupt:
            logger.info("Interrupted by user, shutting down...")
        finally:
            # Clean up
            if connection and connection.is_open:
                try:
                    connection.close()
                    logger.info("RabbitMQ connection closed")
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")


# Module-level worker function for isolated process steps
def training_step_worker(target_func, func_args, result_q):
    try:
        import asyncio
        import gc
        import logging
        
        # Configure logging
        logger = logging.getLogger(__name__)
        
        # Create a new event loop for this process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Import the function dynamically to avoid pickling issues
        module_name = target_func.__module__
        func_name = target_func.__name__
        module = __import__(module_name, fromlist=[func_name])
        function = getattr(module, func_name)
        
        # Define an async function to run the step
        async def run_step():
            await function(**func_args)
            return True
        
        # Run the function
        success = loop.run_until_complete(run_step())
        loop.close()
        
        # Clean up memory
        gc.collect()
        
        # Signal success
        result_q.put((True, None))
    except Exception as e:
        # Capture any exceptions
        error_msg = f"Error in isolated process: {str(e)}"
        try:
            logger.error(error_msg, exc_info=True)
        except:
            print(f"ERROR: {error_msg}")  # Fallback if logger not available
        result_q.put((False, error_msg))

def main():
    """Main entry point for the training managed service"""
    try:
        # Initialize the training job manager
        manager = TrainingJobManager()
        
        # Start consuming messages
        manager.start_consumer()
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
