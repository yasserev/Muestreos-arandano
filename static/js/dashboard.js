/**
 * Camposol Clamshell Quality Control Dashboard Controller
 * Interactive Analytics, ECharts Renderers & Filter Handlers
 */

// Global App State
const AppState = {
    filters: {
        fecha_desde: '',
        fecha_hasta: '',
        turno: '',
        linea: '',
        viaje: '',
        formato: '',
        variedad: '',
        tipo_tecnologia: '',
        cliente: ''
    },
    tablePagination: {
        page: 1,
        pageSize: 15,
        totalPages: 1,
        totalRecords: 0
    },
    minAvailableDate: '',
    maxAvailableDate: '',
    theme: 'light',
    techChartMode: 'base',
    techData: null,
    techEvolutionUnit: 'day',
    techEvolutionSelectedTech: null,
    techEvolutionData: null,
    prodChartViewMode: 'pie',
    prodData: null,
    presentationMode: false,
    charts: {
        scatter: null,
        distribution: null,
        control: null,
        boxplot: null,
        compliance: null,
        technology: null,
        techEvolution: null,
        productionTechnology: null
    }
};

// DOM Elements
const elements = {
    loadingOverlay: document.getElementById('loading-overlay'),
    filterForm: document.getElementById('filter-form'),
    btnResetFilters: document.getElementById('btn-reset-filters'),
    btnThemeToggle: document.getElementById('btn-theme-toggle'),
    themeIcon: document.getElementById('theme-icon'),
    btnExportCsv: document.getElementById('btn-export-csv'),
    btnTogglePresentation: document.getElementById('btn-toggle-presentation'),
    dbStatusText: document.getElementById('db-status-text'),
    // Date inputs
    fechaDesde: document.getElementById('filter-fecha-desde'),
    fechaHasta: document.getElementById('filter-fecha-hasta'),
    // Selects
    selectTurno: document.getElementById('filter-turno'),
    selectLinea: document.getElementById('filter-linea'),
    selectFormato: document.getElementById('filter-formato'),
    selectVariedad: document.getElementById('filter-variedad'),
    selectTecnologia: document.getElementById('filter-tecnologia'),
    selectCliente: document.getElementById('filter-cliente'),
    inputViaje: document.getElementById('filter-viaje'),
    presetBtns: document.querySelectorAll('.preset-btn'),
    // KPIs
    kpiTotalMuestreos: document.getElementById('kpi-total-muestreos'),
    kpiTotalClamshells: document.getElementById('kpi-total-clamshells'),
    kpiPesoPromedio: document.getElementById('kpi-peso-promedio'),
    kpiTolerancia: document.getElementById('kpi-tolerancia'),
    kpiPctEnRango: document.getElementById('kpi-pct-en-rango'),
    progressEnRango: document.getElementById('progress-en-rango'),
    kpiCountEnRango: document.getElementById('kpi-count-en-rango'),
    kpiPctBajoPeso: document.getElementById('kpi-pct-bajo-peso'),
    kpiCountBajoPeso: document.getElementById('kpi-count-bajo-peso'),
    kpiTagRiesgo: document.getElementById('kpi-tag-riesgo'),
    kpiPctSobrepeso: document.getElementById('kpi-pct-sobrepeso'),
    kpiGiveawayG: document.getElementById('kpi-giveaway-g'),
    kpiCpk: document.getElementById('kpi-cpk'),
    kpiCp: document.getElementById('kpi-cp'),
    kpiCpkStatus: document.getElementById('kpi-cpk-status'),
    // Table
    samplesTableBody: document.getElementById('table-body'),
    tableRecordCount: document.getElementById('table-record-count'),
    paginationIndicator: document.getElementById('pagination-indicator'),
    btnPagePrev: document.getElementById('btn-page-prev'),
    btnPageNext: document.getElementById('btn-page-next'),
    // Modal
    sampleModal: document.getElementById('sample-modal'),
    modalTitle: document.getElementById('modal-title'),
    modalSubtitle: document.getElementById('modal-subtitle'),
    modalMetaGrid: document.getElementById('modal-meta-grid'),
    modalSampleStats: document.getElementById('modal-sample-stats'),
    modalClamshellsGrid: document.getElementById('modal-clamshells-grid'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    btnModalDismiss: document.getElementById('btn-modal-dismiss'),
    // Sidebar Collapse & Guide Modal
    mainLayout: document.getElementById('main-layout'),
    btnToggleFilters: document.getElementById('btn-toggle-filters'),
    btnToggleFiltersText: document.getElementById('btn-toggle-filters-text'),
    btnCollapseSidebar: document.getElementById('btn-collapse-sidebar'),
    btnFloatingFilterToggle: document.getElementById('btn-floating-filter-toggle'),
    btnOpenGuide: document.getElementById('btn-open-guide'),
    guideModal: document.getElementById('guide-modal'),
    btnCloseGuideModal: document.getElementById('btn-close-guide-modal'),
    btnGuideModalDismiss: document.getElementById('btn-guide-modal-dismiss'),
    // Limits badge & Chat
    bellLimitsTag: document.getElementById('bell-limits-tag'),
    btnChatFab: document.getElementById('btn-chat-fab'),
    chatDrawer: document.getElementById('chat-drawer'),
    btnChatMinimize: document.getElementById('btn-chat-minimize'),
    btnChatClear: document.getElementById('btn-chat-clear'),
    chatMessagesContainer: document.getElementById('chat-messages'),
    chatInput: document.getElementById('chat-input'),
    btnChatSend: document.getElementById('btn-chat-send'),
    chatForm: document.getElementById('chat-form'),
    chatSuggestions: document.getElementById('chat-suggestions'),
    chatIconOpen: document.getElementById('chat-icon-open'),
    chatIconClose: document.getElementById('chat-icon-close'),
    // Technology Chart Mode Buttons
    btnTechModeDev: document.getElementById('btn-tech-mode-dev'),
    btnTechModeBase: document.getElementById('btn-tech-mode-base'),
    btnTechModeGrams: document.getElementById('btn-tech-mode-grams'),
    // Technology Evolution Controls
    selectEvolutionTech: document.getElementById('select-evolution-tech'),
    btnUnitDay: document.getElementById('btn-unit-day'),
    btnUnitWeek: document.getElementById('btn-unit-week'),
    btnUnitMonth: document.getElementById('btn-unit-month'),
    techEvolutionUnitBtns: document.querySelectorAll('#tech-evolution-unit-group .btn-pill'),
    // Production Technology Chart Elements
    prodTotalKilos: document.getElementById('prod-total-kilos'),
    prodTotalRegistros: document.getElementById('prod-total-registros'),
    btnProdViewPie: document.getElementById('btn-prod-view-pie'),
    btnProdViewDonut: document.getElementById('btn-prod-view-donut'),
    prodChartViewBtns: document.querySelectorAll('#prod-chart-view-group .btn-pill')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    initSidebarState();
    initCharts();
    setupEventListeners();
    initChatWidget();
    await loadFilterOptions();
    await fetchDashboardData();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('dashboard_theme_pref') || 'light';
    setTheme(savedTheme);
}

function setTheme(theme) {
    AppState.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('dashboard_theme_pref', theme);
    if (elements.themeIcon) {
        elements.themeIcon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    }
    // Re-apply charts theme colors if initialized
    if (AppState.charts.scatter) {
        updateAllChartsTheme();
    }
}

// Sidebar Collapsing & Expanding
function initSidebarState() {
    const isCollapsed = localStorage.getItem('filters_collapsed') === 'true';
    if (isCollapsed) {
        setSidebarCollapsed(true, false);
    }
}

function setSidebarCollapsed(collapsed, animate = true) {
    if (!elements.mainLayout) return;
    elements.mainLayout.classList.toggle('filters-collapsed', collapsed);
    localStorage.setItem('filters_collapsed', collapsed ? 'true' : 'false');
    
    if (elements.btnToggleFilters) {
        elements.btnToggleFilters.title = collapsed ? 'Mostrar panel de filtros' : 'Ocultar panel de filtros';
    }
    const icon = elements.btnToggleFilters ? elements.btnToggleFilters.querySelector('i') : null;
    if (icon) {
        icon.className = collapsed ? 'fa-solid fa-filter' : 'fa-solid fa-sliders';
    }

    // Smoothly resize all charts
    resizeAllCharts();
}

function toggleSidebar() {
    const isCurrentlyCollapsed = elements.mainLayout ? elements.mainLayout.classList.contains('filters-collapsed') : false;
    setSidebarCollapsed(!isCurrentlyCollapsed, true);
}

function resizeAllCharts() {
    Object.values(AppState.charts).forEach(c => {
        if (c) c.resize();
    });
    setTimeout(() => {
        Object.values(AppState.charts).forEach(c => {
            if (c) c.resize();
        });
    }, 100);
    setTimeout(() => {
        Object.values(AppState.charts).forEach(c => {
            if (c) c.resize();
        });
    }, 320);
}

// Chart Initialization
function initCharts() {
    const chartConfigs = [
        { key: 'scatter', elId: 'chart-scatter' },
        { key: 'distribution', elId: 'chart-distribution' },
        { key: 'control', elId: 'chart-control' },
        { key: 'boxplot', elId: 'chart-boxplot' },
        { key: 'compliance', elId: 'chart-compliance' },
        { key: 'technology', elId: 'chart-technology' },
        { key: 'techEvolution', elId: 'chart-tech-evolution' },
        { key: 'productionTechnology', elId: 'chart-production-technology' }
    ];

    chartConfigs.forEach(cfg => {
        const el = document.getElementById(cfg.elId);
        if (el) {
            AppState.charts[cfg.key] = echarts.init(el);
        }
    });

    window.addEventListener('resize', () => {
        resizeAllCharts();
    });

    // ResizeObserver on dashboard-content to ensure charts always adapt with zero overflow
    const dashboardContent = document.querySelector('.dashboard-content');
    if (dashboardContent && window.ResizeObserver) {
        const ro = new ResizeObserver(() => {
            resizeAllCharts();
        });
        ro.observe(dashboardContent);
    }
}

function getChartColors() {
    const isDark = AppState.theme === 'dark';
    return {
        text: isDark ? '#94a3b8' : '#64748b',
        title: isDark ? '#f8fafc' : '#0f172a',
        splitLine: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)',
        tooltipBg: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)',
        tooltipBorder: isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.1)',
        tooltipText: isDark ? '#f8fafc' : '#0f172a',
        areaStart: isDark ? 'rgba(59, 130, 246, 0.25)' : 'rgba(2, 132, 199, 0.20)',
        areaEnd: isDark ? 'rgba(59, 130, 246, 0.02)' : 'rgba(2, 132, 199, 0.01)'
    };
}

