# -*- coding: utf-8 -*-
import os
import json
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path="config/config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.blacklist = {"companies": [], "keywords": []}
        self.templates = []
        self._load_all()

    def _load_all(self):
        self._load_yaml_config()
        self._load_blacklist()
        self._load_templates()

    def _load_yaml_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"配置加载成功: {self.config_path}")
            else:
                logger.warning(f"配置文件不存在: {self.config_path}")
                self.config = self._default_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.config = self._default_config()

    def _load_blacklist(self):
        blacklist_path = "config/blacklist.json"
        try:
            if os.path.exists(blacklist_path):
                with open(blacklist_path, "r", encoding="utf-8") as f:
                    self.blacklist = json.load(f)
        except Exception as e:
            logger.warning(f"加载黑名单失败: {e}")

    def _load_templates(self):
        templates_path = "config/templates.json"
        try:
            if os.path.exists(templates_path):
                with open(templates_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.templates = data.get("greeting_templates", [])
        except Exception as e:
            logger.warning(f"加载模板失败: {e}")

    def get(self, key, default=None):
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value if value is not None else default

    def get_search_config(self):
        return self.config.get("search", {})

    def get_filter_config(self):
        return self.config.get("filter", {})

    def get_delivery_config(self):
        return self.config.get("delivery", {})

    def get_anti_crawler_config(self):
        return self.config.get("anti_crawler", {})

    def get_browser_config(self):
        return self.config.get("browser", {})

    def get_blacklist_companies(self):
        return self.blacklist.get("companies", [])

    def get_blacklist_keywords(self):
        return self.blacklist.get("keywords", [])

    def get_greeting_templates(self):
        return self.templates

    @staticmethod
    def _default_config():
        return {
            "app": {"name": "BOSS自动投递工具", "version": "1.0.0", "log_level": "INFO"},
            "browser": {"type": "edge", "headless": False, "window_size": [1920, 1080]},
            "search": {"keywords": ["Python开发工程师"], "city": "北京"},
            "filter": {"required_keywords": ["Python"], "excluded_keywords": ["外包", "996"], "min_salary": 15},
            "delivery": {"mode": "smart", "max_per_hour": 20, "max_per_day": 100,
                         "greeting_template": "您好，我对贵公司的{position}职位很感兴趣。",
                         "auto_send_greeting": True, "test_mode": False},
            "anti_crawler": {"min_delay": 3, "max_delay": 8, "random_scroll": True, "mouse_simulation": True, "max_retry": 3},
        }
