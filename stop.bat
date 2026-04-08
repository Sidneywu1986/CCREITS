@echo off
title REITs数据平台 - 停止服务

echo 正在停止服务...
taskkill /F /IM node.exe 2>nul
echo 服务已停止
pause
