# aihub-web-vue

GICI 助手 - GNSS/INS 组合导航专家 (Vue 3 + Vite)

面向 GICI-lib 的 AI 知识库

前端基于 Vue3.js+Vite 实现，后端基于 OpenCode 实现

![](./assets/demo.png)

## 部署指南

### 1. 环境准备

- **Node.js**: 建议使用 v20.19.0 或 v22.12.0 及以上版本。
- **Python**: 建议使用 v3.13 或以上版本 (用于后端服务)。
- **包管理器**: 前端推荐使用 `npm` (v10+)，后端推荐使用 `uv`。

### 2. 前端部署 (aihub-web-vue)

#### 配置环境变量
在 `frontend/` 目录下创建 `.env.local` 文件，配置后端服务的访问地址：

| 变量名 | 说明 | 默认值 | 关联后端 |
| :--- | :--- | :--- | :--- |
| `VITE_PORT` | 开发服务器端口 | `5173` | - |
| `VITE_BASE_API_URL` | 后端服务地址 | `http://127.0.0.1:8000` | 统一后端 |

示例 `frontend/.env.local`:
```env
VITE_PORT=5173
VITE_BASE_API_URL=http://localhost:8000
```

#### 安装与运行
```sh
cd frontend

# 安装依赖
npm install

# 本地开发 (带热更新)
npm run dev

# 生产构建
npm run build
```

### 3. OpenCode 部署 (AI 引擎)

OpenCode 服务器负责处理核心 AI 业务逻辑。

```bash
# 确保已安装 opencode 工具
opencode serve --host 127.0.0.1 --port 5000
```
- **注意**: 后端服务将代理对此服务的请求。

### 4. 后端部署 (统一入口)

负责用户管理及 AI 业务代理。

#### 服务配置
在 `backend/` 目录下创建 `.env` 文件：
```env
# ./backend/.env
HOST=127.0.0.1
PORT=8000
DEBUG=True
OPENCODE_URL=http://127.0.0.1:5000
```

- **配置**: 确保前端 `VITE_BASE_API_URL` 指向此服务的地址。
- **功能**: 提供 `/api` 路径下的 AI 能力支持。

### 4. 后端部署 (用户管理/第二后端)

负责用户注册、登录及权限管理。用户信息持久化在 `backend/users.json`。

#### 服务配置
在 `backend/` 目录下创建 `.env` 文件：
```env
# ./backend/.env
HOST=127.0.0.1
PORT=8000
DEBUG=True
```

#### 安装与启动
推荐使用 [uv](https://github.com/astral-sh/uv) 快速启动：
```bash
cd backend
# 使用 uv 直接运行 (会自动创建虚拟环境并安装依赖)
uv run main.py
```
或者使用传统方式：
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install -r pyproject.toml
python main.py
```

## 自定义与复用

本项目支持通过简单的配置快速自定义界面，实现快速复用：

### 1. 统一配置 (UI 与文案)
修改项目根目录下的 `config/appConfig.toml` 文件，即可自定义界面上的所有名称、标题、欢迎语、图标、链接和版权信息。

配置文件结构示例：
```toml
[app]
title = "应用标题"
headerTitle = "页眉标题"
copyright = "版权信息"

[ui]
logoIcon = "fa-solid fa-robot" # FontAwesome 图标
logoColor = "#38BDF8"         # 图标颜色

[assistant]
name = "助手名称"
welcomeMessage = "欢迎语 (支持 Markdown)"
chatInputPlaceholder = "输入框占位符..."

[auth]
loginSubtitle = "登录页副标题"
registerSubtitle = "注册页副标题"

[links]
githubRepo = "GitHub 仓库链接"
helpDocUrl = "帮助文档链接"
```

### 2. 后端逻辑
后端已实现中立化，不包含任何品牌相关的硬编码。它通过 API 接收前端传递的配置（如会话标题），从而保持核心逻辑的纯粹与通用。


---

## 技术架构
- **前端框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **图标库**: Font Awesome 6 (本地化部署)
- **字体**: 本地化部署 (Open Sans & Poppins)

## 项目结构
- `src/components`: UI 组件
- `public/fonts`: 本地化字体资源
- `public/fontawesome`: 本地化 Font Awesome 资源
- `index.html`: 入口 HTML

## 离线支持
本项目所有静态资源（字体、图标等）均已本地化，支持在无外网环境下部署和使用。
