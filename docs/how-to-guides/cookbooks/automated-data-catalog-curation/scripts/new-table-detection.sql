INSERT INTO `chicory-mds.agent_monitoring.new_table_log` 
  (project_id, dataset_id, table_name, full_table_name, creation_time)
SELECT 
  table_catalog,
  table_schema, 
  table_name,
  CONCAT(table_catalog, '.', table_schema, '.', table_name),
  creation_time
FROM `chicory-mds.raw_financial_data.INFORMATION_SCHEMA.TABLES`
WHERE 
  creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
  AND table_type = 'BASE TABLE'
  AND table_name NOT LIKE '%backup%'
  AND table_name NOT LIKE 'temp_%'
  AND CONCAT(table_catalog, '.', table_schema, '.', table_name) NOT IN (
    SELECT full_table_name FROM `chicory-mds.agent_monitoring.new_table_log`
  );