function updateAllChartsTheme() {
    // Redraw charts with theme changes
    fetchDashboardData();
}

// Event Listeners
function setupEventListeners() {
    // Presentation Mode Toggle
    if (elements.btnTogglePresentation) {
        elements.btnTogglePresentation.addEventListener('click', () => {
            AppState.presentationMode = !AppState.presentationMode;
            document.body.classList.toggle('presentation-mode', AppState.presentationMode);
            elements.btnTogglePresentation.classList.toggle('active', AppState.presentationMode);

            if (AppState.presentationMode) {
                elements.btnTogglePresentation.innerHTML = '<i class="fa-solid fa-compress"></i>';
                elements.btnTogglePresentation.title = 'Salir del modo presentación y restaurar paneles';
            } else {
                elements.btnTogglePresentation.innerHTML = '<i class="fa-solid fa-chalkboard-user"></i>';
                elements.btnTogglePresentation.title = 'Modo presentación enfocado en tecnologías';
            }

            resizeAllCharts();
        });
    }

    // Theme toggle
    elements.btnThemeToggle.addEventListener('click', () => {
        setTheme(AppState.theme === 'dark' ? 'light' : 'dark');
    });

    // Form submit (Apply filters)
    elements.filterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        syncFiltersFromUI();
        AppState.tablePagination.page = 1;
        fetchDashboardData();
    });

    // Reactive auto-update on dropdown filter selection
    [
        elements.selectTurno,
        elements.selectLinea,
        elements.selectFormato,
        elements.selectVariedad,
        elements.selectTecnologia,
        elements.selectCliente
    ].forEach(sel => {
        sel?.addEventListener('change', () => {
            syncFiltersFromUI();
            AppState.tablePagination.page = 1;
            fetchDashboardData();
        });
    });

    // Reset filters
    elements.btnResetFilters.addEventListener('click', () => {
        elements.filterForm.reset();
        // Reset to last 30 days preset
        applyDatePreset('30d');
        syncFiltersFromUI();
        AppState.tablePagination.page = 1;
        fetchDashboardData();
    });

    // Date Presets
    elements.presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.presetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            applyDatePreset(btn.dataset.preset);
            syncFiltersFromUI();
            AppState.tablePagination.page = 1;
            fetchDashboardData();
        });
    });

    // Export CSV
    elements.btnExportCsv.addEventListener('click', () => {
        syncFiltersFromUI();
        const params = buildQueryParams(AppState.filters);
        window.location.href = `/api/export?${params}`;
    });

    // Pagination
    elements.btnPagePrev.addEventListener('click', () => {
        if (AppState.tablePagination.page > 1) {
            AppState.tablePagination.page--;
            fetchSamplesTable();
        }
    });

    elements.btnPageNext.addEventListener('click', () => {
        if (AppState.tablePagination.page < AppState.tablePagination.totalPages) {
            AppState.tablePagination.page++;
            fetchSamplesTable();
        }
    });

    // Modal Close
    elements.btnCloseModal.addEventListener('click', closeModal);
    elements.btnModalDismiss.addEventListener('click', closeModal);
    elements.sampleModal.addEventListener('click', (e) => {
        if (e.target === elements.sampleModal) closeModal();
    });

    // Sidebar Toggle Buttons
    elements.btnToggleFilters?.addEventListener('click', toggleSidebar);
    elements.btnCollapseSidebar?.addEventListener('click', () => setSidebarCollapsed(true));
    elements.btnFloatingFilterToggle?.addEventListener('click', () => setSidebarCollapsed(false));

    // Guide Modal
    elements.btnOpenGuide?.addEventListener('click', openGuideModal);
    elements.btnCloseGuideModal?.addEventListener('click', closeGuideModal);
    elements.btnGuideModalDismiss?.addEventListener('click', closeGuideModal);
    elements.guideModal?.addEventListener('click', (e) => {
        if (e.target === elements.guideModal) closeGuideModal();
    });

    // Technology Chart Mode Buttons
    elements.btnTechModeDev?.addEventListener('click', () => setTechChartMode('dev'));
    elements.btnTechModeBase?.addEventListener('click', () => setTechChartMode('base'));
    elements.btnTechModeGrams?.addEventListener('click', () => setTechChartMode('grams'));

    // Technology Evolution Select & Unit Buttons
    elements.selectEvolutionTech?.addEventListener('change', (e) => {
        AppState.techEvolutionSelectedTech = e.target.value;
        fetchTechnologyEvolution();
    });

    elements.techEvolutionUnitBtns?.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.techEvolutionUnitBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            AppState.techEvolutionUnit = btn.dataset.unit || 'day';
            fetchTechnologyEvolution();
        });
    });

    // Production Technology View Mode (Pie vs Donut)
    elements.btnProdViewPie?.addEventListener('click', () => setProdChartViewMode('pie'));
    elements.btnProdViewDonut?.addEventListener('click', () => setProdChartViewMode('donut'));
}

function setProdChartViewMode(mode) {
    AppState.prodChartViewMode = mode;
    elements.prodChartViewBtns?.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === mode);
    });
    if (AppState.prodData) {
        renderProductionTechnologyChart(AppState.prodData);
    }
}

function applyDatePreset(preset) {
    if (!AppState.maxAvailableDate) return;
    const maxDate = new Date(AppState.maxAvailableDate);

    if (preset === 'all') {
        elements.fechaDesde.value = AppState.minAvailableDate;
        elements.fechaHasta.value = AppState.maxAvailableDate;
    } else if (preset === '30d') {
        const d30 = new Date(maxDate);
        d30.setDate(d30.getDate() - 30);
        elements.fechaDesde.value = d30.toISOString().split('T')[0];
        elements.fechaHasta.value = AppState.maxAvailableDate;
    } else if (preset === '7d') {
        const d7 = new Date(maxDate);
        d7.setDate(d7.getDate() - 7);
        elements.fechaDesde.value = d7.toISOString().split('T')[0];
        elements.fechaHasta.value = AppState.maxAvailableDate;
    }
}

function syncFiltersFromUI() {
    AppState.filters = {
        fecha_desde: elements.fechaDesde.value || '',
        fecha_hasta: elements.fechaHasta.value || '',
        turno: elements.selectTurno.value || '',
        linea: elements.selectLinea.value || '',
        viaje: elements.inputViaje.value.trim() || '',
        formato: elements.selectFormato.value || '',
        variedad: elements.selectVariedad.value || '',
        tipo_tecnologia: elements.selectTecnologia.value || '',
        cliente: elements.selectCliente.value || ''
    };
}

function buildQueryParams(filterObj) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filterObj)) {
        if (v !== '' && v !== null && v !== undefined) {
            params.append(k, v);
        }
    }
    return params.toString();
}

// Load Distinct Filter Options
async function loadFilterOptions() {
    try {
        const res = await fetch('/api/filters');
        const json = await res.json();
        if (json.status !== 'success') return;

        const data = json.data;
        AppState.minAvailableDate = data.date_range.min;
        AppState.maxAvailableDate = data.date_range.max;

        // Set default to last 30 days
        applyDatePreset('30d');
        elements.presetBtns.forEach(b => {
            if (b.dataset.preset === '30d') b.classList.add('active');
        });
        syncFiltersFromUI();

        // Populate Lineas
        populateSelect(elements.selectLinea, data.lineas, 'Todas las Líneas');
        // Populate Formatos
        populateSelect(elements.selectFormato, data.formatos, 'Todos los Formatos');
        // Populate Variedades
        populateSelect(elements.selectVariedad, data.variedades, 'Todas las Variedades');
        // Populate Tecnologias
        populateSelect(elements.selectTecnologia, data.tecnologias, 'Todas las Tecnologías');
        // Populate Clientes
        populateSelect(elements.selectCliente, data.clientes, 'Todos los Clientes');

    } catch (err) {
        console.error('Error loading filter options:', err);
    }
}

function populateSelect(selectEl, items, defaultLabel) {
    selectEl.innerHTML = `<option value="">${defaultLabel}</option>`;
    items.forEach(item => {
        if (!item) return;
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        selectEl.appendChild(opt);
    });
}

// Main Data Fetcher
async function fetchDashboardData() {
    showLoading(true);
    const query = buildQueryParams(AppState.filters);

    try {
        await Promise.all([
            fetchKPIs(query),
            fetchScatterData(query),
            fetchDistributionData(query),
            fetchControlChartData(query),
            fetchLinesComparison(query),
            fetchTechnologyComparison(query),
            fetchTechnologiesList(query),
            fetchProductionTechnology(query),
            fetchSamplesTable()
        ]);
        await fetchTechnologyEvolution();
    } catch (err) {
        console.error('Error fetching dashboard data:', err);
    } finally {
        showLoading(false);
    }
}

function showLoading(show) {
    if (elements.loadingOverlay) {
        if (show) {
            elements.loadingOverlay.classList.add('active');
        } else {
            elements.loadingOverlay.classList.remove('active');
        }
    }
}

