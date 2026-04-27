import uvicorn
uvicorn.run('admin_app:app', host='0.0.0.0', port=5078, reload=False)
