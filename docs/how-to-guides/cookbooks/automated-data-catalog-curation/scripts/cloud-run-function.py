import functions_framework
import requests
from google.cloud import bigquery
from datetime import datetime, timezone
import time
import json
import re


@functions_framework.http
def process_tables_manual(request):
   try:
       client = bigquery.Client()
      
       # Get all the unprocessed tables
       results = client.query("""
           SELECT id, full_table_name
           FROM `chicory-mds.agent_monitoring.new_table_log`
           WHERE agent_triggered = FALSE
           LIMIT 5
       """).result()
      
       processed_tables = []
      
       for row in results:
           # Call the Chicory agent
           response = requests.post(
               'https://app.chicory.ai/api/v1/runs',
               headers={
                   'Content-Type': 'application/json',
                   'Authorization': CHICORY_API_KEY
               },
               json={
                   'agent_name': CHICORY_AGENT_ID,
                   'input': [{
                       'parts': [{'content_type': 'text/plain', 'content': f'New table: {row.full_table_name}'}],
                       'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                   }]
               }
           )
          
           if response.status_code == 200:
               run_id = response.json().get('run_id')
              
               # Poll for completion (2 minutes max)
               final_status = 'TIMEOUT'
               columns_updated = 0
              
               for i in range(20):  # total 10 min to be safe
                   time.sleep(15)  # Wait 15 seconds
                  
                   status_response = requests.get(
                       f'https://app.chicory.ai/api/v1/runs/{run_id}',
                       headers={'Authorization': CHICORY_API_KEY}
                   )
                  
                   if status_response.status_code == 200:
                       status_data = status_response.json()
                       status = status_data.get('status', '')
                      
                       if status == 'completed':
                           final_status = 'COMPLETED'
                          
                           # Extract JSON and update metadata
                           json_output = get_agent_json_output(status_data)
                           if json_output:
                               extracted_data = extract_column_metadata(json_output)
                               if extracted_data:
                                   columns_updated = update_column_metadata(extracted_data)
                          
                           break
                       elif status == 'failed':
                           final_status = 'FAILED'
                           break
              
               # Update monitoring table
               client.query(f"""
                   UPDATE `chicory-mds.agent_monitoring.new_table_log`
                   SET agent_triggered = TRUE,
                       status = '{final_status}',
                       chicory_run_id = '{run_id}'
                   WHERE id = '{row.id}'
               """)
              
               processed_tables.append({
                   'table': row.full_table_name,
                   'status': final_status,
                   'run_id': run_id,
                   'columns_updated': columns_updated
               })
           else:
               processed_tables.append({
                   'table': row.full_table_name,
                   'status': 'API_FAILED',
                   'error': f'HTTP {response.status_code}'
               })
      
       return {
           'success': True,
           'processed_count': len(processed_tables),
           'tables': processed_tables
       }
      
   except Exception as e:
       return {'error': str(e)}




def get_agent_json_output(status_data):
   try:
       outputs = status_data.get('output', [])
      
       for output in outputs:
           parts = output.get('parts', [])
           for part in parts:
               content = part.get('content', '')
              
               # Parse outer JSON wrapper
               outer_json = json.loads(content)
               response_text = outer_json.get('response', '')
              
               # Remove markdown wrapper
               if '```json' in response_text:
                   json_start = response_text.find('```json') + 7
                   json_end = response_text.rfind('```')
                   raw_json = response_text[json_start:json_end].strip()
                  
                   # Unescape the JSON
                   clean_json = raw_json.replace('\\"', '"').replace('\\n', '\n')
                  
                   return clean_json
              
       return None
   except:
       return None




def extract_column_metadata(json_response):
   """Extract column metadata from agent response"""
   try:
       data = json.loads(json_response)
      
       table_name = data.get('table_name', '')
       columns = data.get('columns', [])
      
       extracted_data = []
       for col in columns:
           column_info = {
               'table_name': table_name,
               'column_name': col.get('column_name', ''),
               'description': col.get('description', ''),
               'policy_tag': col.get('policy_tag', '')
           }
           extracted_data.append(column_info)
      
       return extracted_data
      
   except Exception as e:
       print(f"Error extracting data: {e}")
       return None




def update_column_metadata(extracted_data):
   """Update BigQuery table with column descriptions and policy tags"""
   try:
       client = bigquery.Client()
      
       full_table_name = extracted_data[0]['table_name']
       parts = full_table_name.split('.')
       if len(parts) != 3:
           return 0
          
       project_id, dataset_id, table_id = parts
      
       table_ref = client.dataset(dataset_id, project=project_id).table(table_id)
       table = client.get_table(table_ref)
      
       print(f"Updating table: {full_table_name}")
      
       # DEBUG: Print extracted data
       for col_data in extracted_data:
           print(f"Agent data - Column: '{col_data['column_name']}', Description: '{col_data['description'][:50]}...', Policy: '{col_data.get('policy_tag', 'None')[:50]}...'")
      
       # Create column mapping
       column_updates = {}
       for col_data in extracted_data:
           column_updates[col_data['column_name']] = {
               'description': col_data['description'].strip(),
               'policy_tag': col_data.get('policy_tag', '').strip() or None
           }
      
       print(f"Column updates mapping: {list(column_updates.keys())}")
      
       # Build new schema
       new_schema = []
       updated_count = 0
      
       for field in table.schema:
           print(f"Processing BQ field: '{field.name}'")
           update_info = column_updates.get(field.name, {})
           print(f"  Found update info: {bool(update_info)}")
          
           new_description = update_info.get('description') or field.description or ''
           new_policy_tag = update_info.get('policy_tag')
          
           print(f"  Current desc: '{(field.description or '')[:30]}...'")
           print(f"  New desc: '{new_description[:30]}...'")
           print(f"  New policy tag: {new_policy_tag[:50] if new_policy_tag else 'None'}...")
          
           # Check if changes needed
           description_changed = new_description != (field.description or '')
           existing_tags = set(field.policy_tags.names if field.policy_tags else [])
           new_tags = set([new_policy_tag] if new_policy_tag else [])
           policy_tags_changed = existing_tags != new_tags
          
           print(f"  Description changed: {description_changed}")
           print(f"  Policy tags changed: {policy_tags_changed}")
          
           if description_changed or policy_tags_changed:
               updated_count += 1
               print(f"  *** UPDATING '{field.name}' ***")
          
           # Create new field
           if new_policy_tag:
               policy_tag_list = bigquery.PolicyTagList(names=[new_policy_tag])
               new_field = bigquery.SchemaField(
                   name=field.name,
                   field_type=field.field_type,
                   mode=field.mode,
                   description=new_description,
                   policy_tags=policy_tag_list
               )
           else:
               new_field = bigquery.SchemaField(
                   name=field.name,
                   field_type=field.field_type,
                   mode=field.mode,
                   description=new_description
               )
          
           new_schema.append(new_field)
      
       # Update table
       table.schema = new_schema
       client.update_table(table, ["schema"])
      
       print(f"Successfully updated {updated_count} columns for {full_table_name}")
       return updated_count
      
   except Exception as e:
       print(f"Error updating table: {e}")
       return 0
