/**
 * ============================================
 * VPN Distribution System - API Wrapper
 * ============================================
 */

const API = {
    baseURL: window.location.origin + '/api',

    /**
     * Get auth token from localStorage
     */
    getToken() {
        return localStorage.getItem('token');
    },

    /**
     * Set auth token to localStorage
     */
    setToken(token) {
        localStorage.setItem('token', token);
    },

    /**
     * Remove auth token from localStorage
     */
    removeToken() {
        localStorage.removeItem('token');
    },

    /**
     * Get user info from localStorage
     */
    getUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    },

    /**
     * Set user info to localStorage
     */
    setUser(user) {
        localStorage.setItem('user', JSON.stringify(user));
    },

    /**
     * Remove user info from localStorage
     */
    removeUser() {
        localStorage.removeItem('user');
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.getToken();
    },

    /**
     * Make API request
     */
    async request(endpoint, options = {}) {
        const url = this.baseURL + endpoint;
        const token = this.getToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            // Handle token expired
            if (data.code === 1005) {
                this.removeToken();
                this.removeUser();
                if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                    window.location.href = '/login';
                }
                return data;
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            return {
                code: 5001,
                message: '网络请求失败，请检查网络连接',
                data: null
            };
        }
    },

    // Auth APIs
    auth: {
        async register(email, password) {
            return API.request('/auth/register', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });
        },

        async login(email, password) {
            const data = await API.request('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });

            if (data.code === 0 && data.data.token) {
                API.setToken(data.data.token);
                API.setUser(data.data);
            }

            return data;
        },

        async logout() {
            API.removeToken();
            API.removeUser();
            window.location.href = '/login';
        },

        async me() {
            return API.request('/auth/me');
        }
    },

    // Plans APIs
    plans: {
        async list() {
            return API.request('/plans');
        },

        async get(id) {
            return API.request(`/plans/${id}`);
        }
    },

    // Orders APIs
    orders: {
        async list() {
            return API.request('/orders');
        },

        async get(id) {
            return API.request(`/orders/${id}`);
        },

        async create(planId) {
            return API.request('/orders', {
                method: 'POST',
                body: JSON.stringify({ plan_id: planId })
            });
        },

        async pay(orderId) {
            return API.request(`/orders/${orderId}/pay`, {
                method: 'POST'
            });
        }
    },

    // Subscriptions APIs
    subscriptions: {
        async list() {
            return API.request('/subscriptions');
        },

        async get(id) {
            return API.request(`/subscriptions/${id}`);
        },

        async getLink() {
            return API.request('/subscriptions/link');
        }
    },

    // Dashboard APIs
    dashboard: {
        async getData() {
            return API.request('/dashboard');
        }
    },

    // Flow/Traffic APIs
    flow: {
        async list() {
            return API.request('/flow');
        }
    },

    // Profile APIs
    profile: {
        async update(data) {
            return API.request('/profile', {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },

        async changePassword(oldPassword, newPassword) {
            return API.request('/profile/change-password', {
                method: 'POST',
                body: JSON.stringify({
                    old_password: oldPassword,
                    new_password: newPassword
                })
            });
        }
    },

    // Payment APIs
    payment: {
        async hupijiaoPay(orderId) {
            return API.request(`/payment/hupijiao-pay/${orderId}`, {
                method: 'POST'
            });
        },
        async getStatus(orderId) {
            return API.request(`/payment/status/${orderId}`);
        }
    }
};

/**
 * Toast Notification Helper
 */
const Toast = {
    show(message, type = 'info') {
        const container = document.querySelector('.toast-container') || this.createContainer();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icons = {
            success: '<i class="fas fa-check-circle" style="color: var(--success-color)"></i>',
            error: '<i class="fas fa-times-circle" style="color: var(--danger-color)"></i>',
            warning: '<i class="fas fa-exclamation-triangle" style="color: var(--warning-color)"></i>',
            info: '<i class="fas fa-info-circle" style="color: var(--info-color)"></i>'
        };

        toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    createContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    },

    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    warning(message) { this.show(message, 'warning'); },
    info(message) { this.show(message, 'info'); }
};

/**
 * Loading Helper
 */
const Loading = {
    show(element) {
        if (element) {
            element.disabled = true;
            element.dataset.originalText = element.innerHTML;
            element.innerHTML = '<span class="spinner"></span> 加载中...';
        }
    },

    hide(element) {
        if (element) {
            element.disabled = false;
            if (element.dataset.originalText) {
                element.innerHTML = element.dataset.originalText;
            }
        }
    }
};

/**
 * Format Helpers
 */
const Format = {
    // Format file size
    fileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Format date
    date(dateString) {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
    },

    // Format currency
    currency(amount) {
        return parseFloat(amount).toFixed(2);
    },

    // Format period text
    period(period) {
        const periods = {
            'onetime': '一次性',
            '1month': '一个月',
            '3month': '三个月',
            '6month': '半年',
            '1year': '一年'
        };
        return periods[period] || period;
    },

    // Format order status
    orderStatus(status) {
        const statuses = {
            'pending': '待支付',
            'paid': '已支付',
            'cancelled': '已取消',
            'completed': '已完成'
        };
        return statuses[status] || status;
    },

    // Get order status badge class
    orderStatusClass(status) {
        const classes = {
            'pending': 'badge-warning',
            'paid': 'badge-info',
            'cancelled': 'badge-secondary',
            'completed': 'badge-success'
        };
        return classes[status] || 'badge-secondary';
    }
};

/**
 * Auth Guard - Protect pages that require authentication
 */
function AuthGuard() {
    if (!API.isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

/**
 * Redirect if already authenticated
 */
function RedirectIfAuthenticated() {
    if (API.isAuthenticated()) {
        window.location.href = '/dashboard';
        return false;
    }
    return true;
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API, Toast, Loading, Format, AuthGuard, RedirectIfAuthenticated };
}
