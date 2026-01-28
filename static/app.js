/**
 * Macro Trading Terminal - JavaScript Application v3.1
 * Fixed: ETF Strip, Decoupled buttons, Chart intervals, Solid forecast line
 */

// Global state
const state = {
    calendar: null,
    currentIndicator: null,
    analysisResults: null,
    charts: {
        forecast: null,
        diff: null
    }
};

const API_BASE = '';

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    console.log("Initializing App...");
    setupEventListeners();

    // Load components in parallel without blocking main thread
    loadCalendar().then(() => console.log("Calendar loaded")).catch(e => console.error(e));
    loadMarketGlance().then(() => console.log("Market Glance loaded")).catch(e => console.error(e));
}

function setupEventListeners() {
    // Refresh calendar
    document.getElementById('refreshCalendar').addEventListener('click', loadCalendar);

    // Toggle calendar panel
    document.getElementById('toggleCalendar').addEventListener('click', toggleCalendarPanel);

    // Model type change
    document.getElementById('modelType').addEventListener('change', handleModelTypeChange);

    // Run Analysis (ONLY math models) - Fix 5
    document.getElementById('runAnalysis').addEventListener('click', runAnalysis);

    // AI Research button - Fix 5
    const runAiBtn = document.getElementById('runAiBtn');
    if (runAiBtn) runAiBtn.addEventListener('click', () => loadAIResearch());

    // Edit Query button - Fix 5
    const editQueryBtn = document.getElementById('editQueryBtn');
    if (editQueryBtn) editQueryBtn.addEventListener('click', openQueryModal);

    // Run Custom Query from Modal
    const saveQueryBtn = document.getElementById('saveQueryBtn');
    if (saveQueryBtn) saveQueryBtn.addEventListener('click', runCustomAIQuery);

    // Close Modal
    const closeModal = document.querySelector('.close-modal');
    if (closeModal) closeModal.addEventListener('click', () => {
        document.getElementById('queryModal').style.display = 'none';
    });

    // Period buttons - Fix 3
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', (e) => handlePeriodChange(e.target));
    });

    // RMSE band toggles
    ['show1SigmaUp', 'show1SigmaDown', 'show2SigmaUp', 'show2SigmaDown'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', updateForecastChart);
    });

    // Diff view toggles
    ['showActualDiff', 'showPredictedDiff'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', updateDiffChart);
    });

    // Refresh stocks data
    const refreshStocksBtn = document.getElementById('refreshStocks');
    if (refreshStocksBtn) refreshStocksBtn.addEventListener('click', refreshStocksData);

    // Refresh economic data
    const refreshEconomicBtn = document.getElementById('refreshEconomic');
    if (refreshEconomicBtn) refreshEconomicBtn.addEventListener('click', refreshEconomicData);
}

// ============================================
// REFRESH DATA FUNCTIONS
// ============================================

async function refreshStocksData() {
    const btn = document.getElementById('refreshStocks');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Updating...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/refresh/stocks`, { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            alert('Dane spółek S&P 500 zostały zaktualizowane!');
            await loadCalendar(); // Refresh calendar
        } else {
            alert('Błąd aktualizacji: ' + (data.message || 'Nieznany błąd'));
        }
    } catch (error) {
        console.error('Refresh stocks error:', error);
        alert('Błąd połączenia podczas aktualizacji danych spółek');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function refreshEconomicData() {
    const btn = document.getElementById('refreshEconomic');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Updating...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/refresh/economic`, { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            alert('Kalendarz ekonomiczny został zaktualizowany!');
            await loadCalendar(); // Refresh calendar
        } else {
            alert('Błąd aktualizacji: ' + (data.message || 'Nieznany błąd'));
        }
    } catch (error) {
        console.error('Refresh economic error:', error);
        alert('Błąd połączenia podczas aktualizacji kalendarza ekonomicznego');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function toggleCalendarPanel() {
    const panel = document.getElementById('calendarPanel');
    const btn = document.getElementById('toggleCalendar');
    panel.classList.toggle('collapsed');
    btn.textContent = panel.classList.contains('collapsed') ? '▶' : '◀';
}

function handleModelTypeChange() {
    const modelType = document.getElementById('modelType').value;
    document.getElementById('arimaParams').style.display = modelType === 'ARIMA' ? 'flex' : 'none';
    document.getElementById('maParams').style.display = modelType === 'MovingAverage' ? 'block' : 'none';
    document.getElementById('mcParams').style.display = modelType === 'MonteCarlo' ? 'block' : 'none';
}

// ============================================
// FIX 8: MARKET GLANCE (ETF STRIP)
// ============================================

async function loadMarketGlance() {
    const container = document.getElementById('marketGlance');
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/api/market_glance`);
        const data = await response.json();

        container.innerHTML = '';

        for (const [ticker, info] of Object.entries(data)) {
            const isPositive = info.change >= 0;
            const changeColor = isPositive ? '#059669' : '#dc2626';

            const item = document.createElement('div');
            item.className = 'glance-item';
            item.innerHTML = `
                <div class="glance-header">
                    <span>${ticker}</span>
                    <span class="glance-change ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '▲' : '▼'} ${Math.abs(info.change).toFixed(2)}%
                    </span>
                </div>
                <div class="glance-price">$${info.price.toFixed(2)}</div>
                <canvas id="spark_${ticker}" class="glance-chart" width="100" height="30"></canvas>
            `;
            container.appendChild(item);

            // Render sparkline after element is in DOM
            setTimeout(() => renderSparkline(`spark_${ticker}`, info.data, changeColor), 10);
        }
    } catch (error) {
        console.error('Market glance error:', error);
        container.innerHTML = '<span style="font-size:12px; color:#666; padding:10px;">Market data unavailable</span>';
    }
}

function renderSparkline(canvasId, data, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                data: data,
                borderColor: color,
                borderWidth: 1.5,
                tension: 0.2,
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: { x: { display: false }, y: { display: false } },
            layout: { padding: 2 }
        }
    });
}

// ============================================
// CALENDAR
// ============================================

async function loadCalendar() {
    const loading = document.getElementById('calendarLoading');
    const list = document.getElementById('calendarList');

    loading.style.display = 'flex';
    list.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/api/calendar`);
        const data = await response.json();
        state.calendar = data;
        renderCalendar(data);
    } catch (error) {
        console.error('Error loading calendar:', error);
        list.innerHTML = `<p class="placeholder-text">Error loading calendar data. Reference: ${error.message}</p>`;
    } finally {
        console.log("Hiding calendar loading spinner...");
        loading.style.display = 'none';
    }
}

