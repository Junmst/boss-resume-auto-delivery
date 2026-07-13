# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch

from src.main import BOSSAutoDelivery


class SearchUrlTests(unittest.TestCase):
    def test_build_search_urls_includes_every_configured_keyword(self):
        app = BOSSAutoDelivery()
        app.config.get_search_config = MagicMock(return_value={
            "keywords": ["ai", "Python 开发"],
            "city": "",
        })

        searches = app._build_search_urls()

        self.assertEqual(
            searches,
            [
                ("ai", "https://www.zhipin.com/web/geek/job?query=ai"),
                ("Python 开发", "https://www.zhipin.com/web/geek/job?query=Python%20%E5%BC%80%E5%8F%91"),
            ],
        )

    def test_navigation_retries_when_edge_overwrites_first_request(self):
        from src.browser_driver import BrowserDriver

        driver = MagicMock()
        driver.current_url = "https://ntp.msn.cn/edge/ntp"
        browser = BrowserDriver.__new__(BrowserDriver)
        browser.driver = driver

        with self.assertRaises(RuntimeError):
            browser.navigate(
                "https://www.zhipin.com",
                expected_host="zhipin.com",
                attempts=2,
                wait_seconds=0,
            )

        self.assertEqual(driver.get.call_count, 2)

    def test_navigation_uses_cdp_fallback_after_webdriver_navigation_is_overwritten(self):
        from src.browser_driver import BrowserDriver

        driver = MagicMock()
        driver.current_url = "https://ntp.msn.cn/edge/ntp"
        driver.execute_cdp_cmd.side_effect = lambda command, params: setattr(
            driver, "current_url", params["url"]
        )
        browser = BrowserDriver.__new__(BrowserDriver)
        browser.driver = driver

        result = browser.navigate(
            "https://www.zhipin.com",
            expected_host="zhipin.com",
            attempts=1,
            wait_seconds=0,
        )

        self.assertEqual(result, "https://www.zhipin.com")
        driver.execute_cdp_cmd.assert_called_once_with(
            "Page.navigate", {"url": "https://www.zhipin.com"}
        )

    def test_attached_browser_does_not_quit_the_user_edge_session(self):
        from src.browser_driver import BrowserDriver

        browser = BrowserDriver.__new__(BrowserDriver)
        browser.driver = MagicMock()
        browser.profile_dir = None
        browser.owns_browser = False

        driver = browser.driver
        browser.quit()

        driver.quit.assert_not_called()
        self.assertIsNone(browser.driver)

    def test_search_records_a_result_for_every_keyword(self):
        app = BOSSAutoDelivery()
        app._build_search_urls = MagicMock(return_value=[
            ("ai", "https://example.test/ai"),
            ("python", "https://example.test/python"),
        ])
        app.browser = MagicMock()
        app.driver = MagicMock()
        app.page_handler = MagicMock()
        app.page_handler.get_job_list.side_effect = [
            [{"job_id": "job-1", "title": "AI Engineer"}],
            [],
        ]

        with patch("src.main.capture_search_diagnostics", return_value={
            "status": "no_results",
            "html_path": "data/diagnostics/python.html",
        }):
            jobs, outcomes = app._search_jobs()

        self.assertEqual(jobs[0]["search_keyword"], "ai")
        self.assertEqual(
            outcomes,
            [
                {"keyword": "ai", "count": 1, "status": "ok"},
                {
                    "keyword": "python",
                    "count": 0,
                    "status": "no_results",
                    "diagnostic_path": "data/diagnostics/python.html",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
