/**
 * 玄照 v2.0 - API 封装
 */
const API_BASE = '';

const api = {
    async getChart(birth, location, gender) {
        const params = new URLSearchParams({ birth, location, gender });
        const res = await fetch(`${API_BASE}/api/chart?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async crossValidate(birth, location, gender) {
        const params = new URLSearchParams({ birth, location, gender });
        const res = await fetch(`${API_BASE}/api/cross-validate?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getDebate(birth, location, gender, question, figures) {
        const params = new URLSearchParams({ birth, location, gender, question });
        if (figures) params.append('figures', figures);
        const res = await fetch(`${API_BASE}/api/debate?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async ask(birth, location, gender, question) {
        const params = new URLSearchParams({ birth, location, gender, question });
        const res = await fetch(`${API_BASE}/api/ask?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getFigures() {
        const res = await fetch(`${API_BASE}/api/figures`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }
};
