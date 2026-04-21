"""
Ad group management tools.

Ad groups live inside campaigns and contain ads + keywords.
Types: SEARCH_STANDARD, DISPLAY_STANDARD, SHOPPING_PRODUCT_ADS,
       VIDEO_TRUE_VIEW_IN_STREAM, VIDEO_BUMPER, etc.
"""

from typing import Any, Dict, List
from tools.utils import mutate, gaql, resource_name, label_or_none, micros_to_currency


def register_tools(mcp) -> None:

    @mcp.tool
    def create_ad_group(
        customer_id: str,
        campaign_id: str,
        name: str,
        ad_group_type: str = "SEARCH_STANDARD",
        cpc_bid_micros: int = 0,
        cpm_bid_micros: int = 0,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create an ad group inside a campaign.

        Args:
            customer_id:    Google Ads customer ID.
            campaign_id:    Numeric campaign ID.
            name:           Ad group name.
            ad_group_type:  SEARCH_STANDARD | DISPLAY_STANDARD |
                            SHOPPING_PRODUCT_ADS | VIDEO_TRUE_VIEW_IN_STREAM |
                            VIDEO_BUMPER | VIDEO_NON_SKIPPABLE_IN_STREAM.
            cpc_bid_micros: Default max CPC bid in micros (0 = use campaign default).
            cpm_bid_micros: Default CPM bid in micros for Display (0 = campaign default).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.

        Returns:
            ad_group_id, resource_name.
        """
        campaign_rn = resource_name("campaigns", customer_id, campaign_id)
        ag: Dict[str, Any] = {
            "name": name,
            "campaign": campaign_rn,
            "type": ad_group_type.upper(),
            "status": "ENABLED",
        }
        if cpc_bid_micros:
            ag["cpcBidMicros"] = str(cpc_bid_micros)
        if cpm_bid_micros:
            ag["cpmBidMicros"] = str(cpm_bid_micros)

        result = mutate(
            customer_id, "adGroups", [{"create": ag}],
            label_or_none(account_label), label_or_none(manager_id),
        )
        rn = result["results"][0]["resourceName"]
        ad_group_id = rn.split("/")[-1]
        return {
            "success": True,
            "ad_group_id": ad_group_id,
            "resource_name": rn,
            "name": name,
            "type": ad_group_type,
            "campaign_id": campaign_id,
        }

    @mcp.tool
    def update_ad_group(
        customer_id: str,
        ad_group_id: str,
        name: str = "",
        status: str = "",
        cpc_bid_micros: int = 0,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Update an ad group's name, status, or default bid.

        Args:
            customer_id:    Google Ads customer ID.
            ad_group_id:    Numeric ad group ID.
            name:           New name (leave empty to keep current).
            status:         ENABLED | PAUSED | REMOVED.
            cpc_bid_micros: New default CPC bid in micros (0 = no change).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.
        """
        rn = resource_name("adGroups", customer_id, ad_group_id)
        update: Dict[str, Any] = {"resourceName": rn}
        mask: List[str] = []

        if name:
            update["name"] = name
            mask.append("name")
        if status:
            update["status"] = status.upper()
            mask.append("status")
        if cpc_bid_micros:
            update["cpcBidMicros"] = str(cpc_bid_micros)
            mask.append("cpc_bid_micros")

        if not mask:
            return {"success": False, "message": "No fields to update."}

        op = {"update": update, "updateMask": ",".join(mask)}
        mutate(customer_id, "adGroups", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "ad_group_id": ad_group_id, "updated_fields": mask}

    @mcp.tool
    def pause_ad_group(
        customer_id: str,
        ad_group_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Pause an ad group.

        Args:
            customer_id:   Google Ads customer ID.
            ad_group_id:   Numeric ad group ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("adGroups", customer_id, ad_group_id)
        op = {"update": {"resourceName": rn, "status": "PAUSED"}, "updateMask": "status"}
        mutate(customer_id, "adGroups", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "ad_group_id": ad_group_id, "status": "PAUSED"}

    @mcp.tool
    def enable_ad_group(
        customer_id: str,
        ad_group_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Enable an ad group.

        Args:
            customer_id:   Google Ads customer ID.
            ad_group_id:   Numeric ad group ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("adGroups", customer_id, ad_group_id)
        op = {"update": {"resourceName": rn, "status": "ENABLED"}, "updateMask": "status"}
        mutate(customer_id, "adGroups", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "ad_group_id": ad_group_id, "status": "ENABLED"}

    @mcp.tool
    def remove_ad_group(
        customer_id: str,
        ad_group_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Permanently remove an ad group.

        Args:
            customer_id:   Google Ads customer ID.
            ad_group_id:   Numeric ad group ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("adGroups", customer_id, ad_group_id)
        mutate(customer_id, "adGroups", [{"remove": rn}], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "ad_group_id": ad_group_id, "status": "REMOVED"}

    @mcp.tool
    def list_ad_groups(
        customer_id: str,
        campaign_id: str = "",
        status_filter: str = "ALL",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """List ad groups, optionally filtered by campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Filter by campaign ID (leave empty for all campaigns).
            status_filter: ALL | ENABLED | PAUSED | REMOVED.
            limit:         Max results (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        conditions: List[str] = []
        if status_filter.upper() != "ALL":
            conditions.append(f"ad_group.status = '{status_filter.upper()}'")
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.cpc_bid_micros,
                campaign.id,
                campaign.name
            FROM ad_group
            {where}
            ORDER BY ad_group.name ASC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        ad_groups = []
        for row in data["results"]:
            ag = row.get("adGroup", {})
            c = row.get("campaign", {})
            ad_groups.append({
                "id": ag.get("id"),
                "name": ag.get("name"),
                "status": ag.get("status"),
                "type": ag.get("type"),
                "cpc_bid": micros_to_currency(ag.get("cpcBidMicros", 0)),
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
            })
        return {"ad_groups": ad_groups, "total": len(ad_groups)}
