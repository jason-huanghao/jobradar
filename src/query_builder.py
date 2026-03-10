"""Generate platform-specific search queries from CandidateProfile."""

from __future__ import annotations

import logging

from .config import AppConfig
from .models import CandidateProfile, SearchQuery

logger = logging.getLogger(__name__)

# ── Role vocabulary ─────────────────────────────────────────────────
# Fallback when the CV doesn't contain explicit target roles.
# Covers the AI/ML/data/platform engineering space that this tool
# is primarily designed for.

_ROLE_DE_FALLBACK: dict[str, str] = {
    # AI / ML core
    "AI Engineer":               "KI-Ingenieur",
    "Machine Learning Engineer": "Machine-Learning-Ingenieur",
    "Deep Learning Engineer":    "Deep-Learning-Ingenieur",
    "Applied AI Researcher":     "KI-Forscher",
    "Data Scientist":            "Datenwissenschaftler",
    "Data Engineer":             "Dateningenieur",
    "MLOps Engineer":            "MLOps-Ingenieur",
    # Software / platform
    "Backend Engineer":          "Backend-Entwickler",
    "Software Engineer":         "Softwareentwickler",
    "Platform Engineer":         "Plattform-Ingenieur",
    "Cloud Engineer":            "Cloud-Ingenieur",
    # Product / research
    "AI Product Manager":        "KI-Produktmanager",
    "Research Scientist":        "Wissenschaftlicher Mitarbeiter",
    "Solutions Architect":       "Lösungsarchitekt",
    "Developer Relations":       "Developer Relations",
}

# Chinese role names used when CN platforms are enabled
_ROLE_CN: dict[str, str] = {
    "AI Engineer":               "AI工程师",
    "Machine Learning Engineer": "机器学习工程师",
    "Deep Learning Engineer":    "深度学习工程师",
    "Applied AI Researcher":     "AI算法研究员",
    "Data Scientist":            "数据科学家",
    "Data Engineer":             "数据工程师",
    "MLOps Engineer":            "MLOps工程师",
    "Backend Engineer":          "后端工程师",
    "Software Engineer":         "软件工程师",
    "AI Product Manager":        "AI产品经理",
    "Research Scientist":        "研究科学家",
    "Solutions Architect":       "解决方案架构师",
    "Developer Relations":       "开发者关系",
    "LLM Engineer":              "大模型工程师",
    "Algorithm Engineer":        "算法工程师",
}


