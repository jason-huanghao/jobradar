"""Job translator for English/German to Chinese translation.

Uses LLM with caching for efficient translation of job data.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import AppConfig
from ..llm_client import LLMClient

logger = logging.getLogger(__name__)


# Translation cache
class TranslationCache:
    """In-memory cache for job translations."""

    def __init__(self, cache_dir: Path):
        self.cache_file = cache_dir / "translation_cache.json"
        self._cache: dict = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load translations from disk."""
        if self.cache_file.exists():
            try:
                self._cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
                logger.info(f"Loaded translation cache: {len(self._cache)} entries")
            except Exception as e:
                logger.error(f"Failed to load translation cache: {e}")

    def _save_cache(self) -> None:
        """Save translations to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.debug(f"Saved translation cache: {len(self._cache)} entries")
        except Exception as e:
            logger.error(f"Failed to save translation cache: {e}")

    def get(self, job_id: str, field: str) -> Optional[str]:
        """Get cached translation for a job field."""
        cache_key = f"{job_id}:{field}"
        return self._cache.get(cache_key)

    def set(self, job_id: str, field: str, translation: str) -> None:
        """Set cached translation for a job field."""
        cache_key = f"{job_id}:{field}"
        self._cache[cache_key] = translation
        self._save_cache()

    def get_all(self, job_id: str) -> dict:
        """Get all cached translations for a job."""
        job_translations = {
            k.split(":")[1]: v
            for k, v in self._cache.items()
            if k.startswith(f"{job_id}:")
        }
        return job_translations


class JobTranslator:
    """Translate job data from English/German to Chinese using LLM."""

    COMMON_JOB_TITLES = {
        "AI Engineer": "AI工程师",
        "Machine Learning Engineer": "机器学习工程师",
        "Data Scientist": "数据科学家",
        "Data Analyst": "数据分析师",
        "Software Engineer": "软件工程师",
        "Frontend Developer": "前端工程师",
        "Backend Developer": "后端工程师",
        "Full Stack Developer": "全栈工程师",
        "DevOps Engineer": "DevOps工程师",
        "Product Manager": "产品经理",
        "Project Manager": "项目经理",
        "Technical Lead": "技术负责人",
        "Architect": "架构师",
        "Senior Engineer": "高级工程师",
        "Junior Engineer": "初级工程师",
        "Intern": "实习生",
        "Research Scientist": "研究员",
        "Applied Scientist": "应用科学家",
    }

    COMMON_LOCATIONS = {
        "Berlin": "柏林",
        "Munich": "慕尼黑",
        "Hamburg": "汉堡",
        "Frankfurt": "法兰克福",
        "Stuttgart": "斯图加特",
        "Dusseldorf": "杜塞尔多夫",
        "Cologne": "科隆",
        "Beijing": "北京",
        "Shanghai": "上海",
        "Shenzhen": "深圳",
        "Hangzhou": "杭州",
        "Guangzhou": "广州",
        "Chengdu": "成都",
        "Remote": "远程",
        "Germany": "德国",
        "China": "中国",
    }

    COMMON_COMPANY_TYPES = {
        "GmbH": "有限责任公司",
        "AG": "股份公司",
        "Ltd": "有限公司",
        "LLC": "有限责任公司",
        "Co., Ltd.": "股份有限公司",
        "Inc.": "公司",
    }

    def __init__(self, config: AppConfig):
        """
        Initialize job translator.

        Args:
            config: Application configuration
        """
        self.config = config
        self.llm = LLMClient(config.llm.text)
        self.cache_dir = config.resolve_path(config.runtime.cache_dir)
        self.cache = TranslationCache(self.cache_dir)

    def _get_dictionary_translation(self, text: str, field_type: str = "title") -> Optional[str]:
        """Try to get translation from dictionary first."""
        if field_type == "title":
            return self.COMMON_JOB_TITLES.get(text, None)
        elif field_type == "location":
            return self.COMMON_LOCATIONS.get(text, None)
        elif field_type == "company":
            for company_type, translation in self.COMMON_COMPANY_TYPES.items():
                if company_type in text:
                    return translation
        return None

    async def translate_job(
        self, job_id: str, title: str, company: str, location: str,
        description: Optional[str] = None
    ) -> dict:
        """
        Translate job fields to Chinese.

        Args:
            job_id: Unique job identifier
            title: Job title
            company: Company name
            location: Job location
            description: Job description (optional, can be very long)

        Returns:
            Dictionary with translated fields:
            {
                "title_cn": "",
                "company_cn": "",
                "location_cn": "",
                "description_cn": "",
            }
        """
        translations = {
            "title_cn": "",
            "company_cn": "",
            "location_cn": "",
            "description_cn": "",
        }

        fields_to_translate = []
        if title:
            dict_trans = self._get_dictionary_translation(title, "title")
            if dict_trans:
                translations["title_cn"] = dict_trans
            else:
                fields_to_translate.append(("title", title))

        if company:
            dict_trans = self._get_dictionary_translation(company, "company")
            if dict_trans:
                translations["company_cn"] = dict_trans
            else:
                fields_to_translate.append(("company", company))

        if location:
            dict_trans = self._get_dictionary_translation(location, "location")
            if dict_trans:
                translations["location_cn"] = dict_trans
            else:
                fields_to_translate.append(("location", location))

        # If description is provided, translate it (truncated to first 500 chars)
        if description:
            desc_truncated = description[:500] if description else ""
            if desc_truncated:
                fields_to_translate.append(("description", desc_truncated))

        # If we have dictionary translations only, no LLM call needed
        if not fields_to_translate:
            logger.info(f"Job {job_id}: All fields translated from dictionary")
            self._update_cache(job_id, translations)
            return translations

        # Batch translate remaining fields with LLM
        if fields_to_translate:
            translations = await self._translate_with_llm(job_id, fields_to_translate)

        self._update_cache(job_id, translations)
        return translations

    async def _translate_with_llm(
        self, job_id: str, fields: list[tuple[str, str]]
    ) -> dict:
        """Translate fields using LLM."""
        field_names = ", ".join([f for f, _ in fields])
        
        prompt = f"""Translate the following job information to Chinese (Simplified). Keep technical terms in English.

