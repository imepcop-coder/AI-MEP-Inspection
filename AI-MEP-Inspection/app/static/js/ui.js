document.addEventListener('DOMContentLoaded', () => {
  const toastContainer = document.getElementById('appToastContainer');

  const showToast = (message, type = 'info') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `app-toast ${type}`;
    toast.innerHTML = `<strong>${type.charAt(0).toUpperCase() + type.slice(1)}</strong>${message}`;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
  };

  const highlightActiveMenu = () => {
    const path = window.location.pathname.toLowerCase();
    document.querySelectorAll('.sidebar-nav .nav-link').forEach((link) => {
      const href = link.getAttribute('href') || '';
      if (href === '/' && path === '/') {
        link.classList.add('active');
        return;
      }
      if (href !== '/' && path.startsWith(href.toLowerCase())) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  };

  const saveSidebarState = (isOpen) => localStorage.setItem('sidebarOpen', isOpen ? 'true' : 'false');
  const loadSidebarState = () => localStorage.getItem('sidebarOpen') === 'true';

  const toggleSidebar = () => {
    if (window.innerWidth <= 991) {
      document.body.classList.toggle('sidebar-open');
      saveSidebarState(document.body.classList.contains('sidebar-open'));
    } else {
      document.body.classList.toggle('sidebar-collapsed');
    }
  };

  const sidebarToggle = document.getElementById('sidebarToggle');
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', (event) => {
      event.preventDefault();
      toggleSidebar();
    });
  }

  if (loadSidebarState()) {
    document.body.classList.add('sidebar-open');
  }

  const themeToggle = document.getElementById('themeToggle');
  const applyTheme = (theme) => {
    document.documentElement.dataset.theme = theme;
    document.body.dataset.theme = theme;
    if (theme === 'dark') {
      themeToggle.innerHTML = '<i class="bi bi-moon-stars"></i>';
    } else {
      themeToggle.innerHTML = '<i class="bi bi-sun"></i>';
    }
    localStorage.setItem('theme', theme);
  };

  const currentTheme = localStorage.getItem('theme') || 'light';
  if (themeToggle) {
    applyTheme(currentTheme);
    themeToggle.addEventListener('click', () => {
      const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
    });
  }

  const breadcrumbTitle = document.getElementById('breadcrumbTitle');
  if (breadcrumbTitle) {
    const title = document.title || 'Dashboard';
    breadcrumbTitle.textContent = title.replace(' | AI Construction Inspection Platform', '').trim();
  }

  const tableSearchEmptyClass = 'table-search-empty';
  const filterTableRows = (query) => {
    const tables = Array.from(document.querySelectorAll('.table')); 
    if (!tables.length) return false;
    const searchTerm = query.trim().toLowerCase();
    let matchedAny = false;
    tables.forEach((table) => {
      const rows = Array.from(table.querySelectorAll('tbody tr'));
      let visibleCount = 0;
      rows.forEach((row) => {
        const text = row.innerText.toLowerCase();
        const match = !searchTerm || text.includes(searchTerm);
        row.style.display = match ? '' : 'none';
        if (match) visibleCount += 1;
      });
      const container = table.closest('.table-responsive') || table.parentElement;
      if (container) {
        let emptyState = container.querySelector(`.${tableSearchEmptyClass}`);
        if (!emptyState) {
          emptyState = document.createElement('div');
          emptyState.className = tableSearchEmptyClass;
          emptyState.textContent = 'No results match your search. Adjust your terms to find content.';
          container.appendChild(emptyState);
        }
        emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
      }
      matchedAny = matchedAny || visibleCount > 0;
    });
    return true;
  };

  const globalSearchForm = document.getElementById('globalSearchForm');
  const globalSearchInput = document.getElementById('globalSearchInput');

  const applySearchParam = () => {
    const params = new URLSearchParams(window.location.search);
    const searchValue = params.get('search') || '';
    if (!searchValue) return;
    if (globalSearchInput) {
      globalSearchInput.value = searchValue;
    }
    const calculatorSearch = document.getElementById('calculatorSearch');
    if (calculatorSearch) {
      calculatorSearch.value = searchValue;
      calculatorSearch.dispatchEvent(new Event('input'));
    }
    filterTableRows(searchValue);
  };

  if (globalSearchForm && globalSearchInput) {
    globalSearchForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const query = globalSearchInput.value.trim();
      if (!query) {
        return;
      }
      const calculatorSearch = document.getElementById('calculatorSearch');
      if (calculatorSearch) {
        calculatorSearch.value = query;
        calculatorSearch.dispatchEvent(new Event('input'));
      }
      const filtered = filterTableRows(query);
      if (!filtered) {
        window.location.href = `/calculators?search=${encodeURIComponent(query)}`;
      }
    });
  }

  highlightActiveMenu();
  applySearchParam();

  const forms = Array.from(document.querySelectorAll('form'));
  forms.forEach((form) => {
    if (form.dataset.skipProcessing === 'true') {
      return;
    }

    form.addEventListener('submit', (event) => {
      const requiredFields = Array.from(form.querySelectorAll('[required]'));
      let isValid = true;
      requiredFields.forEach((field) => {
        const value = field.value ? String(field.value).trim() : '';
        const errorBox = field.parentElement?.querySelector('.field-error');
        if (!value) {
          isValid = false;
          field.classList.add('is-invalid');
          if (errorBox) {
            errorBox.style.display = 'block';
            errorBox.textContent = 'This field is required.';
          }
        } else {
          field.classList.remove('is-invalid');
          if (errorBox) {
            errorBox.style.display = 'none';
          }
        }
      });

      if (!isValid) {
        event.preventDefault();
        showToast('Please complete the required fields before submitting.', 'error');
      } else {
        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitButton) {
          submitButton.disabled = true;
          submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        }
      }
    });
  });

  document.querySelectorAll('button[data-toast-success], .btn[data-toast-success]').forEach((button) => {
    button.addEventListener('click', () => showToast(button.dataset.toastSuccess, 'success'));
  });

  document.querySelectorAll('button[data-toast-error], .btn[data-toast-error]').forEach((button) => {
    button.addEventListener('click', () => showToast(button.dataset.toastError, 'error'));
  });

  document.querySelectorAll('[data-action="close-toast"]').forEach((element) => {
    element.addEventListener('click', () => showToast('Action completed successfully.', 'success'));
  });
});
