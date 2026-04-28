/**
 * PostgreSQL advisory lock 封装 - Node.js 版
 * 用于调度器任务互斥
 */
const crypto = require('crypto');
const { pool } = require('./db');

function hashTaskName(name) {
    const hash = crypto.createHash('md5').update(name).digest('hex');
    return parseInt(hash.slice(0, 8), 16);
}

/**
 * 获取任务锁
 * @param {string} taskName - 任务名称
 * @returns {Promise<{client, key}>}
 */
async function acquireLock(taskName) {
    const key = hashTaskName(taskName);
    const client = await pool.connect();
    try {
        await client.query('SELECT pg_advisory_lock($1)', [key]);
        return { client, key, taskName };
    } catch (e) {
        client.release();
        throw e;
    }
}

/**
 * 释放任务锁
 * @param {{client, key, taskName}} lock - acquireLock 返回的对象
 */
async function releaseLock(lock) {
    try {
        await lock.client.query('SELECT pg_advisory_unlock($1)', [lock.key]);
    } finally {
        lock.client.release();
    }
}

/**
 * 带锁执行任务
 * @param {string} taskName - 任务名称
 * @param {Function} taskFn - 任务函数
 */
async function withLock(taskName, taskFn) {
    const lock = await acquireLock(taskName);
    try {
        return await taskFn();
    } finally {
        await releaseLock(lock);
    }
}

module.exports = { acquireLock, releaseLock, withLock };
