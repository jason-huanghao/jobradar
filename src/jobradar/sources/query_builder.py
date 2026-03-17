"""Generate platform-specific search queries from a CandidateProfile."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models.candidate import CandidateProfile
from ..models.job import SearchQuery

logger = logging.getLogger(__name__)

# ── Role vocabulary ────────────────────────────────────────────────

_ROLE_DE: dict[str, str] = {
    "AI Engineer": "KI-Ingenieur",
    "Machine Learning Engineer": "Machine-Learning-Ingenieur",
    "Deep Learning Engineer": "Deep-Learning-Ingenieur",
    "Applied AI Researcher": "KI-Forscher",
    "Data Scientist": "Datenwissenschaftler",
    "Data Engineer": "Dateningenieur",
    "MLOps Engineer": "MLOps-Ingenieur",
    "Backend Engineer": "Backend-Entwickler",
    "Software Engineer": "Softwareentwickler",
    "Platform Engineer": "Plattform-Ingenieur",
    "Cloud Engineer": "Cloud-Ingenieur",
    "AI Product Manager": "KI-Produktmanager",
    "Research Scientist": "Wissenschaftlicher Mitarbeiter",
    "Solutions Architect": "Lösungsarchitekt",
    "Developer Relations": "Developer Relations",
    "LLM Engineer": "LLM-Ingenieur",
    "Algorithm Engineer": "Algorithmus-Ingenieur",
}

_ROLE_CN: dict[str, str] = {
    "AI Engineer": "AI工程师",
    "Machine Learning Engineer": "机器学习工程师",
    "Deep Learning Engineer": "深度学习工程师",
    "Applied AI Researcher": "AI算法研究员",
    "Data Scientist": "数据科学家",
    "Data Engineer": "数据工程师",
    "MLOps Engineer": "MLOps工程师",
    "Backend Engineer": "后端工程师",
    "Software Engineer": "软件工程师",
    "Platform Engineer": "平台工程师",
    "AI Product Manager": "AI产品经理",
    "Research Scientist": "研究科学家",
    "Solutions Architect": "解决方案架构师",
    "LLM Engineer": "大模型工程师",
    "Algorithm Engineer": "算法工程师",
}

_CN_LOCS = {
    "北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "西安",
    "beijing", "shanghai", "shenzhen", "guangzhou", "hangzhou",
    "chengdu", "wuhan", "nanjing", "xian", "china", "cn", "中国",
}

_CN_CITY_CODES: dict[str, str] = {
    "北京": "101010100", "beijing": "101010100",
    "上海": "101020100", "shanghai": "101020100",
    "深圳": "101280600", "shenzhen": "101280600",
    "广州": "101280100", "guangzhou": "101280100",
    "杭州": "101210100", "hangzhou": "101210100",
    "成都": "101270100", "chengdu": "101270100",
    "武汉": "101200100", "wuhan": "101200100",
    "南京": "101190100", "nanjing": "101190100",
    "西安": "101110100", "xian": "101110100",
}


def build_queries(
    profile: CandidateProfile,
    config: AppConfig,
    max_results_override: int | None = None,
) -> list[SearchQuery]:
    """Generate search queries from profile + config, capped sensibly.

    Args:
        profile: Parsed candidate profile.
        config:  App configuration.
        max_results_override: If set, overrides config.search.max_results_per_source
                              for every query (useful for quick/test runs).
    """
    locations = config.search.locations or profile.target.locations or ["Germany"]
    max_results = max_results_override or config.search.max_results_per_source

    # ── Determine keyword sets ──────────────────────────────────────
    if config.search.custom_keywords:
        kw_en = list(config.search.custom_keywords)
        kw_de: list[str] = []
        logger.info("Using custom keywords: %s", kw_en)
    else:
        kw_en = list(profile.target.roles) if profile.target.roles else _derive_keywords(profile)
        kw_de = list(profile.target.roles_de) if profile.target.roles_de else []
        for en in kw_en:
            de = _ROLE_DE.get(en)
            if de and de not in kw_de:
                kw_de.append(de)

    # CN keywords only when CN sources are enabled
    cn_on = any([
        getattr(config.sources.bosszhipin, "enabled", False),
        getattr(config.sources.lagou, "enabled", False),
        getattr(config.sources.zhilian, "enabled", False),
    ])
    kw_cn: list[str] = []
    if cn_on:
        kw_cn = list(profile.target.roles_cn) if profile.target.roles_cn else []
        for en in kw_en:
            cn = _ROLE_CN.get(en)
            if cn and cn not in kw_cn:
                kw_cn.append(cn)

    # Cap keywords to avoid query explosion
    kw_en = kw_en[:8]
    kw_de = kw_de[:6]
    kw_cn = kw_cn[:6]

    eu_locs = [l for l in locations if l.lower() not in _CN_LOCS]
    cn_locs = [l for l in locations if l.lower() in _CN_LOCS] or (["上海"] if cn_on else [])

    queries: list[SearchQuery] = []

    # extra dict shared by all EU sources — always includes max_results
    def eu_extra(**kwargs) -> dict:
        return {"radius_km": config.search.radius_km, "max_results": max_results, **kwargs}

    # ── EU sources ─────────────────────────────────────────────────
    for kw in kw_en + kw_de:
        lang = "de" if kw in kw_de else "en"
        for loc in eu_locs:
            if config.sources.arbeitsagentur.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="arbeitsagentur",
                    language=lang, extra=eu_extra(),
                ))
            if config.sources.jobspy.enabled:
                for board in config.sources.jobspy.boards:
                    queries.append(SearchQuery(
                        keyword=kw, location=loc, source=f"jobspy:{board}",
                        language=lang,
                        extra=eu_extra(
                            country=config.sources.jobspy.country,
                            board=board,
                        ),
                    ))
            if config.sources.stepstone.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="stepstone", language=lang,
                    extra=eu_extra(postal_code=config.search.postal_code),
                ))
            if config.sources.xing.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="xing", language=lang,
                    extra=eu_extra(),
                ))

    # ── CN sources ─────────────────────────────────────────────────
    for kw in kw_cn:
        for loc in cn_locs:
            city_code = _CN_CITY_CODES.get(loc.lower(), "101020100")
            cn_base = {"city_code": city_code, "max_results": max_results}
            if config.sources.bosszhipin.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="bosszhipin", language="zh",
                    extra={**cn_base,
                           "delay_between_requests": config.sources.bosszhipin.delay_between_requests},
                ))
            if config.sources.lagou.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="lagou", language="zh",
                    extra={**cn_base,
                           "delay_between_requests": config.sources.lagou.delay_between_requests},
                ))
            if config.sources.zhilian.enabled:
                queries.append(SearchQuery(
                    keyword=kw, location=loc, source="zhilian", language="zh", extra=cn_base,
                ))

    logger.info(
        "Built %d queries (%d EN, %d DE, %d CN) max_results=%d",
        len(queries), len(kw_en), len(kw_de), len(kw_cn), max_results,
    )
    return queries


def _derive_keywords(profile: CandidateProfile) -> list[str]:
    kws: list[str] = []
    for d in profile.skills.domains[:3]:
        kws.append(f"{d} Engineer")
    for exp in profile.experience[:2]:
        if exp.title:
            kws.append(exp.title)
    if not kws:
        tech = profile.skills.technical[:2]
        kws.append(" ".join(tech) + " Developer" if tech else "Software Engineer")
    return kws