// Fetch & Update KPIs
async function fetchKPIs(query) {
    const res = await fetch(`/api/kpis?${query}`);
    const json = await res.json();
    if (json.status !== 'success') return;
    const kpi = json.data;

    elements.kpiTotalMuestreos.textContent = kpi.total_muestreos.toLocaleString();
    elements.kpiTotalClamshells.textContent = `${kpi.total_clamshells.toLocaleString()} clamshells pesados`;

    elements.kpiPesoPromedio.textContent = kpi.peso_promedio.toFixed(1);
    elements.kpiTolerancia.textContent = `Límites: Mín ${kpi.peso_min_promedio}g | Máx ${kpi.peso_max_promedio}g (σ = ${kpi.desv_estandar}g)`;

    elements.kpiPctEnRango.textContent = `${kpi.pct_en_rango}%`;
    elements.progressEnRango.style.width = `${Math.min(100, Math.max(0, kpi.pct_en_rango))}%`;
    elements.kpiCountEnRango.textContent = `${kpi.count_en_rango.toLocaleString()} unidades dentro`;

    elements.kpiPctBajoPeso.textContent = `${kpi.pct_bajo_peso}%`;
    elements.kpiCountBajoPeso.textContent = `${kpi.count_bajo_peso.toLocaleString()} unidades (&lt; mín)`;
    if (kpi.pct_bajo_peso > 5) {
        elements.kpiTagRiesgo.textContent = 'ALERTA: Alto Riesgo';
        elements.kpiTagRiesgo.className = 'kpi-alert-tag tag-red';
    } else {
        elements.kpiTagRiesgo.textContent = 'Riesgo bajo';
        elements.kpiTagRiesgo.className = 'kpi-alert-tag tag-red';
    }

    elements.kpiPctSobrepeso.textContent = `${kpi.pct_sobrepeso}%`;
    elements.kpiGiveawayG.textContent = `+${kpi.giveaway_promedio_g}g / u | Total: ${(kpi.giveaway_total_g / 1000).toFixed(1)} kg`;

    elements.kpiCpk.textContent = kpi.cpk.toFixed(2);
    elements.kpiCp.textContent = `Cp: ${kpi.cp.toFixed(2)}`;
    elements.kpiCpkStatus.textContent = kpi.cpk_status;

    // Status styling
    if (kpi.cpk >= 1.33) {
        elements.kpiCpkStatus.className = 'badge-status status-excellent';
    } else if (kpi.cpk >= 1.0) {
        elements.kpiCpkStatus.className = 'badge-status status-acceptable';
    } else if (kpi.cpk >= 0.67) {
        elements.kpiCpkStatus.className = 'badge-status status-warning';
    } else {
        elements.kpiCpkStatus.className = 'badge-status status-danger';
    }

    elements.dbStatusText.textContent = `Filtrados: ${kpi.total_muestreos.toLocaleString()} muestreos (${kpi.total_clamshells.toLocaleString()} pesajes)`;
}

// 1. Scatter Plot (Gráfico de Dispersión)
async function fetchScatterData(query) {
    const res = await fetch(`/api/scatter?${query}&max_points=3500`);
    const json = await res.json();
    if (json.status !== 'success') return;
    const data = json.data;

    const colors = getChartColors();
    const chart = AppState.charts.scatter;
    if (!chart) return;

    // Group points by status for series color coding
    const inSpecPoints = [];
    const underPoints = [];
    const overPoints = [];

    data.points.forEach(pt => {
        const item = [pt.x, pt.y, pt];
        if (pt.status === 'in_spec') {
            inSpecPoints.push(item);
        } else if (pt.status === 'underweight') {
            underPoints.push(item);
        } else {
            overPoints.push(item);
        }
    });

    const markLines = [];
    if (data.lsl > 0) {
        markLines.push({
            yAxis: data.lsl,
            name: 'LSL (Mínimo)',
            lineStyle: { color: colors.underweight, type: 'dashed', width: 2 },
            label: { formatter: `Mín: {c}g`, position: 'insideEndTop', color: colors.underweight, fontSize: 11, fontWeight: 'bold' }
        });
    }
    if (data.usl > 0) {
        markLines.push({
            yAxis: data.usl,
            name: 'USL (Máximo)',
            lineStyle: { color: colors.overweight, type: 'dashed', width: 2 },
            label: { formatter: `Máx: {c}g`, position: 'insideEndTop', color: colors.overweight, fontSize: 11, fontWeight: 'bold' }
        });
    }
    if (data.nominal > 0) {
        markLines.push({
            yAxis: data.nominal,
            name: 'Target (Nominal)',
            lineStyle: { color: colors.nominal, type: 'dotted', width: 1.5 },
            label: { formatter: `Target: {c}g`, position: 'insideStartTop', color: colors.nominal, fontSize: 11 }
        });
    }

    const option = {
        backgroundColor: 'transparent',
        animationDuration: 600,
        grid: {
            left: '4%',
            right: '4%',
            top: '12%',
            bottom: '15%',
            containLabel: true
        },
        tooltip: {
            trigger: 'item',
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            textStyle: { color: colors.tooltipText, fontFamily: 'Plus Jakarta Sans' },
            formatter: (params) => {
                const pt = params.data[2];
                if (!pt) return '';
                const diff = (pt.y - pt.max).toFixed(1);
                const statusBadge = pt.status === 'in_spec'
                    ? '<span style="color:#10b981;font-weight:bold">● En Norma</span>'
                    : (pt.status === 'underweight'
                        ? '<span style="color:#f43f5e;font-weight:bold">▲ Bajo Peso (&lt; Mín)</span>'
                        : '<span style="color:#f59e0b;font-weight:bold">▼ Sobrepeso (&gt; Máx)</span>');

                return `
                    <div style="font-size:12px;min-width:180px">
                        <div style="font-weight:bold;margin-bottom:4px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:3px">
                            ${pt.date} | ${pt.line} (${pt.t})
                        </div>
                        <div><b>Formato:</b> ${pt.format}</div>
                        <div><b>Peso Medido:</b> <span style="font-size:14px;font-family:monospace;font-weight:bold">${pt.y} g</span></div>
                        <div><b>Límites:</b> [${pt.min}g - ${pt.max}g]</div>
                        <div style="margin-top:4px">${statusBadge}</div>
                    </div>
                `;
            }
        },
        xAxis: {
            type: 'value',
            name: 'Secuencia Muestreo',
            nameLocation: 'middle',
            nameGap: 30,
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: { color: colors.text, fontSize: 11 }
        },
        yAxis: {
            type: 'value',
            name: 'Peso Clamshell (g)',
            scale: true,
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: { color: colors.text, fontSize: 11 }
        },
        dataZoom: [
            {
                type: 'slider',
                show: true,
                xAxisIndex: [0],
                bottom: '2%',
                height: 22,
                borderColor: 'transparent',
                backgroundColor: 'rgba(255,255,255,0.03)',
                fillerColor: 'rgba(99, 102, 241, 0.2)',
                textStyle: { color: colors.text }
            },
            {
                type: 'inside',
                xAxisIndex: [0]
            }
        ],
        series: [
            {
                name: 'En Norma',
                type: 'scatter',
                data: inSpecPoints,
                symbolSize: 6,
                itemStyle: { color: colors.inSpec, opacity: 0.75 }
            },
            {
                name: 'Bajo Peso',
                type: 'scatter',
                data: underPoints,
                symbolSize: 8,
                itemStyle: { color: colors.underweight, opacity: 0.85 }
            },
            {
                name: 'Sobrepeso',
                type: 'scatter',
                data: overPoints,
                symbolSize: 7,
                itemStyle: { color: colors.overweight, opacity: 0.8 }
            },
            {
                name: 'Límites',
                type: 'line',
                markLine: {
                    symbol: 'none',
                    data: markLines
                }
            }
        ]
    };

    chart.setOption(option, true);
}

function findClosestBinIndex(bins, targetVal) {
    if (!bins || !bins.length || targetVal == null || isNaN(targetVal) || targetVal <= 0) return -1;
    let closestIdx = 0;
    let minDiff = Math.abs(Number(bins[0]) - Number(targetVal));
    for (let i = 1; i < bins.length; i++) {
        const diff = Math.abs(Number(bins[i]) - Number(targetVal));
        if (diff < minDiff) {
            minDiff = diff;
            closestIdx = i;
        }
    }
    return closestIdx;
}

