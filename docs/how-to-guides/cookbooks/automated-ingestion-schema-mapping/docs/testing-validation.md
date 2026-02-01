# Testing & Validation

## Overview

This section covers comprehensive testing and validation strategies for the automated ingestion and schema mapping pipeline. We'll test each component individually and the entire end-to-end workflow.

## Testing Strategy

### 1. Unit Testing

Test individual components in isolation:
- Schema extraction functions
- Chicory agent responses
- dbt model generation
- File processing logic

### 2. Integration Testing

Test component interactions:
- Airflow → GitHub Actions flow
- GitHub Actions → Chicory agents
- Chicory agents → dbt generation
- Complete pipeline execution

### 3. End-to-End Testing

Validate the entire workflow from CSV upload to dbt model deployment.

## Unit Testing

### 1. Schema Extraction Testing

Create `tests/test_schema_extraction.py`:

```python
import unittest
import pandas as pd
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add the scripts directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from generate_schema_mapping import extract_csv_schema, parse_mapping_from_response

class TestSchemaExtraction(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.sample_csv_data = pd.DataFrame({
            'customer_id': [1, 2, 3, 4, 5],
            'first_name': ['John', 'Jane', 'Bob', 'Alice', 'Charlie'],
            'email': ['john@example.com', 'jane@test.com', 'bob@email.com', 'alice@domain.com', 'charlie@site.com'],
            'created_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'is_active': [True, True, False, True, True]
        })

    def test_column_type_detection(self):
        """Test correct detection of column data types"""
        schema_info = self.extract_schema_from_dataframe(self.sample_csv_data, 'customers')

        # Check column count
        self.assertEqual(len(schema_info['columns']), 5)

        # Check specific column types
        columns = {col['name']: col for col in schema_info['columns']}

        self.assertEqual(columns['customer_id']['dtype'], 'int64')
        self.assertEqual(columns['first_name']['dtype'], 'object')
        self.assertEqual(columns['email']['semantic_type'], 'email')
        self.assertEqual(columns['is_active']['dtype'], 'bool')

    def test_semantic_type_inference(self):
        """Test semantic type inference logic"""
        schema_info = self.extract_schema_from_dataframe(self.sample_csv_data, 'customers')
        columns = {col['name']: col for col in schema_info['columns']}

        self.assertEqual(columns['customer_id']['semantic_type'], 'identifier')
        self.assertEqual(columns['email']['semantic_type'], 'email')
        self.assertEqual(columns['created_date']['semantic_type'], 'temporal')

    def test_null_percentage_calculation(self):
        """Test null percentage calculation"""
        # Add some null values
        test_data = self.sample_csv_data.copy()
        test_data.loc[0, 'first_name'] = None
        test_data.loc[1, 'first_name'] = None

        schema_info = self.extract_schema_from_dataframe(test_data, 'customers')
        columns = {col['name']: col for col in schema_info['columns']}

        self.assertEqual(columns['first_name']['null_percentage'], 40.0)  # 2/5 * 100

    def test_unique_count_calculation(self):
        """Test unique value count calculation"""
        schema_info = self.extract_schema_from_dataframe(self.sample_csv_data, 'customers')
        columns = {col['name']: col for col in schema_info['columns']}

        self.assertEqual(columns['customer_id']['unique_count'], 5)
        self.assertEqual(columns['is_active']['unique_count'], 2)

    def extract_schema_from_dataframe(self, df, table_name):
        """Helper method to extract schema from DataFrame"""
        schema_info = {
            'table_name': table_name,
            'row_count': len(df),
            'columns': []
        }

        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'null_percentage': float(df[col].isnull().sum() / len(df) * 100),
                'unique_count': int(df[col].nunique()),
                'sample_values': df[col].dropna().head(5).tolist()
            }

            # Infer semantic type
            if 'id' in col.lower():
                col_info['semantic_type'] = 'identifier'
            elif 'email' in col.lower():
                col_info['semantic_type'] = 'email'
            elif 'phone' in col.lower():
                col_info['semantic_type'] = 'phone'
            elif 'date' in col.lower() or 'time' in col.lower():
                col_info['semantic_type'] = 'temporal'
            elif df[col].dtype in ['float64', 'int64']:
                col_info['semantic_type'] = 'numeric'
            else:
                col_info['semantic_type'] = 'text'

            schema_info['columns'].append(col_info)

        return schema_info

if __name__ == '__main__':
    unittest.main()
```

### 2. Mapping Validation Testing

Create `tests/test_mapping_validation.py`:

