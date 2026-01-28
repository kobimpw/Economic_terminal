// ===== GLOBAL STATE =====
const state = {
    apiKey: '',
    calendarData: [],
    expandedDays: new Set(),
    expandedIndicators: new Set(),
    analysisCache: new Map(),
    currentPeriods: new Map() // Track selected period for each chart
};

// ===== API BASE URL =====
const API_BASE = window.location.origin;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    // Load API key from session storage
    const savedKey = sessionStorage.getItem('fredApiKey');
    if (savedKey) {
        document.getElementById('fredApiKey').value = savedKey;
        state.apiKey = savedKey;
    }

    // Event listeners
    document.getElementById('loadCalendar').addEventListener('click', loadCalendar);
    document.getElementById('fredApiKey').addEventListener('change', (e) => {
        state.apiKey = e.target.value;
        sessionStorage.setItem('fredApiKey', e.target.value);
    });
});

// ===== CALENDAR LOADING =====
async function loadCalendar() {
    if (!state.apiKey) {
        showError('Please enter your FRED API key');
        return;
    }

    showLoading();
    updateStatus('Loading calendar...', 'loading');

    try {
        const response = await fetch(`${API_BASE}/calendar?api_key=${encodeURIComponent(state.apiKey)}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        state.calendarData = await response.json();
        renderCalendar();
        updateStatus('Calendar loaded', 'success');

    } catch (error) {
        console.error('Calendar load error:', error);
        showError(`Failed to load calendar: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

// ===== CALENDAR RENDERING =====
function renderCalendar() {
    const container = document.getElementById('calendarContainer');
    container.innerHTML = '';
    container.classList.remove('hidden');

    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('errorState').classList.add('hidden');

    state.calendarData.forEach(dayData => {
        const dayCard = createDayCard(dayData);
        container.appendChild(dayCard);
    });
}

function createDayCard(dayData) {
    const card = document.createElement('div');
    card.className = 'day-card collapsed';
    card.dataset.date = dayData.date;

    card.innerHTML = `
        <div class="day-card-header">
            <div class="day-card-title">
                <span class="day-card-date">${formatDate(dayData.date)}</span>
                <span class="day-card-count">${dayData.count} indicator${dayData.count !== 1 ? 's' : ''}</span>
            </div>
            <span class="day-card-toggle">▼</span>
        </div>
        <div class="day-card-body">
            <div class="indicators-list"></div>
        </div>
    `;

    // Toggle functionality
    const header = card.querySelector('.day-card-header');
    header.addEventListener('click', () => toggleDayCard(card, dayData));

    return card;
}

function toggleDayCard(card, dayData) {
    const isCollapsed = card.classList.contains('collapsed');
    card.classList.toggle('collapsed');

    if (isCollapsed) {
        // Expand: render indicators if not already rendered
        const indicatorsList = card.querySelector('.indicators-list');
        if (indicatorsList.children.length === 0) {
            dayData.indicators.forEach(indicator => {
                const indicatorCard = createIndicatorCard(indicator);
                indicatorsList.appendChild(indicatorCard);
            });
        }
        state.expandedDays.add(dayData.date);
    } else {
        state.expandedDays.delete(dayData.date);
    }
}

// ===== INDICATOR CARD =====
function createIndicatorCard(indicator) {
    const card = document.createElement('div');
    card.className = 'indicator-card collapsed';
    card.dataset.seriesId = indicator.series_id;

    const lastValueDisplay = indicator.last_value !== null
        ? `${indicator.last_value.toFixed(2)}`
        : 'N/A';

    card.innerHTML = `
        <div class="indicator-header">
            <div class="indicator-title">
                <span class="indicator-name">${indicator.name}</span>
                <span class="indicator-category">${indicator.category}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span class="indicator-forecast" data-forecast>Last: ${lastValueDisplay}</span>
                <span class="indicator-toggle">▼</span>
            </div>
        </div>
        <div class="indicator-body">
            <div class="indicator-content">
                <div class="loading-indicator">
                    <div class="spinner"></div>
                    <p>Loading analysis...</p>
                </div>
            </div>
        </div>
    `;

    // Toggle functionality
    const header = card.querySelector('.indicator-header');
    header.addEventListener('click', () => toggleIndicatorCard(card, indicator));

    return card;
}

async function toggleIndicatorCard(card, indicator) {
    const isCollapsed = card.classList.contains('collapsed');
    card.classList.toggle('collapsed');

    if (isCollapsed) {
        // Expand: load analysis if not cached
        const cacheKey = `${indicator.series_id}_ARIMA_1_1_1`;

        if (!state.analysisCache.has(cacheKey)) {
            await loadIndicatorAnalysis(card, indicator);
        }

        state.expandedIndicators.add(indicator.series_id);
    } else {
        state.expandedIndicators.delete(indicator.series_id);
    }
}

async function loadIndicatorAnalysis(card, indicator) {
    const content = card.querySelector('.indicator-content');

    try {
        // Default ARIMA analysis
        const analysis = await fetchAnalysis(indicator.series_id, {
            model_type: 'ARIMA',
            p: 1, d: 1, q: 1,
            n_test: 12,
            h_future: 6
        });

        // Render full analysis UI
        content.innerHTML = renderAnalysisContent(indicator, analysis);

        // Initialize interactive elements
        initializeModelSelector(card, indicator, analysis);
        renderCharts(card, analysis);

        // Load additional data
        loadMarketCorrelation(card, indicator.series_id);
        loadResearch(card, indicator.series_id);
        loadNews(card, indicator.series_id);

        // Update forecast in header
        const forecastEl = card.querySelector('[data-forecast]');
        if (analysis.forecast && analysis.forecast.values.length > 0) {
            forecastEl.textContent = `Forecast: ${analysis.forecast.values[0].toFixed(2)}`;
        }

    } catch (error) {
        content.innerHTML = `
            <div class="error-state">
                <p>Error loading analysis: ${error.message}</p>
                <button class="btn-secondary" onclick="location.reload()">Retry</button>
            </div>
        `;
    }
}

// ===== ANALYSIS FETCHING =====
async function fetchAnalysis(seriesId, params) {
    const payload = {
        api_key: state.apiKey,
        series_id: seriesId,
        ...params
    };

    const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Analysis failed');
    }

    const data = await response.json();

    // Cache the result
    const cacheKey = `${seriesId}_${params.model_type}_${params.p || ''}_${params.d || ''}_${params.q || ''}`;
    state.analysisCache.set(cacheKey, data);

    return data;
}

// ===== ANALYSIS CONTENT RENDERING =====
function renderAnalysisContent(indicator, analysis) {
    return `
        <div class="model-selector" data-model-selector></div>
        
        <div class="charts-container">
            <div class="chart-main">
                <div class="chart-wrapper">
                    <div class="chart-header">
                        <span class="chart-title">📈 Historical Data & Forecast</span>
                        <div class="period-selector" data-chart="main"></div>
                    </div>
                    <div id="chart-main-${indicator.series_id}" style="width:100%;height:400px;"></div>
                </div>
            </div>
            
            <div class="chart-secondary">
                <div class="chart-wrapper">
                    <div class="chart-header">
                        <span class="chart-title">🎯 Test Phase Comparison</span>
                        <div class="period-selector" data-chart="test"></div>
                    </div>
                    <div id="chart-test-${indicator.series_id}" style="width:100%;height:300px;"></div>
                </div>
                
                <div class="chart-wrapper">
                    <div class="chart-header">
                        <span class="chart-title">📊 Difference Analysis</span>
                        <div class="period-selector" data-chart="diff">
                            <button class="period-btn active" data-diff-mode="real">Real Diff</button>
                            <button class="period-btn" data-diff-mode="forecast">Forecast Diff</button>
                            <button class="period-btn" data-diff-mode="error">Error</button>
                        </div>
                    </div>
                    <div id="chart-diff-${indicator.series_id}" style="width:100%;height:300px;"></div>
                </div>
            </div>
        </div>
        
        <div class="stats-panel" data-stats-panel></div>
        
        <div class="opinion-section">
            <h3>🤖 AI Model Quality Assessment</h3>
            <div class="opinion-content" data-opinion></div>
        </div>
        
        <div class="market-correlation">
            <h3>📊 Market Correlation Analysis</h3>
            <div data-correlation-content>
                <div class="loading-indicator"><div class="spinner"></div></div>
            </div>
        </div>
        
        <div class="research-section">
            <h3>🔍 AI Research (Perplexity)</h3>
            <div class="research-content" data-research-content>
                <div class="loading-indicator"><div class="spinner"></div></div>
            </div>
        </div>
        
        <div class="news-section">
            <h3>📰 News Sentiment Analysis</h3>
            <div data-news-content>
                <div class="loading-indicator"><div class="spinner"></div></div>
            </div>
        </div>
    `;
}

// ===== MODEL SELECTOR =====
function initializeModelSelector(card, indicator, initialAnalysis) {
    const selector = card.querySelector('[data-model-selector]');

    selector.innerHTML = `
        <div class="model-selector-header">
            <button class="model-btn active" data-model="ARIMA">ARIMA</button>
            <button class="model-btn" data-model="MA">Moving Average</button>
            <button class="model-btn" data-model="MONTE">Monte Carlo</button>
        </div>
        <div class="model-params" data-params-container>
            ${renderARIMAParams()}
        </div>
    `;

    // Model button listeners
    selector.querySelectorAll('.model-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            selector.querySelectorAll('.model-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const modelType = btn.dataset.model;
            const paramsContainer = selector.querySelector('[data-params-container]');

            if (modelType === 'ARIMA') {
                paramsContainer.innerHTML = renderARIMAParams();
            } else if (modelType === 'MA') {
                paramsContainer.innerHTML = renderMAParams();
            } else if (modelType === 'MONTE') {
                paramsContainer.innerHTML = renderMonteParams();
            }

            // Add update button listener
            paramsContainer.querySelector('.update-btn').addEventListener('click', () => {
                updateAnalysis(card, indicator, modelType);
            });
        });
    });

    // Initial update button listener
    selector.querySelector('.update-btn').addEventListener('click', () => {
        updateAnalysis(card, indicator, 'ARIMA');
    });

    // Render initial stats and opinion
    renderStats(card, initialAnalysis);
    renderOpinion(card, initialAnalysis);
}

