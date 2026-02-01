"""
Evaluation orchestration utilities for Phase 2 execution.
Handles background task execution, polling, and result aggregation.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
import logging

from app.models.evaluation import EvaluationRun, EvaluationRunStatus, TestCaseRunStatus
from app.models.tasks import Task, TaskRole, TaskStatus
from app.models.agent import Agent
from app.utils.rabbitmq_client import queue_agent_task

logger = logging.getLogger(__name__)

class EvaluationOrchestrator:
    """Orchestrates evaluation execution with parallel task processing"""
    
    def __init__(self, evaluation_run: EvaluationRun, evaluation_test_cases: List[Dict[str, Any]], criteria: str):
        self.evaluation_run = evaluation_run
        self.test_cases = evaluation_test_cases
        self.criteria = criteria
        self.target_tasks: Dict[str, str] = {}  # test_case_id -> task_id
        self.grader_tasks: Dict[str, str] = {}  # test_case_id -> task_id
        
    async def start_evaluation(self):
        """Start the evaluation execution process"""
        try:
            logger.info(f"Starting evaluation run {self.evaluation_run.id}")
            
            # Update status to running
            self.evaluation_run.status = EvaluationRunStatus.RUNNING
            await self.evaluation_run.update({"$set": {"status": self.evaluation_run.status.value}})
            
            # Start target agent tasks for all test cases
            await self._create_target_tasks()
            
            # Start polling for completion
            await self._poll_and_process_results()
            
        except Exception as e:
            logger.error(f"Error in evaluation orchestration: {e}")
            await self._mark_evaluation_failed(str(e))
    
    async def _create_target_tasks(self):
        """Create tasks for the target agent for all test cases"""
        logger.info(f"Creating target tasks for {len(self.test_cases)} test cases")
        
        for i, test_case in enumerate(self.test_cases):
            test_case_id = test_case.get("id", f"tc_{i}")
            task_content = test_case["task"]
            
            try:
                # Create user task for target agent
                user_task = Task(
                    agent_id=self.evaluation_run.target_agent_id,
                    project_id=self.evaluation_run.project_id,
                    role=TaskRole.USER,
                    content=task_content,
                    status=TaskStatus.QUEUED,
                    metadata={"evaluation_run_id": str(self.evaluation_run.id), "test_case_id": test_case_id}
                )
                await user_task.save()
                
                # Create assistant task
                assistant_task = Task(
                    agent_id=self.evaluation_run.target_agent_id,
                    project_id=self.evaluation_run.project_id,
                    role=TaskRole.ASSISTANT,
                    content="",
                    status=TaskStatus.QUEUED,
                    related_task_id=str(user_task.id),
                    metadata={"evaluation_run_id": str(self.evaluation_run.id), "test_case_id": test_case_id}
                )
                await assistant_task.save()
                
                # Store task ID for tracking
                self.target_tasks[test_case_id] = str(assistant_task.id)
                
                # Update test case status
                await self._update_test_case_status(test_case_id, TestCaseRunStatus.RUNNING_TARGET, 
                                                  target_task_id=str(assistant_task.id))
                
                # Queue the task for processing
                await queue_agent_task(
                    task_id=str(user_task.id),
                    assistant_task_id=str(assistant_task.id),
                    agent_id=self.evaluation_run.target_agent_id,
                    project_id=self.evaluation_run.project_id,
                    content=task_content,
                    metadata={"evaluation_run_id": str(self.evaluation_run.id), "test_case_id": test_case_id}
                )
                
                logger.info(f"Created target task {assistant_task.id} for test case {test_case_id}")
                
            except Exception as e:
                logger.error(f"Error creating target task for test case {test_case_id}: {e}")
                await self._update_test_case_status(test_case_id, TestCaseRunStatus.FAILED, 
                                                  error_message=f"Failed to create target task: {str(e)}")
    
    async def _poll_and_process_results(self):
        """Poll for task completion and process results"""
        max_polls = 3600  # 1 hour with 1-second intervals
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                # Check target task completion
                await self._check_target_task_completion()
                
                # Check grader task completion
                await self._check_grader_task_completion()
                
                # Check if evaluation is complete
                if await self._is_evaluation_complete():
                    await self._finalize_evaluation()
                    break
                
                # Wait before next poll
                await asyncio.sleep(1)
                poll_count += 1
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await self._mark_evaluation_failed(str(e))
                break
        
        if poll_count >= max_polls:
            await self._mark_evaluation_failed("Evaluation timed out")
    
    async def _check_target_task_completion(self):
        """Check for completed target agent tasks"""
        for test_case_id, task_id in self.target_tasks.items():
            if not task_id:
                continue
                
            # Get current test case status
            current_result = await self._get_test_case_result(test_case_id)
            if current_result["status"] != TestCaseRunStatus.RUNNING_TARGET.value:
                continue
            
            # Check if task is completed
            task = await Task.get(task_id)
            if task and task.status == TaskStatus.COMPLETED:
                logger.info(f"Target task {task_id} completed for test case {test_case_id}")
                
                # Create grader task
                await self._create_grader_task(test_case_id, task.content)
    
    async def _create_grader_task(self, test_case_id: str, target_response: str):
        """Create grading task for a completed target response"""
        try:
            # Find the test case
            test_case = next((tc for tc in self.test_cases if tc.get("id") == test_case_id), None)
            if not test_case:
                raise ValueError(f"Test case {test_case_id} not found")
            
            # Create grading prompt
            grading_prompt = self._create_grading_prompt(
                task=test_case["task"],
                expected_output=test_case["expected_output"],
                actual_output=target_response,
                evaluation_guideline=test_case["evaluation_guideline"],
                criteria=self.criteria
            )
            
            # Create user task for grading agent
            user_task = Task(
                agent_id=self.evaluation_run.grading_agent_id,
                project_id=self.evaluation_run.grading_agent_project_id,
                role=TaskRole.USER,
                content=grading_prompt,
                status=TaskStatus.QUEUED,
                metadata={"evaluation_run_id": str(self.evaluation_run.id), "test_case_id": test_case_id}
            )
            await user_task.save()
            
            # Create assistant task
            assistant_task = Task(
                agent_id=self.evaluation_run.grading_agent_id,
                project_id=self.evaluation_run.grading_agent_project_id,
                role=TaskRole.ASSISTANT,
                content="",
                status=TaskStatus.QUEUED,
                related_task_id=str(user_task.id),
                metadata={"evaluation_run_id": str(self.evaluation_run.id), "test_case_id": test_case_id}
            )
            await assistant_task.save()
            
            # Store grader task ID
            self.grader_tasks[test_case_id] = str(assistant_task.id)
            
            # Update test case status
            await self._update_test_case_status(test_case_id, TestCaseRunStatus.RUNNING_GRADER,
                                              target_response=target_response,
                                              grader_task_id=str(assistant_task.id))
            
            # Queue the grading task
            await queue_agent_task(
                task_id=str(user_task.id),
                assistant_task_id=str(assistant_task.id),
                agent_id=self.evaluation_run.grading_agent_id,
                project_id=self.evaluation_run.grading_agent_project_id,
                content=grading_prompt,
                metadata={"evaluation_run_id": str(self.evaluation_run.id), "test_case_id": test_case_id}
            )
            
            logger.info(f"Created grader task {assistant_task.id} for test case {test_case_id}")
            
        except Exception as e:
            logger.error(f"Error creating grader task for test case {test_case_id}: {e}")
            await self._update_test_case_status(test_case_id, TestCaseRunStatus.FAILED,
                                              error_message=f"Failed to create grader task: {str(e)}")
    
    async def _check_grader_task_completion(self):
        """Check for completed grader tasks"""
        for test_case_id, task_id in self.grader_tasks.items():
            if not task_id:
                continue
                
            # Get current test case status
            current_result = await self._get_test_case_result(test_case_id)
            if current_result["status"] != TestCaseRunStatus.RUNNING_GRADER.value:
                continue
            
            # Check if grader task is completed
            task = await Task.get(task_id)
            if task and task.status == TaskStatus.COMPLETED:
                logger.info(f"Grader task {task_id} completed for test case {test_case_id}")
                
                # Parse score from grader response
                score = self._parse_score_from_response(task.content)
                
                # Update test case as completed
                await self._update_test_case_status(test_case_id, TestCaseRunStatus.COMPLETED,
                                                  grader_response=task.content,
                                                  score=score,
                                                  completed_at=datetime.utcnow())
    
    def _create_grading_prompt(self, task: str, expected_output: str, actual_output: str, 
                             evaluation_guideline: str, criteria: str) -> str:
        """Create a structured prompt for the grading agent"""
        return f"""You are an expert evaluator. Please evaluate the following response based on the provided criteria and guidelines.

