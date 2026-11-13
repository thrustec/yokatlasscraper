const BOT = 'tuik-sdmx';
const API = `/ops/v1/bots/${BOT}`;
let adminKey = '';
let categories = [];
let allDatasets = [];
let pollTimer = null;

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[ch]));

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'X-API-Key': adminKey,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function setConnection(message, state = '') {
  $('connectionState').textContent = message;
  $('connectionState').style.color = state === 'error' ? '#ae4c47' : state === 'ok' ? '#318362' : '';
  $('botState').textContent = state === 'ok' ? 'Katalog bağlantısı hazır' : state === 'error' ? 'Bağlantı kurulamadı' : 'Bağlantı bekleniyor';
}

async function connect() {
  const entered = $('adminKey').value.trim();
  if (!entered) {
    setConnection('Admin API anahtarını gir.', 'error');
    return;
  }
  adminKey = entered;
  $('connectButton').disabled = true;
  $('connectButton').textContent = 'Bağlanıyor…';
  try {
    const [catalog] = await Promise.all([
      request(`${API}/datasets`),
      loadRuns(),
    ]);
    categories = catalog.categories || [];
    allDatasets = categories.flatMap((group) => group.datasets || []);
    populateCategories();
    renderCatalog();
    $('categoryCount').textContent = categories.length.toLocaleString('tr-TR');
    $('datasetCount').textContent = `${catalog.dataset_count.toLocaleString('tr-TR')} TÜİK veri seti`;
    $('datasetSearch').disabled = false;
    $('catalogCount').textContent = `${catalog.dataset_count} veri seti`;
    setConnection('Bağlantı kuruldu · anahtar sekme belleğinde', 'ok');
    setMessage('TÜİK kataloğu hazır. Kategori, veri seti ve yıl seçebilirsin.');
  } catch (error) {
    adminKey = '';
    setConnection(error.message, 'error');
    setMessage(error.message, 'error');
  } finally {
    $('connectButton').disabled = false;
    $('connectButton').textContent = 'Bağlan';
  }
}

function populateCategories() {
  const select = $('categorySelect');
  select.innerHTML = '<option value="">Kategori seç</option>' + categories.map((category) =>
    `<option value="${escapeHtml(category.id)}">${escapeHtml(category.name)} · ${category.datasets.length}</option>`
  ).join('');
  select.disabled = categories.length === 0;
  updateDatasets();
}

function updateDatasets(preferredId = '') {
  const categoryId = $('categorySelect').value;
  const query = $('datasetSearch').value.trim().toLocaleLowerCase('tr');
  const category = categories.find((item) => item.id === categoryId);
  const matches = (category?.datasets || []).filter((dataset) =>
    !query || `${dataset.title} ${dataset.id}`.toLocaleLowerCase('tr').includes(query)
  );
  const select = $('datasetSelect');
  if (!category) {
    select.innerHTML = '<option value="">Önce kategori seç</option>';
    select.disabled = true;
  } else {
    select.innerHTML = '<option value="">Veri seti seç</option>' + matches.slice(0, 250).map((dataset) =>
      `<option value="${escapeHtml(dataset.id)}" data-version="${escapeHtml(dataset.version)}">${escapeHtml(dataset.title)} (${escapeHtml(dataset.id)})</option>`
    ).join('');
    select.disabled = matches.length === 0;
    if (preferredId && matches.some((item) => item.id === preferredId)) select.value = preferredId;
    else if (matches.length === 1) select.value = matches[0].id;
  }
  renderCatalog();
  updateDatasetInfo();
  updateRunButton();
}

function selectedDataset() {
  const id = $('datasetSelect').value;
  return allDatasets.find((dataset) => dataset.id === id && dataset.category_id === $('categorySelect').value);
}

function updateDatasetInfo() {
  const dataset = selectedDataset();
  const info = $('datasetInfo');
  if (!dataset) {
    info.className = 'dataset-info empty-info';
    info.textContent = 'Katalog bağlantısı kurulduğunda veri seti bilgileri burada görünür.';
    return;
  }
  const pipeline = dataset.normalization === 'typed' ? 'RAW + typed staging' : 'RAW arşiv · staging eşlemesi bekliyor';
  info.className = 'dataset-info';
  info.innerHTML = `<strong>${escapeHtml(dataset.id)} · v${escapeHtml(dataset.version)}</strong> &nbsp; ${escapeHtml(pipeline)}`;
  updateRunButton();
}

function renderCatalog() {
  const query = $('datasetSearch').value.trim().toLocaleLowerCase('tr');
  const visibleCategories = categories.filter((category) => {
    if (!query) return true;
    return category.name.toLocaleLowerCase('tr').includes(query) ||
      category.datasets.some((dataset) => `${dataset.title} ${dataset.id}`.toLocaleLowerCase('tr').includes(query));
  });
  if (!categories.length) return;
  const icons = { demography: '♧', migration: '↗', prices: '◉', labor: '⌁', education: '▥', housing: '⌂', tourism: '✧', agriculture: '❋', health: '✚', trade: '⇄', economy: '◒', other: '▦' };
  $('catalogList').innerHTML = visibleCategories.slice(0, 30).map((category) => {
    const examples = category.datasets.slice(0, 2).map((item) => item.title).join(' · ');
    return `<button class="category-card ${category.id === $('categorySelect').value ? 'selected' : ''}" type="button" data-category="${escapeHtml(category.id)}">
      <span class="category-icon">${icons[category.id] || '▦'}</span>
      <span class="category-copy"><strong>${escapeHtml(category.name)}</strong><small>${escapeHtml(examples || 'Veri seti bulunamadı')}</small></span>
      <span class="category-total">${category.datasets.length}</span></button>`;
  }).join('') || '<div class="catalog-empty"><strong>Eşleşme bulunamadı</strong><span>Farklı bir arama dene.</span></div>';
  $('catalogList').querySelectorAll('[data-category]').forEach((button) => {
    button.addEventListener('click', () => {
      $('categorySelect').value = button.dataset.category;
      updateDatasets();
    });
  });
}

