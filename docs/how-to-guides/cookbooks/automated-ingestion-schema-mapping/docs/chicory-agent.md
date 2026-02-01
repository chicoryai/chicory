# Chicory Agent Creation

## Overview

This section covers creating and configuring Chicory AI agents for automated schema mapping and dbt model generation. We'll create two specialized agents:
1. **Schema Mapping Agent**: Maps source CSV schemas to target data models
2. **dbt Generation Agent**: Creates dbt models and YAML documentation

## Schema Mapping Agent

### 1. Agent Configuration

Create the schema mapping agent with the following configuration:

```json
{
  "agent_name": "schema_mapper_agent",
  "description": "Maps source CSV schemas to target data warehouse schemas",
  "model": "gpt-4",
  "temperature": 0.1,
  "max_tokens": 2000,
  "instructions": "You are a data engineering expert specializing in schema mapping and data modeling. Your task is to analyze source CSV schemas and map them to standardized target schemas following dimensional modeling best practices.",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "generate_schema_mapping",
        "description": "Generate schema mapping between source CSV and target model",
        "parameters": {
          "type": "object",
          "properties": {
            "source_schema": {
              "type": "object",
              "description": "Source CSV schema information"
            },
            "target_standards": {
              "type": "object",
              "description": "Target schema standards and naming conventions"
            }
          },
          "required": ["source_schema", "target_standards"]
        }
      }
    }
  ],
  "system_prompt": "You are an expert data engineer with deep knowledge of:\n- Dimensional modeling (Kimball methodology)\n- Data warehouse design patterns\n- Schema normalization and denormalization\n- Data quality and governance\n- Industry-standard naming conventions\n\nWhen mapping schemas:\n1. Follow consistent naming conventions (snake_case)\n2. Identify primary keys and foreign key relationships\n3. Suggest appropriate data types for the target warehouse\n4. Flag potential data quality issues\n5. Recommend business keys and surrogate keys where appropriate\n6. Consider slowly changing dimensions (SCD) patterns\n7. Output structured mapping in JSON format"
}
```

### 2. Agent Deployment

Use the Chicory API to create the schema mapping agent:

```python
import requests
import json

def create_schema_mapping_agent():
    """Create and deploy the schema mapping agent"""

    chicory_api_key = "your_chicory_api_key"
    base_url = "https://api.chicory.ai/v1"

    headers = {
        "Authorization": f"Bearer {chicory_api_key}",
        "Content-Type": "application/json"
    }

    agent_config = {
        "name": "schema_mapper_agent",
        "description": "Maps source CSV schemas to target data warehouse schemas",
        "model": "gpt-4",
        "temperature": 0.1,
        "max_tokens": 2000,
        "system_prompt": """You are an expert data engineer specializing in schema mapping and data modeling.

TASK: Analyze the provided source CSV schema and generate a comprehensive mapping to a target data warehouse schema.

INPUT FORMAT:
- source_schema: JSON object containing column information, data types, and metadata
- target_standards: JSON object with naming conventions and target schema requirements

OUTPUT FORMAT:
Generate a JSON mapping object with the following structure:
{
  "mapping_metadata": {
    "source_table": "source_table_name",
    "target_table": "target_table_name",
    "mapping_version": "1.0",
    "created_at": "2024-01-15T10:30:00Z",
    "mapping_confidence": 0.95
  },
  "column_mappings": [
    {
      "source_column": "original_name",
      "target_column": "standardized_name",
      "source_type": "VARCHAR",
      "target_type": "STRING",
      "transformation": "UPPER(TRIM({source_column}))",
      "business_rules": ["Remove leading/trailing spaces", "Convert to uppercase"],
      "data_quality_checks": ["NOT NULL", "LENGTH > 0"],
      "semantic_type": "identifier",
      "is_primary_key": false,
      "is_foreign_key": false,
      "description": "Customer unique identifier"
    }
  ],
  "recommendations": {
    "primary_key_suggestion": "customer_sk",
    "indexing_recommendations": ["customer_id", "email"],
    "partitioning_suggestion": "created_date",
    "data_quality_concerns": ["High null rate in phone column"],
    "business_key_candidates": ["customer_id", "email"]
  },
  "target_schema": {
    "table_name": "dim_customer",
    "table_type": "dimension",
    "scd_type": 2,
    "columns": [...]
  }
}

GUIDELINES:
1. Use snake_case naming convention
2. Follow dimensional modeling best practices
3. Identify business vs. surrogate keys
4. Suggest appropriate SCD types
5. Flag data quality issues
6. Provide transformation logic where needed
7. Consider downstream analytics use cases"""
    }

    response = requests.post(
        f"{base_url}/agents",
        headers=headers,
        json=agent_config
    )

    if response.status_code == 201:
        agent_data = response.json()
        print(f"Schema mapping agent created: {agent_data['id']}")
        return agent_data
    else:
        raise Exception(f"Failed to create agent: {response.status_code} - {response.text}")

# Deploy the agent
schema_agent = create_schema_mapping_agent()
```

