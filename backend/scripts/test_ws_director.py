import sys, os
os.environ['DEEPSEEK_API_KEY'] = 'sk-f5dcc16439f144f9abf5d1af7f992a39'
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api_adapter import adapter_app

client = TestClient(adapter_app)

with client.websocket_connect('/ws/chat') as ws:
    ws.send_json({'action': 'chat', 'message': '仓储物流板块大涨怎么看', 'persona': 'lao_k'})
    msgs = []
    for _ in range(30):
        try:
            m = ws.receive_json(timeout=2)
            msgs.append(m['type'])
            if m['type'] == 'message_end':
                print('[END] %s: %s...' % (m.get('persona'), m.get('content', '')[:100]))
            elif m['type'] == 'director_beat':
                print('[DIRECTOR] %s -> %s' % (m.get('speaker_cn'), m.get('beat_type')))
        except:
            break
    print('All types:', msgs)
