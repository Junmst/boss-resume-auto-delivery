# -*- coding: utf-8 -*-
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from src.browser_driver import BrowserDriver
from src.config_manager import ConfigManager

browser = None
try:
    browser = BrowserDriver(ConfigManager("config/config.yaml"))
    driver = browser.get_driver()
    try:
        browser.navigate("https://www.zhipin.com", expected_host="zhipin.com", attempts=1, wait_seconds=5)
    except RuntimeError as error:
        print(f"NAVIGATION_ERROR={error}")
    print(f"CURRENT_HANDLE={driver.current_window_handle}")
    print(f"HANDLES={driver.window_handles}")
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        print(f"HANDLE={handle} URL={driver.current_url} TITLE={driver.title}")
    time.sleep(1)
finally:
    if browser:
        browser.quit()
