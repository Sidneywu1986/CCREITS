import uvicorn
# 新架构入口: admin.app (原 admin_app 为兼容层)
uvicorn.run('admin.app:app', host='0.0.0.0', port=5078, reload=False)
