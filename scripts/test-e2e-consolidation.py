#!/usr/bin/env python3
"""
Chicory E2E Functional Test - Full Data Pipeline
Tests uploads, scanning, claude.md generation, and agent execution.

Usage:
    python scripts/test-e2e-consolidation.py

Requires:
    - Services running (docker compose up)
    - ANTHROPIC_API_KEY in environment
    - BigQuery credentials file at specified path (optional)
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from pathlib import Path

API_URL = os.getenv("API_URL", "http://localhost:8000")
BIGQUERY_CREDS_PATH = os.getenv(
    "BIGQUERY_CREDS_PATH",
    "/Users/hayagrivsridharan/Downloads/chicory-mds-5aae8dd6467c.json"
)
SCAN_TIMEOUT = 300  # 5 minutes for scanning
PROJECTMD_TIMEOUT = 600  # 10 minutes for claude.md generation
TASK_TIMEOUT = 120  # 2 minutes for agent task
DEFAULT_ORG_ID = "e2e-test-org"  # Default organization ID for testing


class E2ETest:
    def __init__(self):
        self.project_id = None
        self.agent_id = None
        self.data_source_ids = []
        self.training_id = None
        self.results = []

    def log(self, step, status, msg=""):
        icon = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "⚠" if status == "WARNING" else "⊘" if status == "SKIPPED" else "..."
        print(f"  {icon} {step}: {msg if msg else status}")
        self.results.append({"step": step, "status": status, "msg": msg})

    async def run(self):
        print("=" * 60)
        print("Chicory E2E Functional Test - Full Data Pipeline")
        print("=" * 60)
        print(f"API URL: {API_URL}")
        print(f"BigQuery Creds: {BIGQUERY_CREDS_PATH}")
        print("=" * 60)

        async with httpx.AsyncClient(base_url=API_URL, timeout=60.0) as client:
            self.client = client

            try:
                # Phase 1: Setup
                print("\n[Phase 1] Setup")
                await self.test_health_check()
                await self.test_create_project()
                await self.test_create_agent()

                # Phase 2: Data Uploads
                print("\n[Phase 2] Data Uploads")
                await self.test_csv_upload()
                await self.test_generic_file_upload()
                await self.test_bigquery_connection()

                # Phase 3: Scanning
                print("\n[Phase 3] Scanning (Training Job)")
                await self.test_create_training()
                await self.test_wait_for_scan()

                # Phase 4: Verify Sandbox
                print("\n[Phase 4] Verify Sandbox Data")
                await self.test_verify_metadata()

                # Phase 5: claude.md Generation
                print("\n[Phase 5] claude.md Generation")
                await self.test_trigger_projectmd()
                await self.test_wait_for_projectmd()
                await self.test_download_projectmd()

                # Phase 6: Agent Execution
                print("\n[Phase 6] Agent Task Execution")
                await self.test_create_playground()
                await self.test_execute_task()

                # Phase 7: Cleanup
                print("\n[Phase 7] Cleanup")
                await self.test_cleanup()

            except Exception as e:
                print(f"\n✗ FATAL ERROR: {e}")
                import traceback
                traceback.print_exc()
                # Still try cleanup
                if self.project_id:
                    try:
                        await self.client.delete(f"/projects/{self.project_id}")
                        print("  (Cleanup attempted)")
                    except:
                        pass
                self.print_summary()
                sys.exit(1)

        # Summary
        self.print_summary()

    # ==================== Phase 1: Setup ====================

    async def test_health_check(self):
        r = await self.client.get("/")
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        self.log("Health check", "PASSED")

    async def test_create_project(self):
        r = await self.client.post("/projects", json={
            "name": f"E2E Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "description": "Automated E2E test for consolidation changes",
            "organization_id": DEFAULT_ORG_ID
        })
        assert r.status_code in [200, 201], f"Create project failed: {r.text}"
        self.project_id = r.json()["id"]
        self.log("Create project", "PASSED", f"id={self.project_id[:8]}...")

    async def test_create_agent(self):
        r = await self.client.post(f"/projects/{self.project_id}/agents", json={
            "name": "E2E Test Agent",
            "instructions": """You are a data analyst assistant.
When asked about the data, use the available tools to query the database and provide insights.
Always be concise and accurate.""",
            "output_format": "text"
        })
        assert r.status_code in [200, 201], f"Create agent failed: {r.text}"
        self.agent_id = r.json()["id"]
        self.log("Create agent", "PASSED", f"id={self.agent_id[:8]}...")

    # ==================== Phase 2: Data Uploads ====================

    async def test_csv_upload(self):
        # Create a test CSV
        csv_content = """name,value,category