// 2. Histograma y Curva Normal
async function fetchDistributionData(query) {
    const res = await fetch(`/api/distribution?${query}`);
    const json = await res.json();
    if (json.status !== 'success') return;
    const data = json.data;

    const colors = getChartColors();
    const isDark = AppState.theme === 'dark';
    const chart = AppState.charts.distribution;
    if (!chart) return;

    const lslIdx = findClosestBinIndex(data.bins, data.lsl);
    const uslIdx = findClosestBinIndex(data.bins, data.usl);
    const muIdx = findClosestBinIndex(data.bins, data.mu);

    const markLines = [];

    // 1. Subtle MarkArea for In-Spec Tolerance window [LSL, USL]
    let markAreaConfig = null;
    if (lslIdx !== -1 && uslIdx !== -1 && lslIdx <= uslIdx) {
        markAreaConfig = {
            silent: true,
            itemStyle: {
                color: isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.07)'
            },
            data: [[
                {
                    name: 'Tolerancia',
                    xAxis: lslIdx,
                    label: {
                        show: true,
                        position: 'insideTop',
                        color: isDark ? 'rgba(148, 163, 184, 0.75)' : 'rgba(71, 85, 105, 0.85)',
                        fontSize: 10,
                        fontWeight: '600',
                        formatter: `Zona Conforme [${data.lsl}g - ${data.usl}g]`
                    }
                },
                {
                    xAxis: uslIdx
                }
            ]]
        };
    }

    // 2. Subtle MarkLine for LSL (Peso Mínimo)
    if (lslIdx !== -1 && data.lsl > 0) {
        markLines.push({
            xAxis: lslIdx,
            name: 'Peso Mínimo',
            lineStyle: {
                color: isDark ? 'rgba(244, 63, 94, 0.75)' : 'rgba(225, 29, 72, 0.7)',
                type: 'dashed',
                width: 1.5,
                dashOffset: 2
            },
            label: {
                show: true,
                formatter: `Mín: ${data.lsl}g`,
                position: 'insideStartTop',
                distance: 6,
                fontSize: 10,
                fontWeight: '600',
                color: isDark ? '#fda4af' : '#e11d48',
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.95)',
                borderColor: isDark ? 'rgba(244, 63, 94, 0.4)' : 'rgba(225, 29, 72, 0.35)',
                borderWidth: 1,
                borderRadius: 4,
                padding: [2, 5]
            }
        });
    }

    // 3. Subtle MarkLine for USL (Peso Máximo)
    if (uslIdx !== -1 && data.usl > 0) {
        markLines.push({
            xAxis: uslIdx,
            name: 'Peso Máximo',
            lineStyle: {
                color: isDark ? 'rgba(245, 158, 11, 0.75)' : 'rgba(217, 119, 6, 0.7)',
                type: 'dashed',
                width: 1.5,
                dashOffset: 2
            },
            label: {
                show: true,
                formatter: `Máx: ${data.usl}g`,
                position: 'insideStartTop',
                distance: 6,
                fontSize: 10,
                fontWeight: '600',
                color: isDark ? '#fcd34d' : '#d97706',
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.95)',
                borderColor: isDark ? 'rgba(245, 158, 11, 0.4)' : 'rgba(217, 119, 6, 0.35)',
                borderWidth: 1,
                borderRadius: 4,
                padding: [2, 5]
            }
        });
    }

    // 4. Subtle MarkLine for Mean (μ)
    if (muIdx !== -1 && data.mu > 0) {
        markLines.push({
            xAxis: muIdx,
            name: 'Media',
            lineStyle: {
                color: colors.accent,
                type: 'solid',
                width: 1.5
            },
            label: {
                show: true,
                formatter: `μ: ${data.mu}g`,
                position: 'insideEndTop',
                distance: 6,
                fontSize: 10,
                fontWeight: 'bold',
                color: colors.accent,
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.95)',
                borderColor: isDark ? 'rgba(99, 102, 241, 0.4)' : 'rgba(99, 102, 241, 0.35)',
                borderWidth: 1,
                borderRadius: 4,
                padding: [2, 5]
            }
        });
    }

    // Update Header Badge in Bell Curve Panel
    if (elements.bellLimitsTag) {
        if (data.lsl > 0 && data.usl > 0) {
            elements.bellLimitsTag.innerHTML = `<i class="fa-solid fa-ruler-horizontal"></i> Límites: <b>Mín ${data.lsl}g</b> | <b>Máx ${data.usl}g</b>`;
            elements.bellLimitsTag.style.display = 'inline-flex';
        } else {
            elements.bellLimitsTag.style.display = 'none';
        }
    }

    const option = {
        backgroundColor: 'transparent',
        grid: { left: '5%', right: '4%', top: '15%', bottom: '12%', containLabel: true },
        tooltip: {
            trigger: 'axis',
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            textStyle: { color: colors.tooltipText }
        },
        xAxis: {
            type: 'category',
            data: data.bins,
            name: 'Peso (g)',
            nameLocation: 'middle',
            nameGap: 26,
            axisLabel: { color: colors.text, fontSize: 10, rotate: 30 }
        },
        yAxis: {
            type: 'value',
            name: 'Frecuencia (Unidades)',
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: { color: colors.text }
        },
        series: [
            {
                name: 'Frecuencia Real',
                type: 'bar',
                data: data.counts,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(99, 102, 241, 0.85)' },
                        { offset: 1, color: 'rgba(99, 102, 241, 0.25)' }
                    ]),
                    borderRadius: [4, 4, 0, 0]
                },
                markArea: markAreaConfig,
                markLine: {
                    symbol: 'none',
                    data: markLines
                }
            },
            {
                name: 'Ajuste Normal (Gauss)',
                type: 'line',
                smooth: true,
                data: data.normal_curve,
                lineStyle: { color: '#38bdf8', width: 2.5 },
                symbol: 'none'
            }
        ]
    };

    chart.setOption(option, true);
}

// 3. Gráfico de Control X-bar
async function fetchControlChartData(query) {
    const res = await fetch(`/api/control_chart?${query}`);
    const json = await res.json();
    if (json.status !== 'success') return;
    const data = json.data;

    const colors = getChartColors();
    const chart = AppState.charts.control;
    if (!chart) return;

    const labels = data.samples.map(s => s.label);
    const means = data.samples.map(s => s.mean);

    const markLines = [
        {
            yAxis: data.grand_mean,
            name: 'Gran Media',
            lineStyle: { color: colors.accent, width: 2 },
            label: { formatter: `X̄̄: ${data.grand_mean}g`, position: 'insideEndTop', color: colors.accent, fontSize: 11, fontWeight: 'bold' }
        },
        {
            yAxis: data.ucl,
            name: 'UCL (+3σ)',
            lineStyle: { color: colors.overweight, type: 'dashed', width: 1.5 },
            label: { formatter: `UCL: ${data.ucl}g`, position: 'insideEndTop', color: colors.overweight, fontSize: 10 }
        },
        {
            yAxis: data.lcl,
            name: 'LCL (-3σ)',
            lineStyle: { color: colors.underweight, type: 'dashed', width: 1.5 },
            label: { formatter: `LCL: ${data.lcl}g`, position: 'insideEndTop', color: colors.underweight, fontSize: 10 }
        }
    ];

    const option = {
        backgroundColor: 'transparent',
        grid: { left: '5%', right: '4%', top: '15%', bottom: '12%', containLabel: true },
        tooltip: {
            trigger: 'axis',
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            textStyle: { color: colors.tooltipText },
            formatter: (params) => {
                const idx = params[0].dataIndex;
                const sample = data.samples[idx];
                const ooc = sample.out_of_control ? '<span style="color:#f43f5e;font-weight:bold">⚠️ Fuera de Control (3σ)</span>' : '<span style="color:#10b981">Control Estadístico Estable</span>';
                return `
                    <div style="font-size:12px">
                        <b>Muestreo:</b> ${sample.date} - ${sample.line}<br>
                        <b>Formato:</b> ${sample.format}<br>
                        <b>Media Muestra (X̄):</b> <span style="font-family:monospace;font-weight:bold">${sample.mean} g</span><br>
                        ${ooc}
                    </div>
                `;
            }
        },
        xAxis: {
            type: 'category',
            data: labels,
            axisLabel: { show: false }
        },
        yAxis: {
            type: 'value',
            name: 'Media de Lote (g)',
            scale: true,
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: { color: colors.text }
        },
        series: [
            {
                name: 'Media por Muestreo',
                type: 'line',
                data: means,
                smooth: false,
                lineStyle: { color: '#818cf8', width: 2 },
                symbol: 'circle',
                symbolSize: 5,
                itemStyle: {
                    color: (param) => {
                        const s = data.samples[param.dataIndex];
                        return s && s.out_of_control ? colors.underweight : '#818cf8';
                    }
                },
                markLine: {
                    symbol: 'none',
                    data: markLines
                }
            }
        ]
    };

    chart.setOption(option, true);
}

