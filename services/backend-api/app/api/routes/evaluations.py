from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Header, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime

from app.models.evaluation import (
    Evaluation, EvaluationCreate, EvaluationUpdate, EvaluationResponse, EvaluationList,
    TestCaseCreate, TestCaseUpdate, TestCaseResponse, TestCaseList, TestCaseBulkCreate,
    EvaluationRun, EvaluationRunCreate, EvaluationRunResponse, EvaluationRunList,
    EvaluationRunStatus, TestCaseRunStatus, TestCaseResult
)
from app.models.agent import Agent
from app.utils.evaluation_utils import (
    process_csv_file, get_grading_agent_id, get_grading_agent_project_id, validate_test_cases
)
from app.utils.evaluation_orchestration import start_evaluation_orchestration

router = APIRouter()

@router.post("/projects/{project_id}/agents/{agent_id}/evaluations", response_model=EvaluationResponse, status_code=201)
async def create_evaluation(
    project_id: str,
    agent_id: str,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    criteria: str = Form(...),
    csv_file: UploadFile = File(...)
):
    """Create a new evaluation with CSV upload"""
    
    # Validate that the agent exists and belongs to the project
    target_agent = await Agent.get(agent_id)
    if not target_agent or target_agent.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id} not found in project {project_id}"
        )

    # Process CSV file using S3 upload pattern
    try:
        s3_metadata, test_cases = await process_csv_file(csv_file, project_id)
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV file: {str(e)}")
    
    # Create evaluation
    evaluation = Evaluation(
        project_id=project_id,
        target_agent_id=agent_id,
        name=name,
        description=description,
        owner="system",  # TODO: Get from authentication
        s3_bucket=s3_metadata["s3_bucket"],
        s3_key=s3_metadata["s3_key"],
        s3_url=s3_metadata["s3_url"],
        original_filename=s3_metadata["original_filename"],
        file_size=s3_metadata["file_size"],
        criteria=criteria,
        test_cases=test_cases,
        test_case_count=len(test_cases),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    await evaluation.create()
    
    # Return response
    return EvaluationResponse(
        id=evaluation.id,
        project_id=evaluation.project_id,
        target_agent_id=evaluation.target_agent_id,
        name=evaluation.name,
        description=evaluation.description,
        owner=evaluation.owner,
        s3_bucket=evaluation.s3_bucket,
        s3_key=evaluation.s3_key,
        s3_url=evaluation.s3_url,
        original_filename=evaluation.original_filename,
        file_size=evaluation.file_size,
        criteria=evaluation.criteria,
        test_case_count=evaluation.test_case_count,
        created_at=evaluation.created_at.isoformat(),
        updated_at=evaluation.updated_at.isoformat()
    )

@router.get("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    project_id: str,
    agent_id: str,
    evaluation_id: str
):
    """Get evaluation by ID"""
    
    evaluation = await Evaluation.find_one({"_id": evaluation_id, "project_id": project_id})
    if not evaluation:
        raise HTTPException(
            status_code=404, 
            detail=f"Evaluation {evaluation_id} not found in project {project_id}"
        )
    
    return EvaluationResponse(
        id=evaluation.id,
        project_id=evaluation.project_id,
        target_agent_id=evaluation.target_agent_id,
        name=evaluation.name,
        description=evaluation.description,
        owner=evaluation.owner,
        s3_bucket=evaluation.s3_bucket,
        s3_key=evaluation.s3_key,
        s3_url=evaluation.s3_url,
        original_filename=evaluation.original_filename,
        file_size=evaluation.file_size,
        criteria=evaluation.criteria,
        test_case_count=evaluation.test_case_count,
        created_at=evaluation.created_at.isoformat(),
        updated_at=evaluation.updated_at.isoformat()
    )

@router.put("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def update_evaluation(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    evaluation_data: EvaluationUpdate
):
    """Update evaluation information"""
    
    evaluation = await Evaluation.find_one({"_id": evaluation_id, "project_id": project_id})
    if not evaluation:
        raise HTTPException(
            status_code=404, 
            detail=f"Evaluation {evaluation_id} not found in project {project_id}"
        )
    
    # Validate target agent if being updated
    if evaluation_data.target_agent_id is not None:
        target_agent = await Agent.get(evaluation_data.target_agent_id)
        if not target_agent or target_agent.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"Target agent {evaluation_data.target_agent_id} not found in project {project_id}"
            )
    
    # Update only provided fields
    update_data = {}
    
    if evaluation_data.target_agent_id is not None:
        update_data["target_agent_id"] = evaluation_data.target_agent_id
    if evaluation_data.name is not None:
        update_data["name"] = evaluation_data.name
    if evaluation_data.description is not None:
        update_data["description"] = evaluation_data.description
    if evaluation_data.criteria is not None:
        update_data["criteria"] = evaluation_data.criteria
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await evaluation.update({"$set": update_data})
        
        # Refresh evaluation from database
        evaluation = await Evaluation.find_one({"_id": evaluation_id, "project_id": project_id, "target_agent_id": agent_id})
    
    return EvaluationResponse(
        id=evaluation.id,
        project_id=evaluation.project_id,
        target_agent_id=evaluation.target_agent_id,
        name=evaluation.name,
        description=evaluation.description,
        owner=evaluation.owner,
        s3_bucket=evaluation.s3_bucket,
        s3_key=evaluation.s3_key,
        s3_url=evaluation.s3_url,
        original_filename=evaluation.original_filename,
        file_size=evaluation.file_size,
        criteria=evaluation.criteria,
        test_case_count=evaluation.test_case_count,
        created_at=evaluation.created_at.isoformat(),
        updated_at=evaluation.updated_at.isoformat()
    )