Title: {fields[0][1]}
Company: {fields[1][1]}
Location: {fields[2][1]}
Description: {fields[3][1] if len(fields) > 3 else ''}

Return JSON: {{"title_cn": "Chinese translation for title field", "company_cn": "Chinese translation for company field", "location_cn": "Chinese translation for location field", "description_cn": "Chinese translation for description field"}}"""
        try:
            response = await self.llm.complete(prompt, temperature=0.2, max_tokens=1000)
            content = response.strip()
            
            try:
                result = json.loads(content)
                translations = {
                    "title_cn": result.get("title_cn", ""),
                    "company_cn": result.get("company_cn", ""),
                    "location_cn": result.get("location_cn", ""),
                    "description_cn": result.get("description_cn", ""),
                }
                logger.info(f"Job {job_id}: LLM translation successful")
                return translations
            except json.JSONDecodeError:
                logger.warning(f"Job {job_id}: LLM response not valid JSON")
                # Fallback: return empty translations
                translations = {
                    "title_cn": "",
                    "company_cn": "",
                    "location_cn": "",
                    "description_cn": "",
                }
                return translations
        except Exception as e:
            logger.error(f"Job {job_id}: LLM translation failed: {e}")
            # Fallback: return empty translations
            translations = {
                "title_cn": "",
                "company_cn": "",
                "location_cn": "",
                "description_cn": "",
            }
            return translations

    def get_cache_stats(self) -> dict:

        return {
            "total_entries": len(self.cache._cache),
            "cache_file": str(self.cache.cache_file),
        }

    async def translate_batch(
        self, jobs: list[tuple[str, str, str, str]], batch_size: int = 5
    ) -> list[dict]:
        """Translate multiple jobs in batches for efficiency."""
        if not jobs:
            return []

        results = []
        total = len(jobs)

        # Create tasks for each job
        tasks = [self.translate_job(job_id, title, company, location, description)
                 for job_id, title, company, location, description in jobs]

        # Process in batches
        batch_results = await asyncio.gather(*tasks)

        for i, result in enumerate(batch_results):
            job_id = jobs[i][0]
            results.append({
                "job_id": job_id,
                **result
            })

        logger.info(f"Translated {len(results)}/{total} jobs in batches")

        # Rate limiting delay between batches
        if total > batch_size:
            await asyncio.sleep(1.0)

        return results
