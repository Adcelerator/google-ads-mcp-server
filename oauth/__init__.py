"""
OAuth module for Google Ads authentication.
Supports single-account (legacy) and multi-account flows.
"""

from .google_auth import (
    format_customer_id,
    get_headers_with_auto_token,
    execute_gaql,
    get_oauth_credentials,
)
from .multi_account import MultiAccountManager, get_account_manager

__all__ = [
    "format_customer_id",
    "get_headers_with_auto_token",
    "execute_gaql",
    "get_oauth_credentials",
    "MultiAccountManager",
    "get_account_manager",
]

__version__ = "3.0.0"
__author__ = "Google Ads MCP Server Contributors"
__description__ = "OAuth 2.0 authentication module for Google Ads API (multi-account)"