@router.delete("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}", response_model=Dict[str, str])
async def delete_evaluation(
    project_id: str,
    agent_id: str,
    evaluation_id: str
):
    """Delete evaluation"""
    
    evaluation = await Evaluation.find_one({"_id": evaluation_id, "project_id": project_id})
    if not evaluation:
        raise HTTPException(
            status_code=404, 
            detail=f"Evaluation {evaluation_id} not found in project {project_id}"
        )
    
    # TODO: Clean up S3 files if needed
    # Could implement S3 cleanup here using evaluation.s3_bucket and evaluation.s3_key
    
    await evaluation.delete()
    
    return {"message": "Evaluation deleted successfully"}

@router.get("/projects/{project_id}/agents/{agent_id}/evaluations", response_model=EvaluationList)
async def list_evaluations(
    project_id: str,
    agent_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of evaluations to return"),
    offset: int = Query(0, ge=0, description="Number of evaluations to skip")
):
    """List evaluations for an agent"""
    
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(
            status_code=404, 
            detail=f"Agent {agent_id} not found in project {project_id}"
        )
    
    # Build query
    query = {"project_id": project_id, "target_agent_id": agent_id}
    
    # Get evaluations with pagination
    evaluations = await Evaluation.find(query).skip(offset).limit(limit + 1).to_list()
    
    # Check if there are more results
    has_more = len(evaluations) > limit
    if has_more:
        evaluations = evaluations[:-1]  # Remove extra item
    
    # Convert to response format
    evaluation_responses = []
    for evaluation in evaluations:
        evaluation_responses.append(EvaluationResponse(
            id=str(evaluation.id),
            project_id=evaluation.project_id,
            target_agent_id=evaluation.target_agent_id,
            name=evaluation.name,
            description=evaluation.description,
            owner=evaluation.owner,
            s3_bucket=evaluation.s3_bucket,
            s3_key=evaluation.s3_key,
            s3_url=evaluation.s3_url,
            original_filename=evaluation.original_filename,
            file_size=evaluation.file_size,
            criteria=evaluation.criteria,
            test_case_count=evaluation.test_case_count,
            created_at=evaluation.created_at.isoformat(),
            updated_at=evaluation.updated_at.isoformat()
        ))
    
    return EvaluationList(evaluations=evaluation_responses, has_more=has_more)

