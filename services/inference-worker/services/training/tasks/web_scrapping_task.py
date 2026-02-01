from services.customer.personalization import get_project_config
from services.utils.tools import save_to_txt, CustomBeautifulSoupTransformer, url_loader_chrom
from services.utils.logger import logger


async def run(config):
    logger.info("Analysing...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    url_list = project_config["url_list"]
    if url_list:
        try:
            logger.info(f"Processing url_list: {project_config['url_list']}")
            faq_docs = await url_loader_chrom(url_list)
            bs_transformer = CustomBeautifulSoupTransformer()
            docs_transformed = bs_transformer.transform_documents(faq_docs)
            dest = f'{base_dir}/{project}/raw/documents/url'
            # writing to disk
            for docs in docs_transformed:
                if isinstance(docs, list):
                    url = docs[0].metadata["source"]
                    for doc in docs:
                        # Add line breaks for readability
                        save_to_txt(url, doc.page_content, dest)
                else:
                    save_to_txt(docs.metadata["source"], docs.page_content, dest)

            logger.info(f"Scanning url completed with project: {project}")
        except Exception as e:
            logger.error(f"Scanning web urls failed for: {project}")
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
    else:
        logger.info(f"No url list: {url_list}")
