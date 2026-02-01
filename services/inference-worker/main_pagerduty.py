import json
import hashlib
import hmac
import logging
import os
import sys
import time
import base64
from datetime import datetime, UTC, timedelta

from services.integration.s3_sync import sync_s3_from_bucket
from services.utils.config import load_default_envs
from services.workflows.data_exploration.pipeline_debugging.mezmo_pipeline_v1 import initialize_memzo_api_workflow_agent as agent_v1
from services.workflows.data_exploration.pipeline_debugging.mezmo_pipeline_v2 import initialize_memzo_api_workflow_agent as agent_v2
from services.integration.phoenix import initialize_phoenix

# Load default envs
load_default_envs()

from fastapi import HTTPException, Response, status, BackgroundTasks
from pprint import pprint
from fastapi import FastAPI, Request
import requests

log_level = os.getenv("LOG_LEVEL", "INFO").lower()
logging.basicConfig(level=logging.INFO if log_level == "info" else logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize PagerDuty credentials
CLIENT_ID = os.getenv('PAGERDUTY_CLIENT_ID')
CLIENT_SECRET = os.getenv('PAGERDUTY_CLIENT_SECRET')
OAUTH_SCOPE = os.getenv('PAGERDUTY_OAUTH_SCOPE')
WEBHOOK_SECRET = os.getenv('PAGERDUTY_WEBHOOK_SECRET')
FROM_EMAIL = os.getenv("PAGERDUTY_EMAIL")

# We'll store the token and expiration in memory for simplicity
OAUTH_TOKEN = None
OAUTH_TOKEN_EXPIRY = datetime.min

project = os.getenv("PROJECT")

# Initialize Phoenix tracing
initialize_phoenix()

# Initialize Chicory Agent Workflow Client
chat_backend_app_v1 = agent_v1("pagerduty_bot", project)
chat_backend_app_v2 = agent_v2("pagerduty_bot", project)
MAX_TEXT_LENGTH = 3000  # Maximum character limit for a single block of text

# Define the FastAPI application
app = FastAPI(
    title="BrewMind Hub PagerDuty Integration",
    description="Chicory AI Autopilot Data Engineer for PagerDuty",
    debug=False if log_level == "info" else True,
)


@app.get("/")
async def get_status():
    return Response(status_code=status.HTTP_200_OK)


@app.get("/health")
async def get_health():
    return {"status": "healthy"}


@app.post("/dev/eda")
async def test_endpoint(request: Request):
    enable_test_endpoint = os.getenv("ENABLE_TEST_ENDPOINT", "false").lower() == "true"
    if not enable_test_endpoint:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoint is disabled."
        )
    
    body_bytes = await request.body()
    request_data = json.loads(body_bytes.decode('utf-8'))

    # Try to process the question and get responses
    try:
        pipeline_id = request_data.get('pipeline_id')
        if not pipeline_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test endpoint is disabled."
            )
        agent_version = request_data.get('agent_version')
        if not agent_version:
            agent_version = "v1"
        metadata = [agent_version]
        question = f"""Investigate the pipeline with ID: {pipeline_id}, for potential optimization opportunities.

Important Instructions:
* Data type is Directed Acyclic Graph and analyze all available execution paths accordingly.
* Assume full access to all necessary APIs. Use the runbook to understand the pipeline structure and retrieve any missing details. 
* If any required data is not directly available, consult the contextual information to identify the appropriate retrieval steps.
* Assume exploration and subsequent steps are pre-approved, with all the validation already available.
* Alongside optimization suggestions, include relevant implications and trade-offs to aid decision-making.

Response Format:
* Pipeline Title
* Transform Breakdown
* Usage and Health Metrics Analysis
* Identified Inefficiencies
* Optimization Summary
	* Be as detailed as possible
	* Include examples from your analysis
	* Provide as many fixes as you can come up with
	* try to salvage intent before suggesting components removal
* Implications & Trade-offs
"""
        output_text = await get_agent_responses(question, metadata, project=project)
        logger.info(f"Response: {output_text}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        output_text = f"Error: {str(e)}"
    return {"result": output_text}

def verify_pd_signature(request_obj, secret):
    """
    Verify PagerDuty's HMAC signature if a secret was configured in PagerDuty.
    
    Following the PagerDuty documentation for webhook signature verification.
    """
    # Extract the signature header
    signature_header = request_obj.headers.get("X-PagerDuty-Signature")
    if not signature_header:
        logger.warning("No X-PagerDuty-Signature header found")
        return False
    
    # Get the raw request body
    try:
        raw_body = request_obj.body
    except Exception as e:
        logger.error(f"Error accessing request body: {str(e)}")
        return False
    
    # Split the signatures (PagerDuty may send multiple signatures)
    signatures = signature_header.split(',')
    
    # For each signature
    for signature in signatures:
        # Compute our own signature
        computed_signature = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                msg=raw_body,  # raw request body
                digestmod=hashlib.sha256
            ).digest()
        ).decode()
        
        # Compare signatures using constant-time comparison
        if hmac.compare_digest(signature.strip(), computed_signature):
            logger.info("PagerDuty webhook signature verified successfully")
            return True
    
    logger.warning("PagerDuty webhook signature verification failed")
    return False

