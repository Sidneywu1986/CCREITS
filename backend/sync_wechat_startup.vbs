' 开机自动同步 wemprss 文章到本地 reits.db（基于 API 版本）
' 静默运行，不显示命令行窗口
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python ""D:\tools\消费看板5（前端）\backend\sync_from_wemprss_api.py""", 0, False
Set WshShell = Nothing
