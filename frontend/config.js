// Centralized API configuration for all frontend scripts.
(function () {
    const isFileProtocol = window.location.protocol === 'file:';
    const isLocalHost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
    const isNonGatewayLocalPort = isLocalHost && window.location.port && window.location.port !== '8000';

    let baseUrl = '';

    if (isFileProtocol || isNonGatewayLocalPort) {
        baseUrl = 'http://localhost:8000';
    }

    const config = {
        BASE_URL: baseUrl,
    };

    window.API_CONFIG = config;
})();