function setMessage(message, state = '') {
  $('runMessage').textContent = message;
  $('runMessage').className = `run-message ${state}`;
}

function updateRunButton() {
  const year = Number($('yearInput').value);
  $('runButton').disabled = !adminKey || !selectedDataset() || !Number.isInteger(year) || year < 1900 || year > 2100;
}

function statusLabel(status) {
  return ({ queued: 'Sırada', running: 'Çalışıyor', completed: 'Tamamlandı',
    succeeded: 'Tamamlandı', completed_with_issues: 'İnceleme gerekli', failed: 'Başarısız' })[status] || status || 'Bilinmiyor';
}

function statusClass(status) {
  return ['queued', 'running', 'completed', 'completed_with_issues', 'succeeded', 'failed'].includes(status) ? status : 'failed';
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(date);
}

function renderRuns(items) {
  if (!items?.length) {
    $('runRows').innerHTML = '<tr><td colspan="6" class="table-empty">Henüz TÜİK botu çalışmamış.</td></tr>';
    $('lastRun').textContent = '—';
    $('lastRunMeta').textContent = 'Henüz çalışma yok';
    $('recordCount').textContent = '—';
    $('recordMeta').textContent = 'TÜİK gözlemi';
    return;
  }
  const latest = items[0];
  $('lastRun').textContent = statusLabel(latest.status);
  $('lastRunMeta').textContent = `${latest.dataflow_title || latest.dataflow_id || 'TÜİK'} · ${latest.year || '—'}`;
  $('recordCount').textContent = latest.records == null ? '—' : Number(latest.records).toLocaleString('tr-TR');
  $('recordMeta').textContent = latest.normalization === 'typed' ? 'ham gözlem · staging eşleşti' : latest.normalization === 'raw_only' ? 'ham katmana yazıldı' : 'son çalışmadaki gözlem';
  $('runRows').innerHTML = items.map((run) => {
    const stage = run.normalization === 'typed' ? `${Number(run.staged_records || 0).toLocaleString('tr-TR')} kayıt` : run.normalization === 'raw_only' ? 'Eşleme bekliyor' : run.normalization === 'partial' ? `${Number(run.staged_records || 0).toLocaleString('tr-TR')} · kısmi` : '—';
    const detail = run.message ? `<small>${escapeHtml(run.message)}</small>` : `<small>${escapeHtml(run.dataflow_id || '')} · çalışma #${escapeHtml(run.run_id)}</small>`;
    return `<tr><td><div class="dataset-cell"><strong>${escapeHtml(run.dataflow_title || run.dataflow_id || 'TÜİK işi')}</strong>${detail}</div></td>
      <td>${escapeHtml(run.year ?? '—')}</td><td>${escapeHtml(formatDate(run.started_at))}</td>
      <td>${run.records == null ? '—' : Number(run.records).toLocaleString('tr-TR')}</td><td>${escapeHtml(stage)}</td>
      <td><span class="status-pill ${statusClass(run.status)}"><i></i>${escapeHtml(statusLabel(run.status))}</span></td></tr>`;
  }).join('');
}

async function loadRuns() {
  const result = await request(`${API}/runs?limit=20`);
  const items = result.items || [];
  renderRuns(items);
  if (items.some((item) => ['queued', 'running'].includes(item.status))) startPolling();
  else stopPolling();
  return items;
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(() => loadRuns().catch(() => {}), 3500);
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

async function startRun() {
  const dataset = selectedDataset();
  const year = Number($('yearInput').value);
  if (!dataset) return;
  $('runButton').disabled = true;
  $('runButton').innerHTML = '<span>…</span> Başlatılıyor';
  setMessage('İş kuyruğa alınıyor…');
  try {
    const result = await request(`${API}/runs`, {
      method: 'POST',
      body: JSON.stringify({ dataflow_id: dataset.id, version: dataset.version, year }),
    });
    setMessage(`Çalışma #${result.run_id} başlatıldı. Durum birkaç saniyede bir yenileniyor.`, 'success');
    await loadRuns();
    startPolling();
  } catch (error) {
    setMessage(error.message, 'error');
  } finally {
    $('runButton').innerHTML = '<span>▶</span> Şimdi veri çek';
    updateRunButton();
  }
}

$('connectButton').addEventListener('click', connect);
$('refreshButton').addEventListener('click', () => connect());
$('historyRefresh').addEventListener('click', () => loadRuns().catch((error) => setMessage(error.message, 'error')));
$('categorySelect').addEventListener('change', () => updateDatasets());
$('datasetSelect').addEventListener('change', updateDatasetInfo);
$('datasetSearch').addEventListener('input', () => updateDatasets());
$('yearInput').addEventListener('input', updateRunButton);
$('runButton').addEventListener('click', startRun);
$('adminKey').addEventListener('keydown', (event) => { if (event.key === 'Enter') connect(); });

if (window.location.protocol === 'file:') {
  setConnection('Dosya önizlemesi · veri çekmek için sunucu adresini aç.');
  $('adminKey').disabled = true;
  $('connectButton').disabled = true;
  $('connectButton').textContent = 'Sunucu gerekli';
  setMessage('Çalıştırılabilir panel: http://127.0.0.1:8000/admin/tuik/');
}
