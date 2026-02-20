const BASE_API_URL = API_CONFIG.BASE_URL;
const TOKEN_STORAGE_KEY = "access_token";


function setupLoginButton(button) {
    const initialText = button.textContent || 'Login';
    button.setAttribute('data-label', initialText);
    button.setAttribute('aria-live', 'polite');

    const spinner = document.createElement('span');
    spinner.className = 'btn__spinner hidden';
    spinner.setAttribute('aria-hidden', 'true');

    const label = document.createElement('span');
    label.className = 'btn__label';
    label.textContent = initialText;

    button.textContent = '';
    button.appendChild(spinner);
    button.appendChild(label);
}

function setButtonLoading(button, isLoading) {
    const spinner = button.querySelector('.btn__spinner');
    const label = button.querySelector('.btn__label');

    button.disabled = isLoading;
    button.classList.toggle('btn--loading', isLoading);
    button.setAttribute('aria-busy', isLoading ? 'true' : 'false');

    if (spinner) {
        spinner.classList.toggle('hidden', !isLoading);
    }
    if (label) {
        label.textContent = isLoading ? 'Logging in...' : (button.getAttribute('data-label') || 'Login');
    }
}


async function submitLogin(organization_name, user_id, password) {
    const response = await fetch(`${BASE_API_URL}/api/auth/org-login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ organization_name, user_id, password })
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result?.access_token) {
        const message = result?.detail || result?.message || 'Login failed. Please check your credentials.';
        throw new Error(message);
    }

    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
    localStorage.setItem('organization_name', organization_name);
    localStorage.setItem('user_id', user_id);
}

document.addEventListener('DOMContentLoaded', () => {
    const existingToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (existingToken) {
        window.location.href = 'index.html';
        return;
    }

    const form = document.getElementById('loginForm');
    const button = document.getElementById('loginButton');

    if (!form || !button) return;

    setupLoginButton(button);

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const organization_name = document.getElementById('organizationName')?.value?.trim() || '';
        const user_id = document.getElementById('userId')?.value?.trim() || '';
        const password = document.getElementById('password')?.value || '';

        if (!organization_name || !user_id || !password) {
            showToast('error', 'Organization Name, Email, and Password are required.');
            return;
        }

        setButtonLoading(button, true);

        try {
            await submitLogin(organization_name, user_id, password);
            window.location.href = 'index.html';
        } catch (error) {
            console.error('Login error:', error);
            showToast('error', error.message || 'Unable to login. Please try again.');
        } finally {
            setButtonLoading(button, false);
        }
    });
});
