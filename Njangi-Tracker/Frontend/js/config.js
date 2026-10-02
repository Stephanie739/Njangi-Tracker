/*
 * Frontend configuration.
 * - Local development (Frontend/serve.py on port 5500): the backend runs on port 8000 of the same machine.
 * - Anywhere else (nginx in production): the API is on the same address under /api.
 *   (nginx forwards /api/ to the backend, so no other setting is needed.)
 */
window.NJANGI_CONFIG = {
  API_BASE: (function () {
    if (location.port === '5500') {
      return 'http://' + (location.hostname || '127.0.0.1') + ':8000/api';
    }
    return '/api';
  })()
};
