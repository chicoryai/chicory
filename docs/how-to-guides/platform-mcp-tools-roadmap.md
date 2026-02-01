# Platform MCP Tools — Roadmap

This document captures proposed additions to the Chicory platform MCP tools. These are **meta-level authoring tools** available to all platform users, not integration-specific tools (Snowflake, BigQuery, etc.).

## Current Tools (29)

| Category | Count | Tools |
|----------|-------|-------|
| Projects | 1 | list_projects |
| Agents | 5 | create, list, get, update, deploy |
| Execution | 2 | execute_agent, get_context |
| Tasks | 2 | list_agent_tasks, get_agent_task |
| Evaluations | 7 | create, list, get, delete, execute, add_test_cases, list_runs, get_result |
| Data Sources | 8 | list_types, list, get, create, update, delete, validate_credentials, test_connection |
| Folder Files | 3 | list_folder_files, get_folder_file, delete_folder_file |

---

## Proposed Tools

### P0 — High Value

#### 1. `chicory_clone_agent`
Duplicate an agent within or across projects. Copies instructions, output format, and optionally evaluation test cases.

**Why:** Core authoring workflow. Users iterate by cloning a working agent, tweaking instructions, and comparing results via evals. Today this requires get + create + manually copying config.

**Parameters:**
- `project_id` (string, required): Source project
- `agent_id` (string, required): Agent to clone
- `target_project_id` (string, optional): Target project (defaults to same project)
- `name` (string, optional): Name for the clone (defaults to `{original_name} (Copy)`)
- `include_evaluations` (boolean, optional): Clone evaluation test cases too (default: false)

---

#### 2. `chicory_delete_agent`
Delete an agent from a project.

**Why:** Notable gap — you can create, update, and deploy agents but cannot delete one via MCP. Forces users to the web UI for cleanup.

**Parameters:**
- `project_id` (string, required)
- `agent_id` (string, required)

---

#### 3. `chicory_compare_evaluation_runs`
Given two evaluation run IDs, return a side-by-side diff of scores and individual test case pass/fail changes.

**Why:** The iterate-and-improve loop is the core value prop. Currently users fetch two results separately and mentally diff them. This should be a single call.

**Parameters:**
- `project_id` (string, required)
- `agent_id` (string, required)
- `evaluation_id` (string, required)
- `run_id_a` (string, required): Baseline run
- `run_id_b` (string, required): Comparison run

**Returns:** Overall score delta, per-test-case comparison (improved / regressed / unchanged), summary statistics.

---

#### 4. `chicory_bulk_execute_agent`
Execute an agent against multiple inputs in one call (batch mode).

**Why:** Testing agents at scale requires N sequential `execute_agent` calls today. Batch mode enables prompt sweeping, regression testing, and load testing from a single invocation.

**Parameters:**
- `project_id` (string, required)
- `agent_id` (string, required)
- `tasks` (array, required): Array of `{ task_content, metadata? }` objects (max 50)
- `wait_for_result` (boolean, optional): Wait for all to complete (default: false)

**Returns:** Batch ID + individual task IDs for tracking.

---

#### 5. `chicory_get_agent_logs`
Fetch recent agent execution logs — not just task results, but operational logs, errors, and tool call traces.

**Why:** Debugging agent misbehavior without the web UI. Especially useful for programmatic monitoring and alerting workflows.

**Parameters:**
- `project_id` (string, required)
- `agent_id` (string, required)
- `limit` (integer, optional): Number of log entries (default: 100)
- `level` (string, optional): Filter by level — `error`, `warn`, `info`, `debug`
- `since` (string, optional): ISO timestamp to fetch logs after

---

#### 6. `chicory_list_projects_summary`
Lightweight project listing with activity context: agent count, data source count, last activity timestamp per project.

**Why:** Current `list_projects` returns basic metadata. Users managing multiple projects can't tell which ones are active or how large they are without making N follow-up calls.

**Parameters:** None (or optional `include_counts: boolean`)

**Returns:** Projects with `agent_count`, `data_source_count`, `last_activity_at`.

---

### P1 — Medium Value

#### 7. `chicory_export_agent` / `chicory_import_agent`
Serialize an agent's full config (instructions, output format, description, eval test cases, data source bindings) to a portable JSON blob. Import recreates the agent from that blob.

**Why:** Enables version control of agent configs in git, sharing agents between orgs, backup/restore, and CI/CD pipelines for agent deployment.

**Export parameters:**
- `project_id`, `agent_id` (required)
- `include_evaluations` (boolean, optional)

**Import parameters:**
- `project_id` (required)
- `agent_config` (object, required): The exported JSON blob
- `name` (string, optional): Override name

---

#### 8. `chicory_get_agent_metrics`
Aggregated statistics for an agent over a time window: total executions, average latency, success/failure rate, token usage.

**Why:** Operational visibility. Today you'd list all tasks and compute metrics yourself — expensive and impractical at scale.

**Parameters:**
- `project_id`, `agent_id` (required)
- `period` (string, optional): `1h`, `24h`, `7d`, `30d` (default: `24h`)

**Returns:** `{ total_executions, success_rate, avg_latency_ms, p95_latency_ms, total_tokens, error_count }`.

---

#### 9. `chicory_search_tasks`
Search across task history by content, status, date range, or error type.

**Why:** `list_agent_tasks` only paginates chronologically. No way to find "all failed tasks from last week" or "tasks containing keyword X" without fetching everything.

**Parameters:**
- `project_id`, `agent_id` (required)
- `query` (string, optional): Full-text search on task content/response
- `status` (string, optional): `completed`, `failed`, `in_progress`
- `from_date` / `to_date` (string, optional): ISO timestamps
- `limit`, `skip` (integer, optional)

---

#### 10. `chicory_undeploy_agent`
Disable a deployed agent without deleting it. Pause an agent that's misbehaving or under maintenance.

**Why:** There's `deploy` but no `undeploy`. The only way to stop an agent today is to delete it, losing all config.

**Parameters:**
- `project_id`, `agent_id` (required)

---

### P2 — Lower Priority

#### 11. `chicory_list_mcp_gateways` / `chicory_manage_gateway_tools`
Platform-level gateway management. The backend REST endpoints exist but aren't exposed as platform MCP tools.

**Why:** Power users managing custom MCP gateways and tools programmatically.

---

#### 12. `chicory_trigger_training`
Start a data scan/training job via MCP. Currently only available through the web UI.

**Why:** Enables automation — trigger a re-scan after adding new data sources programmatically.

**Parameters:**
- `project_id` (required)
- `data_source_ids` (array, optional): Specific sources to scan (default: all)

---

#### 13. `chicory_get_training_status`
Check training/scan job progress via MCP.

**Why:** Companion to `trigger_training`. Complete the automation loop: trigger scan, poll status, then run evals.

**Parameters:**
- `project_id` (required)
- `job_id` (string, optional): Specific job (default: latest)