# Function to obtain (or refresh) PagerDuty OAuth Token
def get_pagerduty_oauth_token():
    """
    Retrieve a PagerDuty OAuth 2.0 token using the client_credentials grant type.
    Caches the token in memory until it expires.
    """
    global OAUTH_TOKEN, OAUTH_TOKEN_EXPIRY

    # If we already have a token that hasn't expired, return it
    if OAUTH_TOKEN and datetime.now() < OAUTH_TOKEN_EXPIRY:
        return OAUTH_TOKEN

    url = "https://identity.pagerduty.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": OAUTH_SCOPE
    }

    logger.info("Requesting new PagerDuty OAuth token...")
    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()

    token_json = response.json()
    OAUTH_TOKEN = token_json.get("access_token")
    expires_in = token_json.get("expires_in", 3600)  # default 1 hour if not provided

    # Mark expiry time
    OAUTH_TOKEN_EXPIRY = datetime.now() + timedelta(seconds=expires_in - 30)
    # (subtract 30s to refresh slightly early)
    logger.info(f"Successfully obtained new token. Expires in {expires_in} seconds.")
    return OAUTH_TOKEN


# Function to get incident details from PagerDuty API
async def get_incident_details(incident_id):
    """
    Retrieve detailed information about a PagerDuty incident using its ID.
    """
    token = get_pagerduty_oauth_token()  # Ensure we have a valid OAuth token
    
    # API endpoint for getting incident details
    incident_url = f"https://api.pagerduty.com/incidents/{incident_id}?include[]=body"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
        "From": FROM_EMAIL,
    }
    
    try:
        response = requests.get(incident_url, headers=headers)
        response.raise_for_status()
        incident_data = response.json()
        logger.info(f"Successfully retrieved details for incident {incident_id}")
        return incident_data
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error retrieving incident {incident_id} details: {e}")
        raise e

# Function to update incident with analysis results
async def update_incident(incident_id, analysis_text):
    """
    Update a PagerDuty incident with analysis results.
    """
    token = get_pagerduty_oauth_token()  # Ensure we have a valid OAuth token
    
    # Add a note to the incident with our analysis
    notes_url = f"https://api.pagerduty.com/incidents/{incident_id}/notes"
    # Get email from environment variable with a default fallback

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
        "From": FROM_EMAIL,
    }

    note_data = {
        "note": {
            "content": analysis_text
        }
    }
    try:
        response = requests.post(notes_url, headers=headers, json=note_data)
        response.raise_for_status()
        logger.info(f"Added analysis note to incident {incident_id}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error adding note to incident {incident_id}: {e}")

