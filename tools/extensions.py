"""
Ad extensions (assets) management tools.

Google Ads uses the Assets model (v13+):
  1. Create the asset  → returns customers/{cid}/assets/{asset_id}
  2. Link the asset to a campaign or customer

Supported types: SITELINK, CALLOUT, CALL, STRUCTURED_SNIPPET, PROMOTION.
"""

from typing import Any, Dict, List, Optional
from tools.utils import mutate, gaql, resource_name, label_or_none, API_BASE, api_post


def _link_asset_to_campaign(
    customer_id: str,
    campaign_id: str,
    asset_rn: str,
    field_type: str,
    account_label: Optional[str],
    manager_id: Optional[str],
) -> str:
    """Link an asset to a campaign and return the campaign asset resource name."""
    campaign_rn = resource_name("campaigns", customer_id, campaign_id)
    op = {
        "create": {
            "campaign": campaign_rn,
            "asset": asset_rn,
            "fieldType": field_type,
        }
    }
    result = mutate(customer_id, "campaignAssets", [op], account_label, manager_id)
    return result["results"][0]["resourceName"]


def _link_asset_to_customer(
    customer_id: str,
    asset_rn: str,
    field_type: str,
    account_label: Optional[str],
    manager_id: Optional[str],
) -> str:
    """Link an asset at account level."""
    op = {
        "create": {
            "asset": asset_rn,
            "fieldType": field_type,
        }
    }
    result = mutate(customer_id, "customerAssets", [op], account_label, manager_id)
    return result["results"][0]["resourceName"]


