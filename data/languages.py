"""
Google Ads language constants.

Usage:
    from data.languages import LANGUAGES, find_language

    lang = find_language("italian")      # -> {"id": 1004, "name": "Italian", "code": "it"}
    resource = f"languageConstants/{lang['id']}"
"""

from typing import Dict, List, Optional

# Official Google Ads language criterion IDs
# Source: languageConstant resource (Google Ads API)
LANGUAGES: Dict[str, Dict] = {
    "arabic":              {"id": 1019, "name": "Arabic",              "code": "ar"},
    "bengali":             {"id": 1056, "name": "Bengali",             "code": "bn"},
    "bulgarian":           {"id": 1020, "name": "Bulgarian",           "code": "bg"},
    "catalan":             {"id": 1038, "name": "Catalan",             "code": "ca"},
    "chinese_simplified":  {"id": 1017, "name": "Chinese (Simplified)","code": "zh_CN"},
    "chinese_traditional": {"id": 1018, "name": "Chinese (Traditional)","code": "zh_TW"},
    "croatian":            {"id": 1039, "name": "Croatian",            "code": "hr"},
    "czech":               {"id": 1021, "name": "Czech",               "code": "cs"},
    "danish":              {"id": 1009, "name": "Danish",              "code": "da"},
    "dutch":               {"id": 1010, "name": "Dutch",               "code": "nl"},
    "english":             {"id": 1000, "name": "English",             "code": "en"},
    "estonian":            {"id": 1043, "name": "Estonian",            "code": "et"},
    "filipino":            {"id": 1042, "name": "Filipino",            "code": "tl"},
    "finnish":             {"id": 1011, "name": "Finnish",             "code": "fi"},
    "french":              {"id": 1002, "name": "French",              "code": "fr"},
    "german":              {"id": 1001, "name": "German",              "code": "de"},
    "greek":               {"id": 1022, "name": "Greek",               "code": "el"},
    "gujarati":            {"id": 1072, "name": "Gujarati",            "code": "gu"},
    "hebrew":              {"id": 1027, "name": "Hebrew",              "code": "iw"},
    "hindi":               {"id": 1023, "name": "Hindi",               "code": "hi"},
    "hungarian":           {"id": 1025, "name": "Hungarian",           "code": "hu"},
    "icelandic":           {"id": 1026, "name": "Icelandic",           "code": "is"},
    "indonesian":          {"id": 1024, "name": "Indonesian",          "code": "id"},
    "italian":             {"id": 1004, "name": "Italian",             "code": "it"},
    "japanese":            {"id": 1005, "name": "Japanese",            "code": "ja"},
    "kannada":             {"id": 1086, "name": "Kannada",             "code": "kn"},
    "korean":              {"id": 1012, "name": "Korean",              "code": "ko"},
    "latvian":             {"id": 1028, "name": "Latvian",             "code": "lv"},
    "lithuanian":          {"id": 1029, "name": "Lithuanian",          "code": "lt"},
    "malay":               {"id": 1102, "name": "Malay",               "code": "ms"},
    "malayalam":           {"id": 1098, "name": "Malayalam",           "code": "ml"},
    "marathi":             {"id": 1101, "name": "Marathi",             "code": "mr"},
    "norwegian":           {"id": 1013, "name": "Norwegian",           "code": "no"},
    "persian":             {"id": 1064, "name": "Persian",             "code": "fa"},
    "polish":              {"id": 1030, "name": "Polish",              "code": "pl"},
    "portuguese":          {"id": 1014, "name": "Portuguese",          "code": "pt"},
    "punjabi":             {"id": 1110, "name": "Punjabi",             "code": "pa"},
    "romanian":            {"id": 1032, "name": "Romanian",            "code": "ro"},
    "russian":             {"id": 1031, "name": "Russian",             "code": "ru"},
    "serbian":             {"id": 1035, "name": "Serbian",             "code": "sr"},
    "slovak":              {"id": 1033, "name": "Slovak",              "code": "sk"},
    "slovenian":           {"id": 1034, "name": "Slovenian",           "code": "sl"},
    "spanish":             {"id": 1003, "name": "Spanish",             "code": "es"},
    "swedish":             {"id": 1015, "name": "Swedish",             "code": "sv"},
    "tamil":               {"id": 1130, "name": "Tamil",               "code": "ta"},
    "telugu":              {"id": 1131, "name": "Telugu",              "code": "te"},
    "thai":                {"id": 1044, "name": "Thai",                "code": "th"},
    "turkish":             {"id": 1037, "name": "Turkish",             "code": "tr"},
    "ukrainian":           {"id": 1036, "name": "Ukrainian",           "code": "uk"},
    "urdu":                {"id": 1041, "name": "Urdu",                "code": "ur"},
    "vietnamese":          {"id": 1040, "name": "Vietnamese",          "code": "vi"},
}


def find_language(query: str) -> Optional[Dict]:
    """
    Find a language by name, key, or ISO code (case-insensitive).

    Examples:
        find_language("italian")   -> {"id": 1004, "name": "Italian", "code": "it"}
        find_language("it")        -> {"id": 1004, ...}
        find_language("1004")      -> {"id": 1004, ...}
    """
    q = query.strip().lower()
    # Direct key match
    if q in LANGUAGES:
        return LANGUAGES[q]
    # Search by code or name
    for key, lang in LANGUAGES.items():
        if lang["code"].lower() == q or lang["name"].lower() == q:
            return lang
        if str(lang["id"]) == q:
            return lang
    # Partial name match
    for key, lang in LANGUAGES.items():
        if q in lang["name"].lower() or q in key:
            return lang
    return None


def language_resource(language_id: int) -> str:
    """Return the Google Ads resource string for a language constant."""
    return f"languageConstants/{language_id}"


def list_all_languages() -> List[Dict]:
    """Return all languages as a sorted list."""
    return sorted(LANGUAGES.values(), key=lambda x: x["name"])
