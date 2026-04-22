let scanData = [];
let currentFilter = 'all';
let searchQuery = '';
let currentView = 'grid';

document.addEventListener('DOMContentLoaded', () => {
    initControls();
    initModal();
});

function initControls() {
    const searchInput = document.getElementById('ticker-search');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const cardViewBtn = document.getElementById('card-view-btn');
    const listViewBtn = document.getElementById('list-view-btn');
    const runScanBtn = document.getElementById('run-scan-btn');
    const tickerInput = document.getElementById('ticker-input');

    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase();
        renderDashboard();
    });

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.id === 'run-scan-btn') return;
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderDashboard();
        });
    });

    cardViewBtn.addEventListener('click', () => {
        cardViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
        currentView = 'grid';
        document.getElementById('ticker-grid').classList.remove('list-view');
        renderDashboard();
    });

    listViewBtn.addEventListener('click', () => {
        listViewBtn.classList.add('active');
        cardViewBtn.classList.remove('active');
        currentView = 'list';
        document.getElementById('ticker-grid').classList.add('list-view');
        renderDashboard();
    });

    runScanBtn.addEventListener('click', async () => {
        const input = tickerInput.value.trim();
        if (!input) return alert("Please enter at least one ticker.");
        
        showLoading(true);
        try {
            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers: input })
            });
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            scanData = data;
            renderDashboard();
            document.getElementById('last-updated').innerText = `Scan Complete: ${new Date().toLocaleTimeString()}`;
        } catch (err) {
            alert("Analysis failed: " + err.message);
        } finally {
            showLoading(false);
        }
    });
}

function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

function initModal() {
    const modal = document.getElementById('detail-modal');
    const closeBtn = document.querySelector('.close-btn');
    closeBtn.onclick = () => modal.style.display = "none";
    window.onclick = (e) => { if (e.target == modal) modal.style.display = "none"; }
}

function renderDashboard() {
    const grid = document.getElementById('ticker-grid');
    const totalScanned = document.getElementById('total-scanned');
    const activeSignals = document.getElementById('active-signals');

    let filteredData = scanData.filter(stock => {
        const matchesSearch = (stock.ticker || '').toLowerCase().includes(searchQuery);
        const matchesFilter = currentFilter === 'all' || (currentFilter === 'active' && stock.in_2_sessions);
        return matchesSearch && matchesFilter;
    });

    filteredData.sort((a, b) => (b.in_2_sessions - a.in_2_sessions));

    totalScanned.innerText = scanData.length;
    activeSignals.innerText = scanData.filter(s => s.in_2_sessions).length;

    grid.innerHTML = '';

    if (filteredData.length === 0 && scanData.length > 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-secondary);">No matches.</div>`;
        return;
    }

    if (scanData.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 5rem; color: var(--text-secondary);">Enter tickers above to start.</div>`;
        return;
    }

    if (currentView === 'list') {
        const header = document.createElement('div');
        header.className = 'list-header';
        header.innerHTML = `<div>Ticker</div><div>Strategy</div><div>Entry</div><div>Targets</div><div>SL</div><div style="text-align: right">Signal</div>`;
        grid.appendChild(header);
    }

    filteredData.forEach((stock, index) => grid.appendChild(createStockCard(stock, index)));
}

function createStockCard(stock, index) {
    const card = document.createElement('div');
    card.className = 'stock-card';
    card.onclick = () => showModal(stock);
    const isActive = stock.in_2_sessions;
    
    card.innerHTML = `
        <div class="card-header">
            <div class="ticker-info">
                <h2>${stock.ticker}</h2>
                <div class="cmp-label">₹${stock.cmp}</div>
            </div>
            <div class="strategy-badge ${isActive ? 'badge-active' : 'badge-neutral'}">${stock.strategy}</div>
        </div>
        <div class="card-body">
            <div class="data-row"><span class="data-label">Entry</span><span class="data-value">${stock.entry_range || 'Wait'}</span></div>
            <div class="data-row"><span class="data-label">Targets</span><div class="target-list">${stock.targets.length ? stock.targets.map(t => `<span class="target-pill">₹${t}</span>`).join('') : 'N/A'}</div></div>
            <div class="data-row"><span class="data-label">SL</span><span class="data-value" style="color: var(--accent-red)">${stock.sl ? '₹'+stock.sl : 'N/A'}</span></div>
        </div>
        <div class="card-footer">
            <div class="window-indicator ${isActive ? 'active' : 'wait'}"><span>${isActive ? 'ACTION' : 'WAIT'}</span></div>
        </div>
    `;
    return card;
}

function showModal(stock) {
    const modal = document.getElementById('detail-modal');
    const body = document.getElementById('modal-body');
    body.innerHTML = `
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">${stock.ticker} <span style="color: var(--accent-blue)">₹${stock.cmp}</span></h1>
        <p style="color: var(--text-secondary); margin-bottom: 2rem;">Strategy: ${stock.strategy}</p>
        <div class="modal-grid">
            <div class="stat-card"><div class="stat-label">Trade Params</div><div class="data-row">Entry: ${stock.entry_range || 'Wait'}</div><div class="data-row">SL: ₹${stock.sl || 'N/A'}</div></div>
            <div class="stat-card"><div class="stat-label">Technicals</div><div class="data-row">RSI: ${stock.rsi}</div><div class="data-row">OB: ${stock.smc.recent_ob}</div></div>
        </div>
        <div style="margin-top: 2rem;"><div class="stat-label">Targets</div><div style="display: flex; gap: 1rem; margin-top: 1rem;">${stock.targets.map(t => `<div class="stat-card" style="flex:1;text-align:center;">₹${t}</div>`).join('')}</div></div>
    `;
    modal.style.display = "block";
}