function renderARIMAParams() {
    return `
        <div class="param-group">
            <label>p (AR order)</label>
            <input type="number" name="p" value="1" min="0" max="5">
        </div>
        <div class="param-group">
            <label>d (Differencing)</label>
            <input type="number" name="d" value="1" min="0" max="2">
        </div>
        <div class="param-group">
            <label>q (MA order)</label>
            <input type="number" name="q" value="1" min="0" max="5">
        </div>
        <div class="param-group">
            <label>Test Length</label>
            <input type="number" name="n_test" value="12" min="6" max="36">
        </div>
        <div class="param-group">
            <label>Forecast Horizon</label>
            <input type="number" name="h_future" value="6" min="1" max="24">
        </div>
        <button class="btn-primary update-btn">Update Forecast</button>
    `;
}

function renderMAParams() {
    return `
        <div class="param-group">
            <label>Window Size</label>
            <input type="number" name="ma_window" value="3" min="2" max="12">
        </div>
        <div class="param-group">
            <label>Test Length</label>
            <input type="number" name="n_test" value="12" min="6" max="36">
        </div>
        <div class="param-group">
            <label>Forecast Horizon</label>
            <input type="number" name="h_future" value="6" min="1" max="24">
        </div>
        <button class="btn-primary update-btn">Update Forecast</button>
    `;
}

