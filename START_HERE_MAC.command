#!/bin/sh
set -u

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ContextLens] 未找到 Python 3。请先安装 Python 3.10 或更高版本。"
  echo "下载地址：https://www.python.org/downloads/"
  printf "按回车键关闭窗口..."
  read -r _answer
  exit 1
fi

./start-contextlens
status=$?
if [ "$status" -ne 0 ]; then
  echo
  echo "ContextLens 启动失败。请将本窗口内容发给项目作者。"
  printf "按回车键关闭窗口..."
  read -r _answer
fi
exit "$status"
