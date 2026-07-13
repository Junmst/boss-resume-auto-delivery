# -*- coding: utf-8 -*-
"""BOSS自动投递工具 - Web配置管理界面"""

import os
import sys
import time
import json
import yaml
import logging
import threading
import subprocess
import socket
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gui")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

PORT = 8520
AUTOMATION_LOCK = threading.Lock()
CONFIG_BROWSER = None
CONFIG_BROWSER_LOCK = threading.Lock()


def _edge_debug_address():
    port = int(load_config().get("browser", {}).get("debug_port", 9222))
    return f"127.0.0.1:{port}", port


def _port_is_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def launch_configuration_edge():
    """Open the configuration page in a project-owned Edge debugging session."""
    address, port = _edge_debug_address()
    if _port_is_open(port):
        return address

    edge_paths = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    edge = next((path for path in edge_paths if path.is_file()), None)
    if edge is None:
        raise RuntimeError("未找到 Microsoft Edge")

    profile = Path(PROJECT_ROOT) / "edge_browser_data"
    subprocess.Popen(
        [
            str(edge),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--remote-allow-origins=http://localhost",
            "--no-first-run",
            "--no-default-browser-check",
            f"http://127.0.0.1:{PORT}",
        ],
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    for _ in range(30):
        if _port_is_open(port):
            return address
        time.sleep(0.2)
    raise RuntimeError("Edge 调试端口启动超时")


def open_boss_login_tab():
    """Open exactly one BOSS login tab in the Edge instance hosting the config page."""
    edge_paths = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    edge = next((path for path in edge_paths if path.is_file()), None)
    if edge is None:
        raise RuntimeError("未找到 Microsoft Edge")

    profile = Path(PROJECT_ROOT) / "edge_browser_data"
    _, port = _edge_debug_address()
    subprocess.Popen(
        [
            str(edge),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--new-tab",
            "https://www.zhipin.com/web/user/?ka=header-login",
        ],
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def _edge_page_urls():
    _, port = _edge_debug_address()
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as response:
        pages = json.load(response)
    return [page.get("url", "") for page in pages if page.get("type") == "page"]


def is_boss_logged_in():
    return any(
        "zhipin.com" in url and "/web/user/" not in url
        for url in _edge_page_urls()
    )


def open_boss_search_tabs():
    """Open one normal Edge tab per configured keyword after the user logs in."""
    config = load_config().get("search", {})
    city = str(config.get("city", "")).strip()
    city_query = f"&city={quote(city)}" if city else ""
    keywords = [str(item).strip() for item in config.get("keywords", []) if str(item).strip()]
    if not keywords:
        raise RuntimeError("请先至少配置一个搜索关键词")

    edge_paths = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    edge = next((path for path in edge_paths if path.is_file()), None)
    if edge is None:
        raise RuntimeError("未找到 Microsoft Edge")

    profile = Path(PROJECT_ROOT) / "edge_browser_data"
    _, port = _edge_debug_address()
    for keyword in keywords:
        search_url = f"https://www.zhipin.com/web/geek/job?query={quote(keyword)}{city_query}"
        subprocess.Popen(
            [
                str(edge),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}",
                "--new-tab",
                search_url,
            ],
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )


def load_config():
    """加载主配置"""
    path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(data):
    """保存主配置"""
    path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_templates():
    """加载消息模板"""
    path = os.path.join(PROJECT_ROOT, "config", "templates.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(data):
    """保存消息模板"""
    path = os.path.join(PROJECT_ROOT, "config", "templates.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_api_config():
    """加载API配置"""
    path = os.path.join(PROJECT_ROOT, "config", "api.json")
    defaults = {
        "enabled": False, "provider": "openai", "api_key": "",
        "api_base": "https://api.openai.com/v1", "model": "gpt-3.5-turbo",
        "temperature": 0.7, "max_tokens": 200, "resume": "",
    }
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    return defaults


def save_api_config(data):
    """保存API配置"""
    path = os.path.join(PROJECT_ROOT, "config", "api.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BOSS自动投递 - 配置管理</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-size:17px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f5f7fa;color:#333;height:100vh;overflow:hidden}
.container{display:flex;height:100vh}
.sidebar{width:270px;background:#001529;color:#fff;display:flex;flex-direction:column;box-shadow:2px 0 8px rgba(0,0,0,.1)}
.logo{padding:28px 24px;border-bottom:1px solid rgba(255,255,255,.1)}
.logo h1{font-size:23px;font-weight:600;margin-bottom:6px}
.logo .version{font-size:15px;opacity:.7}
.nav{flex:1;padding:14px 0;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:14px;padding:16px 24px;color:rgba(255,255,255,.75);cursor:pointer;transition:all .2s;font-size:17px;border-left:4px solid transparent}
.nav-item:hover{background:rgba(255,255,255,.08);color:#fff}
.nav-item.active{background:rgba(22,119,255,.15);color:#fff;border-left-color:#1677ff}
.nav-item .icon{font-size:22px;width:24px;text-align:center}
.nav-item .badge{display:inline-block;background:#ff4d4f;color:#fff;font-size:13px;border-radius:10px;padding:2px 8px;margin-left:auto}
.run-section{padding:20px 24px;border-top:1px solid rgba(255,255,255,.1)}
.run-btn{width:100%;background:#52c41a;color:#fff;border:none;padding:16px;border-radius:6px;font-size:18px;font-weight:600;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:10px}
.run-btn:hover{background:#73d13d;transform:translateY(-1px);box-shadow:0 4px 12px rgba(82,196,26,.3)}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.header{background:#fff;padding:26px 40px;border-bottom:1px solid #e8e8e8;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.header h2{font-size:26px;color:#000;font-weight:600}
.header .desc{font-size:17px;color:#777;margin-top:8px}
.content{flex:1;overflow-y:auto;padding:32px 40px}
.card{background:#fff;border-radius:8px;padding:32px;margin-bottom:24px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.card h3{font-size:21px;margin-bottom:20px;color:#000;display:flex;align-items:center;gap:10px;font-weight:600}
.card h3 .icon{width:24px;height:24px}
label.slabel{display:block;font-size:16px;color:#555;margin-bottom:8px;font-weight:500}
input[type="text"],input[type="url"],input[type="password"],input[type="number"],textarea,select{width:100%;padding:14px 16px;border:1px solid #d9d9d9;border-radius:5px;font-size:18px;outline:none;transition:all .2s;font-family:inherit}
input:focus,textarea:focus,select:focus{border-color:#1677ff;box-shadow:0 0 0 2px rgba(22,119,255,.08)}
textarea{resize:vertical;min-height:90px}
.row{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}
.col{flex:1;min-width:240px}
.col2{flex:2}
.tag-list{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
.tag{display:inline-flex;align-items:center;gap:8px;background:#f0f5ff;color:#1677ff;padding:9px 15px;border-radius:5px;font-size:16px;border:1px solid #d6e4ff}
.tag .del{width:20px;height:20px;cursor:pointer;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;color:#999;transition:all .2s}
.tag .del:hover{background:#ff4d4f;color:#fff}
.tag-input-row{display:flex;gap:12px;align-items:flex-end}
.tag-input-row input{flex:1}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:13px 20px;border:none;border-radius:5px;font-size:17px;cursor:pointer;font-weight:500;transition:all .2s;font-family:inherit}
.btn-primary{background:#1677ff;color:#fff}
.btn-primary:hover{background:#4096ff}
.btn-default{background:#fff;color:#333;border:1px solid #d9d9d9}
.btn-default:hover{border-color:#1677ff;color:#1677ff}
.btn-sm{padding:11px 16px;font-size:16px}
.btn-group{display:flex;gap:12px;margin-top:20px}
.msg-preview{background:#fafafa;border:1px solid #e8e8e8;border-radius:5px;padding:18px 20px;margin-top:16px;font-size:17px;color:#444;line-height:1.8}
.msg-preview .highlight{background:#fff3cd;padding:2px 7px;border-radius:3px;font-weight:500;color:#d48806}
.toast{position:fixed;top:28px;left:50%;transform:translateX(-50%);background:#52c41a;color:#fff;padding:14px 28px;border-radius:5px;font-size:17px;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,.15);animation:fadeIn .3s}
.toast.err{background:#ff4d4f}
@keyframes fadeIn{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
.toggle-switch{position:relative;display:inline-block;width:44px;height:22px}
.toggle-switch input{display:none}
.toggle-slider{position:absolute;inset:0;background:#ccc;border-radius:22px;cursor:pointer;transition:.3s}
.toggle-slider::before{content:"";position:absolute;width:18px;height:18px;left:2px;bottom:2px;background:#fff;border-radius:50%;transition:.3s}
.toggle-switch input:checked+.toggle-slider{background:#1677ff}
.toggle-switch input:checked+.toggle-slider::before{transform:translateX(22px)}
.tip{font-size:15px;color:#777;margin-top:8px;line-height:1.7}
.section-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.empty{text-align:center;color:#aaa;padding:30px;font-size:16px}
.panel{display:none}
.panel.active{display:block}
.info-card{background:#e6f7ff;border:1px solid #91d5ff;border-radius:5px;padding:22px;margin-bottom:24px}
.info-card h3{font-size:19px;color:#096dd9;margin-bottom:12px;font-weight:600}
.info-card ul{font-size:16px;color:#444;line-height:1.9;padding-left:24px}
.info-card ul li{margin-bottom:6px}
.template-item{display:flex;align-items:center;gap:14px;padding:16px 18px;background:#fafafa;border:1px solid #e8e8e8;border-radius:5px;margin-bottom:10px;transition:all .2s}
.template-item:hover{background:#f0f5ff;border-color:#adc6ff}
.template-item .text{flex:1;font-size:17px;line-height:1.7;color:#333}
.template-item .del{width:30px;height:30px;cursor:pointer;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:20px;color:#999;transition:all .2s}
.template-item .del:hover{background:#ff4d4f;color:#fff}
.test-status{margin:14px 0;font-size:16px;color:#555}
.test-results{display:grid;gap:12px}
.test-result{border:1px solid #e8e8e8;border-radius:5px;padding:16px;background:#fafafa}
.test-result dl{display:grid;grid-template-columns:110px 1fr;gap:8px 14px;margin:0;font-size:15px;line-height:1.6}
.test-outcomes{display:grid;gap:8px;margin-bottom:12px}.test-outcome{display:flex;justify-content:space-between;gap:12px;padding:10px 12px;border:1px solid #e8e8e8;border-radius:5px;font-size:15px}.test-outcome.ok{border-color:#b7eb8f;background:#f6ffed}.test-outcome.failed{border-color:#ffccc7;background:#fff2f0}.test-outcome span{color:#666;overflow-wrap:anywhere}
.test-result dt{color:#777;font-weight:600}.test-result dd{margin:0;white-space:pre-wrap;word-break:break-word}
.match-score{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:50%;font-size:14px;font-weight:700;color:#fff;flex-shrink:0}
.match-high{background:#52c41a}.match-mid{background:#faad14}.match-low{background:#ff4d4f}
.match-header{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.match-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.match-tag{display:inline-block;background:#e6f7ff;color:#096dd9;padding:3px 10px;border-radius:3px;font-size:13px}
.match-summary{font-size:14px;color:#555;margin-top:6px;line-height:1.6}
.match-bar{height:4px;border-radius:2px;margin-top:6px;transition:width .5s}
.ai-match-btn{background:linear-gradient(135deg,#722ed1,#1677ff);color:#fff;margin-left:10px}
.ai-match-btn:hover{opacity:.9;transform:translateY(-1px)}
.sort-bar{display:flex;align-items:center;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.sort-bar select{padding:8px 12px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;width:auto}
.resume-textarea{min-height:160px;font-size:15px;line-height:1.7}
.ai-loading{display:flex;align-items:center;gap:10px;padding:16px;color:#1677ff}
.ai-loading::before{content:'';width:18px;height:18px;border:2px solid #1677ff;border-top-color:transparent;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

</style>
</head>
<body>
<div class="container">
  <div class="sidebar">
    <div class="logo">
      <h1>⚡ BOSS自动投递</h1>
      <div class="version">配置管理 v1.0</div>
    </div>
    <div class="nav">
      <div class="nav-item active" onclick="switchPanel('greeting')">
        <span class="icon">💬</span>
        <span>发送消息</span>
      </div>
      <div class="nav-item" onclick="switchPanel('keywords')">
        <span class="icon">🔍</span>
        <span>岗位筛选</span>
      </div>
      <div class="nav-item" onclick="switchPanel('delivery')">
        <span class="icon">⚙️</span>
        <span>投递设置</span>
      </div>
      <div class="nav-item" onclick="switchPanel('api')">
        <span class="icon">🤖</span>
        <span>AI配置</span>
        <span class="badge" id="api-badge" style="display:none">ON</span>
      </div>
      <div class="nav-item" onclick="switchPanel('help')">
        <span class="icon">❓</span>
        <span>使用说明</span>
      </div>
    </div>
    <div class="run-section">
      <button class="run-btn" onclick="startDelivery()">
        <span>▶</span>
        <span>启动投递</span>
      </button>
    </div>
  </div>
  
  <div class="main">
    <div class="header">
      <h2 id="page-title">发送消息配置</h2>
      <div class="desc" id="page-desc">设置发给HR的打招呼消息模板</div>
    </div>
    <div class="content">
      
      <!-- 面板1: 发送消息 -->
      <div id="panel-greeting" class="panel active">
        <div class="card">
          <h3>📝 消息模板</h3>
          <div class="tip">可用占位符: <code>{position}</code> 职位名、<code>{company}</code> 公司名、<code>{hr_name}</code> HR名</div>
          <div id="template-list" style="margin-top:16px"></div>
          <div class="tag-input-row" style="margin-top:12px">
            <input type="text" id="new-template" placeholder="输入新模板，按回车添加..." onkeydown="if(event.key==='Enter')addTemplate()">
            <button class="btn btn-primary btn-sm" onclick="addTemplate()">添加</button>
          </div>
          <div class="btn-group">
            <button class="btn btn-primary" onclick="saveTemplates()">💾 保存模板</button>
            <button class="btn btn-default" onclick="loadAllData()">🔄 重新加载</button>
          </div>
        </div>

        <div class="card">
          <h3>👁️ 实时预览</h3>
          <div class="row">
            <div class="col"><label class="slabel">模拟职位名</label><input type="text" id="preview-position" value="Python后端开发工程师" oninput="updatePreview()"></div>
            <div class="col"><label class="slabel">模拟公司名</label><input type="text" id="preview-company" value="腾讯科技" oninput="updatePreview()"></div>
            <div class="col"><label class="slabel">模拟HR名</label><input type="text" id="preview-hr" value="HR" oninput="updatePreview()"></div>
          </div>
          <div class="msg-preview" id="msg-preview"></div>
        </div>
      </div>

      <!-- 面板2: 岗位筛选 -->
      <div id="panel-keywords" class="panel">
        <div class="card">
          <h3>🎯 搜索关键词</h3>
          <div class="tip">BOSS直聘搜索框中使用的关键词</div>
          <div class="tag-list" id="search-keywords"></div>
          <div class="tag-input-row" style="margin-top:12px">
            <input type="text" id="new-search-kw" placeholder="如: Python开发" onkeydown="if(event.key==='Enter')addSearchKeyword()">
            <button class="btn btn-primary btn-sm" onclick="addSearchKeyword()">添加</button>
          </div>
        </div>

        <div class="card">
          <h3>✅ 必须包含关键词</h3>
          <div class="tip">职位描述中必须包含的关键词（全部满足才投递）</div>
          <div class="tag-list" id="required-keywords"></div>
          <div class="tag-input-row" style="margin-top:12px">
            <input type="text" id="new-required-kw" placeholder="如: Django" onkeydown="if(event.key==='Enter')addRequiredKeyword()">
            <button class="btn btn-primary btn-sm" onclick="addRequiredKeyword()">添加</button>
          </div>
        </div>

        <div class="card">
          <h3>🚫 排除关键词</h3>
          <div class="tip">职位描述中包含任一排除词则跳过</div>
          <div class="tag-list" id="excluded-keywords"></div>
          <div class="tag-input-row" style="margin-top:12px">
            <input type="text" id="new-excluded-kw" placeholder="如: 外包、实习" onkeydown="if(event.key==='Enter')addExcludedKeyword()">
            <button class="btn btn-primary btn-sm" onclick="addExcludedKeyword()">添加</button>
          </div>
        </div>

        <div class="card">
          <h3>🏢 城市 & 薪资</h3>
          <div class="row">
            <div class="col"><label class="slabel">目标城市</label><input type="text" id="cfg-city" placeholder="如: 北京、上海、深圳"></div>
            <div class="col"><label class="slabel">最低薪资(K/月)</label><input type="number" id="cfg-min-salary" min="5" max="100"></div>
            <div class="col"><label class="slabel">工作经验</label>
              <select id="cfg-experience">
                <option value="应届生">应届生</option><option value="1年以内">1年以内</option><option value="1-3年">1-3年</option>
                <option value="3-5年">3-5年</option><option value="5-10年">5-10年</option><option value="10年以上">10年以上</option>
              </select>
            </div>
          </div>
          <div class="btn-group">
            <button class="btn btn-primary" onclick="saveKeywordsConfig()">💾 保存设置</button>
          </div>
        </div>
      </div>

      <!-- 面板3: 投递设置 -->
      <div id="panel-delivery" class="panel">
        <div class="card">
          <h3>⚙️ 投递频率</h3>
          <div class="row">
            <div class="col"><label class="slabel">每天最多投递</label><input type="number" id="cfg-max-day" min="1" max="200"></div>
            <div class="col"><label class="slabel">每小时最多投递</label><input type="number" id="cfg-max-hour" min="1" max="50"></div>
            <div class="col"><label class="slabel">操作间隔(秒)</label><input type="number" id="cfg-min-delay" min="1" max="30"></div>
          </div>
        </div>
        
        <div class="card">
          <div class="section-header">
            <h3>🧪 测试搜索</h3>
            <label class="toggle-switch"><input type="checkbox" id="cfg-test-mode" onchange="toggleTestMode()"><span class="toggle-slider"></span></label>
          </div>
          <div class="tip">开启后只搜索并读取岗位信息，不会投递或发送任何消息。关闭后按正式投递流程执行。</div>
          <div class="btn-group">
            <button class="btn btn-default" onclick="previewJobs()">📋 读取当前搜索标签</button>
            <button class="btn btn-primary ai-match-btn" onclick="aiMatchJobs()" id="btn-ai-match">🤖 AI智能匹配</button>
          </div>
          <div class="sort-bar" id="ai-sort-bar" style="display:none">
            <span style="font-size:14px;color:#555">排序:</span>
            <select onchange="sortMatchedJobs()" id="ai-sort-select">
              <option value="score">按匹配度降序</option>
              <option value="tags">按命中标签数降序</option>
              <option value="salary">按薪资降序</option>
            </select>
            <span style="font-size:13px;color:#888;margin-left:auto" id="ai-count-label"></span>
          </div>
          <div class="test-status" id="test-status">测试模式未开启</div>
          <div class="test-results" id="test-results"></div>
        </div>

        <div class="card">
          <h3>💬 消息发送</h3>
          <div class="row">
            <div class="col">
              <label class="slabel">自动发送打招呼消息</label>
              <label class="toggle-switch"><input type="checkbox" id="cfg-auto-greet"><span class="toggle-slider"></span></label>
              <div class="tip">开启后会自动发送消息模板，建议开启</div>
            </div>
            <div class="col">
              <label class="slabel">投递模式</label>
              <select id="cfg-mode">
                <option value="conservative">保守模式（严格筛选）</option>
                <option value="smart">智能模式（动态调整）</option>
                <option value="aggressive">激进模式（大量投递）</option>
              </select>
              <div class="tip">智能模式根据通过率自动调整筛选条件</div>
            </div>
          </div>
          <div class="btn-group">
            <button class="btn btn-primary" onclick="saveDeliveryConfig()">💾 保存设置</button>
          </div>
        </div>
      </div>

      <!-- 面板4: AI配置 -->
      <div id="panel-api" class="panel">
    <div class="card">
      <div class="section-header">
        <h3>🤖 AI智能消息生成</h3>
        <label class="toggle-switch"><input type="checkbox" id="api-enabled" onchange="toggleApiSection(); saveApiConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div class="tip" style="margin-bottom:12px">开启后可根据职位描述自动生成个性化打招呼消息（需自行提供API Key）</div>
      <div id="api-section">
        <div class="row">
          <div class="col"><label class="slabel">API提供商</label>
            <select id="api-provider" onchange="onProviderChange()">
              <option value="openai">OpenAI</option>
              <option value="custom">自定义兼容接口</option>
            </select>
          </div>
          <div class="col"><label class="slabel">模型</label><input type="text" id="api-model" placeholder="gpt-3.5-turbo"></div>
        </div>
        <div class="row" style="margin-top:8px">
          <div class="col2"><label class="slabel">API Key</label><input type="password" id="api-key" placeholder="sk-..."></div>
        </div>
        <div class="row" style="margin-top:8px">
          <div class="col2"><label class="slabel">API地址</label><input type="url" id="api-base" placeholder="https://api.openai.com/v1"></div>
        </div>
        <div class="row" style="margin-top:8px">
          <div class="col"><label class="slabel">温度 (0-2)</label><input type="number" id="api-temperature" min="0" max="2" step="0.1"></div>
          <div class="col"><label class="slabel">最大Token</label><input type="number" id="api-max-tokens" min="50" max="500"></div>
        </div>
        <div class="btn-group" style="margin-top:12px">
          <button class="btn btn-primary" onclick="testApi()">🧪 测试连接</button>
          <button class="btn btn-primary" onclick="saveApiConfig()">💾 保存设置</button>
        </div>
        <div style="margin-top:20px;padding-top:20px;border-top:1px solid #e8e8e8">
          <label class="slabel">📄 我的简历（用于AI智能匹配）</label>
          <textarea id="api-resume" class="resume-textarea" placeholder="粘贴你的简历内容或技能描述，AI将以此为基准匹配最合适的岗位...&#10;&#10;例如：&#10;- 技术栈: Python, React, Django, Docker&#10;- 经验: 3年后端开发&#10;- 学历: 本科计算机&#10;- 期望: 远程办公、AI方向"></textarea>
          <div class="tip">简历仅保存在本地，不会上传到任何第三方。填写后AI会根据你的简历自动匹配合适的岗位。</div>
        </div>
      </div>
    </div>
    <div class="card" style="background:#fffbe6;border:1px solid #ffe58f">
      <h3>💡 说明</h3>
      <ul style="font-size:14px;color:#555;line-height:2;padding-left:18px">
        <li>脚本本身<strong>不强制需要AI</strong>，默认使用预设模板即可正常投递</li>
        <li>开启AI后，它会根据每条职位描述自动生成个性化消息，<strong>提高HR回复率</strong></li>
        <li>支持 OpenAI 及任何兼容接口（如国内中转、本地模型等）</li>
        <li>API Key 仅保存在本地 <code>config/api.json</code>，不会上传</li>
      </ul>
    </div>
  </div>

  <!-- 面板5: 使用说明 -->
  <div id="panel-help" class="panel">
    <div class="info-card">
      <h3>使用说明</h3>
      <ul>
        <li>先在发送消息和岗位筛选中完成基础配置，再保存对应设置。</li>
        <li>投递设置用于控制频率和自动打招呼消息。</li>
        <li>AI配置为可选功能，未启用时将使用消息模板投递。</li>
        <li>完成配置后，点击左下角“启动投递”开始执行。</li>
      </ul>
    </div>
  </div>

</div>

<script>
// === State ===
let state = {templates:[],searchKeywords:[],requiredKeywords:[],excludedKeywords:[],delivery:{},api:{}};

// === Navigation ===
const panelMeta={
  greeting:['发送消息配置','设置发给HR的打招呼消息模板'],
  keywords:['岗位筛选配置','设置职位搜索与筛选条件'],
  delivery:['投递设置','控制投递频率与消息发送方式'],
  api:['AI配置','管理个性化消息生成服务'],
  help:['使用说明','查看配置与启动投递的基本流程']
};

function switchPanel(name){
  const panel=document.getElementById('panel-'+name);
  const meta=panelMeta[name];
  if(!panel||!meta)return;
  document.querySelectorAll('.nav-item').forEach(item=>item.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(item=>item.classList.remove('active'));
  panel.classList.add('active');
  document.querySelector(`.nav-item[onclick="switchPanel('${name}')"]`).classList.add('active');
  document.getElementById('page-title').textContent=meta[0];
  document.getElementById('page-desc').textContent=meta[1];
}

// === Toast ===
function toast(msg,isErr){
  let t=document.createElement('div');t.className='toast'+(isErr?' err':'');
  t.textContent=msg;document.body.appendChild(t);
  setTimeout(()=>t.remove(),2000);
}

// === Load All ===
async function loadAllData(){
  try{
    let r=await fetch('/api/config');
    let d=await r.json();
    state.templates=d.templates||[];
    state.searchKeywords=d.search_keywords||[];
    state.requiredKeywords=d.required_keywords||[];
    state.excludedKeywords=d.excluded_keywords||[];
    state.delivery=d.delivery||{};
    state.api=d.api||{};
    renderAll();
    updateApiBadge();
  }catch(e){toast('加载配置失败: '+e.message,true)}
}

// === Render ===
function renderTemplates(){
  let el=document.getElementById('template-list');
  if(!state.templates.length){el.innerHTML='<div class="empty">暂无模板，请添加</div>';return}
  el.innerHTML=state.templates.map((t,i)=>`<div class="tag" style="width:100%;padding:8px 14px;margin-bottom:6px">
    <span style="flex:1;font-size:14px;line-height:1.7">${t.replace(/\{(\w+)\}/g,'<span class="highlight">{$1}</span>')}</span>
    <span class="del" onclick="delTemplate(${i})" title="删除">✕</span>
  </div>`).join('');
  updatePreview();
}

function renderTagList(id,list){
  let el=document.getElementById(id);
  if(!list.length){el.innerHTML='<div class="empty">暂无</div>';return}
  el.innerHTML=list.map((t,i)=>`<span class="tag">${t}<span class="del" onclick="delFromList('${id}',${i})">✕</span></span>`).join('');
}

function renderAll(){
  renderTemplates();
  renderTagList('search-keywords',state.searchKeywords);
  renderTagList('required-keywords',state.requiredKeywords);
  renderTagList('excluded-keywords',state.excludedKeywords);
  // fill form fields
  let d=state.delivery;
  document.getElementById('cfg-max-day').value=d.max_per_day||100;
  document.getElementById('cfg-max-hour').value=d.max_per_hour||20;
  document.getElementById('cfg-min-delay').value=(d.anti_crawler||{}).min_delay||3;
  document.getElementById('cfg-auto-greet').checked=d.auto_send_greeting!==false;
  document.getElementById('cfg-test-mode').checked=d.test_mode===true;
  document.getElementById('cfg-mode').value=d.mode||'smart';
  toggleTestMode();
  let f=state.filter||{};
  document.getElementById('cfg-city').value=(state.search||{}).city||'';
  document.getElementById('cfg-min-salary').value=f.min_salary||15;
  document.getElementById('cfg-experience').value=(state.search||{}).experience||'3-5年';
  // api
  let a=state.api;
  document.getElementById('api-enabled').checked=a.enabled||false;
  document.getElementById('api-provider').value=a.provider||'openai';
  document.getElementById('api-model').value=a.model||'gpt-3.5-turbo';
  document.getElementById('api-key').value=a.api_key||'';
  document.getElementById('api-base').value=a.api_base||'https://api.openai.com/v1';
  document.getElementById('api-temperature').value=a.temperature||0.7;
  document.getElementById('api-max-tokens').value=a.max_tokens||200;
  document.getElementById('api-resume').value=a.resume||'';
  toggleApiSection();
}

function updateApiBadge(){
  let b=document.getElementById('api-badge');
  b.style.display=state.api.enabled?'inline-block':'none';
}

function updatePreview(){
  let pos=document.getElementById('preview-position').value||'Python后端开发';
  let com=document.getElementById('preview-company').value||'腾讯科技';
  let hr=document.getElementById('preview-hr').value||'HR';
  let tpl=state.templates[0]||'暂无模板';
  let msg=tpl.replace(/\{position\}/g,pos).replace(/\{company\}/g,com).replace(/\{hr_name\}/g,hr);
  document.getElementById('msg-preview').innerHTML=msg.replace(/\{(\w+)\}/g,'<span class="highlight">{$1}</span>');
}

// === Template Ops ===
function addTemplate(){
  let v=document.getElementById('new-template').value.trim();
  if(!v)return;
  state.templates.push(v);
  document.getElementById('new-template').value='';
  renderTemplates();
}
function delTemplate(i){state.templates.splice(i,1);renderTemplates()}

// === Tag Ops ===
function addToList(inputId,listKey){
  let v=document.getElementById(inputId).value.trim();
  if(!v)return;
  state[listKey].push(v);
  document.getElementById(inputId).value='';
  renderAll();
}
function delFromList(renderId,i){
  let map={'search-keywords':'searchKeywords','required-keywords':'requiredKeywords','excluded-keywords':'excludedKeywords'};
  state[map[renderId]].splice(i,1);
  renderAll();
}

function addSearchKeyword(){addToList('new-search-kw','searchKeywords')}
function addRequiredKeyword(){addToList('new-required-kw','requiredKeywords')}
function addExcludedKeyword(){addToList('new-excluded-kw','excludedKeywords')}

let testResultsTimer=null;
function toggleTestMode(){
  const enabled=document.getElementById('cfg-test-mode').checked;
  document.getElementById('test-status').textContent=enabled?'测试模式已开启：启动后仅搜索和预览，不会投递。':'测试模式未开启：启动后将执行正式投递。';
  if(enabled&&!testResultsTimer)loadTestResults();
}

async function loadTestResults(){
  try{
    const response=await fetch('/api/test-results');
    const data=await response.json();
    const statusMap={idle:'暂无测试结果',running:'正在搜索并读取岗位信息...',completed:'测试搜索完成',failed:'测试搜索失败'};
    document.getElementById('test-status').textContent=statusMap[data.status]||'测试状态未知'+(data.error?': '+data.error:'');
    const results=data.results||[];
    const outcomes=data.search_outcomes||[];
    const outcomeHtml=outcomes.length?`<div class="test-outcomes">${outcomes.map(item=>`<div class="test-outcome ${item.status==='ok'?'ok':'failed'}"><strong>${escapeHtml(item.keyword)}</strong><span>${item.status==='ok'?`找到 ${item.count} 个岗位`:`${escapeHtml(item.status)}${item.diagnostic_path?` · ${escapeHtml(item.diagnostic_path)}`:''}`}</span></div>`).join('')}</div>`:'';
    const previewHtml=results.length?results.map((item,index)=>`<div class="test-result"><strong>岗位 ${index+1}</strong><dl><dt>关键词</dt><dd>${escapeHtml(item.keyword)}</dd><dt>地点</dt><dd>${escapeHtml(item.location)}</dd><dt>岗位要求</dt><dd>${escapeHtml(item.requirements)}</dd><dt>面试方式</dt><dd>${escapeHtml(item.interview_type)}</dd><dt>薪资</dt><dd>${escapeHtml(item.salary)}</dd></dl></div>`).join(''):'<div class="empty">暂无岗位预览信息</div>';
    document.getElementById('test-results').innerHTML=outcomeHtml+previewHtml;
    if(data.status==='running')testResultsTimer=setTimeout(()=>{testResultsTimer=null;loadTestResults()},1500);
  }catch(e){document.getElementById('test-status').textContent='读取测试结果失败: '+e.message}
}

function escapeHtml(value){
  const element=document.createElement('div');
  element.textContent=value||'无';
  return element.innerHTML;
}

// === Save Functions ===
async function saveTemplates(){
  try{
    let r=await fetch('/api/templates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({templates:state.templates})});
    if(r.ok)toast('消息模板已保存！');
  }catch(e){toast('保存失败: '+e.message,true)}
}

async function saveDeliveryConfig(showToast=true){
  let d={
    mode:document.getElementById('cfg-mode').value,
    max_per_day:parseInt(document.getElementById('cfg-max-day').value),
    max_per_hour:parseInt(document.getElementById('cfg-max-hour').value),
    auto_send_greeting:document.getElementById('cfg-auto-greet').checked,
    test_mode:document.getElementById('cfg-test-mode').checked,
    greeting_template:state.templates[0]||'您好，我对贵公司的{position}职位很感兴趣。'
  };
  let ac={min_delay:parseInt(document.getElementById('cfg-min-delay').value),max_delay:8,random_scroll:true,mouse_simulation:true,max_retry:3};
  try{
    let r=await fetch('/api/delivery',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delivery:d,anti_crawler:ac})});
    if(!r.ok)throw new Error('保存投递设置失败');
    state.delivery=d;
    if(showToast)toast(d.test_mode?'测试模式已保存！':'投递设置已保存！');
    return true;
  }catch(e){toast('保存失败: '+e.message,true);return false}
}

async function saveKeywordsConfig(){
  let s={keywords:state.searchKeywords,city:document.getElementById('cfg-city').value,
    experience:document.getElementById('cfg-experience').value,education:'本科',salary_min:parseInt(document.getElementById('cfg-min-salary').value),salary_max:30,job_type:'全职'};
  let f={required_keywords:state.requiredKeywords,excluded_keywords:state.excludedKeywords,
    min_salary:parseInt(document.getElementById('cfg-min-salary').value),company_size:['500-999人','1000人以上'],finance_stage:['已上市','D轮及以上']};
  try{
    let r=await fetch('/api/keywords',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({search:s,filter:f})});
    if(r.ok)toast('关键词配置已保存！');
  }catch(e){toast('保存失败: '+e.message,true)}
}

async function saveApiConfig(){
  let a={
    enabled:document.getElementById('api-enabled').checked,
    provider:document.getElementById('api-provider').value,
    api_key:document.getElementById('api-key').value,
    api_base:document.getElementById('api-base').value,
    model:document.getElementById('api-model').value,
    temperature:parseFloat(document.getElementById('api-temperature').value),
    max_tokens:parseInt(document.getElementById('api-max-tokens').value),
    resume:document.getElementById('api-resume').value
  };
  try{
    let r=await fetch('/api/config/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)});
    if(r.ok){
      state.api=a;
      toast('API配置已保存！');
      updateApiBadge();
    }
  }catch(e){toast('保存失败: '+e.message,true)}
}

async function testApi(){
  if(!document.getElementById('api-enabled').checked){toast('请先开启AI功能',true);return}
  toast('正在测试连接...');
  try{
    let r=await fetch('/api/test',{method:'POST'});
    let d=await r.json();
    if(d.ok)toast('✅ 连接成功！模型返回: '+d.reply);
    else toast('❌ 连接失败: '+d.error,true);
  }catch(e){toast('测试请求失败: '+e.message,true)}
}

async function previewJobs(){
  document.getElementById('test-status').textContent='正在只读提取当前搜索标签的岗位信息...';
  try{
    const response=await fetch('/api/preview-jobs',{method:'POST'});
    const data=await response.json();
    if(!data.ok)throw new Error(data.error||'读取失败');
    document.getElementById('test-status').textContent=`已读取 ${data.count} 个岗位；未发送消息或投递。`;
    document.getElementById('test-results').innerHTML=data.jobs.length?data.jobs.map((item,index)=>`<div class="test-result"><strong>岗位 ${index+1}</strong><dl><dt>关键词</dt><dd>${escapeHtml(item.keyword)}</dd><dt>职位</dt><dd>${escapeHtml(item.title)}</dd><dt>公司</dt><dd>${escapeHtml(item.company)}</dd><dt>地址</dt><dd>${escapeHtml(item.location)}</dd><dt>薪资</dt><dd>${escapeHtml(item.salary)}</dd><dt>标签</dt><dd>${escapeHtml((item.tags||[]).join(' / '))}</dd><dt>要求</dt><dd>${escapeHtml(item.requirements)}</dd></dl></div>`).join(''):'<div class="empty">未识别到岗位卡片，请确认搜索标签已加载完成。</div>';
  }catch(e){document.getElementById('test-status').textContent='读取岗位失败: '+e.message}
}

function toggleApiSection(){
  let en=document.getElementById('api-enabled').checked;
  document.getElementById('api-section').style.opacity=en?'1':'0.4';
  document.getElementById('api-section').style.pointerEvents='auto';
  updateApiBadge();
}

function onProviderChange(){
  let p=document.getElementById('api-provider').value;
  if(p==='openai')document.getElementById('api-base').value='https://api.openai.com/v1';
}

async function startDelivery(){
  const testMode=document.getElementById('cfg-test-mode').checked;
  if(!await saveDeliveryConfig(false))return;
  try{
    const response=await fetch('/api/start',{method:'POST'});
    const data=await response.json();
    if(!data.ok){toast('启动失败: '+data.error,true);return}
    if(data.status==='search_tabs_opened'){
      document.getElementById('test-status').textContent='已检测到 BOSS 登录，正在为全部关键词打开搜索标签页。';
      document.getElementById('test-results').innerHTML='<div class="empty">已打开关键词搜索标签页，请在 BOSS 页面查看岗位。</div>';
      toast('已在当前 Edge 中打开全部关键词搜索标签页。');
    }else if(testMode){
      document.getElementById('test-status').textContent='已在当前 Edge 新标签页打开 BOSS 登录页面，请完成登录后再次点击启动投递。';
      document.getElementById('test-results').innerHTML='<div class="empty">等待你完成 BOSS 登录...</div>';
      toast('BOSS 登录页已在当前 Edge 新标签页打开。');
    }else toast('BOSS 登录页已在当前 Edge 新标签页打开。');
  }catch(e){toast('启动失败: '+e.message,true)}
}

// === AI 智能匹配 ===
let matchedJobs=[];

async function aiMatchJobs(){
  const btn=document.getElementById('btn-ai-match');
  const statusEl=document.getElementById('test-status');
  const resultsEl=document.getElementById('test-results');
  const sortBar=document.getElementById('ai-sort-bar');
  const countLabel=document.getElementById('ai-count-label');

  btn.disabled=true; btn.textContent='⏳ AI分析中...';
  statusEl.textContent='正在读取搜索标签页的岗位信息...';
  resultsEl.innerHTML='<div class="ai-loading">正在通过CDP读取岗位数据...</div>';

  try{
    // 1. 先读取搜索标签页的岗位
    const previewResp=await fetch('/api/preview-jobs',{method:'POST'});
    const previewData=await previewResp.json();
    if(!previewData.ok)throw new Error(previewData.error||'读取岗位失败');
    if(!previewData.jobs.length){statusEl.textContent='未读取到任何岗位，请先在BOSS页面搜索。';btn.disabled=false;btn.textContent='🤖 AI智能匹配';return}

    statusEl.textContent=`已读取 ${previewData.jobs.length} 个岗位，正在调用AI进行智能匹配...`;
    resultsEl.innerHTML='<div class="ai-loading">AI正在分析岗位匹配度，请稍候...</div>';

    // 2. 调用AI匹配
    const tags=state.searchKeywords;
    const resume=document.getElementById('api-resume').value||state.api.resume||'';
    const matchResp=await fetch('/api/ai-match',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jobs:previewData.jobs,tags:tags,resume:resume})
    });
    const matchData=await matchResp.json();
    if(!matchData.ok){
      // 如果AI不可用，用本地标签计数作为fallback
      if(matchData.error&&matchData.error.includes('未开启')){
        statusEl.textContent='AI功能未开启，使用标签计数匹配。请在AI配置中开启后重试。';
        matchedJobs=simpleTagMatch(previewData.jobs,tags);
      }else{
        throw new Error(matchData.error||'AI匹配失败');
      }
    }else{
      matchedJobs=matchData.results||[];
      const avgScore=matchedJobs.length?Math.round(matchedJobs.reduce((s,j)=>s+(j.match_score||0),0)/matchedJobs.length):0;
      statusEl.textContent=`AI智能匹配完成！共 ${matchedJobs.length} 个岗位，平均匹配度 ${avgScore} 分`;
    }

    sortBar.style.display='flex';
    countLabel.textContent=`共 ${matchedJobs.length} 个岗位`;
    renderMatchedJobs();
  }catch(e){
    statusEl.textContent='AI匹配失败: '+e.message;
    resultsEl.innerHTML='<div class="empty">'+escapeHtml(e.message)+'</div>';
  }
  btn.disabled=false; btn.textContent='🤖 AI智能匹配';
}

function simpleTagMatch(jobs,tags){
  const tl=tags.map(t=>t.toLowerCase());
  return jobs.map(j=>{
    const text=JSON.stringify(j).toLowerCase();
    const matched=tl.filter(t=>text.includes(t));
    j.match_score=matched.length*10;
    j.matched_tags=matched;
    j.match_summary=matched.length?`命中 ${matched.length}/${tags.length} 个标签`:'未命中标签';
    return j;
  }).sort((a,b)=>(b.match_score||0)-(a.match_score||0));
}

function sortMatchedJobs(){
  const sortBy=document.getElementById('ai-sort-select').value;
  if(sortBy==='tags'){
    matchedJobs.sort((a,b)=>(b.matched_tags||[]).length-(a.matched_tags||[]).length);
  }else if(sortBy==='salary'){
    matchedJobs.sort((a,b)=>parseSalary(b.salary)-parseSalary(a.salary));
  }else{
    matchedJobs.sort((a,b)=>(b.match_score||0)-(a.match_score||0));
  }
  renderMatchedJobs();
}

function parseSalary(s){
  if(!s)return 0;
  const m=s.toString().match(/(\d+)[kK]/);
  return m?parseInt(m[1]):parseInt(s)||0;
}

function renderMatchedJobs(){
  const resultsEl=document.getElementById('test-results');
  if(!matchedJobs.length){resultsEl.innerHTML='<div class="empty">暂无匹配结果</div>';return}
  resultsEl.innerHTML=matchedJobs.map((item,idx)=>{
    const score=item.match_score||0;
    const cls=score>=70?'match-high':score>=40?'match-mid':'match-low';
    const barColor=score>=70?'#52c41a':score>=40?'#faad14':'#ff4d4f';
    const tags=(item.matched_tags||[]).map(t=>`<span class="match-tag">${escapeHtml(t)}</span>`).join('');
    const keyInfo=item.key_info||{};
    const kiHtml=keyInfo.tech_stack?`<div style="margin-top:8px;font-size:13px;color:#666"><strong>技术栈:</strong> ${escapeHtml(keyInfo.tech_stack)}</div>`:'';
    return `<div class="test-result" style="border-left:3px solid ${barColor}">
      <div class="match-header">
        <div class="match-score ${cls}">${score}</div>
        <div style="flex:1">
          <strong style="font-size:16px">${idx+1}. ${escapeHtml(item.title)}</strong>
          <span style="color:#888;margin-left:8px">${escapeHtml(item.company)}</span>
          <span style="color:#1677ff;margin-left:8px">${escapeHtml(item.salary)}</span>
        </div>
      </div>
      <div class="match-bar" style="width:${score}%;background:${barColor}"></div>
      <div class="match-summary">${escapeHtml(item.match_summary||'')}</div>
      <div class="match-meta">${tags}</div>
      ${kiHtml}
      <dl style="margin-top:8px;grid-template-columns:90px 1fr">
        <dt>岗位要求</dt><dd>${escapeHtml((item.requirements||'无').substring(0,200))}</dd>
        <dt>地点</dt><dd>${escapeHtml(item.location||'未知')}</dd>
      </dl>
    </div>`;
  }).join('');
}

// === Init ===
loadAllData();
</script>
</body>
</html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress log

    def _send(self, code, content, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.wfile.write(content)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send(200, HTML, "text/html; charset=utf-8")
        elif self.path == "/api/config":
            try:
                cfg = load_config()
                tmpl = load_templates()
                api = load_api_config()
                data = {
                    "templates": tmpl.get("greeting_templates", []),
                    "search_keywords": cfg.get("search", {}).get("keywords", []),
                    "required_keywords": cfg.get("filter", {}).get("required_keywords", []),
                    "excluded_keywords": cfg.get("filter", {}).get("excluded_keywords", []),
                    "delivery": cfg.get("delivery", {}),
                    "filter": cfg.get("filter", {}),
                    "search": cfg.get("search", {}),
                    "anti_crawler": cfg.get("anti_crawler", {}),
                    "api": api,
                }
                self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))
        elif self.path == "/api/test-results":
            result_path = os.path.join(PROJECT_ROOT, "data", "test_results.json")
            default_result = {"status": "idle", "results": []}
            try:
                if os.path.exists(result_path):
                    with open(result_path, "r", encoding="utf-8") as file:
                        default_result = json.load(file)
                self._send(200, json.dumps(default_result, ensure_ascii=False))
            except (OSError, json.JSONDecodeError) as e:
                self._send(200, json.dumps({"status": "failed", "results": [], "error": str(e)}, ensure_ascii=False))

    def _cors(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._cors()

    def do_POST(self):
        try:
            if self.path == "/api/templates":
                data = self._read_body()
                save_templates({"greeting_templates": data.get("templates", [])})
                self._send(200, json.dumps({"ok": True}))

            elif self.path == "/api/delivery":
                data = self._read_body()
                cfg = load_config()
                if "delivery" in data:
                    cfg["delivery"].update(data["delivery"])
                if "anti_crawler" in data:
                    cfg["anti_crawler"] = data["anti_crawler"]
                save_config(cfg)
                self._send(200, json.dumps({"ok": True}))

            elif self.path == "/api/keywords":
                data = self._read_body()
                cfg = load_config()
                if "search" in data:
                    cfg["search"].update(data["search"])
                if "filter" in data:
                    cfg["filter"].update(data["filter"])
                save_config(cfg)
                self._send(200, json.dumps({"ok": True}))

            elif self.path == "/api/config/api":
                data = self._read_body()
                save_api_config(data)
                self._send(200, json.dumps({"ok": True}))

            elif self.path == "/api/test":
                api = load_api_config()
                if not api.get("enabled"):
                    self._send(400, json.dumps({"ok": False, "error": "AI功能未开启"}))
                    return
                try:
                    import requests as req
                    resp = req.post(
                        f"{api['api_base']}/chat/completions",
                        headers={"Authorization": f"Bearer {api['api_key']}", "Content-Type": "application/json"},
                        json={"model": api.get("model", "gpt-3.5-turbo"),
                              "messages": [{"role": "user", "content": "回复一个字：好"}],
                              "max_tokens": 10, "temperature": 0},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        reply = resp.json()["choices"][0]["message"]["content"].strip()
                        self._send(200, json.dumps({"ok": True, "reply": reply}))
                    else:
                        self._send(200, json.dumps({"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}))
                except Exception as e:
                    self._send(200, json.dumps({"ok": False, "error": str(e)}))

            elif self.path == "/api/preview-jobs":
                try:
                    from src.cdp_preview import preview_search_tabs

                    _, port = _edge_debug_address()
                    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as response:
                        pages = json.load(response)
                    jobs, outcomes = preview_search_tabs(pages)
                    self._send(200, json.dumps({
                        "ok": True,
                        "count": len(jobs),
                        "jobs": jobs,
                        "outcomes": outcomes,
                    }, ensure_ascii=False))
                except Exception as exc:
                    logger.error(f"读取岗位预览失败: {exc}", exc_info=True)
                    self._send(500, json.dumps({"ok": False, "error": str(exc)}))

            elif self.path == "/api/start":
                try:
                    if is_boss_logged_in():
                        open_boss_search_tabs()
                        logger.info("检测到 BOSS 已登录，已为全部关键词打开搜索标签页")
                        self._send(200, json.dumps({"ok": True, "status": "search_tabs_opened"}))
                    else:
                        open_boss_login_tab()
                        logger.info("未检测到 BOSS 登录状态，已打开登录页面")
                        self._send(200, json.dumps({"ok": True, "status": "login_tab_opened"}))
                except Exception as exc:
                    logger.error(f"打开 BOSS 页面失败: {exc}", exc_info=True)
                    self._send(500, json.dumps({"ok": False, "error": str(exc)}))

            elif self.path == "/api/ai-match":
                try:
                    from src.ai_matcher import AIJobMatcher
                    api = load_api_config()
                    if not api.get("enabled"):
                        self._send(400, json.dumps({"ok": False, "error": "AI功能未开启，请在AI配置中开启"}))
                        return
                    body = self._read_body()
                    jobs = body.get("jobs", [])
                    tags = body.get("tags", [])
                    resume = body.get("resume", api.get("resume", ""))
                    matcher = AIJobMatcher(api)
                    scored = matcher.match_jobs(jobs, resume or "", tags)
                    self._send(200, json.dumps({"ok": True, "results": scored, "count": len(scored)}, ensure_ascii=False))
                except Exception as exc:
                    logger.error(f"AI匹配失败: {exc}", exc_info=True)
                    self._send(500, json.dumps({"ok": False, "error": str(exc)}))

            elif self.path == "/api/ai-detail":
                try:
                    from src.ai_matcher import AIJobMatcher
                    api = load_api_config()
                    if not api.get("enabled"):
                        self._send(400, json.dumps({"ok": False, "error": "AI功能未开启"}))
                        return
                    body = self._read_body()
                    job = body.get("job", {})
                    tags = body.get("tags", [])
                    resume = body.get("resume", api.get("resume", ""))
                    matcher = AIJobMatcher(api)
                    analysis = matcher.analyze_job_detail(job, resume or "", tags)
                    self._send(200, json.dumps({"ok": True, "analysis": analysis}, ensure_ascii=False))
                except Exception as exc:
                    logger.error(f"AI详情分析失败: {exc}", exc_info=True)
                    self._send(500, json.dumps({"ok": False, "error": str(exc)}))

            else:
                self._send(404, json.dumps({"error": "not found"}))

        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    # 先在线程中启动HTTP服务，再让浏览器打开配置页面
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    logger.info("配置服务已启动，将在项目 Edge 中打开配置页面")
    try:
        launch_configuration_edge()
    except Exception as exc:
        logger.error(f"无法启动配置页 Edge: {exc}")
        raise

    print(f"\n  BOSS自动投递 - 配置管理页面")
    print(f"  ===================================")
    print(f"  地址: http://127.0.0.1:{PORT}")
    print(f"  按 Ctrl+C 停止服务")
    print(f"  ===================================\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  服务已停止。")
        server.shutdown()


if __name__ == "__main__":
    main()
