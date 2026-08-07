document.addEventListener('DOMContentLoaded', () => {
  const analyticsData = window.analyticsData;
  if (!analyticsData || typeof Chart === 'undefined') {
    return;
  }

  const animateKpiCounters = () => {
    const counters = Array.from(document.querySelectorAll('.kpi-value[data-value]'));
    counters.forEach((counter) => {
      const targetValue = Number(String(counter.dataset.value).replace(/,/g, ''));
      if (Number.isNaN(targetValue)) {
        return;
      }

      const duration = 1300;
      const startTime = performance.now();
      const formatValue = (value) => value.toLocaleString();

      const tick = (currentTime) => {
        const progress = Math.min((currentTime - startTime) / duration, 1);
        counter.textContent = formatValue(Math.round(targetValue * progress));
        if (progress < 1) {
          requestAnimationFrame(tick);
        }
      };

      requestAnimationFrame(tick);
    });
  };

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 900, easing: 'easeOutQuart' },
    plugins: {
      legend: { display: false },
      tooltip: { mode: 'index', intersect: false },
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
  };

  const hexToRgba = (hex, alpha = 1) => {
    const raw = hex.replace('#', '');
    const bigint = parseInt(raw, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const createLineChart = (elementId, labels, data, label, borderColor) => {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label,
            data,
            borderColor,
            backgroundColor: hexToRgba(borderColor, 0.18),
            tension: 0.35,
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: true,
          },
        ],
      },
      options: chartDefaults,
    });
  };

  const createBarChart = (elementId, labels, data, backgroundColor) => {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

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
      options: chartDefaults,
    });
  };

  const createPieChart = (elementId, labels, data, colors) => {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

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
        animation: { duration: 900, easing: 'easeOutQuart' },
        plugins: {
          legend: { position: 'bottom', labels: { color: '#6b7280' } },
          tooltip: { mode: 'index', intersect: false },
        },
      },
    });
  };

  const trendLabels = analyticsData.timeline?.map((_, index) => `Period ${index + 1}`) || [];

  animateKpiCounters();
  createLineChart('trendChart', trendLabels, analyticsData.inspection_trend || [], 'Inspection Trend', '#2563eb');
  createPieChart('pieChart', ['Pass', 'Fail'], analyticsData.pass_fail || [], ['#22c55e', '#ef4444']);
  createLineChart('ncrChart', analyticsData.ncr_trend?.map((_, index) => `Week ${index + 1}`) || [], analyticsData.ncr_trend || [], 'NCR Trend', '#f59e0b');
  createBarChart('aiChart', analyticsData.ai_usage?.map((_, index) => `Q${index + 1}`) || [], analyticsData.ai_usage || [], ['#2563eb', '#0ea5e9', '#38bdf8', '#7dd3fc', '#bae6fd']);
  createBarChart('timelineChart', trendLabels, analyticsData.timeline || [], ['#2563eb']);
});
