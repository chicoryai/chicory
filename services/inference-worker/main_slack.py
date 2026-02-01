import asyncio
import json
import hashlib
import hmac
import logging
import os
import sys
import time
import re

from services.integration.s3_sync import sync_s3_from_bucket
from services.utils.config import load_default_envs

# Load default envs
load_default_envs()

from fastapi import HTTPException, Header, Response, status, BackgroundTasks
from pprint import pprint
from datetime import datetime, UTC
from fastapi import FastAPI, Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

log_level = os.getenv("LOG_LEVEL", "INFO").lower()
logging.basicConfig(level=logging.INFO if log_level == "info" else logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Slack client
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_bot_id = os.getenv("SLACK_BOT_ID").upper()
slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
enable_test_endpoint = os.getenv("ENABLE_TEST_ENDPOINT", "false").lower() == "true"

client = WebClient(token=slack_bot_token)

project = os.getenv("PROJECT")

from services.workflows.data_understanding.hybrid_rag.adaptive_rag import initialize_agent
from services.integration.phoenix import initialize_phoenix

# Initialize Phoenix tracing
initialize_phoenix()

# Initialize Chicory Agent Workflow Client
chat_backend_app = initialize_agent("slack_bot", project)
MAX_TEXT_LENGTH = 3000  # Slack's maximum character limit for a single block of text

# Define the FastAPI application
app = FastAPI(
    title="BrewMind Hub Chatbot",
    description="Chicory AI Autopilot Data Engineer",
    debug=False if log_level == "info" else True,
)

@app.get("/")
async def get_status():
    return Response(status_code=status.HTTP_200_OK)


@app.get("/health")
async def get_health():
    return {"status": "healthy"}


@app.post("/test/local")
async def test_endpoint(request: Request):
    if not enable_test_endpoint:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoint is disabled."
        )
    
    body_bytes = await request.body()
    request_data = json.loads(body_bytes.decode('utf-8'))

    # Try to process the question and get responses
    try:
        output_text = await get_agent_responses(request_data.get('question'), True, True, project=project)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        output_text = f"Error: {str(e)}"
    return {"result": output_text}


# FastAPI route to handle Slack events
@app.post("/slack/events")
async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    # Retrieve headers manually
    headers = request.headers
    slack_signature = headers.get("x-slack-signature")
    slack_request_timestamp = headers.get("x-slack-request-timestamp")
    slack_retry_num = headers.get("x-slack-retry-num")
    slack_retry_reason = headers.get("x-slack-retry-reason")

    if slack_retry_num is not None:
        # This is a retry event, handle it accordingly (e.g., log it and skip processing)
        print(f"Slack Retry Event #{slack_retry_num}: {slack_retry_reason}")
        return {"status": "ok"}  # Return 200 OK to stop further retries

    # Verify the request signature
    await verify_slack_signature(request, slack_signature, slack_request_timestamp)

    body = await request.body()
    request_data = json.loads(body.decode('utf-8'))

    if request_data["type"] == "url_verification":
        return {"challenge": request_data["challenge"]}

    event = request_data["event"]
    if request_data["type"] == "event_callback" and "bot_id" not in event:
        if event["type"] == "app_mention":
            text = event["text"]
            channel = event["channel"]
            user = event["user"]
            thread_ts = event.get("ts")  # Extract the timestamp of the message

            # Parse the message text and extract the question or command
            question = text.replace(f"<@{slack_bot_id}>", "").strip()

            # Handle the event in the background
            background_tasks.add_task(process_slack_message, question, channel, thread_ts)

    return {"status": "ok"}  # Return 200 OK to stop further retries


def split_text(text, max_length=MAX_TEXT_LENGTH):
    """Split text into chunks no longer than max_length."""
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind("\n", 0, max_length)  # Try to split at the last newline within the limit
        if split_index == -1:  # If no newline is found, split at max_length
            split_index = max_length
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
    chunks.append(text)
    return chunks


