import ipaddress
import json
import logging
import socket
from typing import Dict, Any, Tuple
from urllib.parse import urlparse
from requests.exceptions import RequestException, Timeout
import requests

# Configure logging
logger = logging.getLogger(__name__)

# Connection configuration
REQUEST_TIMEOUT = 15
ASSET_SAMPLE_SIZE = 10
DNS_TIMEOUT = 5  # Timeout for DNS resolution

# Blocked hostnames for SSRF protection (exact match)
BLOCKED_HOSTNAMES = {
    # Localhost variations
    'localhost', 'localhost.localdomain',
    # Cloud metadata endpoints (AWS, GCP, Azure, etc.)
    'metadata.google.internal', 'metadata.goog',
    'metadata.azure.internal', 'metadata.aws.internal',
    'kubernetes.default.svc',
    # IP addresses as hostnames
    '169.254.169.254', '169.254.170.2',
}

# Cloud metadata IP addresses to block
CLOUD_METADATA_IPS = {
    '169.254.169.254',  # AWS, GCP, Azure metadata
    '169.254.170.2',    # AWS ECS task metadata
    'fd00:ec2::254',    # AWS IPv6 metadata
}

# Blocked domain suffixes for internal networks
BLOCKED_DOMAIN_SUFFIXES = (
    '.internal',
    '.local',
    '.localhost',
    '.localdomain',
    '.intranet',
    '.corp',
    '.lan'
)


def _is_ip_private_or_reserved(ip_str: str) -> bool:
    """
    Check if an IP address (IPv4 or IPv6) is private, reserved, loopback, or unsafe.

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


def _resolve_all_ips(hostname: str) -> Tuple[bool, list, str]:
    """
    Resolve hostname to all IP addresses using getaddrinfo.
    This catches round-robin DNS with mixed public/private IPs.

    Args:
        hostname: The hostname to resolve

    Returns:
        Tuple of (success, list_of_ips, error_message)
    """
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DNS_TIMEOUT)

    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
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
        socket.setdefaulttimeout(original_timeout)


def _validate_url_for_ssrf(url: str) -> Tuple[bool, str]:
    """
    Validate URL to prevent SSRF attacks.

    This provides defense-in-depth through:
    - HTTPS scheme enforcement
    - Blocked hostname exact matching (localhost, metadata endpoints)
    - Blocked domain suffix matching (internal domains)
    - Direct IP address validation
    - DNS resolution with IP validation (catches rebinding/round-robin)

    Note on TOCTOU: DNS is validated at check time, but actual requests happen
    later. An attacker could theoretically change DNS between validation and
    request. This window is minimized by validating immediately before requests
    and is accepted as a reasonable trade-off for SSL certificate compatibility.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # Require HTTPS scheme
        if parsed.scheme != 'https':
            return False, "Only HTTPS URLs are allowed for security reasons"

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname found"

        hostname_lower = hostname.lower()

        # Check blocked hostnames (exact match)
        if hostname_lower in BLOCKED_HOSTNAMES:
            return False, f"URL hostname '{hostname}' is not allowed"

        # Check blocked domain suffixes (suffix match)
        if hostname_lower.endswith(BLOCKED_DOMAIN_SUFFIXES):
            return False, f"Internal domain suffix not allowed: {hostname}"

        # Check if hostname is directly an IP address
        if _is_ip_private_or_reserved(hostname):
            return False, "Cannot use private/internal IP addresses"

        # Resolve hostname and validate ALL returned IPs
        # This prevents bypass via round-robin DNS with mixed public/private IPs
        success, ips, error = _resolve_all_ips(hostname)

        if not success:
            logger.warning(f"DNS resolution failed for {hostname}: {error}")
            return False, f"Could not resolve hostname: {hostname}"

        # Check every resolved IP for private/reserved ranges
        for ip in ips:
            if _is_ip_private_or_reserved(ip):
                logger.warning(f"Hostname {hostname} resolves to blocked IP: {ip}")
                return False, "URL resolves to a private/internal IP address"

        # Validate Atlan-specific domain pattern (warning only for flexibility)
        if not hostname_lower.endswith('.atlan.com'):
            logger.warning(f"Non-standard Atlan domain: {hostname}. Expected *.atlan.com")

        return True, ""

    except Exception as e:
        return False, f"URL validation failed: {str(e)}"