function renderMonteParams() {
    return `
        <div class="param-group">
            <label>Simulations</label>
            <input type="number" name="mc_sims" value="1000" min="100" max="10000" step="100">
        </div>
        <div class="param-group">
            <label>Test Length</label>
            <input type="number" name="n_test" value="12" min="6" max="36">
        </div>
        <div class="param-group">
            <label>Forecast Horizon</label>
            <input type="number" name="h_future" value="6" min="1" max="24">
        </div>
        <button class="btn-primary update-btn">Update Forecast</button>
    `;
}

async function updateAnalysis(card, indicator, modelType) {
    const paramsContainer = card.querySelector('[data-params-container]');
    const inputs = paramsContainer.querySelectorAll('input');

    const params = { model_type: modelType };
    inputs.forEach(input => {
        const value = parseInt(input.value);
        if (input.name === 'ma_window') {
            params.ma_windows = [value];
        } else {
            params[input.name] = value;
        }
    });

    // Show loading
    const content = card.querySelector('.indicator-content');
    content.style.opacity = '0.5';

    try {
        const analysis = await fetchAnalysis(indicator.series_id, params);

        // Update charts
        renderCharts(card, analysis);

        // Update stats and opinion
        renderStats(card, analysis);
        renderOpinion(card, analysis);

        // Update forecast in header
        const forecastEl = card.querySelector('[data-forecast]');
        if (analysis.forecast && analysis.forecast.values.length > 0) {
            forecastEl.textContent = `Forecast: ${analysis.forecast.values[0].toFixed(2)}`;
        }

        content.style.opacity = '1';

    } catch (error) {
        alert(`Error updating analysis: ${error.message}`);
        content.style.opacity = '1';
    }
}

