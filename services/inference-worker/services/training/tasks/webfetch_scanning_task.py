import os
import hashlib
import asyncio
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

from services.utils.logger import logger

FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v1"

# Default timeouts in seconds (can be overridden via env vars)
DEFAULT_CRAWL_TIMEOUT = 600  # 10 minutes
DEFAULT_SCRAPE_TIMEOUT = 120  # 2 minutes

# Polling configuration
DEFAULT_POLL_INTERVAL = 5
DEFAULT_MAX_CONSECUTIVE_ERRORS = 10

# Log truncation
MAX_LOG_RESPONSE_LENGTH = 200


def escape_yaml_string(value: str) -> str:
    """
    Escape a string for safe inclusion in YAML front matter.
    Handles all YAML special characters that could break parsing or cause injection.

    Uses double-quoted YAML string escaping rules.
    """
    if not value:
        return ""

    # Replace problematic characters for double-quoted YAML strings
    value = value.replace('\\', '\\\\')  # Escape backslashes first
    value = value.replace('"', '\\"')     # Escape double quotes
    value = value.replace('\n', '\\n')    # Escape newlines (preserve as escape sequence)
    value = value.replace('\r', '\\r')    # Escape carriage returns
    value = value.replace('\t', '\\t')    # Escape tabs
    value = value.replace('\0', '')       # Remove null bytes

    # Handle other control characters
    result = []
    for char in value:
        if ord(char) < 32 and char not in '\n\r\t':
            # Replace other control characters with space
            result.append(' ')
        else:
            result.append(char)

    return ''.join(result)


