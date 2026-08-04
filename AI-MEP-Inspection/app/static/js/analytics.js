document.addEventListener('DOMContentLoaded', () => {
  const analyticsData = window.analyticsData;
  if (!analyticsData || typeof Chart === 'undefined') {
    return;
  }

  const createLineChart = (elementId, labels, data, label, borderColor) => {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
      return;
    }

    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label,
            data,
            borderColor,
            backgroundColor: borderColor,
            tension: 0.35,
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#6b7280' },
          },
          y: {
            beginAtZero: true,
            ticks: { color: '#6b7280' },
            grid: { color: 'rgba(15, 23, 42, 0.08)' },
          },
        },
      },
    });
  };

  const createBarChart = (elementId, labels, data, backgroundColor) => {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
      return;
    }

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor,
            borderRadius: 12,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#6b7280' },
          },
          y: {
            beginAtZero: true,
            ticks: { color: '#6b7280' },
            grid: { color: 'rgba(15, 23, 42, 0.08)' },
          },
        },
      },
    });
  };

  const createPieChart = (elementId, labels, data, colors) => {
    const ctx = document.getElementById(elementId);
    if (!ctx) {
      return;
    }

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#6b7280' } },
        },
      },
    });
  };

  const trendLabels = analyticsData.timeline?.map((value, index) => `Period ${index + 1}`) || [];
  createLineChart('trendChart', trendLabels, analyticsData.inspection_trend || [], 'Inspection Trend', '#2563eb');
  createPieChart('pieChart', ['Pass', 'Fail'], analyticsData.pass_fail || [], ['#22c55e', '#ef4444']);
  createLineChart('ncrChart', analyticsData.ncr_trend?.map((_, index) => `Week ${index + 1}`) || [], analyticsData.ncr_trend || [], 'NCR Trend', '#f59e0b');
  createBarChart('aiChart', analyticsData.ai_usage?.map((_, index) => `Q${index + 1}`) || [], analyticsData.ai_usage || [], ['#2563eb', '#0ea5e9', '#38bdf8', '#7dd3fc', '#bae6fd']);
  createBarChart('timelineChart', trendLabels, analyticsData.timeline || [], ['#2563eb']);
});