// ===== CHARTS RENDERING =====
function renderCharts(card, analysis) {
    const seriesId = analysis.series_id;

    // Main chart
    renderMainChart(card, seriesId, analysis);

    // Test phase chart
    renderTestChart(card, seriesId, analysis);

    // Diff chart
    renderDiffChart(card, seriesId, analysis);

    // Add period selectors
    addPeriodSelectors(card, seriesId, analysis);
}

function renderMainChart(card, seriesId, analysis) {
    const chartId = `chart-main-${seriesId}`;

    const historical = {
        x: analysis.historical.dates,
        y: analysis.historical.values,
        type: 'scatter',
        mode: 'lines',
        name: 'Historical',
        line: { color: '#00d4ff', width: 2 }
    };

    const forecast = {
        x: analysis.forecast.dates,
        y: analysis.forecast.values,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Forecast',
        line: { color: '#ff6b35', width: 2 },
        marker: { size: 6 }
    };

    const sigma1Upper = {
        x: analysis.forecast.dates,
        y: analysis.forecast.sigma_1_up,
        type: 'scatter',
        mode: 'lines',
        name: '±1σ (68%)',
        line: { color: '#4ecdc4', width: 1, dash: 'dot' },
        showlegend: false
    };

    const sigma1Lower = {
        x: analysis.forecast.dates,
        y: analysis.forecast.sigma_1_down,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: 'rgba(78, 205, 196, 0.1)',
        line: { color: '#4ecdc4', width: 1, dash: 'dot' },
        name: '±1σ (68%)'
    };

    const sigma2Upper = {
        x: analysis.forecast.dates,
        y: analysis.forecast.sigma_2_up,
        type: 'scatter',
        mode: 'lines',
        name: '±2σ (95%)',
        line: { color: '#ffd93d', width: 1, dash: 'dash' },
        showlegend: false
    };

    const sigma2Lower = {
        x: analysis.forecast.dates,
        y: analysis.forecast.sigma_2_down,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: 'rgba(255, 217, 61, 0.05)',
        line: { color: '#ffd93d', width: 1, dash: 'dash' },
        name: '±2σ (95%)'
    };

    const layout = {
        paper_bgcolor: '#1a1f3a',
        plot_bgcolor: '#252b48',
        font: { color: '#b8c5d6', family: 'Inter' },
        margin: { l: 50, r: 30, t: 30, b: 40 },
        xaxis: { gridcolor: '#2d3454', showgrid: true },
        yaxis: { gridcolor: '#2d3454', showgrid: true },
        legend: { x: 0, y: 1.1, orientation: 'h' },
        hovermode: 'x unified'
    };

    const config = { responsive: true, displayModeBar: false };

    Plotly.newPlot(chartId, [sigma2Upper, sigma2Lower, sigma1Upper, sigma1Lower, historical, forecast], layout, config);
}

function renderTestChart(card, seriesId, analysis) {
    const chartId = `chart-test-${seriesId}`;

    const actual = {
        x: analysis.comparison.dates,
        y: analysis.comparison.actual,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Actual',
        line: { color: '#00d4ff', width: 2 },
        marker: { size: 5 }
    };

    const predicted = {
        x: analysis.comparison.dates,
        y: analysis.comparison.predict,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Predicted',
        line: { color: '#ff6b35', width: 2, dash: 'dash' },
        marker: { size: 5, symbol: 'square' }
    };

    const layout = {
        paper_bgcolor: '#1a1f3a',
        plot_bgcolor: '#252b48',
        font: { color: '#b8c5d6', family: 'Inter' },
        margin: { l: 50, r: 30, t: 20, b: 40 },
        xaxis: { gridcolor: '#2d3454' },
        yaxis: { gridcolor: '#2d3454' },
        legend: { x: 0, y: 1.1, orientation: 'h' },
        hovermode: 'x unified'
    };

    const config = { responsive: true, displayModeBar: false };

    Plotly.newPlot(chartId, [actual, predicted], layout, config);
}

