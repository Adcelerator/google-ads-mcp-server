"""
Google Ads geo target constants for common countries and regions.

The IDs here match Google's geoTargetConstants resource.
For cities/regions not listed, use search_geo_targets() which queries the live API.

Usage:
    from data.geo_targets import COUNTRIES, find_country

    country = find_country("italy")
    resource = f"geoTargetConstants/{country['id']}"
"""

from typing import Dict, List, Optional

# Country-level geo target criterion IDs
# Verified against Google Ads API geoTargetConstants resource
COUNTRIES: Dict[str, Dict] = {
    # Europe
    "italy":           {"id": 20854, "name": "Italy",           "code": "IT", "region": "Europe"},
    "germany":         {"id": 2276,  "name": "Germany",         "code": "DE", "region": "Europe"},
    "france":          {"id": 2250,  "name": "France",          "code": "FR", "region": "Europe"},
    "spain":           {"id": 2724,  "name": "Spain",           "code": "ES", "region": "Europe"},
    "united_kingdom":  {"id": 2826,  "name": "United Kingdom",  "code": "GB", "region": "Europe"},
    "netherlands":     {"id": 2528,  "name": "Netherlands",     "code": "NL", "region": "Europe"},
    "belgium":         {"id": 2056,  "name": "Belgium",         "code": "BE", "region": "Europe"},
    "switzerland":     {"id": 2756,  "name": "Switzerland",     "code": "CH", "region": "Europe"},
    "austria":         {"id": 2040,  "name": "Austria",         "code": "AT", "region": "Europe"},
    "portugal":        {"id": 2620,  "name": "Portugal",        "code": "PT", "region": "Europe"},
    "poland":          {"id": 2616,  "name": "Poland",          "code": "PL", "region": "Europe"},
    "sweden":          {"id": 2752,  "name": "Sweden",          "code": "SE", "region": "Europe"},
    "norway":          {"id": 2578,  "name": "Norway",          "code": "NO", "region": "Europe"},
    "denmark":         {"id": 2208,  "name": "Denmark",         "code": "DK", "region": "Europe"},
    "finland":         {"id": 2246,  "name": "Finland",         "code": "FI", "region": "Europe"},
    "ireland":         {"id": 2372,  "name": "Ireland",         "code": "IE", "region": "Europe"},
    "greece":          {"id": 2300,  "name": "Greece",          "code": "GR", "region": "Europe"},
    "czech_republic":  {"id": 2203,  "name": "Czech Republic",  "code": "CZ", "region": "Europe"},
    "hungary":         {"id": 2348,  "name": "Hungary",         "code": "HU", "region": "Europe"},
    "romania":         {"id": 2642,  "name": "Romania",         "code": "RO", "region": "Europe"},
    "ukraine":         {"id": 2804,  "name": "Ukraine",         "code": "UA", "region": "Europe"},
    "russia":          {"id": 2643,  "name": "Russia",          "code": "RU", "region": "Europe"},
    # Americas
    "united_states":   {"id": 2840,  "name": "United States",   "code": "US", "region": "Americas"},
    "canada":          {"id": 2124,  "name": "Canada",          "code": "CA", "region": "Americas"},
    "mexico":          {"id": 2484,  "name": "Mexico",          "code": "MX", "region": "Americas"},
    "brazil":          {"id": 2076,  "name": "Brazil",          "code": "BR", "region": "Americas"},
    "argentina":       {"id": 2032,  "name": "Argentina",       "code": "AR", "region": "Americas"},
    "colombia":        {"id": 2170,  "name": "Colombia",        "code": "CO", "region": "Americas"},
    "chile":           {"id": 2152,  "name": "Chile",           "code": "CL", "region": "Americas"},
    "peru":            {"id": 2604,  "name": "Peru",            "code": "PE", "region": "Americas"},
    # Asia-Pacific
    "japan":           {"id": 2392,  "name": "Japan",           "code": "JP", "region": "Asia-Pacific"},
    "china":           {"id": 2156,  "name": "China",           "code": "CN", "region": "Asia-Pacific"},
    "india":           {"id": 2356,  "name": "India",           "code": "IN", "region": "Asia-Pacific"},
    "south_korea":     {"id": 2410,  "name": "South Korea",     "code": "KR", "region": "Asia-Pacific"},
    "australia":       {"id": 2036,  "name": "Australia",       "code": "AU", "region": "Asia-Pacific"},
    "new_zealand":     {"id": 2554,  "name": "New Zealand",     "code": "NZ", "region": "Asia-Pacific"},
    "singapore":       {"id": 2702,  "name": "Singapore",       "code": "SG", "region": "Asia-Pacific"},
    "hong_kong":       {"id": 2344,  "name": "Hong Kong",       "code": "HK", "region": "Asia-Pacific"},
    "taiwan":          {"id": 2158,  "name": "Taiwan",          "code": "TW", "region": "Asia-Pacific"},
    "indonesia":       {"id": 2360,  "name": "Indonesia",       "code": "ID", "region": "Asia-Pacific"},
    "malaysia":        {"id": 2458,  "name": "Malaysia",        "code": "MY", "region": "Asia-Pacific"},
    "thailand":        {"id": 2764,  "name": "Thailand",        "code": "TH", "region": "Asia-Pacific"},
    "vietnam":         {"id": 2704,  "name": "Vietnam",         "code": "VN", "region": "Asia-Pacific"},
    "philippines":     {"id": 2608,  "name": "Philippines",     "code": "PH", "region": "Asia-Pacific"},
    "pakistan":        {"id": 2586,  "name": "Pakistan",        "code": "PK", "region": "Asia-Pacific"},
    "bangladesh":      {"id": 2050,  "name": "Bangladesh",      "code": "BD", "region": "Asia-Pacific"},
    # Middle East & Africa
    "saudi_arabia":    {"id": 2682,  "name": "Saudi Arabia",    "code": "SA", "region": "Middle East"},
    "uae":             {"id": 2784,  "name": "United Arab Emirates","code": "AE", "region": "Middle East"},
    "israel":          {"id": 2376,  "name": "Israel",          "code": "IL", "region": "Middle East"},
    "turkey":          {"id": 2792,  "name": "Turkey",          "code": "TR", "region": "Middle East"},
    "egypt":           {"id": 2818,  "name": "Egypt",           "code": "EG", "region": "Africa"},
    "south_africa":    {"id": 2710,  "name": "South Africa",    "code": "ZA", "region": "Africa"},
    "nigeria":         {"id": 2566,  "name": "Nigeria",         "code": "NG", "region": "Africa"},
    "kenya":           {"id": 2404,  "name": "Kenya",           "code": "KE", "region": "Africa"},
    "ghana":           {"id": 2288,  "name": "Ghana",           "code": "GH", "region": "Africa"},
}


def find_country(query: str) -> Optional[Dict]:
    """
    Find a country by name, key, ISO code, or geo target ID (case-insensitive).

    Examples:
        find_country("italy")    -> {"id": 20854, "name": "Italy", "code": "IT", ...}
        find_country("IT")       -> same
        find_country("20854")    -> same
    """
    q = query.strip().lower()
    # Direct dict key
    if q in COUNTRIES:
        return COUNTRIES[q]
    # Search by code, name, or id
    for key, country in COUNTRIES.items():
        if (country["code"].lower() == q
                or country["name"].lower() == q
                or str(country["id"]) == q):
            return country
    # Partial name / key match
    for key, country in COUNTRIES.items():
        if q in country["name"].lower() or q in key:
            return country
    return None


def geo_resource(geo_target_id: int) -> str:
    """Return the Google Ads resource string for a geo target constant."""
    return f"geoTargetConstants/{geo_target_id}"


def list_countries_by_region(region: str = None) -> List[Dict]:
    """Return countries, optionally filtered by region."""
    countries = list(COUNTRIES.values())
    if region:
        countries = [c for c in countries if c.get("region", "").lower() == region.lower()]
    return sorted(countries, key=lambda x: x["name"])