function renderCalendar(calendar) {
    const list = document.getElementById('calendarList');
    list.innerHTML = '';

    for (const [dateKey, indicators] of Object.entries(calendar)) {
        // Date header
        const dateHeader = document.createElement('div');
        dateHeader.className = 'calendar-date-header';
        dateHeader.innerHTML = `<h3>${formatDateKey(dateKey)}</h3>`;
        list.appendChild(dateHeader);

        for (const indicator of indicators) {
            if (!indicator || !indicator.series_id) {
                console.warn('Skipping invalid indicator:', indicator);
                continue;
            }
            const dataType = indicator.type || 'fred';
            const tileId = `tile-${indicator.series_id.replace(/[^a-zA-Z0-9]/g, '_')}`;

            // Create expandable tile using <details>
            const details = document.createElement('details');
            details.className = `expandable-tile tile-${dataType}`;
            details.id = tileId;

            // Summary (always visible header)
            let subLabel = indicator.series_id;
            if (dataType === 'stock') {
                subLabel = `${indicator.market_cap || ''} • ${indicator.ticker}`;
            } else if (dataType === 'economic') {
                subLabel = `${indicator.time || ''} • ${indicator.category || ''}`;
            }

            const summary = document.createElement('summary');
            summary.className = 'tile-header';
            summary.innerHTML = `
                <div class="tile-info">
                    <span class="tile-name">${indicator.display_name || indicator.name}</span>
                    <span class="tile-sublabel">${subLabel}</span>
                </div>
                <span class="tile-expand-icon">▼</span>
            `;
            details.appendChild(summary);

            // Expandable content
            const content = document.createElement('div');
            content.className = 'tile-content';
            content.dataset.seriesId = indicator.series_id;
            content.dataset.type = dataType;

            if (dataType === 'fred') {
                // FRED indicator - full analysis layout
                content.innerHTML = `
                    <div class="tile-layout">
                        <div class="tile-main">
                            <!-- Config Bar -->
                            <div class="tile-config-bar">
                                <div class="config-group">
                                    <label>MODEL</label>
                                    <select class="model-type-select">
                                        <option value="ARIMA">ARIMA</option>
                                        <option value="MovingAverage">Moving Average</option>
                                        <option value="MonteCarlo">Monte Carlo</option>
                                    </select>
                                </div>
                                <div class="config-group arima-params">
                                    <label>ORDER (P,D,Q)</label>
                                    <input type="number" class="order-p" value="1" min="0" max="5">
                                    <input type="number" class="order-d" value="1" min="0" max="2">
                                    <input type="number" class="order-q" value="1" min="0" max="5">
                                </div>
                                <div class="config-group">
                                    <label>TEST</label>
                                    <input type="number" class="n-test" value="12" min="1" max="36">
                                </div>
                                <div class="config-group">
                                    <label>FORECAST</label>
                                    <input type="number" class="h-future" value="6" min="1" max="24">
                                </div>
                                <button class="btn btn-primary btn-run-analysis">Run Model Analysis</button>
                            </div>
                            
                            <!-- Stats -->
                            <div class="tile-stats">
                                <h4>Model Statistics</h4>
                                <div class="stats-grid"></div>
                            </div>

                            <!-- Chart -->
                            <div class="tile-chart-card">
                                <div class="tile-chart-header">
                                    <h4>Historical + Forecast</h4>
                                    <div class="chart-period-selector">
                                        <button class="period-btn active" data-period="12">12 Obs</button>
                                        <button class="period-btn" data-period="24">24 Obs</button>
                                        <button class="period-btn" data-period="60">60 Obs</button>
                                        <button class="period-btn" data-period="0">Max</button>
                                    </div>
                                </div>
                                <div class="tile-chart-container">
                                    <canvas class="forecast-chart"></canvas>
                                </div>
                            </div>

                            <!-- Diff Chart (Added) -->
                            <div class="tile-chart-card">
                                <div class="tile-chart-header">
                                    <h4>Difference (Actual vs Predicted)</h4>
                                </div>
                                <div class="tile-chart-container" style="height: 150px;">
                                    <canvas class="diff-chart"></canvas>
                                </div>
                            </div>
                            
                            <!-- ETF Correlation -->
                            <div class="tile-correlation">
                                <h4>ETF Correlation Heatmap</h4>
                                <div class="heatmap-container"></div>
                            </div>
                        </div>
                        
                        <div class="tile-sidebar">
                            <div class="tile-ai-section">
                                <div class="ai-header">
                                    <h4>AI Research</h4>
                                    <button class="btn btn-primary btn-xs btn-run-ai">Run AI</button>
                                </div>
                                <div class="ai-content">
                                    <p class="placeholder-text">Click "Run AI" to generate research</p>
                                </div>
                            </div>
                            <div class="tile-quality">
                                <h4>Model Quality</h4>
                                <div class="quality-content">
                                    <p class="placeholder-text">Run analysis to see assessment</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (dataType === 'stock') {
                // Stock - summary + Yahoo Finance chart
                content.innerHTML = `
                    <div class="tile-layout">
                        <div class="tile-main">
                            <div class="tile-stock-summary">
                                <div class="summary-grid">
                                    <div class="summary-item">
                                        <span class="summary-label">Market Cap</span>
                                        <span class="summary-value">${indicator.market_cap || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Price</span>
                                        <span class="summary-value">${indicator.price || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Change</span>
                                        <span class="summary-value ${parseFloat(indicator.change_pct) >= 0 ? 'positive' : 'negative'}">${indicator.change_pct || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Price Target</span>
                                        <span class="summary-value">${indicator.price_target || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Revenue</span>
                                        <span class="summary-value">${indicator.revenue || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Analyst Rating</span>
                                        <span class="summary-value">${indicator.analysts || 'N/A'}</span>
                                    </div>
                                </div>
                                ${indicator.link ? `<a href="${indicator.link}" target="_blank" class="external-link-btn">View →</a>` : ''}
                            </div>
                            
                            <!-- Yahoo Finance Chart -->
                            <div class="tile-chart-card">
                                <div class="tile-chart-header">
                                    <h4>Stock Price (1Y)</h4>
                                </div>
                                <div class="tile-chart-container stock-chart-container">
                                    <canvas class="stock-chart"></canvas>
                                </div>
                            </div>
                        </div>
                        
                        <div class="tile-sidebar">
                            <div class="tile-ai-section">
                                <div class="ai-header">
                                    <h4>AI Research</h4>
                                    <button class="btn btn-primary btn-xs btn-run-ai">Run AI</button>
                                </div>
                                <div class="ai-content">
                                    <p class="placeholder-text">Click "Run AI" to generate research</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // Economic event - summary only
                content.innerHTML = `
                    <div class="tile-layout">
                        <div class="tile-main">
                            <div class="tile-economic-summary">
                                <div class="summary-grid">
                                    <div class="summary-item">
                                        <span class="summary-label">Date</span>
                                        <span class="summary-value">${indicator.sort_date || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Time</span>
                                        <span class="summary-value">${indicator.time || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Country</span>
                                        <span class="summary-value">${indicator.country || 'N/A'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Actual</span>
                                        <span class="summary-value">${indicator.actual || '-'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Previous</span>
                                        <span class="summary-value">${indicator.previous || '-'}</span>
                                    </div>
                                    <div class="summary-item">
                                        <span class="summary-label">Consensus</span>
                                        <span class="summary-value">${indicator.consensus || '-'}</span>
                                    </div>
                                </div>
                                ${indicator.link ? `<a href="${indicator.link}" target="_blank" class="external-link-btn">View →</a>` : ''}
                            </div>
                        </div>
                        
                        <div class="tile-sidebar">
                            <div class="tile-ai-section">
                                <div class="ai-header">
                                    <h4>AI Research</h4>
                                    <button class="btn btn-primary btn-xs btn-run-ai">Run AI</button>
                                </div>
                                <div class="ai-content">
                                    <p class="placeholder-text">Click "Run AI" to generate research</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }

            try {
                details.appendChild(content);

                // Event listeners for this tile
                details.addEventListener('toggle', () => {
                    if (details.open) {
                        state.currentIndicator = indicator;
                        initializeTileContent(content, indicator);
                    }
                });

                list.appendChild(details);
            } catch (tileError) {
                console.error('Error rendering individual tile:', tileError, indicator);
            }
        }
    }
}

// Initialize content when tile is expanded
async function initializeTileContent(content, indicator) {
    const dataType = indicator.type || 'fred';

    // Setup Run Analysis button for FRED
    if (dataType === 'fred') {
        const runBtn = content.querySelector('.btn-run-analysis');
        if (runBtn) {
            runBtn.onclick = () => runTileAnalysis(content, indicator);
        }

        // Load correlation
        loadTileCorrelation(content, indicator.series_id);

        // AUTO-LOAD PRECOMPUTED BEST MODEL
        loadPrecomputedModel(content, indicator);
    }

    // Setup Run AI button
    const aiBtn = content.querySelector('.btn-run-ai');
    if (aiBtn) {
        aiBtn.onclick = () => runTileAI(content, indicator);
    }

    // Load stock chart if stock type
    if (dataType === 'stock' && indicator.ticker) {
        loadTileStockChart(content, indicator.ticker);
    }
}

// Load precomputed best model for FRED indicator
async function loadPrecomputedModel(content, indicator) {
    const chartContainer = content.querySelector('.tile-chart-container');
    const statsGrid = content.querySelector('.stats-grid');
    const qualityContent = content.querySelector('.quality-content');

    if (!chartContainer) return;

    // Show loading state
    chartContainer.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><span>Loading best model...</span></div>';

    try {
        const response = await fetch(`${API_BASE}/api/precomputed/${indicator.series_id}`);
        const data = await response.json();

        if (data.error) {
            chartContainer.innerHTML = `<p class="placeholder-text">Model not ready: ${data.error}</p>`;
            return;
        }

        // Restore canvas
        chartContainer.innerHTML = '<canvas class="forecast-chart"></canvas>';

        // Render results
        if (data.result) {
            const result = data.result;
            // state.currentIndicator = indicator; // Don't overwrite global state unnecessarily
            state.analysisResults = result;
            state.fullChartData = { historical: result.historical, forecast: result.forecast };

            // Render chart
            renderTileForecastChart(content, result, 12); // Default to 12

            // Setup period buttons
            content.querySelectorAll('.period-btn').forEach(btn => {
                btn.onclick = () => {
                    content.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const canvas = content.querySelector('.forecast-chart');
                    if (canvas && canvas._fullData) {
                        renderTileForecastChart(content, canvas._fullData, parseInt(btn.dataset.period));
                    }
                };
            });

            // Render diff chart if present
            if (result.comparison) {
                renderTileDiffChart(content, result);
            }

            // Render stats
            if (statsGrid && result.stats) {
                const modelType = data.best_model || 'ARIMA';
                const stats = result.stats;
                statsGrid.innerHTML = `
                    <div class="stat-item"><div class="stat-value best-model">${modelType}</div><div class="stat-label">Best Model</div></div>
                    <div class="stat-item"><div class="stat-value">${stats.RMSE?.toFixed(4) || '--'}</div><div class="stat-label">RMSE</div></div>
                    <div class="stat-item"><div class="stat-value">${stats.MAPE?.toFixed(2) || '--'}%</div><div class="stat-label">MAPE</div></div>
                    <div class="stat-item"><div class="stat-value">${stats.MAE?.toFixed(4) || '--'}</div><div class="stat-label">MAE</div></div>
                `;
            }

            // Render quality
            if (qualityContent && result.opinion) {
                let formatted = result.opinion
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>')
                    .replace(/✅/g, '<span style="color: #059669">✓</span>')
                    .replace(/⚠️/g, '<span style="color: #d97706">⚠</span>')
                    .replace(/❌/g, '<span style="color: #dc2626">✗</span>');
                qualityContent.innerHTML = `<div>${formatted}</div>`;
            }
        }
    } catch (error) {
        console.error('Error loading precomputed model:', error);
        chartContainer.innerHTML = '<canvas class="forecast-chart"></canvas>';
    }
}

function formatDateKey(dateKey) {
    if (dateKey === '9999-12-31') return 'Upcoming / TBD';
    if (dateKey === 'TBD' || dateKey === 'Error') return dateKey;

    try {
        const date = new Date(dateKey);
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric'
        });
    } catch {
        return dateKey;
    }
}

// ============================================
// INDICATOR SELECTION
// ============================================

function selectIndicator(indicator) {
    state.currentIndicator = indicator;
    const dataType = indicator.type || 'fred';

    document.querySelectorAll('.calendar-indicator').forEach(el => {
        el.classList.toggle('active', el.dataset.seriesId === indicator.series_id);
    });

    document.getElementById('placeholder').style.display = 'none';
    document.getElementById('indicatorDetail').style.display = 'block';

    // Hide Daily AI panel if open
    const dailyAIMainPanel = document.getElementById('dailyAIMainPanel');
    if (dailyAIMainPanel) dailyAIMainPanel.style.display = 'none';

    document.getElementById('indicatorName').textContent = indicator.display_name || indicator.name;
    document.getElementById('nextRelease').textContent = indicator.release_text || '--';
    document.getElementById('seriesId').textContent = indicator.series_id;

    // Pobierz referencje do sekcji
    const configBar = document.querySelector('.config-bar');
    const fredLink = document.getElementById('fredLink');
    const summaryContainer = document.getElementById('dataSummary');
    const chartCards = document.querySelectorAll('.chart-card');
    const statsCard = document.querySelector('.stats-card');
    const qualityCard = document.querySelector('.quality-card');

    if (dataType === 'stock') {
        // Stock - hide ARIMA panel, hide chart sections, show summary
        if (configBar) configBar.style.display = 'none';
        chartCards.forEach(card => card.style.display = 'none');
        if (statsCard) statsCard.style.display = 'none';
        if (qualityCard) qualityCard.style.display = 'none';
        fredLink.href = indicator.link || '#';
        fredLink.textContent = 'View →';
        renderStockSummary(indicator);
        // Load Yahoo Finance chart for stock
        if (indicator.ticker) {
            loadStockChart(indicator.ticker);
        }
    } else if (dataType === 'economic') {
        // Economic calendar - hide ARIMA panel and charts, show summary only
        if (configBar) configBar.style.display = 'none';
        chartCards.forEach(card => card.style.display = 'none');
        if (statsCard) statsCard.style.display = 'none';
        if (qualityCard) qualityCard.style.display = 'none';
        if (indicator.link) {
            fredLink.href = indicator.link;
            fredLink.textContent = 'View →';
        } else {
            fredLink.href = '#';
            fredLink.textContent = '';
        }
        renderEconomicSummary(indicator);
        // Hide stock chart for economic events
        hideStockChart();
    } else {
        // FRED indicator - show ARIMA panel and all chart sections
        if (configBar) configBar.style.display = 'flex';
        chartCards.forEach(card => card.style.display = 'block');
        if (statsCard) statsCard.style.display = 'block';
        if (qualityCard) qualityCard.style.display = 'block';
        fredLink.href = `https://fred.stlouisfed.org/series/${indicator.series_id}`;
        fredLink.textContent = 'View on FRED →';
        // Hide summary for FRED
        if (summaryContainer) summaryContainer.style.display = 'none';
        // Hide stock chart
        hideStockChart();
    }

    resetResults();
}

function renderStockSummary(stock) {
    const container = document.getElementById('dataSummary');
    if (!container) return;

    container.style.display = 'block';
    container.className = 'data-summary stock-summary';
    container.innerHTML = `
        <div class="summary-header">
            <h4>${stock.ticker} - Stock Summary</h4>
        </div>
        <div class="summary-grid">
            <div class="summary-item">
                <span class="summary-label">Market Cap</span>
                <span class="summary-value">${stock.market_cap || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Price</span>
                <span class="summary-value">${stock.price || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Change</span>
                <span class="summary-value ${parseFloat(stock.change_pct) >= 0 ? 'positive' : 'negative'}">${stock.change_pct || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Price Target</span>
                <span class="summary-value">${stock.price_target || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Revenue</span>
                <span class="summary-value">${stock.revenue || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Analyst Rating</span>
                <span class="summary-value analyst-rating">${stock.analysts || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Earnings Date</span>
                <span class="summary-value">${stock.release_text || 'N/A'}</span>
            </div>
        </div>
        ${stock.link ? `<a href="${stock.link}" target="_blank" class="external-link-btn">View →</a>` : ''}
    `;
}

function renderEconomicSummary(event) {
    const container = document.getElementById('dataSummary');
    if (!container) return;

    container.style.display = 'block';
    container.className = 'data-summary economic-summary';
    container.innerHTML = `
        <div class="summary-header">
            <h4>Economic Event</h4>
        </div>
        <div class="summary-grid">
            <div class="summary-item">
                <span class="summary-label">Date</span>
                <span class="summary-value">${event.sort_date || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Time</span>
                <span class="summary-value">${event.time || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Country</span>
                <span class="summary-value">${event.country || 'N/A'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Actual</span>
                <span class="summary-value">${event.actual || '-'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Previous</span>
                <span class="summary-value">${event.previous || '-'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Consensus</span>
                <span class="summary-value">${event.consensus || '-'}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Forecast</span>
                <span class="summary-value">${event.forecast || '-'}</span>
            </div>
        </div>
        ${event.link ? `<a href="${event.link}" target="_blank" class="external-link-btn">View →</a>` : ''}
    `;
}

function resetResults() {
    if (state.charts.forecast) {
        state.charts.forecast.destroy();
        state.charts.forecast = null;
    }
    if (state.charts.diff) {
        state.charts.diff.destroy();
        state.charts.diff = null;
    }

    document.getElementById('statsGrid').innerHTML = '';
    document.getElementById('correlationHeatmap').innerHTML = '';
    document.getElementById('modelQuality').innerHTML = '<p class="placeholder-text">Run analysis to see assessment</p>';
    document.getElementById('aiContent').innerHTML = '<p class="placeholder-text">Click "Run AI" to generate research</p>';
    document.getElementById('aiSources').style.display = 'none';
}

// ============================================
// ANALYSIS (MATH MODEL ONLY - FIX 5)
// ============================================

async function runAnalysis() {
    if (!state.currentIndicator) {
        alert('Please select an indicator first.');
        return;
    }

    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';
    document.getElementById('loadingText').textContent = 'Running analysis...';

    try {
        const modelType = document.getElementById('modelType').value;
        const params = getModelParams(modelType);

        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                series_id: state.currentIndicator.series_id,
                model_type: modelType,
                ...params
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Analysis failed');
        }

        const analysisData = await response.json();
        state.analysisResults = analysisData;

        renderForecastChart(analysisData);
        renderDiffChart(analysisData);
        renderStats(analysisData, modelType);
        renderModelQuality(analysisData);

        // Load correlation (separate, doesn't cost money)
        loadCorrelation();

    } catch (error) {
        console.error('Analysis error:', error);
        alert('Analysis Error: ' + error.message);
    } finally {
        overlay.style.display = 'none';
    }
}

function getModelParams(modelType) {
    const nTest = parseInt(document.getElementById('nTest').value);
    const hFuture = parseInt(document.getElementById('hFuture').value);

    switch (modelType) {
        case 'ARIMA':
            return {
                order: [
                    parseInt(document.getElementById('paramP').value),
                    parseInt(document.getElementById('paramD').value),
                    parseInt(document.getElementById('paramQ').value)
                ],
                n_test: nTest,
                h_future: hFuture
            };
        case 'MovingAverage':
            return {
                windows: document.getElementById('maWindows').value.split(',').map(w => parseInt(w.trim())),
                n_test: nTest,
                h_future: hFuture
            };
        case 'MonteCarlo':
            return {
                simulations: parseInt(document.getElementById('mcSims').value),
                n_test: nTest,
                h_future: hFuture
            };
    }
}

// ============================================
// CHARTS - FIX 3 (Intervals) & FIX 4 (Solid Line)
// ============================================

function renderForecastChart(data) {
    console.log('renderForecastChart called', data);
    const ctx = document.getElementById('forecastChart').getContext('2d');

    if (state.charts.forecast) {
        state.charts.forecast.destroy();
    }

    const historical = data.historical;
    const forecast = data.forecast;

    console.log('Historical dates:', historical?.dates?.length, 'Forecast dates:', forecast?.dates?.length);

    // Store for period filtering
    state.fullChartData = { historical, forecast };

    // Combine dates and values
    const allDates = [...historical.dates, ...forecast.dates];
    const historicalValues = [...historical.values, ...Array(forecast.dates.length).fill(null)];
    const forecastValues = [...Array(historical.dates.length - 1).fill(null), historical.values[historical.values.length - 1], ...forecast.values];

    state.charts.forecast = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'Historical',
                    data: historicalValues,
                    borderColor: '#374151',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1
                },
                {
                    label: 'Forecast',
                    data: forecastValues,
                    borderColor: '#1a56db',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0, // FIX 4: Solid line instead of dots
                    tension: 0.1
                },
                {
                    label: '+2σ RMSE',
                    data: [...Array(historical.dates.length).fill(null), ...forecast.sigma_2_up],
                    borderColor: 'rgba(26, 86, 219, 0.2)',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: '+1σ RMSE',
                    data: [...Array(historical.dates.length).fill(null), ...forecast.sigma_1_up],
                    borderColor: 'rgba(26, 86, 219, 0.4)',
                    backgroundColor: 'rgba(26, 86, 219, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1'
                },
                {
                    label: '-1σ RMSE',
                    data: [...Array(historical.dates.length).fill(null), ...forecast.sigma_1_down],
                    borderColor: 'rgba(26, 86, 219, 0.4)',
                    backgroundColor: 'rgba(26, 86, 219, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '-1'
                },
                {
                    label: '-2σ RMSE',
                    data: [...Array(historical.dates.length).fill(null), ...forecast.sigma_2_down],
                    borderColor: 'rgba(26, 86, 219, 0.2)',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'white',
                    titleColor: '#1f2937',
                    bodyColor: '#6b7280',
                    borderColor: '#e5e7eb',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: { maxTicksLimit: 8, font: { size: 10 } }
                },
                y: {
                    display: true,
                    grid: { color: '#f3f4f6' },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });
}

function updateForecastChart() {
    if (!state.charts.forecast || !state.analysisResults) return;

    const show1Up = document.getElementById('show1SigmaUp').checked;
    const show1Down = document.getElementById('show1SigmaDown').checked;
    const show2Up = document.getElementById('show2SigmaUp').checked;
    const show2Down = document.getElementById('show2SigmaDown').checked;

    state.charts.forecast.data.datasets[2].hidden = !show2Up;
    state.charts.forecast.data.datasets[3].hidden = !show1Up;
    state.charts.forecast.data.datasets[4].hidden = !show1Down;
    state.charts.forecast.data.datasets[5].hidden = !show2Down;

    state.charts.forecast.update();
}

// FIX 3: Handle Period Change - OBSERVATION-BASED FILTERING
function handlePeriodChange(btn) {
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (!state.analysisResults || !state.fullChartData) return;

    const periodValue = parseInt(btn.dataset.period);
    const { historical, forecast } = state.fullChartData;

    let histStart = 0;
    if (periodValue > 0) {
        // Treat as number of observations (as per plan.md requirements)
        histStart = Math.max(0, historical.dates.length - periodValue);
    }

    const slicedHistDates = historical.dates.slice(histStart);
    const slicedHistValues = historical.values.slice(histStart);

    // Rebuild chart with sliced data
    const allDates = [...slicedHistDates, ...forecast.dates];
    const historicalValues = [...slicedHistValues, ...Array(forecast.dates.length).fill(null)];
    const forecastValues = [...Array(slicedHistDates.length - 1).fill(null), slicedHistValues[slicedHistValues.length - 1], ...forecast.values];

    let chartToUpdate = state.charts.forecast;

    // Check if this is a tile-specific chart (for expandable tiles)
    const tileContent = btn.closest('.tile-content');
    if (tileContent) {
        const canvas = tileContent.querySelector('.forecast-chart');
        chartToUpdate = Chart.getChart(canvas);
    }

    if (chartToUpdate) {
        chartToUpdate.data.labels = allDates;
        chartToUpdate.data.datasets[0].data = historicalValues;
        chartToUpdate.data.datasets[1].data = forecastValues;
        chartToUpdate.data.datasets[2].data = [...Array(slicedHistDates.length).fill(null), ...forecast.sigma_2_up];
        chartToUpdate.data.datasets[3].data = [...Array(slicedHistDates.length).fill(null), ...forecast.sigma_1_up];
        chartToUpdate.data.datasets[4].data = [...Array(slicedHistDates.length).fill(null), ...forecast.sigma_1_down];
        chartToUpdate.data.datasets[5].data = [...Array(slicedHistDates.length).fill(null), ...forecast.sigma_2_down];
        chartToUpdate.update();
    }
}

function renderDiffChart(data) {
    const ctx = document.getElementById('diffChart').getContext('2d');

    if (state.charts.diff) {
        state.charts.diff.destroy();
    }

    const comparison = data.comparison;

    state.charts.diff = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: comparison.dates,
            datasets: [
                {
                    label: 'Actual Diff',
                    data: comparison.actual_diff,
                    backgroundColor: 'rgba(5, 150, 105, 0.7)',
                    borderColor: '#059669',
                    borderWidth: 1
                },
                {
                    label: 'Predicted Diff',
                    data: comparison.predict_diff,
                    backgroundColor: 'rgba(26, 86, 219, 0.7)',
                    borderColor: '#1a56db',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: true, grid: { display: false }, ticks: { font: { size: 9 } } },
                y: { display: true, grid: { color: '#f3f4f6' }, ticks: { font: { size: 9 } } }
            }
        }
    });
}

function updateDiffChart() {
    if (!state.charts.diff) return;
    const showActual = document.getElementById('showActualDiff').checked;
    const showPredicted = document.getElementById('showPredictedDiff').checked;
    state.charts.diff.data.datasets[0].hidden = !showActual;
    state.charts.diff.data.datasets[1].hidden = !showPredicted;
    state.charts.diff.update();
}

// ============================================
// STATS & QUALITY
// ============================================

function renderStats(data, modelType) {
    const grid = document.getElementById('statsGrid');
    const stats = data.stats;

    let html = '';
    if (modelType === 'ARIMA') {
        html = `
            <div class="stat-item"><div class="stat-value">${stats.AIC?.toFixed(2) || '--'}</div><div class="stat-label">AIC</div></div>
            <div class="stat-item"><div class="stat-value">${stats.BIC?.toFixed(2) || '--'}</div><div class="stat-label">BIC</div></div>
            <div class="stat-item"><div class="stat-value">${stats.MAE?.toFixed(4) || '--'}</div><div class="stat-label">MAE</div></div>
            <div class="stat-item"><div class="stat-value">${stats.RMSE?.toFixed(4) || '--'}</div><div class="stat-label">RMSE</div></div>
            <div class="stat-item"><div class="stat-value">${stats.MAPE?.toFixed(2) || '--'}%</div><div class="stat-label">MAPE</div></div>
        `;
    } else if (modelType === 'MovingAverage') {
        html = `
            <div class="stat-item"><div class="stat-value">${stats.MAE?.toFixed(4) || '--'}</div><div class="stat-label">MAE</div></div>
            <div class="stat-item"><div class="stat-value">${stats.RMSE?.toFixed(4) || '--'}</div><div class="stat-label">RMSE</div></div>
            <div class="stat-item"><div class="stat-value">${stats.Windows?.join(',') || '--'}</div><div class="stat-label">Windows</div></div>
        `;
    } else {
        html = `
            <div class="stat-item"><div class="stat-value">${((stats['Mean Return'] || 0) * 100).toFixed(2)}%</div><div class="stat-label">Mean Return</div></div>
            <div class="stat-item"><div class="stat-value">${((stats.Volatility || 0) * 100).toFixed(2)}%</div><div class="stat-label">Volatility</div></div>
            <div class="stat-item"><div class="stat-value">${stats.MAE?.toFixed(4) || '--'}</div><div class="stat-label">MAE</div></div>
            <div class="stat-item"><div class="stat-value">${stats.RMSE?.toFixed(4) || '--'}</div><div class="stat-label">RMSE</div></div>
        `;
    }
    grid.innerHTML = html;
}

function renderModelQuality(data) {
    const container = document.getElementById('modelQuality');
    const opinion = data.opinion || 'No assessment available';

    let formatted = opinion
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/✅/g, '<span style="color: #059669">✓</span>')
        .replace(/⚠️/g, '<span style="color: #d97706">⚠</span>')
        .replace(/❌/g, '<span style="color: #dc2626">✗</span>');

    container.innerHTML = `<div>${formatted}</div>`;
}

