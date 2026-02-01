import logging
import ipaddress
from typing import Dict, Any, Optional, Union, Tuple
from urllib.parse import urlparse
import socket
import requests

logger = logging.getLogger(__name__)

FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v1"

# Configuration constants
MAX_PAGES_LIMIT = 1000
MIN_PAGES_LIMIT = 1
API_TIMEOUT = 30
DNS_TIMEOUT = 5  # Timeout for DNS resolution
MAX_ERROR_RESPONSE_LENGTH = 200  # Reduced to limit information disclosure

# Block internal/private hostnames and cloud metadata endpoints for SSRF protection
# This list includes common variations and cloud provider metadata endpoints
BLOCKED_HOSTNAMES = {
    # Localhost variations
    'localhost',
    'localhost.localdomain',
    # Cloud metadata endpoints (AWS, GCP, Azure, etc.)
    'metadata.google.internal',
    'metadata.goog',
    'kubernetes.default.svc',
    # Common internal hostnames
    'internal',
    'intranet',
}

# Cloud metadata IP addresses to block
CLOUD_METADATA_IPS = {
    '169.254.169.254',  # AWS, GCP, Azure metadata
    '169.254.170.2',    # AWS ECS task metadata
    'fd00:ec2::254',    # AWS IPv6 metadata
}

# Additional blocked hostnames that resolve to metadata endpoints
BLOCKED_HOSTNAMES.update({
    'metadata',
    '169.254.169.254',  # Sometimes used as hostname
})