function renderDiffChart(card, seriesId, analysis, mode = 'real') {
    const chartId = `chart-diff-${seriesId}`;

    let data;

    if (mode === 'real') {
        data = [{
            x: analysis.comparison.dates,
            y: analysis.comparison.actual_diff,
            type: 'bar',
            name: 'Real Diff',
            marker: { color: '#00d4ff' }
        }];
    } else if (mode === 'forecast') {
        data = [{
            x: analysis.comparison.dates,
            y: analysis.comparison.predict_diff,
            type: 'bar',
            name: 'Forecast Diff',
            marker: { color: '#ff6b35' }
        }];
    } else {
        data = [{
            x: analysis.comparison.dates,
            y: analysis.comparison.diff_error,
            type: 'bar',
            name: 'Difference Error',
            marker: { color: '#4ecdc4' }
        }];
    }

    const layout = {
        paper_bgcolor: '#1a1f3a',
        plot_bgcolor: '#252b48',
        font: { color: '#b8c5d6', family: 'Inter' },
        margin: { l: 50, r: 30, t: 20, b: 40 },
        xaxis: { gridcolor: '#2d3454' },
        yaxis: { gridcolor: '#2d3454' },
        hovermode: 'x unified'
    };

    const config = { responsive: true, displayModeBar: false };

    Plotly.newPlot(chartId, data, layout, config);

    // Add diff mode toggle listeners
    const diffButtons = card.querySelectorAll('[data-diff-mode]');
    diffButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            diffButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderDiffChart(card, seriesId, analysis, btn.dataset.diffMode);
        });
    });
}

function addPeriodSelectors(card, seriesId, analysis) {
    // For now, period selectors are visual only
    // Full implementation would filter data client-side
    const selectors = card.querySelectorAll('.period-selector[data-chart]');

    selectors.forEach(selector => {
        if (selector.dataset.chart === 'diff') return; // Skip diff chart (has custom buttons)

        selector.innerHTML = `
            <button class="period-btn" data-period="12M">12M</button>
            <button class="period-btn" data-period="2Y">2Y</button>
            <button class="period-btn" data-period="5Y">5Y</button>
            <button class="period-btn active" data-period="MAX">MAX</button>
        `;

        selector.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                selector.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // TODO: Implement actual filtering
            });
        });
    });
}

// ===== STATS RENDERING =====
function renderStats(card, analysis) {
    const statsPanel = card.querySelector('[data-stats-panel]');

    const stats = analysis.stats;
    let statsHTML = '<div class="stats-grid">';

    for (const [key, value] of Object.entries(stats)) {
        if (typeof value === 'number') {
            statsHTML += `
                <div class="stat-item">
                    <div class="stat-label">${key}</div>
                    <div class="stat-value">${value.toFixed(4)}</div>
                </div>
            `;
        }
    }

    statsHTML += '</div>';
    statsPanel.innerHTML = statsHTML;
}

function renderOpinion(card, analysis) {
    const opinionEl = card.querySelector('[data-opinion]');

    if (analysis.opinion) {
        // Convert markdown to HTML if needed
        opinionEl.innerHTML = marked.parse(analysis.opinion);
    } else {
        opinionEl.textContent = 'No quality assessment available.';
    }
}

