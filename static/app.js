// AquaTrace AI prototype: lightweight client-side behavior only.
// All anomaly calculations and database writes happen in the Flask backend.
document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.reading-form');
  const input = document.querySelector('#usage_liters');
  const zone = document.querySelector('#zone');

  if (form && input && zone) {
    form.addEventListener('submit', (event) => {
      const value = Number(input.value);
      if (!Number.isFinite(value) || value <= 0) {
        event.preventDefault();
        input.focus();
        input.setCustomValidity('Enter a positive numeric reading in litres.');
        input.reportValidity();
        return;
      }
      input.setCustomValidity('');
    });

    input.addEventListener('input', () => input.setCustomValidity(''));
  }

  // Keep anchor navigation pleasant for the dashboard cards.
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        event.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
});
