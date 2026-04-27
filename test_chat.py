import sys
sys.path.insert(0, 'D:/tools/消费看板5（前端）/backend')

from fastapi.testclient import TestClient
from api_adapter import adapter_app

client = TestClient(adapter_app)

# Test 1: 老K + 贪婪市场
print("=== Test 1: 老K回答（贪婪市场）===")
resp = client.post("/api/ai/chat-reits", json={
    "message": "仓储物流板块怎么看？最近涨了不少",
    "persona": "lao_k"
})
data = resp.json()
print(f"Status: {resp.status_code}")
print(f"Agent: {data.get('agent_name')}")
print(f"Sources: {data.get('sources', [])}")
content = data.get('content', '')
print(f"Content[:200]: {content[:200]}...")
print()

# Test 2: 苏苏 + 恐慌市场
print("=== Test 2: 苏苏回答（恐慌市场）===")
resp2 = client.post("/api/ai/chat-reits", json={
    "message": "消费REITs大跌，市场恐慌怎么办",
    "persona": "su_su"
})
data2 = resp2.json()
print(f"Status: {resp2.status_code}")
print(f"Agent: {data2.get('agent_name')}")
content2 = data2.get('content', '')
print(f"Content[:200]: {content2[:200]}...")
print()

# Test 3: 人设路由（不指定，关键词匹配）
print("=== Test 3: 自动人设路由 ===")
resp3 = client.post("/api/ai/chat-reits", json={
    "message": "长期持有分红怎么看",
})
data3 = resp3.json()
print(f"Status: {resp3.status_code}")
print(f"Agent: {data3.get('agent_name')}")
print(f"Sources: {data3.get('sources', [])}")
content3 = data3.get('content', '')
print(f"Content[:200]: {content3[:200]}...")
print()

# Test 4: Stats API
print("=== Test 4: 知识库统计 ===")
resp4 = client.get("/api/v1/search/stats")
print(f"Stats: {resp4.json()}")