// ===== MARKET CORRELATION =====
async function loadMarketCorrelation(card, seriesId) {
    const container = card.querySelector('[data-correlation-content]');

    try {
        const response = await fetch(`${API_BASE}/market-impact?api_key=${encodeURIComponent(state.apiKey)}&series_id=${seriesId}`);
        const data = await response.json();

        if (Object.keys(data).length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted);">No correlation data available.</p>';
            return;
        }

        let tableHTML = `
            <table class="correlation-table">
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Long-Term Corr</th>
                        <th>Immediate Corr</th>
                        <th>Beta</th>
                        <th>Interpretation</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (const [ticker, info] of Object.entries(data)) {
            const corrClass = info.long_term_correlation > 0 ? 'corr-positive' : 'corr-negative';
            const immCorr = info.immediate_correlation !== null ? info.immediate_correlation.toFixed(3) : 'N/A';

            tableHTML += `
                <tr>
                    <td><strong>${info.name}</strong></td>
                    <td class="${corrClass}">${info.long_term_correlation.toFixed(3)}</td>
                    <td>${immCorr}</td>
                    <td>${info.beta.toFixed(3)}</td>
                    <td style="color: var(--text-muted); font-size: 0.85rem;">${info.interpretation}</td>
                </tr>
            `;
        }

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;

    } catch (error) {
        container.innerHTML = `<p style="color: var(--accent-red);">Error loading correlation: ${error.message}</p>`;
    }
}

// ===== RESEARCH =====
async function loadResearch(card, seriesId) {
    const container = card.querySelector('[data-research-content]');

    try {
        const response = await fetch(`${API_BASE}/research?series_id=${seriesId}`);
        const data = await response.json();

        if (data.outlook === 'ERROR') {
            container.innerHTML = `<p style="color: var(--text-muted);">${data.summary}</p>`;
            return;
        }

        // Render markdown content
        container.innerHTML = marked.parse(data.summary);

        // Add sources
        if (data.sources && data.sources.length > 0) {
            let sourcesHTML = '<div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);"><strong>Sources:</strong><ul>';
            data.sources.forEach(source => {
                if (typeof source === 'string' && source.startsWith('http')) {
                    sourcesHTML += `<li><a href="${source}" target="_blank">${source}</a></li>`;
                } else {
                    sourcesHTML += `<li>${source}</li>`;
                }
            });
            sourcesHTML += '</ul></div>';
            container.innerHTML += sourcesHTML;
        }

    } catch (error) {
        container.innerHTML = `<p style="color: var(--accent-red);">Error loading research: ${error.message}</p>`;
    }
}

// ===== NEWS =====
async function loadNews(card, seriesId) {
    const container = card.querySelector('[data-news-content]');

    try {
        const response = await fetch(`${API_BASE}/news?series_id=${seriesId}`);
        const data = await response.json();

        if (data.error) {
            container.innerHTML = `<p style="color: var(--text-muted);">Error: ${data.error}</p>`;
            return;
        }

        if (!data.articles || data.articles.length === 0) {
            container.innerHTML = `<p style="color: var(--text-muted);">No recent news articles found.</p>`;
            return;
        }

        // Render overall sentiment gauge
        const gaugeClass = data.overall_label === 'Positive' ? 'corr-positive' :
            data.overall_label === 'Negative' ? 'corr-negative' : '';

        let newsHTML = `
            <div class="sentiment-gauge">
                <div class="gauge-value ${gaugeClass}">${data.overall}/100</div>
                <div style="color: var(--text-muted); font-size: 0.9rem;">Overall Sentiment: ${data.overall_label}</div>
            </div>
            <div class="news-list">
        `;

        data.articles.forEach(article => {
            const sentimentClass = article.sentiment_label === 'Positive' ? 'sentiment-positive' :
                article.sentiment_label === 'Negative' ? 'sentiment-negative' :
                    'sentiment-neutral';

            newsHTML += `
                <div class="news-item">
                    <div class="news-header">
                        <a href="${article.url}" target="_blank" class="news-title">${article.title}</a>
                        <span class="news-sentiment ${sentimentClass}">${article.sentiment}</span>
                    </div>
                    <div class="news-meta">${article.source} • ${formatDate(article.publishedAt)}</div>
                </div>
            `;
        });

        newsHTML += '</div>';
        container.innerHTML = newsHTML;

    } catch (error) {
        container.innerHTML = `<p style="color: var(--accent-red);">Error loading news: ${error.message}</p>`;
    }
}

// ===== UTILITY FUNCTIONS =====
function showLoading() {
    document.getElementById('loadingState').classList.remove('hidden');
    document.getElementById('calendarContainer').classList.add('hidden');
    document.getElementById('errorState').classList.add('hidden');
}

function showError(message) {
    document.getElementById('errorState').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('calendarContainer').classList.add('hidden');
}

function updateStatus(text, type) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = indicator.querySelector('.status-text');
    const statusDot = indicator.querySelector('.status-dot');

    statusText.textContent = text;

    if (type === 'loading') {
        statusDot.style.background = 'var(--accent-yellow)';
    } else if (type === 'success') {
        statusDot.style.background = 'var(--accent-green)';
    } else if (type === 'error') {
        statusDot.style.background = 'var(--accent-red)';
    }
}

function formatDate(dateString) {
    if (!dateString || dateString === 'TBD' || dateString === 'N/A') {
        return dateString;
    }

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch {
        return dateString;
    }
}
