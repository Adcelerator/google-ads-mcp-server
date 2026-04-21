"""
Geo & language targeting tools.

Handles campaign-level location and language criteria.
Supports any country, region, or city via the live API lookup,
with a curated shortcut dict for common countries.
"""

from typing import Any, Dict, List, Optional
from tools.utils import mutate, gaql, resource_name, label_or_none


def register_tools(mcp) -> None:

    @mcp.tool
    def search_geo_targets(
        customer_id: str,
        search_term: str,
        locale: str = "en",
        country_code: str = "",
        limit: int = 15,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Search Google Ads geo target constants by name (country, region, city).

        Use this to find the numeric ID needed for set_campaign_geo_targeting.

        Args:
            customer_id:   Any valid Google Ads customer ID (used only for auth).
            search_term:   Location name to search (e.g. "Italy", "Rome", "Lombardy").
            locale:        Language for result names (e.g. "en", "it", "de").
            country_code:  Optional ISO country code to narrow results (e.g. "IT").
            limit:         Max results to return (default 15).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.

        Returns:
            List of matching locations with id, name, type, country_code.
        """
        import requests
        from tools.utils import _get_headers, API_BASE

        headers = _get_headers(label_or_none(account_label), label_or_none(manager_id))
        url = f"{API_BASE}/geoTargetConstants:suggest"
        body: Dict[str, Any] = {
            "locale": locale,
            "searchTerm": search_term,
        }
        if country_code:
            body["countryCode"] = country_code.upper()

        resp = requests.post(url, headers=headers, json=body)
        if not resp.ok:
            # Fallback: GAQL-based search
            return _gaql_geo_search(customer_id, search_term, limit, account_label, manager_id)

        suggestions = resp.json().get("geoTargetConstantSuggestions", [])
        results = []
        for s in suggestions[:limit]:
            gtc = s.get("geoTargetConstant", {})
            results.append({
                "id": gtc.get("id"),
                "name": gtc.get("name"),
                "canonical_name": gtc.get("canonicalName"),
                "country_code": gtc.get("countryCode"),
                "target_type": gtc.get("targetType"),
                "status": gtc.get("status"),
                "resource_string": f"geoTargetConstants/{gtc.get('id')}",
            })
        return {
            "results": results,
            "total": len(results),
            "usage": "Pass 'id' values to set_campaign_geo_targeting geo_target_ids parameter.",
        }

    def _gaql_geo_search(customer_id, search_term, limit, account_label, manager_id):
        """Fallback GAQL-based geo target search."""
        query = f"""
            SELECT
                geo_target_constant.id,
                geo_target_constant.name,
                geo_target_constant.canonical_name,
                geo_target_constant.country_code,
                geo_target_constant.target_type,
                geo_target_constant.status
            FROM geo_target_constant
            WHERE geo_target_constant.name LIKE '%{search_term}%'
            AND geo_target_constant.status = 'ENABLED'
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        results = []
        for row in data["results"]:
            gtc = row.get("geoTargetConstant", {})
            results.append({
                "id": gtc.get("id"),
                "name": gtc.get("name"),
                "canonical_name": gtc.get("canonicalName"),
                "country_code": gtc.get("countryCode"),
                "target_type": gtc.get("targetType"),
                "resource_string": f"geoTargetConstants/{gtc.get('id')}",
            })
        return {"results": results, "total": len(results)}

    @mcp.tool
    def find_country_id(
        country_name_or_code: str,
    ) -> Dict[str, Any]:
        """Look up a country's geo target ID from the built-in shortcut table.

        Accepts country name, ISO-2 code, or existing numeric ID.
        Use search_geo_targets for cities, regions, or countries not in the table.

        Args:
            country_name_or_code: e.g. "Italy", "IT", "united_states", "US", "2840".

        Returns:
            Country info with geo target id and resource_string.
        """
        from data.geo_targets import find_country, COUNTRIES

        match = find_country(country_name_or_code)
        if match:
            return {
                "found": True,
                **match,
                "resource_string": f"geoTargetConstants/{match['id']}",
            }
        return {
            "found": False,
            "message": (
                f"'{country_name_or_code}' not in built-in table. "
                "Use search_geo_targets to query the live API."
            ),
            "available_countries": sorted(COUNTRIES.keys()),
        }

    @mcp.tool
    def get_language_constants(
        search: str = "",
    ) -> Dict[str, Any]:
        """List all available language constants, optionally filtered by name or code.

        Args:
            search: Optional filter string (e.g. "italian", "it", "1004").

        Returns:
            List of languages with id, name, code, and resource_string.
        """
        from data.languages import list_all_languages, find_language

        if search:
            match = find_language(search)
            if match:
                return {
                    "found": True,
                    **match,
                    "resource_string": f"languageConstants/{match['id']}",
                }
            return {"found": False, "message": f"Language '{search}' not found."}

        langs = list_all_languages()
        return {
            "languages": [
                {**l, "resource_string": f"languageConstants/{l['id']}"}
                for l in langs
            ],
            "total": len(langs),
        }

    @mcp.tool
    def set_campaign_geo_targeting(
        customer_id: str,
        campaign_id: str,
        geo_target_ids: List[int],
        negative: bool = False,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Set geographic targeting for a campaign.

        Pass numeric geo target IDs from search_geo_targets or find_country_id.
        Can be called multiple times to add more locations.

        Args:
            customer_id:    Google Ads customer ID.
            campaign_id:    Numeric campaign ID.
            geo_target_ids: List of numeric geo target constant IDs
                            (e.g. [20854] for Italy, [2840] for USA).
            negative:       True to exclude these locations (negative targeting).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.

        Returns:
            List of created campaign criterion resource names.

        Examples:
            # Target Italy + Germany
            set_campaign_geo_targeting("1234567890", "111", [20854, 2276])
            # Exclude UK
            set_campaign_geo_targeting("1234567890", "111", [2826], negative=True)
        """
        campaign_rn = resource_name("campaigns", customer_id, campaign_id)
        operations = [
            {
                "create": {
                    "campaign": campaign_rn,
                    "negative": negative,
                    "location": {
                        "geoTargetConstant": f"geoTargetConstants/{gid}"
                    },
                }
            }
            for gid in geo_target_ids
        ]
        result = mutate(
            customer_id, "campaignCriteria", operations,
            label_or_none(account_label), label_or_none(manager_id),
        )
        created = [r["resourceName"] for r in result.get("results", [])]
        return {
            "success": True,
            "campaign_id": campaign_id,
            "locations_added": len(created),
            "negative": negative,
            "geo_target_ids": geo_target_ids,
            "resource_names": created,
        }

    @mcp.tool
    def set_campaign_language_targeting(
        customer_id: str,
        campaign_id: str,
        language_ids: List[int],
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Set language targeting for a campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            language_ids:  List of language constant IDs
                           (e.g. [1004] for Italian, [1000] for English).
                           Use get_language_constants to look up IDs.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.

        Returns:
            List of created campaign criterion resource names.

        Examples:
            # Target Italian + English speakers
            set_campaign_language_targeting("1234567890", "111", [1004, 1000])
        """
        campaign_rn = resource_name("campaigns", customer_id, campaign_id)
        operations = [
            {
                "create": {
                    "campaign": campaign_rn,
                    "language": {
                        "languageConstant": f"languageConstants/{lid}"
                    },
                }
            }
            for lid in language_ids
        ]
        result = mutate(
            customer_id, "campaignCriteria", operations,
            label_or_none(account_label), label_or_none(manager_id),
        )
        created = [r["resourceName"] for r in result.get("results", [])]
        return {
            "success": True,
            "campaign_id": campaign_id,
            "languages_added": len(created),
            "language_ids": language_ids,
            "resource_names": created,
        }

    @mcp.tool
    def remove_campaign_criterion(
        customer_id: str,
        campaign_id: str,
        criterion_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Remove a geo or language criterion from a campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            criterion_id:  Numeric criterion ID (from list_campaign_criteria).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        from oauth.google_auth import format_customer_id
        cid = format_customer_id(customer_id)
        rn = f"customers/{cid}/campaignCriteria/{campaign_id}~{criterion_id}"
        mutate(customer_id, "campaignCriteria", [{"remove": rn}], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "criterion_id": criterion_id, "status": "REMOVED"}

    @mcp.tool
    def list_campaign_criteria(
        customer_id: str,
        campaign_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """List geo and language targeting criteria on a campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        query = f"""
            SELECT
                campaign_criterion.criterion_id,
                campaign_criterion.type,
                campaign_criterion.negative,
                campaign_criterion.location.geo_target_constant,
                campaign_criterion.language.language_constant
            FROM campaign_criterion
            WHERE campaign.id = {campaign_id}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        criteria = []
        for row in data["results"]:
            cc = row.get("campaignCriterion", {})
            entry: Dict[str, Any] = {
                "criterion_id": cc.get("criterionId"),
                "type": cc.get("type"),
                "negative": cc.get("negative", False),
            }
            if cc.get("location"):
                entry["geo_target_constant"] = cc["location"].get("geoTargetConstant")
            if cc.get("language"):
                entry["language_constant"] = cc["language"].get("languageConstant")
            criteria.append(entry)
        return {"criteria": criteria, "total": len(criteria)}