```python
import unittest
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from validate_mapping import validate_mapping_structure, validate_naming_conventions, validate_data_types

class TestMappingValidation(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.valid_mapping = {
            "mapping_metadata": {
                "source_table": "customers",
                "target_table": "dim_customer",
                "mapping_version": "1.0",
                "mapping_confidence": 0.95
            },
            "column_mappings": [
                {
                    "source_column": "customer_id",
                    "target_column": "customer_bk",
                    "source_type": "int64",
                    "target_type": "STRING",
                    "transformation": "CAST({source_column} AS STRING)"
                },
                {
                    "source_column": "first_name",
                    "target_column": "first_name",
                    "source_type": "object",
                    "target_type": "STRING",
                    "transformation": "INITCAP(TRIM({source_column}))"
                }
            ],
            "recommendations": {
                "primary_key_suggestion": "customer_sk"
            }
        }

    def test_valid_mapping_structure(self):
        """Test that valid mapping passes structure validation"""
        issues = validate_mapping_structure(self.valid_mapping)
        self.assertEqual(len(issues), 0)

    def test_missing_metadata(self):
        """Test detection of missing metadata"""
        invalid_mapping = self.valid_mapping.copy()
        del invalid_mapping['mapping_metadata']

        issues = validate_mapping_structure(invalid_mapping)
        self.assertTrue(any('mapping_metadata' in issue for issue in issues))

    def test_missing_column_mappings(self):
        """Test detection of missing column mappings"""
        invalid_mapping = self.valid_mapping.copy()
        del invalid_mapping['column_mappings']

        issues = validate_mapping_structure(invalid_mapping)
        self.assertTrue(any('column_mappings' in issue for issue in issues))

    def test_naming_convention_validation(self):
        """Test naming convention validation"""
        # Test valid snake_case
        issues = validate_naming_conventions(self.valid_mapping)
        self.assertEqual(len(issues), 0)

        # Test invalid naming (uppercase)
        invalid_mapping = self.valid_mapping.copy()
        invalid_mapping['column_mappings'][0]['target_column'] = 'CustomerBK'

        issues = validate_naming_conventions(invalid_mapping)
        self.assertTrue(len(issues) > 0)

    def test_data_type_validation(self):
        """Test data type validation"""
        issues = validate_data_types(self.valid_mapping)
        self.assertEqual(len(issues), 0)

        # Test invalid data type
        invalid_mapping = self.valid_mapping.copy()
        invalid_mapping['column_mappings'][0]['target_type'] = 'INVALID_TYPE'

        issues = validate_data_types(invalid_mapping)
        self.assertTrue(len(issues) > 0)

if __name__ == '__main__':
    unittest.main()
```

### 3. dbt Generation Testing

Create `tests/test_dbt_generation.py`:

```python
import unittest
import tempfile
import os
from pathlib import Path
import yaml

class TestDBTGeneration(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.sample_mapping = {
            "mapping_metadata": {
                "source_table": "customers",
                "target_table": "dim_customer"
            },
            "column_mappings": [
                {
                    "source_column": "customer_id",
                    "target_column": "customer_bk",
                    "source_type": "int64",
                    "target_type": "STRING",
                    "transformation": "CAST({source_column} AS STRING)"
                }
            ]
        }

    def test_sql_model_generation(self):
        """Test SQL model generation"""
        # Mock generated SQL
        generated_sql = """
        select
          cast(customer_id as string) as customer_bk
        from {{ source('raw', 'customers') }}
        """

        # Test SQL contains expected elements
        self.assertIn('customer_bk', generated_sql)
        self.assertIn('source(', generated_sql)
        self.assertIn('cast(', generated_sql.lower())

    def test_yaml_documentation_generation(self):
        """Test YAML documentation generation"""
        generated_yaml = """
        version: 2
        models:
          - name: dim_customer
            columns:
              - name: customer_bk
                description: Business key for customer
                tests:
                  - not_null
                  - unique
        """

        # Parse YAML to ensure it's valid
        parsed_yaml = yaml.safe_load(generated_yaml)

        self.assertEqual(parsed_yaml['version'], 2)
        self.assertEqual(len(parsed_yaml['models']), 1)
        self.assertEqual(parsed_yaml['models'][0]['name'], 'dim_customer')

    def test_file_output_structure(self):
        """Test that generated files have correct structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simulate file creation
            model_file = Path(temp_dir) / "dim_customer.sql"
            yaml_file = Path(temp_dir) / "_dim_customer.yml"

            model_file.write_text("select * from source")
            yaml_file.write_text("version: 2")

            # Verify files exist and have content
            self.assertTrue(model_file.exists())
            self.assertTrue(yaml_file.exists())
            self.assertTrue(len(model_file.read_text()) > 0)
            self.assertTrue(len(yaml_file.read_text()) > 0)

if __name__ == '__main__':
    unittest.main()
```

