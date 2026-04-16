/**
 * 简化的分时图实现 - 使用真实关键点位
 */

function renderMinuteChartSimple(chartDom, fundData) {
    const chart = echarts.init(chartDom);
    
    // 获取关键价格
    const open = fundData.open || fundData.price;
    const close = fundData.price;
    const high = fundData.high || Math.max(open, close);
    const low = fundData.low || Math.min(open, close);
    const prevClose = fundData.prev_close || fundData.price * 0.99;
    
    // 获取当前时间
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    
    // 计算当前交易分钟索引（0-239，不含午休）
    let currentTradingIndex = 0;
    const startMinutes = 9 * 60 + 30; // 9:30
    const morningEnd = 11 * 60 + 30;  // 11:30
    const afternoonStart = 13 * 60;   // 13:00
    const currentTotalMinutes = currentHour * 60 + currentMinute;
    
    if (currentHour < 9 || (currentHour === 9 && currentMinute < 30)) {
        currentTradingIndex = 0;
    } else if (currentTotalMinutes <= morningEnd) {
        // 上午：9:30-11:30
        currentTradingIndex = currentTotalMinutes - startMinutes;
    } else if (currentTotalMinutes < afternoonStart) {
        // 午休：11:30-13:00，显示到上午收盘
        currentTradingIndex = 120;
    } else if (currentTotalMinutes < 15 * 60) {
        // 下午：13:00-15:00
        currentTradingIndex = 120 + (currentTotalMinutes - afternoonStart);
    } else {
        // 收盘后，显示完整日线
        currentTradingIndex = 240;
    }
    
    // 生成时间轴（交易时间9:30-11:30, 13:00-15:00）
    const times = [];
    // 上午 9:30-11:30 (120分钟)
    for (let i = 0; i < 120 && i < currentTradingIndex; i++) {
        const totalMinutes = startMinutes + i;
        const hour = Math.floor(totalMinutes / 60);
        const min = totalMinutes % 60;
        times.push(`${hour}:${String(min).padStart(2, '0')}`);
    }
    // 下午 13:00-15:00 (120分钟)
    for (let i = 0; i < 120 && (120 + i) < currentTradingIndex; i++) {
        const totalMinutes = afternoonStart + i;
        const hour = Math.floor(totalMinutes / 60);
        const min = totalMinutes % 60;
        times.push(`${hour}:${String(min).padStart(2, '0')}`);
    }
    
    // 构建价格数据（简化为关键点位）
    const prices = [];
    const totalPoints = times.length;
    
    for (let i = 0; i < totalPoints; i++) {
        const progress = i / (totalPoints - 1 || 1);
        
        // 简单的价格路径：开盘 -> 波动 -> 收盘
        let price;
        if (progress < 0.3) {
            // 开盘阶段
            price = open + (Math.random() - 0.5) * (high - low) * 0.3;
        } else if (progress < 0.7) {
            // 盘中阶段，接近最高或最低
            price = (i % 2 === 0) ? high : low;
            price += (Math.random() - 0.5) * (high - low) * 0.1;
        } else {
            // 收盘阶段
            price = close + (Math.random() - 0.5) * (high - low) * 0.2;
        }
        
        prices.push(parseFloat(price.toFixed(3)));
    }
    
    // 确保起点和终点正确
    if (prices.length > 0) prices[0] = open;
    if (prices.length > 1) prices[prices.length - 1] = close;
    
    const isUp = close >= prevClose;
    const color = isUp ? '#dc2626' : '#16a34a';
    
    chart.setOption({
        grid: { top: 10, right: 10, bottom: 30, left: 50 },
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                const price = params[0].data;
                const change = ((price - prevClose) / prevClose * 100).toFixed(2);
                return `${params[0].axisValue}<br/>价格: ${price}<br/>涨跌: ${change}%`;
            }
        },
        xAxis: {
            type: 'category',
            data: times,
            axisLine: { lineStyle: { color: '#e5e7eb' } },
            axisLabel: { 
                color: '#9ca3af', 
                fontSize: 10, 
                interval: (index, value) => {
                    // 只显示整点和半点: 9:30, 10:00, 10:30, 11:00, 11:30, 13:00, 13:30, 14:00, 14:30, 15:00
                    const showTimes = ['9:30', '10:00', '10:30', '11:00', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00'];
                    return !showTimes.includes(value);
                }
            }
        },
        yAxis: {
            type: 'value',
            min: low * 0.995,
            max: high * 1.005,
            splitLine: { lineStyle: { color: '#f3f4f6' } },
            axisLabel: { 
                color: '#6b7280', 
                fontSize: 10,
                formatter: (val) => val.toFixed(2)
            }
        },
        series: [{
            type: 'line',
            data: prices,
            smooth: true,
            symbol: 'none',
            lineStyle: { color: color, width: 1.5 },
            areaStyle: {
                color: {
                    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: isUp ? 'rgba(220,38,38,0.2)' : 'rgba(22,163,74,0.2)' }, 
                        { offset: 1, color: isUp ? 'rgba(220,38,38,0.02)' : 'rgba(22,163,74,0.02)' }
                    ]
                }
            },
            markLine: {
                silent: true,
                data: [{
                    yAxis: prevClose,
                    lineStyle: { color: '#999', type: 'dashed', width: 1 },
                    label: { formatter: '昨收', fontSize: 10, color: '#999' }
                }]
            }
        }]
    });
    
    return chart;
}
