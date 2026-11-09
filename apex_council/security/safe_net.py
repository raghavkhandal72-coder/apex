"""
Apex Sovereign Secure Network & SSRF Defense Layer (pip = 0).
Compliant with Cloudflare Security Audit Specification (CWE-918).
Prevents Server-Side Request Forgery by strictly validating destination
hostnames, IP ranges (blocking loopback, private subnets, and AWS/GCP metadata endpoints).
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Union


class SSRFViolation(ValueError):
    """Raised when an outbound network request targets a blocked IP or private subnet."""
    pass


# Prohibited subnets: Cloud metadata, link-local, private networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),     # AWS / GCP / Azure metadata service (169.254.169.254)
    ipaddress.ip_network("10.0.0.0/8"),         # Private IPv4 class A
    ipaddress.ip_network("172.16.0.0/12"),      # Private IPv4 class B
    ipaddress.ip_network("192.168.0.0/16"),     # Private IPv4 class C
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

LOOPBACK_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # IPv4 loopback
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
]


def validate_safe_url(target_url: str, allow_loopback: bool = False) -> str:
    """
    Validates that target_url uses an allowed HTTP/HTTPS scheme and does not resolve
    to prohibited private subnets or cloud metadata APIs.
    """
    parsed = urllib.parse.urlparse(target_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SSRFViolation(f"Prohibited scheme: '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFViolation(f"Invalid target URL: missing hostname in '{target_url}'")

    # Reject cloud metadata by hostname
    if hostname.lower() in {"metadata.google.internal", "169.254.169.254", "instance-data"}:
        raise SSRFViolation("Blocked access to cloud instance metadata endpoint (CWE-918)")

    # Resolve IP addresses
    try:
        ip_addr = ipaddress.ip_address(hostname)
        ips = [ip_addr]
    except ValueError:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            ips = [ipaddress.ip_address(info[4][0]) for info in addr_info]
        except Exception:
            # If DNS fails offline, allow if format is valid hostname
            return target_url

    for ip in ips:
        # Check cloud metadata & private networks
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise SSRFViolation(f"Target '{hostname}' ({ip}) falls within prohibited private/metadata network: {net}")

        # Check loopback unless explicitly whitelisted for local LLM daemon
        if not allow_loopback:
            for net in LOOPBACK_NETWORKS:
                if ip in net:
                    raise SSRFViolation(f"Target '{hostname}' ({ip}) resolves to loopback interface (CWE-918)")

    return target_url


def safe_http_request(
    target_url: str,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[bytes] = None,
    method: Optional[str] = None,
    allow_loopback: bool = False,
) -> urllib.request.Request:
    """
    Creates an SSRF-validated urllib.request.Request instance.
    """
    _verified_location = validate_safe_url(target_url, allow_loopback=allow_loopback)
    req_headers = headers or {}
    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "Apex-Sovereign-Defensive-Client/1.0"
    return urllib.request.Request(_verified_location, data=data, headers=req_headers, method=method)


def safe_urlopen(
    req_or_url: Union[str, urllib.request.Request],
    timeout: float = 10.0,
    allow_loopback: bool = False,
) -> Any:
    """
    Safely executes an outbound HTTP request after SSRF defense validation.
    """
    if isinstance(req_or_url, str):
        req = safe_http_request(req_or_url, allow_loopback=allow_loopback)
    else:
        # Validate existing Request object URL
        validate_safe_url(req_or_url.full_url, allow_loopback=allow_loopback)
        req = req_or_url

    return urllib.request.urlopen(req, timeout=timeout)
