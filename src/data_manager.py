# -*- coding: utf-8 -*-
"""数据管理模块 - 管理投递历史和统计分析"""
import os
import sqlite3
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器"""

    def __init__(self, db_path="data/history.db"):
        self.db_path = db_path
        self._init_database()

    def _get_conn(self):
        """获取数据库连接"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(100) NOT NULL UNIQUE,
                job_title VARCHAR(200),
                company_name VARCHAR(200),
                company_size VARCHAR(50),
                salary_range VARCHAR(50),
                job_url TEXT,
                hr_name VARCHAR(100),
                delivery_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                response_time TIMESTAMP,
                notes TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name VARCHAR(200) NOT NULL UNIQUE,
                reason TEXT,
                added_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_statistics (
                date DATE PRIMARY KEY,
                total_viewed INTEGER DEFAULT 0,
                total_filtered INTEGER DEFAULT 0,
                total_delivered INTEGER DEFAULT 0,
                response_count INTEGER DEFAULT 0,
                response_rate FLOAT DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")

    def is_delivered(self, job_id):
        """检查职位是否已投递"""
        if not job_id:
            return False
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM delivery_history WHERE job_id = ?", (job_id,)
            )
            result = cursor.fetchone()
            return result is not None

    def save_delivery(self, job_info):
        """保存投递记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO delivery_history 
                (job_id, job_title, company_name, salary_range, job_url, status, delivery_time)
                VALUES (?, ?, ?, ?, ?, 'delivered', ?)""",
                (
                    job_info.get("job_id", ""),
                    job_info.get("title", ""),
                    job_info.get("company", ""),
                    job_info.get("salary", ""),
                    job_info.get("job_url", ""),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

            # 更新统计
            self._update_statistics(cursor, "total_delivered")
            conn.commit()
            logger.info(f"投递记录已保存: {job_info.get('title')} - {job_info.get('company')}")
        except Exception as e:
            logger.error(f"保存投递记录失败: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _update_statistics(self, cursor, field):
        """更新今天统计数据"""
        today = date.today().isoformat()
        cursor.execute(
            f"""INSERT INTO delivery_statistics (date, {field})
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET {field} = {field} + 1""",
            (today,),
        )

    def get_delivery_count_today(self):
        """获取今天的投递数"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            today = date.today().isoformat()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM delivery_history WHERE date(delivery_time) = ?",
                (today,),
            )
            result = cursor.fetchone()
            return result["cnt"] if result else 0

    def get_delivery_count_hour(self):
        """获取当前小时的投递数"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            hour_start = now.replace(minute=0, second=0, microsecond=0).isoformat()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM delivery_history WHERE delivery_time >= ?",
                (hour_start,),
            )
            result = cursor.fetchone()
            return result["cnt"] if result else 0

    def get_statistics(self):
        """获取统计信息"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM delivery_history")
            total = cursor.fetchone()["total"]

            cursor.execute(
                "SELECT COUNT(*) as today FROM delivery_history WHERE date(delivery_time) = ?",
                (date.today().isoformat(),),
            )
            today = cursor.fetchone()["today"]

            return {"total_delivered": total, "today_delivered": today}

    def add_to_blacklist(self, company_name, reason=""):
        """添加公司到黑名单"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO company_blacklist (company_name, reason)
                VALUES (?, ?)""",
                (company_name, reason),
            )
            conn.commit()
            logger.info(f"已加入黑名单: {company_name}")
        except Exception as e:
            logger.error(f"添加黑名单失败: {e}")
        finally:
            conn.close()

    def get_delivery_history(self, limit=50):
        """获取投递历史记录"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM delivery_history ORDER BY delivery_time DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def export_history(self, filepath="data/history_export.json"):
        """导出投递历史为JSON"""
        import json
        history = self.get_delivery_history(limit=10000)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        logger.info(f"投递历史已导出至: {filepath}")