// ============================================
// CORRELATION HEATMAP - FIX 9 (Beta)
// ============================================

async function loadCorrelation() {
    if (!state.currentIndicator) return;

    const container = document.getElementById('correlationHeatmap');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><span>Loading...</span></div>';

    try {
        const response = await fetch(`${API_BASE}/api/correlation/${state.currentIndicator.series_id}`);
        const data = await response.json();
        renderHeatmap(data);
    } catch (error) {
        console.error('Correlation error:', error);
        container.innerHTML = '<p class="placeholder-text">Error loading correlation</p>';
    }
}

function renderHeatmap(correlations) {
    const container = document.getElementById('correlationHeatmap');

    if (!correlations || Object.keys(correlations).length === 0) {
        container.innerHTML = '<p class="placeholder-text">No correlation data available</p>';
        return;
    }

    let html = '<div class="heatmap-grid">';

    for (const [ticker, data] of Object.entries(correlations)) {
        // Handle both old format (number) and new format (object with correlation and beta)
        let corr = typeof data === 'number' ? data : (data?.correlation ?? 0);
        let beta = typeof data === 'object' ? (data?.beta ?? null) : null;

        // Safety check for invalid values
        if (corr === null || corr === undefined || isNaN(corr)) {
            corr = 0;
        }

        const bgColor = getHeatmapColor(corr);
        const corrDisplay = corr.toFixed(2);
        const betaDisplay = beta !== null && !isNaN(beta) ? beta.toFixed(2) : '--';

        // Determine trend indicator
        const trendIcon = corr > 0.3 ? '↗' : corr < -0.3 ? '↘' : '→';
        const trendColor = corr > 0.3 ? '#059669' : corr < -0.3 ? '#dc2626' : '#6b7280';

        html += `
            <div class="heatmap-cell">
                <div class="heatmap-ticker">${ticker}</div>
                <div class="heatmap-corr" style="background-color: ${bgColor};">${corrDisplay}</div>
                <div class="heatmap-beta">
                    <span class="beta-label">β</span>
                    <span class="beta-value">${betaDisplay}</span>
                    <span class="trend-icon" style="color: ${trendColor}">${trendIcon}</span>
                </div>
            </div>
        `;
    }

    html += '</div>';
    container.innerHTML = html;
}

