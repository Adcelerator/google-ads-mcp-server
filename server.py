"""
Google Ads MCP Server – Extended Edition
=========================================
Comprehensive Google Ads management via the Model Context Protocol.

Features
--------
• Multi-account OAuth login (add_google_account, set_active_google_account, …)
• Campaign management    – create, update, pause, enable, remove, list
• Budget management      – create, update
• Ad group management    – create, update, pause, enable, remove, list
• Ad management          – RSA, RDA, call-only, status updates
• Keyword management     – add, remove, update bids, negatives
• Geo & language         – search geo targets, set targeting for any country
• Performance reporting  – campaigns, ad groups, keywords, search terms,
                           geographic, device, ad-level
• Extensions             – sitelinks, callouts, calls, structured snippets
• Raw GAQL               – run_gaql for custom queries
• Keyword ideas          – run_keyword_planner

Transport
---------
  Default : STDIO  (Claude Desktop / Claude Code)
  Optional: HTTP   run with --http flag (http://127.0.0.1:8000/mcp)
"""

import os
import sys
import logging

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP, Context
from typing import Any, Dict, List, Optional
import requests

from oauth.google_auth import format_customer_id, get_headers_with_auto_token, execute_gaql
from oauth.multi_account import get_account_manager

# ── Tool modules ────────────────────────────────────────────────────────────
import tools.campaigns  as _campaigns
import tools.ad_groups  as _ad_groups
import tools.ads        as _ads
import tools.keywords   as _keywords
import tools.targeting  as _targeting
import tools.reporting  as _reporting
import tools.extensions as _extensions

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("google_ads_server")

GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")

# ── MCP instance ─────────────────────────────────────────────────────────────
mcp = FastMCP("Google Ads Tools")
logger.info("Initialising Google Ads MCP Server …")

# ── Register all tool modules ────────────────────────────────────────────────
_campaigns.register_tools(mcp)
_ad_groups.register_tools(mcp)
_ads.register_tools(mcp)
_keywords.register_tools(mcp)
_targeting.register_tools(mcp)
_reporting.register_tools(mcp)
_extensions.register_tools(mcp)

# ============================================================================
#  MULTI-ACCOUNT MANAGEMENT TOOLS
#  (defined inline so they can close over get_account_manager)
# ============================================================================

@mcp.tool
def add_google_account(
    label: str,
    credentials_path: str,
    display_name: str = "",
    default_customer_id: str = "",
) -> Dict[str, Any]:
    """Add (or re-authenticate) a Google Ads account via OAuth browser flow.

    Run this once per Google login you want to manage.
    The token is saved locally and reused on every subsequent call.

    Args:
        label:               Short unique name for this account
                             (e.g. "agency", "client_abc", "my_brand").
        credentials_path:    Absolute path to the OAuth client_secret JSON
                             downloaded from Google Cloud Console.
        display_name:        Optional human-readable name shown in listings.
        default_customer_id: Default Google Ads customer ID for this login.

    Returns:
        Confirmation with account details and whether it's now active.

    Example:
        add_google_account(
            label="agency",
            credentials_path="/home/user/client_secret.json",
            display_name="My Agency Account",
            default_customer_id="123-456-7890"
        )
    """
    manager = get_account_manager()
    return manager.add_account(label, credentials_path, display_name, default_customer_id)


@mcp.tool
def list_google_accounts() -> Dict[str, Any]:
    """List all configured Google Ads OAuth accounts.

    Shows label, display name, active status, token validity,
    and the default customer ID for each account.
    """
    manager = get_account_manager()
    accounts = manager.list_accounts()
    active = manager.get_active_account_label()
    return {
        "accounts": accounts,
        "total": len(accounts),
        "active_account": active,
        "tip": (
            "Use set_active_google_account(label) to switch accounts. "
            "All tools accept an optional account_label parameter to target "
            "a specific account without changing the active one."
        ),
    }


@mcp.tool
def set_active_google_account(label: str) -> Dict[str, Any]:
    """Switch the active Google Ads account.

    The active account is used by default when no account_label is specified
    in any tool call.

    Args:
        label: The label of the account to activate (from list_google_accounts).
    """
    manager = get_account_manager()
    return manager.set_active_account(label)


