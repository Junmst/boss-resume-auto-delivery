# -*- coding: utf-8 -*-
"""Capture actionable evidence whenever BOSS search does not return jobs."""
from datetime import datetime
from pathlib import Path
import re


def classify_search_page(url, title, page_text):
    text = " ".join((url or "", title or "", page_text or "")).casefold()
    if any(marker in text for marker in ("验证码", "安全验证", "访问异常", "verify", "captcha")):
        return "verification_required"
    if "登录" in text or "login" in text:
        return "login_required"
    if "zhipin.com" not in (url or ""):
        return "navigation_failed"
    if re.search(r"暂无.{0,8}(职位|岗位)|没有找到.{0,8}(职位|岗位)", page_text or ""):
        return "no_results"
    return "dom_changed_or_loading_failed"


def capture_search_diagnostics(driver, output_dir, keyword):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_keyword = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", keyword)[:40] or "empty"
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    base_path = target_dir / f"search-{timestamp}-{safe_keyword}"
    page_text = driver.find_element("tag name", "body").text
    html_path = base_path.with_suffix(".html")
    screenshot_path = base_path.with_suffix(".png")
    html_path.write_text(driver.page_source, encoding="utf-8")
    driver.save_screenshot(str(screenshot_path))
    return {
        "url": driver.current_url,
        "title": driver.title,
        "status": classify_search_page(driver.current_url, driver.title, page_text),
        "html_path": str(html_path),
        "screenshot_path": str(screenshot_path),
    }