// 4. Comparativa de Líneas (Boxplot & Cumplimiento)
async function fetchLinesComparison(query) {
    const res = await fetch(`/api/lines_comparison?${query}`);
    const json = await res.json();
    if (json.status !== 'success') return;
    const data = json.data;

    const colors = getChartColors();
    const chartBox = AppState.charts.boxplot;
    const chartComp = AppState.charts.compliance;

    // Boxplot
    if (chartBox) {
        const optionBox = {
            backgroundColor: 'transparent',
            grid: { left: '5%', right: '4%', top: '15%', bottom: '15%', containLabel: true },
            tooltip: {
                trigger: 'item',
                backgroundColor: colors.tooltipBg,
                borderColor: colors.tooltipBorder,
                textStyle: { color: colors.tooltipText }
            },
            xAxis: {
                type: 'category',
                data: data.lines,
                axisLabel: { color: colors.text, rotate: 35, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                name: 'Peso (g)',
                scale: true,
                splitLine: { lineStyle: { color: colors.splitLine } },
                axisLabel: { color: colors.text }
            },
            series: [
                {
                    name: 'Dispersión Línea',
                    type: 'boxplot',
                    data: data.boxplot_data,
                    itemStyle: {
                        color: 'rgba(99, 102, 241, 0.25)',
                        borderColor: '#818cf8',
                        borderWidth: 1.5
                    }
                }
            ]
        };
        chartBox.setOption(optionBox, true);
    }

    // Stacked bar compliance
    if (chartComp) {
        const lines = data.compliance.map(c => c.line);
        const inSpecs = data.compliance.map(c => c.pct_in);
        const unders = data.compliance.map(c => c.pct_under);
        const overs = data.compliance.map(c => c.pct_over);

        const optionComp = {
            backgroundColor: 'transparent',
            legend: {
                data: ['En Norma', 'Bajo Peso', 'Sobrepeso'],
                textStyle: { color: colors.text },
                top: '2%'
            },
            grid: { left: '5%', right: '4%', top: '15%', bottom: '15%', containLabel: true },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                backgroundColor: colors.tooltipBg,
                borderColor: colors.tooltipBorder,
                textStyle: { color: colors.tooltipText }
            },
            xAxis: {
                type: 'category',
                data: lines,
                axisLabel: { color: colors.text, rotate: 35, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                name: '% Distribución',
                max: 100,
                splitLine: { lineStyle: { color: colors.splitLine } },
                axisLabel: { color: colors.text, formatter: '{value}%' }
            },
            series: [
                {
                    name: 'En Norma',
                    type: 'bar',
                    stack: 'total',
                    data: inSpecs,
                    itemStyle: { color: colors.inSpec }
                },
                {
                    name: 'Bajo Peso',
                    type: 'bar',
                    stack: 'total',
                    data: unders,
                    itemStyle: { color: colors.underweight }
                },
                {
                    name: 'Sobrepeso',
                    type: 'bar',
                    stack: 'total',
                    data: overs,
                    itemStyle: { color: colors.overweight }
                }
            ]
        };
        chartComp.setOption(optionComp, true);
    }
}

// 4.5 Technology Deviation & Excess Comparison (3 Marks: Venta, Tecnologia, Real)
async function fetchTechnologyComparison(query) {
    try {
        const res = await fetch(`/api/technology_comparison?${query}`);
        const json = await res.json();
        if (json.status !== 'success') return;
        AppState.techData = json.data.technologies || [];
        renderTechnologyChart();
    } catch (err) {
        console.error('Error fetching technology comparison:', err);
    }
}

function setTechChartMode(mode) {
    AppState.techChartMode = mode;
    elements.btnTechModeBase?.classList.toggle('active', mode === 'base');
    elements.btnTechModeDev?.classList.toggle('active', mode === 'dev');
    renderTechnologyChart();
}

function renderTechnologyChart() {
    const chartTech = AppState.charts.technology;
    if (!chartTech) return;

    const techList = AppState.techData || [];
    const colors = getChartColors();
    const mode = AppState.techChartMode || 'base';

    if (techList.length === 0) {
        chartTech.clear();
        chartTech.setOption({
            title: {
                text: 'No hay datos de tecnología para los filtros aplicados',
                left: 'center',
                top: 'middle',
                textStyle: { color: colors.text, fontSize: 13, fontWeight: 'normal' }
            }
        });
        return;
    }

    const categories = techList.map(t => t.tecnologia);

    let yAxisConfig = {};
    let series1Data = []; // 1. Peso Venta
    let series2Data = []; // 2. Peso Mínimo
    let series3Data = []; // 3. Peso Máximo
    let series4Data = []; // 4. Peso Real

    if (mode === 'dev') {
        // Mode: % Desviación adicional sobre Venta (Venta = 0%, Mín = +X%, Máx = +Y%, Real = +Z%)
        const allDevs = techList.flatMap(t => [0, t.dev_minimo, t.dev_maximo, t.dev_real]);
        const minVal = Math.min(...allDevs);
        const maxVal = Math.max(...allDevs);

        yAxisConfig = {
            type: 'value',
            min: Math.floor(Math.min(0, minVal) - 1),
            max: Math.ceil(maxVal + 1.5),
            name: '% Variación vs Venta',
            nameTextStyle: { color: colors.text, fontSize: 11 },
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: {
                color: colors.text,
                formatter: val => `${val > 0 ? '+' : ''}${val}%`
            }
        };

        series1Data = techList.map(() => 0);
        series2Data = techList.map(t => t.dev_minimo);
        series3Data = techList.map(t => t.dev_maximo);
        series4Data = techList.map(t => {
            const barColor = t.status === 'under' ? '#ef4444' : (t.status === 'over' ? '#f59e0b' : '#10b981');
            return {
                value: t.dev_real,
                itemStyle: {
                    color: barColor,
                    borderRadius: [4, 4, 0, 0]
                }
            };
        });
    } else {
        // Default Mode: % Base 100% (Venta = 100%, Mín = 102.5%, Máx = 103.7%, Real = 102.0%)
        const allPcts = techList.flatMap(t => [100, t.pct_minimo, t.pct_maximo, t.pct_real]);
        const minVal = Math.min(...allPcts);
        const maxVal = Math.max(...allPcts);

        yAxisConfig = {
            type: 'value',
            min: Math.floor(Math.min(95, minVal - 1.5)),
            max: Math.ceil(maxVal + 3.0),
            name: '% del Peso Venta (Base 100)',
            nameTextStyle: { color: colors.text, fontSize: 11 },
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: {
                color: colors.text,
                formatter: '{value}%'
            }
        };

        series1Data = techList.map(() => 100.0);
        series2Data = techList.map(t => t.pct_minimo);
        series3Data = techList.map(t => t.pct_maximo);
        series4Data = techList.map(t => {
            const barColor = t.status === 'under' ? '#ef4444' : (t.status === 'over' ? '#f59e0b' : '#10b981');
            return {
                value: t.pct_real,
                itemStyle: {
                    color: barColor,
                    borderRadius: [4, 4, 0, 0]
                }
            };
        });
    }

    const option = {
        grid: {
            top: 70,
            right: 25,
            bottom: categories.length > 4 ? 70 : 45,
            left: 55,
            containLabel: true
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            confine: true,
            extraCssText: 'box-shadow: 0 10px 25px rgba(0,0,0,0.2); border-radius: 8px; z-index: 100;',
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            textStyle: { color: colors.tooltipText },
            formatter: function(params) {
                if (!params || params.length === 0) return '';
                const idx = params[0].dataIndex;
                const item = techList[idx];
                if (!item) return '';

                const realColor = item.status === 'under' ? '#ef4444' : (item.status === 'over' ? '#f59e0b' : '#10b981');
                const signalIcon = item.status === 'under' ? '⚠️' : (item.status === 'over' ? '⚠️' : '✓');
                
                let alertBox = '';
                if (item.status === 'under') {
                    alertBox = `
                        <div style="margin-top:8px;padding:6px 10px;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);border-radius:6px;color:#ef4444;font-size:0.75rem;font-weight:600">
                            🚨 BAJO MÍNIMO: Falta ${Math.abs(item.diff_pct)}% para alcanzar la tolerancia de deshidratación
                        </div>`;
                } else if (item.status === 'over') {
                    alertBox = `
                        <div style="margin-top:8px;padding:6px 10px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);border-radius:6px;color:#f59e0b;font-size:0.75rem;font-weight:600">
                            ⚠️ SOBRE MÁXIMO: Exceso de +${item.diff_pct}% de fruta sobre el límite superior
                        </div>`;
                } else {
                    alertBox = `
                        <div style="margin-top:8px;padding:6px 10px;background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);border-radius:6px;color:#10b981;font-size:0.75rem;font-weight:600">
                            ✓ Cumplimiento conforme: dentro de la ventana de control [${item.pct_minimo}% - ${item.pct_maximo}%]
                        </div>`;
                }

                return `
                    <div style="font-size:0.85rem;min-width:280px;line-height:1.4">
                        <div style="font-weight:700;margin-bottom:3px;color:${colors.title};font-size:0.95rem">
                            📦 ${item.tecnologia}
                        </div>
                        <div style="font-size:0.75rem;color:${colors.text};margin-bottom:8px">
                            Muestreos analizados: <b>${item.n_muestreos.toLocaleString()}</b>
                        </div>
                        <hr style="border:none;border-top:1px solid ${colors.splitLine};margin:6px 0">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#94a3b8;margin-right:6px"></span>1. Peso Venta (Base):</span>
                            <b>100.0%</b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#0284c7;margin-right:6px"></span>2. Peso Mínimo con Tecnología:</span>
                            <b><span style="color:#0284c7;font-weight:bold">${item.pct_minimo}%</span></b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#6366f1;margin-right:6px"></span>3. Peso Máximo de Control:</span>
                            <b><span style="color:#6366f1;font-weight:bold">${item.pct_maximo}%</span></b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${realColor};margin-right:6px"></span>4. Peso Real Medido:</span>
                            <b><span style="color:${realColor};font-weight:bold">${item.pct_real}%</span></b>
                        </div>
                        <hr style="border:none;border-top:1px solid ${colors.splitLine};margin:6px 0">
                        <div style="display:flex;justify-content:space-between;align-items:center;color:${realColor};font-weight:700">
                            <span>Señal de Rango:</span>
                            <span style="font-size:0.9rem">${signalIcon} ${item.signal}</span>
                        </div>
                        ${alertBox}
                    </div>
                `;
            }
        },
        legend: {
            show: false
        },
        xAxis: {
            type: 'category',
            data: categories,
            axisLabel: {
                color: colors.text,
                rotate: categories.length > 4 ? 25 : 0,
                interval: 0,
                fontSize: 11,
                formatter: function(val) {
                    if (val.length > 22) return val.substring(0, 20) + '...';
                    return val;
                }
            },
            axisLine: { lineStyle: { color: colors.splitLine } },
            axisTick: { alignWithLabel: true }
        },
        yAxis: yAxisConfig,
        series: [
            {
                name: '1. Peso Venta (100%)',
                type: 'bar',
                barGap: '26%',
                barMaxWidth: 24,
                data: series1Data,
                itemStyle: {
                    color: '#94a3b8',
                    borderRadius: [3, 3, 0, 0]
                },
                label: {
                    show: true,
                    position: 'top',
                    distance: 4,
                    formatter: () => mode === 'dev' ? '0%' : '100%',
                    fontSize: 8.5,
                    color: colors.text
                }
            },
            {
                name: '2. Peso Mínimo',
                type: 'bar',
                barMaxWidth: 24,
                data: series2Data,
                itemStyle: {
                    color: '#0284c7',
                    borderRadius: [3, 3, 0, 0]
                },
                label: {
                    show: true,
                    position: 'top',
                    distance: 4,
                    formatter: function(p) {
                        const item = techList[p.dataIndex];
                        return mode === 'dev' ? `+${Number(item.dev_minimo).toFixed(1)}%` : `${Number(item.pct_minimo).toFixed(1)}%`;
                    },
                    fontSize: 8.5,
                    color: '#0284c7',
                    fontWeight: 'bold'
                }
            },
            {
                name: '3. Peso Máximo',
                type: 'bar',
                barMaxWidth: 24,
                data: series3Data,
                itemStyle: {
                    color: '#6366f1',
                    borderRadius: [3, 3, 0, 0]
                },
                label: {
                    show: true,
                    position: 'top',
                    distance: 4,
                    formatter: function(p) {
                        const item = techList[p.dataIndex];
                        return mode === 'dev' ? `+${Number(item.dev_maximo).toFixed(1)}%` : `${Number(item.pct_maximo).toFixed(1)}%`;
                    },
                    fontSize: 8.5,
                    color: '#6366f1',
                    fontWeight: 'bold'
                }
            },
            {
                name: '4. Peso Real Medido',
                type: 'bar',
                barMaxWidth: 24,
                data: series4Data,
                label: {
                    show: true,
                    position: 'top',
                    distance: 7,
                    formatter: function(p) {
                        const item = techList[p.dataIndex];
                        if (!item) return '';
                        return mode === 'dev' 
                            ? `${item.dev_real > 0 ? '+' : ''}${Number(item.dev_real).toFixed(1)}%` 
                            : `${Number(item.pct_real).toFixed(1)}%`;
                    },
                    fontSize: 9.5,
                    fontWeight: 'bold',
                    color: function(p) {
                        const item = techList[p.dataIndex];
                        if (!item) return colors.text;
                        return item.status === 'under' ? '#ef4444' : (item.status === 'over' ? '#f59e0b' : '#10b981');
                    }
                }
            },
            {
                // 5th invisible series: renders deviation badge INSIDE the bar.
                // Transparent bars, but ECharts labels with position:'inside' always
                // render on top of the bar fill, solving z-order issues entirely.
                name: '5. Desviación (interno)',
                type: 'bar',
                barMaxWidth: 24,
                stack: null,
                data: series4Data.map((d, i) => {
                    const item = techList[i];
                    const val = typeof d === 'object' ? d.value : d;
                    const isDark = AppState.theme === 'dark';
                    return {
                        value: val,
                        itemStyle: { color: 'transparent', borderColor: 'transparent' },
                        label: {
                            color: isDark ? '#f8fafc' : '#0f172a'
                        }
                    };
                }),
                label: {
                    show: true,
                    position: 'inside',
                    color: AppState.theme === 'dark' ? '#f8fafc' : '#0f172a',
                    fontSize: 9.5,
                    fontWeight: 'bold',
                    formatter: function(p) {
                        const item = techList[p.dataIndex];
                        if (!item) return '';
                        const txt = item.status === 'in_range'
                            ? '✓ OK'
                            : (item.diff_pct > 0 ? `+${item.diff_pct.toFixed(1)}%` : `${item.diff_pct.toFixed(1)}%`);
                        return `{badgeText|${txt}}`;
                    },
                    rich: {
                        badgeText: {
                            color: AppState.theme === 'dark' ? '#f8fafc' : '#0f172a',
                            fontSize: 9.5,
                            fontWeight: 'bold'
                        }
                    },
                    backgroundColor: AppState.theme === 'dark' ? 'rgba(255, 255, 255, 0.09)' : 'rgba(100, 116, 139, 0.14)',
                    borderColor: AppState.theme === 'dark' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(100, 116, 139, 0.25)',
                    borderWidth: 1,
                    borderRadius: 4,
                    padding: [3, 5],
                    textBorderWidth: 0,
                    textBorderColor: 'transparent'
                },
                tooltip: { show: false },
                silent: true
            }
        ]
    };

    chartTech.setOption(option, true);
}

// Deviation badges are now rendered via the 5th transparent bar series (position:'inside').
// This stub is kept for backward compatibility with any lingering references.
function updateTechCenterBadges() {}

// 4.6 Single Technology Temporal Evolution Chart
async function fetchTechnologiesList(query = '') {
    try {
        const url = query ? `/api/technologies?${query}` : '/api/technologies';
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'success') return;
        const techs = json.data || [];
        AppState.technologiesList = techs;

        if (elements.selectEvolutionTech) {
            const currentSelected = AppState.techEvolutionSelectedTech || elements.selectEvolutionTech.value;
            elements.selectEvolutionTech.innerHTML = '';

            if (techs.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = '(Sin tecnologías en el rango)';
                elements.selectEvolutionTech.appendChild(opt);
                AppState.techEvolutionSelectedTech = null;
                return;
            }

            techs.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.tecnologia;
                const sampleWord = t.n_muestreos === 1 ? 'muestra' : 'muestras';
                opt.textContent = `${t.tecnologia} (${t.n_muestreos.toLocaleString()} ${sampleWord})`;
                elements.selectEvolutionTech.appendChild(opt);
            });

            const exists = techs.some(t => t.tecnologia === currentSelected);
            if (exists) {
                elements.selectEvolutionTech.value = currentSelected;
                AppState.techEvolutionSelectedTech = currentSelected;
            } else {
                elements.selectEvolutionTech.value = techs[0].tecnologia;
                AppState.techEvolutionSelectedTech = techs[0].tecnologia;
            }
        }
    } catch (err) {
        console.error('Error fetching technologies list:', err);
    }
}

