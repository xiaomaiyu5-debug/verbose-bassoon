# 舆情分析 PoC

一个轻量级的中文舆情分析演示项目（Flask），包含关键词检索、基础分析与自动生成 HTML 报告。

## 主要功能
- 首页提交关键词与时间窗，异步生成报告
- 后台搜索与抓取（受站点限制时自动降级为 DEMO 数据）
- 报告包含趋势、渠道分布、关键词与聚类、核心洞察等

## 快速开始
1. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. 启动开发服务器：
   ```bash
   PORT=5050 python app.py
   ```
3. 打开浏览器访问：http://127.0.0.1:5050/

## 项目结构
- `app.py`：Flask 路由与异步任务
- `src/`：核心逻辑（agents、services、pipeline）
- `templates/`：页面模板（首页、报告、任务页）
- `static/`：样式文件
- `reports/`：报告输出目录（HTML/MD），运行时自动生成

## 备注
- 项目处于 PoC 阶段，外部站点反爬严格时会使用 DEMO 数据生成报告，确保页面体验。
- 如需进一步增强站点定制抓取（知乎/B站/贴吧等），可在 `src/services/fetchers.py` 与相关 agents 中扩展。

## 许可
仅用于演示与学习目的。