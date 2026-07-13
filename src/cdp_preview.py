# -*- coding: utf-8 -*-
"""Read BOSS search tabs through CDP without interacting with the page."""
import json
from urllib.parse import parse_qs, urlparse

import websocket


CARD_EXTRACTION_SCRIPT = r"""
(() => {
  const clean = value => (value || '').replace(/\s+/g, ' ').trim();
  const firstText = (root, selectors) => {
    for (const selector of selectors) {
      const element = root.querySelector(selector);
      const value = clean(element && element.innerText);
      if (value) return value;
    }
    return '';
  };
  const cards = [...document.querySelectorAll('.job-card-wrapper, .job-card-box, li[class*="job-card"], .job-primary')];
  return cards.slice(0, 20).map(card => ({
    title: firstText(card, ['.job-name', '.job-title', '[class*="job-name"]', 'h3']),
    company: firstText(card, ['.company-name', '.company-text', '[class*="company-name"]', '.cname']),
    salary: firstText(card, ['.salary', '[class*="salary"]', '.red']),
    location: firstText(card, ['.job-area', '.job-area-wrapper', '[class*="job-area"]', '.location']),
    tags: [...card.querySelectorAll('.tag, [class*="tag"], [class*="skills"], [class*="welfare"]')]
      .map(element => clean(element.innerText)).filter(Boolean).slice(0, 12),
    requirements: firstText(card, ['.job-info', '.job-card-footer', '[class*="require"]', '[class*="experience"]']),
  })).filter(card => card.title || card.company);
})()
"""


def extract_job_cards(raw_cards):
    """Normalize raw DOM values for the preview response."""
    previews = []
    for card in raw_cards or []:
        tags = card.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        previews.append({
            "title": str(card.get("title") or "未知职位").strip(),
            "company": str(card.get("company") or "未知公司").strip(),
            "salary": str(card.get("salary") or "未提供").strip(),
            "location": str(card.get("location") or "未提供").strip(),
            "tags": [str(tag).strip() for tag in tags if str(tag).strip()],
            "requirements": str(card.get("requirements") or "未提供").strip(),
        })
    return previews


def read_page_value(websocket_url, timeout=4):
    """Evaluate the extraction script without changing browser state."""
    connection = websocket.create_connection(websocket_url, timeout=timeout, origin="http://localhost")
    try:
        connection.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": CARD_EXTRACTION_SCRIPT,
                "returnByValue": True,
                "awaitPromise": True,
            },
        }))
        while True:
            message = json.loads(connection.recv())
            if message.get("id") == 1:
                result = message.get("result", {}).get("result", {})
                return result.get("value", [])
    finally:
        connection.close()


def preview_search_tabs(pages):
    """Return read-only job previews and per-keyword diagnostics."""
    previews = []
    outcomes = []
    for page in pages:
        url = page.get("url", "")
        websocket_url = page.get("webSocketDebuggerUrl")
        if "/web/geek/jobs" not in url or not websocket_url:
            continue
        keyword = parse_qs(urlparse(url).query).get("query", [""])[0] or "未提供"
        try:
            cards = extract_job_cards(read_page_value(websocket_url))
            for card in cards:
                card["keyword"] = keyword
                previews.append(card)
            outcomes.append({"keyword": keyword, "count": len(cards), "status": "ok"})
        except Exception as exc:
            outcomes.append({"keyword": keyword, "count": 0, "status": "read_failed", "error": str(exc)})
    return previews, outcomes