async function fetchTechnologyEvolution() {
    const chart = AppState.charts.techEvolution;
    if (!chart) return;

    try {
        const query = buildQueryParams(AppState.filters);
        const selectedTech = AppState.techEvolutionSelectedTech || (elements.selectEvolutionTech?.value || '');
        const timeUnit = AppState.techEvolutionUnit || 'day';

        const url = `/api/technology_evolution?${query}&technology=${encodeURIComponent(selectedTech)}&time_unit=${timeUnit}`;
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'success') return;

        AppState.techEvolutionData = json.data;
        renderTechEvolutionChart(json.data);
    } catch (err) {
        console.error('Error fetching technology evolution:', err);
    }
}

function renderTechEvolutionChart(data) {
    const chart = AppState.charts.techEvolution;
    if (!chart) return;

    const colors = getChartColors();
    if (!data || !data.series || data.series.length === 0) {
        chart.clear();
        chart.setOption({
            title: {
                text: `No hay datos temporales para la tecnología "${data?.technology || ''}" con los filtros actuales`,
                left: 'center',
                top: 'middle',
                textStyle: { color: colors.text, fontSize: 13, fontWeight: 'normal' }
            }
        });
        return;
    }

    const series = data.series;
    const periods = series.map(s => s.periodo);
    const realPcts = series.map(s => s.pct_real);
    const globalMin = data.global_pct_minimo || 102.5;
    const globalMax = data.global_pct_maximo || 103.7;

    const allVals = realPcts.concat([globalMin, globalMax, 100.0]);
    const minVal = Math.min(...allVals);
    const maxVal = Math.max(...allVals);
    const yPad = Math.max(1.0, (maxVal - minVal) * 0.2);

    const option = {
        grid: {
            top: 60,
            right: 50,
            bottom: periods.length > 8 ? 65 : 45,
            left: 55,
            containLabel: true
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'line',
                lineStyle: { color: colors.splitLine, width: 1.5, type: 'dashed' }
            },
            confine: true,
            extraCssText: 'box-shadow: 0 10px 25px rgba(0,0,0,0.2); border-radius: 8px; z-index: 100;',
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            textStyle: { color: colors.tooltipText },
            formatter: function(params) {
                if (!params || params.length === 0) return '';
                const idx = params[0].dataIndex;
                const pt = series[idx];
                if (!pt) return '';

                const statusColor = pt.status === 'under' ? '#ef4444' : (pt.status === 'over' ? '#f59e0b' : '#10b981');
                const statusIcon = pt.status === 'under' ? '⚠️' : (pt.status === 'over' ? '⚠️' : '✓');

                return `
                    <div style="font-size:0.85rem;min-width:260px;line-height:1.4">
                        <div style="font-weight:700;margin-bottom:2px;color:${colors.title};font-size:0.95rem">
                            📅 ${pt.periodo} — ${data.technology}
                        </div>
                        <div style="font-size:0.75rem;color:${colors.text};margin-bottom:8px">
                            Muestreos en este período: <b>${pt.n_muestreos.toLocaleString()}</b>
                        </div>
                        <hr style="border:none;border-top:1px solid ${colors.splitLine};margin:6px 0">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#94a3b8;margin-right:6px"></span>1. Peso Venta (Base):</span>
                            <b>100.0%</b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#0284c7;margin-right:6px"></span>2. Límite Mínimo (Período):</span>
                            <b><span style="color:#0284c7;font-weight:bold">${pt.pct_minimo}%</span></b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#6366f1;margin-right:6px"></span>3. Límite Máximo (Período):</span>
                            <b><span style="color:#6366f1;font-weight:bold">${pt.pct_maximo}%</span></b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                            <span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${statusColor};margin-right:6px"></span>4. Peso Real Medido:</span>
                            <b><span style="color:${statusColor};font-weight:bold">${pt.pct_real}%</span></b>
                        </div>
                        <hr style="border:none;border-top:1px solid ${colors.splitLine};margin:6px 0">
                        <div style="display:flex;justify-content:space-between;align-items:center;color:${statusColor};font-weight:700">
                            <span>Señal de Rango:</span>
                            <span style="font-size:0.9rem">${statusIcon} ${pt.signal}</span>
                        </div>
                    </div>
                `;
            }
        },
        xAxis: {
            type: 'category',
            data: periods,
            axisLabel: {
                color: colors.text,
                rotate: periods.length > 8 ? 35 : 0,
                interval: 0,
                fontSize: 11
            },
            axisLine: { lineStyle: { color: colors.splitLine } },
            axisTick: { alignWithLabel: true }
        },
        yAxis: {
            type: 'value',
            name: '% del Peso Venta (Base 100)',
            min: Math.floor((minVal - yPad) * 10) / 10,
            max: Math.ceil((maxVal + yPad) * 10) / 10,
            nameTextStyle: { color: colors.text, fontSize: 11 },
            splitLine: { lineStyle: { color: colors.splitLine } },
            axisLabel: {
                color: colors.text,
                formatter: '{value}%'
            }
        },
        series: [
            {
                name: 'Peso Real Medido',
                type: 'line',
                data: series.map(s => {
                    const ptColor = s.status === 'under' ? '#ef4444' : (s.status === 'over' ? '#f59e0b' : '#10b981');
                    return {
                        value: s.pct_real,
                        itemStyle: {
                            color: ptColor,
                            borderColor: '#ffffff',
                            borderWidth: 2
                        }
                    };
                }),
                smooth: true,
                symbol: 'circle',
                symbolSize: 8,
                lineStyle: {
                    color: '#10b981',
                    width: 2.5
                },
                markArea: {
                    silent: true,
                    itemStyle: {
                        color: 'rgba(16, 185, 129, 0.08)'
                    },
                    data: [
                        [
                            {
                                yAxis: globalMin,
                                name: 'Rango Conforme'
                            },
                            {
                                yAxis: globalMax
                            }
                        ]
                    ]
                },
                markLine: {
                    symbol: 'none',
                    silent: false,
                    data: [
                        {
                            yAxis: globalMin,
                            name: 'Límite Mínimo',
                            lineStyle: { color: '#0284c7', type: 'dashed', width: 2 },
                            label: {
                                show: true,
                                position: 'insideEndTop',
                                formatter: `Mínimo Global: ${globalMin}%`,
                                color: '#0284c7',
                                fontSize: 10,
                                fontWeight: 'bold'
                            }
                        },
                        {
                            yAxis: globalMax,
                            name: 'Límite Máximo',
                            lineStyle: { color: '#6366f1', type: 'dashed', width: 2 },
                            label: {
                                show: true,
                                position: 'insideEndTop',
                                formatter: `Máximo Global: ${globalMax}%`,
                                color: '#6366f1',
                                fontSize: 10,
                                fontWeight: 'bold'
                            }
                        }
                    ]
                }
            }
        ]
    };

    chart.setOption(option, true);
}

// 4.7 Distribución de Producción por Tecnología (Gráfico de Torta / Dona)
async function fetchProductionTechnology(query = '') {
    const chart = AppState.charts.productionTechnology;
    if (!chart) return;

    try {
        const url = query ? `/api/production_technology?${query}` : '/api/production_technology';
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'success') return;

        AppState.prodData = json.data;

        // Update badge stats in panel header
        if (elements.prodTotalKilos) {
            const kg = json.data.total_kilos || 0;
            elements.prodTotalKilos.textContent = `${Number(kg).toLocaleString('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg`;
        }
        if (elements.prodTotalRegistros) {
            elements.prodTotalRegistros.textContent = Number(json.data.total_registros || 0).toLocaleString('es-PE');
        }

        renderProductionTechnologyChart(json.data);
    } catch (err) {
        console.error('Error fetching production technology distribution:', err);
    }
}

