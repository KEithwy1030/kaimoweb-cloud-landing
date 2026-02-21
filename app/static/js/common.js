/**
 * ============================================
 * VPN Distribution System - Common JavaScript
 * ============================================
 */

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    initMobileMenu();
    initSidebar();
});

/**
 * Mobile Menu Toggle
 */
function initMobileMenu() {
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            if (overlay) {
                overlay.classList.toggle('active');
            }
        });

        if (overlay) {
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
            });
        }
    }
}

/**
 * Initialize Sidebar Navigation
 */
function initSidebar() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
            item.classList.add('active');
        }
    });
}

/**
 * Show/Hide Password Toggle
 */
function togglePassword(inputId, iconElement) {
    const input = document.getElementById(inputId);
    if (input) {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        if (iconElement) {
            iconElement.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
        }
    }
}

/**
 * Copy to Clipboard
 */
async function copyToClipboard(text, successMessage = '复制成功！') {
    try {
        await navigator.clipboard.writeText(text);
        Toast.success(successMessage);
    } catch (err) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            Toast.success(successMessage);
        } catch (e) {
            Toast.error('复制失败，请手动复制');
        }
        document.body.removeChild(textarea);
    }
}

/**
 * Format bytes to human readable
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Confirm dialog
 */
function confirmDialog(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Refresh subscription
 */
async function refreshSubscription() {
    const btn = document.querySelector('.refresh-subscription-btn');
    Loading.show(btn);

    try {
        const result = await API.dashboard.getData();
        Loading.hide(btn);

        if (result.code === 0) {
            Toast.success('订阅刷新成功！');
            setTimeout(() => location.reload(), 1000);
        } else {
            Toast.error(result.message || '刷新失败');
        }
    } catch (error) {
        Loading.hide(btn);
        Toast.error('网络请求失败');
    }
}

/**
 * Show QR Code for subscription
 */
function showSubscriptionQR() {
    API.subscriptions.getLink().then(result => {
        if (result.code === 0) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content">
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                    <h3>订阅二维码</h3>
                    <div class="qr-code-container">
                        <img src="${result.data.qr_code}" alt="订阅二维码">
                    </div>
                    <p class="subscription-link">${result.data.subscription_url}</p>
                    <button class="btn btn-primary" onclick="copyToClipboard('${result.data.subscription_url}')">
                        <i class="fas fa-copy"></i> 复制订阅链接
                    </button>
                </div>
            `;
            document.body.appendChild(modal);
        } else {
            Toast.error(result.message || '获取订阅链接失败');
        }
    });
}

/**
 * Logout
 */
function logout() {
    if (confirm('确定要退出登录吗？')) {
        API.auth.logout();
    }
}
