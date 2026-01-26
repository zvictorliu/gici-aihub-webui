# 定义变量，方便后续修改
FRONTEND_DIR = frontend
BACKEND_DIR = backend

.PHONY: help install dev-frontend dev-backend dev clean

# 默认显示帮助信息
help:
	@echo "可用指令:"
	@echo "  make install      - 安装前后端所有依赖"
	@echo "  make dev-frontend - 启动前端开发服务器 (npm)"
	@echo "  make dev-backend  - 启动后端开发服务器 (uv)"
	@echo "  make dev          - 同时启动前后端 (并行运行)"
	@echo "  make clean        - 清理缓存和临时文件"

# 1. 安装依赖
install:
	@echo "正在安装前端依赖..."
	cd $(FRONTEND_DIR) && npm install
	@echo "正在安装后端依赖..."
	cd $(BACKEND_DIR) && uv sync

# 2. 启动前端
dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

# 3. 启动后端 (假设入口是 main.py)
dev-backend:
	cd $(BACKEND_DIR) && uv run main.py

# 4. 同时启动 (使用 -j 参数实现并行)
# 注意：这会将两者的日志交替输出到当前终端
dev:
	make -j 2 dev-frontend dev-backend

# 5. 清理环境
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(BACKEND_DIR)/.venv