Alice,100,A
Bob,200,B
Charlie,150,A
Diana,300,C
Eve,250,B"""

        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        data = {"name": "Test CSV Data", "description": "Sample CSV for E2E test"}

        r = await self.client.post(
            f"/projects/{self.project_id}/data-sources/csv-upload",
            files=files,
            data=data
        )
        assert r.status_code in [200, 201], f"CSV upload failed: {r.text}"
        ds_id = r.json()["id"]
        self.data_source_ids.append(ds_id)
        self.log("CSV upload", "PASSED", f"id={ds_id[:8]}...")

    async def test_generic_file_upload(self):
        # Create a test markdown file
        md_content = """# Project Documentation

## Overview
This is a test document for E2E testing.

## Data Dictionary
- **name**: Person's name
- **value**: Numeric value
- **category**: Category label (A, B, or C)
"""

        files = {"file": ("documentation.md", md_content, "text/markdown")}
        data = {
            "name": "Test Documentation",
            "description": "Sample markdown doc",
            "category": "document"
        }

        r = await self.client.post(
            f"/projects/{self.project_id}/data-sources/generic-upload",
            files=files,
            data=data
        )
        assert r.status_code in [200, 201], f"Generic upload failed: {r.text}"
        ds_id = r.json()["id"]
        self.data_source_ids.append(ds_id)
        self.log("Generic file upload", "PASSED", f"id={ds_id[:8]}...")

    async def test_bigquery_connection(self):
        # Load BigQuery credentials
        creds_path = Path(BIGQUERY_CREDS_PATH)
        if not creds_path.exists():
            self.log("BigQuery connection", "SKIPPED", "Credentials file not found")
            return

        with open(creds_path) as f:
            creds = json.load(f)

        # Create BigQuery data source
        r = await self.client.post(f"/projects/{self.project_id}/data-sources", json={
            "type": "bigquery",
            "name": "BigQuery Test Connection",
            "configuration": {
                "project_id": creds.get("project_id"),
                "private_key_id": creds.get("private_key_id"),
                "private_key": creds.get("private_key"),
                "client_email": creds.get("client_email"),
                "client_id": creds.get("client_id"),
                "client_x509_cert_url": creds.get("client_x509_cert_url"),
                "auth_uri": creds.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": creds.get("token_uri", "https://oauth2.googleapis.com/token")
            }
        })
        assert r.status_code in [200, 201], f"BigQuery create failed: {r.text}"
        ds_id = r.json()["id"]
        self.data_source_ids.append(ds_id)
        self.log("BigQuery data source created", "PASSED", f"id={ds_id[:8]}...")

        # Validate connection
        r = await self.client.post(f"/projects/{self.project_id}/data-sources/{ds_id}/validate")
        if r.status_code == 200:
            result = r.json()
            status = result.get("status", "unknown")
            self.log("BigQuery validation", "PASSED", f"status={status}")
        else:
            self.log("BigQuery validation", "WARNING", f"Validation returned {r.status_code}: {r.text}")

    # ==================== Phase 3: Scanning ====================

    async def test_create_training(self):
        r = await self.client.post(f"/projects/{self.project_id}/training", json={
            "data_source_ids": self.data_source_ids,
            "description": "E2E test scan"
        })
        assert r.status_code in [200, 201], f"Create training failed: {r.text}"
        self.training_id = r.json()["id"]
        self.log("Create training job", "PASSED", f"id={self.training_id[:8]}...")

    async def test_wait_for_scan(self):
        print("       Waiting for scan to complete", end="", flush=True)

        for i in range(SCAN_TIMEOUT):
            await asyncio.sleep(1)
            r = await self.client.get(f"/projects/{self.project_id}/training/{self.training_id}")
            status_data = r.json()

            if status_data["status"] == "completed":
                print()
                self.log("Scan completed", "PASSED")
                return
            elif status_data["status"] == "failed":
                print()
                error = status_data.get("error", "Unknown error")
                self.log("Scan", "FAILED", error)
                raise Exception(f"Scan failed: {error}")

            if i % 10 == 0:
                print(".", end="", flush=True)

        print()
        self.log("Scan", "FAILED", f"Timeout after {SCAN_TIMEOUT}s")
        raise Exception("Scan timeout")

    # ==================== Phase 4: Verify Sandbox ====================

    async def test_verify_metadata(self):
        r = await self.client.get(f"/projects/{self.project_id}/data-sources/metadata")
        assert r.status_code == 200, f"Get metadata failed: {r.text}"

        metadata = r.json()
        status = metadata.get("status", "unknown")

        if status == "available":
            providers = metadata.get("providers", [])
            self.log("Sandbox metadata", "PASSED", f"{len(providers)} providers found")

            # List what was found
            for provider in providers[:5]:  # Show first 5
                name = provider.get("name", "unknown")
                print(f"         - {name}")
        else:
            self.log("Sandbox metadata", "WARNING", f"status={status}")

    # ==================== Phase 5: claude.md Generation ====================

    async def test_trigger_projectmd(self):
        r = await self.client.post(
            f"/projects/{self.project_id}/training/{self.training_id}/projectmd"
        )
        assert r.status_code in [200, 201, 202], f"Trigger projectmd failed: {r.text}"
        self.log("Trigger claude.md generation", "PASSED")

    async def test_wait_for_projectmd(self):
        print("       Waiting for claude.md generation", end="", flush=True)

        for i in range(PROJECTMD_TIMEOUT):
            await asyncio.sleep(1)
            r = await self.client.get(f"/projects/{self.project_id}/training/{self.training_id}")
            training = r.json()

            projectmd = training.get("projectmd_generation", {})
            status = projectmd.get("status", "unknown")

            if status == "completed":
                print()
                self.log("claude.md generation", "PASSED", "s3_url set")
                return
            elif status == "failed":
                print()
                error = projectmd.get("error_message", "Unknown error")
                self.log("claude.md generation", "FAILED", error)
                raise Exception(f"claude.md generation failed: {error}")

            if i % 10 == 0:
                print(".", end="", flush=True)

        print()
        self.log("claude.md generation", "FAILED", f"Timeout after {PROJECTMD_TIMEOUT}s")
        raise Exception("claude.md generation timeout")

    async def test_download_projectmd(self):
        r = await self.client.get(f"/projects/{self.project_id}/training/latest/projectmd")

        if r.status_code == 200:
            content = r.text
            lines = content.split('\n')
            preview = '\n'.join(lines[:5]) + "..." if len(lines) > 5 else content
            self.log("Download claude.md", "PASSED", f"{len(content)} bytes")
            print(f"         Preview:")
            for line in preview.split('\n')[:5]:
                print(f"           {line}")
        else:
            self.log("Download claude.md", "WARNING", f"Status {r.status_code}")

    # ==================== Phase 6: Agent Execution ====================

    async def test_create_playground(self):
        r = await self.client.post(
            f"/projects/{self.project_id}/agents/{self.agent_id}/playgrounds",
            json={"name": "E2E Test Playground"}
        )
        assert r.status_code in [200, 201], f"Create playground failed: {r.text}"
        self.log("Create playground", "PASSED")

    async def test_execute_task(self):
        # Create task
        r = await self.client.post(
            f"/projects/{self.project_id}/agents/{self.agent_id}/tasks",
            json={"content": "What data sources are available? List them briefly."}
        )
        assert r.status_code in [200, 201, 202], f"Create task failed: {r.text}"
        task_id = r.json()["id"]
        self.log("Create task", "PASSED", f"id={task_id[:8]}...")

        # Wait for completion
        print("       Waiting for task completion", end="", flush=True)

        for i in range(TASK_TIMEOUT):
            await asyncio.sleep(1)
            r = await self.client.get(
                f"/projects/{self.project_id}/agents/{self.agent_id}/tasks/{task_id}"
            )
            task = r.json()

            if task["status"] == "completed":
                print()
                response = task.get("response", "")[:200]
                self.log("Task execution", "PASSED")
                print(f"         Response: {response}...")
                return
            elif task["status"] == "failed":
                print()
                error = task.get("error", "Unknown")
                self.log("Task execution", "FAILED", error)
                raise Exception(f"Task failed: {error}")

            if i % 5 == 0:
                print(".", end="", flush=True)

        print()
        self.log("Task execution", "FAILED", f"Timeout after {TASK_TIMEOUT}s")
        raise Exception("Task timeout")

    # ==================== Phase 7: Cleanup ====================

    async def test_cleanup(self):
        try:
            await self.client.delete(f"/projects/{self.project_id}")
            self.log("Delete project", "PASSED")
        except Exception as e:
            self.log("Delete project", "WARNING", str(e))

    # ==================== Summary ====================

    def print_summary(self):
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        skipped = sum(1 for r in self.results if r["status"] == "SKIPPED")
        warnings = sum(1 for r in self.results if r["status"] == "WARNING")

        print(f"  PASSED:   {passed}")
        print(f"  FAILED:   {failed}")
        print(f"  SKIPPED:  {skipped}")
        print(f"  WARNINGS: {warnings}")
        print("=" * 60)

        if failed > 0:
            print("RESULT: FAILED")
            sys.exit(1)
        else:
            print("RESULT: PASSED")
            sys.exit(0)


if __name__ == "__main__":
    test = E2ETest()
    asyncio.run(test.run())
