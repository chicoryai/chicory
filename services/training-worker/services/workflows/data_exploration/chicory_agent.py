import os

from services.utils.tools import fetch_url_list_from_file


class ChicoryProjectConfig:
    def __init__(self, project, data_path = None, url_list_path = None, runbook_directory = None, work_directory = None):

        HOME_PATH = os.getenv("HOME_PATH", "/home/ubuntu/brewsearch")
        # Defaults
        self.code_docs_path = f"{HOME_PATH}/data/{project}/raw/code"
        self.tbls_docs_path = f"{HOME_PATH}/data/{project}/preprocessed/data"
        self.data_path = f"{HOME_PATH}/data/{project}/raw/data"
        self.persist_directory = f"{HOME_PATH}/data/{project}/vector.db"
        self.schema_file_path = f"{HOME_PATH}/data/{project}/preprocessed/data/schema.json.txt"
        self.metadata_file_path = f"{HOME_PATH}/data/{project}/preprocessed/data/metadata.json.txt"
        self.relation_file_path = f"{HOME_PATH}/data/{project}/preprocessed/data/relation.json.txt"
        self.data_source = f"{HOME_PATH}/data/{project}/raw/data/database.sqlite"
        self.graph_rag_source = f"{HOME_PATH}/data/{project}/graphrag/output"
        self.api_directory = f"{HOME_PATH}/data/{project}/raw/api"
        self.work_directory = f"{HOME_PATH}/data/{project}/wd"
        self.runbook_directory = f"{HOME_PATH}/data/{project}/raw/documents/runbooks"
        self.catalog = f"{HOME_PATH}/data/{project}/wd/{project}_catalog.csv"
        self.url_list = []

        # custom
        if data_path:
            self.data_path = data_path
        if url_list_path:
            self.url_list = fetch_url_list_from_file(url_list_path)
        if runbook_directory:
            self.runbook_directory = runbook_directory
        if work_directory:
            self.work_directory = work_directory


class ChicoryProjectTask:
    def __init__(self, query, agent_description, runbook_dir, user_hints, response_template):
        self.query = query
        self.agent_description = agent_description
        self.runbook_dir = runbook_dir
        self.user_hints = user_hints
        self.response_template = response_template


class ChicoryAgent:
    def __init__(self, agent, project, task):
        self.agent = agent  # string
        self.project = project  # project name (string)
        self.config = ChicoryProjectConfig(project)  # auto builds config from project
        self.task = task  # ChicoryProjectTask object

    def __repr__(self):
        return f"<ChicoryProject agent={self.agent}>"
