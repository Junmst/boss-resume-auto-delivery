# -*- coding: utf-8 -*-
"""AI 智能岗位匹配模块 —— 调用配置的 AI API 对抓取的岗位信息进行多标签匹配、打分和关键信息提取。"""
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AIJobMatcher:
    """基于简历和标签的 AI 岗位匹配器"""

    def __init__(self, api_config: dict):
        self.api_config = api_config
        self.enabled = bool(api_config.get("enabled"))

    # ---- 公共接口 ----------------------------------------------------------

    def match_jobs(self, jobs: list, resume: str, tags: list) -> list:
        """对岗位列表进行 AI 匹配打分，返回按匹配度降序的结果列表。"""
        if not self.enabled:
            logger.warning("AI 功能未开启，回退为简单标签计数匹配")
            return self._fallback_match(jobs, tags)

        if not jobs:
            return []

        try:
            scored = self._call_ai_batch(jobs, resume, tags)
            scored.sort(key=lambda j: j.get("match_score", 0), reverse=True)
            return scored
        except Exception as exc:
            logger.error(f"AI 匹配请求失败，回退为简单标签计数匹配: {exc}")
            return self._fallback_match(jobs, tags)

    def generate_message(self, job_info: dict, resume: str, tags: list) -> str:
        """为单个岗位生成个性化打招呼消息。"""
        if not self.enabled:
            return ""

        prompt = self._build_message_prompt(job_info, resume, tags)
        try:
            reply = self._call_ai(prompt, max_tokens=400)
            return reply.strip()[:500]
        except Exception as exc:
            logger.error(f"AI 消息生成失败: {exc}")
            return ""

    def analyze_job_detail(self, job_info: dict, resume: str, tags: list) -> dict:
        """对单个岗位的详情做深度分析，返回关键信息和匹配理由。"""
        if not self.enabled:
            return {}

        prompt = self._build_detail_prompt(job_info, resume, tags)
        try:
            reply = self._call_ai(prompt, max_tokens=600)
            return self._parse_detail_analysis(reply, job_info)
        except Exception as exc:
            logger.error(f"AI 详情分析失败: {exc}")
            return {}

    # ---- 内部 ------------------------------------------------------------

    @staticmethod
    def _fallback_match(jobs: list, tags: list) -> list:
        """不依赖 AI 的多标签联合匹配：以命中标签数量为主要排序依据。
        命中数量越多分越高；职位名命中权重 > 标签字段命中 > 要求字段命中。
        """
        tags_lower = [t.lower() for t in tags]
        for job in jobs:
            title_lower = (job.get("title", "") or "").lower()
            req_lower = (job.get("requirements", "") or "").lower()
            tags_text = " ".join(job.get("tags", []) or []).lower()
            full_text = f"{title_lower} {req_lower} {tags_text}"

            matched = [tags[i] for i, t in enumerate(tags_lower) if t in full_text]
            title_hits = [tags[i] for i, t in enumerate(tags_lower) if t in title_lower]
            tag_hits = [tags[i] for i, t in enumerate(tags_lower) if t in tags_text]
            req_hits = [tags[i] for i, t in enumerate(tags_lower) if t in req_lower]
            missed = [t for t in tags if t not in matched]

            # 主分：每个命中标签 100 分；副分：职位名/标签字段/要求命中分别额外加分
            score = len(matched) * 100 + len(title_hits) * 50 + len(tag_hits) * 30 + len(req_hits) * 10
            if len(matched) == len(tags) and len(tags) > 0:
                score += 200  # 命中全部标签额外奖励

            # 不再封顶 99，避免命中更多标签时分值相同
            job["match_score"] = score
            job["matched_tags"] = matched
            job["missed_tags"] = missed
            job["title_hits"] = title_hits
            if len(matched) == len(tags) and len(tags) > 0:
                job["match_summary"] = f"命中全部 {len(tags)} 个标签: {', '.join(matched)}"
            elif matched:
                job["match_summary"] = f"命中 {len(matched)}/{len(tags)} 个标签: {', '.join(matched)}"
            else:
                job["match_summary"] = "未命中任何标签"
        jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        return jobs

    def _call_ai_batch(self, jobs: list, resume: str, tags: list) -> list:
        """调用 AI 批量打分。每批最多 15 个岗位，分批请求。"""
        batch_size = 15
        all_scored = []
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            prompt = self._build_scoring_prompt(batch, resume, tags)
            reply = self._call_ai(prompt, max_tokens=2000)
            scored = self._parse_scoring_response(reply, batch)
            all_scored.extend(scored)
        return all_scored

    def _build_scoring_prompt(self, jobs: list, resume: str, tags: list) -> str:
        jobs_json = []
        for idx, job in enumerate(jobs):
            jobs_json.append({
                "id": idx,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "salary": job.get("salary", ""),
                "location": job.get("location", ""),
                "tags": job.get("tags", []),
                "requirements": job.get("requirements", ""),
            })

        return f"""你是一个专业的招聘匹配分析师。请根据以下信息，对每个岗位进行多标签联合匹配评分。

【评分核心规则】—— 最重要的排序依据是"同时命中意向标签的数量"：
- 命中所有 {len(tags)} 个标签的岗位 → 最高分（90-99分）
- 命中 N 个标签的岗位 → 第二梯队（每少一个扣 8-10 分）
- 仅命中 1 个标签的岗位 → 低分
- 没有任何一个意向标签命中的岗位 → 接近 0 分
- 同等命中数量下，再看简历与岗位描述的契合度、薪资、地点
- 职位名称中命中的标签比职位描述/要求中命中的标签权重更高

【我的简历/背景】
{resume if resume else "（未提供简历，请仅基于标签匹配）"}

【我的意向标签（共 {len(tags)} 个）】
{', '.join(tags)}

【待评估岗位列表】
{json.dumps(jobs_json, ensure_ascii=False, indent=2)}

请对每个岗位返回 JSON 格式的分析结果，包含：
- id: 岗位编号
- match_score: 匹配度分数(0-99)，**先按命中标签数打分**（命中全部标签至少 90 分，命中一半 70-80 分，仅命中 1 个 50 分以下）
- matched_tags: 命中的意向标签列表（按出现顺序）
- missed_tags: 未命中的意向标签列表
- match_summary: 30字以内，重点说明"命中了几个标签"以及简要理由
- key_info: {{"tech_stack": "技术栈", "highlights": "亮点", "concerns": "需要注意的点"}}

请只返回一个 JSON 数组，不要包含其他文字："""

    def _build_detail_prompt(self, job_info: dict, resume: str, tags: list) -> str:
        return f"""你是一个专业的岗位分析师。请深入分析以下岗位是否适合我。

【我的简历/背景】
{resume if resume else "（未提供）"}

【意向标签】
{', '.join(tags)}

【岗位信息】
职位: {job_info.get('title', '')}
公司: {job_info.get('company', '')}
薪资: {job_info.get('salary', '')}
地点: {job_info.get('location', '')}
标签: {', '.join(job_info.get('tags', []))}
要求: {job_info.get('requirements', '')}

请返回 JSON，包含：
- overall_score: 综合匹配度(0-100)
- pros: 数组,我匹配这个岗位的优势(2-3条)
- cons: 数组,可能不匹配的点(1-2条)
- tech_stack: 主要技术栈
- suggestion: 是否推荐投递及简短理由
- greeting_hint: 打招呼时可以强调的点

只返回 JSON，不要其他文字："""

    def _build_message_prompt(self, job_info: dict, resume: str, tags: list) -> str:
        return f"""你是一个求职助手，需要为以下岗位写一段简短的打招呼消息。

我的背景: {resume[:300] if resume else '技术开发背景'}

岗位: {job_info.get('title', '')} - {job_info.get('company', '')}
薪资: {job_info.get('salary', '')}
要求: {(job_info.get('requirements', '') or '')[:200]}

要求：
- 50-150字
- 自然真诚，不要模板化
- 结合岗位要求，突出匹配的技能或经验
- 不要求回复，只是简单介绍自己和表达兴趣
- 只返回消息内容，不要加任何前缀"""

    def _call_ai(self, prompt: str, max_tokens: int = 1000) -> str:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.api_config.get("model", "gpt-3.5-turbo"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": float(self.api_config.get("temperature", 0.3)),
        }

        api_base = self.api_config.get("api_base", "https://api.openai.com/v1").rstrip("/")
        resp = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"AI API 返回 HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _parse_scoring_response(reply: str, batch: list) -> list:
        """从 AI 返回中提取 JSON 评分数组，并合并回原岗位数据。"""
        # 尝试提取 JSON 数组
        json_str = reply
        start = reply.find("[")
        end = reply.rfind("]")
        if start != -1 and end != -1:
            json_str = reply[start:end + 1]

        scores = json.loads(json_str)
        id_map = {item.get("id"): item for item in scores}

        scored = []
        for idx, job in enumerate(batch):
            analysis = id_map.get(idx, {})
            job["match_score"] = analysis.get("match_score", 0)
            job["matched_tags"] = analysis.get("matched_tags", [])
            job["missed_tags"] = analysis.get("missed_tags", [])
            job["match_summary"] = analysis.get("match_summary", "")
            job["key_info"] = analysis.get("key_info", {})
            scored.append(job)

        # AI 已按规则评分，但仍按 score 兜底排序以防 AI 没排序
        scored.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        return scored

    @staticmethod
    def _parse_detail_analysis(reply: str, job_info: dict) -> dict:
        json_str = reply
        start = reply.find("{")
        end = reply.rfind("}")
        if start != -1 and end != -1:
            json_str = reply[start:end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"overall_score": 0, "pros": [], "cons": [], "suggestion": reply[:200]}
