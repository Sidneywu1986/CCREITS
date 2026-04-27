import os
os.environ['PORT'] = '5076'
import uvicorn
uvicorn.run('api_adapter:adapter_app', host='0.0.0.0', port=5076, reload=False)
