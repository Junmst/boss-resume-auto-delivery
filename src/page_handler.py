# -*- coding: utf-8 -*-
"""页面操作模块 - 封装BOSS直聘页面元素的定位和操作"""
import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class PageHandler:
    """页面操作处理器"""

    def __init__(self, driver):
        self.driver = driver
        self.actions = ActionChains(driver)

    # ==================== 职位列表相关 ====================

    def get_job_list(self):
        """获取当前页面的职位列表"""
        jobs = []
        try:
            # 等待职位卡片加载
            job_selectors = [
                (By.CSS_SELECTOR, ".job-card-wrapper"),
                (By.CSS_SELECTOR, ".job-list-box .job-card-wrapper"),
                (By.CSS_SELECTOR, ".search-job-result .job-card-wrapper"),
                (By.CSS_SELECTOR, "li[class*='job-card']"),
                (By.CSS_SELECTOR, ".job-primary"),
            ]

            job_elements = None
            for by_type, selector in job_selectors:
                try:
                    job_elements = WebDriverWait(self.driver, 8).until(
                        EC.presence_of_all_elements_located((by_type, selector))
                    )
                    if job_elements:
                        logger.info(f"使用选择器找到 {len(job_elements)} 个职位: {selector}")
                        break
                except Exception:
                    continue

            if not job_elements:
                logger.warning("未找到任何职位卡片")
                # 打印页面标题帮助调试
                logger.info(f"当前页面标题: {self.driver.title}")
                return jobs

            for idx, elem in enumerate(job_elements):
                try:
                    job_info = self._parse_job_card(elem)
                    if job_info:
                        jobs.append(job_info)
                except Exception as e:
                    logger.debug(f"解析第{idx}个职位卡片失败: {e}")
                    continue

            logger.info(f"成功解析 {len(jobs)} 个职位")
        except Exception as e:
            logger.error(f"获取职位列表失败: {e}")

        return jobs

    def _parse_job_card(self, elem):
        """解析单个职位卡片"""
        job_info = {}

        # 尝试多种选择器匹配各字段
        title_selectors = [
            ".job-name", ".job-title", ".name", "[class*='job-name']", "h3"
        ]
        company_selectors = [
            ".company-name", ".cname", "[class*='company-name']", ".company-text"
        ]
        salary_selectors = [
            ".salary", ".red", "[class*='salary']"
        ]
        link_selectors = [
            "a.job-card-left", "a[class*='job-card']", "a"
        ]

        for sel in title_selectors:
            try:
                job_info["title"] = elem.find_element(By.CSS_SELECTOR, sel).text.strip()
                if job_info["title"]:
                    break
            except Exception:
                continue

        for sel in company_selectors:
            try:
                job_info["company"] = elem.find_element(By.CSS_SELECTOR, sel).text.strip()
                if job_info["company"]:
                    break
            except Exception:
                continue

        for sel in salary_selectors:
            try:
                job_info["salary"] = elem.find_element(By.CSS_SELECTOR, sel).text.strip()
                if job_info["salary"]:
                    break
            except Exception:
                continue

        for sel in link_selectors:
            try:
                link = elem.find_element(By.CSS_SELECTOR, sel)
                job_info["job_url"] = link.get_attribute("href")
                if job_info["job_url"]:
                    break
            except Exception:
                continue

        # 提取职位ID
        if "job_url" in job_info and job_info["job_url"]:
            import re
            match = re.search(r"job_detail/([a-zA-Z0-9]+)", job_info["job_url"])
            if match:
                job_info["job_id"] = match.group(1)
            else:
                job_info["job_id"] = job_info.get("job_url", "").split("/")[-1]
        else:
            job_info["job_id"] = elem.get_attribute("data-jobid") or elem.get_attribute("data-id") or ""

        # 必须至少有职位名称或公司名称
        if not job_info.get("title") and not job_info.get("company"):
            return None

        job_info.setdefault("title", "未知职位")
        job_info.setdefault("company", "未知公司")
        job_info.setdefault("salary", "未知薪资")
        job_info.setdefault("job_url", "")
        job_info.setdefault("job_id", f"auto_{hash(job_info.get('title', ''))}")

        return job_info

    # ==================== 职位详情相关 ====================

    def open_job_detail(self, job_info):
        """打开职位详情页"""
        try:
            job_url = job_info.get("job_url", "")
            if not job_url:
                logger.warning(f"职位URL为空: {job_info.get('title')}")
                return False

            self.driver.get(job_url)
            time.sleep(random.uniform(2, 4))
            self._random_scroll()
            logger.info(f"已打开职位详情: {job_info.get('title')}")
            return True
        except Exception as e:
            logger.error(f"打开职位详情失败: {e}")
            return False

    def get_job_description(self):
        """获取职位描述文字"""
        desc_selectors = [
            (By.CSS_SELECTOR, ".job-detail .text"),
            (By.CSS_SELECTOR, ".job-sec-text"),
            (By.CSS_SELECTOR, ".job-detail-section .job-detail-content"),
            (By.CSS_SELECTOR, "[class*='job-detail'] [class*='text']"),
        ]

        for by_type, selector in desc_selectors:
            try:
                elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                return elem.text.strip()
            except Exception:
                continue
        return ""

    def collect_job_preview(self, job_info, keyword):
        """读取职位详情供测试预览使用，不执行沟通或投递操作。"""
        if not self.open_job_detail(job_info):
            return self._build_preview(job_info, keyword, "", "")

        description = self.get_job_description()
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        location = self._first_text([
            ".job-area", ".location", "[class*='job-area']", "[class*='location']"
        ])
        if not location:
            location = self._extract_location(page_text)
        interview_type = self._get_interview_type(page_text)
        return self._build_preview(job_info, keyword, description, location, interview_type)

    def _first_text(self, selectors):
        for selector in selectors:
            try:
                text = self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
                if text:
                    return text
            except Exception:
                continue
        return ""

    @staticmethod
    def _extract_location(text):
        import re
        match = re.search(r"(?:工作地址|上班地址|地址)[:：\s]*([^\n]{2,80})", text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _get_interview_type(text):
        normalized = text.casefold()
        if "线上面试" in normalized or "视频面试" in normalized or "远程面试" in normalized:
            return "线上面试"
        if "线下面试" in normalized or "现场面试" in normalized or "到面" in normalized:
            return "线下面试"
        return ""

    @staticmethod
    def _build_preview(job_info, keyword, description, location, interview_type=""):
        return {
            "keyword": keyword or "无",
            "location": location or "无",
            "requirements": description or "无",
            "interview_type": interview_type or "无",
            "salary": job_info.get("salary") or "无",
        }

    # ==================== 沟通/投递相关 ====================

    def click_chat_button(self):
        """点击「立即沟通」按钮"""
        chat_selectors = [
            (By.CSS_SELECTOR, ".btn-startchat"),
            (By.CSS_SELECTOR, ".op-btn-chat"),
            (By.CSS_SELECTOR, "a[class*='chat']"),
            (By.CSS_SELECTOR, ".btn[class*='chat']"),
            (By.XPATH, "//*[contains(text(), '立即沟通')]"),
            (By.XPATH, "//*[contains(text(), '立即聊')]"),
        ]

        for by_type, selector in chat_selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                # 模拟鼠标移动
                self.actions.move_to_element(btn).pause(random.uniform(0.3, 0.8)).click().perform()
                logger.info("已点击「立即沟通」按钮")
                time.sleep(random.uniform(1, 2))
                return True
            except Exception:
                continue

        logger.warning("未找到「立即沟通」按钮")
        return False

    def send_greeting_message(self, message):
        """在聊天框发送打招呼消息"""
        # 等待聊天输入框出现
        input_selectors = [
            (By.CSS_SELECTOR, ".chat-input textarea"),
            (By.CSS_SELECTOR, ".chat-input .input-box"),
            (By.CSS_SELECTOR, ".chat-input textarea"),
            (By.CSS_SELECTOR, "textarea[placeholder*='消息']"),
            (By.CSS_SELECTOR, ".input-area textarea"),
            (By.TAG_NAME, "textarea"),
        ]

        input_box = None
        for by_type, selector in input_selectors:
            try:
                input_box = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                break
            except Exception:
                continue

        if not input_box:
            logger.warning("未找到聊天输入框")
            return False

        try:
            # 模拟打字输入
            self.actions.move_to_element(input_box).click().perform()
            time.sleep(random.uniform(0.3, 0.6))
            input_box.clear()
            for char in message:
                input_box.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            time.sleep(random.uniform(0.5, 1.0))

            # 点击发送按钮
            send_selectors = [
                (By.CSS_SELECTOR, ".send-btn"),
                (By.CSS_SELECTOR, "button[class*='send']"),
                (By.XPATH, "//*[contains(text(), '发送')]"),
                (By.CSS_SELECTOR, ".btn-send"),
            ]

            for by_type, selector in send_selectors:
                try:
                    send_btn = self.driver.find_element(by_type, selector)
                    self.actions.move_to_element(send_btn).click().perform()
                    logger.info(f"消息已发送: {message[:30]}...")
                    time.sleep(random.uniform(1, 2))
                    return True
                except Exception:
                    continue

            # 尝试使用Enter发送
            from selenium.webdriver.common.keys import Keys
            input_box.send_keys(Keys.RETURN)
            logger.info(f"消息已通过回车发送: {message[:30]}...")
            time.sleep(random.uniform(1, 2))
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    # ==================== 辅助功能 ====================

    def _random_scroll(self):
        """随机滚动页面模拟人工浏览"""
        try:
            scroll_times = random.randint(2, 4)
            for _ in range(scroll_times):
                scroll_px = random.randint(200, 600)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_px})")
                time.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass

    def close_popup(self):
        """关闭可能的弹窗"""
        close_selectors = [
            (By.CSS_SELECTOR, ".dialog-close"),
            (By.CSS_SELECTOR, ".modal-close"),
            (By.CSS_SELECTOR, ".popup-close"),
            (By.CSS_SELECTOR, "[class*='close']"),
            (By.XPATH, "//*[contains(@class, 'close')]"),
        ]

        for by_type, selector in close_selectors:
            try:
                elem = self.driver.find_element(by_type, selector)
                if elem.is_displayed():
                    elem.click()
                    logger.info("已关闭弹窗")
                    time.sleep(0.5)
            except Exception:
                continue

    def go_to_next_page(self):
        """翻到下一页"""
        next_selectors = [
            (By.CSS_SELECTOR, ".page .next"),
            (By.CSS_SELECTOR, ".pagination .next"),
            (By.CSS_SELECTOR, "[class*='page'] [class*='next']"),
            (By.XPATH, "//*[contains(text(), '下一页')]"),
            (By.XPATH, "//*[contains(@class, 'next')]"),
        ]

        for by_type, selector in next_selectors:
            try:
                btn = self.driver.find_element(by_type, selector)
                if btn.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView();", btn)
                    time.sleep(0.5)
                    self.actions.move_to_element(btn).click().perform()
                    logger.info("已翻到下一页")
                    time.sleep(random.uniform(2, 4))
                    return True
            except Exception:
                continue

        logger.info("没有更多页面了")
        return False
