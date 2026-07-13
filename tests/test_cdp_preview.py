# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch


class CdpPreviewTests(unittest.TestCase):
    def test_extract_job_cards_returns_normalized_preview_fields(self):
        from src.cdp_preview import extract_job_cards

        cards = extract_job_cards([
            {
                "title": "Python开发工程师",
                "company": "示例科技",
                "salary": "15-25K",
                "location": "北京·海淀区",
                "tags": ["Python", "Django"],
                "requirements": "3-5年 | 本科",
            }
        ])

        self.assertEqual(cards[0]["title"], "Python开发工程师")
        self.assertEqual(cards[0]["location"], "北京·海淀区")
        self.assertEqual(cards[0]["tags"], ["Python", "Django"])
        self.assertEqual(cards[0]["requirements"], "3-5年 | 本科")

    @patch("src.cdp_preview.read_page_value")
    def test_preview_search_tabs_reads_only_search_pages(self, read_page_value):
        from src.cdp_preview import preview_search_tabs

        read_page_value.return_value = [{
            "title": "Python开发工程师",
            "company": "示例科技",
            "salary": "15-25K",
            "location": "北京·海淀区",
            "tags": ["Python"],
            "requirements": "3-5年",
        }]
        pages = [
            {"type": "page", "url": "http://127.0.0.1:8520/"},
            {"type": "page", "url": "https://www.zhipin.com/web/geek/jobs?query=python", "webSocketDebuggerUrl": "ws://test"},
        ]

        previews, outcomes = preview_search_tabs(pages)

        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0]["keyword"], "python")
        self.assertEqual(outcomes, [{"keyword": "python", "count": 1, "status": "ok"}])
        read_page_value.assert_called_once_with("ws://test")


if __name__ == "__main__":
    unittest.main()
