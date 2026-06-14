/**
 * 玄照 v2.0 - API 封装
 * Enhanced error handling with user-friendly messages
 */
const API_BASE = '';
const TIMEOUT_MS = 60000; // Increased to 60s for complex computations

/**
 * Human-readable error messages for common HTTP status codes
 */
const ERROR_MESSAGES = {
    400: '请求参数有误，请检查输入信息',
    404: '请求的资源不存在，服务可能正在更新',
    408: '请求超时，服务器计算量较大，请稍后重试',
    422: '输入数据格式不正确，请检查出生时间等信息',
    429: '请求过于频繁，请稍候再试',
    500: '服务器内部错误，排盘引擎处理异常',
    502: '服务暂时不可用，请稍后重试',
    503: '服务正在启动或维护中，请稍后重试',
    504: '服务器响应超时，计算任务较重',
};

/**
 * Network error messages
 */
const NETWORK_ERRORS = {
    'Failed to fetch': '无法连接服务器，请检查网络连接或确认服务已启动',
    'NetworkError': '网络错误，请检查网络连接',
    'NetworkError when attempting to fetch resource': '网络连接失败，请确认服务运行中',
    'Load failed': '无法加载数据，请检查网络连接',
    'The operation was aborted': '请求被取消，可能是网络不稳定',
    'The user aborted a request': '请求已取消',
};

// Retry logic for resilience
async function fetchWithRetry(url, options = {}, maxRetries = 2, timeout = TIMEOUT_MS) {
    let lastError;
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fetchWithTimeout(url, options, timeout);
        } catch (err) {
            lastError = err;
            if (i < maxRetries - 1) {
                await new Promise(r => setTimeout(r, 1000 * (i + 1)));
            }
        }
    }
    throw lastError;
}

function fetchWithTimeout(url, options = {}, timeout = TIMEOUT_MS) {
    return new Promise((resolve, reject) => {
        const controller = new AbortController();
        const timer = setTimeout(() => {
            controller.abort();
            reject(new Error('请求超时（' + Math.round(timeout/1000) + '秒），服务器计算量较大，请稍后重试'));
        }, timeout);
        fetch(url, { ...options, signal: controller.signal })
            .then(res => {
                clearTimeout(timer);
                resolve(res);
            })
            .catch(err => {
                clearTimeout(timer);
                if (err.name === 'AbortError') {
                    reject(new Error('请求超时（' + Math.round(timeout/1000) + '秒），服务器计算量较大，请稍后重试'));
                } else {
                    // Translate network errors to user-friendly messages
                    const friendlyMsg = NETWORK_ERRORS[err.message] || NETWORK_ERRORS[err.name];
                    if (friendlyMsg) {
                        reject(new Error(friendlyMsg));
                    } else {
                        reject(err);
                    }
                }
            });
    });
}

/**
 * Parse error response and return user-friendly message
 */
async function parseErrorResponse(res) {
    let detail = '';
    let body = null;
    try {
        body = await res.json();
        detail = body.error || body.detail || body.message || '';
    } catch {
        try {
            detail = await res.text();
        } catch {
            detail = '';
        }
    }
    const statusMsg = ERROR_MESSAGES[res.status] || '请求失败';
    const msg = detail ? `${statusMsg}（${detail}）` : statusMsg;
    const err = new Error(msg);
    err.data = body || {};
    err.status = res.status;
    return err;
}

/**
 * 统一请求方法：自动处理超时+错误
 */
async function _fetch(url, timeout) {
    const res = await fetchWithTimeout(url, {}, timeout);
    if (!res.ok) throw await parseErrorResponse(res);
    return res.json();
}

const api = {
    healthCheck: () => _fetch(`${API_BASE}/api/health`, 5000),

    getChart(birth, location, gender, name = '') {
        if (!birth) throw new Error('请输入出生时间');
        const p = new URLSearchParams({ birth, location, gender });
        if (name) p.append('name', name);
        return _fetch(`${API_BASE}/api/chart?${p}`);
    },

    crossValidate(birth, location, gender) {
        if (!birth) throw new Error('请输入出生时间');
        return _fetch(`${API_BASE}/api/cross-validate?${new URLSearchParams({ birth, location, gender })}`);
    },

    getDebate(birth, location, gender, question, figures) {
        if (!birth) throw new Error('请输入出生时间');
        if (!question) throw new Error('请输入要问的问题');
        const p = new URLSearchParams({ birth, location, gender, question });
        if (figures) p.append('figures', figures);
        return _fetch(`${API_BASE}/api/debate?${p}`, 120000);
    },

    ask(birth, location, gender, question) {
        if (!birth) throw new Error('请输入出生时间');
        if (!question) throw new Error('请输入问题');
        return _fetch(`${API_BASE}/api/ask?${new URLSearchParams({ birth, location, gender, question })}`, 90000);
    },

    getFigures: () => _fetch(`${API_BASE}/api/figures`),

    getXuanzhao(birth, location, gender, question, figures) {
        if (!birth) throw new Error('请输入出生时间');
        if (!question) throw new Error('请输入问题');
        const p = new URLSearchParams({ birth, location, gender, question });
        if (figures) p.append('figures', figures);
        return _fetch(`${API_BASE}/api/xuanzhao?${p}`, 120000);
    },
};