function renderProductionTechnologyChart(data) {
    const chart = AppState.charts.productionTechnology;
    if (!chart) return;

    const colors = getChartColors();
    const isDark = AppState.theme === 'dark';
    const isDonut = AppState.prodChartViewMode === 'donut';

    const items = data.items || [];
    const totalKilos = data.total_kilos || 0;

    if (items.length === 0) {
        chart.setOption({
            title: {
                text: 'No se encontraron datos de producción para los filtros seleccionados',
                left: 'center',
                top: 'middle',
                textStyle: { color: colors.text, fontSize: 13, fontWeight: 'normal' }
            },
            series: []
        }, true);
        return;
    }

    // Technology color palette
    const techColorPalette = {
        'AC 0.1%': '#0ea5e9',
        'BPAM': '#10b981',
        'AC 0.3%': '#8b5cf6',
        'AM': '#f59e0b',
        'AC DRISCOLL': '#ec4899',
        'AÉREO': '#06b6d4',
        'A\ufffdREO': '#06b6d4'
    };
    const fallbackColors = ['#0ea5e9', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899', '#06b6d4', '#6366f1', '#14b8a6', '#f97316'];

    const seriesData = items.map((item, idx) => {
        let techName = (item.tecnologia || '').trim();
        if (techName.includes('REO') || techName.toLowerCase().includes('aereo')) {
            techName = 'AÉREO';
        }
        const color = techColorPalette[techName] || fallbackColors[idx % fallbackColors.length];

        return {
            name: techName,
            value: item.kilos,
            porcentaje: item.porcentaje,
            registros: item.registros,
            itemStyle: {
                color: color,
                borderRadius: 6,
                borderColor: isDark ? '#1e293b' : '#ffffff',
                borderWidth: 2
            }
        };
    });

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            confine: true,
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            textStyle: { color: colors.tooltipText },
            extraCssText: 'box-shadow: 0 10px 25px rgba(0,0,0,0.2); border-radius: 8px; z-index: 100;',
            formatter: function(params) {
                const d = params.data;
                const dot = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${params.color};margin-right:6px"></span>`;
                const tn = (d.value / 1000).toFixed(2);
                return `
                    <div style="font-size:0.85rem;min-width:250px;line-height:1.4">
                        <div style="font-weight:700;margin-bottom:4px;color:${colors.title};font-size:0.95rem">
                            ${dot} ${d.name}
                        </div>
                        <hr style="border:none;border-top:1px solid ${colors.splitLine};margin:6px 0">
                        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                            <span>Kilos Producidos:</span>
                            <b>${Number(d.value).toLocaleString('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg</b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                            <span>Toneladas Métricas:</span>
                            <b>${Number(tn).toLocaleString('es-PE', { minimumFractionDigits: 2 })} Tn</b>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                            <span>Participación:</span>
                            <b style="color:${params.color}">${d.porcentaje.toFixed(2)}%</b>
                        </div>
                        <div style="display:flex;justify-content:space-between">
                            <span>Registros en Hoja:</span>
                            <b>${Number(d.registros).toLocaleString('es-PE')}</b>
                        </div>
                    </div>
                `;
            }
        },
        legend: {
            orient: 'horizontal',
            bottom: '2%',
            left: 'center',
            textStyle: {
                color: colors.text,
                fontSize: 11
            },
            formatter: function(name) {
                const found = seriesData.find(s => s.name === name);
                if (!found) return name;
                return `${name} (${found.porcentaje.toFixed(1)}%)`;
            }
        },
        graphic: isDonut ? [
            {
                type: 'text',
                left: 'center',
                top: '43%',
                style: {
                    text: totalKilos >= 1000000 
                        ? `${(totalKilos / 1000).toLocaleString('es-PE', { maximumFractionDigits: 0 })}k kg` 
                        : `${totalKilos.toLocaleString('es-PE', { maximumFractionDigits: 0 })} kg`,
                    fill: colors.title,
                    fontSize: 20,
                    fontWeight: 'bold',
                    textAlign: 'center'
                }
            },
            {
                type: 'text',
                left: 'center',
                top: '52%',
                style: {
                    text: 'Total Kilos',
                    fill: colors.text,
                    fontSize: 11,
                    textAlign: 'center'
                }
            }
        ] : [],
        series: [
            {
                name: 'Distribución de Kilos',
                type: 'pie',
                radius: isDonut ? ['42%', '72%'] : ['0%', '72%'],
                center: ['50%', '47%'],
                avoidLabelOverlap: true,
                padAngle: isDonut ? 3 : 1,
                data: seriesData,
                label: {
                    show: true,
                    position: 'outside',
                    formatter: function(params) {
                        return `{b|${params.name}}\n{d|${params.percent.toFixed(1)}%}`;
                    },
                    rich: {
                        b: {
                            fontSize: 11,
                            fontWeight: '600',
                            color: colors.title
                        },
                        d: {
                            fontSize: 11,
                            fontWeight: 'bold',
                            color: colors.text
                        }
                    }
                },
                labelLine: {
                    show: true,
                    length: 15,
                    length2: 12,
                    smooth: true,
                    lineStyle: {
                        color: colors.splitLine || '#94a3b8'
                    }
                },
                emphasis: {
                    scale: true,
                    scaleSize: 8,
                    itemStyle: {
                        shadowBlur: 15,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.3)'
                    }
                }
            }
        ]
    };

    chart.setOption(option, true);
}

// 5. Samples Paginated Table & Detail Viewer
async function fetchSamplesTable() {
    const params = buildQueryParams(AppState.filters);
    const url = `/api/samples?${params}&page=${AppState.tablePagination.page}&page_size=${AppState.tablePagination.pageSize}`;

    try {
        const res = await fetch(url);
        const json = await res.json();
        if (json.status !== 'success') return;
        const data = json.data;

        AppState.tablePagination.totalPages = data.total_pages;
        AppState.tablePagination.totalRecords = data.total_records;

        elements.tableRecordCount.textContent = `Mostrando ${(data.page - 1) * data.page_size + 1} - ${Math.min(data.page * data.page_size, data.total_records)} de ${data.total_records.toLocaleString()} registros`;
        elements.paginationIndicator.textContent = `Página ${data.page} de ${data.total_pages || 1}`;

        elements.btnPagePrev.disabled = data.page <= 1;
        elements.btnPageNext.disabled = data.page >= data.total_pages;

        renderTableRows(data.items);
    } catch (err) {
        console.error('Error fetching samples table:', err);
    }
}