def is_ip_private_or_reserved(ip_str: str) -> bool:
    """
    Check if an IP address (IPv4 or IPv6) is private, reserved, loopback, or otherwise unsafe.
    Uses Python's ipaddress module for comprehensive validation.

    Returns:
        True if the IP is private/reserved/loopback/unsafe, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)

        # Check common properties
        if (ip.is_private or
            ip.is_loopback or
            ip.is_reserved or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_unspecified):
            return True

        # Additional check for IPv6 site-local (deprecated but still valid)
        if isinstance(ip, ipaddress.IPv6Address):
            # Site-local addresses (fec0::/10) - deprecated but check anyway
            site_local_network = ipaddress.IPv6Network('fec0::/10')
            if ip in site_local_network:
                return True

        # Check against known cloud metadata IPs
        if ip_str in CLOUD_METADATA_IPS:
            return True

        return False
    except ValueError:
        # Not a valid IP address
        return False


def resolve_all_ips(hostname: str) -> Tuple[bool, list, str]:
    """
    Resolve hostname to all IP addresses using getaddrinfo.
    This catches round-robin DNS with mixed public/private IPs.

    Args:
        hostname: The hostname to resolve

    Returns:
        Tuple of (success, list_of_ips, error_message)
    """
    # Set DNS timeout
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DNS_TIMEOUT)

    try:
        # Get all address info (both IPv4 and IPv6)
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)

        # Extract unique IP addresses
        ips = list(set(info[4][0] for info in addr_info))

        if not ips:
            return False, [], "No IP addresses found"

        return True, ips, ""

    except socket.gaierror as e:
        return False, [], f"DNS resolution failed: {e}"
    except socket.timeout:
        return False, [], "DNS resolution timed out"
    except Exception as e:
        return False, [], f"DNS error: {str(e)}"
    finally:
        # Restore original timeout
        socket.setdefaulttimeout(original_timeout)


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL format and check for SSRF vulnerabilities.
    Uses ipaddress module for comprehensive IPv4/IPv6 validation.

    Note on TOCTOU (Time-of-Check Time-of-Use): This validation checks DNS at
    validation time, but the actual request is made later by Firecrawl. An attacker
    could potentially change DNS records between validation and fetch (DNS rebinding).
    This is mitigated by Firecrawl's own SSRF protections. For maximum security,
    consider implementing request-time validation if Firecrawl supports it.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http:// or https://"

        # Check netloc exists
        if not parsed.netloc:
            return False, "Invalid URL format - missing domain"

        # Extract hostname (handle port numbers)
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL format - missing hostname"

        # Normalize hostname for comparison
        hostname_lower = hostname.lower()

        # Block known dangerous hostnames
        if hostname_lower in BLOCKED_HOSTNAMES:
            return False, "Cannot use localhost or internal hostnames"

        # Check for blocked hostname patterns (subdomains of blocked hosts)
        for blocked in BLOCKED_HOSTNAMES:
            if hostname_lower.endswith('.' + blocked):
                return False, f"Cannot use internal hostname: {hostname}"

        # Check if hostname is directly an IP address
        if is_ip_private_or_reserved(hostname):
            return False, "Cannot use private/internal IP addresses"

        # Resolve hostname and check ALL returned IPs
        # This prevents bypass via round-robin DNS with mixed IPs
        success, ips, error = resolve_all_ips(hostname)

        if not success:
            # DNS resolution failed - fail closed for security
            logger.warning(f"DNS resolution failed for {hostname}: {error}")
            return False, f"Could not resolve hostname: {hostname}"

        # Check every resolved IP for private/reserved ranges
        for ip in ips:
            if is_ip_private_or_reserved(ip):
                logger.warning(f"Hostname {hostname} resolves to blocked IP: {ip}")
                return False, "URL resolves to a private/internal IP address"

        return True, ""
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def validate_credentials(
    api_key: str,
    mode: str = "scrape",
    url: Optional[str] = None,
    start_url: Optional[str] = None,
    max_pages: Optional[Union[int, str]] = None
) -> Dict[str, Any]:
    """
    Validate Firecrawl API key and configuration.

    NOTE: Validation performs a lightweight scrape of example.com to verify the API key.
    This consumes a small amount of API credits.

    Args:
        api_key: Firecrawl API key
        mode: "scrape" for single page or "crawl" for multiple pages
        url: URL to scrape (for scrape mode)
        start_url: Starting URL for crawl (for crawl mode)
        max_pages: Maximum pages to crawl (optional, for crawl mode)

    Returns:
        Dict with status (success/error), message, and details
    """
    # Validate required fields
    if not api_key:
        logger.error("Firecrawl API key not provided")
        return {
            "status": "error",
            "message": "Firecrawl API key is required",
            "details": None
        }

    if mode not in ["scrape", "crawl"]:
        logger.error(f"Invalid mode: {mode}")
        return {
            "status": "error",
            "message": "Mode must be 'scrape' or 'crawl'",
            "details": None
        }

    # Determine target URL based on mode
    target_url = url if mode == "scrape" else start_url
    if not target_url:
        field_name = "URL" if mode == "scrape" else "Start URL"
        logger.error(f"{field_name} not provided for {mode} mode")
        return {
            "status": "error",
            "message": f"{field_name} is required for {mode} mode",
            "details": None
        }

    # Validate URL format and check for SSRF
    is_valid, error_msg = validate_url(target_url)
    if not is_valid:
        logger.error(f"URL validation failed: {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "details": None
        }

    # Validate max_pages for crawl mode
    if mode == "crawl" and max_pages is not None:
        try:
            # Handle string input with stricter validation
            if isinstance(max_pages, str):
                # Reject scientific notation and decimals
                if 'e' in max_pages.lower() or '.' in max_pages:
                    return {
                        "status": "error",
                        "message": "max_pages must be a whole number",
                        "details": None
                    }
                # Strip whitespace and validate it's a pure integer string
                max_pages = max_pages.strip()
                if not max_pages.lstrip('-').isdigit():
                    return {
                        "status": "error",
                        "message": "max_pages must be a valid number",
                        "details": None
                    }

            max_pages_int = int(max_pages)
            if max_pages_int < MIN_PAGES_LIMIT or max_pages_int > MAX_PAGES_LIMIT:
                return {
                    "status": "error",
                    "message": f"max_pages must be between {MIN_PAGES_LIMIT} and {MAX_PAGES_LIMIT}",
                    "details": None
                }
        except (ValueError, TypeError):
            return {
                "status": "error",
                "message": "max_pages must be a valid number",
                "details": None
            }

    try:
        logger.info(f"Validating Firecrawl API key for {mode} mode")

        # Test API key validity with a minimal scrape request
        # We scrape example.com which is lightweight
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{FIRECRAWL_API_BASE}/scrape",
            headers=headers,
            json={"url": "https://example.com", "formats": ["markdown"]},
            timeout=API_TIMEOUT
        )

        if response.status_code == 401:
            logger.error("Invalid Firecrawl API key")
            return {
                "status": "error",
                "message": "Invalid Firecrawl API key",
                "details": None
            }

        if response.status_code == 402:
            logger.error("Firecrawl quota exceeded or payment required")
            return {
                "status": "error",
                "message": "Firecrawl quota exceeded or payment required",
                "details": None
            }

        if response.status_code not in [200, 201]:
            logger.error(f"Firecrawl API error: {response.status_code}")
            # Truncate response to avoid exposing sensitive data
            error_details = response.text[:MAX_ERROR_RESPONSE_LENGTH] if response.text else None
            return {
                "status": "error",
                "message": f"Firecrawl API error: {response.status_code}",
                "details": error_details
            }

        logger.info(f"Firecrawl API key validated successfully for {mode} mode")

        return {
            "status": "success",
            "message": f"API key verified. {mode.capitalize()} will run when you start scanning.",
            "details": {
                "mode": mode,
                "target_url": target_url,
                "max_pages": max_pages if mode == "crawl" else None,
                "api_valid": True
            }
        }

    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Firecrawl API")
        return {
            "status": "error",
            "message": "Could not connect to Firecrawl API. Please check your network connection.",
            "details": None
        }
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to Firecrawl API")
        return {
            "status": "error",
            "message": "Timeout connecting to Firecrawl API. Please try again.",
            "details": None
        }
    except Exception as e:
        logger.error(f"Firecrawl validation error: {str(e)}")
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "details": None
        }
