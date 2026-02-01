import io
import os
import pandas as pd
import io
import uuid
from fastapi import HTTPException, status
import logging
from .s3_utils import get_s3_client
from typing import List, Tuple, Dict, Any, Optional
from botocore.exceptions import ClientError
from fastapi import HTTPException, status, UploadFile
import logging

# Configure logging
logger = logging.getLogger(__name__)

async def process_csv_file(csv_file: UploadFile, project_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process uploaded CSV file following S3 upload pattern
    
    Args:
        csv_file: Uploaded CSV file
        project_id: ID of the project for S3 storage organization
        
    Returns:
        Tuple of (s3_metadata, test_cases)
    """
    # Validate file type
    if not csv_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Read file content
    content = await csv_file.read()
    
    # Validate file size (limit to 50MB like other uploads)
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 50MB limit")
    
    # Validate CSV content and get metadata
    try:
        csv_metadata = await validate_csv_content(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Parse test cases
    try:
        test_cases = await parse_csv_content(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Generate unique filename following S3 pattern
    original_filename = csv_file.filename.replace(' ', '_')
    unique_filename = f"{uuid.uuid4()}_{original_filename}"
    
    # Create S3 key following the pattern from data_sources
    s3_key = f"artifacts/{project_id}/evaluations/csv/{unique_filename}"
    
    # Upload to S3
    try:
        s3_result = await upload_file_to_s3(content, s3_key, 'text/csv')
        
        # Combine S3 result with CSV metadata
        s3_metadata = {
            **s3_result,
            "original_filename": original_filename,
            "file_size": len(content),
            **csv_metadata
        }
        
        return s3_metadata, test_cases
        
    except Exception as e:
        logger.error(f"Error uploading CSV to S3: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload CSV file: {str(e)}"
        )


async def upload_file_to_s3(file_data, s3_key, content_type=None):
    """Upload a file to S3"""
    s3_client, s3_bucket, s3_region = await get_s3_client()
    
    try:
        if isinstance(file_data, bytes):
            file_io = io.BytesIO(file_data)
        else:
            file_io = file_data
            
        file_io.seek(0)
        
        upload_args = {}
        if content_type:
            upload_args['ExtraArgs'] = {'ContentType': content_type}
        
        if 'ExtraArgs' in upload_args:
            s3_client.upload_fileobj(
                file_io,
                s3_bucket,
                s3_key,
                ExtraArgs=upload_args['ExtraArgs']
            )
        else:
            s3_client.upload_fileobj(
                file_io,
                s3_bucket,
                s3_key
            )
            
        s3_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
        
        return {
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "s3_url": s3_url
        }
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to S3: {str(e)}"
        )

async def parse_csv_content(csv_content: bytes) -> List[Dict[str, Any]]:
    """Parse CSV content and return list of test cases"""
    test_cases = []

    try:
        # Use pandas to parse CSV from bytes
        csv_io = io.BytesIO(csv_content)
        df = pd.read_csv(csv_io)

        # Validate required columns
        required_columns = ['task', 'expected_output']
        optional_columns = ['evaluation_guideline']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        # Convert DataFrame to test cases
        for index, row in df.iterrows():
            # Clean and validate data
            task = str(row['task']).strip() if pd.notna(row['task']) else ""
            expected_output = str(row['expected_output']).strip() if pd.notna(row['expected_output']) else ""
            evaluation_guideline = str(row['evaluation_guideline']).strip() if 'evaluation_guideline' in df.columns and pd.notna(row['evaluation_guideline']) else None

            if not task or not expected_output:
                raise ValueError(f"Row {index + 2}: task and expected_output are required and cannot be empty")  # +2 because pandas is 0-indexed and CSV has header

            # Create test case with metadata for any additional columns
            test_case = {
                "id": str(uuid.uuid4()),  # Generate unique ID for each test case
                "task": task,
                "expected_output": expected_output,
                "evaluation_guideline": evaluation_guideline,
                "metadata": {}
            }

            # Add any additional columns as metadata
            for col in df.columns:
                if col not in required_columns and col not in optional_columns and pd.notna(row[col]):
                    test_case["metadata"][col] = str(row[col]).strip()

            test_cases.append(test_case)

        if not test_cases:
            raise ValueError("CSV file contains no valid test cases")

        return test_cases

    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except pd.errors.ParserError as e:
        raise ValueError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error parsing CSV: {str(e)}")

async def validate_csv_content(file_content: bytes) -> Dict[str, Any]:
    """Validate CSV content and return metadata"""
    try:
        csv_io = io.BytesIO(file_content)
        df = pd.read_csv(csv_io)

        # Get basic info
        row_count = len(df)
        column_count = len(df.columns)
        columns = df.columns.tolist()

        # Validate required columns (evaluation_guideline is now optional)
        required_columns = ['task', 'expected_output']
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        logger.info(f"CSV validated: {row_count} rows, {column_count} columns")

        return {
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns,
            "file_size": len(file_content)
        }

    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except pd.errors.ParserError as e:
        raise ValueError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error validating CSV: {str(e)}")

async def generate_grader_prompt(criteria: str) -> str:
    """
    Generate LLM-as-Judge grader prompt from natural language criteria
    
    For now, this is a template-based approach. In the future, this could
    use Claude Code SDK to generate more sophisticated prompts.
    
    Args:
        criteria: Natural language evaluation criteria
        
    Returns:
        Structured grader prompt
    """
    grader_prompt = f"""You are an expert evaluator tasked with grading AI assistant responses.

**Evaluation Criteria:**
{criteria}

**Scoring Instructions:**
Rate the response on a scale from 0.0 to 1.0 based on how well it meets the criteria:

- **1.0**: Perfect response, meets all criteria excellently
- **0.8-0.9**: Very good response, minor issues only  
- **0.6-0.7**: Good response, meets most criteria
- **0.4-0.5**: Fair response, significant issues but partially helpful
- **0.2-0.3**: Poor response, major problems
- **0.0-0.1**: Completely wrong or unhelpful

**Important Guidelines:**
- Be objective and consistent in your evaluation
- Consider the specific evaluation guideline provided for each test case
- Focus on practical helpfulness to the user
- Explain your reasoning clearly

**Response Format:**
You must respond in valid JSON format:
{{
  "score": [number between 0.0 and 1.0],
  "reasoning": "[brief explanation of the score, highlighting what was good/bad]"
}}

Only return the JSON, no other text."""

    return grader_prompt

def validate_test_cases(test_cases: List[Dict[str, Any]]) -> List[str]:
    """
    Validate test cases and return list of validation errors

    Args:
        test_cases: List of test case dictionaries

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not test_cases:
        errors.append("At least one test case is required")
        return errors

    for i, test_case in enumerate(test_cases):
        case_num = i + 1

        # Check required fields
        required_fields = ['task', 'expected_output']
        for field in required_fields:
            if field not in test_case or not test_case[field] or not test_case[field].strip():
                errors.append(f"Test case {case_num}: {field} is required and cannot be empty")

        # Check field lengths
        if 'task' in test_case and len(test_case['task']) > 1000:
            errors.append(f"Test case {case_num}: task is too long (max 1000 characters)")

        if 'expected_output' in test_case and len(test_case['expected_output']) > 2000:
            errors.append(f"Test case {case_num}: expected_output is too long (max 2000 characters)")

        # evaluation_guideline is optional, but validate length if provided
        if 'evaluation_guideline' in test_case and test_case['evaluation_guideline'] and len(test_case['evaluation_guideline']) > 500:
            errors.append(f"Test case {case_num}: evaluation_guideline is too long (max 500 characters)")

    return errors

async def get_grading_agent_id() -> Optional[str]:
    """Get the grading agent ID from environment variable"""
    return os.getenv("GRADING_AGENT_ID")

def get_grading_agent_project_id() -> Optional[str]:
    """Get the grading agent project ID from environment variable"""
    return os.getenv("GRADING_AGENT_PROJECT_ID")
