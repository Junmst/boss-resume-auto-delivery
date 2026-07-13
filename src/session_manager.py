# -*- coding: utf-8 -*-
"""会话管理模块 - 处理登录Cookie和会话状态"""
import os
import json
import time
import logging
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器"""

    def __init__(self, cookie_file="data/cookies.json"):
        self.cookie_file = cookie_file

    def save_cookies(self, driver):
        """保存登录Cookie到本地"""
        try:
            cookies = [
                cookie for cookie in driver.get_cookies()
                if "zhipin.com" in str(cookie.get("domain", ""))
            ]
            if not cookies:
                logger.warning("当前没有可保存的 BOSS 登录 Cookie")
                return
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookie已保存至: {self.cookie_file}")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")

    def load_cookies(self, driver):
        """加载本地Cookie并注入浏览器"""
        if not os.path.exists(self.cookie_file):
            logger.info("Cookie文件不存在，需要手动登录")
            return False

        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # BOSS直聘需要先在域名下才能注入Cookie
            current_url = driver.current_url or ""
            if "zhipin.com" not in current_url:
                driver.get("https://www.zhipin.com")
                time.sleep(2)

            zhipin_cookies = [
                cookie for cookie in cookies
                if "zhipin.com" in str(cookie.get("domain", ""))
            ]
            if not zhipin_cookies:
                logger.warning("Cookie文件中没有 BOSS 直聘会话，将要求手动登录")
                return False

            for cookie in zhipin_cookies:
                try:
                    # 移除可能导致问题的字段
                    cookie.pop("sameSite", None)
                    cookie.pop("httpOnly", None)
                    driver.add_cookie(cookie)
                except Exception:
                    continue

            logger.info(f"已加载 {len(zhipin_cookies)} 条 BOSS Cookie")
            return True
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return False

    def check_login_status(self, driver):
        """检查当前登录状态"""
        try:
            current_url = driver.current_url

            # 方式1: URL中如果带有login说明还在登录页
            if "login" in current_url.lower() or "register" in current_url.lower():
                return False

            # 方式2: 检查是否存在"登录/注册"按钮——有则表示未登录
            logout_indicators = [
                (By.CSS_SELECTOR, ".header-login-btn"),
                (By.CSS_SELECTOR, ".btns .btn-login"),
                (By.XPATH, "//*[contains(text(), '登录/注册')]"),
            ]
            for by_type, selector in logout_indicators:
                try:
                    elem = driver.find_element(by_type, selector)
                    if elem.is_displayed():
                        return False
                except Exception:
                    continue

            # 方式3: 检查已登录才会出现的元素
            login_indicators = [
                (By.CSS_SELECTOR, ".user-nav .user-menu"),
                (By.CSS_SELECTOR, ".nav-link[href*='geek']"),
                (By.CSS_SELECTOR, "[class*='header-user']"),
                (By.CSS_SELECTOR, ".user-dropdown"),
            ]
            for by_type, selector in login_indicators:
                try:
                    elem = driver.find_element(by_type, selector)
                    if elem.is_displayed():
                        logger.info("检测到已登录状态")
                        return True
                except Exception:
                    continue

            # 无法确定时默认假设未登录，继续等待
            return False
        except Exception as e:
            logger.error(f"检查登录状态异常: {e}")
            return False

    def clear_cookies(self):
        """清除本地Cookie文件"""
        if os.path.exists(self.cookie_file):
            os.remove(self.cookie_file)
            logger.info("Cookie文件已清除")

    def manual_login(self, driver):
        """手动扫码登录流程"""
        logger.info("=" * 50)
        logger.info("请在弹出的浏览器窗口中手动登录BOSS直聘")
        logger.info("支持方式: 微信扫码 / 手机号登录 / 账号密码")
        logger.info("=" * 50)

        # 等待用户登录
        while not self.check_login_status(driver):
            time.sleep(2)

        logger.info("检测到登录成功！")
        # 保存Cookie以便下次自动登录
        time.sleep(3)
        self.save_cookies(driver)