def register_tools(mcp) -> None:

    @mcp.tool
    def create_sitelink(
        customer_id: str,
        link_text: str,
        final_url: str,
        description1: str = "",
        description2: str = "",
        campaign_id: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a sitelink extension and optionally attach it to a campaign.

        Sitelinks add extra links below your main ad, driving users to specific pages.

        Args:
            customer_id:   Google Ads customer ID.
            link_text:     Anchor text of the sitelink (max 25 chars).
            final_url:     Destination URL for this sitelink.
            description1:  Optional first description line (max 35 chars).
            description2:  Optional second description line (max 35 chars).
            campaign_id:   Link to this campaign (leave empty for account-level).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.

        Returns:
            asset_id, resource_name, and optionally campaign_asset_resource_name.
        """
        sitelink: Dict[str, Any] = {"linkText": link_text[:25]}
        if description1:
            sitelink["description1"] = description1[:35]
        if description2:
            sitelink["description2"] = description2[:35]

        op = {
            "create": {
                "finalUrls": [final_url],
                "sitelinkAsset": sitelink,
            }
        }
        result = mutate(
            customer_id, "assets", [op],
            label_or_none(account_label), label_or_none(manager_id),
        )
        asset_rn = result["results"][0]["resourceName"]
        asset_id = asset_rn.split("/")[-1]
        response: Dict[str, Any] = {
            "success": True,
            "asset_id": asset_id,
            "asset_resource_name": asset_rn,
            "type": "SITELINK",
        }

        if campaign_id:
            campaign_asset_rn = _link_asset_to_campaign(
                customer_id, campaign_id, asset_rn, "SITELINK",
                label_or_none(account_label), label_or_none(manager_id),
            )
            response["campaign_asset_resource_name"] = campaign_asset_rn
            response["linked_to_campaign"] = campaign_id
        else:
            customer_asset_rn = _link_asset_to_customer(
                customer_id, asset_rn, "SITELINK",
                label_or_none(account_label), label_or_none(manager_id),
            )
            response["customer_asset_resource_name"] = customer_asset_rn
            response["linked_to"] = "account"

        return response

    @mcp.tool
    def create_callout(
        customer_id: str,
        callout_texts: List[str],
        campaign_id: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create callout extensions (short phrases below the ad).

        Callouts highlight key offerings: "Free Shipping", "24/7 Support", etc.

        Args:
            customer_id:    Google Ads customer ID.
            callout_texts:  List of callout strings (max 25 chars each).
            campaign_id:    Link to this campaign (leave empty for account-level).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.
        """
        created_assets = []
        for text in callout_texts:
            op = {"create": {"calloutAsset": {"calloutText": text[:25]}}}
            result = mutate(
                customer_id, "assets", [op],
                label_or_none(account_label), label_or_none(manager_id),
            )
            asset_rn = result["results"][0]["resourceName"]
            entry: Dict[str, Any] = {
                "asset_id": asset_rn.split("/")[-1],
                "asset_resource_name": asset_rn,
                "text": text,
            }
            if campaign_id:
                ca_rn = _link_asset_to_campaign(
                    customer_id, campaign_id, asset_rn, "CALLOUT",
                    label_or_none(account_label), label_or_none(manager_id),
                )
                entry["campaign_asset_resource_name"] = ca_rn
            else:
                ca_rn = _link_asset_to_customer(
                    customer_id, asset_rn, "CALLOUT",
                    label_or_none(account_label), label_or_none(manager_id),
                )
                entry["customer_asset_resource_name"] = ca_rn
            created_assets.append(entry)

        return {
            "success": True,
            "created_count": len(created_assets),
            "callouts": created_assets,
            "linked_to": campaign_id or "account",
        }

    @mcp.tool
    def create_call_extension(
        customer_id: str,
        phone_number: str,
        country_code: str,
        campaign_id: str = "",
        call_conversion_reporting_state: str = "USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a call extension to show a phone number in your ads.

        Args:
            customer_id:   Google Ads customer ID.
            phone_number:  Phone number (e.g. "+39 02 1234567").
            country_code:  ISO 2-letter country code (e.g. "IT").
            campaign_id:   Link to this campaign (leave empty for account-level).
            call_conversion_reporting_state:
                           USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION |
                           USE_RESOURCE_LEVEL_CALL_CONVERSION_ACTION |
                           DISABLED.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        op = {
            "create": {
                "callAsset": {
                    "phoneNumber": phone_number,
                    "countryCode": country_code.upper(),
                    "callConversionReportingState": call_conversion_reporting_state,
                }
            }
        }
        result = mutate(
            customer_id, "assets", [op],
            label_or_none(account_label), label_or_none(manager_id),
        )
        asset_rn = result["results"][0]["resourceName"]
        response: Dict[str, Any] = {
            "success": True,
            "asset_id": asset_rn.split("/")[-1],
            "asset_resource_name": asset_rn,
            "type": "CALL",
        }

        if campaign_id:
            ca_rn = _link_asset_to_campaign(
                customer_id, campaign_id, asset_rn, "CALL",
                label_or_none(account_label), label_or_none(manager_id),
            )
            response["campaign_asset_resource_name"] = ca_rn
            response["linked_to_campaign"] = campaign_id
        else:
            ca_rn = _link_asset_to_customer(
                customer_id, asset_rn, "CALL",
                label_or_none(account_label), label_or_none(manager_id),
            )
            response["customer_asset_resource_name"] = ca_rn
            response["linked_to"] = "account"

        return response

    @mcp.tool
    def create_structured_snippet(
        customer_id: str,
        header: str,
        values: List[str],
        campaign_id: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a structured snippet extension.

        Structured snippets show a list of values under a predefined header.
        Common headers: Services, Products, Brands, Courses, Styles, etc.

        Args:
            customer_id:   Google Ads customer ID.
            header:        Snippet header (e.g. "Services", "Products", "Brands").
            values:        List of values (max 10, each max 25 chars).
            campaign_id:   Link to this campaign (leave empty for account-level).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        op = {
            "create": {
                "structuredSnippetAsset": {
                    "header": header,
                    "values": [v[:25] for v in values[:10]],
                }
            }
        }
        result = mutate(
            customer_id, "assets", [op],
            label_or_none(account_label), label_or_none(manager_id),
        )
        asset_rn = result["results"][0]["resourceName"]
        response: Dict[str, Any] = {
            "success": True,
            "asset_id": asset_rn.split("/")[-1],
            "asset_resource_name": asset_rn,
            "type": "STRUCTURED_SNIPPET",
            "header": header,
        }

        target = campaign_id or None
        if target:
            ca_rn = _link_asset_to_campaign(
                customer_id, campaign_id, asset_rn, "STRUCTURED_SNIPPET",
                label_or_none(account_label), label_or_none(manager_id),
            )
            response["campaign_asset_resource_name"] = ca_rn
            response["linked_to_campaign"] = campaign_id
        else:
            ca_rn = _link_asset_to_customer(
                customer_id, asset_rn, "STRUCTURED_SNIPPET",
                label_or_none(account_label), label_or_none(manager_id),
            )
            response["customer_asset_resource_name"] = ca_rn
            response["linked_to"] = "account"

        return response

    @mcp.tool
    def remove_campaign_asset(
        customer_id: str,
        campaign_id: str,
        asset_id: str,
        field_type: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Remove an asset from a campaign.

        Args:
            customer_id:   Google Ads customer ID.
            campaign_id:   Numeric campaign ID.
            asset_id:      Numeric asset ID.
            field_type:    SITELINK | CALLOUT | CALL | STRUCTURED_SNIPPET.
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        from oauth.google_auth import format_customer_id
        cid = format_customer_id(customer_id)
        rn = f"customers/{cid}/campaignAssets/{campaign_id}~{asset_id}~{field_type.upper()}"
        mutate(customer_id, "campaignAssets", [{"remove": rn}], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "asset_id": asset_id, "campaign_id": campaign_id, "status": "REMOVED"}

    @mcp.tool
    def list_campaign_assets(
        customer_id: str,
        campaign_id: str = "",
        field_type_filter: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """List assets attached to a campaign (or all campaigns).

        Args:
            customer_id:      Google Ads customer ID.
            campaign_id:      Filter by campaign ID (optional).
            field_type_filter: SITELINK | CALLOUT | CALL | STRUCTURED_SNIPPET | etc.
            account_label:    Multi-account label (optional).
            manager_id:       MCC manager account ID, if applicable.
        """
        conditions: List[str] = ["campaign_asset.status != 'REMOVED'"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        if field_type_filter:
            conditions.append(f"campaign_asset.field_type = '{field_type_filter.upper()}'")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                campaign_asset.asset,
                campaign_asset.field_type,
                campaign_asset.status,
                campaign.id,
                campaign.name,
                asset.id,
                asset.type,
                asset.name
            FROM campaign_asset
            {where}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        assets = []
        for row in data["results"]:
            ca = row.get("campaignAsset", {})
            c = row.get("campaign", {})
            a = row.get("asset", {})
            assets.append({
                "asset_id": a.get("id"),
                "asset_type": a.get("type"),
                "asset_name": a.get("name"),
                "field_type": ca.get("fieldType"),
                "status": ca.get("status"),
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
            })
        return {"assets": assets, "total": len(assets)}
