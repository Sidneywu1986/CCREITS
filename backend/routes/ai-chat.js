/**
 * AI聊REIT - WebSocket和API路由
 * 实现AI聊天室、用户行为统计、热点话题管理
 */

const express = require('express');
const router = express.Router();
const { db } = require('../database/db');
const WebSocket = require('ws');

// ==================== 用户行为统计 ====================

// 记录用户行为
router.post('/analytics', (req, res) => {
    const { session_id, page_path, event_type, event_data, referrer, duration_ms } = req.body;
    const ip_address = req.ip || req.connection.remoteAddress;
    const user_agent = req.headers['user-agent'];
    
    const sql = `
        INSERT INTO user_analytics (session_id, page_path, event_type, event_data, user_agent, ip_address, referrer, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `;
    
    db.run(sql, [session_id, page_path, event_type, JSON.stringify(event_data), user_agent, ip_address, referrer, duration_ms], function(err) {
        if (err) {
            console.error('记录用户行为失败:', err);
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, id: this.lastID });
    });
});

// 获取统计数据
router.get('/analytics/summary', (req, res) => {
    const sql = `
        SELECT 
            COUNT(DISTINCT session_id) as uv,
            COUNT(*) as pv,
            page_path,
            DATE(created_at) as date
        FROM user_analytics
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY page_path, DATE(created_at)
        ORDER BY date DESC, pv DESC
    `;
    
    db.all(sql, [], (err, rows) => {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, data: rows });
    });
});

// ==================== AI角色管理 ====================

// 获取所有AI角色
router.get('/personas', (req, res) => {
    db.all('SELECT * FROM ai_personas WHERE is_active = 1', [], (err, rows) => {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, data: rows });
    });
});

// ==================== 热点话题管理 ====================

// 获取热点话题
router.get('/hot-topics', (req, res) => {
    const sql = `
        SELECT * FROM hot_topics 
        WHERE created_at >= datetime('now', '-24 hours')
        ORDER BY heat_score DESC 
        LIMIT 10
    `;
    
    db.all(sql, [], (err, rows) => {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, data: rows });
    });
});

// 添加热点话题
router.post('/hot-topics', (req, res) => {
    const { topic, category, heat_score, related_funds, source_urls } = req.body;
    
    const sql = `
        INSERT INTO hot_topics (topic, category, heat_score, related_funds, source_urls)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(topic) DO UPDATE SET
            heat_score = MAX(heat_score, excluded.heat_score),
            updated_at = CURRENT_TIMESTAMP
    `;
    
    db.run(sql, [topic, category, heat_score, JSON.stringify(related_funds), JSON.stringify(source_urls)], function(err) {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, id: this.lastID });
    });
});

// ==================== 聊天室管理 ====================

// 获取聊天室列表
router.get('/rooms', (req, res) => {
    db.all('SELECT * FROM ai_chat_rooms WHERE status = "active"', [], (err, rows) => {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, data: rows });
    });
});

// 获取聊天记录
router.get('/rooms/:roomId/messages', (req, res) => {
    const { roomId } = req.params;
    const { limit = 50, offset = 0 } = req.query;
    
    const sql = `
        SELECT * FROM ai_chat_messages 
        WHERE room_id = ? 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    `;
    
    db.all(sql, [roomId, parseInt(limit), parseInt(offset)], (err, rows) => {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        res.json({ success: true, data: rows.reverse() });
    });
});

