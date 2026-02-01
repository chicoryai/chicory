const ICON_MAP: Record<string, string> = {
  airflow: "/icons/airflow.svg",
  anthropic: "/icons/anthropic.png",
  azure_blob_storage: "/icons/azure_blob_storage.svg",
  "azure-blob-storage": "/icons/azure_blob_storage.svg",
  azure_data_factory: "/icons/azure_data_factory.svg",
  "azure-data-factory": "/icons/azure_data_factory.svg",
  bigquery: "/icons/bigquery.svg",
  "code-file-upload": "/icons/code_file_upload.svg",
  code_file_upload: "/icons/code_file_upload.svg",
  "csv-upload": "/icons/csv_upload.svg",
  csv_upload: "/icons/csv_upload.svg",
  databricks: "/icons/databricks.svg",
  datahub: "/icons/datahub.svg",
  dbt: "/icons/dbt.svg",
  "direct-upload": "/icons/direct_upload.svg",
  direct_upload: "/icons/direct_upload.svg",
  "generic-file-upload": "/icons/generic_file_upload.svg",
  generic_file_upload: "/icons/generic_file_upload.svg",
  "generic-integration": "/icons/generic-integration.svg",
  github: "/icons/github.svg",
  glue: "/icons/glue.svg",
  aws_glue: "/icons/glue.svg",
  "aws-glue": "/icons/glue.svg",
  "google-drive": "/icons/google_drive.svg",
  google_drive: "/icons/google_drive.svg",
  looker: "/icons/looker.svg",
  redash: "/icons/redash.svg",
  redshift: "/icons/redshift.svg",
  s3: "/icons/s3.png",
  aws_s3: "/icons/s3.png",
  "aws-s3": "/icons/s3.png",
  snowflake: "/icons/snowflake.svg",
  "xlsx-upload": "/icons/xlsx_upload.svg",
  xlsx_upload: "/icons/xlsx_upload.svg",
  mcp: "/icons/generic-integration.svg",
  jira: "/icons/jira.svg"
};

const DEFAULT_ICON = ICON_MAP["generic-integration"];

export function resolveIntegrationIcon(...values: Array<string | null | undefined>) {
  for (const value of values) {
    if (!value) continue;
    if (value.startsWith("/")) {
      return value;
    }

    const trimmed = value.trim().toLowerCase();
    if (ICON_MAP[trimmed]) {
      return ICON_MAP[trimmed];
    }

    const slug = trimmed.replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
    if (slug && ICON_MAP[slug]) {
      return ICON_MAP[slug];
    }

    const snake = trimmed.replace(/[^a-z0-9]+/g, "_").replace(/(^_|_$)/g, "");
    if (snake && ICON_MAP[snake]) {
      return ICON_MAP[snake];
    }
  }

  return DEFAULT_ICON;
}

export const integrationIconMap = ICON_MAP;