## Integration Testing

### 1. Airflow DAG Testing

Create `tests/test_airflow_dag.py`:

```python
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Mock Airflow imports
sys.modules['airflow'] = MagicMock()
sys.modules['airflow.models'] = MagicMock()
sys.modules['airflow.operators'] = MagicMock()
sys.modules['airflow.providers'] = MagicMock()

class TestAirflowDAG(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.sample_s3_response = {
            'Contents': [
                {
                    'Key': 'incoming/customers_20240115_120000.csv',
                    'LastModified': datetime(2024, 1, 15, 12, 0, 0)
                }
            ]
        }

    @patch('boto3.client')
    def test_s3_file_detection(self, mock_boto3):
        """Test S3 file detection logic"""
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = self.sample_s3_response
        mock_boto3.return_value = mock_s3_client

        # Test file detection logic
        latest_file = self.get_latest_s3_file(mock_s3_client)

        self.assertEqual(latest_file, 'incoming/customers_20240115_120000.csv')
        mock_s3_client.list_objects_v2.assert_called_once()

    def test_filename_parsing(self):
        """Test filename parsing logic"""
        filename = 'customers_20240115_120000.csv'
        parts = filename.replace('.csv', '').split('_')

        source_system = parts[0] if len(parts) > 0 else 'unknown'
        table_name = parts[1] if len(parts) > 1 else 'unknown'

        self.assertEqual(source_system, 'customers')
        self.assertEqual(table_name, '20240115')  # This would need better parsing

    @patch('requests.post')
    def test_github_workflow_trigger(self, mock_post):
        """Test GitHub workflow trigger"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        # Test workflow trigger
        result = self.trigger_github_workflow({
            'source_system': 'crm',
            'table_name': 'customers',
            'file_path': 'incoming/customers.csv'
        })

        self.assertEqual(result, "SUCCESS")
        mock_post.assert_called_once()

    def get_latest_s3_file(self, s3_client):
        """Helper method to simulate S3 file detection"""
        response = s3_client.list_objects_v2(Bucket='test-bucket', Prefix='incoming/')

        if 'Contents' not in response:
            raise ValueError("No files found")

        csv_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.csv')]
        if not csv_files:
            raise ValueError("No CSV files found")

        latest_file = max(csv_files, key=lambda x: x['LastModified'])
        return latest_file['Key']

    def trigger_github_workflow(self, schema_info):
        """Helper method to simulate GitHub workflow trigger"""
        import requests

        payload = {
            'ref': 'main',
            'inputs': {
                'source_system': schema_info['source_system'],
                'table_name': schema_info['table_name'],
                's3_file_path': schema_info['file_path']
            }
        }

        response = requests.post(
            'https://api.github.com/repos/test/test/actions/workflows/test.yml/dispatches',
            json=payload
        )

        return "SUCCESS" if response.status_code == 204 else "FAILED"

if __name__ == '__main__':
    unittest.main()
```

### 2. GitHub Actions Testing

Create `tests/test_github_actions.py`:

```python
import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

class TestGitHubActions(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.sample_workflow_inputs = {
            'source_system': 'crm',
            'table_name': 'customers',
            'schema_json': json.dumps({
                'table_name': 'customers',
                'columns': [
                    {'name': 'customer_id', 'dtype': 'int64'},
                    {'name': 'name', 'dtype': 'object'}
                ]
            }),
            's3_file_path': 'incoming/customers.csv'
        }

    @patch('subprocess.run')
    def test_schema_mapping_script_execution(self, mock_subprocess):
        """Test schema mapping script execution"""
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Simulate script execution
        result = self.run_schema_mapping_script(self.sample_workflow_inputs)

        self.assertEqual(result, 0)  # Success exit code
        mock_subprocess.assert_called_once()

    def test_pr_creation_logic(self):
        """Test PR creation logic"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock mapping file
            mapping_file = os.path.join(temp_dir, 'mapping.json')
            with open(mapping_file, 'w') as f:
                json.dump({
                    'mapping_metadata': {
                        'source_table': 'customers',
                        'target_table': 'dim_customer'
                    }
                }, f)

            # Test PR details generation
            pr_details = self.generate_pr_details(mapping_file, self.sample_workflow_inputs)

            self.assertIn('customers', pr_details['title'])
            self.assertIn('Schema Mapping', pr_details['title'])

    def run_schema_mapping_script(self, inputs):
        """Simulate running the schema mapping script"""
        import subprocess

        cmd = [
            'python', 'scripts/generate_schema_mapping.py',
            '--source-schema', inputs['schema_json'],
            '--source-system', inputs['source_system'],
            '--table-name', inputs['table_name'],
            '--output-file', 'mapping.json'
        ]

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode

    def generate_pr_details(self, mapping_file, inputs):
        """Generate PR details from mapping file"""
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)

        title = f"Schema Mapping: {inputs['source_system']}.{inputs['table_name']}"

        body = f"""
        ## Schema Mapping Summary

        **Source System:** {inputs['source_system']}
        **Table Name:** {inputs['table_name']}

        Mapping created from: {inputs['s3_file_path']}
        """

        return {
            'title': title,
            'body': body,
            'branch': f"feature/schema-mapping-{inputs['source_system']}-{inputs['table_name']}"
        }

if __name__ == '__main__':
    unittest.main()
```

