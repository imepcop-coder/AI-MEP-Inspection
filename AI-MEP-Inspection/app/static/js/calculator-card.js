const initializeCalculatorCardScript = () => {
  const storage = {
    favorites: 'mepCalculatorFavorites',
    recent: 'mepCalculatorRecent',
    history: 'mepCalculatorHistory',
  };
  
  const getArray = (key) => {
    try {
      return JSON.parse(localStorage.getItem(key) || '[]');
    } catch (error) {
      return [];
    }
  };

  const renderHistoryItems = () => {
    if (!historyList || !historyCount) return;

    const history = getArray(storage.history);
    historyCount.textContent = String(history.length);
    historyList.replaceChildren();

    if (!history.length) {
      historyList.innerHTML = '<div class="panel-empty">Completed calculations will appear here.</div>';
      return;
    }

    history.slice(0, 6).forEach((item) => {
      const row = document.createElement('a');
      row.href = item.url;
      row.className = 'panel-item';
      row.dataset.historyId = item.id;
      const date = new Date(item.createdAt);
      row.textContent = `${item.name} · ${date.toLocaleString()}`;
      historyList.appendChild(row);
    });
  };

  const recordCompletedCalculation = () => {
    const form = document.querySelector('form[data-calculation-complete="true"]');
    if (!form) return;

    const inputs = {};
    new FormData(form).forEach((value, key) => {
      if (key && !key.toLowerCase().includes('csrf')) inputs[key] = value;
    });
    const url = window.location.pathname;
    const name = form.dataset.calculatorTitle || document.querySelector('h1')?.textContent.trim() || document.title;
    const history = getArray(storage.history);
    history.unshift({
      id: `${Date.now()}-${url}`,
      name,
      url,
      inputs,
      createdAt: new Date().toISOString(),
    });
    if (history.length > 10) history.length = 10;
    saveArray(storage.history, history);
  };

  const restoreCalculationInputs = () => {
    const saved = sessionStorage.getItem('mepCalculatorRestore');
    if (!saved) return;
    let item;
    try {
      item = JSON.parse(saved);
    } catch (error) {
      sessionStorage.removeItem('mepCalculatorRestore');
      return;
    }
    if (!item || typeof item !== 'object' || item.url !== window.location.pathname) return;

    const form = document.querySelector('form[data-calculation-complete]');
    if (form) {
      Object.entries(item.inputs || {}).forEach(([name, value]) => {
        const field = form.elements.namedItem(name);
        if (field) field.value = value;
      });
    }
    sessionStorage.removeItem('mepCalculatorRestore');
  };

  const saveArray = (key, value) => {
    localStorage.setItem(key, JSON.stringify(value));
  };

  const favoritesList = document.getElementById('favoritesList');
  const recentList = document.getElementById('recentList');
  const favoriteCount = document.getElementById('favoriteCount');
  const recentCount = document.getElementById('recentCount');
  const heroFavoriteCount = document.getElementById('heroFavoriteCount');
  const heroRecentCount = document.getElementById('heroRecentCount');
  const historyList = document.getElementById('calculationHistoryList');
  const historyCount = document.getElementById('calculationHistoryCount');
  const noResults = document.getElementById('noResults');
  const calculatorCards = Array.from(document.querySelectorAll('.calculator-card'));
  const searchInput = document.getElementById('calculatorSearch');
  const favoritesOnlyToggle = document.getElementById('favoritesOnlyToggle');
  const categoryPills = Array.from(document.querySelectorAll('.category-pill'));
  let favoritesOnly = false;

  const getSelectedCategory = () => {
    const params = new URLSearchParams(window.location.search);
    const selected = params.get('category');
    return selected ? selected.toLowerCase() : 'all';
  };

  const renderFavoriteItems = () => {
    if (!favoritesList || !favoriteCount || !heroFavoriteCount) return;

    const favorites = getArray(storage.favorites);
    favoriteCount.textContent = String(favorites.length);
    heroFavoriteCount.textContent = String(favorites.length);
    favoritesList.innerHTML = '';

    if (!favorites.length) {
      favoritesList.innerHTML = '<div class="panel-empty">No favorites yet. Use the heart icon to save your most-used calculators.</div>';
      return;
    }

    favorites.slice(0, 6).forEach((item) => {
      const row = document.createElement('a');
      row.href = item.url;
      row.className = 'panel-item';
      row.textContent = item.name;
      favoritesList.appendChild(row);
    });
  };

  const renderRecentItems = () => {
    if (!recentList || !recentCount || !heroRecentCount) return;

    const recent = getArray(storage.recent);
    recentCount.textContent = String(recent.length);
    heroRecentCount.textContent = String(recent.length);
    recentList.innerHTML = '';

    if (!recent.length) {
      recentList.innerHTML = '<div class="panel-empty">Your recently opened calculators will appear here.</div>';
      return;
    }

    recent.slice(0, 6).forEach((item) => {
      const row = document.createElement('a');
      row.href = item.url;
      row.className = 'panel-item';
      row.textContent = item.name;
      recentList.appendChild(row);
    });
  };

  const updateFavoriteButtons = () => {
    const favorites = getArray(storage.favorites);
    const favoriteIds = new Set(favorites.map((item) => item.id));

    document.querySelectorAll('.favorite-toggle').forEach((button) => {
      const id = button.dataset.calculatorId;
      const isFavorite = favoriteIds.has(id);
      button.classList.toggle('active', isFavorite);
      const icon = button.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-heart-fill', isFavorite);
        icon.classList.toggle('bi-heart', !isFavorite);
      }
    });
  };

  const toggleFavorite = (calculatorId, name, url) => {
    const favorites = getArray(storage.favorites);
    const index = favorites.findIndex((item) => item.id === calculatorId);

    if (index >= 0) {
      favorites.splice(index, 1);
    } else {
      favorites.unshift({ id: calculatorId, name, url });
    }

    saveArray(storage.favorites, favorites);
    updateFavoriteButtons();
    renderFavoriteItems();
    applyFilters();
  };

  const recordRecent = (item) => {
    const recent = getArray(storage.recent);
    const existing = recent.findIndex((entry) => entry.id === item.id);

    if (existing >= 0) {
      recent.splice(existing, 1);
    }

    recent.unshift(item);
    if (recent.length > 8) recent.length = 8;
    saveArray(storage.recent, recent);
    renderRecentItems();
  };

  const applyFilters = () => {
    if (!searchInput || !calculatorCards.length) return;

    const activeCategory = getSelectedCategory();
    const searchValue = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    calculatorCards.forEach((card) => {
      const name = card.dataset.name || '';
      const description = card.dataset.description || '';
      const category = card.dataset.category || 'all';
      const matchesCategory = activeCategory === 'all' || category === activeCategory;
      const matchesSearch = !searchValue || name.includes(searchValue) || description.includes(searchValue) || category.includes(searchValue);
      const favorites = getArray(storage.favorites);
      const isFavorite = favorites.some((item) => item.id === card.dataset.calculatorId);
      const visible = matchesCategory && matchesSearch && (!favoritesOnly || isFavorite);
      const cell = card.closest('.calculator-grid__cell');
      const displayValue = visible ? '' : 'none';
      if (cell) {
        cell.classList.toggle('d-none', !visible);
      }
      card.style.display = displayValue;
      if (visible) visibleCount += 1;
    });

    if (noResults) {
      noResults.classList.toggle('d-none', visibleCount > 0);
    }
  };

  const bindFavoriteButtons = () => {
    document.querySelectorAll('.favorite-toggle').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        const card = event.currentTarget.closest('.calculator-card');
        if (!card) return;
        toggleFavorite(card.dataset.calculatorId, card.dataset.name, card.dataset.url);
      });
    });
  };

  const bindOpenButtons = () => {
    document.querySelectorAll('.calculator-card__primary').forEach((link) => {
      link.addEventListener('click', () => {
        recordRecent({
          id: link.dataset.calculatorId,
          name: link.dataset.name,
          url: link.dataset.url,
          category: link.dataset.category,
        });
      });
    });

    document.querySelectorAll('.calculator-card__action--pdf, .calculator-card__action--excel').forEach((link) => {
      link.addEventListener('click', () => {
        recordRecent({
          id: link.dataset.calculatorId,
          name: link.dataset.name,
          url: link.dataset.url,
          category: link.dataset.category,
        });
      });
    });
  };

  const bindPrintButtons = () => {
    document.querySelectorAll('.calculator-card__action--print').forEach((button) => {
      button.addEventListener('click', () => {
        const url = button.dataset.printUrl;
        if (!url) return;
        const win = window.open(url, '_blank');
        if (win) {
          win.focus();
          setTimeout(() => {
            win.print();
          }, 250);
        }
      });
    });
  };

  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }
  if (favoritesOnlyToggle) {
    favoritesOnlyToggle.addEventListener('click', () => {
      favoritesOnly = !favoritesOnly;
      favoritesOnlyToggle.setAttribute('aria-pressed', String(favoritesOnly));
      favoritesOnlyToggle.classList.toggle('active', favoritesOnly);
      favoritesOnlyToggle.innerHTML = favoritesOnly
        ? '<i class="bi bi-heart-fill me-1"></i>Showing favorites'
        : '<i class="bi bi-heart me-1"></i>Show favorites only';
      applyFilters();
    });
  }
  if (historyList) {
    historyList.addEventListener('click', (event) => {
      const link = event.target.closest('a[data-history-id]');
      if (!link) return;
      const item = getArray(storage.history).find((entry) => entry.id === link.dataset.historyId);
      if (!item) return;
      sessionStorage.setItem('mepCalculatorRestore', JSON.stringify(item));
    });
  }

  categoryPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      const selected = pill.dataset.category || 'all';
      const params = new URLSearchParams(window.location.search);
      params.set('category', selected);
      const url = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState({}, '', url);
      applyFilters();
      categoryPills.forEach((item) => item.classList.toggle('active', item === pill));
    });
  });

  bindFavoriteButtons();
  bindOpenButtons();
  bindPrintButtons();
  updateFavoriteButtons();
  renderFavoriteItems();
  renderRecentItems();
  renderHistoryItems();
  restoreCalculationInputs();
  recordCompletedCalculation();
  applyFilters();
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeCalculatorCardScript);
} else {
  initializeCalculatorCardScript();
}
