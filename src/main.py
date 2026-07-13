# -*- coding: utf-8 -*-
"""BOSS直聘自动投递工具 - 主程序入口"""
import sys
import os
import time
import json
import logging
from datetime import datetime

# 确保工作目录为项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PROJECT_ROOT)

from src.config_manager import ConfigManager
from src.browser_driver import BrowserDriver
from src.session_manager import SessionManager
from src.page_handler import PageHandler
from src.job_filter import JobFilter
from src.delivery_executor import DeliveryExecutor
from src.data_manager import DataManager
from src.utils import setup_logging
from src.run_lock import RunLock
from src.search_diagnostics import capture_search_diagnostics


class BOSSAutoDelivery:
    """BOSS直聘自动投递主控制器"""

    def __init__(self, driver=None, on_finished=None, debug_address=None):
        self._shared_driver = driver
        self._on_finished = on_finished
        self._background_mode = (on_finished is not None)
        self._debug_address = debug_address
        self._attached_browser = bool(debug_address)

        # 加载配置
        self.config = ConfigManager("config/config.yaml")

        # 设置日志
        log_level = self.config.get("app.log_level", "INFO")
        self.logger = setup_logging(log_level)
        self.logger.info("=" * 60)
        self.logger.info(
            f"{self.config.get('app.name', 'BOSS自动投递工具')} "
            f"v{self.config.get('app.version', '1.0.0')}"
        )
        self.logger.info("=" * 60)

        # 初始化模块
        self.data_manager = DataManager("data/history.db")
        self.browser = None
        self.session = None
        self.page_handler = None
        self.job_filter = None
        self.executor = None

        # 运行状态
        self.current_page = 1
        self.max_pages = 10
        self.consecutive_errors = 0
        self.run_lock = RunLock(os.path.join(_PROJECT_ROOT, "data", "automation.lock"))

    def _init_modules(self):
        """初始化模块"""
        if self._shared_driver is not None:
            self.driver = self._shared_driver
            self.logger.info("复用现有浏览器，将在新标签页打开 BOSS 直聘")
        elif self._debug_address:
            self.logger.info("附加到配置页 Edge，将在同一窗口新建 BOSS 标签页")
            self.browser = BrowserDriver.attach_to_edge(self._debug_address)
            self.driver = self.browser.get_driver()
        else:
            self.logger.info("正在初始化独立浏览器...")
            self.browser = BrowserDriver(self.config)
            self.driver = self.browser.get_driver()

        self.session = SessionManager("data/cookies.json")
        self.page_handler = PageHandler(self.driver)
        self.job_filter = JobFilter(self.config)
        self.executor = DeliveryExecutor(
            self.driver, self.config, self.data_manager, self.page_handler
        )

    def _login(self):
        """登录BOSS直聘"""
        self.logger.info("=" * 60)
        self.logger.info("开始登录流程")
        self.logger.info("=" * 60)

        self.logger.info("正在打开BOSS直聘...")
        if self._shared_driver is not None or self._attached_browser:
            self.driver.switch_to.new_window("tab")
            self.logger.info("已在配置页 Edge 中创建 BOSS 标签页")
        if self.browser:
            self.browser.navigate("https://www.zhipin.com", expected_host="zhipin.com")
        else:
            self.driver.get("https://www.zhipin.com")
            time.sleep(3)
        if "zhipin.com" not in (self.driver.current_url or ""):
            self.logger.error(f"BOSS 页面未成功加载，当前地址: {self.driver.current_url}")
            return False

        # 尝试Cookie登录
        if self.session.load_cookies(self.driver):
            self.driver.refresh()
            time.sleep(3)

            if self.session.check_login_status(self.driver):
                self.logger.info("Cookie登录成功!")
                return True
            else:
                self.logger.info("Cookie已过期，需要手动登录")

        # 手动登录
        self.logger.info("-" * 50)
        self.logger.info("请在浏览器中完成登录操作")
        self.logger.info("支持: 微信扫码 / 手机号 / 账号密码")
        self.logger.info("-" * 50)

        if self._background_mode:
            # 后台模式：轮询检测登录状态
            max_wait = self.config.get("browser.login_timeout_seconds", 600)
            for i in range(max_wait):
                time.sleep(1)
                if self.session.check_login_status(self.driver):
                    self.session.save_cookies(self.driver)
                    self.logger.info("登录成功!")
                    return True
                if i % 5 == 0:  # 每5秒打印一次
                    self.logger.info(f"等待登录中... ({i}/{max_wait}秒)")
            self.logger.error(f"登录超时（{max_wait}秒），请重试")
            return False
        else:
            # 命令行模式：等待用户按回车
            input("登录完成后按 Enter 键继续...")
            if self.session.check_login_status(self.driver):
                self.session.save_cookies(self.driver)
                self.logger.info("登录成功!")
                return True
            else:
                self.logger.error("登录验证失败，请重试")
                return False

    def _build_search_urls(self):
        """为每一个已配置关键词构建独立搜索 URL。"""
        search_config = self.config.get_search_config()
        keywords = [str(item).strip() for item in search_config.get("keywords", []) if str(item).strip()]
        if not keywords:
            raise ValueError("至少需要配置一个搜索关键词")
        city = str(search_config.get("city", "")).strip()
        from urllib.parse import quote
        city_query = f"&city={quote(city)}" if city else ""
        return [
            (keyword, f"https://www.zhipin.com/web/geek/job?query={quote(keyword)}{city_query}")
            for keyword in keywords
        ]

    def _search_jobs(self):
        """搜索所有关键词，并返回职位和每个关键词的可诊断结果。"""
        all_jobs = []
        outcomes = []
        seen_ids = set()
        for keyword, search_url in self._build_search_urls():
            self.logger.info(f"搜索关键词 [{keyword}]: {search_url}")
            if self.browser:
                self.browser.navigate(search_url, expected_host="zhipin.com")
            else:
                self.driver.get(search_url)
                time.sleep(3)
            self.page_handler.close_popup()
            jobs = self.page_handler.get_job_list()
            if not jobs:
                evidence = capture_search_diagnostics(
                    self.driver, os.path.join(_PROJECT_ROOT, "data", "diagnostics"), keyword
                )
                outcomes.append({
                    "keyword": keyword,
                    "count": 0,
                    "status": evidence["status"],
                    "diagnostic_path": evidence["html_path"],
                })
                self.logger.warning(
                    "关键词 [%s] 无职位结果，页面状态=%s，证据=%s",
                    keyword, evidence["status"], evidence["html_path"],
                )
                continue

            added_count = 0
            for job in jobs:
                job["search_keyword"] = keyword
                job_key = job.get("job_id") or job.get("job_url")
                if job_key and job_key in seen_ids:
                    continue
                if job_key:
                    seen_ids.add(job_key)
                all_jobs.append(job)
                added_count += 1
            outcomes.append({"keyword": keyword, "count": added_count, "status": "ok"})
        return all_jobs, outcomes

    @staticmethod
    def _write_test_results(status, results=None, error=None, search_outcomes=None):
        """原子写入测试预览状态，供配置页面轮询。"""
        result_path = os.path.join(_PROJECT_ROOT, "data", "test_results.json")
        payload = {
            "status": status,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "results": results or [],
            "search_outcomes": search_outcomes or [],
        }
        if error:
            payload["error"] = str(error)
        temp_path = result_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, result_path)

    def _run_test_search(self, jobs, search_outcomes):
        """仅搜索和读取职位信息，绝不进入投递流程。"""
        previews = []
        self._write_test_results("running", search_outcomes=search_outcomes)
        for index, job in enumerate(jobs, 1):
            self.logger.info(f"[测试 {index}/{len(jobs)}] 读取: {job.get('title')} - {job.get('company')}")
            previews.append(self.page_handler.collect_job_preview(job, job.get("search_keyword", "无")))
            self._write_test_results("running", previews, search_outcomes=search_outcomes)
        self._write_test_results("completed", previews, search_outcomes=search_outcomes)
        self.logger.info(f"测试搜索完成，已读取 {len(previews)} 个职位，不会发送消息或投递。")

    def run(self):
        """主运行流程"""
        try:
            if not self.run_lock.acquire():
                self.logger.error("已有自动化任务在运行；请等待其完成后再启动")
                return
            # 1. 初始化
            self._init_modules()

            # 2. 登录
            if not self._login():
                self.logger.error("登录失败，程序退出")
                return

            # 3. 显示当前统计
            stats = self.data_manager.get_statistics()
            self.logger.info(
                f"历史投递: {stats['total_delivered']} 个, "
                f"今日已投: {stats['today_delivered']} 个"
            )

            # 4. 搜索职位
            jobs, search_outcomes = self._search_jobs()
            if not jobs:
                self._write_test_results("completed", search_outcomes=search_outcomes)
                self.logger.warning("未找到任何职位，请检查搜索条件或查看诊断文件")
                return

            self.logger.info(f"搜索到 {len(jobs)} 个职位")

            if self.config.get_delivery_config().get("test_mode", False):
                self._run_test_search(jobs, search_outcomes)
                return

            # 5. 筛选职位
            valid_jobs = self.job_filter.filter_batch(jobs)

            # 6. 投递
            self.logger.info("-" * 50)
            self.logger.info(f"开始投递，共 {len(valid_jobs)} 个符合条件的职位")
            self.logger.info("-" * 50)

            delivered = 0
            skipped = 0
            failed = 0

            for idx, job in enumerate(valid_jobs, 1):
                self.logger.info(
                    f"[{idx}/{len(valid_jobs)}] "
                    f"{job.get('title')} - {job.get('company')} "
                    f"({job.get('salary', '未知')})"
                )

                # 检查频率限制
                if not self.executor.rate_limiter.can_proceed():
                    self.logger.info("已达到频率限制，暂停投递")
                    break

                # 尝试投递
                if self.executor.deliver_resume(job):
                    delivered += 1
                    self.consecutive_errors = 0
                else:
                    # 判断是跳过还是失败
                    if self.data_manager.is_delivered(job.get("job_id", "")):
                        skipped += 1
                    else:
                        failed += 1
                        self.consecutive_errors += 1

                # 连续失败过多则暂停
                if self.consecutive_errors >= 5:
                    self.logger.warning("连续失败5次，可能遇到反爬或网络问题，建议稍后重试")
                    if self._background_mode:
                        # 后台模式：直接停止
                        self.logger.error("后台模式下自动停止投递")
                        break
                    else:
                        # 命令行模式：询问用户
                        choice = input("继续投递? (y/n): ").strip().lower()
                        if choice != "y":
                            break
                        self.consecutive_errors = 0

            # 7. 输出总结
            self.logger.info("=" * 60)
            self.logger.info("投递总结:")
            self.logger.info(f"  成功投递: {delivered}")
            self.logger.info(f"  已跳过(重复): {skipped}")
            self.logger.info(f"  投递失败: {failed}")
            self.logger.info(f"  总计处理: {len(valid_jobs)}")
            self.logger.info("=" * 60)

            # 导出记录
            self.data_manager.export_history()
            stats = self.data_manager.get_statistics()
            self.logger.info(f"历史累计投递: {stats['total_delivered']} 个")

        except KeyboardInterrupt:
            self.logger.info("用户中断运行")
            if self.config.get_delivery_config().get("test_mode", False):
                self._write_test_results("failed", error="测试已中断")
        except Exception as e:
            self.logger.error(f"运行异常: {e}", exc_info=True)
            if self.config.get_delivery_config().get("test_mode", False):
                self._write_test_results("failed", error=e)
        finally:
            if self._on_finished:
                self._on_finished()
            if self.browser:
                self.logger.info("正在关闭浏览器...")
                self.browser.quit()
            self.run_lock.release()
            self.logger.info("程序已退出")


def main():
    app = BOSSAutoDelivery()
    app.run()


if __name__ == "__main__":
    main()
