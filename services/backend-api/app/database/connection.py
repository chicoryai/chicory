import os
import logging
import ssl
import re
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.project import Project
from app.models.data_source import DataSource
from app.models.agent import Agent
from app.models.tasks import Task
from app.models.training import Training
from app.models.tool import Tool
from app.models.evaluation import Evaluation, EvaluationRun
from app.models.mcp_gateway import MCPGateway, MCPTool
from app.models.playground import Playground, PlaygroundInvocation
from app.models.workzone import Workzone, WorkzoneInvocation
from app.models.env_variable import EnvVariable
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.folder_upload import FolderUpload

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None

db = Database()

def is_documentdb_uri(uri: str) -> bool:
    """Detect if the MongoDB URI is pointing to AWS DocumentDB"""
    documentdb_patterns = [
        r'\.docdb\.', # Official DocumentDB domain
        r'amazonaws\.com',  # Any AWS hostname
        r'tlsCAFile='  # DocumentDB typically requires TLS
    ]
    
    return any(re.search(pattern, uri) for pattern in documentdb_patterns)

def parse_mongo_uri(uri: str) -> Tuple[str, Dict[str, Any]]:
    """Parse a MongoDB URI and return the database name and connection options"""
    # Default database name and connection options
    db_name = 'project_management'
    is_docdb = is_documentdb_uri(uri)
    
    # Extract database name from URI
    try:
        parsed_uri = urlparse(uri)
        path = parsed_uri.path.strip('/')
        if path:
            db_name = path
    except Exception as e:
        logger.warning(f"Failed to parse database name from URI: {e}")
    
    # Extract TLS CA file path if provided
    tls_ca_file = None
    query_params = {}
    
    if '?' in uri:
        try:
            query_string = uri.split('?', 1)[1]
            pairs = query_string.split('&')
            
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    query_params[key] = value
                    
            if 'tlsCAFile' in query_params:
                tls_ca_file = query_params['tlsCAFile']
        except Exception as e:
            logger.warning(f"Failed to parse query parameters from URI: {e}")
    
    # Build connection options
    if is_docdb:
        # DocumentDB connection options
        client_kwargs = {
            'serverSelectionTimeoutMS': 30000,  # 30 seconds
            'connectTimeoutMS': 30000,  # 30 seconds
            'socketTimeoutMS': 30000,  # 30 seconds
            'retryWrites': False,  # DocumentDB doesn't support retryWrites
            'ssl': True if tls_ca_file or 'tls=true' in uri.lower() or 'ssl=true' in uri.lower() else False,
            'readPreference': 'primary'  # Always read from primary to avoid replica lag
        }
        
        # Add TLS CA file if specified
        if tls_ca_file:
            client_kwargs['tlsCAFile'] = tls_ca_file
            # Confirm the CA file exists
            if not os.path.exists(tls_ca_file):
                logger.warning(f"TLS CA file does not exist: {tls_ca_file}")
    else:
        # Local MongoDB connection options
        client_kwargs = {
            'serverSelectionTimeoutMS': 5000,  # 5 seconds is enough for local
            'connectTimeoutMS': 5000,
            'retryWrites': True,  # Local MongoDB supports retry writes
            'readPreference': 'primary'  # Consistent reads from primary
        }
    
    return db_name, client_kwargs

async def connect_to_mongo():
    """Connect to MongoDB or DocumentDB instance based on connection URI"""
    try:
        # Get connection details from environment variables
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/project_management")
        
        # Determine if we're connecting to DocumentDB or local MongoDB
        is_docdb = is_documentdb_uri(mongo_uri)
        connection_type = "AWS DocumentDB" if is_docdb else "Local MongoDB"
        logger.info(f"Detected connection type: {connection_type}")
        
        # Parse the MongoDB URI
        db_name, client_kwargs = parse_mongo_uri(mongo_uri)
        
        # Create client with appropriate options
        # Mask credentials in log
        if '@' in mongo_uri:
            masked_uri = f"{mongo_uri.split('@')[0].split('://')[0]}://*****@{mongo_uri.split('@')[1]}"
        else:
            masked_uri = mongo_uri
        logger.info(f"Connecting to {connection_type} with URI: {masked_uri}")
        logger.info(f"Read preference set to: {client_kwargs.get('readPreference', 'default')}")

        # Configure SSL options based on URI parameters
        # Check if SSL/TLS is explicitly disabled in the URI
        uri_lower = mongo_uri.lower()
        tls_disabled = 'tls=false' in uri_lower or 'ssl=false' in uri_lower
        
        if tls_disabled:
            # SSL/TLS explicitly disabled in URI - don't add conflicting SSL options
            logger.info("SSL/TLS disabled via URI parameters - using connection string settings")
        else:
            # DocumentDB requires SSL/TLS
            client_kwargs['ssl'] = True  # Enable SSL/TLS
            client_kwargs['tlsAllowInvalidCertificates'] = True  # Equivalent to CERT_NONE
            logger.info("SSL/TLS enabled for DocumentDB connection")

        # Create the database client
        db.client = AsyncIOMotorClient(mongo_uri, **client_kwargs)
        
        logger.info(f"Using database: {db_name}")
        
        # Initialize Beanie with the document models
        await init_beanie(
            database=db.client.get_database(db_name),
            document_models=[
                Project,
                DataSource,
                Agent,
                Task,
                Training,
                Tool,
                Evaluation,
                EvaluationRun,
                MCPGateway,
                MCPTool,
                Playground,
                PlaygroundInvocation,
                Workzone,
                WorkzoneInvocation,
                EnvVariable,
                Conversation,
                Message,
                FolderUpload
            ]
        )
        
        # Test the connection
        await db.client.admin.command('ismaster')
        logger.info(f"Successfully connected to {connection_type}")
    except Exception as e:
        logger.error(f"Could not connect to database: {e}")
        raise

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("Closed MongoDB connection")

async def get_database():
    """Get database instance"""
    if not db.client:
        logger.warning("Database client not initialized. Attempting to connect...")
        await connect_to_mongo()
    
    # Get connection details from environment variables
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/project_management")
    
    # Parse the MongoDB URI to get the database name
    db_name, _ = parse_mongo_uri(mongo_uri)
            
    return db.client.get_database(db_name)
