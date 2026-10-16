@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if errorlevel 1 (
    echo 错误: 无法进入项目目录。
    pause
    exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
    echo 错误: 未找到 uv。请按 README.md 安装 uv 后重试。
    pause
    exit /b 1
)

uv run --locked python main.py %*
set "run_exit_code=%errorlevel%"
pause
exit /b %run_exit_code%
