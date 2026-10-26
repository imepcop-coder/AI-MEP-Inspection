document.addEventListener('DOMContentLoaded', () => {
  const calculatorSearch = document.getElementById('calculatorSearch');
  if (calculatorSearch) {
    calculatorSearch.addEventListener('input', () => {
      const query = calculatorSearch.value.toLowerCase().trim();
      document.querySelectorAll('.calculator-card, .card').forEach((card) => {
        const title = (card.querySelector('h2, h3, h4, h5')?.textContent || '').toLowerCase();
        card.style.display = title.includes(query) || query === '' ? '' : 'none';
      });
    });
  }

  const connection = document.getElementById('liveConnection');
  if (!connection) return;

  const statusText = document.getElementById('liveStatusText');
  const updatedAt = document.getElementById('liveUpdatedAt');
  const refreshButton = document.getElementById('refreshDashboard');
  const tableBody = document.getElementById('recentInspections');
  const searchInput = document.getElementById('inspectionSearch');
  const statusFilter = document.getElementById('inspectionStatusFilter');
  const emptyState = document.getElementById('inspectionEmptyState');
  const emptyTitle = document.getElementById('inspectionEmptyTitle');
  const emptyMessage = document.getElementById('inspectionEmptyMessage');
  let inspections = [];
  let requestInProgress = false;

  const updateText = (id, value) => {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value);
  };

  const setConnectionState = (state, label) => {
    connection.dataset.state = state;
    statusText.textContent = label;
  };

  const makeCell = (value) => {
    const cell = document.createElement('td');
    cell.textContent = value || '—';
    return cell;
  };

  const renderInspections = () => {
    if (!tableBody) return;
    tableBody.replaceChildren();

    inspections.forEach((inspection) => {
      const row = document.createElement('tr');
      row.dataset.inspectionRow = '';
      row.append(
        makeCell(inspection.inspection_no),
        makeCell(inspection.inspector),
        makeCell(inspection.discipline),
      );

      const statusCell = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = inspection.status || 'Open';
      const normalizedStatus = badge.textContent.toLowerCase();
      if (normalizedStatus === 'approved') {
        badge.classList.add('bg-success');
      } else if (normalizedStatus === 'pending') {
        badge.classList.add('bg-warning', 'text-dark');
      } else if (normalizedStatus === 'open') {
        badge.classList.add('bg-secondary');
      } else {
        badge.classList.add('bg-danger');
      }
      statusCell.appendChild(badge);
      row.append(statusCell, makeCell(inspection.inspection_date), makeCell(inspection.location));
      row.dataset.status = normalizedStatus;
      row.dataset.search = [
        inspection.inspection_no,
        inspection.inspector,
        inspection.discipline,
        inspection.location,
        inspection.status,
      ].join(' ').toLowerCase();
      tableBody.appendChild(row);
    });

    if (statusFilter) {
      const selected = statusFilter.value;
      const availableStatuses = [...new Set(inspections.map((item) => item.status || 'Open'))]
        .sort((a, b) => a.localeCompare(b));
      statusFilter.replaceChildren(new Option('All statuses', ''));
      availableStatuses.forEach((status) => statusFilter.add(new Option(status, status.toLowerCase())));
      statusFilter.value = availableStatuses.some((status) => status.toLowerCase() === selected) ? selected : '';
    }
    applyInspectionFilters();
  };

  const applyInspectionFilters = () => {
    if (!tableBody) return;
    const query = (searchInput?.value || '').trim().toLowerCase();
    const selectedStatus = statusFilter?.value || '';
    let visibleRows = 0;

    tableBody.querySelectorAll('[data-inspection-row]').forEach((row) => {
      const matches = (!query || row.dataset.search.includes(query))
        && (!selectedStatus || row.dataset.status === selectedStatus);
      row.hidden = !matches;
      if (matches) visibleRows += 1;
    });

    if (emptyState) {
      emptyState.classList.toggle('d-none', visibleRows > 0);
      const filteredOut = inspections.length > 0 && visibleRows === 0;
      emptyTitle.textContent = filteredOut ? 'No matching inspections' : 'No inspections yet';
      emptyMessage.textContent = filteredOut
        ? 'Try another search term or choose a different status.'
        : 'Start an inspection to see live activity here.';
    }
  };

  const displayUpdatedTime = (value) => {
    const date = new Date(value);
    updatedAt.textContent = Number.isNaN(date.getTime())
      ? 'Updated just now'
      : `Updated ${new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(date)}`;
  };

  const refreshDashboard = async () => {
    if (requestInProgress || document.visibilityState === 'hidden') return;
    requestInProgress = true;
    if (refreshButton) {
      refreshButton.disabled = true;
      refreshButton.classList.add('is-refreshing');
    }
    setConnectionState('loading', 'Updating');

    try {
      const response = await fetch('/api/dashboard/live', {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(`Dashboard refresh failed (${response.status})`);

      const data = await response.json();
      updateText('heroProjectCount', data.projects);
      updateText('heroInspectionCount', data.inspections);
      updateText('heroApprovedCount', data.approved);
      updateText('totalProjects', data.projects);
      updateText('totalInspections', data.inspections);
      updateText('pendingInspections', data.pending);
      updateText('aiRequests', data.ai_requests);

      const completion = data.inspections ? Math.round((data.approved / data.inspections) * 100) : 0;
      updateText('completionLabel', `${data.approved} of ${data.inspections} approved`);
      updateText('completionRate', `${completion}%`);
      const progressBar = document.querySelector('.progress-section .progress-bar');
      if (progressBar) {
        progressBar.style.width = `${completion}%`;
        progressBar.setAttribute('aria-valuenow', String(completion));
        progressBar.setAttribute('aria-label', `Inspection completion ${completion} percent`);
      }

      const notificationBadge = document.getElementById('unreadNotificationCount');
      if (notificationBadge) {
        const count = Number(data.unread_notifications) || 0;
        notificationBadge.textContent = count > 99 ? '99+' : String(count);
        notificationBadge.classList.toggle('d-none', count === 0);
        notificationBadge.setAttribute('aria-label', `${count} unread notifications`);
      }

      inspections = Array.isArray(data.recent_inspections) ? data.recent_inspections : [];
      renderInspections();
      displayUpdatedTime(data.updated_at);
      setConnectionState('online', 'Live');
    } catch (error) {
      console.error('Unable to refresh live dashboard data:', error);
      setConnectionState('offline', 'Refresh unavailable');
      updatedAt.textContent = 'Showing last available data';
    } finally {
      requestInProgress = false;
      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.classList.remove('is-refreshing');
      }
    }
  };

  searchInput?.addEventListener('input', applyInspectionFilters);
  statusFilter?.addEventListener('change', applyInspectionFilters);
  refreshButton?.addEventListener('click', refreshDashboard);
  window.addEventListener('online', refreshDashboard);
  window.addEventListener('offline', () => {
    setConnectionState('offline', 'Offline');
    updatedAt.textContent = 'Showing last available data';
  });
  window.setInterval(refreshDashboard, 30000);
  refreshDashboard();
});
