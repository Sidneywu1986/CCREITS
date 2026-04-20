/**
 * 告警管理器
 */
class AlertManager {
    static stats = { total: 0, last24Hours: 0 };

    static sendAlert(alert) {
        this.stats.total++;
        console.log(`📢 告警: ${alert.message}`);
    }

    static sendFormattedAlert(type, details, severity) {
        console.log(`📢 告警 [${severity}] ${type}:`, details);
    }

    static getStats() {
        return this.stats;
    }

    static cleanup(days) {
        console.log(`🧹 清理${days}天前的告警记录`);
    }
}

module.exports = AlertManager;
