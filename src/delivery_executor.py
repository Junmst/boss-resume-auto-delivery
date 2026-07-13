# -*- coding: utf-8 -*-
"""投递执行模块 - 控制投递流程和频率"""
import time
import random
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


class RateLimiter:
    """请求频率控制器"""

    def __init__(self, max_per_hour=20, max_per_day=100):
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self.hourly_count = 0
        self.daily_count = 0
        self.hour_start = time.time()
        self.day_start = date.today()

    def _reset_if_needed(self):
        """重置计数器"""
        # 检查小时重置
        if time.time() - self.hour_start > 3600:
            self.hourly_count = 0
            self.hour_start = time.time()

        # 检查日期重置
        if date.today() != self.day_start:
            self.daily_count = 0
            self.day_start = date.today()

    def can_proceed(self):
        """检查是否可以继续投递"""
        self._reset_if_needed()

        if self.hourly_count >= self.max_per_hour:
            elapsed = time.time() - self.hour_start
            wait_sec = int(3600 - elapsed)
            logger.warning(
                f"已达到小时投递上限({self.max_per_hour}个)，"
                f"需等待 {wait_sec//60} 分钟"
            )
            return False

        if self.daily_count >= self.max_per_day:
            logger.warning(f"已达到每日投递上限({self.max_per_day}个)，停止运行")
            return False

        return True

    def record_delivery(self):
        """记录一次投递"""
        self.hourly_count += 1
        self.daily_count += 1
        logger.info(
            f"投递计数: 本小时 {self.hourly_count}/{self.max_per_hour}, "
            f"今日 {self.daily_count}/{self.max_per_day}"
        )


class DeliveryExecutor:
    """投递执行器"""

    def __init__(self, driver, config, data_manager, page_handler):
        self.driver = driver
        self.config = config
        self.data_manager = data_manager
        self.page_handler = page_handler

        delivery_config = config.get_delivery_config()
        anti_crawler_config = config.get_anti_crawler_config()

        self.rate_limiter = RateLimiter(
            max_per_hour=delivery_config.get("max_per_hour", 20),
            max_per_day=delivery_config.get("max_per_day", 100),
        )
        self.mode = delivery_config.get("mode", "smart")
        self.auto_greeting = delivery_config.get("auto_send_greeting", True)
        self.greeting_template = delivery_config.get(
            "greeting_template",
            "您好，我对贵公司的{position}职位很感兴趣，期待详细沟通。"
        )
        self.min_delay = anti_crawler_config.get("min_delay", 3)
        self.max_delay = anti_crawler_config.get("max_delay", 8)
        self.mouse_simulation = anti_crawler_config.get("mouse_simulation", True)
        self.max_retry = anti_crawler_config.get("max_retry", 3)

        self.templates = config.get_greeting_templates()
        self.delivery_count = 0

    def deliver_resume(self, job_info):
        """投递单份简历"""
        job_title = job_info.get("title", "未知")
        company = job_info.get("company", "未知")

        # 检查去重
        if self.data_manager.is_delivered(job_info.get("job_id", "")):
            logger.debug(f"已投递过: {job_title} - {company}")
            return False

        # 检查频率限制
        if not self.rate_limiter.can_proceed():
            return False

        # 打开职位详情
        logger.info(f"开始投递: {job_title} - {company}")
        if not self.page_handler.open_job_detail(job_info):
            return False

        # 获取职位描述用于后续筛选
        description = self.page_handler.get_job_description()
        job_info["description"] = description

        # 随机延迟
        self._random_delay(1, 2)

        # 点击「立即沟通」按钮
        if not self.page_handler.click_chat_button():
            logger.warning(f"无法投递: {job_title} - {company}")
            return False

        # 发送打招呼消息
        if self.auto_greeting:
            self._random_delay(0.5, 1.5)
            message = self._generate_message(job_info)
            self.page_handler.send_greeting_message(message)

        # 保存投递记录
        self.data_manager.save_delivery(job_info)
        self.rate_limiter.record_delivery()
        self.delivery_count += 1

        # 操作间隔
        self._random_delay(self.min_delay, self.max_delay)

        logger.info(f"投递成功 ({self.delivery_count}): {job_title} - {company}")
        return True

    def _generate_message(self, job_info):
        """生成打招呼消息"""
        # 如果AI已启用且配置了API，尝试使用AI生成
        api_config = self._load_api_config()
        if api_config.get("enabled") and api_config.get("api_key"):
            try:
                from src.ai_matcher import AIJobMatcher
                matcher = AIJobMatcher(api_config)
                ai_msg = matcher.generate_message(job_info, api_config.get("resume", ""), [])
                if ai_msg and len(ai_msg) > 10:
                    logger.info("使用AI生成打招呼消息")
                    return ai_msg[:150]
            except Exception as e:
                logger.warning(f"AI生成消息失败，回退到模板: {e}")

        # 优先使用模板列表随机选择
        if self.templates:
            template = random.choice(self.templates)
        else:
            template = self.greeting_template

        title = job_info.get("title", "这个职位")
        company = job_info.get("company", "贵公司")

        message = template.format(position=title, company=company)

        # 确保消息长度合理
        if len(message) > 150:
            message = message[:147] + "..."

        return message

    @staticmethod
    def _load_api_config():
        """加载API配置"""
        import json
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "api.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"enabled": False}

    def _random_delay(self, min_sec, max_sec):
        """随机延迟"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