def build_queries(profile: CandidateProfile, config: AppConfig) -> list[SearchQuery]:
    """Generate search queries from profile + config.

    Priority:
    1. config.search.custom_keywords (if set, use those)
    2. profile.target.roles + profile.target.roles_de + profile.target.roles_cn
    3. Fallback: extract from skills/experience, then translate via vocabulary tables
    """
    queries: list[SearchQuery] = []
    locations = config.search.locations or profile.target.locations or ["Germany"]

    # ── Determine keyword sets ────────────────────────────────
    keywords_en: list[str] = []
    keywords_de: list[str] = []
    keywords_cn: list[str] = []

    if config.search.custom_keywords:
        keywords_en = list(config.search.custom_keywords)
        logger.info("Using custom keywords: %s", keywords_en)
    else:
        keywords_en = list(profile.target.roles) if profile.target.roles else []
        keywords_de = list(profile.target.roles_de) if profile.target.roles_de else []

        if not keywords_en:
            keywords_en = _derive_keywords(profile)
            logger.info("Derived keywords from profile: %s", keywords_en)

        # Supplement German keywords from fallback table for any EN role not
        # already translated by the LLM
        de_supplement = {
            _ROLE_DE_FALLBACK[en]
            for en in keywords_en
            if en in _ROLE_DE_FALLBACK and _ROLE_DE_FALLBACK[en] not in keywords_de
        }
        keywords_de = list(dict.fromkeys(keywords_de + list(de_supplement)))

    # Build CN keywords only when at least one CN source is enabled
    cn_enabled = (
        getattr(config.sources, "bosszhipin", None) and config.sources.bosszhipin.enabled
    ) or (
        getattr(config.sources, "lagou", None) and config.sources.lagou.enabled
    ) or (
        getattr(config.sources, "zhilian", None) and config.sources.zhilian.enabled
    )
    if cn_enabled:
        cn_from_profile = getattr(profile.target, "roles_cn", [])
        cn_supplement = [
            _ROLE_CN[en]
            for en in keywords_en
            if en in _ROLE_CN
        ]
        keywords_cn = list(dict.fromkeys(list(cn_from_profile) + cn_supplement))

    # ── European source queries ───────────────────────────────
    eu_keywords = keywords_en + keywords_de
    for kw in eu_keywords:
        lang = "de" if kw in keywords_de else "en"
        for loc in locations:
            if _is_cn_location(loc):
                continue  # skip CN-specific locations for EU sources

            if config.sources.arbeitsagentur.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc,
                    source="arbeitsagentur", language=lang,
                    extra={"radius_km": config.search.radius_km,
                           "max_results": config.search.max_results_per_source},
                ))

            if config.sources.jobspy.enabled:
                for board in config.sources.jobspy.boards:
                    queries.append(SearchQuery(
                        keyword=kw, location=loc,
                        source=f"jobspy:{board}", language=lang,
                        extra={"country": config.sources.jobspy.country, "board": board},
                    ))

            if config.sources.stepstone.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="stepstone", language=lang,
                    extra={"postal_code": config.search.postal_code,
                           "radius_km": config.search.radius_km},
                ))

            if config.sources.xing.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="xing", language=lang,
                ))

            if config.sources.linkedin.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="linkedin", language=lang,
                ))

    # ── Chinese source queries ────────────────────────────────
    if cn_enabled and keywords_cn:
        cn_locations = _cn_locations(locations)
        for kw in keywords_cn:
            for loc in cn_locations:
                city_code = _cn_city_code(loc)
                base_extra = {"city_code": city_code,
                              "max_results": config.search.max_results_per_source}

                if config.sources.bosszhipin.enabled:
                    queries.append(SearchQuery(
                        keyword=kw, location=loc,
                        source="bosszhipin", language="zh",
                        extra={**base_extra,
                               "delay_between_requests": config.sources.bosszhipin.delay_between_requests},
                    ))

                if config.sources.lagou.enabled:
                    queries.append(SearchQuery(
                        keyword=kw, location=loc,
                        source="lagou", language="zh",
                        extra={**base_extra,
                               "delay_between_requests": config.sources.lagou.delay_between_requests},
                    ))

                if getattr(config.sources, "zhilian", None) and config.sources.zhilian.enabled:
                    queries.append(SearchQuery(
                        keyword=kw, location=loc,
                        source="zhilian", language="zh",
                        extra=base_extra,
                    ))

    logger.info(
        "Generated %d queries (%d EN, %d DE, %d CN)",
        len(queries), len(keywords_en), len(keywords_de), len(keywords_cn),
    )
    return queries


# ── Helper functions ────────────────────────────────────────────────

_CN_CITY_CODES: dict[str, str] = {
    "北京": "101010100",  "beijing":  "101010100",
    "上海": "101020100",  "shanghai": "101020100",
    "深圳": "101280600",  "shenzhen": "101280600",
    "广州": "101280100",  "guangzhou":"101280100",
    "杭州": "101210100",  "hangzhou": "101210100",
    "成都": "101270100",  "chengdu":  "101270100",
    "武汉": "101200100",  "wuhan":    "101200100",
    "南京": "101190100",  "nanjing":  "101190100",
    "西安": "101110100",  "xian":     "101110100",
}

_CN_LOCATION_KEYWORDS = {
    "北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "西安",
    "beijing", "shanghai", "shenzhen", "guangzhou", "hangzhou", "chengdu",
    "wuhan", "nanjing", "xian", "china", "cn", "中国",
}


def _is_cn_location(loc: str) -> bool:
    return loc.lower() in _CN_LOCATION_KEYWORDS


def _cn_locations(locations: list[str]) -> list[str]:
    """Return CN-flagged locations from the list, default to Shanghai if none."""
    cn = [loc for loc in locations if _is_cn_location(loc)]
    return cn or ["上海"]


def _cn_city_code(loc: str) -> str:
    return _CN_CITY_CODES.get(loc.lower(), "101020100")  # default: Shanghai


def _derive_keywords(profile: CandidateProfile) -> list[str]:
    """Fallback: derive search keywords from skills and experience."""
    keywords: list[str] = []

    for domain in profile.skills.domains[:3]:
        keywords.append(f"{domain} Engineer")

    for exp in profile.experience[:2]:
        if exp.title:
            keywords.append(exp.title)

    if not keywords:
        tech = profile.skills.technical[:3]
        if tech:
            keywords.append(" ".join(tech[:2]) + " Developer")
        else:
            keywords.append("Software Engineer")

    return keywords
