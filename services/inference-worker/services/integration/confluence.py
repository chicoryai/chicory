import os
import requests
import base64

from services.utils.logger import logger


def download_space(space_key, api_token=None, email=None, base_url=None, output_dir=None):
    """
    Downloads all pages from a Confluence space and saves them as HTML files.

    Args:
        space_key (str): Key of the Confluence space to download.
        api_token (str): API token for authentication.
        email (str): Email associated with the API token.
        base_url (str): Base URL of the Confluence instance.
        output_dir (str): Directory to save the downloaded pages.
    """
    if not (space_key and api_token and email and base_url and output_dir):
        raise ValueError("All parameters (space_key, api_token, email, base_url, output_dir) must be provided.")

    os.makedirs(output_dir, exist_ok=True)

    # Set up authentication headers
    auth_header = f"Basic {base64.b64encode(f'{email}:{api_token}'.encode()).decode()}"
    headers = {
        "Accept": "application/json",
        "Authorization": auth_header
    }

    try:
        # Pagination variables
        start = 0
        limit = 100
        has_more_results = True

        while has_more_results:
            # Get a batch of pages
            response = requests.get(
                f"{base_url}/rest/api/space/{space_key}/content?limit={limit}&start={start}",
                headers=headers
            )
            response.raise_for_status()  # Raise exception for HTTP errors
            data = response.json()

            # Process each page
            if 'page' in data:
                pages = data['page']
            else:
                pages = data
            for page in pages.get('results', []):
                page_id = page['id']
                page_title = page['title'].replace('/', '_').replace('\\', '_').replace(':',
                                                                                        '_')  # Handle special characters
                logger.info(f"Downloading page: {page_title} (ID: {page_id})")

                # Get the page content
                content_response = requests.get(
                    f"{base_url}/rest/api/content/{page_id}?expand=body.storage",
                    headers=headers
                )
                content_response.raise_for_status()
                content_data = content_response.json()
                page_content = content_data['body']['storage']['value']

                # Save to file
                file_path = os.path.join(output_dir, f"{page_title}.html")
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(page_content)

            # Check if there are more results
            start += limit
            has_more_results = data.get('size', 0) > 0 and start < data.get('totalSize', 0)

        logger.info(f"Download complete! Files saved to: {output_dir}")

    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while downloading pages: {e}", exc_info=True)
    except Exception as ex:
        logger.error(f"An unexpected error occurred: {ex}", exc_info=True)
