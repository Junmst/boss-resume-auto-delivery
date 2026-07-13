# -*- coding: utf-8 -*-
"""岗位筛选模块 - 根据配置条件过滤职位"""
import re
import logging

logger = logging.getLogger(__name__)


class JobFilter:
    """职位筛选器"""

    def __init__(self, config):
        self.config = config
        self.filter_config = config.get_filter_config()
        self.blacklist_companies = config.get_blacklist_companies()
        self.blacklist_keywords = config.get_blacklist_keywords()

    def is_valid_job(self, job_info):
        """综合判断职位是否有效"""
        checks = [
            ("关键词匹配", self._check_keywords, job_info),
            ("薪资范围", self._check_salary, job_info),
            ("公司黑名单", self._check_company, job_info),
            ("关键词黑名单", self._check_blacklist_keywords, job_info),
        ]

        for check_name, check_func, info in checks:
            if not check_func(info):
                logger.debug(f"过滤 [{check_name}]: {info.get('title')} - {info.get('company')}")
                return False

        return True

    def _check_keywords(self, job_info):
        """检查必须包含的关键词"""
        required = self.filter_config.get("required_keywords", [])
        if not required:
            return True

        # 获取职位标题和描述文本
        text = f"{job_info.get('title', '')}"
        desc = job_info.get("description", "")
        if desc:
            text += " " + desc

        normalized_text = text.casefold()
        for keyword in required:
            # 支持 | 分隔的"或"条件，并统一忽略英文大小写。
            if "|" in keyword:
                sub_keywords = keyword.split("|")
                if not any(item.strip().casefold() in normalized_text for item in sub_keywords):
                    logger.debug(f"缺少关键词(或条件): {keyword}")
                    return False
            elif keyword.casefold() not in normalized_text:
                logger.debug(f"缺少关键词: {keyword}")
                return False

        return True

    def _check_salary(self, job_info):
        """检查薪资是否符合期望"""
        min_salary = self.filter_config.get("min_salary", 0)
        if min_salary <= 0:
            return True

        salary_text = job_info.get("salary", "")
        if not salary_text:
            return True  # 没有薪资信息时放行

        # 解析各种薪资格式: "15-30K", "15K-30K", "15-30K·13薪", "15000-30000元/月"
        patterns = [
            r"(\d+)\s*[kK]\s*-\s*(\d+)\s*[kK]",  # 15K-30K
            r"(\d+)\s*-\s*(\d+)\s*[kK]",          # 15-30K
            r"(\d+)\s*-\s*(\d+)\s*元",             # 15000-30000元
            r"(\d+)k\s*-\s*(\d+)k",                 # 15k-30k
            r"(\d+)\s*-\s*(\d+)",                    # 15-30
        ]

        for pattern in patterns:
            match = re.search(pattern, salary_text, re.IGNORECASE)
            if match:
                try:
                    low = int(match.group(1))
                    high = int(match.group(2))
                    # 判断最低薪资是否达到期望
                    if low < min_salary:
                        logger.debug(f"薪资不达标: {low}K < {min_salary}K")
                        return False
                    return True
                except (ValueError, IndexError):
                    continue

        # 如果无法解析薪资，默认放行
        return True

    def _check_company(self, job_info):
        """检查公司是否在黑名单中"""
        company = job_info.get("company", "")
        if not company:
            return True

        if company in self.blacklist_companies:
            logger.debug(f"公司黑名单: {company}")
            return False

        return True

    def _check_blacklist_keywords(self, job_info):
        """检查是否包含黑名单关键词"""
        text = f"{job_info.get('title', '')}"
        desc = job_info.get("description", "")
        if desc:
            text += " " + desc

        normalized_text = text.casefold()
        excluded_keywords = self.filter_config.get("excluded_keywords", [])
        for keyword in [*excluded_keywords, *self.blacklist_keywords]:
            if keyword and keyword.casefold() in normalized_text:
                logger.debug(f"命中排除关键词: {keyword}")
                return False

        return True

    def filter_batch(self, jobs):
        """批量筛选职位"""
        valid = []
        filtered = 0

        for job in jobs:
            if self.is_valid_job(job):
                valid.append(job)
            else:
                filtered += 1

        logger.info(f"筛选结果: 通过 {len(valid)} / 过滤 {filtered} / 总数 {len(jobs)}")
        return valid