# FastAPI route to handle PagerDuty webhooks
@app.post("/pagerduty-webhook")
async def pagerduty_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint to receive PagerDuty events and process incidents.
    """
    logger.info("Received PagerDuty webhook request:")
    logger.info(request)
    payload = await request.json()
    if not payload:
        return {"error": "No JSON payload"}, 400

    # Verify webhook signature if a secret is configured
    # if WEBHOOK_SECRET:
    #     if not verify_pd_signature(request, WEBHOOK_SECRET):
    #         logger.error("Invalid signature from PagerDuty.")
    #         return {"error": "Invalid signature"}, 403

    logger.info("Received PagerDuty webhook payload:")
    logger.info(payload)

    # Extract event information
    event_info = payload.get("event", {})
    event_type = event_info.get("event_type", "")
    data_obj = event_info.get("data", {})

    incident_id = data_obj.get("id", "")
    incident_title = data_obj.get("title", "")
    incident_status = data_obj.get("status", "")
    incident_description = data_obj.get("description", "")

    logger.info(f"Event Type: {event_type}")
    logger.info(f"Incident ID: {incident_id}, Title: {incident_title}, Status: {incident_status}")

    # Only process triggered incidents
    if incident_status == "triggered" and incident_id:
        # Process the incident in the background
        background_tasks.add_task(
            process_pagerduty_incident, 
            incident_id, 
            incident_title, 
            data_obj
        )

    # Return a 200 OK so PagerDuty doesn't retry
    return {"status": "ok"}


# Function to process PagerDuty incidents
async def process_pagerduty_incident(incident_id: str, incident_title: str, data_obj: dict):
    logger.info(f"Processing incident: {incident_title} (ID: {incident_id})")
    
    # Get detailed incident information from PagerDuty API
    try:
        incident_details = await get_incident_details(incident_id)
        
        # Extract additional information from the API response
        incident_data = incident_details.get('incident', {})
        
        # Get important fields from the incident
        urgency = incident_data.get('urgency', 'unknown')
        status = incident_data.get('status', 'unknown')
        created_at = incident_data.get('created_at', 'unknown')
        service = incident_data.get('service', {}).get('summary', 'unknown')
        alert_body = incident_data.get('body', 'unknown')
        
        logger.info(f"Retrieved additional details for incident {incident_id}: urgency={urgency}, status={status}")
        
        # Convert data_obj to a JSON string for better readability
        data_json = json.dumps(data_obj, indent=2)
        
        # Convert incident_details to a JSON string for better readability
        incident_details_json = json.dumps(incident_details, indent=2)
        
        # Extract relevant metadata from the incident with additional API details
        metadata = [
            f"Incident ID: {incident_id}",
            f"Urgency: {urgency}",
            f"Created At: {created_at}",
            f"Service: {service}",
            f"Incident Details: \n{alert_body}"
        ]
    except Exception as e:
        logger.warning(f"Failed to get additional incident details: {str(e)}. Using basic information only.")
        
        # Convert data_obj to a JSON string for better readability
        data_json = json.dumps(data_obj, indent=2)
        
        # Extract relevant metadata from the incident (fallback to basic info)
        metadata = [
            f"Incident ID: {incident_id}",
            f"Detail: {data_json}"
        ]
    
    # Construct a question that summarizes the incident
    question = f"Analyze this PagerDuty incident: {incident_title}. Provide root cause analysis and recommended actions."
    
    # Get analysis
    try:
        analysis_text = await get_agent_responses(question, metadata, project=project)
        logger.info(f"Analysis generated for incident {incident_id}")
        
        # Update the incident with our analysis
        await update_incident(incident_id, analysis_text)
    except Exception as e:
        error_message = f"Error analyzing incident {incident_id}: {str(e)}"
        logger.error(error_message)
        # Try to update the incident with the error message
        try:
            await update_incident(incident_id, f"Error during analysis: {str(e)}")
        except Exception as update_error:
            logger.error(f"Failed to update incident with error message: {str(update_error)}")


# Function to run the analysis workflow
async def run(question: str, metadata: list, project: str):
    # Create a combined input with the question and incident metadata
    # Format the metadata as part of the question for better context
    if metadata[0] == "v1":
        chat_backend_app = chat_backend_app_v1
    elif metadata[0] == "v2":
        chat_backend_app = chat_backend_app_v2
    else:
        metadata_text = '\n'.join(metadata)
        chat_backend_app = chat_backend_app_v1
        question = f"{question}\n\n{metadata_text}",
    
    # Run
    inputs = {
        "question": question,
        "user_hints": """
Hints:
pipeline base url, env: PIPELINE_API_ENDPOINT
x-control-token, env: CONTROL_TOKEN
x-auth-subject-email, env: SUBJECT_EMAIL
x-auth-account-id, fetch: log_analysis_id
"""
    }
    config = {
        "recursion_limit": 30,
        "handle_parsing_errors": True,
        "configurable": {
            "thread_id": "chicory-api-action",
            "thread_ts": datetime.now(UTC).isoformat(),
            "client": "pagerduty-api",
            "user": "pagerduty-bot",
            "project": project,
        }
    }
    
    full_response = ""
    output_text = ""
    
    try:
        if chat_backend_app:
            async for event in chat_backend_app.astream(inputs, config=config):
                for key, value in event.items():
                    # Handle final response
                    if value and 'response' in value:
                        output_text = str(value["response"])
                        full_response += f"\n\n{output_text}"
                        logger.info(f"Incident Analysis: {output_text}")
                        return output_text
            
            # If we get here without returning, use the full response
            if full_response:
                return full_response
            return "Analysis completed but no specific response was generated."
        else:
            return "App still initializing..."
    except Exception as e:
        error_msg = f"Analysis error: {str(e)}"
        logger.error(error_msg)
        return error_msg

# Function to invoke the Langgraph workflow
async def get_agent_responses(incident, metadata, project):
    # Just run the analysis without separate suggestions
    response = await run(incident, metadata, project)
    return response


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting PagerDuty Integration Service...")
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

    logger.info("Stopping PagerDuty Integration Service...")