@mcp.tool
def remove_google_account(label: str) -> Dict[str, Any]:
    """Remove a Google Ads account and delete its saved token.

    Args:
        label: The label of the account to remove (from list_google_accounts).
    """
    manager = get_account_manager()
    return manager.remove_account(label)


# ============================================================================
#  LEGACY / POWER-USER TOOLS  (kept from original server)
# ============================================================================

@mcp.tool
def run_gaql(
    customer_id: str,
    query: str,
    manager_id: str = "",
    account_label: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Execute any GAQL (Google Ads Query Language) query directly.

    Use this for custom reports, debugging, or queries not covered by
    the built-in reporting tools.

    Args:
        customer_id:   Google Ads customer ID (10 digits, no dashes).
        query:         Full GAQL query string.
        manager_id:    MCC manager account ID if access is via a manager.
        account_label: Multi-account label (optional; uses active account if empty).
        ctx:           MCP context (injected automatically).

    Returns:
        {results: [...], totalRows: int, query: str}

    See the gaql://reference resource for query examples.
    """
    if ctx:
        ctx.info(f"Executing GAQL for customer {customer_id} …")

    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN is not set.")

    from tools.utils import gaql as _gaql, label_or_none
    result = _gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))

    if ctx:
        ctx.info(f"Query returned {result['totalRows']} rows.")
    return result


@mcp.tool
def list_accounts(ctx: Context = None) -> Dict[str, Any]:
    """List all accessible Google Ads accounts (including nested MCC sub-accounts).

    Queries the Google Ads API to discover every account accessible with
    the current (or active) OAuth token.

    Returns:
        {accounts: [...], total_accounts: int}
        Each account has: id, name, access_type, is_manager, level.
    """
    if ctx:
        ctx.info("Listing accessible Google Ads accounts …")

    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN is not set.")

    headers = get_headers_with_auto_token()
    url = "https://googleads.googleapis.com/v19/customers:listAccessibleCustomers"
    resp = requests.get(url, headers=headers)
    if not resp.ok:
        raise Exception(f"Error listing accounts: {resp.status_code} {resp.reason} - {resp.text}")

    resource_names = resp.json().get("resourceNames", [])
    if not resource_names:
        return {"accounts": [], "message": "No accessible accounts found.", "total_accounts": 0}

    def _get_name(cid: str) -> str:
        try:
            r = execute_gaql(cid, "SELECT customer.descriptive_name FROM customer")
            rows = r.get("results", [])
            return rows[0].get("customer", {}).get("descriptiveName", f"Account {cid}") if rows else f"Account {cid}"
        except Exception:
            return f"Account {cid}"

    def _is_manager(cid: str) -> bool:
        try:
            r = execute_gaql(cid, "SELECT customer.manager FROM customer")
            rows = r.get("results", [])
            return bool(rows[0].get("customer", {}).get("manager", False)) if rows else False
        except Exception:
            return False

    def _get_subs(mgr_id: str) -> List[Dict]:
        try:
            q = (
                "SELECT customer_client.id, customer_client.descriptive_name, "
                "customer_client.level, customer_client.manager "
                "FROM customer_client WHERE customer_client.level > 0"
            )
            r = execute_gaql(mgr_id, q)
            subs = []
            for row in r.get("results", []):
                cl = row.get("customerClient", {}) or row.get("customer_client", {})
                cid = format_customer_id(str(cl.get("id", "")))
                subs.append({
                    "id": cid,
                    "name": cl.get("descriptiveName", f"Sub-account {cid}"),
                    "access_type": "managed",
                    "is_manager": bool(cl.get("manager", False)),
                    "parent_id": mgr_id,
                    "level": int(cl.get("level", 0)),
                })
            return subs
        except Exception:
            return []

    accounts: List[Dict] = []
    seen: set = set()
    for rn in resource_names:
        cid = format_customer_id(rn.split("/")[-1])
        name = _get_name(cid)
        manager = _is_manager(cid)
        accounts.append({"id": cid, "name": name, "access_type": "direct", "is_manager": manager, "level": 0})
        seen.add(cid)
        if manager:
            for sub in _get_subs(cid):
                if sub["id"] not in seen:
                    accounts.append(sub)
                    seen.add(sub["id"])
                    if sub["is_manager"]:
                        for nested in _get_subs(sub["id"]):
                            if nested["id"] not in seen:
                                accounts.append(nested)
                                seen.add(nested["id"])

    if ctx:
        ctx.info(f"Found {len(accounts)} accounts total.")

    return {"accounts": accounts, "total_accounts": len(accounts)}


@mcp.tool
def run_keyword_planner(
    customer_id: str,
    keywords: List[str],
    manager_id: str = "",
    page_url: Optional[str] = None,
    language_id: int = 1000,
    geo_target_id: int = 2840,
    start_year: Optional[int] = None,
    start_month: Optional[str] = None,
    end_year: Optional[int] = None,
    end_month: Optional[str] = None,
    page_size: int = 25,
    account_label: str = "",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Generate keyword ideas using Google Ads Keyword Planner.

    Returns search volume, competition level, and bid estimates.

    Args:
        customer_id:    Google Ads customer ID.
        keywords:       List of seed keywords (e.g. ["scarpe running", "comprare sneakers"]).
        manager_id:     MCC manager account ID if applicable.
        page_url:       Optional seed URL for keyword ideas.
        language_id:    Language constant ID (default 1000 = English).
                        Use get_language_constants() to look up IDs.
                        e.g. 1004 = Italian, 1001 = German, 1002 = French.
        geo_target_id:  Geo target constant ID (default 2840 = United States).
                        Use find_country_id() or search_geo_targets() to look up IDs.
                        e.g. 20854 = Italy, 2276 = Germany, 2250 = France.
        start_year:     Historical data start year (default: last year).
        start_month:    Historical data start month (default: JANUARY).
        end_year:       Historical data end year (default: current year).
        end_month:      Historical data end month (default: current month).
        page_size:      Number of ideas to return (default 25, max 1000).
        account_label:  Multi-account label (optional).
        ctx:            MCP context (injected automatically).

    Returns:
        keyword_ideas with avg_monthly_searches, competition, bid estimates.
    """
    if ctx:
        ctx.info(f"Generating keyword ideas for customer {customer_id} …")

    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN is not set.")

    if not keywords and not page_url:
        raise ValueError("At least one of keywords or page_url is required.")

    from tools.utils import _get_headers, label_or_none
    headers = _get_headers(label_or_none(account_label), label_or_none(manager_id))
    if manager_id:
        headers["login-customer-id"] = format_customer_id(manager_id)

    formatted_cid = format_customer_id(customer_id)
    url = f"https://googleads.googleapis.com/v19/customers/{formatted_cid}:generateKeywordIdeas"

    from datetime import datetime
    now = datetime.now()
    valid_months = ["JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE",
                    "JULY","AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"]
    s_year  = start_year  or (now.year - 1)
    s_month = start_month.upper() if start_month and start_month.upper() in valid_months else "JANUARY"
    e_year  = end_year    or now.year
    e_month = end_month.upper() if end_month and end_month.upper() in valid_months else now.strftime("%B").upper()

    body: Dict[str, Any] = {
        "language": f"languageConstants/{language_id}",
        "geoTargetConstants": [f"geoTargetConstants/{geo_target_id}"],
        "keywordPlanNetwork": "GOOGLE_SEARCH_AND_PARTNERS",
        "includeAdultKeywords": False,
        "pageSize": min(page_size, 1000),
        "historicalMetricsOptions": {
            "yearMonthRange": {
                "start": {"year": s_year, "month": s_month},
                "end":   {"year": e_year, "month": e_month},
            }
        },
    }

    if not keywords and page_url:
        body["urlSeed"] = {"url": page_url}
    elif keywords and not page_url:
        body["keywordSeed"] = {"keywords": keywords}
    else:
        body["keywordAndUrlSeed"] = {"url": page_url, "keywords": keywords}

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        raise Exception(f"Keyword Planner error {resp.status_code}: {resp.text}")

    results = resp.json().get("results", [])
    ideas = []
    for r in results:
        m = r.get("keywordIdeaMetrics", {})
        ideas.append({
            "keyword": r.get("text"),
            "avg_monthly_searches": m.get("avgMonthlySearches"),
            "competition": m.get("competition"),
            "competition_index": m.get("competitionIndex"),
            "low_top_of_page_bid": m.get("lowTopOfPageBidMicros"),
            "high_top_of_page_bid": m.get("highTopOfPageBidMicros"),
        })

    if ctx:
        ctx.info(f"Found {len(ideas)} keyword ideas.")

    return {
        "keyword_ideas": ideas,
        "total_ideas": len(ideas),
        "seed_keywords": keywords or [],
        "seed_url": page_url,
        "language_id": language_id,
        "geo_target_id": geo_target_id,
        "date_range": f"{s_month} {s_year} – {e_month} {e_year}",
    }


# ============================================================================
#  RESOURCE: GAQL reference
# ============================================================================

@mcp.resource("gaql://reference")
def gaql_reference() -> str:
    """Google Ads Query Language (GAQL) reference documentation."""
    return """
## GAQL Basic Structure

    SELECT field1, field2, ...
    FROM resource_type
    WHERE condition
    ORDER BY field [ASC|DESC]
    LIMIT n

## Common Resources

    campaign          – top-level campaign data
    ad_group          – ad groups within campaigns
    ad_group_ad       – ads within ad groups
    keyword_view      – keyword performance
    search_term_view  – actual search queries that triggered ads
    geographic_view   – performance by location
    campaign_criterion – geo / language targeting criteria
    campaign_budget   – budget info
    geo_target_constant  – look up geo target IDs
    language_constant    – look up language IDs

## Metric Fields

    metrics.impressions          metrics.clicks
    metrics.cost_micros          metrics.conversions
    metrics.conversions_value    metrics.ctr
    metrics.average_cpc          metrics.search_impression_share
    metrics.quality_score

## Segment Fields

    segments.date        segments.device      segments.day_of_week

## Date Ranges

    WHERE segments.date DURING LAST_7_DAYS
    WHERE segments.date DURING LAST_30_DAYS
    WHERE segments.date BETWEEN '2024-01-01' AND '2024-01-31'

## String Matching (use LIKE, not CONTAINS)

    WHERE campaign.name LIKE '%Brand%'

## Example Queries

    -- Campaign performance
    SELECT campaign.id, campaign.name, metrics.clicks, metrics.cost_micros
    FROM campaign
    WHERE segments.date DURING LAST_30_DAYS
    ORDER BY metrics.cost_micros DESC

    -- Keyword performance
    SELECT ad_group_criterion.keyword.text, metrics.impressions, metrics.ctr
    FROM keyword_view
    WHERE segments.date DURING LAST_7_DAYS
    ORDER BY metrics.impressions DESC

    -- Search terms
    SELECT search_term_view.search_term, metrics.impressions, metrics.clicks
    FROM search_term_view
    WHERE segments.date DURING LAST_30_DAYS

    -- Geo target lookup (find ID for "Italy")
    SELECT geo_target_constant.id, geo_target_constant.name, geo_target_constant.target_type
    FROM geo_target_constant
    WHERE geo_target_constant.name LIKE '%Italy%'

## Common Mistakes

    WRONG: campaign.campaign_budget.amount_micros
    RIGHT: campaign_budget.amount_micros (query FROM campaign_budget)

    WRONG: keyword.text
    RIGHT: ad_group_criterion.keyword.text (query FROM keyword_view)

    WRONG: WHERE campaign.name CONTAINS 'brand'
    RIGHT: WHERE campaign.name LIKE '%brand%'

    WRONG: WHERE segments.date >= '2024-01-01'
    RIGHT: WHERE segments.date BETWEEN '2024-01-01' AND '2024-01-31'
"""


# ============================================================================
#  Entry point
# ============================================================================

if __name__ == "__main__":
    if "--http" in sys.argv:
        logger.info("Starting with HTTP transport on http://127.0.0.1:8000/mcp")
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, path="/mcp")
    else:
        logger.info("Starting with STDIO transport (Claude Desktop / Claude Code)")
        mcp.run(transport="stdio")
