# -*- coding: utf-8 -*-
"""浏览器驱动模块 - 初始化和管理WebDriver"""
import logging
import random
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


class BrowserDriver:
    """浏览器驱动管理器"""

    def __init__(self, config):
        self.config = config
        self.driver = None
        self.profile_dir = None
        self.owns_browser = True
        self._init_driver()

    def _init_driver(self):
        """初始化浏览器驱动"""
        browser_config = self.config.get_browser_config()
        browser_type = browser_config.get("type", "edge")

        if browser_type == "chrome":
            self.driver = self._init_chrome(browser_config)
        elif browser_type == "edge":
            self.driver = self._init_edge(browser_config)
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")

        logger.info(f"{browser_type.upper()} 浏览器启动成功")

    def _init_chrome(self, browser_config):
        """初始化Chrome浏览器"""
        options = Options()

        # 防反爬设置 - 隐藏自动化特征
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # 窗口大小
        window_size = browser_config.get("window_size", [1920, 1080])
        options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")

        # 用户数据目录 (持久化登录状态)
        user_data_dir = browser_config.get("user_data_dir")
        if user_data_dir:
            options.add_argument(f"--user-data-dir={user_data_dir}")

        # 随机User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        options.add_argument(f"user-agent={random.choice(user_agents)}")

        # 禁用GPU加速
        options.add_argument("--disable-gpu")
        # 禁用沙箱
        options.add_argument("--no-sandbox")
        # 禁用扩展
        options.add_argument("--disable-extensions")
        # 忽略证书错误
        options.add_argument("--ignore-certificate-errors")
        # 禁用日志
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # 静默模式
        if browser_config.get("headless", False):
            options.add_argument("--headless")

        # 尝试使用本地驱动
        driver = None
        driver_paths = [
            "./drivers/chromedriver.exe",
            "chromedriver",
            "chromedriver.exe",
        ]
        import os
        for dp in driver_paths:
            if os.path.exists(dp):
                service = Service(executable_path=dp)
                driver = webdriver.Chrome(service=service, options=options)
                break

        if driver is None:
            driver = webdriver.Chrome(options=options)

        # 隐藏 navigator.webdriver 属性
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            """
        })

        return driver

    def _init_edge(self, browser_config):
        """初始化 Microsoft Edge 浏览器"""
        import os
        from pathlib import Path
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.edge.service import Service as EdgeService

        options = EdgeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-features=msEdgeFirstRunExperience")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        window_size = browser_config.get("window_size", [1920, 1080])
        options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")

        project_root = Path(__file__).resolve().parent.parent
        profile_root = project_root / "data" / "browser_profiles"
        profile_root.mkdir(parents=True, exist_ok=True)
        self.profile_dir = Path(tempfile.mkdtemp(prefix="boss-", dir=profile_root))
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        logger.info(f"投递浏览器使用独立临时目录: {self.profile_dir}")

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--ignore-certificate-errors")
        if browser_config.get("headless", False):
            options.add_argument("--headless=new")

        driver_path = project_root / "drivers" / "msedgedriver.exe"
        service_log = project_root / "data" / "logs" / "msedgedriver.log"
        service = EdgeService(
            executable_path=os.fspath(driver_path),
            log_output=os.fspath(service_log),
            service_args=["--verbose"],
        )
        if driver_path.is_file():
            driver = webdriver.Edge(service=service, options=options)
        else:
            driver = webdriver.Edge(options=options)

        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })

        # Edge may asynchronously redirect its startup tab to the Microsoft new-tab page.
        # Use a WebDriver-created tab for automation and discard that unstable startup tab.
        import time
        startup_handle = driver.current_window_handle
        driver.switch_to.new_window("tab")
        automation_handle = driver.current_window_handle
        driver.switch_to.window(startup_handle)
        driver.close()
        driver.switch_to.window(automation_handle)
        time.sleep(1)
        return driver

    @classmethod
    def attach_to_edge(cls, debug_address, driver_path=None):
        """Attach to the Edge instance that hosts the configuration page."""
        from pathlib import Path
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.edge.service import Service as EdgeService

        instance = cls.__new__(cls)
        instance.config = None
        instance.profile_dir = None
        instance.owns_browser = False
        options = EdgeOptions()
        options.add_experimental_option("debuggerAddress", debug_address)
        if driver_path is None:
            driver_path = Path(__file__).resolve().parent.parent / "drivers" / "msedgedriver.exe"
        instance.driver = webdriver.Edge(
            service=EdgeService(executable_path=str(driver_path)),
            options=options,
        )
        logger.info(f"已附加到配置页 Edge 会话: {debug_address}")
        return instance

    def get_driver(self):
        """获取驱动实例"""
        return self.driver

    def navigate(self, url, expected_host, attempts=3, wait_seconds=2):
        """Navigate with verification because Edge may finish its new-tab load late."""
        import time

        for attempt in range(1, attempts + 1):
            self.driver.get(url)
            time.sleep(wait_seconds)
            current_url = self.driver.current_url or ""
            if expected_host in current_url:
                return current_url
            logger.warning(
                "导航第 %s/%s 次未到达 %s，当前地址: %s",
                attempt, attempts, expected_host, current_url,
            )

        logger.warning("WebDriver 导航被 Edge 新标签页覆盖，切换到 CDP 导航")
        self.driver.execute_cdp_cmd("Page.navigate", {"url": url})
        time.sleep(wait_seconds)
        current_url = self.driver.current_url or ""
        if expected_host in current_url:
            return current_url
        raise RuntimeError(f"导航失败，未到达 {expected_host}: {current_url}")

    def quit(self):
        """Release WebDriver and only close browsers started by this instance."""
        if self.driver:
            try:
                if self.owns_browser:
                    self.driver.quit()
                    logger.info("浏览器已关闭")
                else:
                    logger.info("已断开配置页 Edge 会话，浏览器保持打开")
            except Exception as e:
                logger.warning(f"关闭浏览器异常: {e}")
            finally:
                self.driver = None
        if self.profile_dir:
            shutil.rmtree(self.profile_dir, ignore_errors=True)
            self.profile_dir = None
