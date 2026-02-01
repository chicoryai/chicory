import os

def load_config():
    return {
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "DRY_RUN": os.getenv("DRY_RUN", "False"),
        "PROJECT": os.getenv("PROJECT"),
        "HOME_PATH": os.getenv("HOME_PATH", "/app"),
        "BASE_DIR": os.getenv("BASE_DIR", "./data"),
        "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "DISABLE_DATABRICKS_SCANNING": os.getenv("DISABLE_DATABRICKS_SCANNING", "False"),
        "DISABLE_ORACLE_SCANNING": os.getenv("DISABLE_ORACLE_SCANNING", "False"),
        "DISABLE_CONFLUENCE_SCANNING": os.getenv("DISABLE_CONFLUENCE_SCANNING", "False"),
        "DISABLE_GOOGLE_DOCS_SCANNING": os.getenv("DISABLE_GOOGLE_DOCS_SCANNING", "False"),
        "DISABLE_GITHUB_SCANNING": os.getenv("DISABLE_GITHUB_SCANNING", "False"),
        "DISABLE_WEB_SCRAPING": os.getenv("DISABLE_WEB_SCRAPING", "False"),
        "DISABLE_SNOWFLAKE_SCANNING": os.getenv("DISABLE_SNOWFLAKE_SCANNING", "False"),
        "DISABLE_WEBFETCH_SCANNING": os.getenv("DISABLE_WEBFETCH_SCANNING", "False"),
    }