### 3. Schema Mapping Function

```python
def map_schema_with_chicory(source_schema, target_standards):
    """Use Chicory agent to map source schema to target schema"""

    chicory_api_key = "your_chicory_api_key"
    agent_id = schema_agent['id']
    base_url = "https://api.chicory.ai/v1"

    headers = {
        "Authorization": f"Bearer {chicory_api_key}",
        "Content-Type": "application/json"
    }

    # Prepare the mapping request
    mapping_request = {
        "messages": [
            {
                "role": "user",
                "content": f"""Please map the following source schema to our target standards:

SOURCE SCHEMA:
{json.dumps(source_schema, indent=2)}

TARGET STANDARDS:
{json.dumps(target_standards, indent=2)}

Generate a comprehensive schema mapping following the specified output format."""
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "generate_schema_mapping",
                    "description": "Generate comprehensive schema mapping",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mapping": {
                                "type": "object",
                                "description": "Complete schema mapping object"
                            }
                        }
                    }
                }
            }
        ]
    }

    # Call the agent
    response = requests.post(
        f"{base_url}/agents/{agent_id}/chat",
        headers=headers,
        json=mapping_request
    )

    if response.status_code == 200:
        result = response.json()

        # Extract mapping from agent response
        if 'tool_calls' in result['choices'][0]['message']:
            tool_call = result['choices'][0]['message']['tool_calls'][0]
            mapping_data = json.loads(tool_call['function']['arguments'])
            return mapping_data['mapping']
        else:
            # Parse from text response if no tool calls
            return parse_mapping_from_text(result['choices'][0]['message']['content'])
    else:
        raise Exception(f"Schema mapping failed: {response.status_code} - {response.text}")

def parse_mapping_from_text(text_response):
    """Extract JSON mapping from text response"""
    import re

    # Look for JSON blocks in the response
    json_match = re.search(r'```json\n(.*?)\n```', text_response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))

    raise ValueError("Could not parse JSON mapping from response")
```

## dbt Generation Agent

### 1. Agent Configuration

Create the dbt generation agent:

