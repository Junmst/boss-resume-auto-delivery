# -*- coding: utf-8 -*-
"""BOSS自动投递工具 - Web配置管理界面"""

import os
import sys
import json
import yaml
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

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
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"enabled": False, "provider": "openai", "api_key": "", "api_base": "https://api.openai.com/v1", "model": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 200}


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
body{font-size:15px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f5f7fa;color:#333;height:100vh;overflow:hidden}
.container{display:flex;height:100vh}
.sidebar{width:240px;background:#001529;color:#fff;display:flex;flex-direction:column;box-shadow:2px 0 8px rgba(0,0,0,.1)}
.logo{padding:24px 20px;border-bottom:1px solid rgba(255,255,255,.1)}
.logo h1{font-size:20px;font-weight:600;margin-bottom:4px}
.logo .version{font-size:13px;opacity:.6}
.nav{flex:1;padding:12px 0;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:12px;padding:14px 20px;color:rgba(255,255,255,.7);cursor:pointer;transition:all .2s;font-size:15px;border-left:3px solid transparent}
.nav-item:hover{background:rgba(255,255,255,.08);color:#fff}
.nav-item.active{background:rgba(22,119,255,.15);color:#fff;border-left-color:#1677ff}
.nav-item .icon{font-size:18px;width:20px;text-align:center}
.nav-item .badge{display:inline-block;background:#ff4d4f;color:#fff;font-size:11px;border-radius:10px;padding:1px 6px;margin-left:auto}
.run-section{padding:16px 20px;border-top:1px solid rgba(255,255,255,.1)}
.run-btn{width:100%;background:#52c41a;color:#fff;border:none;padding:12px;border-radius:6px;font-size:15px;font-weight:500;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:8px}
.run-btn:hover{background:#73d13d;transform:translateY(-1px);box-shadow:0 4px 12px rgba(82,196,26,.3)}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.header{background:#fff;padding:20px 32px;border-bottom:1px solid #e8e8e8;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.header h2{font-size:20px;color:#000;font-weight:600}
.header .desc{font-size:14px;color:#888;margin-top:6px}
.content{flex:1;overflow-y:auto;padding:24px 32px}
.card{background:#fff;border-radius:8px;padding:24px;margin-bottom:20px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.card h3{font-size:16px;margin-bottom:16px;color:#000;display:flex;align-items:center;gap:8px;font-weight:600}
.card h3 .icon{width:20px;height:20px}
label.slabel{display:block;font-size:13px;color:#666;margin-bottom:6px;font-weight:500}
input[type="text"],input[type="url"],input[type="password"],input[type="number"],textarea,select{width:100%;padding:9px 12px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;outline:none;transition:all .2s;font-family:inherit}
input:focus,textarea:focus,select:focus{border-color:#1677ff;box-shadow:0 0 0 2px rgba(22,119,255,.08)}
textarea{resize:vertical;min-height:90px}
.row{display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.col{flex:1;min-width:200px}
.col2{flex:2}
.tag-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.tag{display:inline-flex;align-items:center;gap:6px;background:#f0f5ff;color:#1677ff;padding:6px 12px;border-radius:4px;font-size:13px;border:1px solid #d6e4ff}
.tag .del{width:16px;height:16px;cursor:pointer;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;color:#999;transition:all .2s}
.tag .del:hover{background:#ff4d4f;color:#fff}
.tag-input-row{display:flex;gap:8px;align-items:flex-end}
.tag-input-row input{flex:1}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 16px;border:none;border-radius:4px;font-size:14px;cursor:pointer;font-weight:500;transition:all .2s;font-family:inherit}
.btn-primary{background:#1677ff;color:#fff}
.btn-primary:hover{background:#4096ff}
.btn-default{background:#fff;color:#333;border:1px solid #d9d9d9}
.btn-default:hover{border-color:#1677ff;color:#1677ff}
.btn-sm{padding:6px 12px;font-size:13px}
.btn-group{display:flex;gap:10px;margin-top:16px}
.msg-preview{background:#fafafa;border:1px solid #e8e8e8;border-radius:4px;padding:12px 16px;margin-top:12px;font-size:13px;color:#555;line-height:1.8}
.msg-preview .highlight{background:#fff3cd;padding:2px 6px;border-radius:3px;font-weight:500;color:#d48806}
.toast{position:fixed;top:24px;left:50%;transform:translateX(-50%);background:#52c41a;color:#fff;padding:12px 24px;border-radius:4px;font-size:14px;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,.15);animation:fadeIn .3s}
.toast.err{background:#ff4d4f}
@keyframes fadeIn{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
.toggle-switch{position:relative;display:inline-block;width:44px;height:22px}
.toggle-switch input{display:none}
.toggle-slider{position:absolute;inset:0;background:#ccc;border-radius:22px;cursor:pointer;transition:.3s}
.toggle-slider::before{content:"";position:absolute;width:18px;height:18px;left:2px;bottom:2px;background:#fff;border-radius:50%;transition:.3s}
.toggle-switch input:checked+.toggle-slider{background:#1677ff}
.toggle-switch input:checked+.toggle-slider::before{transform:translateX(22px)}
.tip{font-size:12px;color:#999;margin-top:6px;line-height:1.6}
.section-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.empty{text-align:center;color:#bbb;padding:24px;font-size:13px}
.panel{display:none}
.panel.active{display:block}
.info-card{background:#e6f7ff;border:1px solid #91d5ff;border-radius:4px;padding:16px;margin-bottom:20px}
.info-card h3{font-size:15px;color:#096dd9;margin-bottom:10px;font-weight:600}
.info-card ul{font-size:13px;color:#555;line-height:1.9;padding-left:20px}
.info-card ul li{margin-bottom:4px}
.template-item{display:flex;align-items:center;gap:12px;padding:10px 14px;background:#fafafa;border:1px solid #e8e8e8;border-radius:4px;margin-bottom:8px;transition:all .2s}
.template-item:hover{background:#f0f5ff;border-color:#adc6ff}
.template-item .text{flex:1;font-size:14px;line-height:1.6;color:#333}
.template-item .del{width:24px;height:24px;cursor:pointer;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:16px;color:#999;transition:all .2s}
.template-item .del:hover{background:#ff4d4f;color:#fff}
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
        <label class="toggle-switch"><input type="checkbox" id="api-enabled" onchange="toggleApiSection()"><span class="toggle-slider"></span></label>
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

</div>

<script>
// === State ===
let state = {templates:[],searchKeywords:[],requiredKeywords:[],excludedKeywords:[],delivery:{},api:{}};

// === Tab Switch ===
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('panel-'+name).classList.add('active');
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
  document.getElementById('cfg-mode').value=d.mode||'smart';
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

// === Save Functions ===
async function saveTemplates(){
  try{
    let r=await fetch('/api/templates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({templates:state.templates})});
    if(r.ok)toast('消息模板已保存！');
  }catch(e){toast('保存失败: '+e.message,true)}
}

async function saveDeliveryConfig(){
  let d={
    mode:document.getElementById('cfg-mode').value,
    max_per_day:parseInt(document.getElementById('cfg-max-day').value),
    max_per_hour:parseInt(document.getElementById('cfg-max-hour').value),
    auto_send_greeting:document.getElementById('cfg-auto-greet').checked,
    greeting_template:state.templates[0]||'您好，我对贵公司的{position}职位很感兴趣。'
  };
  let ac={min_delay:parseInt(document.getElementById('cfg-min-delay').value),max_delay:8,random_scroll:true,mouse_simulation:true,max_retry:3};
  try{
    let r=await fetch('/api/delivery',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delivery:d,anti_crawler:ac})});
    if(r.ok)toast('投递设置已保存！');
  }catch(e){toast('保存失败: '+e.message,true)}
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
    max_tokens:parseInt(document.getElementById('api-max-tokens').value)
  };
  try{
    let r=await fetch('/api/config/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)});
    if(r.ok)toast('API配置已保存！');
    updateApiBadge();
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

function toggleApiSection(){
  let en=document.getElementById('api-enabled').checked;
  document.getElementById('api-section').style.opacity=en?'1':'0.4';
  document.getElementById('api-section').style.pointerEvents=en?'auto':'none';
  updateApiBadge();
}

function onProviderChange(){
  let p=document.getElementById('api-provider').value;
  if(p==='openai')document.getElementById('api-base').value='https://api.openai.com/v1';
}

function startDelivery(){
  let kw=state.searchKeywords.length?state.searchKeywords.join(','):'未设置关键词';
  if(!confirm('即将启动自动投递脚本\\n当前搜索关键词: '+kw+'\\n\\n确定要启动吗？'))return;
  fetch('/api/start',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.ok)toast('✅ 投递脚本已在后台启动！');
    else toast('❌ 启动失败: '+d.error,true);
  }).catch(e=>toast('启动失败: '+e.message,true));
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

            elif self.path == "/api/start":
                import subprocess
                script = os.path.join(PROJECT_ROOT, "run.py")
                subprocess.Popen([sys.executable, script], cwd=PROJECT_ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
                self._send(200, json.dumps({"ok": True}))

            else:
                self._send(404, json.dumps({"error": "not found"}))

        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n  ⚡ BOSS自动投递 - 配置管理页面")
    print(f"  ┌─────────────────────────────────┐")
    print(f"  │  地址: http://127.0.0.1:{PORT}     │")
    print(f"  │  按 Ctrl+C 停止服务             │")
    print(f"  └─────────────────────────────────┘\n")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务已停止。")
        server.shutdown()


if __name__ == "__main__":
    main()
