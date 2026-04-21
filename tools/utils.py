"""
Shared helpers for Google Ads REST API calls.

All tool modules import from here so authentication logic lives in one place.
Falls back gracefully to the legacy single-account flow when no multi-account
profile is configured.
"""

import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger("google_ads_tools")

API_VERSION = "v19"
API_BASE = f"https://googleads.googleapis.com/{API_VERSION}"


# --------------------------------------------------------------------------- #
#  Auth helpers                                                                #
# --------------------------------------------------------------------------- #

def _get_headers(
    account_label: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Return auth headers.  Tries multi-account manager first;
    falls back to legacy single-account flow.
    """
    from oauth.multi_account import get_account_manager

    manager = get_account_manager()
    if manager.list_accounts():
        try:
            return manager.get_headers(account_label or None, manager_id or None)
        except Exception:
            pass

    # Legacy fallback
    from oauth.google_auth import get_headers_with_auto_token, format_customer_id
    headers = get_headers_with_auto_token()
    if manager_id:
        headers["login-customer-id"] = format_customer_id(manager_id)
    return headers


# --------------------------------------------------------------------------- #
#  Low-level HTTP wrappers                                                     #
# --------------------------------------------------------------------------- #

def _handle_response(resp: requests.Response) -> Dict[str, Any]:
    if not resp.ok:
        try:
            err = resp.json().get("error", {})
            msg = err.get("message") or err.get("status") or resp.text
        except Exception:
            msg = resp.text
        raise Exception(f"Google Ads API {resp.status_code}: {msg}")
    return resp.json() if resp.text.strip() else {}


def api_post(
    url: str,
    body: Dict[str, Any],
    account_label: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Dict[str, Any]:
    headers = _get_headers(account_label, manager_id)
    return _handle_response(requests.post(url, headers=headers, json=body))


def api_get(
    url: str,
    account_label: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Dict[str, Any]:
    headers = _get_headers(account_label, manager_id)
    return _handle_response(requests.get(url, headers=headers))


# --------------------------------------------------------------------------- #
#  Google Ads-specific helpers                                                 #
# --------------------------------------------------------------------------- #

def mutate(
    customer_id: str,
    resource: str,
    operations: List[Dict[str, Any]],
    account_label: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a mutate operation on a single Google Ads resource collection.

    POST .../customers/{cid}/{resource}:mutate
    """
    from oauth.google_auth import format_customer_id
    cid = format_customer_id(customer_id)
    url = f"{API_BASE}/customers/{cid}/{resource}:mutate"
    return api_post(url, {"operations": operations}, account_label, manager_id)


def gaql(
    customer_id: str,
    query: str,
    account_label: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a GAQL query and return {results, totalRows, query}."""
    from oauth.google_auth import format_customer_id
    cid = format_customer_id(customer_id)
    url = f"{API_BASE}/customers/{cid}/googleAds:search"
    data = api_post(url, {"query": query}, account_label, manager_id)
    results = data.get("results", [])
    return {"results": results, "totalRows": len(results), "query": query}


def resource_name(resource_type: str, customer_id: str, entity_id: str) -> str:
    """Build a Google Ads resource name string."""
    from oauth.google_auth import format_customer_id
    cid = format_customer_id(customer_id)
    return f"customers/{cid}/{resource_type}/{entity_id}"


def label_or_none(s: str) -> Optional[str]:
    """Convert empty string to None (used for optional account_label params)."""
    return s or None


def micros_to_currency(micros: Any) -> float:
    """Convert micros (int or str) to currency units."""
    try:
        return round(int(micros) / 1_000_000, 4)
    except (TypeError, ValueError):
        return 0.0