**Task/Query:**
{task}

**Expected Output:**
{expected_output}

**Actual Response:**
{actual_output}

**Evaluation Guideline:**
{evaluation_guideline}

**Overall Criteria:**
{criteria}

**Instructions:**
1. Evaluate the actual response against the expected output and guidelines
2. Consider accuracy, completeness, helpfulness, and adherence to criteria
3. Provide a score between 0.0 and 1.0 (where 1.0 is perfect)
4. Include your reasoning for the score

**Required Response Format:**
Score: [0.0-1.0]
Reasoning: [Your detailed explanation]

Please provide your evaluation now."""
    
    def _parse_score_from_response(self, grader_response: str) -> Optional[float]:
        """Parse numerical score from grader response"""
        try:
            # Look for "Score: X.X" pattern
            score_match = re.search(r'Score:\s*([0-9]*\.?[0-9]+)', grader_response, re.IGNORECASE)
            if score_match:
                score = float(score_match.group(1))
                # Ensure score is between 0.0 and 1.0
                return max(0.0, min(1.0, score))
            
            # Look for other numeric patterns
            numeric_matches = re.findall(r'\b([0-9]*\.?[0-9]+)\b', grader_response)
            for match in numeric_matches:
                score = float(match)
                if 0.0 <= score <= 1.0:
                    return score
                elif 0 <= score <= 10:  # Convert 0-10 scale to 0-1
                    return score / 10.0
                elif 0 <= score <= 100:  # Convert 0-100 scale to 0-1
                    return score / 100.0
            
            logger.warning(f"Could not parse score from grader response: {grader_response[:100]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing score from grader response: {e}")
            return None
    
    async def _update_test_case_status(self, test_case_id: str, status: TestCaseRunStatus, **kwargs):
        """Update test case status in the evaluation run"""
        # Find and update the test case result
        for i, result in enumerate(self.evaluation_run.test_case_results):
            if result["test_case_id"] == test_case_id:
                self.evaluation_run.test_case_results[i]["status"] = status.value
                
                # Update additional fields
                for key, value in kwargs.items():
                    if value is not None:
                        if key == "completed_at" and isinstance(value, datetime):
                            self.evaluation_run.test_case_results[i][key] = value
                        else:
                            self.evaluation_run.test_case_results[i][key] = value
                
                # Update the database
                await self.evaluation_run.update({"$set": {"test_case_results": self.evaluation_run.test_case_results}})
                break
    
    async def _get_test_case_result(self, test_case_id: str) -> Dict[str, Any]:
        """Get current test case result"""
        for result in self.evaluation_run.test_case_results:
            if result["test_case_id"] == test_case_id:
                return result
        return {}
    
    async def _is_evaluation_complete(self) -> bool:
        """Check if all test cases are completed or failed"""
        for result in self.evaluation_run.test_case_results:
            status = result["status"]
            if status not in [TestCaseRunStatus.COMPLETED.value, TestCaseRunStatus.FAILED.value]:
                return False
        return True
    
    async def _finalize_evaluation(self):
        """Calculate final scores and mark evaluation as complete"""
        completed_count = 0
        failed_count = 0
        total_score = 0.0
        scored_count = 0
        
        for result in self.evaluation_run.test_case_results:
            if result["status"] == TestCaseRunStatus.COMPLETED.value:
                completed_count += 1
                if result.get("score") is not None:
                    total_score += result["score"]
                    scored_count += 1
            elif result["status"] == TestCaseRunStatus.FAILED.value:
                failed_count += 1
        
        # Calculate overall score (simple average)
        overall_score = total_score / scored_count if scored_count > 0 else None
        
        # Update evaluation run
        self.evaluation_run.status = EvaluationRunStatus.COMPLETED
        self.evaluation_run.completed_test_cases = completed_count
        self.evaluation_run.failed_test_cases = failed_count
        self.evaluation_run.overall_score = overall_score
        self.evaluation_run.completed_at = datetime.utcnow()
        
        await self.evaluation_run.update({"$set": {
            "status": self.evaluation_run.status.value,
            "completed_test_cases": completed_count,
            "failed_test_cases": failed_count,
            "overall_score": overall_score,
            "completed_at": self.evaluation_run.completed_at
        }})
        
        logger.info(f"Evaluation run {self.evaluation_run.id} completed. Score: {overall_score}, "
                   f"Completed: {completed_count}, Failed: {failed_count}")
    
    async def _mark_evaluation_failed(self, error_message: str):
        """Mark evaluation as failed"""
        self.evaluation_run.status = EvaluationRunStatus.FAILED
        self.evaluation_run.error_message = error_message
        self.evaluation_run.completed_at = datetime.utcnow()
        
        await self.evaluation_run.update({"$set": {
            "status": self.evaluation_run.status.value,
            "error_message": error_message,
            "completed_at": self.evaluation_run.completed_at
        }})
        
        logger.error(f"Evaluation run {self.evaluation_run.id} failed: {error_message}")


async def start_evaluation_orchestration(evaluation_run_id: str):
    """Start evaluation orchestration in the background"""
    try:
        # Get evaluation run
        evaluation_run = await EvaluationRun.find_one({"_id": evaluation_run_id})
        if not evaluation_run:
            logger.error(f"Evaluation run {evaluation_run_id} not found")
            return
        
        # Get evaluation details
        from app.models.evaluation import Evaluation
        evaluation = await Evaluation.get(evaluation_run.evaluation_id)
        if not evaluation:
            logger.error(f"Evaluation {evaluation_run.evaluation_id} not found")
            return
        
        # Start orchestration
        orchestrator = EvaluationOrchestrator(evaluation_run, evaluation.test_cases, evaluation.criteria)
        await orchestrator.start_evaluation()
        
    except Exception as e:
        logger.error(f"Error starting evaluation orchestration: {e}")
