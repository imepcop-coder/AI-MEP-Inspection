document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('calculatorSearch');
  if (!searchInput) {
    return;
  }

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();
    const cards = document.querySelectorAll('.card');

    cards.forEach((card) => {
      const title = (card.querySelector('h2, h3, h4, h5')?.textContent || '').toLowerCase();
      card.style.display = title.includes(query) || query === '' ? '' : 'none';
    });
  });
});
