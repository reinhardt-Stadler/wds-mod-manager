@echo off
chcp 65001 >nul 2>&1
title WDS 图包管理器 - 安装

echo.
echo  ═══════════════════════════════════════════
echo    WDS 图包管理器 - 一键安装
echo  ═══════════════════════════════════════════
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.10+ 并加入 PATH。
    echo  下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 显示 Python 版本
echo  [1/3] 检测 Python 环境...
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        %%v
echo.

:: 安装
echo  [2/3] 正在安装 wds-mod-manager ...
echo.
pip install "%~dp0wds-mod-manager" --quiet
if %errorlevel% neq 0 (
    echo.
    echo  [错误] 安装失败，请检查网络连接或尝试:
    echo         pip install "%~dp0wds-mod-manager"
    echo.
    pause
    exit /b 1
)

:: 验证
echo.
echo  [3/3] 验证安装...
where wds >nul 2>&1
if %errorlevel% neq 0 (
    echo  [警告] wds 命令未在 PATH 中找到。
    echo         可能需要重新打开终端，或手动将 Python Scripts 目录加入 PATH。
) else (
    echo        wds 命令已就绪。
)

echo.
echo  ═══════════════════════════════════════════
echo    安装完成！在任意终端输入 wds 即可启动。
echo    输入 wds -help 查看完整使用说明。
echo  ═══════════════════════════════════════════
echo.
pause
