"""
Campaign & budget management tools.

Supported campaign types: SEARCH, DISPLAY, SHOPPING, VIDEO,
PERFORMANCE_MAX, DISCOVERY (Demand Gen), APP, LOCAL_SERVICES.

All campaigns are created in PAUSED status for safety.
Use enable_campaign to activate.
"""

from typing import Any, Dict, List, Optional
from tools.utils import mutate, gaql, resource_name, label_or_none, micros_to_currency


def register_tools(mcp) -> None:

    # ------------------------------------------------------------------ #
    #  Budgets                                                             #
    # ------------------------------------------------------------------ #

    @mcp.tool
    def create_campaign_budget(
        customer_id: str,
        name: str,
        amount_micros: int,
        delivery_method: str = "STANDARD",
        shared: bool = False,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a campaign budget.

        Args:
            customer_id:     Google Ads customer ID (10 digits, no dashes).
            name:            Budget name.
            amount_micros:   Daily budget in micros (1 USD = 1,000,000).
            delivery_method: STANDARD (even pacing) or ACCELERATED.
            shared:          True to make a shared budget reusable across campaigns.
            account_label:   Multi-account label (leave empty for active/default).
            manager_id:      MCC manager account ID, if applicable.

        Returns:
            resource_name and human-readable amount.
        """
        op = {
            "create": {
                "name": name,
                "amountMicros": str(amount_micros),
                "deliveryMethod": delivery_method.upper(),
                "explicitlyShared": shared,
            }
        }
        result = mutate(customer_id, "campaignBudgets", [op], label_or_none(account_label), label_or_none(manager_id))
        rn = result["results"][0]["resourceName"]
        budget_id = rn.split("/")[-1]
        return {
            "success": True,
            "budget_resource_name": rn,
            "budget_id": budget_id,
            "name": name,
            "amount_micros": amount_micros,
            "daily_budget": micros_to_currency(amount_micros),
        }

    @mcp.tool
    def update_campaign_budget(
        customer_id: str,
        budget_id: str,
        amount_micros: int,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Update a campaign budget's daily amount.

        Args:
            customer_id:   Google Ads customer ID.
            budget_id:     Numeric budget ID (from budget resource name).
            amount_micros: New daily budget in micros.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("campaignBudgets", customer_id, budget_id)
        op = {
            "update": {"resourceName": rn, "amountMicros": str(amount_micros)},
            "updateMask": "amount_micros",
        }
        mutate(customer_id, "campaignBudgets", [op], label_or_none(account_label), label_or_none(manager_id))
        return {
            "success": True,
            "budget_id": budget_id,
            "new_amount_micros": amount_micros,
            "new_daily_budget": micros_to_currency(amount_micros),
        }

    # ------------------------------------------------------------------ #
    #  Campaigns – create                                                  #
    # ------------------------------------------------------------------ #

    @mcp.tool
    def create_campaign(
        customer_id: str,
        name: str,
        budget_resource_name: str,
        campaign_type: str = "SEARCH",
        bidding_strategy: str = "MAXIMIZE_CONVERSIONS",
        target_cpa_micros: int = 0,
        target_roas: float = 0.0,
        start_date: str = "",
        end_date: str = "",
        target_search: bool = True,
        target_search_network: bool = True,
        target_content_network: bool = False,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a Google Ads campaign (starts PAUSED for safety).

        Args:
            customer_id:           Google Ads customer ID.
            name:                  Campaign name.
            budget_resource_name:  Resource name from create_campaign_budget
                                   e.g. "customers/1234567890/campaignBudgets/456".
            campaign_type:         SEARCH | DISPLAY | SHOPPING | VIDEO |
                                   PERFORMANCE_MAX | DISCOVERY | APP | LOCAL_SERVICES.
            bidding_strategy:      MAXIMIZE_CONVERSIONS | MAXIMIZE_CONVERSION_VALUE |
                                   TARGET_CPA | TARGET_ROAS | MANUAL_CPC |
                                   MAXIMIZE_CLICKS | TARGET_IMPRESSION_SHARE.
            target_cpa_micros:     Required when bidding_strategy=TARGET_CPA.
            target_roas:           Required when bidding_strategy=TARGET_ROAS (e.g. 4.0 = 400%).
            start_date:            YYYYMMDD – leave empty for today.
            end_date:              YYYYMMDD – leave empty for no end date.
            target_search:         Include Google Search (Search only).
            target_search_network: Include Search Network partners (Search only).
            target_content_network: Include Display Network (Search only).
            account_label:         Multi-account label (optional).
            manager_id:            MCC manager account ID, if applicable.

        Returns:
            campaign_id, resource_name, and setup guidance.
        """
        campaign: Dict[str, Any] = {
            "name": name,
            "advertisingChannelType": campaign_type.upper(),
            "campaignBudget": budget_resource_name,
            "status": "PAUSED",
        }

        # Bidding strategy
        bs = bidding_strategy.upper()
        if bs == "TARGET_CPA" and target_cpa_micros:
            campaign["targetCpa"] = {"targetCpaMicros": str(target_cpa_micros)}
        elif bs == "TARGET_ROAS" and target_roas:
            campaign["targetRoas"] = {"targetRoas": target_roas}
        elif bs == "MANUAL_CPC":
            campaign["manualCpc"] = {"enhancedCpcEnabled": False}
        elif bs == "MAXIMIZE_CLICKS":
            campaign["maximizeClicks"] = {}
        elif bs == "TARGET_IMPRESSION_SHARE":
            campaign["targetImpressionShare"] = {
                "location": "ANYWHERE_ON_PAGE",
                "locationFractionMicros": "1000000",
            }
        elif bs == "MAXIMIZE_CONVERSION_VALUE":
            campaign["maximizeConversionValue"] = {}
        else:
            campaign["maximizeConversions"] = {}

        # Network settings (Search only)
        if campaign_type.upper() == "SEARCH":
            campaign["networkSettings"] = {
                "targetGoogleSearch": target_search,
                "targetSearchNetwork": target_search_network,
                "targetContentNetwork": target_content_network,
                "targetPartnerSearchNetwork": False,
            }

        if start_date:
            campaign["startDate"] = start_date
        if end_date:
            campaign["endDate"] = end_date

        result = mutate(
            customer_id, "campaigns", [{"create": campaign}],
            label_or_none(account_label), label_or_none(manager_id),
        )
        rn = result["results"][0]["resourceName"]
        campaign_id = rn.split("/")[-1]

        return {
            "success": True,
            "campaign_id": campaign_id,
            "resource_name": rn,
            "name": name,
            "type": campaign_type,
            "status": "PAUSED",
            "next_steps": [
                f"Set geo targeting: set_campaign_geo_targeting(customer_id='{customer_id}', campaign_id='{campaign_id}', ...)",
                f"Set language:      set_campaign_language_targeting(customer_id='{customer_id}', campaign_id='{campaign_id}', ...)",
                f"Create ad group:   create_ad_group(customer_id='{customer_id}', campaign_id='{campaign_id}', ...)",
                f"Enable campaign:   enable_campaign(customer_id='{customer_id}', campaign_id='{campaign_id}')",
            ],
        }

    # ------------------------------------------------------------------ #
    #  Campaigns – update / status                                         #
    # ------------------------------------------------------------------ #

    @mcp.tool
    def update_campaign(
        customer_id: str,
        campaign_id: str,
        name: str = "",
        status: str = "",
        end_date: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Update campaign name, status, or end date.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            name:          New campaign name (leave empty to keep current).
            status:        ENABLED | PAUSED | REMOVED (leave empty to keep current).
            end_date:      New end date YYYYMMDD, or "none" to clear it.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("campaigns", customer_id, campaign_id)
        update: Dict[str, Any] = {"resourceName": rn}
        mask: List[str] = []

        if name:
            update["name"] = name
            mask.append("name")
        if status:
            update["status"] = status.upper()
            mask.append("status")
        if end_date:
            update["endDate"] = "" if end_date.lower() == "none" else end_date
            mask.append("end_date")

        if not mask:
            return {"success": False, "message": "No fields to update provided."}

        op = {"update": update, "updateMask": ",".join(mask)}
        mutate(customer_id, "campaigns", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "campaign_id": campaign_id, "updated_fields": mask}

    @mcp.tool
    def pause_campaign(
        customer_id: str,
        campaign_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Pause a campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("campaigns", customer_id, campaign_id)
        op = {"update": {"resourceName": rn, "status": "PAUSED"}, "updateMask": "status"}
        mutate(customer_id, "campaigns", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "campaign_id": campaign_id, "status": "PAUSED"}

    @mcp.tool
    def enable_campaign(
        customer_id: str,
        campaign_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Enable (activate) a campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("campaigns", customer_id, campaign_id)
        op = {"update": {"resourceName": rn, "status": "ENABLED"}, "updateMask": "status"}
        mutate(customer_id, "campaigns", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "campaign_id": campaign_id, "status": "ENABLED"}

    @mcp.tool
    def remove_campaign(
        customer_id: str,
        campaign_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Permanently remove (delete) a campaign. Cannot be undone.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        rn = resource_name("campaigns", customer_id, campaign_id)
        mutate(customer_id, "campaigns", [{"remove": rn}], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "campaign_id": campaign_id, "status": "REMOVED"}

    # ------------------------------------------------------------------ #
    #  Campaigns – list / details                                          #
    # ------------------------------------------------------------------ #

    @mcp.tool
    def list_campaigns(
        customer_id: str,
        status_filter: str = "ALL",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """List campaigns in an account with basic metrics.

        Args:
            customer_id:   Google Ads customer ID.
            status_filter: ALL | ENABLED | PAUSED | REMOVED.
            limit:         Maximum number of results (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.

        Returns:
            List of campaigns with id, name, status, type, budget.
        """
        where = "" if status_filter.upper() == "ALL" else f"WHERE campaign.status = '{status_filter.upper()}'"
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.start_date,
                campaign.end_date
            FROM campaign
            {where}
            ORDER BY campaign.name ASC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        campaigns = []
        for row in data["results"]:
            c = row.get("campaign", {})
            b = row.get("campaignBudget", {})
            campaigns.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "status": c.get("status"),
                "type": c.get("advertisingChannelType"),
                "daily_budget": micros_to_currency(b.get("amountMicros", 0)),
                "start_date": c.get("startDate"),
                "end_date": c.get("endDate"),
            })
        return {"campaigns": campaigns, "total": len(campaigns)}

    @mcp.tool
    def get_campaign_details(
        customer_id: str,
        campaign_id: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get full details of a single campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.bidding_strategy_type,
                campaign.start_date,
                campaign.end_date,
                campaign_budget.id,
                campaign_budget.name,
                campaign_budget.amount_micros,
                campaign_budget.delivery_method
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        if not data["results"]:
            return {"error": f"Campaign {campaign_id} not found."}
        row = data["results"][0]
        c = row.get("campaign", {})
        b = row.get("campaignBudget", {})
        return {
            "id": c.get("id"),
            "name": c.get("name"),
            "status": c.get("status"),
            "type": c.get("advertisingChannelType"),
            "bidding_strategy_type": c.get("biddingStrategyType"),
            "start_date": c.get("startDate"),
            "end_date": c.get("endDate"),
            "budget": {
                "id": b.get("id"),
                "name": b.get("name"),
                "daily_budget": micros_to_currency(b.get("amountMicros", 0)),
                "delivery_method": b.get("deliveryMethod"),
            },
        }
