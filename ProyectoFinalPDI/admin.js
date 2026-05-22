/* =============================================
   AforoLAB UAO — admin.js
   Lógica del dashboard administrativo (admin.html)
   Requiere: Chart.js cargado, data.js cargado
   ============================================= */

/* ─── Generar datos históricos simulados ─── */
const HOURS = Array.from({ length: 14 }, (_, i) => i + 7); // 7:00 a 20:00
const CHART_COLORS = [
  '#C8102E', '#1E40AF', '#059669', '#D97706',
  '#7C3AED', '#0891B2', '#DB2777', '#65A30D',
];

function generateDayData() {
  return HOURS.map(h => {
    const row = { hora: `${h}:00` };
    LABS_DATA.forEach(lab => {
      const peak1  = Math.exp(-Math.pow(h - 11, 2) / 4);
      const peak2  = Math.exp(-Math.pow(h - 15, 2) / 6) * 0.8;
      const noise  = Math.random() * 0.2;
      const occ    = Math.min(1, peak1 + peak2 * 0.7 + noise) * lab.capacity;
      row[lab.name.replace('Lab. ', '')] = Math.round(occ);
    });
    return row;
  });
}

/* Seed fijo para rankings reproducibles en la sesión */
function seededRandom(seed) {
  let s = seed;
  return function () {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}
const rng = seededRandom(42);

const ranking = LABS_DATA.map(l => ({
  name:        l.name.replace('Lab. ', ''),
  usos:        Math.round(40 + rng() * 200),
  permanencia: Math.round(25 + rng() * 90),
})).sort((a, b) => b.usos - a.usos);

const subutilizados = [...ranking].slice(-3).reverse();
const dayData = generateDayData();

/* ─── KPIs ─── */
function renderKPIs() {
  const peakHour = dayData.reduce((best, row) => {
    const total = LABS_DATA.reduce((s, l) => s + (row[l.name.replace('Lab. ', '')] || 0), 0);
    return total > best.total ? { hora: row.hora, total } : best;
  }, { hora: '-', total: 0 });

  const avgPerm = Math.round(ranking.reduce((s, r) => s + r.permanencia, 0) / ranking.length);

  const kpis = [
    { icon: '📈', label: 'Hora pico identificada',  value: peakHour.hora },
    { icon: '⏱️',  label: 'Permanencia promedio',    value: `${avgPerm} min` },
    { icon: '🏆', label: 'Lab. más usado',           value: ranking[0]?.name ?? '—' },
    { icon: '⚠️', label: 'Subutilizado',             value: subutilizados[0]?.name ?? '—' },
  ];

  document.getElementById('kpi-grid').innerHTML = kpis.map(k => `
    <div class="kpi-card">
      <div class="kpi-icon">${k.icon}</div>
      <div>
        <p class="kpi-label">${k.label}</p>
        <p class="kpi-value">${k.value}</p>
      </div>
    </div>
  `).join('');
}

/* ─── Gráfico de líneas: ocupación por hora ─── */
function renderLineChart() {
  const ctx = document.getElementById('lineChart').getContext('2d');
  const labels = dayData.map(r => r.hora);
  const datasets = LABS_DATA.map((lab, i) => ({
    label:           lab.name.replace('Lab. ', ''),
    data:            dayData.map(r => r[lab.name.replace('Lab. ', '')] || 0),
    borderColor:     CHART_COLORS[i % CHART_COLORS.length],
    backgroundColor: 'transparent',
    borderWidth:     2,
    pointRadius:     0,
    tension:         0.4,
  }));

  new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 11, family: 'Inter' }, boxWidth: 14, padding: 14 },
        },
        tooltip: { bodyFont: { family: 'Inter' }, titleFont: { family: 'Inter' } },
      },
      scales: {
        x: { grid: { color: '#E5E7EB' }, ticks: { font: { size: 11, family: 'Inter' } } },
        y: { grid: { color: '#E5E7EB' }, ticks: { font: { size: 11, family: 'Inter' } }, beginAtZero: true },
      },
    },
  });
}

/* ─── Ranking horizontal ─── */
function renderRankChart() {
  const ctx = document.getElementById('rankChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels:   ranking.map(r => r.name),
      datasets: [{
        label:           'Usos en la semana',
        data:            ranking.map(r => r.usos),
        backgroundColor: '#C8102E',
        borderRadius:    6,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { bodyFont: { family: 'Inter' }, titleFont: { family: 'Inter' } },
      },
      scales: {
        x: { grid: { color: '#E5E7EB' }, ticks: { font: { size: 11, family: 'Inter' } }, beginAtZero: true },
        y: { grid: { display: false }, ticks: { font: { size: 11, family: 'Inter' } } },
      },
    },
  });
}

/* ─── Permanencia vertical ─── */
function renderPermChart() {
  const ctx = document.getElementById('permChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels:   ranking.map(r => r.name),
      datasets: [{
        label:           'Minutos promedio',
        data:            ranking.map(r => r.permanencia),
        backgroundColor: '#1E40AF',
        borderRadius:    6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { bodyFont: { family: 'Inter' }, titleFont: { family: 'Inter' } },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { size: 10, family: 'Inter' },
            maxRotation: 30,
            minRotation: 30,
          },
        },
        y: {
          grid: { color: '#E5E7EB' },
          ticks: { font: { size: 11, family: 'Inter' } },
          beginAtZero: true,
        },
      },
    },
  });
}

/* ─── Subutilizados ─── */
function renderSubutilizados() {
  document.getElementById('sub-list').innerHTML = subutilizados.map(s => `
    <li>
      <div>
        <p class="sub-name">${s.name}</p>
        <p class="sub-detail">Solo ${s.usos} usos en la semana · permanencia ${s.permanencia} min</p>
      </div>
      <span class="sub-badge">Bajo uso</span>
    </li>
  `).join('');
}

/* ─── Export CSV ─── */
function exportCSV() {
  const from = document.getElementById('date-from').value;
  const to   = document.getElementById('date-to').value;
  const header = ['Laboratorio', 'Usos semana', 'Permanencia promedio (min)'];
  const rows   = ranking.map(r => [r.name, r.usos, r.permanencia]);
  const csv    = [header, ...rows].map(r => r.join(',')).join('\n');
  const blob   = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url    = URL.createObjectURL(blob);
  const a      = document.createElement('a');
  a.href       = url;
  a.download   = `aforo-uao-${from}_${to}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

/* ─── BOOT ─── */
renderKPIs();
renderLineChart();
renderRankChart();
renderPermChart();
renderSubutilizados();