```python
def create_dbt_generation_agent():
    """Create agent for dbt model and YAML generation"""

    chicory_api_key = "your_chicory_api_key"
    base_url = "https://api.chicory.ai/v1"

    headers = {
        "Authorization": f"Bearer {chicory_api_key}",
        "Content-Type": "application/json"
    }

    agent_config = {
        "name": "dbt_generator_agent",
        "description": "Generates dbt models and YAML documentation from schema mappings",
        "model": "gpt-4",
        "temperature": 0.1,
        "max_tokens": 3000,
        "system_prompt": """You are an expert dbt developer with deep knowledge of:
- dbt best practices and conventions
- SQL optimization and performance
- Data modeling patterns
- Documentation and testing strategies
- Jinja templating and macros

TASK: Generate dbt model SQL and YAML documentation from schema mapping specifications.

INPUT: Schema mapping JSON with source-to-target column mappings and transformations

OUTPUT: Generate two components:
1. dbt model SQL file (.sql)
2. dbt model YAML documentation (.yml)

DBT MODEL REQUIREMENTS:
- Use proper dbt materialization (table, view, incremental)
- Include source references with proper syntax
- Apply transformations from mapping specification
- Use meaningful aliases and column ordering
- Include data quality tests where appropriate
- Follow dbt naming conventions
- Add appropriate Jinja macros for reusability

YAML DOCUMENTATION REQUIREMENTS:
- Complete model and column descriptions
- Data quality tests (not_null, unique, relationships, accepted_values)
- Column-level metadata and business context
- Source and model relationships
- Tags for categorization

Generate clean, production-ready dbt artifacts following best practices."""
    }

    response = requests.post(
        f"{base_url}/agents",
        headers=headers,
        json=agent_config
    )

    if response.status_code == 201:
        agent_data = response.json()
        print(f"dbt generation agent created: {agent_data['id']}")
        return agent_data
    else:
        raise Exception(f"Failed to create dbt agent: {response.status_code} - {response.text}")

# Deploy the dbt agent
dbt_agent = create_dbt_generation_agent()
```

### 2. dbt Generation Function

```python
def generate_dbt_artifacts(schema_mapping, dbt_project_config):
    """Generate dbt model and YAML using Chicory agent"""

    chicory_api_key = "your_chicory_api_key"
    agent_id = dbt_agent['id']
    base_url = "https://api.chicory.ai/v1"

    headers = {
        "Authorization": f"Bearer {chicory_api_key}",
        "Content-Type": "application/json"
    }

    # Prepare generation request
    generation_request = {
        "messages": [
            {
                "role": "user",
                "content": f"""Generate dbt model artifacts for the following schema mapping:

SCHEMA MAPPING:
{json.dumps(schema_mapping, indent=2)}

DBT PROJECT CONFIG:
{json.dumps(dbt_project_config, indent=2)}

Please generate:
1. Complete dbt model SQL file
2. Comprehensive YAML documentation
3. Any necessary macro or test files

Ensure the output follows dbt best practices and includes proper documentation, tests, and transformations."""
            }
        ]
    }

    response = requests.post(
        f"{base_url}/agents/{agent_id}/chat",
        headers=headers,
        json=generation_request
    )

    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']

        # Parse the generated artifacts
        artifacts = parse_dbt_artifacts(content)
        return artifacts
    else:
        raise Exception(f"dbt generation failed: {response.status_code} - {response.text}")

def parse_dbt_artifacts(content):
    """Extract dbt SQL and YAML from agent response"""
    import re

    artifacts = {}

    # Extract SQL model
    sql_match = re.search(r'```sql\n(.*?)\n```', content, re.DOTALL)
    if sql_match:
        artifacts['sql_model'] = sql_match.group(1).strip()

    # Extract YAML documentation
    yaml_match = re.search(r'```yaml\n(.*?)\n```', content, re.DOTALL)
    if yaml_match:
        artifacts['yaml_doc'] = yaml_match.group(1).strip()

    # Extract any additional artifacts
    macro_match = re.search(r'```macro\n(.*?)\n```', content, re.DOTALL)
    if macro_match:
        artifacts['macro'] = macro_match.group(1).strip()

    return artifacts
```

## Target Standards Configuration

Define your organization's target schema standards:

```python
target_standards = {
    "naming_conventions": {
        "table_prefix": {
            "dimension": "dim_",
            "fact": "fact_",
            "staging": "stg_",
            "intermediate": "int_"
        },
        "column_case": "snake_case",
        "reserved_suffixes": {
            "primary_key": "_sk",
            "business_key": "_bk",
            "foreign_key": "_fk",
            "date": "_date",
            "timestamp": "_ts",
            "flag": "_flag"
        }
    },
    "data_types": {
        "string_default": "STRING",
        "integer_default": "INTEGER",
        "decimal_default": "NUMERIC(15,2)",
        "date_default": "DATE",
        "timestamp_default": "TIMESTAMP",
        "boolean_default": "BOOLEAN"
    },
    "standard_columns": {
        "audit_columns": [
            {
                "name": "created_at",
                "type": "TIMESTAMP",
                "description": "Record creation timestamp"
            },
            {
                "name": "updated_at",
                "type": "TIMESTAMP",
                "description": "Record last update timestamp"
            },
            {
                "name": "is_active",
                "type": "BOOLEAN",
                "description": "Record active status flag"
            }
        ]
    },
    "data_quality_rules": {
        "required_tests": ["not_null", "unique"],
        "relationship_tests": ["relationships"],
        "custom_tests": ["positive_values", "valid_email"]
    }
}
```

## Testing Agents

### 1. Unit Testing

```python
def test_schema_mapping_agent():
    """Test schema mapping functionality"""

    # Sample source schema
    test_source_schema = {
        "source_system": "crm",
        "table_name": "customers",
        "columns": [
            {
                "name": "customer_id",
                "dtype": "int64",
                "semantic_type": "identifier"
            },
            {
                "name": "first_name",
                "dtype": "object",
                "semantic_type": "text"
            },
            {
                "name": "email",
                "dtype": "object",
                "semantic_type": "email"
            }
        ]
    }

    # Test mapping
    mapping_result = map_schema_with_chicory(test_source_schema, target_standards)

    # Validate mapping structure
    assert 'mapping_metadata' in mapping_result
    assert 'column_mappings' in mapping_result
    assert 'recommendations' in mapping_result

    print("Schema mapping test passed ✓")

def test_dbt_generation_agent():
    """Test dbt generation functionality"""

    # Sample mapping result
    test_mapping = {
        "mapping_metadata": {
            "source_table": "crm_customers",
            "target_table": "dim_customer"
        },
        "column_mappings": [
            {
                "source_column": "customer_id",
                "target_column": "customer_bk",
                "transformation": "CAST({source_column} AS STRING)"
            }
        ]
    }

    dbt_config = {
        "project_name": "analytics_dbt",
        "materialization": "table",
        "source_name": "raw_data"
    }

    # Test generation
    artifacts = generate_dbt_artifacts(test_mapping, dbt_config)

    # Validate artifacts
    assert 'sql_model' in artifacts
    assert 'yaml_doc' in artifacts

    print("dbt generation test passed ✓")

# Run tests
if __name__ == "__main__":
    test_schema_mapping_agent()
    test_dbt_generation_agent()
```

### 2. Integration Testing

```python
def test_end_to_end_pipeline():
    """Test complete schema mapping and dbt generation pipeline"""

    # Simulate S3 schema extraction result
    extracted_schema = extract_test_schema()

    # Map schema
    mapping = map_schema_with_chicory(extracted_schema, target_standards)

    # Generate dbt artifacts
    artifacts = generate_dbt_artifacts(mapping, dbt_project_config)

    # Validate end-to-end result
    assert mapping is not None
    assert artifacts['sql_model'] is not None
    assert artifacts['yaml_doc'] is not None

    print("End-to-end pipeline test passed ✓")
```

## Agent Monitoring

### 1. Performance Metrics

```python
def track_agent_performance():
    """Monitor agent performance metrics"""

    metrics = {
        "schema_mapping": {
            "avg_response_time": 0,
            "success_rate": 0,
            "accuracy_score": 0
        },
        "dbt_generation": {
            "avg_response_time": 0,
            "success_rate": 0,
            "compilation_success": 0
        }
    }

    # Implement metrics collection
    # Send to monitoring system (CloudWatch, DataDog, etc.)
```

### 2. Quality Validation

```python
def validate_generated_artifacts(artifacts):
    """Validate quality of generated dbt artifacts"""

    validations = {
        "sql_syntax": False,
        "dbt_compilation": False,
        "yaml_structure": False,
        "test_coverage": False
    }

    # Implement validation logic
    return validations
```

---

Next: [GitHub Actions Workflow](github-actions-workflow.md)