function renderTableRows(items) {
    if (!items || items.length === 0) {
        elements.samplesTableBody.innerHTML = `
            <tr>
                <td colspan="13" style="text-align:center;padding:2rem;color:var(--text-muted)">
                    <i class="fa-solid fa-magnifying-glass" style="font-size:1.5rem;margin-bottom:0.5rem;display:block"></i>
                    No se encontraron muestreos con los filtros seleccionados.
                </td>
            </tr>
        `;
        return;
    }

    elements.samplesTableBody.innerHTML = items.map((row, idx) => {
        const comp = row.pct_compliance;
        const compClass = comp >= 85 ? 'compliance-high' : (comp >= 60 ? 'compliance-mid' : 'compliance-low');
        const horaStr = row.hora ? row.hora.substring(0, 5) : '--';
        const pMin = row.peso_minimo || 0;
        const pMax = row.peso_maximo || 0;

        return `
            <tr>
                <td><b>${row.fecha}</b></td>
                <td>${horaStr}</td>
                <td><span class="badge-status">T${row.turno}</span></td>
                <td><b>${row.linea}</b></td>
                <td>${row.formato}</td>
                <td>${row.variedad}</td>
                <td><span style="font-family:monospace">${row.viaje || '--'}</span></td>
                <td title="${row.cliente || ''}">${truncate(row.cliente, 20)}</td>
                <td><span style="font-family:monospace;color:var(--text-muted)">[${pMin} - ${pMax}]g</span></td>
                <td><span style="font-family:monospace;font-weight:bold">${row.promedio_pesos ? row.promedio_pesos.toFixed(1) : '--'} g</span></td>
                <td><span style="font-family:monospace">${row.std_dev} g</span></td>
                <td><span class="tag-compliance ${compClass}">${comp}%</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="openSampleModal(${idx})">
                        <i class="fa-solid fa-eye"></i> Ver (${row.total_tested})
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Attach items to window for modal lookup
    window.currentTableItems = items;
}

function truncate(str, max) {
    if (!str) return '--';
    return str.length > max ? str.substring(0, max) + '...' : str;
}

// Modal: 48 Clamshell Viewer
function openSampleModal(index) {
    const row = window.currentTableItems[index];
    if (!row) return;

    elements.modalTitle.textContent = `Muestreo: ${row.fecha} ${row.hora ? row.hora.substring(0,5) : ''} - Línea ${row.linea}`;
    elements.modalSubtitle.textContent = `ID Control: ${row.id_control} | Formato: ${row.formato} | Variedad: ${row.variedad}`;

    // Metadata Grid
    elements.modalMetaGrid.innerHTML = `
        <div class="meta-item">
            <span class="meta-label">Controlador de Línea</span>
            <span class="meta-value">${row.control_linea || 'No registrado'}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Cliente</span>
            <span class="meta-value">${row.cliente || '--'}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Viaje / Lote</span>
            <span class="meta-value" style="font-family:monospace">${row.viaje || '--'}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Tecnología</span>
            <span class="meta-value">${row.tipo_tecnologia || '--'}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Peso Nominal / Tara</span>
            <span class="meta-value">${row.peso_nominal || '--'} g / ${row.tara || '--'} g</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Límites Especificación</span>
            <span class="meta-value" style="color:var(--accent-primary)">[${row.peso_minimo} g - ${row.peso_maximo} g]</span>
        </div>
    `;

    // Stats Bar
    elements.modalSampleStats.innerHTML = `
        <div style="text-align:center">
            <div style="font-size:0.75rem;color:var(--text-muted)">PROMEDIO</div>
            <div style="font-size:1.3rem;font-weight:bold;font-family:monospace">${row.promedio_pesos ? row.promedio_pesos.toFixed(2) : '--'} g</div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.75rem;color:var(--text-muted)">DESVIACIÓN (σ)</div>
            <div style="font-size:1.3rem;font-weight:bold;font-family:monospace">${row.std_dev} g</div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.75rem;color:var(--color-green)">EN NORMA</div>
            <div style="font-size:1.3rem;font-weight:bold;color:var(--color-green)">${row.count_in} <small style="font-size:0.75rem">(${row.pct_compliance}%)</small></div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.75rem;color:var(--color-red)">BAJO PESO</div>
            <div style="font-size:1.3rem;font-weight:bold;color:var(--color-red)">${row.count_under}</div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.75rem;color:var(--color-amber)">SOBREPESO</div>
            <div style="font-size:1.3rem;font-weight:bold;color:var(--color-amber)">${row.count_over}</div>
        </div>
    `;

    // Clamshells Grid
    const pMin = row.peso_minimo || 0;
    const pMax = row.peso_maximo || 0;

    elements.modalClamshellsGrid.innerHTML = row.weights.map((w, i) => {
        let cardClass = 'card-in-spec';
        let weightClass = 'weight-in';
        let tagText = 'Norma';

        if (pMin > 0 && w < pMin) {
            cardClass = 'card-underweight';
            weightClass = 'weight-under';
            tagText = 'Bajo';
        } else if (w > pMax) {
            cardClass = 'card-overweight';
            weightClass = 'weight-over';
            tagText = 'Sobre';
        }

        return `
            <div class="clamshell-card ${cardClass}">
                <span class="clamshell-num">T${i + 1}</span>
                <span class="clamshell-weight ${weightClass}">${w}g</span>
                <span class="clamshell-tag ${weightClass}">${tagText}</span>
            </div>
        `;
    }).join('');

    elements.sampleModal.classList.add('active');
}

function closeModal() {
    elements.sampleModal.classList.remove('active');
}

function openGuideModal() {
    elements.guideModal?.classList.add('active');
}

function closeGuideModal() {
    elements.guideModal?.classList.remove('active');
}

// ==========================================================================
// AI Chat Assistant Controller
// ==========================================================================
const chatHistory = [];
let isChatOpen = false;
let isWaitingChatResponse = false;

function initChatWidget() {
    if (!elements.btnChatFab || !elements.chatDrawer) return;

    // Toggle drawer on FAB click
    elements.btnChatFab.addEventListener('click', toggleChatWidget);

    // Minimize / Close button
    elements.btnChatMinimize?.addEventListener('click', () => setChatOpen(false));

    // Clear chat button
    elements.btnChatClear?.addEventListener('click', clearChatHistory);

    // Chat form submit
    elements.chatForm?.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = elements.chatInput?.value.trim();
        if (text) {
            sendChatMessage(text);
        }
    });

    // Suggestion pills click delegation
    elements.chatSuggestions?.addEventListener('click', (e) => {
        const pill = e.target.closest('.suggestion-pill');
        if (pill && pill.dataset.query) {
            sendChatMessage(pill.dataset.query);
        }
    });
}

function toggleChatWidget() {
    setChatOpen(!isChatOpen);
}

function setChatOpen(open) {
    isChatOpen = open;
    if (!elements.chatDrawer) return;

    elements.chatDrawer.style.display = open ? 'flex' : 'none';
    if (elements.chatIconOpen && elements.chatIconClose) {
        elements.chatIconOpen.style.display = open ? 'none' : 'block';
        elements.chatIconClose.style.display = open ? 'block' : 'none';
    }

    if (open) {
        setTimeout(() => elements.chatInput?.focus(), 150);
        scrollChatToBottom();
    }
}

function clearChatHistory() {
    chatHistory.length = 0;
    if (!elements.chatMessagesContainer) return;

    elements.chatMessagesContainer.innerHTML = `
        <div class="chat-msg-row assistant">
            <div class="chat-bubble-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="chat-bubble">
                <div class="chat-bubble-text">
                    <p>¡Hola! Soy tu asistente analítico de <b>Camposol</b>. Conversación reiniciada. ¿En qué te puedo colaborar?</p>
                </div>
            </div>
        </div>
        <div class="chat-suggestions" id="chat-suggestions">
            <span class="suggestions-label"><i class="fa-regular fa-lightbulb"></i> Consultas rápidas:</span>
            <div class="suggestions-pills">
                <button type="button" class="suggestion-pill" data-query="¿Cuál es la línea con mayor cumplimiento y menor sobrepeso?">
                    🏆 ¿Mejor línea de empaque?
                </button>
                <button type="button" class="suggestion-pill" data-query="¿Qué formato tiene mayor sobrepeso y pérdida de giveaway?">
                    📦 Sobrepeso por formato
                </button>
                <button type="button" class="suggestion-pill" data-query="¿Cómo se compara el desempeño entre el Turno 1 (Día) y Turno 2 (Noche)?">
                    ⏱️ Comparar turnos 1 y 2
                </button>
                <button type="button" class="suggestion-pill" data-query="¿Cuál es el Cpk del formato 4.4 onz y cómo está centrado el proceso?">
                    📈 Capacidad Cpk de 4.4 onz
                </button>
            </div>
        </div>
    `;
}

function formatMarkdownToHtml(text) {
    if (!text) return '';
    let html = text
        // Headers ###
        .replace(/^### (.*$)/gim, '<h5 style="margin:0.4rem 0 0.2rem;font-size:0.92rem;font-weight:700;color:var(--text-primary)">$1</h5>')
        // Bold **text**
        .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
        // Inline code `code`
        .replace(/`(.*?)`/g, '<code style="background:var(--bg-input);padding:0.1rem 0.35rem;border-radius:4px;font-size:0.8rem;font-family:var(--font-mono)">$1</code>')
        // Bullet points - or *
        .replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');

    // Wrap li inside ul
    html = html.replace(/(<li>.*<\/li>)/gms, '<ul style="margin:0.3rem 0 0.5rem 1.1rem;padding:0">$1</ul>');

    // Convert markdown tables
    if (html.includes('|')) {
        const lines = html.split('\n');
        let inTable = false;
        let tableRows = [];
        let newLines = [];

        for (let line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
                if (trimmed.includes('---')) continue; // Skip separator line
                inTable = true;
                const cells = trimmed.split('|').slice(1, -1).map(c => c.trim());
                tableRows.push(cells);
            } else {
                if (inTable) {
                    newLines.push(renderTableHtml(tableRows));
                    tableRows = [];
                    inTable = false;
                }
                newLines.push(line);
            }
        }
        if (inTable) {
            newLines.push(renderTableHtml(tableRows));
        }
        html = newLines.join('\n');
    }

    // Paragraphs
    html = html.split('\n\n').map(p => {
        p = p.trim();
        if (!p) return '';
        if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<table') || p.startsWith('<hr')) {
            return p;
        }
        return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    return html;
}

function renderTableHtml(rows) {
    if (!rows || rows.length === 0) return '';
    let html = '<table>';
    // Header
    html += '<thead><tr>' + rows[0].map(c => `<th>${c}</th>`).join('') + '</tr></thead>';
    // Body
    if (rows.length > 1) {
        html += '<tbody>';
        for (let i = 1; i < rows.length; i++) {
            html += '<tr>' + rows[i].map(c => `<td>${c}</td>`).join('') + '</tr>';
        }
        html += '</tbody>';
    }
    html += '</table>';
    return html;
}

async function sendChatMessage(message) {
    if (!message || isWaitingChatResponse) return;
    if (elements.chatInput) elements.chatInput.value = '';

    // Hide initial suggestion chips on first question
    const suggestions = document.getElementById('chat-suggestions');
    if (suggestions) suggestions.style.display = 'none';

    // Append User Message
    appendMessageRow('user', escapeHtml(message));
    chatHistory.push({ role: 'user', content: message });
    scrollChatToBottom();

    // Append Loading Indicator
    isWaitingChatResponse = true;
    if (elements.btnChatSend) elements.btnChatSend.disabled = true;
    const loadingId = 'chat-loading-' + Date.now();
    appendLoadingBubble(loadingId);
    scrollChatToBottom();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: chatHistory
            })
        });
        const json = await res.json();
        removeLoadingBubble(loadingId);

        if (json.status === 'success') {
            const formattedReply = formatMarkdownToHtml(json.reply);
            appendMessageRow('assistant', formattedReply, false);
            chatHistory.push({ role: 'assistant', content: json.reply });
        } else {
            appendMessageRow('assistant', `<p style="color:var(--color-red)">⚠️ ${json.message || 'Error al procesar la consulta'}</p>`, false);
        }
    } catch (err) {
        removeLoadingBubble(loadingId);
        appendMessageRow('assistant', '<p style="color:var(--color-red)">⚠️ No se pudo conectar con el servidor. Inténtalo nuevamente.</p>', false);
    } finally {
        isWaitingChatResponse = false;
        if (elements.btnChatSend) elements.btnChatSend.disabled = false;
        elements.chatInput?.focus();
        scrollChatToBottom();
    }
}

function appendMessageRow(role, contentHtml, isEscaped = true) {
    if (!elements.chatMessagesContainer) return;
    const row = document.createElement('div');
    row.className = `chat-msg-row ${role}`;

    if (role === 'assistant') {
        row.innerHTML = `
            <div class="chat-bubble-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="chat-bubble">
                <div class="chat-bubble-text">${contentHtml}</div>
            </div>
        `;
    } else {
        row.innerHTML = `
            <div class="chat-bubble">
                <div class="chat-bubble-text">${isEscaped ? contentHtml : contentHtml}</div>
            </div>
        `;
    }
    elements.chatMessagesContainer.appendChild(row);
}

function appendLoadingBubble(id) {
    if (!elements.chatMessagesContainer) return;
    const row = document.createElement('div');
    row.id = id;
    row.className = 'chat-msg-row assistant';
    row.innerHTML = `
        <div class="chat-bubble-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-bubble typing-bubble">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span style="font-size:0.75rem;color:var(--text-muted);margin-left:4px">Consultando datos...</span>
        </div>
    `;
    elements.chatMessagesContainer.appendChild(row);
}

function removeLoadingBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollChatToBottom() {
    if (elements.chatMessagesContainer) {
        elements.chatMessagesContainer.scrollTop = elements.chatMessagesContainer.scrollHeight;
    }
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