@router.get("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/test-cases", response_model=TestCaseList)
async def get_test_cases(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get test cases for an evaluation"""
    
    evaluation = await Evaluation.get(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    if evaluation.project_id != project_id or evaluation.target_agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Evaluation does not belong to the specified project/agent")
    
    # Apply pagination to test cases
    test_cases = evaluation.test_cases[offset:offset + limit]
    
    # Convert to response format
    test_case_responses = []
    for test_case in test_cases:
        test_case_responses.append(TestCaseResponse(
            id=test_case.get("id", "unknown"),
            task=test_case["task"],
            expected_output=test_case["expected_output"],
            evaluation_guideline=test_case["evaluation_guideline"],
            metadata=test_case.get("metadata", {})
        ))
    
    return TestCaseList(
        test_cases=test_case_responses,
        total_count=len(evaluation.test_cases)
    )

@router.patch("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/test-cases/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    test_case_id: str,
    test_case_data: TestCaseUpdate
):
    """Update a specific test case"""
    
    evaluation = await Evaluation.get(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    if evaluation.project_id != project_id or evaluation.target_agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Evaluation does not belong to the specified project/agent")
    
    # Find test case
    test_case_index = None
    for i, test_case in enumerate(evaluation.test_cases):
        if test_case.get("id") == test_case_id:
            test_case_index = i
            break
    
    if test_case_index is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    # Update test case
    test_case = evaluation.test_cases[test_case_index]
    
    if test_case_data.task is not None:
        test_case["task"] = test_case_data.task
    if test_case_data.expected_output is not None:
        test_case["expected_output"] = test_case_data.expected_output
    if test_case_data.evaluation_guideline is not None:
        test_case["evaluation_guideline"] = test_case_data.evaluation_guideline
    if test_case_data.metadata is not None:
        test_case["metadata"] = test_case_data.metadata
    
    # Validate updated test cases
    validation_errors = validate_test_cases(evaluation.test_cases)
    if validation_errors:
        raise HTTPException(status_code=400, detail=f"Test case validation failed: {'; '.join(validation_errors)}")
    
    # Update CSV file
    try:
        new_file_path = await update_csv_file(evaluation_id, evaluation.test_cases)
        evaluation.csv_file_path = new_file_path
    except Exception as e:
        print(f"Warning: Failed to update CSV file: {e}")
    
    # Save evaluation
    evaluation.updated_at = datetime.utcnow()
    await evaluation.save()
    
    return TestCaseResponse(
        id=test_case["id"],
        task=test_case["task"],
        expected_output=test_case["expected_output"],
        evaluation_guideline=test_case["evaluation_guideline"],
        metadata=test_case.get("metadata", {})
    )

@router.post("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/test-cases", response_model=TestCaseList, status_code=201)
async def add_test_cases(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    test_case_data: TestCaseBulkCreate
):
    """Add one or more test cases to evaluation"""

    evaluation = await Evaluation.get(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    if evaluation.project_id != project_id or evaluation.target_agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Evaluation does not belong to the specified project/agent")

    # Create new test cases
    import uuid
    new_test_cases = []
    for test_case in test_case_data.test_cases:
        new_test_case = {
            "id": f"tc-{str(uuid.uuid4())[:8]}",
            "task": test_case.task,
            "expected_output": test_case.expected_output,
            "evaluation_guideline": test_case.evaluation_guideline,
            "metadata": test_case.metadata or {}
        }
        new_test_cases.append(new_test_case)

    # Add to evaluation
    evaluation.test_cases.extend(new_test_cases)
    evaluation.test_case_count = len(evaluation.test_cases)

    # Validate test cases
    validation_errors = validate_test_cases(evaluation.test_cases)
    if validation_errors:
        raise HTTPException(status_code=400, detail=f"Test case validation failed: {'; '.join(validation_errors)}")

    # Update CSV file
    try:
        new_file_path = await update_csv_file(evaluation_id, evaluation.test_cases)
        evaluation.csv_file_path = new_file_path
    except Exception as e:
        print(f"Warning: Failed to update CSV file: {e}")

    # Save evaluation
    evaluation.updated_at = datetime.utcnow()
    await evaluation.save()

    # Return list of created test cases
    test_case_responses = []
    for test_case in new_test_cases:
        test_case_responses.append(TestCaseResponse(
            id=test_case["id"],
            task=test_case["task"],
            expected_output=test_case["expected_output"],
            evaluation_guideline=test_case["evaluation_guideline"],
            metadata=test_case.get("metadata", {})
        ))

    return TestCaseList(
        test_cases=test_case_responses,
        total_count=evaluation.test_case_count
    )

@router.delete("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/test-cases/{test_case_id}", response_model=Dict[str, str])
async def delete_test_case(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    test_case_id: str
):
    """Delete a test case"""
    
    evaluation = await Evaluation.get(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    if evaluation.project_id != project_id or evaluation.target_agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Evaluation does not belong to the specified project/agent")
    
    # Find and remove test case
    test_case_index = None
    for i, test_case in enumerate(evaluation.test_cases):
        if test_case.get("id") == test_case_id:
            test_case_index = i
            break
    
    if test_case_index is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    # Remove test case
    evaluation.test_cases.pop(test_case_index)
    evaluation.test_case_count = len(evaluation.test_cases)
    
    # Update CSV file
    try:
        new_file_path = await update_csv_file(evaluation_id, evaluation.test_cases)
        evaluation.csv_file_path = new_file_path
    except Exception as e:
        print(f"Warning: Failed to update CSV file: {e}")
    
    # Save evaluation
    evaluation.updated_at = datetime.utcnow()
    await evaluation.save()
    
    return {"message": "Test case deleted successfully"}

# Phase 2: Evaluation Run Endpoints

@router.post("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/runs", response_model=EvaluationRunResponse, status_code=201)
async def run_evaluation(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    run_data: EvaluationRunCreate,
    background_tasks: BackgroundTasks
):
    """Start running an evaluation"""
    
    # Verify evaluation exists and belongs to the specified project/agent
    evaluation = await Evaluation.find_one({
        "_id": evaluation_id, 
        "project_id": project_id, 
        "target_agent_id": agent_id
    })
    if not evaluation:
        raise HTTPException(
            status_code=404, 
            detail=f"Evaluation {evaluation_id} not found for agent {agent_id} in project {project_id}"
        )
    
    # Get grading agent configuration from environment variables
    grading_agent_id = await get_grading_agent_id()
    grading_agent_project_id = get_grading_agent_project_id()
    
    if not grading_agent_id:
        raise HTTPException(
            status_code=500,
            detail="Grading agent not configured. Please set GRADING_AGENT_ID environment variable."
        )
    
    if not grading_agent_project_id:
        raise HTTPException(
            status_code=500,
            detail="Grading agent project not configured. Please set GRADING_AGENT_PROJECT_ID environment variable."
        )
    
    # Validate that grading agent exists in the specified project
    grading_agent = await Agent.get(grading_agent_id)
    if not grading_agent or grading_agent.project_id != grading_agent_project_id:
        raise HTTPException(
            status_code=500,
            detail=f"Configured grading agent {grading_agent_id} not found in project {grading_agent_project_id}"
        )
    
    # Initialize test case results
    test_case_results = []
    for test_case in evaluation.test_cases:
        test_case_results.append({
            "test_case_id": test_case.get("id", "unknown"),
            "status": TestCaseRunStatus.PENDING.value,
            "target_task_id": None,
            "grader_task_id": None,
            "target_response": None,
            "grader_response": None,
            "score": None,
            "error_message": None,
            "started_at": None,
            "completed_at": None
        })
    
    # Create evaluation run
    evaluation_run = EvaluationRun(
        evaluation_id=evaluation_id,
        project_id=project_id,
        target_agent_id=agent_id,
        grading_agent_id=grading_agent_id,
        grading_agent_project_id=grading_agent_project_id,
        status=EvaluationRunStatus.QUEUED,
        test_case_results=test_case_results,
        total_test_cases=len(evaluation.test_cases),
        completed_test_cases=0,
        failed_test_cases=0,
        overall_score=None,
        started_at=datetime.utcnow()
    )
    
    await evaluation_run.save()
    
    # Start background orchestration for evaluation execution
    background_tasks.add_task(start_evaluation_orchestration, str(evaluation_run.id))
    
    # Convert test case results to response format
    test_case_response_list = []
    for result in test_case_results:
        test_case_response_list.append(TestCaseResult(
            test_case_id=result["test_case_id"],
            status=TestCaseRunStatus(result["status"]),
            target_task_id=result["target_task_id"],
            grader_task_id=result["grader_task_id"],
            target_response=result["target_response"],
            grader_response=result["grader_response"],
            score=result["score"],
            error_message=result["error_message"],
            started_at=result["started_at"],
            completed_at=result["completed_at"]
        ))
    
    return EvaluationRunResponse(
        id=str(evaluation_run.id),
        evaluation_id=evaluation_run.evaluation_id,
        project_id=evaluation_run.project_id,
        target_agent_id=evaluation_run.target_agent_id,
        grading_agent_id=evaluation_run.grading_agent_id,
        grading_agent_project_id=evaluation_run.grading_agent_project_id,
        status=evaluation_run.status.value,
        test_case_results=test_case_response_list,
        total_test_cases=evaluation_run.total_test_cases,
        completed_test_cases=evaluation_run.completed_test_cases,
        failed_test_cases=evaluation_run.failed_test_cases,
        overall_score=evaluation_run.overall_score,
        error_message=evaluation_run.error_message,
        started_at=evaluation_run.started_at.isoformat() if evaluation_run.started_at else None,
        completed_at=evaluation_run.completed_at.isoformat() if evaluation_run.completed_at else None,
        created_at=evaluation_run.created_at.isoformat(),
        updated_at=evaluation_run.updated_at.isoformat()
    )

@router.get("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    run_id: str
):
    """Get evaluation run status and results"""
    
    # Verify evaluation run exists and belongs to the specified project/agent/evaluation
    evaluation_run = await EvaluationRun.find_one({
        "_id": run_id,
        "evaluation_id": evaluation_id,
        "project_id": project_id,
        "target_agent_id": agent_id
    })
    if not evaluation_run:
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation run {run_id} not found"
        )
    
    # Convert test case results to response format
    test_case_response_list = []
    for result in evaluation_run.test_case_results:
        test_case_response_list.append(TestCaseResult(
            test_case_id=result["test_case_id"],
            status=TestCaseRunStatus(result["status"]),
            target_task_id=result.get("target_task_id"),
            grader_task_id=result.get("grader_task_id"),
            target_response=result.get("target_response"),
            grader_response=result.get("grader_response"),
            score=result.get("score"),
            error_message=result.get("error_message"),
            started_at=result.get("started_at"),
            completed_at=result.get("completed_at")
        ))
    
    return EvaluationRunResponse(
        id=str(evaluation_run.id),
        evaluation_id=evaluation_run.evaluation_id,
        project_id=evaluation_run.project_id,
        target_agent_id=evaluation_run.target_agent_id,
        grading_agent_id=evaluation_run.grading_agent_id,
        grading_agent_project_id=evaluation_run.grading_agent_project_id,
        status=evaluation_run.status.value,
        test_case_results=test_case_response_list,
        total_test_cases=evaluation_run.total_test_cases,
        completed_test_cases=evaluation_run.completed_test_cases,
        failed_test_cases=evaluation_run.failed_test_cases,
        overall_score=evaluation_run.overall_score,
        error_message=evaluation_run.error_message,
        started_at=evaluation_run.started_at.isoformat() if evaluation_run.started_at else None,
        completed_at=evaluation_run.completed_at.isoformat() if evaluation_run.completed_at else None,
        created_at=evaluation_run.created_at.isoformat(),
        updated_at=evaluation_run.updated_at.isoformat()
    )

@router.get("/projects/{project_id}/agents/{agent_id}/evaluations/{evaluation_id}/runs", response_model=EvaluationRunList)
async def list_evaluation_runs(
    project_id: str,
    agent_id: str,
    evaluation_id: str,
    status: Optional[str] = Query(None, description="Filter by run status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip")
):
    """List evaluation runs for an evaluation"""
    
    # Verify evaluation exists and belongs to the specified project/agent
    evaluation = await Evaluation.get(evaluation_id)
    if not evaluation or evaluation.project_id != project_id or evaluation.target_agent_id != agent_id:
        raise HTTPException(
            status_code=404, 
            detail=f"Evaluation {evaluation_id} not found for agent {agent_id} in project {project_id}"
        )
    
    # Build query
    query = {
        "evaluation_id": evaluation_id,
        "project_id": project_id,
        "target_agent_id": agent_id
    }
    if status:
        query["status"] = status
    
    # Get evaluation runs with pagination
    evaluation_runs = await EvaluationRun.find(query).skip(offset).limit(limit).to_list()
    
    # Convert to response format
    run_responses = []
    for run in evaluation_runs:
        test_case_response_list = []
        for result in run.test_case_results:
            test_case_response_list.append(TestCaseResult(
                test_case_id=result["test_case_id"],
                status=TestCaseRunStatus(result["status"]),
                target_task_id=result.get("target_task_id"),
                grader_task_id=result.get("grader_task_id"),
                target_response=result.get("target_response"),
                grader_response=result.get("grader_response"),
                score=result.get("score"),
                error_message=result.get("error_message"),
                started_at=result.get("started_at"),
                completed_at=result.get("completed_at")
            ))
        
        run_responses.append(EvaluationRunResponse(
            id=str(run.id),
            evaluation_id=run.evaluation_id,
            project_id=run.project_id,
            target_agent_id=run.target_agent_id,
            grading_agent_id=run.grading_agent_id,
            grading_agent_project_id=run.grading_agent_project_id,
            status=run.status.value,
            test_case_results=test_case_response_list,
            total_test_cases=run.total_test_cases,
            completed_test_cases=run.completed_test_cases,
            failed_test_cases=run.failed_test_cases,
            overall_score=run.overall_score,
            error_message=run.error_message,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            created_at=run.created_at.isoformat(),
            updated_at=run.updated_at.isoformat()
        ))
    
    return EvaluationRunList(
        runs=run_responses,
        has_more=len(evaluation_runs) == limit
    )
