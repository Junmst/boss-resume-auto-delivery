# 长期记忆

## 项目信息
- 项目名称：BOSS 简历自动投递工具
- 工作目录：`D:\apps\boss简历自动投递`
- GitHub 仓库：`https://github.com/Junmst/boss-resume-auto-delivery`
- 用户 GitHub 地址：`https://github.com/dashboard`

## 技术栈与架构
- Python 3，Selenium Edge WebDriver，原生 HTML/JS 配置页面（`gui.py`）
- 配置页 HTTP 端口：8520
- 配置页使用系统浏览器打开，避免占用 Selenium 用户数据目录
- 投递浏览器使用独立 `edge_delivery_data` 目录

## 重要修复记录
- AI 智能消息生成开关曾因 `pointerEvents: none` 导致保存按钮无法点击，已修复为 toggle 自动保存。
- 投递流程浏览器创建失败的根因尚未完全解决，曾因 Edge 首次启动页覆盖 BOSS 导航和会话创建失败。

## 功能特性
- AI 智能岗位匹配：`src/ai_matcher.py` 根据简历和标签给岗位打分并排序。
- 投递消息可基于 AI 生成，失败回退模板。
- 测试模式仅预览岗位不投递。

## 用户偏好
- 用户后续推送到 GitHub 时应使用当前工作目录的源码为准。
- 用户希望 AI 标签搜索满足多标签同时匹配，而不是单个关键词独立搜索。