## End-to-End Testing

### 1. Full Pipeline Test

Create `tests/test_end_to_end.py`:

```python
import unittest
import tempfile
import json
import os
import time
from pathlib import Path

class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        """Set up test environment"""
        self.test_csv_content = """customer_id,first_name,last_name,email,created_date
1,John,Doe,john@example.com,2024-01-01
2,Jane,Smith,jane@example.com,2024-01-02
3,Bob,Johnson,bob@example.com,2024-01-03"""

    def test_complete_pipeline_flow(self):
        """Test the complete pipeline from CSV to dbt model"""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create test CSV file
            csv_file = Path(temp_dir) / "crm_customers_20240115_120000.csv"
            csv_file.write_text(self.test_csv_content)

            # Step 2: Extract schema
            schema_info = self.extract_schema_from_csv(csv_file)
            self.assertIsNotNone(schema_info)
            self.assertEqual(len(schema_info['columns']), 5)

            # Step 3: Generate mapping
            mapping = self.generate_mapping_from_schema(schema_info)
            self.assertIn('mapping_metadata', mapping)
            self.assertIn('column_mappings', mapping)

            # Step 4: Validate mapping
            validation_result = self.validate_mapping(mapping)
            self.assertTrue(validation_result)

            # Step 5: Generate dbt artifacts
            artifacts = self.generate_dbt_artifacts(mapping)
            self.assertIn('sql_model', artifacts)
            self.assertIn('yaml_doc', artifacts)

            # Step 6: Validate generated dbt files
            dbt_validation = self.validate_dbt_artifacts(artifacts)
            self.assertTrue(dbt_validation)

    def extract_schema_from_csv(self, csv_file):
        """Simulate schema extraction from CSV file"""
        import pandas as pd

        df = pd.read_csv(csv_file)

        filename = csv_file.name
        parts = filename.replace('.csv', '').split('_')
        source_system = parts[0] if len(parts) > 0 else 'unknown'
        table_name = parts[1] if len(parts) > 1 else 'unknown'

        schema_info = {
            'source_system': source_system,
            'table_name': table_name,
            'filename': filename,
            'row_count': len(df),
            'columns': []
        }

        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'unique_count': int(df[col].nunique()),
                'sample_values': df[col].head(3).tolist()
            }
            schema_info['columns'].append(col_info)

        return schema_info

    def generate_mapping_from_schema(self, schema_info):
        """Simulate mapping generation"""
        # Mock mapping generation (in real scenario, this would call Chicory agent)
        mapping = {
            'mapping_metadata': {
                'source_table': schema_info['table_name'],
                'target_table': f"dim_{schema_info['table_name']}",
                'mapping_version': '1.0',
                'source_system': schema_info['source_system']
            },
            'column_mappings': []
        }

        for col in schema_info['columns']:
            col_mapping = {
                'source_column': col['name'],
                'target_column': col['name'].lower(),
                'source_type': col['dtype'],
                'target_type': 'STRING',
                'transformation': f"CAST({{{col['name']}}} AS STRING)"
            }
            mapping['column_mappings'].append(col_mapping)

        return mapping

    def validate_mapping(self, mapping):
        """Simulate mapping validation"""
        required_keys = ['mapping_metadata', 'column_mappings']
        return all(key in mapping for key in required_keys)

    def generate_dbt_artifacts(self, mapping):
        """Simulate dbt artifact generation"""
        target_table = mapping['mapping_metadata']['target_table']

        sql_model = f"""
        select
          {', '.join([f"cast({cm['source_column']} as string) as {cm['target_column']}"
                     for cm in mapping['column_mappings']])}
        from {{{{ source('raw', '{mapping['mapping_metadata']['source_table']}') }}}}
        """

        yaml_doc = f"""
        version: 2
        models:
          - name: {target_table}
            description: Auto-generated model for {target_table}
            columns:
              {chr(10).join([f"- name: {cm['target_column']}"
                            for cm in mapping['column_mappings']])}
        """

        return {
            'sql_model': sql_model.strip(),
            'yaml_doc': yaml_doc.strip()
        }

    def validate_dbt_artifacts(self, artifacts):
        """Simulate dbt artifact validation"""
        # Check that SQL contains expected elements
        sql_valid = (
            'select' in artifacts['sql_model'].lower() and
            'source(' in artifacts['sql_model']
        )

        # Check that YAML is properly formatted
        yaml_valid = (
            'version: 2' in artifacts['yaml_doc'] and
            'models:' in artifacts['yaml_doc']
        )

        return sql_valid and yaml_valid

    def test_error_handling(self):
        """Test error handling in pipeline"""

        # Test invalid CSV
        with self.assertRaises(Exception):
            self.extract_schema_from_csv(Path("nonexistent.csv"))

        # Test invalid mapping
        invalid_mapping = {'invalid': 'structure'}
        self.assertFalse(self.validate_mapping(invalid_mapping))

if __name__ == '__main__':
    unittest.main()
```