async def run(config: Dict[str, Any], data_sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Execute web fetching for all webfetch data sources.
    Called during training/scan workflow.

    Args:
        config: Training configuration dictionary
        data_sources: Optional list of data source configurations (if not using env vars)

    Returns:
        Dict with results of all webfetch operations
    """
    logger.info("Starting webfetch scanning task...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    # Get webfetch configuration from environment variables
    project_upper = project.upper()

    results = []

    # Check for webfetch data sources passed directly or from environment variables
    if data_sources:
        webfetch_sources = [ds for ds in data_sources if ds.get("type") == "webfetch"]
        for ds in webfetch_sources:
            ds_config = ds.get("configuration", {})
            mode = ds_config.get("mode", "scrape")

            # Mode-specific URL validation
            if mode == "scrape" and not ds_config.get("url"):
                logger.error(f"Webfetch source {ds.get('id', 'unknown')}: scrape mode requires 'url' field")
                results.append({
                    "status": "error",
                    "ds_id": ds.get("id", "unknown"),
                    "error": "Scrape mode requires 'url' field"
                })
                continue
            elif mode == "crawl" and not ds_config.get("start_url"):
                logger.error(f"Webfetch source {ds.get('id', 'unknown')}: crawl mode requires 'start_url' field")
                results.append({
                    "status": "error",
                    "ds_id": ds.get("id", "unknown"),
                    "error": "Crawl mode requires 'start_url' field"
                })
                continue

            # Safely convert max_pages
            max_pages_raw = ds_config.get("max_pages", 100)
            try:
                max_pages = int(max_pages_raw) if max_pages_raw else 100
            except (ValueError, TypeError):
                logger.warning(f"Invalid max_pages value '{max_pages_raw}', using default 100")
                max_pages = 100

            result = await process_webfetch_source(
                api_key=ds_config.get("api_key"),
                mode=mode,
                url=ds_config.get("url"),
                start_url=ds_config.get("start_url"),
                max_pages=max_pages,
                base_dir=base_dir,
                project=project,
                ds_id=ds.get("id", "default")
            )
            results.append(result)
    else:
        # Check environment variables for webfetch configuration
        api_key = os.getenv(f"{project_upper}_WEBFETCH_API_KEY")
        mode = os.getenv(f"{project_upper}_WEBFETCH_MODE", "scrape")
        url = os.getenv(f"{project_upper}_WEBFETCH_URL")
        start_url = os.getenv(f"{project_upper}_WEBFETCH_START_URL")
        max_pages_str = os.getenv(f"{project_upper}_WEBFETCH_MAX_PAGES", "100")

        # Safely convert max_pages
        try:
            max_pages = int(max_pages_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_pages value '{max_pages_str}', using default 100")
            max_pages = 100

        if api_key and (url or start_url):
            result = await process_webfetch_source(
                api_key=api_key,
                mode=mode,
                url=url,
                start_url=start_url,
                max_pages=max_pages,
                base_dir=base_dir,
                project=project,
                ds_id="env"
            )
            results.append(result)
        else:
            logger.info("No webfetch configuration found, skipping...")

    logger.info(f"Webfetch scanning task completed with {len(results)} source(s)")
    return {"webfetch_results": results}


async def process_webfetch_source(
    api_key: str,
    mode: str,
    url: Optional[str],
    start_url: Optional[str],
    max_pages: int,
    base_dir: str,
    project: str,
    ds_id: str
) -> Dict[str, Any]:
    """
    Process a single webfetch data source.

    Args:
        api_key: Firecrawl API key
        mode: "scrape" or "crawl"
        url: URL for scrape mode
        start_url: Starting URL for crawl mode
        max_pages: Maximum pages to crawl
        base_dir: Base directory for storing files
        project: Project name
        ds_id: Data source ID

    Returns:
        Dict with processing result
    """
    try:
        if mode == "scrape":
            return await scrape_url(api_key, url, base_dir, project, ds_id)
        else:
            return await crawl_site(api_key, start_url, max_pages, base_dir, project, ds_id)
    except Exception as e:
        logger.error(f"Error processing webfetch source {ds_id}: {str(e)}", exc_info=True)
        return {"status": "error", "ds_id": ds_id, "error": str(e)}


def save_content_to_file(
    content: str,
    title: str,
    source_url: str,
    output_dir: Path,
    url_hash: str
) -> Optional[str]:
    """
    Save content to a markdown file with YAML front matter.

    Args:
        content: The markdown content to save
        title: Page title
        source_url: Source URL
        output_dir: Directory to save the file
        url_hash: Hash of the URL for filename

    Returns:
        File path if successful, None if failed
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{url_hash}.md"

        # Escape title and URL for YAML
        escaped_title = escape_yaml_string(title)
        escaped_url = escape_yaml_string(source_url)

        content_with_header = f'''---
title: "{escaped_title}"
source: "{escaped_url}"
---

{content}
'''
        output_file.write_text(content_with_header, encoding="utf-8")
        return str(output_file)
    except OSError as e:
        logger.error(f"Failed to write file {url_hash}.md: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error writing file {url_hash}.md: {str(e)}")
        return None


async def scrape_url(
    api_key: str,
    url: str,
    base_dir: str,
    project: str,
    ds_id: str
) -> Dict[str, Any]:
    """
    Scrape a single URL and save content.

    Args:
        api_key: Firecrawl API key
        url: URL to scrape
        base_dir: Base directory for storing files
        project: Project name
        ds_id: Data source ID

    Returns:
        Dict with scrape result
    """
    logger.info(f"Scraping URL: {url}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Configurable timeout
    scrape_timeout = int(os.getenv("WEBFETCH_SCRAPE_TIMEOUT", str(DEFAULT_SCRAPE_TIMEOUT)))

    try:
        response = requests.post(
            f"{FIRECRAWL_API_BASE}/scrape",
            headers=headers,
            json={"url": url, "formats": ["markdown"]},
            timeout=scrape_timeout
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("data", {}).get("markdown", "")

            if not content:
                logger.warning(f"No content received for URL: {url}")
                return {"status": "warning", "url": url, "message": "No content received"}

            # Save to file
            output_dir = Path(base_dir) / project / "raw" / "documents" / "webfetch" / ds_id

            # Use full MD5 hash to prevent collisions
            url_hash = hashlib.md5(url.encode()).hexdigest()

            # Get metadata
            metadata = data.get("data", {}).get("metadata", {})
            title = metadata.get("title", "Untitled")
            source_url = metadata.get("sourceURL", url)

            # Save with error handling
            saved_path = save_content_to_file(content, title, source_url, output_dir, url_hash)

            if saved_path:
                logger.info(f"Successfully scraped and saved: {url} -> {saved_path}")
                return {"status": "success", "url": url, "file": saved_path}
            else:
                return {"status": "error", "url": url, "error": "Failed to save file"}

        else:
            error_msg = f"Firecrawl API error: {response.status_code}"
            # Truncate response to avoid logging sensitive data
            truncated_response = response.text[:MAX_LOG_RESPONSE_LENGTH] if response.text else ""
            logger.error(f"{error_msg} for URL: {url} - Response: {truncated_response}")
            return {"status": "error", "url": url, "error": error_msg}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout scraping URL: {url}")
        return {"status": "error", "url": url, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error scraping URL {url}: {str(e)}")
        return {"status": "error", "url": url, "error": str(e)}


async def crawl_site(
    api_key: str,
    start_url: str,
    max_pages: int,
    base_dir: str,
    project: str,
    ds_id: str
) -> Dict[str, Any]:
    """
    Crawl a site (async with polling) and save all content.

    Args:
        api_key: Firecrawl API key
        start_url: Starting URL for crawl
        max_pages: Maximum pages to crawl
        base_dir: Base directory for storing files
        project: Project name
        ds_id: Data source ID

    Returns:
        Dict with crawl result
    """
    logger.info(f"Starting crawl for: {start_url} (max pages: {max_pages})")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # Start crawl job
        crawl_response = requests.post(
            f"{FIRECRAWL_API_BASE}/crawl",
            headers=headers,
            json={
                "url": start_url,
                "limit": max_pages
            },
            timeout=30
        )

        if crawl_response.status_code not in [200, 201]:
            error_msg = f"Failed to start crawl: {crawl_response.status_code}"
            truncated_response = crawl_response.text[:MAX_LOG_RESPONSE_LENGTH] if crawl_response.text else ""
            logger.error(f"{error_msg} - {truncated_response}")
            return {"status": "error", "start_url": start_url, "error": error_msg}

        job_data = crawl_response.json()
        job_id = job_data.get("id")

        if not job_id:
            return {"status": "error", "start_url": start_url, "error": "No job ID returned"}

        logger.info(f"Crawl job started with ID: {job_id}")

        # Poll for completion with configurable timeout
        max_wait = int(os.getenv("WEBFETCH_CRAWL_TIMEOUT", str(DEFAULT_CRAWL_TIMEOUT)))
        poll_interval = int(os.getenv("WEBFETCH_POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL)))
        max_consecutive_errors = int(os.getenv("WEBFETCH_MAX_ERRORS", str(DEFAULT_MAX_CONSECUTIVE_ERRORS)))

        elapsed = 0
        consecutive_errors = 0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                status_response = requests.get(
                    f"{FIRECRAWL_API_BASE}/crawl/{job_id}",
                    headers=headers,
                    timeout=30
                )

                if status_response.status_code != 200:
                    logger.warning(f"Status check failed: {status_response.status_code}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive polling errors ({consecutive_errors})")
                        return {"status": "error", "start_url": start_url, "error": "Polling failed", "job_id": job_id}
                    continue

                # Reset error counter on successful response
                consecutive_errors = 0

                status_data = status_response.json()
                status = status_data.get("status")

                if status == "completed":
                    # Save all pages
                    pages = status_data.get("data", [])
                    logger.info(f"Crawl completed with {len(pages)} pages")

                    output_dir = Path(base_dir) / project / "raw" / "documents" / "webfetch" / ds_id

                    saved_count = 0
                    skipped_count = 0
                    failed_count = 0

                    for page in pages:
                        content = page.get("markdown", "")
                        if not content:
                            skipped_count += 1
                            page_url = page.get("metadata", {}).get("sourceURL", "unknown")
                            logger.debug(f"Skipping page with no content: {page_url}")
                            continue

                        metadata = page.get("metadata", {})
                        page_url = metadata.get("sourceURL", "unknown")
                        title = metadata.get("title", "Untitled")

                        # Use full MD5 hash to prevent collisions
                        url_hash = hashlib.md5(page_url.encode()).hexdigest()

                        # Save with error handling
                        saved_path = save_content_to_file(content, title, page_url, output_dir, url_hash)

                        if saved_path:
                            saved_count += 1
                        else:
                            failed_count += 1

                    logger.info(f"Crawl results: {saved_count} saved, {skipped_count} skipped (no content), {failed_count} failed")

                    return {
                        "status": "success",
                        "start_url": start_url,
                        "pages_crawled": len(pages),
                        "pages_saved": saved_count,
                        "pages_skipped": skipped_count,
                        "pages_failed": failed_count,
                        "job_id": job_id
                    }

                elif status == "failed":
                    error_msg = "Crawl job failed"
                    logger.error(f"{error_msg} for job {job_id}")
                    return {"status": "error", "start_url": start_url, "error": error_msg, "job_id": job_id}

                else:
                    # Still in progress
                    completed = status_data.get("completed", 0)
                    total = status_data.get("total", "unknown")
                    logger.debug(f"Crawl in progress: {completed}/{total} pages")

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as poll_error:
                logger.warning(f"Network error polling crawl status: {str(poll_error)}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive network errors ({consecutive_errors})")
                    return {"status": "error", "start_url": start_url, "error": "Network errors during polling", "job_id": job_id}
                continue
            except Exception as poll_error:
                logger.error(f"Unexpected error polling crawl status: {str(poll_error)}", exc_info=True)
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors})")
                    return {"status": "error", "start_url": start_url, "error": str(poll_error), "job_id": job_id}
                continue

        logger.error(f"Crawl job timed out after {max_wait} seconds")
        return {"status": "error", "start_url": start_url, "error": "Crawl job timed out", "job_id": job_id}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout starting crawl for: {start_url}")
        return {"status": "error", "start_url": start_url, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error starting crawl for {start_url}: {str(e)}")
        return {"status": "error", "start_url": start_url, "error": str(e)}