function getHeatmapColor(value) {
    if (value >= 0) {
        const intensity = Math.round(value * 200);
        return `rgb(${26}, ${86 + intensity / 2}, ${219})`;
    } else {
        const intensity = Math.round(Math.abs(value) * 200);
        return `rgb(${220}, ${38 + intensity / 2}, ${38})`;
    }
}

// ============================================
// AI RESEARCH - FIX 5 (POST endpoint)
// ============================================

function openQueryModal() {
    const modal = document.getElementById('queryModal');
    const input = document.getElementById('customQueryInput');

    if (!input.value && state.currentIndicator) {
        input.value = `Analyze the outlook for ${state.currentIndicator.display_name || state.currentIndicator.name}`;
    }
    modal.style.display = 'flex';
}

async function runCustomAIQuery() {
    const modal = document.getElementById('queryModal');
    modal.style.display = 'none';
    await loadAIResearch(document.getElementById('customQueryInput').value);
}

async function loadAIResearch(customQuery = null) {
    if (!state.currentIndicator) {
        alert('Please select an indicator first.');
        return;
    }

    const content = document.getElementById('aiContent');
    const sources = document.getElementById('aiSources');
    const loading = document.getElementById('aiLoading');

    loading.style.display = 'flex';
    content.innerHTML = '';
    sources.style.display = 'none';

    try {
        // Use POST endpoint with query
        const response = await fetch(`${API_BASE}/api/research`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                series_id: state.currentIndicator.series_id,
                query: customQuery
            })
        });

        const data = await response.json();

        if (data.outlook === 'ERROR') {
            content.innerHTML = `<p class="placeholder-text">${data.summary}</p>`;
        } else {
            let summary = data.summary
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>')
                .replace(/- /g, '• ');

            content.innerHTML = `<p>${summary}</p>`;

            if (data.sources && data.sources.length > 0) {
                const sourcesList = document.getElementById('sourcesList');
                sourcesList.innerHTML = data.sources.map(s => `<li>${s}</li>`).join('');
                sources.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('AI Research error:', error);
        content.innerHTML = '<p class="placeholder-text">Error loading research</p>';
    } finally {
        loading.style.display = 'none';
    }
}

