# -*- coding: utf-8 -*-
import logging
import os

def setup_logging(log_level="INFO", log_dir="data/logs"):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("BOSS")

def safe_find_element(driver, selectors, timeout=3):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    for by_type, selector in selectors:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
        except Exception:
            continue
    return None

def safe_find_elements(driver, selectors, timeout=3):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    for by_type, selector in selectors:
        try:
            elems = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by_type, selector))
            )
            if elems:
                return elems
        except Exception:
            continue
    return []