// 发送消息（REST API备用）
router.post('/rooms/:roomId/messages', (req, res) => {
    const { roomId } = req.params;
    const { sender_type, sender_id, sender_name, message, message_type, reply_to } = req.body;
    
    const sql = `
        INSERT INTO ai_chat_messages 
        (room_id, sender_type, sender_id, sender_name, message, message_type, reply_to)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    db.run(sql, [roomId, sender_type, sender_id, sender_name, message, message_type, reply_to], function(err) {
        if (err) {
            return res.status(500).json({ success: false, error: err.message });
        }
        
        // 更新房间消息数
        db.run('UPDATE ai_chat_rooms SET message_count = message_count + 1 WHERE id = ?', [roomId]);
        
        res.json({ success: true, id: this.lastID });
    });
});

// ==================== AI聊天核心逻辑 ====================

// AI对话生成
async function generateAIResponse(persona, context, lastMessages) {
    // 这里可以集成OpenAI API或其他AI服务
    // 目前使用预设回复模拟
    
    const responses = {
        '老李': [
            '从宏观角度来看，当前REITs市场正处于结构性调整期。',
            '我认为需要关注政策面的变化，特别是财税支持政策。',
            '数据显示，近期机构资金在持续流入优质资产。',
            '大家要注意风险控制，不要盲目追高。',
            '从估值角度分析，部分板块已经进入合理区间。'
        ],
        '小陈': [
            '老李说得对！但是我个人觉得短线还有机会。',
            '刚才看了一下资金流向，发现有个有趣的现象...',
            '有人关注过基础设施REITs的折价率吗？',
            '我觉得可以适当布局一些高分红的品种。',
            '市场情绪最近确实在回暖，大家怎么看？'
        ],
        '王博士': [
            '从学术研究的角度，我想补充一些数据支撑。',
            '根据我的模型测算，当前估值水平处于历史...',
            '底层资产的质量是决定REITs长期价值的关键。',
            '我想分享一个有趣的案例分析...',
            '财务报表显示，部分REITs的运营效率在提升。'
        ]
    };
    
    const personaResponses = responses[persona.name] || responses['老李'];
    return personaResponses[Math.floor(Math.random() * personaResponses.length)];
}

// ==================== WebSocket处理 ====================

let wss = null;
const clients = new Map();

// 初始化WebSocket服务器
function initWebSocket(server) {
    wss = new WebSocket.Server({ server, path: '/ws/ai-chat' });
    
    wss.on('connection', (ws, req) => {
        const clientId = Date.now().toString();
        const sessionId = req.url.split('sessionId=')[1] || clientId;
        
        clients.set(clientId, {
            ws,
            sessionId,
            roomId: 1,
            joinedAt: new Date()
        });
        
        console.log(`AI聊天室: 新用户连接 ${clientId}, 当前在线: ${clients.size}`);
        
        // 发送欢迎消息
        ws.send(JSON.stringify({
            type: 'system',
            content: '欢迎来到REITs AI投资交流群！',
            timestamp: new Date().toISOString()
        }));
        
        // 更新房间人数
        updateRoomParticipantCount(1);
        
        ws.on('message', async (data) => {
            try {
                const message = JSON.parse(data);
                await handleWebSocketMessage(clientId, message);
            } catch (err) {
                console.error('WebSocket消息处理错误:', err);
            }
        });
        
        ws.on('close', () => {
            clients.delete(clientId);
            updateRoomParticipantCount(1);
            console.log(`AI聊天室: 用户断开 ${clientId}, 当前在线: ${clients.size}`);
        });
    });
    
    // 启动AI自动对话
    startAIAutoChat();
}

// 处理WebSocket消息
async function handleWebSocketMessage(clientId, message) {
    const client = clients.get(clientId);
    if (!client) return;
    
    switch (message.type) {
        case 'chat':
            // 保存用户消息
            await saveChatMessage(client.roomId, 'human', clientId, '用户', message.content);
            
            // 广播给用户
            broadcastToRoom(client.roomId, {
                type: 'chat',
                sender: '用户',
                senderType: 'human',
                content: message.content,
                timestamp: new Date().toISOString()
            });
            
            // 触发AI回复
            if (message.content.includes('@')) {
                await triggerAIResponse(client.roomId, message.content);
            }
            break;
            
        case 'join':
            client.roomId = message.roomId;
            break;
            
        case 'typing':
            broadcastToRoom(client.roomId, {
                type: 'typing',
                sender: message.sender,
                timestamp: new Date().toISOString()
            }, clientId);
            break;
    }
}

// 保存聊天消息到数据库
function saveChatMessage(roomId, senderType, senderId, senderName, message, messageType = 'text') {
    return new Promise((resolve, reject) => {
        const sql = `
            INSERT INTO ai_chat_messages 
            (room_id, sender_type, sender_id, sender_name, message, message_type)
            VALUES (?, ?, ?, ?, ?, ?)
        `;
        
        db.run(sql, [roomId, senderType, senderId, senderName, message, messageType], function(err) {
            if (err) {
                console.error('保存聊天消息失败:', err);
                reject(err);
            } else {
                resolve(this.lastID);
            }
        });
    });
}

// 广播消息到房间
function broadcastToRoom(roomId, message, excludeClientId = null) {
    clients.forEach((client, clientId) => {
        if (client.roomId === roomId && clientId !== excludeClientId) {
            if (client.ws.readyState === WebSocket.OPEN) {
                client.ws.send(JSON.stringify(message));
            }
        }
    });
}

// 更新房间在线人数
function updateRoomParticipantCount(roomId) {
    const count = Array.from(clients.values()).filter(c => c.roomId === roomId).length;
    broadcastToRoom(roomId, {
        type: 'participant_count',
        count: count + 3 // +3 for AI bots
    });
}

// 启动AI自动对话
function startAIAutoChat() {
    const AI_PERSONAS = [
        { id: 'laoli', name: '老李', expertise: ['宏观经济', '政策解读'] },
        { id: 'xiaochen', name: '小陈', expertise: ['技术分析', '短线操作'] },
        { id: 'wang', name: '王博士', expertise: ['资产评估', '长期价值'] }
    ];
    
    // 每20-40秒随机触发一次AI对话
    setInterval(async () => {
        const roomId = 1;
        const ai = AI_PERSONAS[Math.floor(Math.random() * AI_PERSONAS.length)];
        
        // 获取最近的消息作为上下文
        const recentMessages = await getRecentMessages(roomId, 5);
        const context = recentMessages.map(m => m.message).join(' | ');
        
        // 生成AI回复
        const response = await generateAIResponse(ai, context, recentMessages);
        
        // 保存到数据库
        await saveChatMessage(roomId, 'ai', ai.id, ai.name, response);
        
        // 广播
        broadcastToRoom(roomId, {
            type: 'chat',
            sender: ai.name,
            senderType: 'ai',
            senderId: ai.id,
            content: response,
            timestamp: new Date().toISOString()
        });
    }, 20000 + Math.random() * 20000);
}

// 获取最近消息
function getRecentMessages(roomId, limit = 5) {
    return new Promise((resolve, reject) => {
        db.all(
            'SELECT * FROM ai_chat_messages WHERE room_id = ? ORDER BY created_at DESC LIMIT ?',
            [roomId, limit],
            (err, rows) => {
                if (err) reject(err);
                else resolve(rows.reverse());
            }
        );
    });
}

// 触发AI回复
async function triggerAIResponse(roomId, userMessage) {
    const AI_PERSONAS = [
        { id: 'laoli', name: '老李', expertise: ['宏观经济', '政策解读'] },
        { id: 'xiaochen', name: '小陈', expertise: ['技术分析', '短线操作'] },
        { id: 'wang', name: '王博士', expertise: ['资产评估', '长期价值'] }
    ];
    
    // 检查@了哪位AI
    const mentionedAI = AI_PERSONAS.find(ai => userMessage.includes('@' + ai.name));
    
    if (mentionedAI) {
        setTimeout(async () => {
            const response = await generateAIResponse(mentionedAI, userMessage, []);
            
            await saveChatMessage(roomId, 'ai', mentionedAI.id, mentionedAI.name, response);
            
            broadcastToRoom(roomId, {
                type: 'chat',
                sender: mentionedAI.name,
                senderType: 'ai',
                senderId: mentionedAI.id,
                content: response,
                timestamp: new Date().toISOString()
            });
        }, 1000);
    }
}

module.exports = { router, initWebSocket };