// News functionality removed as per plan.md requirements

// ============================================
// PANEL TABS REMOVED - NEW DAILY AI LOGIC
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    setupDailyAIPanel();
});

function setupDailyAIPanel() {
    const openBtn = document.getElementById('openDailyAI');
    const closeBtn = document.getElementById('closeDailyAI');
    const mainPanel = document.getElementById('dailyAIMainPanel');
    const indicatorView = document.getElementById('indicatorView'); // Contains placeholder and indicator details

    if (openBtn && mainPanel) {
        openBtn.addEventListener('click', () => {
            // New logic: hide calendar, show daily AI
            const calendarView = document.querySelector('.calendar-fullwidth');
            if (calendarView) calendarView.style.display = 'none';
            mainPanel.style.display = 'flex';
            loadDailyAIDays();
        });

        closeBtn.addEventListener('click', () => {
            mainPanel.style.display = 'none';
            const calendarView = document.querySelector('.calendar-fullwidth');
            if (calendarView) calendarView.style.display = 'block';
        });
    }

    // Generate article button
    const generateBtn = document.getElementById('generateArticleMain');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateDailyArticle);
    }
}

// ============================================
// DAILY AI SUMMARY FUNCTIONS
// ============================================

let selectedDayForAI = null;
let selectedDayEvents = [];