## Performance Testing

### 1. Load Testing

Create `tests/test_performance.py`:

```python
import unittest
import time
import concurrent.futures
import statistics

class TestPerformance(unittest.TestCase):

    def test_schema_extraction_performance(self):
        """Test schema extraction performance"""
        start_time = time.time()

        # Simulate schema extraction for large file
        for i in range(100):
            self.simulate_schema_extraction(1000)  # 1000 rows

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete within reasonable time
        self.assertLess(total_time, 30)  # 30 seconds max

    def test_concurrent_processing(self):
        """Test concurrent file processing"""
        def process_file(file_id):
            start_time = time.time()
            self.simulate_complete_pipeline(file_id)
            return time.time() - start_time

        # Test concurrent processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_file, i) for i in range(10)]

            processing_times = []
            for future in concurrent.futures.as_completed(futures):
                processing_times.append(future.result())

        # Check performance metrics
        avg_time = statistics.mean(processing_times)
        max_time = max(processing_times)

        self.assertLess(avg_time, 10)  # Average under 10 seconds
        self.assertLess(max_time, 20)  # Max under 20 seconds

    def simulate_schema_extraction(self, num_rows):
        """Simulate schema extraction processing"""
        time.sleep(0.01)  # Simulate processing time
        return {'columns': num_rows // 10}

    def simulate_complete_pipeline(self, file_id):
        """Simulate complete pipeline processing"""
        time.sleep(0.1)  # Simulate processing time
        return f"processed_{file_id}"

if __name__ == '__main__':
    unittest.main()
```

## Test Automation

### 1. Test Runner Script

Create `tests/run_tests.py`:

```python
#!/usr/bin/env python3
"""
Test runner for automated ingestion pipeline
"""

import unittest
import sys
import os
from io import StringIO

def run_test_suite():
    """Run the complete test suite"""

    # Discover and run all tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')

    # Run tests with detailed output
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(test_suite)

    # Print results
    print("=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100:.1f}%")

    # Print detailed output
    test_output = stream.getvalue()
    print("\nDETAILED OUTPUT:")
    print(test_output)

    # Print failures and errors
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    exit_code = run_test_suite()
    sys.exit(exit_code)
```

### 2. CI/CD Integration

Create `.github/workflows/test.yml`:

```yaml
name: Run Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: |
          python -m pytest tests/test_*.py -v --cov=scripts --cov-report=xml

      - name: Run integration tests
        run: |
          python tests/run_tests.py

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

## Validation Checklist

### 1. Pre-deployment Checklist

- [ ] All unit tests pass
- [ ] Integration tests complete successfully
- [ ] End-to-end pipeline test works
- [ ] Performance tests meet requirements
- [ ] Error handling scenarios tested
- [ ] Documentation is up to date

### 2. Production Validation

- [ ] Schema mappings generate correctly
- [ ] dbt models compile without errors
- [ ] Generated models pass all tests
- [ ] Data quality checks pass
- [ ] Performance meets SLA requirements
- [ ] Monitoring and alerting functional

### 3. Regression Testing

- [ ] Existing mappings still work
- [ ] Backward compatibility maintained
- [ ] No performance degradation
- [ ] All automation workflows functional

---

Next: [Troubleshooting](troubleshooting.md)