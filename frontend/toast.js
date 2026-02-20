(function () {
    function getToastContainer() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    function showToast(type, message, timeoutMs) {
        const container = getToastContainer();
        const toast = document.createElement('div');
        const variant = type === 'error' ? 'toast--error' : 'toast--success';
        toast.className = `alert ${type === 'error' ? 'alert--error' : 'alert--info'} ${variant} toast-message`;
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        toast.innerHTML = `<p>${message}</p>`;

        container.appendChild(toast);

        const dismissAfter = typeof timeoutMs === 'number' ? timeoutMs : 4000;
        setTimeout(() => {
            toast.remove();
            if (!container.children.length) {
                container.remove();
            }
        }, dismissAfter);
    }

    window.showToast = showToast;
    window.showSuccessMessage = function (message) {
        showToast('success', message);
    };
    window.showErrorMessage = function (message) {
        showToast('error', message);
    };
})();