async function loadDailyAIDays() {
    const listContainer = document.getElementById('dailyAIDaysList');
    if (!listContainer) return;

    listContainer.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><span>Loading days...</span></div>';

    try {
        // Get calendar data to extract unique dates
        // If calendar data is already loaded in state, use it
        let calendar = state.calendar;
        if (!calendar) {
            const response = await fetch(`${API_BASE}/api/calendar`);
            calendar = await response.json();
        }

        const days = Object.keys(calendar).filter(d => d !== '9999-12-31').sort().slice(0, 14); // Next 14 days

        if (days.length === 0) {
            listContainer.innerHTML = '<p class="placeholder-text">No upcoming events</p>';
            return;
        }

        listContainer.innerHTML = days.map(dateKey => {
            const events = calendar[dateKey] || [];
            const displayDate = formatDateKey(dateKey);
            const stockCount = events.filter(e => e.type === 'stock').length;
            const econCount = events.filter(e => e.type === 'economic').length;
            const fredCount = events.filter(e => !e.type || e.type === 'fred').length;

            return `
                <div class="dailyai-day" data-date="${dateKey}">
                    <span class="dailyai-day-date">${displayDate}</span>
                    <span class="dailyai-day-count">
                        ${fredCount > 0 ? `${fredCount} FRED` : ''}
                        ${stockCount > 0 ? ` ${stockCount} Earnings` : ''}
                        ${econCount > 0 ? ` ${econCount} Econ` : ''}
                    </span>
                </div>
            `;
        }).join('');

        // Add click handlers
        listContainer.querySelectorAll('.dailyai-day').forEach(el => {
            el.addEventListener('click', () => selectDayForAI(el.dataset.date, calendar[el.dataset.date]));
        });

    } catch (error) {
        console.error('Error loading days:', error);
        listContainer.innerHTML = '<p class="placeholder-text">Error loading days</p>';
    }
}

