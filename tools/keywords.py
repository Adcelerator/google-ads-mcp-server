"""
Keyword management tools.

Keywords live on ad group criteria (adGroupCriteria).
Match types: BROAD, PHRASE, EXACT.
"""

from typing import Any, Dict, List
from tools.utils import mutate, gaql, resource_name, label_or_none, micros_to_currency


def register_tools(mcp) -> None:

    @mcp.tool
    def add_keywords(
        customer_id: str,
        ad_group_id: str,
        keywords: List[str],
        match_type: str = "BROAD",
        cpc_bid_micros: int = 0,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Add keywords to an ad group.

        Args:
            customer_id:    Google Ads customer ID.
            ad_group_id:    Numeric ad group ID.
            keywords:       List of keyword texts (e.g. ["running shoes", "buy sneakers"]).
            match_type:     BROAD | PHRASE | EXACT (applied to all keywords in the list).
            cpc_bid_micros: Optional per-keyword CPC bid in micros (0 = use group default).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.

        Returns:
            List of created criterion resource names.
        """
        ad_group_rn = resource_name("adGroups", customer_id, ad_group_id)
        operations = []
        for kw in keywords:
            criterion: Dict[str, Any] = {
                "adGroup": ad_group_rn,
                "status": "ENABLED",
                "keyword": {
                    "text": kw.strip(),
                    "matchType": match_type.upper(),
                },
            }
            if cpc_bid_micros:
                criterion["cpcBidMicros"] = str(cpc_bid_micros)
            operations.append({"create": criterion})

        result = mutate(
            customer_id, "adGroupCriteria", operations,
            label_or_none(account_label), label_or_none(manager_id),
        )
        created = [r["resourceName"] for r in result.get("results", [])]
        return {
            "success": True,
            "added_count": len(created),
            "keywords": keywords,
            "match_type": match_type.upper(),
            "resource_names": created,
        }

    @mcp.tool
    def add_negative_keywords(
        customer_id: str,
        ad_group_id: str,
        keywords: List[str],
        match_type: str = "BROAD",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Add negative keywords to an ad group.

        Args:
            customer_id:   Google Ads customer ID.
            ad_group_id:   Numeric ad group ID.
            keywords:      List of negative keyword texts.
            match_type:    BROAD | PHRASE | EXACT.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        ad_group_rn = resource_name("adGroups", customer_id, ad_group_id)
        operations = [
            {
                "create": {
                    "adGroup": ad_group_rn,
                    "negative": True,
                    "keyword": {"text": kw.strip(), "matchType": match_type.upper()},
                }
            }
            for kw in keywords
        ]
        result = mutate(
            customer_id, "adGroupCriteria", operations,
            label_or_none(account_label), label_or_none(manager_id),
        )
        created = [r["resourceName"] for r in result.get("results", [])]
        return {
            "success": True,
            "added_count": len(created),
            "negative_keywords": keywords,
            "match_type": match_type.upper(),
        }

    @mcp.tool
    def add_campaign_negative_keywords(
        customer_id: str,
        campaign_id: str,
        keywords: List[str],
        match_type: str = "BROAD",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Add campaign-level negative keywords.

        Campaign-level negatives block traffic for the entire campaign,
        not just a single ad group.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            keywords:      List of negative keyword texts.
            match_type:    BROAD | PHRASE | EXACT.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        campaign_rn = resource_name("campaigns", customer_id, campaign_id)
        operations = [
            {
                "create": {
                    "campaign": campaign_rn,
                    "negative": True,
                    "keyword": {"text": kw.strip(), "matchType": match_type.upper()},
                }
            }
            for kw in keywords
        ]
        result = mutate(
            customer_id, "campaignCriteria", operations,
            label_or_none(account_label), label_or_none(manager_id),
        )
        created = [r["resourceName"] for r in result.get("results", [])]
        return {
            "success": True,
            "added_count": len(created),
            "negative_keywords": keywords,
            "level": "campaign",
        }

    @mcp.tool
    def remove_keyword(
        customer_id: str,
        ad_group_id: str,
        criterion_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Remove a keyword criterion from an ad group.

        Args:
            customer_id:   Google Ads customer ID.
            ad_group_id:   Numeric ad group ID.
            criterion_id:  Numeric criterion ID (from list_keywords).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        from oauth.google_auth import format_customer_id
        cid = format_customer_id(customer_id)
        rn = f"customers/{cid}/adGroupCriteria/{ad_group_id}~{criterion_id}"
        mutate(customer_id, "adGroupCriteria", [{"remove": rn}], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "criterion_id": criterion_id, "status": "REMOVED"}

    @mcp.tool
    def update_keyword_bid(
        customer_id: str,
        ad_group_id: str,
        criterion_id: str,
        cpc_bid_micros: int,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Update the CPC bid for a specific keyword.

        Args:
            customer_id:    Google Ads customer ID.
            ad_group_id:    Numeric ad group ID.
            criterion_id:   Numeric criterion ID (from list_keywords).
            cpc_bid_micros: New CPC bid in micros (1 USD = 1,000,000).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.
        """
        from oauth.google_auth import format_customer_id
        cid = format_customer_id(customer_id)
        rn = f"customers/{cid}/adGroupCriteria/{ad_group_id}~{criterion_id}"
        op = {
            "update": {"resourceName": rn, "cpcBidMicros": str(cpc_bid_micros)},
            "updateMask": "cpc_bid_micros",
        }
        mutate(customer_id, "adGroupCriteria", [op], label_or_none(account_label), label_or_none(manager_id))
        return {
            "success": True,
            "criterion_id": criterion_id,
            "new_cpc_bid": micros_to_currency(cpc_bid_micros),
        }

    @mcp.tool
    def list_keywords(
        customer_id: str,
        ad_group_id: str = "",
        campaign_id: str = "",
        include_negatives: bool = False,
        status_filter: str = "ALL",
        limit: int = 200,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """List keywords in an ad group or campaign.

        Args:
            customer_id:       Google Ads customer ID.
            ad_group_id:       Filter by ad group (optional).
            campaign_id:       Filter by campaign (optional).
            include_negatives: Include negative keywords in results.
            status_filter:     ALL | ENABLED | PAUSED | REMOVED.
            limit:             Max results (default 200).
            account_label:     Multi-account label (optional).
            manager_id:        MCC manager account ID, if applicable.
        """
        conditions: List[str] = []
        if not include_negatives:
            conditions.append("ad_group_criterion.negative = FALSE")
        if status_filter.upper() != "ALL":
            conditions.append(f"ad_group_criterion.status = '{status_filter.upper()}'")
        if ad_group_id:
            conditions.append(f"ad_group.id = {ad_group_id}")
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        # Only keyword type
        conditions.append("ad_group_criterion.type = 'KEYWORD'")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.negative,
                ad_group_criterion.cpc_bid_micros,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name
            FROM ad_group_criterion
            {where}
            ORDER BY ad_group_criterion.keyword.text ASC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        keywords = []
        for row in data["results"]:
            crit = row.get("adGroupCriterion", {})
            kw = crit.get("keyword", {})
            ag = row.get("adGroup", {})
            c = row.get("campaign", {})
            keywords.append({
                "criterion_id": crit.get("criterionId"),
                "text": kw.get("text"),
                "match_type": kw.get("matchType"),
                "status": crit.get("status"),
                "negative": crit.get("negative", False),
                "cpc_bid": micros_to_currency(crit.get("cpcBidMicros", 0)),
                "ad_group_id": ag.get("id"),
                "ad_group_name": ag.get("name"),
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
            })
        return {"keywords": keywords, "total": len(keywords)}
