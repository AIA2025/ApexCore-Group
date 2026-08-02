// Stripe checkout integration utilities
(function() {
  'use strict';

  function handleCheckoutError(message) {
    const errorEl = document.getElementById('error-msg');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    } else {
      alert(message);
    }
  }

  window.handleCheckoutError = handleCheckoutError;
})();
