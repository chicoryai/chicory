import os

from services.customer.personalization import get_project_config
from services.integration.google_docs import download_file, authenticate_service_account, \
    list_all_accessible_items
from services.utils.logger import logger


def run(config):
    logger.info("Analysing...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.info("Project NOT supported yet!")
        return None

    google_sa_pvt_key_id = os.getenv(f"{project.upper()}_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID", os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID", None))
    google_sa_pvt_key = os.getenv(f"{project.upper()}_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", "")).replace("\\n", "\n")
    google_sa_client_id = os.getenv(f"{project.upper()}_GOOGLE_SERVICE_ACCOUNT_CLIENT_ID", os.getenv("GOOGLE_SERVICE_ACCOUNT_CLIENT_ID", None))
    google_sa_client_email = os.getenv(f"{project.upper()}_GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL", os.getenv("GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL", None))
    google_sa_client_cert_url = os.getenv(f"{project.upper()}_GOOGLE_SERVICE_ACCOUNT_CLIENT_CERT_URL", os.getenv("GOOGLE_SERVICE_ACCOUNT_CLIENT_CERT_URL", None))
    google_project_id = os.getenv(f"{project.upper()}_GOOGLE_PROJECT_ID", os.getenv("GOOGLE_PROJECT_ID", None))
    google_folder_id = os.getenv(f"{project.upper()}_GOOGLE_FOLDER", os.getenv("GOOGLE_FOLDER", None))

    if google_project_id and google_sa_pvt_key_id and google_sa_pvt_key and google_sa_client_email and \
                                 google_sa_client_id and google_sa_client_cert_url and google_folder_id:
        try:
            save_path = os.path.join(base_dir, project, "raw", "documents", "google_docs")
            os.makedirs(save_path, exist_ok=True) # making sure the path exists

            service = authenticate_service_account(google_project_id, google_sa_pvt_key_id, google_sa_pvt_key, google_sa_client_email,
                                 google_sa_client_id, google_sa_client_cert_url)

            # List files in the folder
            # files = list_files_recursive(service, google_folder_id)
            files = list_all_accessible_items(service)
            if not files:
                logger.info("No files found in the specified folder.")
                return

            logger.info("Files in folder:")
            for file in files:
                logger.info(f"- {file['name']} (ID: {file['id']})")

            # Download each file
            for file in files:
                download_file(service, file['id'], file['name'], save_path)
            logger.info(f"Scanning google docs completed with project: {project}")
        except Exception as e:
            logger.error(f"Scanning google docs failed for: {project}")
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
    else:
        logger.info(f"No Google Project Integration Found!")
