"""
Performance reporting tools.

All reports use GAQL under the hood and return pre-formatted dicts
ready for direct consumption by an LLM or downstream analytics.

Common date_range values:
    TODAY, YESTERDAY, LAST_7_DAYS, LAST_14_DAYS, LAST_30_DAYS,
    THIS_MONTH, LAST_MONTH, LAST_BUSINESS_WEEK, THIS_WEEK_SUN_TODAY
Or a custom range passed as "BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'".
"""

from typing import Any, Dict, List, Optional
from tools.utils import gaql, label_or_none, micros_to_currency


def _fmt_date_range(date_range: str) -> str:
    """Wrap BETWEEN ranges; leave DURING keywords unchanged."""
    dr = date_range.strip().upper()
    if dr.startswith("BETWEEN"):
        return date_range.strip()
    return f"DURING {dr}"


def register_tools(mcp) -> None:

    @mcp.tool
    def get_campaign_performance(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        status_filter: str = "ALL",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get campaign-level performance metrics.

        Args:
            customer_id:   Google Ads customer ID.
            date_range:    LAST_7_DAYS | LAST_30_DAYS | THIS_MONTH | etc.
                           or "BETWEEN '2024-01-01' AND '2024-01-31'".
            campaign_id:   Filter to a single campaign (leave empty for all).
            status_filter: ALL | ENABLED | PAUSED | REMOVED.
            limit:         Max rows returned (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.

        Returns:
            Campaigns with impressions, clicks, cost, conversions, CTR, CPC.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if status_filter.upper() != "ALL":
            conditions.append(f"campaign.status = '{status_filter.upper()}'")
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc,
                metrics.search_impression_share
            FROM campaign
            {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            cost = micros_to_currency(m.get("costMicros", 0))
            conv = float(m.get("conversions", 0) or 0)
            rows.append({
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
                "status": c.get("status"),
                "type": c.get("advertisingChannelType"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": cost,
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "avg_cpc": micros_to_currency(m.get("averageCpc", 0)),
                "conversions": round(conv, 2),
                "conv_value": round(float(m.get("conversionsValue", 0) or 0), 2),
                "roas": round(float(m.get("conversionsValue", 0) or 0) / cost, 2) if cost else 0,
                "search_imp_share": m.get("searchImpressionShare"),
            })
        return {"campaigns": rows, "total": len(rows), "date_range": date_range}

    @mcp.tool
    def get_ad_group_performance(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get ad group-level performance metrics.

        Args:
            customer_id:   Google Ads customer ID.
            date_range:    Date range (see get_campaign_performance).
            campaign_id:   Filter by campaign ID (leave empty for all).
            limit:         Max rows (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM ad_group
            {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            ag = row.get("adGroup", {})
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            rows.append({
                "ad_group_id": ag.get("id"),
                "ad_group_name": ag.get("name"),
                "status": ag.get("status"),
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": micros_to_currency(m.get("costMicros", 0)),
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "avg_cpc": micros_to_currency(m.get("averageCpc", 0)),
                "conversions": round(float(m.get("conversions", 0) or 0), 2),
            })
        return {"ad_groups": rows, "total": len(rows), "date_range": date_range}

    @mcp.tool
    def get_keyword_performance(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        ad_group_id: str = "",
        min_impressions: int = 0,
        limit: int = 200,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get keyword-level performance metrics.

        Args:
            customer_id:    Google Ads customer ID.
            date_range:     Date range (see get_campaign_performance).
            campaign_id:    Filter by campaign ID (optional).
            ad_group_id:    Filter by ad group ID (optional).
            min_impressions: Only return keywords with >= this many impressions.
            limit:          Max rows (default 200).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        if ad_group_id:
            conditions.append(f"ad_group.id = {ad_group_id}")
        if min_impressions:
            conditions.append(f"metrics.impressions >= {min_impressions}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                campaign.name,
                ad_group.name,
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc,
                metrics.search_impression_share,
                metrics.quality_score
            FROM keyword_view
            {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            crit = row.get("adGroupCriterion", {})
            kw = crit.get("keyword", {})
            ag = row.get("adGroup", {})
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            rows.append({
                "criterion_id": crit.get("criterionId"),
                "keyword": kw.get("text"),
                "match_type": kw.get("matchType"),
                "status": crit.get("status"),
                "campaign_name": c.get("name"),
                "ad_group_name": ag.get("name"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": micros_to_currency(m.get("costMicros", 0)),
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "avg_cpc": micros_to_currency(m.get("averageCpc", 0)),
                "conversions": round(float(m.get("conversions", 0) or 0), 2),
                "quality_score": m.get("qualityScore"),
                "search_imp_share": m.get("searchImpressionShare"),
            })
        return {"keywords": rows, "total": len(rows), "date_range": date_range}

    @mcp.tool
    def get_search_terms_report(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        min_impressions: int = 10,
        limit: int = 200,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get the search terms report – what users actually typed.

        Use this to find new keyword opportunities and negatives.

        Args:
            customer_id:    Google Ads customer ID.
            date_range:     Date range (see get_campaign_performance).
            campaign_id:    Filter by campaign ID (optional).
            min_impressions: Only return terms with >= this impressions.
            limit:          Max rows (default 200).
            account_label:  Multi-account label (optional).
            manager_id:     MCC manager account ID, if applicable.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        if min_impressions:
            conditions.append(f"metrics.impressions >= {min_impressions}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                search_term_view.search_term,
                search_term_view.status,
                campaign.id,
                campaign.name,
                ad_group.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr
            FROM search_term_view
            {where}
            ORDER BY metrics.impressions DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            stv = row.get("searchTermView", {})
            c = row.get("campaign", {})
            ag = row.get("adGroup", {})
            m = row.get("metrics", {})
            rows.append({
                "search_term": stv.get("searchTerm"),
                "status": stv.get("status"),
                "campaign_id": c.get("id"),
                "campaign_name": c.get("name"),
                "ad_group_name": ag.get("name"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": micros_to_currency(m.get("costMicros", 0)),
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "conversions": round(float(m.get("conversions", 0) or 0), 2),
            })
        return {"search_terms": rows, "total": len(rows), "date_range": date_range}

    @mcp.tool
    def get_geographic_performance(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get performance broken down by geographic location.

        Args:
            customer_id:   Google Ads customer ID.
            date_range:    Date range (see get_campaign_performance).
            campaign_id:   Filter by campaign ID (optional).
            limit:         Max rows (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                campaign.name,
                geographic_view.location_type,
                geographic_view.country_criterion_id,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr
            FROM geographic_view
            {where}
            ORDER BY metrics.impressions DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            gv = row.get("geographicView", {})
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            rows.append({
                "campaign_name": c.get("name"),
                "location_type": gv.get("locationType"),
                "country_criterion_id": gv.get("countryCriterionId"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": micros_to_currency(m.get("costMicros", 0)),
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "conversions": round(float(m.get("conversions", 0) or 0), 2),
            })
        return {"locations": rows, "total": len(rows), "date_range": date_range}

    @mcp.tool
    def get_device_performance(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get performance broken down by device (mobile, desktop, tablet).

        Args:
            customer_id:   Google Ads customer ID.
            date_range:    Date range (see get_campaign_performance).
            campaign_id:   Filter by campaign ID (optional).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                campaign.name,
                segments.device,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            {where}
            ORDER BY metrics.cost_micros DESC
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            c = row.get("campaign", {})
            s = row.get("segments", {})
            m = row.get("metrics", {})
            rows.append({
                "campaign_name": c.get("name"),
                "device": s.get("device"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": micros_to_currency(m.get("costMicros", 0)),
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "avg_cpc": micros_to_currency(m.get("averageCpc", 0)),
                "conversions": round(float(m.get("conversions", 0) or 0), 2),
            })
        return {"devices": rows, "total": len(rows), "date_range": date_range}

    @mcp.tool
    def get_ad_performance(
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        campaign_id: str = "",
        ad_group_id: str = "",
        limit: int = 100,
        account_label: str = "",
        manager_id: str = "",
    ) -> Dict[str, Any]:
        """Get ad-level performance metrics.

        Args:
            customer_id:   Google Ads customer ID.
            date_range:    Date range (see get_campaign_performance).
            campaign_id:   Filter by campaign ID (optional).
            ad_group_id:   Filter by ad group ID (optional).
            limit:         Max rows (default 100).
            account_label: Multi-account label (optional).
            manager_id:    MCC manager account ID, if applicable.
        """
        conditions: List[str] = [f"segments.date {_fmt_date_range(date_range)}"]
        if campaign_id:
            conditions.append(f"campaign.id = {campaign_id}")
        if ad_group_id:
            conditions.append(f"ad_group.id = {ad_group_id}")
        where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.type,
                ad_group_ad.status,
                ad_group.name,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM ad_group_ad
            {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        data = gaql(customer_id, query, label_or_none(account_label), label_or_none(manager_id))
        rows = []
        for row in data["results"]:
            a = row.get("adGroupAd", {})
            ad_obj = a.get("ad", {})
            ag = row.get("adGroup", {})
            c = row.get("campaign", {})
            m = row.get("metrics", {})
            rows.append({
                "ad_id": ad_obj.get("id"),
                "type": ad_obj.get("type"),
                "status": a.get("status"),
                "ad_group_name": ag.get("name"),
                "campaign_name": c.get("name"),
                "impressions": int(m.get("impressions", 0) or 0),
                "clicks": int(m.get("clicks", 0) or 0),
                "cost": micros_to_currency(m.get("costMicros", 0)),
                "ctr_pct": round(float(m.get("ctr", 0) or 0) * 100, 2),
                "avg_cpc": micros_to_currency(m.get("averageCpc", 0)),
                "conversions": round(float(m.get("conversions", 0) or 0), 2),
            })
        return {"ads": rows, "total": len(rows), "date_range": date_range}