async def run(question: str, detailed_analysis: bool, concise_response: bool, project: str):
    # Run
    inputs = {
        "question": question,
        "breakdown": detailed_analysis,
        "load_data": detailed_analysis,
        "concise": concise_response,
        "global_flag": detailed_analysis
    }
    config = {
        "recursion_limit": 50,
        "configurable": {
            "thread_id": "chicory-ui-discovery",
            "thread_ts": datetime.now(UTC).isoformat(),
            "client": "slack-api",
            "user": "slack-bot",
            "project": project,
        }
    }
    try:
        if detailed_analysis and chat_backend_app:
            async for event in chat_backend_app.astream(inputs, config=config):
                for key, value in event.items():
                    pprint(f"Node '{key}':")
            if 'generation' in value:
                return value["generation"]
            elif 'data_summary' in value:
                return value["data_summary"]
            else:
                return value
    except Exception as e:
        print(e)
        return f"Try again. {str(e)}"


# Function to verify Slack signature
async def verify_slack_signature(
        request: Request,
        slack_signature: str = Header(None),
        slack_request_timestamp: str = Header(None)
    ):
    if not slack_signature or not slack_request_timestamp:
        raise HTTPException(status_code=400, detail="Missing Slack signature or timestamp")

    # To prevent replay attacks, reject requests older than 5 minutes
    if abs(time.time() - int(slack_request_timestamp)) > 60 * 5:
        raise HTTPException(status_code=400, detail="Request is too old")

    request_body = await request.body()
    base_string = f"v0:{slack_request_timestamp}:{request_body.decode('utf-8')}"
    signature = 'v0=' + hmac.new(
        slack_signing_secret.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Verify that the request signature matches the calculated signature
    if not hmac.compare_digest(signature, slack_signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")


async def process_slack_message(question: str, channel: str, thread_ts: str):
    logger.info(f"Processing question: {question}")

    # Step 1: Send an initial "Thinking..." message and capture the timestamp
    try:
        response_thread_message = client.chat_postMessage(
            channel=channel,
            text="Thinking ... ☕️",
            thread_ts=thread_ts  # Reply in the thread
        )
        #TODO: Capture the ts (timestamp) of the "Thinking..." message
        response_thread_message_ts = response_thread_message["ts"]
    except SlackApiError as e:
        logger.error(f"Error sending initial message to Slack: {e.response['error']}")
        return

    # Step 2: Try to process the question and get responses
    try:
        output_text = await get_agent_responses(question, True, False, project=project)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        output_text = f"Error: {str(e)}"

    # Step 3: Split the output text into chunks
    text_chunks = split_text(output_text)

    # Step 4: Send response chunks and suggestions as a single message
    try:
        for i, chunk in enumerate(text_chunks):
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"{chunk}"}},
            ]
            if i == 0:
                client.chat_update(
                    channel=channel,
                    ts=response_thread_message_ts,  # Use the ts of the "Thinking..." message
                    blocks=blocks  # Use Block Kit formatting
                )
            else:
                client.chat_postMessage(
                    channel=channel,
                    blocks=blocks,  # Use Block Kit formatting
                    thread_ts=thread_ts  # Reply in the same thread
                )
    except SlackApiError as e:
        logger.error(f"Error sending messages in Slack: {e.response['error']}")


# Function to invoke the Langgraph workflow
async def get_agent_responses(question, detailed, concise, project):
    task_list = []
    task_list.append(run(question, detailed, concise, project))

    # Run both tasks concurrently
    run_response = await asyncio.gather(*task_list)
    return run_response [0]


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Inference Service...")
    home_path = os.getenv("HOME_PATH", "/app")
    data_path = os.getenv("BASE_DIR", os.path.join(home_path, "data"))

    # Ensure the data directory exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        logger.info(f"Created data directory at {data_path}")

    time.sleep(30)
    # Sync data from S3 if required
    if not os.listdir(data_path):
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            logger.info("Syncing data from S3...")
            sync_s3_from_bucket(data_path)
            if os.listdir(data_path):  # Check if directory is no longer empty
                logger.info("Data sync from S3 completed.")
                break
            retry_count += 1
            logger.warning(f"Retrying data sync from S3... Attempt {retry_count}/{max_retries}")
            time.sleep(30)
        else:
            # If all retries fail, raise an exception
            error_message = "Failed to sync data from S3 after multiple attempts."
            logger.error(error_message)
            sys.exit(1)

    # Start the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=log_level,
    )

    logger.info("Stopping Inference Service...")
