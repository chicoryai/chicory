# S3 Bucket Setup

## Overview

This section covers setting up your S3 bucket infrastructure to support automated CSV ingestion monitoring. We'll configure the bucket structure, IAM permissions, and file organization patterns.

## S3 Bucket Configuration

### 1. Create S3 Bucket

```bash
# Create the main ingestion bucket
aws s3 mb s3://your-data-ingestion-bucket --region us-east-1

# Create folder structure
aws s3api put-object --bucket your-data-ingestion-bucket --key incoming/
aws s3api put-object --bucket your-data-ingestion-bucket --key processed/
aws s3api put-object --bucket your-data-ingestion-bucket --key failed/
```

### 2. Bucket Structure

```
your-data-ingestion-bucket/
├── incoming/           # New CSV files land here
│   ├── customer_data/
│   ├── product_data/
│   └── transaction_data/
├── processed/          # Successfully processed files moved here
├── failed/            # Failed processing files moved here
└── schemas/           # Extracted schemas stored here
```

### 3. Lifecycle Policy

Create a lifecycle policy to manage storage costs:

```json
{
    "Rules": [
        {
            "ID": "IngestionLifecycle",
            "Status": "Enabled",
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"
                }
            ],
            "Filter": {
                "Prefix": "processed/"
            }
        }
    ]
}
```

## IAM Configuration

### 1. Airflow Service Role

Create an IAM role for Airflow to access S3:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-data-ingestion-bucket",
                "arn:aws:s3:::your-data-ingestion-bucket/*"
            ]
        }
    ]
}
```

### 2. Trust Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "composer.googleapis.com",
                    "ec2.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

## File Naming Convention

Establish a consistent naming convention for uploaded files:

```
{source_system}_{table_name}_{YYYYMMDD}_{HHMMSS}.csv

Examples:
- salesforce_accounts_20240115_143022.csv
- shopify_orders_20240115_143125.csv
- crm_contacts_20240115_143230.csv
```

## S3 Event Notifications (Optional)

For immediate processing, set up S3 event notifications:

```json
{
    "CloudWatchConfiguration": {
        "CloudWatchConfiguration": {
            "LogGroupName": "/aws/s3/ingestion-bucket"
        }
    },
    "TopicConfigurations": [
        {
            "Id": "NewFileNotification",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:new-file-topic",
            "Events": [
                "s3:ObjectCreated:*"
            ],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {
                            "Name": "prefix",
                            "Value": "incoming/"
                        },
                        {
                            "Name": "suffix",
                            "Value": ".csv"
                        }
                    ]
                }
            }
        }
    ]
}
```

## Environment Variables

Set up environment variables for your Airflow deployment:

```bash
# Airflow Variables
export AWS_S3_BUCKET="your-data-ingestion-bucket"
export AWS_REGION="us-east-1"
export GITHUB_TOKEN="your_github_token"
export GITHUB_REPO="your-org/your-dbt-repo"
export CHICORY_API_KEY="your_chicory_api_key"
```

## Testing S3 Setup

Upload a test file to verify the setup:

```bash
# Create a sample CSV
echo "id,name,email,created_date" > test_customers_20240115_120000.csv
echo "1,John Doe,john@example.com,2024-01-15" >> test_customers_20240115_120000.csv

# Upload to S3
aws s3 cp test_customers_20240115_120000.csv s3://your-data-ingestion-bucket/incoming/

# Verify upload
aws s3 ls s3://your-data-ingestion-bucket/incoming/
```

## Security Best Practices

1. **Enable Server-Side Encryption**:
   ```bash
   aws s3api put-bucket-encryption \
     --bucket your-data-ingestion-bucket \
     --server-side-encryption-configuration '{
       "Rules": [
         {
           "ApplyServerSideEncryptionByDefault": {
             "SSEAlgorithm": "AES256"
           }
         }
       ]
     }'
   ```

2. **Enable Access Logging**:
   ```bash
   aws s3api put-bucket-logging \
     --bucket your-data-ingestion-bucket \
     --bucket-logging-status '{
       "LoggingEnabled": {
         "TargetBucket": "your-logging-bucket",
         "TargetPrefix": "access-logs/"
       }
     }'
   ```

3. **Block Public Access**:
   ```bash
   aws s3api put-public-access-block \
     --bucket your-data-ingestion-bucket \
     --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
   ```

---

Next: [Airflow DAG Configuration](airflow-dag-configuration.md)