def validate_credentials(tenant_url: str, api_token: str) -> Dict[str, Any]:
    """
    Validate Atlan credentials and API access

    Args:
        tenant_url: Atlan tenant URL (e.g., https://org.atlan.com)
        api_token: Atlan API token for authentication

    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not tenant_url:
        logger.error('Atlan tenant URL not provided')
        return {
            "status": "error",
            "message": "Atlan tenant URL is required",
            "details": None
        }

    if not api_token:
        logger.error('Atlan API token not provided')
        return {
            "status": "error",
            "message": "Atlan API token is required",
            "details": None
        }

    try:
        # Normalize and validate tenant_url scheme
        tenant_url = tenant_url.strip().rstrip('/')

        # Reject explicit http:// URLs immediately
        if tenant_url.lower().startswith('http://'):
            logger.error('HTTP URLs are not allowed - HTTPS required')
            return {
                "status": "error",
                "message": "Only HTTPS URLs are allowed for security reasons. Please use https:// or just the hostname.",
                "details": None
            }

        # Add https:// if no scheme provided
        if not tenant_url.lower().startswith('https://'):
            tenant_url = f"https://{tenant_url}"

        # Validate URL for SSRF protection (includes DNS resolution)
        is_valid, error_msg = _validate_url_for_ssrf(tenant_url)
        if not is_valid:
            logger.error(f'URL validation failed: {error_msg}')
            return {
                "status": "error",
                "message": error_msg,
                "details": None
            }

        logger.info(f'Testing Atlan connection for tenant: {tenant_url}')

        # Set up headers for Atlan API authentication
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        # Test authentication by getting type definitions
        # Atlan uses Apache Atlas-based API at /api/meta
        auth_endpoint = f"{tenant_url}/api/meta/types/typedefs/headers"

        logger.info('Testing authentication with Atlan API...')
        try:
            response = requests.get(
                auth_endpoint,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=True,  # Explicitly verify SSL certificates
                allow_redirects=False  # Prevent SSRF via redirects
            )

            # Check for redirects (blocked for SSRF prevention)
            if 300 <= response.status_code < 400:
                redirect_url = response.headers.get('Location', 'unknown')
                logger.error(f'Server attempted redirect to {redirect_url} - blocked for security')
                return {
                    "status": "error",
                    "message": "Server redirect detected. Redirects are not allowed for security reasons. Please verify the tenant URL.",
                    "details": {"error_code": response.status_code, "redirect_url": redirect_url}
                }

            # Check for authentication errors
            if response.status_code == 401:
                logger.error('Authentication failed: Invalid API token (401)')
                return {
                    "status": "error",
                    "message": "Authentication failed: Invalid API token. Ensure the token has proper persona assignments.",
                    "details": {"error_code": 401}
                }
            elif response.status_code == 403:
                logger.error('Authentication failed: Access forbidden (403)')
                return {
                    "status": "error",
                    "message": "Authentication failed: Access forbidden. The API token may not have required permissions.",
                    "details": {"error_code": 403}
                }
            elif response.status_code >= 400:
                logger.error(f'HTTP error {response.status_code}: {response.text}')
                return {
                    "status": "error",
                    "message": f"HTTP error {response.status_code}: {response.reason}",
                    "details": {"error_code": response.status_code}
                }

            logger.info('Successfully authenticated with Atlan API')

        except Timeout:
            logger.error(f'Connection timeout: Could not reach Atlan server within {REQUEST_TIMEOUT} seconds')
            return {
                "status": "error",
                "message": f"Connection timeout: Could not reach Atlan server within {REQUEST_TIMEOUT} seconds",
                "details": None
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Connection error: Could not connect to Atlan server - {str(e)}')
            return {
                "status": "error",
                "message": "Connection error: Could not connect to Atlan server. Please verify the tenant URL.",
                "details": None
            }

        # Try to get asset count using search API
        asset_count = 0
        sample_assets = []

        try:
            logger.info('Attempting to get asset count from Atlan catalog...')
            search_endpoint = f"{tenant_url}/api/meta/search/indexsearch"

            # Simple search to get asset count
            search_payload = {
                "dsl": {
                    "from": 0,
                    "size": ASSET_SAMPLE_SIZE,
                    "query": {
                        "match_all": {}
                    }
                },
                "attributes": ["name", "qualifiedName", "__typeName"]
            }

            search_response = requests.post(
                search_endpoint,
                json=search_payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=True,  # Explicitly verify SSL certificates
                allow_redirects=False  # Prevent SSRF via redirects
            )

            # Check for redirects on search endpoint too
            if 300 <= search_response.status_code < 400:
                logger.warning('Search endpoint redirect detected - ignoring asset count')
            elif search_response.status_code == 200:
                search_data = search_response.json()
                asset_count = search_data.get("approximateCount", 0)

                # Get sample asset names
                entities = search_data.get("entities", [])
                for entity in entities[:5]:
                    attrs = entity.get("attributes", {})
                    name = attrs.get("name", entity.get("guid", "Unknown"))
                    type_name = entity.get("typeName", attrs.get("__typeName", "Unknown"))
                    sample_assets.append(f"{type_name}: {name}")

                logger.info(f'Successfully retrieved {asset_count} total assets from Atlan catalog')
            else:
                logger.warning(f'Search returned status {search_response.status_code}, but auth succeeded')

        except (RequestException, json.JSONDecodeError, KeyError) as e:
            logger.warning(f'Could not retrieve asset count: {type(e).__name__}: {str(e)}')
            # Auth succeeded, so we still report success but without asset count

        # Prepare success response
        success_message = f"Atlan connection successful for tenant {tenant_url}"
        if asset_count > 0:
            success_message += f" with access to {asset_count:,} cataloged assets"

        return {
            "status": "success",
            "message": success_message,
            "details": {
                "tenant_url": tenant_url,
                "asset_count": asset_count,
                "sample_assets": sample_assets if sample_assets else None
            }
        }

    except Exception as e:
        # Catch any unexpected errors at the top level
        logger.error(f'Atlan unexpected error: {type(e).__name__}: {str(e)}')
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "details": None
        }
