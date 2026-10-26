document.addEventListener('DOMContentLoaded', () => {
  const dashboard = document.getElementById('analyticsDashboard');
  const filterForm = document.getElementById('analyticsFilters');
  if (!dashboard || !filterForm) return;

  const controls = Array.from(filterForm.querySelectorAll('select, input'));
  const periodFilter = document.getElementById('periodFilter');
  const startDateFilter = document.getElementById('startDateFilter');
  const endDateFilter = document.getElementById('endDateFilter');
  const loading = document.getElementById('analyticsLoading');
  const error = document.getElementById('analyticsError');
  const refreshButton = document.getElementById('refreshAnalytics');
  const exportLink = document.getElementById('exportAnalytics');
  const charts = new Map();
  let activeRequest = null;

  const chartDefinitions = [
    { key: 'inspection_trend', id: 'trendChart', type: 'line', label: 'Inspections', color: '#087f78' },
    { key: 'inspection_status', id: 'inspectionStatusChart', type: 'doughnut' },
    { key: 'ncr_severity', id: 'ncrSeverityChart', type: 'bar', label: 'NCRs', color: '#c28b3c' },
    { key: 'ncr_status', id: 'ncrStatusChart', type: 'doughnut' },
    { key: 'discipline_performance', id: 'disciplineChart', type: 'stacked' },
    { key: 'project_progress', id: 'projectChart', type: 'horizontal' },
    { key: 'ai_usage', id: 'aiChart', type: 'line', label: 'AI requests', color: '#3976a8' },
    { key: 'compliance_status', id: 'complianceChart', type: 'doughnut' },
  ];

  const filterParams = () => {
    const params = new URLSearchParams();
    const usesCustomDates = periodFilter.value === 'custom';
    controls.forEach((control) => {
      if (!usesCustomDates && ['start_date', 'end_date'].includes(control.name)) return;
      if (control.value) params.set(control.name, control.value);
    });
    return params;
  };

  const updateExportLink = () => {
    const query = filterParams().toString();
    exportLink.href = `/analytics/export.csv${query ? `?${query}` : ''}`;
  };

  const showError = (message) => {
    error.textContent = message;
    error.classList.remove('d-none');
  };

  const hideError = () => {
    error.textContent = '';
    error.classList.add('d-none');
  };

  const setLoading = (isLoading) => {
    loading.classList.toggle('d-none', !isLoading);
    dashboard.setAttribute('aria-busy', String(isLoading));
    refreshButton.disabled = isLoading;
  };

  const updateKpis = (data) => {
    document.querySelectorAll('[data-kpi]').forEach((element) => {
      const key = element.dataset.kpi;
      const value = data.kpis[key];
      element.textContent = value === null || value === undefined ? '—' : Number(value).toLocaleString();
      const card = element.closest('.kpi-card');
      const reason = data.unavailable[key];
      if (card) {
        card.classList.toggle('kpi-unavailable', Boolean(reason));
        if (reason) card.title = reason;
        else card.removeAttribute('title');
      }
    });

    document.querySelectorAll('[data-kpi-note]').forEach((element) => {
      element.textContent = data.unavailable[element.dataset.kpiNote] || 'Workspace request records';
    });
  };

  const colorsFor = (labels) => {
    const palette = ['#087f78', '#c28b3c', '#3976a8', '#8b6bb5', '#5a9b68', '#d56b58', '#64878c'];
    return labels.map((_, index) => palette[index % palette.length]);
  };

  const setChartEmptyState = (definition, chartData, unavailable) => {
    const canvas = document.getElementById(definition.id);
    const empty = canvas?.parentElement.querySelector('.chart-empty');
    if (!canvas || !empty) return false;
    const values = chartData?.data || chartData?.total || [];
    const hasData = !unavailable
      && Array.isArray(chartData?.labels)
      && chartData.labels.length > 0
      && (definition.key === 'project_progress'
        ? values.length > 0
        : values.some((value) => Number(value) > 0));
    canvas.classList.toggle('d-none', !hasData);
    empty.classList.toggle('d-none', hasData);
    return hasData;
  };

  const renderChart = (definition, chartData) => {
    const isAvailable = definition.key !== 'ai_usage' || chartData.available;
    const canvas = document.getElementById(definition.id);
    const empty = canvas?.parentElement.querySelector('.chart-empty');
    if (definition.key === 'ai_usage' && empty) {
      empty.textContent = isAvailable
        ? 'No AI requests recorded in this range.'
        : 'AI requests cannot be scoped to the selected inspection filters.';
    }
    if (!setChartEmptyState(definition, chartData, !isAvailable)) return;
    if (typeof Chart === 'undefined') {
      if (canvas && empty) {
        canvas.classList.add('d-none');
        empty.textContent = 'Charts are unavailable because the chart library did not load.';
        empty.classList.remove('d-none');
      }
      return;
    }
    charts.get(definition.id)?.destroy();
    charts.get(definition.id)?.destroy();
    let config;
    if (definition.type === 'line') {
      config = {
        type: 'line',
        data: {
          labels: chartData.labels,
          datasets: [{
            label: definition.label,
            data: chartData.data,
            borderColor: definition.color,
            backgroundColor: `${definition.color}22`,
            fill: true,
            tension: 0.3,
            pointRadius: 2,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      };
    } else if (definition.type === 'bar') {
      config = {
        type: 'bar',
        data: {
          labels: chartData.labels,
          datasets: [{
            label: definition.label,
            data: chartData.data,
            backgroundColor: colorsFor(chartData.labels),
            borderRadius: 5,
          }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      };
    } else if (definition.type === 'stacked') {
      config = {
        type: 'bar',
        data: {
          labels: chartData.labels,
          datasets: [
            { label: 'Closed', data: chartData.completed, backgroundColor: '#087f78', borderRadius: 4 },
            { label: 'Not closed', data: chartData.total.map((value, index) => value - chartData.completed[index]), backgroundColor: '#dce6e3', borderRadius: 4 },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } }, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } } },
      };
    } else if (definition.type === 'horizontal') {
      config = {
        type: 'bar',
        data: {
          labels: chartData.labels,
          datasets: [{ label: 'Completion %', data: chartData.data, backgroundColor: '#087f78', borderRadius: 5 }],
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, max: 100 } } },
      };
    } else {
      config = {
        type: 'doughnut',
        data: {
          labels: chartData.labels,
          datasets: [{ data: chartData.data, backgroundColor: colorsFor(chartData.labels), borderWidth: 0 }],
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '66%', plugins: { legend: { position: 'bottom' } } },
      };
    }
    charts.set(definition.id, new Chart(canvas, config));
  };

  const appendCell = (row, value) => {
    const cell = document.createElement('td');
    cell.textContent = value || '—';
    row.appendChild(cell);
  };

  const renderProgressTable = (projects) => {
    const body = document.getElementById('projectProgressTable');
    const empty = document.getElementById('projectProgressEmpty');
    body.replaceChildren();
    projects.forEach((project) => {
      const row = document.createElement('tr');
      const nameCell = document.createElement('td');
      const link = document.createElement('a');
      link.href = project.url;
      link.textContent = project.name;
      nameCell.appendChild(link);
      row.appendChild(nameCell);
      appendCell(row, `${project.completed} / ${project.total}`);
      appendCell(row, `${project.completion_rate}%`);
      body.appendChild(row);
    });
    empty.classList.toggle('d-none', projects.length > 0);
  };

  const renderInspections = (items) => {
    const body = document.getElementById('recentInspectionsTable');
    const empty = document.getElementById('recentInspectionsEmpty');
    body.replaceChildren();
    items.forEach((inspection) => {
      const row = document.createElement('tr');
      const numberCell = document.createElement('td');
      const link = document.createElement('a');
      link.href = inspection.url;
      link.textContent = inspection.inspection_no;
      numberCell.appendChild(link);
      row.appendChild(numberCell);
      [inspection.project, inspection.inspector, inspection.discipline, inspection.status, inspection.date]
        .forEach((value) => appendCell(row, value));
      body.appendChild(row);
    });
    empty.classList.toggle('d-none', items.length > 0);
  };

  const renderInsights = (items) => {
    const list = document.getElementById('analyticsInsights');
    list.replaceChildren();
    items.forEach((item) => {
      const entry = document.createElement('li');
      entry.className = `attention-item attention-${item.kind}`;
      const iconHolder = document.createElement('span');
      iconHolder.className = 'attention-icon';
      const icon = document.createElement('i');
      icon.className = `bi ${item.kind === 'critical' ? 'bi-exclamation-triangle' : item.kind === 'warning' ? 'bi-exclamation-circle' : 'bi-check-circle'}`;
      icon.setAttribute('aria-hidden', 'true');
      iconHolder.appendChild(icon);
      const link = document.createElement('a');
      link.href = item.url;
      link.textContent = item.text;
      entry.append(iconHolder, link);
      list.appendChild(entry);
    });
  };

  const renderAnalytics = (data) => {
    updateKpis(data);
    chartDefinitions.forEach((definition) => renderChart(definition, data.charts[definition.key]));
    renderProgressTable(data.project_progress);
    renderInspections(data.recent_inspections);
    renderInsights(data.insights);
    document.getElementById('analyticsUpdatedAt').textContent = `Updated ${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(data.generated_at))}`;
  };

  const updateData = async () => {
    if (activeRequest) activeRequest.abort();
    const requestController = new AbortController();
    activeRequest = requestController;
    setLoading(true);
    hideError();
    updateExportLink();
    try {
      const query = filterParams().toString();
      const response = await fetch(`/api/analytics${query ? `?${query}` : ''}`, {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
        credentials: 'same-origin',
        signal: requestController.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Analytics refresh failed (${response.status}).`);
      renderAnalytics(data);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Unable to update analytics:', err);
        showError(err.message || 'Unable to load analytics. Please try again.');
      }
    } finally {
      if (activeRequest === requestController) {
        setLoading(false);
        activeRequest = null;
      }
    }
  };

  const updateCustomDateVisibility = () => {
    const showCustom = periodFilter.value === 'custom';
    document.getElementById('customDateStart').classList.toggle('d-none', !showCustom);
    document.getElementById('customDateEnd').classList.toggle('d-none', !showCustom);
    startDateFilter.required = showCustom;
    endDateFilter.required = showCustom;
  };

  filterForm.addEventListener('submit', (event) => {
    event.preventDefault();
    updateData();
  });
  periodFilter.addEventListener('change', () => {
    updateCustomDateVisibility();
    updateExportLink();
    if (periodFilter.value !== 'custom') updateData();
  });
  controls.filter((control) => control !== periodFilter).forEach((control) => {
    control.addEventListener('change', () => {
      updateExportLink();
      if (periodFilter.value !== 'custom' || (startDateFilter.value && endDateFilter.value)) updateData();
    });
  });
  exportLink.addEventListener('click', (event) => {
    if (periodFilter.value === 'custom' && (!startDateFilter.value || !endDateFilter.value)) {
      event.preventDefault();
      showError('Choose both a start and end date before exporting a custom range.');
    }
  });
  document.getElementById('clearAnalyticsFilters').addEventListener('click', () => {
    filterForm.reset();
    updateCustomDateVisibility();
    updateData();
  });
  refreshButton.addEventListener('click', updateData);

  updateCustomDateVisibility();
  updateExportLink();
  if (window.analyticsData) renderAnalytics(window.analyticsData);
});