function selectDayForAI(dateKey, events) {
    selectedDayForAI = dateKey;
    selectedDayEvents = events || [];

    // Update UI
    document.querySelectorAll('.dailyai-day').forEach(el => {
        el.classList.toggle('active', el.dataset.date === dateKey);
    });

    const articlePanel = document.getElementById('dailyAIArticlePanel');
    const articleDate = document.getElementById('articleDateMain');
    const articleEvents = document.getElementById('articleEventsMain');
    const articleContent = document.getElementById('articleContentMain');

    if (articlePanel) articlePanel.style.display = 'block';
    if (articleDate) articleDate.textContent = `Analysis for ${formatDateKey(dateKey)}`;

    // Show events list
    if (articleEvents) {
        articleEvents.innerHTML = selectedDayEvents.map(event => {
            const typeClass = event.type || 'fred';
            const typeLabel = event.type === 'stock' ? 'STOCK' : (event.type === 'economic' ? 'ECON' : 'FRED');
            return `
                <div class="article-event-item">
                    <span class="article-event-type ${typeClass}">${typeLabel}</span>
                    <span>${event.display_name || event.name}</span>
                </div>
            `;
        }).join('');
    }

    // Clear previous article
    if (articleContent) {
        articleContent.innerHTML = '<p class="placeholder-text">Click "Generate AI Analysis" to create the article</p>';
    }
}

