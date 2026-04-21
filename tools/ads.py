"""
Ad creation and management tools.

Supported ad types:
  - Responsive Search Ad (RSA)  – standard for Search campaigns
  - Responsive Display Ad (RDA) – standard for Display campaigns
  - Call-only Ad                – click-to-call on mobile
  - App Ad                      – for Universal App campaigns
"""

from typing import Any, Dict, List, Optional
from tools.utils import mutate, gaql, resource_name, label_or_none


def register_tools(mcp) -> None:

    @mcp.tool
    def create_responsive_search_ad(
        customer_id: str,
        ad_group_id: str,
        headlines: List[str],
        descriptions: List[str],
        final_urls: List[str],
        path1: str = "",
        path2: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a Responsive Search Ad (RSA) in an ad group.

        Google automatically tests combinations of headlines and descriptions
        to find the best-performing mix.

        Args:
            customer_id:  Google Ads customer ID.
            ad_group_id:  Numeric ad group ID.
            headlines:    3–15 headlines (max 30 chars each).
            descriptions: 2–4 descriptions (max 90 chars each).
            final_urls:   At least one landing page URL.
            path1:        Optional display URL path 1 (max 15 chars).
            path2:        Optional display URL path 2 (max 15 chars).
            account_label: Multi-account label (optional).
            manager_id:   MCC manager account ID, if applicable.

        Returns:
            ad_id and resource_name of the created ad.
        """
        if len(headlines) < 3:
            raise ValueError("RSA requires at least 3 headlines.")
        if len(descriptions) < 2:
            raise ValueError("RSA requires at least 2 descriptions.")

        ad_group_rn = resource_name("adGroups", customer_id, ad_group_id)

        rsa: Dict[str, Any] = {
            "headlines": [{"text": h[:30]} for h in headlines],
            "descriptions": [{"text": d[:90]} for d in descriptions],
        }
        if path1:
            rsa["path1"] = path1[:15]
        if path2:
            rsa["path2"] = path2[:15]

        ad: Dict[str, Any] = {
            "adGroup": ad_group_rn,
            "status": "ENABLED",
            "ad": {
                "responsiveSearchAd": rsa,
                "finalUrls": final_urls,
            },
        }

        result = mutate(
            customer_id, "adGroupAds", [{"create": ad}],
            label_or_none(account_label), label_or_none(manager_id),
        )
        rn = result["results"][0]["resourceName"]
        ad_id = rn.split("/")[-1]
        return {
            "success": True,
            "ad_id": ad_id,
            "resource_name": rn,
            "type": "RESPONSIVE_SEARCH_AD",
            "headlines_count": len(headlines),
            "descriptions_count": len(descriptions),
        }

    @mcp.tool
    def create_responsive_display_ad(
        customer_id: str,
        ad_group_id: str,
        headlines: List[str],
        long_headline: str,
        descriptions: List[str],
        business_name: str,
        final_urls: List[str],
        marketing_image_asset: str = "",
        logo_image_asset: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a Responsive Display Ad (RDA) for Display campaigns.

        Args:
            customer_id:           Google Ads customer ID.
            ad_group_id:           Numeric ad group ID.
            headlines:             1–5 short headlines (max 30 chars each).
            long_headline:         Single long headline (max 90 chars).
            descriptions:          1–5 descriptions (max 90 chars each).
            business_name:         Brand/company name (max 25 chars).
            final_urls:            Landing page URLs.
            marketing_image_asset: Resource name of a previously uploaded image asset.
            logo_image_asset:      Resource name of a previously uploaded logo asset.
            account_label:         Multi-account label (optional).
            manager_id:            MCC manager account ID, if applicable.
        """
        ad_group_rn = resource_name("adGroups", customer_id, ad_group_id)

        rda: Dict[str, Any] = {
            "headlines": [{"text": h[:30]} for h in headlines],
            "longHeadline": {"text": long_headline[:90]},
            "descriptions": [{"text": d[:90]} for d in descriptions],
            "businessName": business_name[:25],
        }
        if marketing_image_asset:
            rda["marketingImages"] = [{"asset": marketing_image_asset}]
        if logo_image_asset:
            rda["logoImages"] = [{"asset": logo_image_asset}]

        ad: Dict[str, Any] = {
            "adGroup": ad_group_rn,
            "status": "ENABLED",
            "ad": {
                "responsiveDisplayAd": rda,
                "finalUrls": final_urls,
            },
        }

        result = mutate(
            customer_id, "adGroupAds", [{"create": ad}],
            label_or_none(account_label), label_or_none(manager_id),
        )
        rn = result["results"][0]["resourceName"]
        return {
            "success": True,
            "ad_id": rn.split("/")[-1],
            "resource_name": rn,
            "type": "RESPONSIVE_DISPLAY_AD",
        }

    @mcp.tool
    def create_call_only_ad(
        customer_id: str,
        ad_group_id: str,
        phone_number: str,
        country_code: str,
        headline1: str,
        headline2: str,
        description1: str,
        description2: str,
        business_name: str,
        final_urls: List[str],
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Create a call-only ad (click-to-call on mobile).

        Args:
            customer_id:  Google Ads customer ID.
            ad_group_id:  Numeric ad group ID.
            phone_number: Phone number (e.g. "+39 02 1234567").
            country_code: ISO country code (e.g. "IT", "US").
            headline1:    First headline (max 30 chars).
            headline2:    Second headline (max 30 chars).
            description1: First description (max 90 chars).
            description2: Second description (max 90 chars).
            business_name: Brand name (max 25 chars).
            final_urls:   Landing page URLs (required by API).
            account_label: Multi-account label (optional).
            manager_id:   MCC manager account ID, if applicable.
        """
        ad_group_rn = resource_name("adGroups", customer_id, ad_group_id)
        ad: Dict[str, Any] = {
            "adGroup": ad_group_rn,
            "status": "ENABLED",
            "ad": {
                "callOnlyAd": {
                    "phoneNumber": phone_number,
                    "countryCode": country_code.upper(),
                    "headline1": headline1[:30],
                    "headline2": headline2[:30],
                    "description1": description1[:90],
                    "description2": description2[:90],
                    "businessName": business_name[:25],
                    "phoneNumberVerificationUrl": final_urls[0] if final_urls else "",
                },
                "finalUrls": final_urls,
            },
        }
        result = mutate(
            customer_id, "adGroupAds", [{"create": ad}],
            label_or_none(account_label), label_or_none(manager_id),
        )
        rn = result["results"][0]["resourceName"]
        return {"success": True, "ad_id": rn.split("/")[-1], "resource_name": rn, "type": "CALL_ONLY_AD"}

    @mcp.tool
    def update_ad_status(
        customer_id: str,
        ad_group_id: str,
        ad_id: str,
        status: str,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Update the status of an ad (ENABLED | PAUSED | REMOVED).

        Args:
            customer_id:  Google Ads customer ID.
            ad_group_id:  Numeric ad group ID.
            ad_id:        Numeric ad ID.
            status:       ENABLED | PAUSED | REMOVED.
            account_label: Multi-account label (optional).
            manager_id:   MCC manager account ID, if applicable.
        """
        from oauth.google_auth import format_customer_id
        cid = format_customer_id(customer_id)
        rn = f"customers/{cid}/adGroupAds/{ad_group_id}~{ad_id}"
        op = {"update": {"resourceName": rn, "status": status.upper()}, "updateMask": "status"}
        mutate(customer_id, "adGroupAds", [op], label_or_none(account_label), label_or_none(manager_id))
        return {"success": True, "ad_id": ad_id, "status": status.upper()}

    @mcp.tool
    def list_ads(
        customer_id: str,
        ad_group_id: str = "",
        campaign_id: str = "",
        status_filter: str = "ALL",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """List ads in an account, campaign, or ad group.

        Args:
            customer_id:   Google Ads customer ID.
            ad_group_id:   Filter by ad group (leave empty for all).
            campaign_id:   Filter by campaign (leave empty for all).
            status_filter: ALL | ENABLED | PAUSED | REMOVED.
            limit:         Max results (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        conditions: List[str] = []
        if status_filter.upper() != "ALL":
            conditions.append(f"ad_group_ad.status = '{status_filter.upper()}'")
        if ad_group_id:
            conditions.append(f"ad_group.id = {ad_group_id}")
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.type,
                ad_group_ad.status,
                ad_group_ad.ad.final_urls,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name
            FROM ad_group_ad
            {where}
            ORDER BY ad_group_ad.ad.id DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        ads = []
        for row in data["results"]:
            a = row.get("adGroupAd", {})
            ad_obj = a.get("ad", {})
            ag = row.get("adGroup", {})
            c = row.get("campaign", {})
            ads.append({
                "ad_id": ad_obj.get("id"),
                "type": ad_obj.get("type"),
                "status": a.get("status"),
                "final_urls": ad_obj.get("finalUrls", []),
                "ad_group_id": ag.get("id"),
                "ad_group_name": ag.get("name"),
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
            })
        return {"ads": ads, "total": len(ads)}
