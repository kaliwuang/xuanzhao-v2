/**
 * 玄照 v2.0 - API 封装
 */
const API_BASE = '';
const TIMEOUT_MS = 30000;

function fetchWithTimeout(url, options = {}, timeout = TIMEOUT_MS) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('请求超时，请检查网络连接')), timeout);
        fetch(url, options)
            .then(res => {
                clearTimeout(timer);
                resolve(res);
            })
            .catch(err => {
                clearTimeout(timer);
                reject(err);
            });
    });
}

const api = {
    async getChart(birth, location, gender) {
        const params = new URLSearchParams({ birth, location, gender });
        const res = await fetchWithTimeout(`${API_BASE}/api/chart?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        return res.json();
    },

    async crossValidate(birth, location, gender) {
        const params = new URLSearchParams({ birth, location, gender });
        const res = await fetchWithTimeout(`${API_BASE}/api/cross-validate?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        return res.json();
    },

    async getDebate(birth, location, gender, question, figures) {
        const params = new URLSearchParams({ birth, location, gender, question });
        if (figures) params.append('figures', figures);
        const res = await fetchWithTimeout(`${API_BASE}/api/debate?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        return res.json();
    },

    async ask(birth, location, gender, question) {
        const params = new URLSearchParams({ birth, location, gender, question });
        const res = await fetchWithTimeout(`${API_BASE}/api/ask?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        return res.json();
    },

    async getFigures() {
        const res = await fetchWithTimeout(`${API_BASE}/api/figures`);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        return res.json();
    }
};