async function generateDailyArticle() {
    if (!selectedDayForAI || selectedDayEvents.length === 0) {
        alert('Please select a day first');
        return;
    }

    const btn = document.getElementById('generateArticleMain');
    const articleContent = document.getElementById('articleContentMain');

    const originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px"></span> Generating...';
    btn.disabled = true;

    articleContent.innerHTML = `
        <div class="article-loading">
            <div class="spinner"></div>
            <p>AI is generating X (Twitter) posts for ${selectedDayEvents.length} events...</p>
            <p style="font-size: 11px; margin-top: 8px;">This may take up to 60 seconds</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/ai/daily-summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: selectedDayForAI,
                events: selectedDayEvents
            })
        });

        const data = await response.json();

        if (data.error) {
            articleContent.innerHTML = `<p class="placeholder-text">Error: ${data.error}</p>`;
        } else if (data.article) {
            // Parse X posts format
            const posts = parseXPosts(data.article);

            articleContent.innerHTML = posts.map(post => `
                <div class="x-post-card">
                    <div class="x-post-content">${post.content}</div>
                    <div class="x-post-hashtags">${post.hashtags}</div>
                    ${post.source ? `<div class="x-post-source"><a href="${post.source}" target="_blank">Source: ${post.source}</a></div>` : ''}
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error generating article:', error);
        articleContent.innerHTML = `<p class="placeholder-text">Error: ${error.message}</p>`;
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function parseXPosts(text) {
    const posts = [];
    // Split by ---POST X--- separators
    const rawPosts = text.split(/---POST \d+---/).filter(p => p.trim().length > 0);

    rawPosts.forEach(raw => {
        let content = raw.replace(/---END POST \d+---/g, '').trim();

        // Extract hashtags (lines strictly starting with # or at end)
        let hashtags = '';
        const hashtagMatch = content.match(/#\w+(?: #\w+)*$/m);
        if (hashtagMatch) {
            hashtags = hashtagMatch[0];
            content = content.replace(hashtagMatch[0], '').trim();
        }

        // Extract Source URL (usually at the end)
        let source = '';
        const urlMatch = content.match(/(https?:\/\/[^\s]+)$/m);
        if (urlMatch) {
            source = urlMatch[1];
            content = content.replace(urlMatch[1], '').trim();
        }

        // Clean up content
        content = content.replace(/\n\n/g, '<br><br>');

        posts.push({ content, hashtags, source });
    });

    return posts;
}

// ============================================
// YAHOO FINANCE STOCK CHART
// ============================================

let stockPriceChart = null;

async function loadStockChart(ticker) {
    const chartContainer = document.querySelector('.column-charts .column-scroll');
    if (!chartContainer) return;

    // Add stock chart container if not exists
    let stockChartDiv = document.getElementById('stockChartContainer');
    if (!stockChartDiv) {
        stockChartDiv = document.createElement('div');
        stockChartDiv.id = 'stockChartContainer';
        stockChartDiv.className = 'stock-chart-container';
        stockChartDiv.innerHTML = `
            <div class="stock-chart-header">
                <h4>Price History (1 Year)</h4>
                <span class="stock-chart-period">Yahoo Finance</span>
            </div>
            <canvas id="stockPriceCanvas" height="300"></canvas>
        `;
        chartContainer.insertBefore(stockChartDiv, chartContainer.firstChild);
    }

    stockChartDiv.style.display = 'block';

    try {
        const response = await fetch(`${API_BASE}/api/stocks/chart/${ticker}`);
        const data = await response.json();

        if (data.error) {
            document.getElementById('stockPriceCanvas').parentElement.innerHTML =
                `<p class="placeholder-text">${data.error}</p>`;
            return;
        }

        renderStockChart(data);
    } catch (error) {
        console.error('Error loading stock chart:', error);
    }
}

function renderStockChart(data) {
    const ctx = document.getElementById('stockPriceCanvas');
    if (!ctx) return;

    if (stockPriceChart) {
        stockPriceChart.destroy();
    }

    const labels = data.data.map(d => d.date);
    const prices = data.data.map(d => d.close);

    // Determine color based on price trend
    const firstPrice = prices[0];
    const lastPrice = prices[prices.length - 1];
    const isPositive = lastPrice >= firstPrice;
    const lineColor = isPositive ? '#059669' : '#dc2626';
    const bgColor = isPositive ? 'rgba(5, 150, 105, 0.1)' : 'rgba(220, 38, 38, 0.1)';

    stockPriceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${data.ticker} Price`,
                data: prices,
                borderColor: lineColor,
                backgroundColor: bgColor,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: {
                        maxTicksLimit: 6,
                        font: { size: 10 }
                    }
                },
                y: {
                    display: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        font: { size: 10 },
                        callback: value => '$' + value.toFixed(0)
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function hideStockChart() {
    const stockChartDiv = document.getElementById('stockChartContainer');
    if (stockChartDiv) {
        stockChartDiv.style.display = 'none';
    }
}

// ============================================
// TILE-SPECIFIC FUNCTIONS (New expandable layout)
// ============================================

// Run analysis for a specific tile
async function runTileAnalysis(content, indicator) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';
    document.getElementById('loadingText').textContent = 'Running analysis...';

    try {
        const modelType = content.querySelector('.model-type-select').value;
        const orderP = parseInt(content.querySelector('.order-p')?.value) || 1;
        const orderD = parseInt(content.querySelector('.order-d')?.value) || 1;
        const orderQ = parseInt(content.querySelector('.order-q')?.value) || 1;
        const nTest = parseInt(content.querySelector('.n-test').value) || 12;
        const hFuture = parseInt(content.querySelector('.h-future').value) || 6;

        let params = { n_test: nTest, h_future: hFuture };
        if (modelType === 'ARIMA') {
            params.order = [orderP, orderD, orderQ];
        }

        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                series_id: indicator.series_id,
                model_type: modelType,
                ...params
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Analysis failed');
        }

        const analysisData = await response.json();

        // Render chart inside this tile
        renderTileForecastChart(content, analysisData, 12);

        // Setup period buttons for this NEW results
        content.querySelectorAll('.period-btn').forEach(btn => {
            // Re-bind to ensure it uses the NEW dynamic analysisData
            btn.onclick = () => {
                content.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderTileForecastChart(content, analysisData, parseInt(btn.dataset.period));
            };
        });

        // Render diff chart inside this tile
        if (analysisData.comparison) {
            renderTileDiffChart(content, analysisData);
        }

        // Render stats inside this tile
        renderTileStats(content, analysisData, modelType);

        // Render quality inside this tile
        renderTileQuality(content, analysisData);

    } catch (error) {
        console.error('Analysis error:', error);
        alert('Analysis failed: ' + error.message);
    } finally {
        overlay.style.display = 'none';
    }
}

// Render forecast chart inside tile
function renderTileForecastChart(content, data, periodValue = 12) {
    const canvas = content.querySelector('.forecast-chart');
    if (!canvas) return;

    // Store full data on canvas for later re-filtering
    canvas._fullData = data;

    const ctx = canvas.getContext('2d');
    let historical = data.historical;
    const forecast = data.forecast;

    // Slicing logic for period buttons
    if (periodValue > 0) {
        const histStart = Math.max(0, historical.dates.length - periodValue);
        historical = {
            dates: historical.dates.slice(histStart),
            values: historical.values.slice(histStart)
        };
    }

    console.log(`Rendering tile chart with ${periodValue} obs. Hist:`, historical.dates.length);

    // Clear existing chart property and destroy Chart.js instance properly
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    const allDates = [...historical.dates, ...forecast.dates];
    const historicalValues = [...historical.values, ...Array(forecast.dates.length).fill(null)];
    const forecastValues = [...Array(historical.dates.length - 1).fill(null), historical.values[historical.values.length - 1], ...forecast.values];

    console.log(`[Chart] Range: ${allDates[0]} to ${allDates[allDates.length - 1]}`);

    canvas._chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'Historical',
                    data: historicalValues,
                    borderColor: '#374151',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1
                },
                {
                    label: 'Forecast',
                    data: forecastValues,
                    borderColor: '#1a56db',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1
                },
                {
                    label: '+1σ RMSE',
                    data: [...Array(historical.dates.length).fill(null), ...forecast.sigma_1_up],
                    borderColor: 'rgba(26, 86, 219, 0.4)',
                    backgroundColor: 'rgba(26, 86, 219, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1'
                },
                {
                    label: '-1σ RMSE',
                    data: [...Array(historical.dates.length).fill(null), ...forecast.sigma_1_down],
                    borderColor: 'rgba(26, 86, 219, 0.4)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: { maxTicksLimit: 8, font: { size: 10 } }
                },
                y: {
                    display: true,
                    grid: { color: '#f3f4f6' },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });
}

// Render stats inside tile
function renderTileStats(content, data, modelType) {
    const statsGrid = content.querySelector('.stats-grid');
    if (!statsGrid || !data.stats) return;

    const stats = data.stats;
    statsGrid.innerHTML = `
        <div class="stat-item">
            <div class="stat-value">${stats.RMSE?.toFixed(4) || 'N/A'}</div>
            <div class="stat-label">RMSE</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${stats.MAPE?.toFixed(2) || 'N/A'}%</div>
            <div class="stat-label">MAPE</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${stats.AIC?.toFixed(2) || 'N/A'}</div>
            <div class="stat-label">AIC</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${stats.BIC?.toFixed(2) || 'N/A'}</div>
            <div class="stat-label">BIC</div>
        </div>
    `;
}

// Render quality inside tile
function renderTileQuality(content, data) {
    const qualityContent = content.querySelector('.quality-content');
    if (!qualityContent) return;

    if (data.opinion) {
        qualityContent.innerHTML = `<p>${data.opinion.replace(/\n/g, '<br>')}</p>`;
    } else {
        qualityContent.innerHTML = '<p class="placeholder-text">No quality assessment available</p>';
    }
}

// Load correlation for tile
async function loadTileCorrelation(content, seriesId) {
    const heatmapContainer = content.querySelector('.heatmap-container');
    if (!heatmapContainer) return;

    try {
        const response = await fetch(`${API_BASE}/api/correlation/${seriesId}`);
        const correlations = await response.json();

        if (!correlations || correlations.length === 0) {
            heatmapContainer.innerHTML = '<p class="placeholder-text">No correlation data</p>';
            return;
        }

        let html = '<div class="heatmap-grid">';
        for (const item of correlations) {
            const color = getHeatmapColor(item.correlation);
            const arrow = item.beta > 0 ? '↑' : '↓';
            html += `
                <div class="heatmap-cell">
                    <span class="heatmap-ticker">${item.ticker}</span>
                    <span class="heatmap-corr" style="background-color: ${color}">${item.correlation.toFixed(2)}</span>
                    <span class="heatmap-beta"><span class="beta-label">β:</span> <span class="beta-value">${item.beta.toFixed(2)}</span> <span class="trend-icon">${arrow}</span></span>
                </div>
            `;
        }
        html += '</div>';
        heatmapContainer.innerHTML = html;
    } catch (error) {
        console.error('Correlation error:', error);
        heatmapContainer.innerHTML = '<p class="placeholder-text">Error loading correlation</p>';
    }
}

// Run AI research for tile
async function runTileAI(content, indicator) {
    const aiContent = content.querySelector('.ai-content');
    if (!aiContent) return;

    aiContent.innerHTML = '<div class="spinner"></div><span>Analyzing...</span>';

    try {
        const response = await fetch(`${API_BASE}/api/research`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                series_id: indicator.series_id,
                query: indicator.display_name || indicator.name
            })
        });

        const data = await response.json();

        if (data.content) {
            aiContent.innerHTML = `<div class="ai-text">${data.content.replace(/\n/g, '<br>')}</div>`;
        } else if (data.error) {
            aiContent.innerHTML = `<p class="placeholder-text">Error: ${data.error}</p>`;
        }
    } catch (error) {
        console.error('AI Research error:', error);
        aiContent.innerHTML = '<p class="placeholder-text">Error loading AI research</p>';
    }
}

// Load stock chart for tile
async function loadTileStockChart(content, ticker) {
    const canvas = content.querySelector('.stock-chart');
    if (!canvas) return;

    try {
        const response = await fetch(`${API_BASE}/api/stocks/chart/${ticker}`);
        const data = await response.json();

        if (data.error) {
            canvas.parentElement.innerHTML = `<p class="placeholder-text">${data.error}</p>`;
            return;
        }

        const ctx = canvas.getContext('2d');

        if (canvas._chart) {
            canvas._chart.destroy();
        }

        canvas._chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: ticker,
                    data: data.prices,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        display: true,
                        grid: { display: false },
                        ticks: { maxTicksLimit: 6, font: { size: 10 } }
                    },
                    y: {
                        display: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: {
                            font: { size: 10 },
                            callback: value => '$' + value.toFixed(0)
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Stock chart error:', error);
        canvas.parentElement.innerHTML = '<p class="placeholder-text">Error loading chart</p>';
    }
}

// Render diff chart inside tile
function renderTileDiffChart(content, data) {
    const canvas = content.querySelector('.diff-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const comparison = data.comparison;

    if (canvas._chart) { canvas._chart.destroy(); }

    canvas._chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: comparison.dates,
            datasets: [
                {
                    label: 'Actual Diff',
                    data: comparison.actual_diff,
                    backgroundColor: 'rgba(5, 150, 105, 0.7)',
                    borderColor: '#059669',
                    borderWidth: 1
                },
                {
                    label: 'Predicted Diff',
                    data: comparison.predict_diff,
                    backgroundColor: 'rgba(26, 86, 219, 0.7)',
                    borderColor: '#1a56db',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: true, grid: { display: false }, ticks: { font: { size: 9 } } },
                y: { display: true, grid: { color: '#f3f4f6' }, ticks: { font: { size: 9 } } }
            }
        }
    });
}
