CREATE TABLE `project_id.agent_monitoring.new_table_log` (
  id STRING DEFAULT GENERATE_UUID(),
  project_id STRING,
  dataset_id STRING,
  table_name STRING,
  full_table_name STRING,
  creation_time TIMESTAMP,
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  agent_triggered BOOLEAN DEFAULT FALSE,
  status STRING DEFAULT 'DETECTED',
  chicory_run_id STRING
);