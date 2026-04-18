// Wetsu Finance App - Frontend JavaScript

const API_BASE = '';
let currentPage = 0;
const pageSize = 25;
let categories = {};
let wallets = [];
let expensesChart = null;
let trendChart = null;

// ── Tab navigation ──────────────────────────────────────────
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');

    if (tabName === 'dashboard')         loadDashboard();
    else if (tabName === 'transactions') { currentPage = 0; loadTransactions(); }
    else if (tabName === 'carteras')     loadCarteras();
    else if (tabName === 'deudas')       loadDeudas();
}

// ── Formatters ──────────────────────────────────────────────
function formatCurrency(amount) {
    return '$' + parseInt(amount).toLocaleString('en-US');
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

// ── Dashboard ───────────────────────────────────────────────
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard`);
        const data = await response.json();

        const income     = data.summary.income     || { count: 0, total: 0 };
        const expense    = data.summary.expense    || { count: 0, total: 0 };
        const investment = data.summary.investment || { count: 0, total: 0 };

        document.getElementById('total-income').textContent     = formatCurrency(income.total);
        document.getElementById('income-count').textContent     = `${income.count} transactions`;
        document.getElementById('total-expense').textContent    = formatCurrency(expense.total);
        document.getElementById('expense-count').textContent    = `${expense.count} transactions`;
        document.getElementById('total-investment').textContent = formatCurrency(investment.total);
        document.getElementById('investment-count').textContent = `${investment.count} transactions`;

        const net = income.total - expense.total - investment.total;
        document.getElementById('net-balance').textContent = formatCurrency(net);

        // Recent transactions
        const recentBody = document.querySelector('#recent-table tbody');
        recentBody.innerHTML = data.recent_transactions.map(t => `
            <tr>
                <td>${formatDate(t.date)}</td>
                <td>${t.category_main}</td>
                <td>${t.note || '—'}</td>
                <td class="${t.type === 'income' ? 'positive' : 'negative'}">${formatCurrency(t.amount)}</td>
                <td><span class="badge ${t.type}">${t.type}</span></td>
            </tr>
        `).join('');

        renderWalletStrip(data.wallets || []);
        renderDebtSummaryBar(data.debt_summary || {});
        updateCharts(data);
    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

function renderWalletStrip(ws) {
    const strip = document.getElementById('wallet-strip');
    if (!ws.length) { strip.innerHTML = ''; return; }
    strip.innerHTML = ws.map(w => `
        <div class="card wallet">
            <div class="wallet-type">${w.type}</div>
            <h3>${w.name}</h3>
            <div class="amount">${formatCurrency(w.current_balance)}</div>
        </div>
    `).join('');
}

function renderDebtSummaryBar(ds) {
    const bar = document.getElementById('debt-summary-bar');
    if (!ds.active_count) { bar.innerHTML = ''; return; }
    bar.innerHTML = `
        <div class="debt-summary-item owed-by-me">
            <span class="debt-label">Debo</span>
            <span class="debt-amount">${formatCurrency(ds.total_owed_by_me)}</span>
        </div>
        <div class="debt-summary-item owed-to-me">
            <span class="debt-label">Me deben</span>
            <span class="debt-amount">${formatCurrency(ds.total_owed_to_me)}</span>
        </div>
        <div class="debt-summary-item">
            <span class="debt-label">Deudas activas</span>
            <span class="debt-amount">${ds.active_count}</span>
        </div>
    `;
}

// ── Charts ──────────────────────────────────────────────────
function updateCharts(data) {
    const expenseCtx = document.getElementById('expensesChart').getContext('2d');
    if (expensesChart) expensesChart.destroy();

    const expenseCanvas = document.getElementById('expensesChart');
    const expenseEmptyEl = document.getElementById('expensesChart-empty') || (() => {
        const el = document.createElement('p');
        el.id = 'expensesChart-empty';
        el.style.cssText = 'color:var(--text-dim);font-size:0.8rem;text-align:center;padding:60px 0;display:none';
        el.textContent = 'No expense data yet';
        expenseCanvas.after(el);
        return el;
    })();

    const expenseContainer = expenseCanvas.parentElement;
    if (!data.expenses_by_category || data.expenses_by_category.length === 0) {
        expenseCanvas.style.display = 'none';
        expenseEmptyEl.style.display = 'block';
        expenseContainer.classList.add('empty');
    } else {
        expenseCanvas.style.display = '';
        expenseEmptyEl.style.display = 'none';
        expenseContainer.classList.remove('empty');
        expensesChart = new Chart(expenseCtx, {
            type: 'doughnut',
            data: {
                labels: data.expenses_by_category.map(c => c.category_main),
                datasets: [{
                    data: data.expenses_by_category.map(c => c.total),
                    backgroundColor: ['#f87171','#60a5fa','#d4a853','#4ade80','#a78bfa','#34d399','#6b7280','#fb923c'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#6b6b7a', font: { family: 'Outfit', size: 12 }, boxWidth: 12 }
                    }
                }
            }
        });
    }

    const trendCtx = document.getElementById('trendChart').getContext('2d');
    if (trendChart) trendChart.destroy();
    const monthly = [...data.monthly_trend].reverse();

    trendChart = new Chart(trendCtx, {
        type: 'bar',
        data: {
            labels: monthly.map(m => m.month),
            datasets: [
                { label: 'Income',  data: monthly.map(m => m.income  || 0), backgroundColor: '#4ade80' },
                { label: 'Expense', data: monthly.map(m => m.expense || 0), backgroundColor: '#f87171' }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: '#6b6b7a' }, grid: { color: '#1e1e28' } },
                y: { beginAtZero: true, ticks: { color: '#6b6b7a' }, grid: { color: '#1e1e28' } }
            },
            plugins: {
                legend: { labels: { color: '#6b6b7a', font: { family: 'Outfit', size: 12 }, boxWidth: 12 } }
            }
        }
    });
}

// ── Transactions ────────────────────────────────────────────
async function loadTransactions() {
    try {
        const typeFilter     = document.getElementById('filter-type').value;
        const categoryFilter = document.getElementById('filter-category').value;
        const startDate      = document.getElementById('filter-start').value;
        const endDate        = document.getElementById('filter-end').value;

        let url = `${API_BASE}/api/transactions?limit=${pageSize}&offset=${currentPage * pageSize}`;
        if (typeFilter)     url += `&type=${typeFilter}`;
        if (categoryFilter) url += `&category=${categoryFilter}`;
        if (startDate)      url += `&start_date=${startDate}`;
        if (endDate)        url += `&end_date=${endDate}`;

        const response = await fetch(url);
        const data = await response.json();

        const tbody = document.querySelector('#transactions-table tbody');
        const walletMap = Object.fromEntries(wallets.map(w => [w.id, w.name]));
        tbody.innerHTML = data.transactions.map(t => `
            <tr>
                <td class="col-id">${t.id}</td>
                <td>${formatDate(t.date)}</td>
                <td><span class="badge ${t.type}">${t.type}</span></td>
                <td>${t.category_main}</td>
                <td class="col-subcat">${t.category_sub}</td>
                <td>${t.note || '—'}</td>
                <td class="col-wallet">${t.wallet_id ? (walletMap[t.wallet_id] || '—') : '—'}</td>
                <td class="${t.type === 'income' ? 'positive' : 'negative'}">${formatCurrency(t.amount)}</td>
                <td>
                    <button class="action-btn edit" onclick="editTransaction(${t.id})">Edit</button>
                    <button class="action-btn delete" onclick="deleteTransaction(${t.id})">Delete</button>
                </td>
            </tr>
        `).join('');

        const totalPages = Math.ceil(data.total / pageSize);
        document.getElementById('page-info').textContent = `Page ${currentPage + 1} of ${totalPages || 1}`;
    } catch (err) {
        console.error('Error loading transactions:', err);
    }
}

function prevPage() { if (currentPage > 0) { currentPage--; loadTransactions(); } }
function nextPage() { currentPage++; loadTransactions(); }

// ── Categories ──────────────────────────────────────────────
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/api/categories`);
        categories = await response.json();

        const mainCatSelect   = document.getElementById('trans-main-cat');
        const filterCatSelect = document.getElementById('filter-category');

        Object.keys(categories).forEach(cat => {
            [mainCatSelect, filterCatSelect].forEach(sel => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                sel.appendChild(opt);
            });
        });
    } catch (err) {
        console.error('Error loading categories:', err);
    }
}

document.getElementById('trans-main-cat')?.addEventListener('change', function () {
    const subCatSelect = document.getElementById('trans-sub-cat');
    subCatSelect.innerHTML = '<option value="">Select...</option>';
    if (this.value && categories[this.value]) {
        categories[this.value].forEach(sub => {
            const opt = document.createElement('option');
            opt.value = sub.sub;
            opt.textContent = sub.sub;
            subCatSelect.appendChild(opt);
        });
    }
});

// ── Wallets ─────────────────────────────────────────────────
async function loadWallets() {
    try {
        const response = await fetch(`${API_BASE}/api/wallets`);
        wallets = await response.json();
        populateWalletSelects();
    } catch (err) {
        console.error('Error loading wallets:', err);
    }
}

function populateWalletSelects() {
    ['trans-wallet', 'edit-wallet', 'payment-wallet'].forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const current = sel.value;
        sel.innerHTML = '<option value="">Sin cartera</option>';
        wallets.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w.id;
            opt.textContent = `${w.name} (${w.type})`;
            sel.appendChild(opt);
        });
        sel.value = current;
    });
}

async function loadCarteras() {
    await loadWallets();
    loadTransferHistory();
    const grid = document.getElementById('wallets-grid');
    if (!wallets.length) {
        grid.innerHTML = '<p class="empty-state">No hay carteras aún. Crea una con el botón de arriba.</p>';
        return;
    }
    grid.innerHTML = wallets.map(w => `
        <div class="wallet-card">
            <div class="wallet-card-header">
                <span class="wallet-type-badge">${w.type}</span>
                <div class="wallet-card-actions">
                    <button class="action-btn edit" onclick="openWalletModal(${w.id})">Editar</button>
                    <button class="action-btn delete" onclick="deactivateWallet(${w.id})">Desactivar</button>
                </div>
            </div>
            <div class="wallet-card-name">${w.name}</div>
            <div class="wallet-card-balance">${formatCurrency(w.current_balance)}</div>
            <div class="wallet-card-footer">
                <span class="wallet-card-currency">${w.currency}</span>
                <button class="btn-adjust" onclick="openAdjustModal(${w.id}, ${w.current_balance}, '${w.name}')">Ajustar saldo</button>
            </div>
        </div>
    `).join('');
}

function openWalletModal(editId = null) {
    document.getElementById('wallet-edit-id').value = editId || '';
    document.getElementById('wallet-modal-title').textContent = editId ? 'Editar Cartera' : 'Nueva Cartera';
    document.getElementById('wallet-balance-row').style.display = editId ? 'none' : '';
    document.getElementById('wallet-form').reset();
    if (editId) {
        const w = wallets.find(x => x.id === editId);
        if (w) {
            document.getElementById('wallet-name').value = w.name;
            document.getElementById('wallet-type').value = w.type;
        }
    }
    document.getElementById('new-wallet-modal').style.display = 'block';
}

document.getElementById('wallet-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const editId = document.getElementById('wallet-edit-id').value;
    const body = {
        name: document.getElementById('wallet-name').value,
        type: document.getElementById('wallet-type').value
    };
    if (!editId) body.initial_balance = parseInt(document.getElementById('wallet-initial-balance').value) || 0;

    const url    = editId ? `${API_BASE}/api/wallets/${editId}` : `${API_BASE}/api/wallets`;
    const method = editId ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        if (res.ok) {
            closeModal('new-wallet-modal');
            loadCarteras();
            loadWallets();
        } else {
            alert('Error guardando cartera');
        }
    } catch (err) {
        console.error(err);
    }
});

function openAdjustModal(walletId, currentBalance, walletName) {
    document.getElementById('adjust-wallet-id').value = walletId;
    document.getElementById('adjust-current-balance').textContent = formatCurrency(currentBalance);
    document.getElementById('adjust-target').value = '';
    document.getElementById('adjust-note').value = '';
    document.getElementById('adjust-diff-preview').innerHTML = '';
    document.getElementById('adjust-date').valueAsDate = new Date();
    document.getElementById('adjust-wallet-modal').style.display = 'block';

    // Live diff preview
    const targetInput = document.getElementById('adjust-target');
    targetInput.oninput = function () {
        const target = parseInt(this.value) || 0;
        const diff = target - currentBalance;
        const preview = document.getElementById('adjust-diff-preview');
        if (!this.value) { preview.innerHTML = ''; return; }
        const sign = diff > 0 ? '+' : '';
        const cls  = diff > 0 ? 'positive' : diff < 0 ? 'negative' : '';
        preview.innerHTML = diff === 0
            ? `<span class="adjust-diff-zero">Sin cambios</span>`
            : `<span class="${cls}">Se creará una transacción de ajuste de ${sign}${formatCurrency(Math.abs(diff))}</span>`;
    };
}

document.getElementById('adjust-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const walletId = document.getElementById('adjust-wallet-id').value;
    const body = {
        target_balance: parseInt(document.getElementById('adjust-target').value),
        date:           document.getElementById('adjust-date').value,
        note:           document.getElementById('adjust-note').value
    };
    try {
        const res = await fetch(`${API_BASE}/api/wallets/${walletId}/adjust`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        const data = await res.json();
        if (res.ok) {
            closeModal('adjust-wallet-modal');
            loadCarteras();
            loadDashboard();
        } else {
            alert(data.detail || 'Error al ajustar saldo');
        }
    } catch (err) {
        console.error(err);
    }
});

// ── Transfers ────────────────────────────────────────────────
function openTransferModal() {
    document.getElementById('transfer-form').reset();
    document.getElementById('transfer-preview').innerHTML = '';
    document.getElementById('transfer-date').valueAsDate = new Date();

    // Populate both selects
    ['transfer-from', 'transfer-to'].forEach(id => {
        const sel = document.getElementById(id);
        sel.innerHTML = '<option value="">Seleccionar cartera...</option>';
        wallets.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w.id;
            opt.textContent = `${w.name} — ${formatCurrency(w.current_balance)}`;
            sel.appendChild(opt);
        });
    });

    // Live preview
    const updatePreview = () => {
        const fromId = parseInt(document.getElementById('transfer-from').value);
        const toId   = parseInt(document.getElementById('transfer-to').value);
        const amount = parseInt(document.getElementById('transfer-amount').value) || 0;
        const preview = document.getElementById('transfer-preview');

        if (!fromId || !toId || !amount) { preview.innerHTML = ''; return; }
        if (fromId === toId) {
            preview.innerHTML = '<span class="negative">Las carteras deben ser diferentes</span>';
            return;
        }
        const from = wallets.find(w => w.id === fromId);
        const to   = wallets.find(w => w.id === toId);
        preview.innerHTML = `
            <div class="transfer-flow">
                <div class="transfer-flow-item">
                    <span class="transfer-flow-label">${from.name}</span>
                    <span class="negative">−${formatCurrency(amount)}</span>
                    <span class="transfer-flow-result">${formatCurrency(from.current_balance - amount)}</span>
                </div>
                <div class="transfer-flow-arrow">→</div>
                <div class="transfer-flow-item">
                    <span class="transfer-flow-label">${to.name}</span>
                    <span class="positive">+${formatCurrency(amount)}</span>
                    <span class="transfer-flow-result">${formatCurrency(to.current_balance + amount)}</span>
                </div>
            </div>
        `;
    };

    document.getElementById('transfer-from').onchange   = updatePreview;
    document.getElementById('transfer-to').onchange     = updatePreview;
    document.getElementById('transfer-amount').oninput  = updatePreview;

    document.getElementById('transfer-modal').style.display = 'block';
}

document.getElementById('transfer-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const fromId = parseInt(document.getElementById('transfer-from').value);
    const toId   = parseInt(document.getElementById('transfer-to').value);
    if (fromId === toId) { alert('Las carteras deben ser diferentes'); return; }

    const body = {
        from_wallet_id: fromId,
        to_wallet_id:   toId,
        amount:  parseInt(document.getElementById('transfer-amount').value),
        date:    document.getElementById('transfer-date').value,
        note:    document.getElementById('transfer-note').value
    };
    try {
        const res = await fetch(`${API_BASE}/api/transfers`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        const data = await res.json();
        if (res.ok) {
            closeModal('transfer-modal');
            loadCarteras();
            loadDashboard();
        } else {
            alert(data.detail || 'Error al registrar transferencia');
        }
    } catch (err) { console.error(err); }
});

async function loadTransferHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/transfers`);
        const transfers = await res.json();
        const container = document.getElementById('transfers-history');
        if (!transfers.length) { container.innerHTML = ''; return; }

        container.innerHTML = `
            <h3 class="debts-subtitle" style="margin-top:40px">Historial de Transferencias</h3>
            <div class="table-scroll">
                <table>
                    <thead><tr>
                        <th>Fecha</th><th>Desde</th><th>Hacia</th>
                        <th>Monto</th><th>Nota</th><th>Acciones</th>
                    </tr></thead>
                    <tbody>
                        ${transfers.map(t => `
                            <tr>
                                <td>${formatDate(t.date)}</td>
                                <td>${t.from_wallet_name}</td>
                                <td>${t.to_wallet_name}</td>
                                <td class="positive">${formatCurrency(t.amount)}</td>
                                <td>${t.note || '—'}</td>
                                <td><button class="action-btn delete" onclick="deleteTransfer(${t.id})">Eliminar</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) { console.error(err); }
}

async function deleteTransfer(id) {
    if (!confirm('¿Eliminar esta transferencia? Se eliminarán las dos transacciones vinculadas.')) return;
    try {
        const res = await fetch(`${API_BASE}/api/transfers/${id}`, { method: 'DELETE' });
        if (res.ok) { loadCarteras(); loadDashboard(); }
        else alert('Error al eliminar transferencia');
    } catch (err) { console.error(err); }
}

async function deactivateWallet(id) {
    if (!confirm('¿Desactivar esta cartera?')) return;
    try {
        await fetch(`${API_BASE}/api/wallets/${id}`, { method: 'DELETE' });
        loadCarteras();
        loadWallets();
    } catch (err) {
        console.error(err);
    }
}

// ── Debts ───────────────────────────────────────────────────
async function loadDeudas() {
    try {
        const res   = await fetch(`${API_BASE}/api/debts`);
        const debts = await res.json();
        renderDebtTable('debts-owed-by-me-table', debts.filter(d => d.direction === 'owed_by_me'), 'Sin deudas activas');
        renderDebtTable('debts-owed-to-me-table', debts.filter(d => d.direction === 'owed_to_me'), 'Sin préstamos activos');
    } catch (err) {
        console.error('Error loading debts:', err);
    }
}

function renderDebtTable(tableId, debts, emptyMsg) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!debts.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-row">${emptyMsg}</td></tr>`;
        return;
    }
    tbody.innerHTML = debts.map(d => {
        const paid   = d.status === 'paid';
        const cuotas = d.installments > 1
            ? `${d.installments} × ${formatCurrency(d.installment_amount)}`
            : '—';
        return `
            <tr class="${paid ? 'debt-row-paid' : ''}">
                <td>${d.counterpart_name}</td>
                <td>${formatCurrency(d.total_amount)}</td>
                <td>${formatCurrency(d.remaining_amount)}</td>
                <td>${cuotas}</td>
                <td>${d.due_date ? formatDate(d.due_date) : '—'}</td>
                <td><span class="badge ${paid ? 'paid' : 'active-debt'}">${paid ? 'Pagada' : 'Activa'}</span></td>
                <td>${!paid ? `<button class="action-btn edit" onclick="openPaymentModal(${d.id}, ${d.remaining_amount})">Pagar</button>` : ''}</td>
            </tr>
        `;
    }).join('');
}

function openDebtModal() {
    document.getElementById('debt-form').reset();
    document.getElementById('new-debt-modal').style.display = 'block';
}

document.getElementById('debt-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const body = {
        direction:        document.getElementById('debt-direction').value,
        counterpart_name: document.getElementById('debt-counterpart').value,
        total_amount:     parseInt(document.getElementById('debt-amount').value),
        installments:     parseInt(document.getElementById('debt-installments').value) || 1,
        due_date:         document.getElementById('debt-due-date').value || null,
        notes:            document.getElementById('debt-notes').value
    };
    try {
        const res = await fetch(`${API_BASE}/api/debts`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        if (res.ok) {
            closeModal('new-debt-modal');
            loadDeudas();
        } else {
            alert('Error creando deuda');
        }
    } catch (err) {
        console.error(err);
    }
});

function openPaymentModal(debtId, remaining) {
    document.getElementById('payment-form').reset();
    document.getElementById('payment-debt-id').value = debtId;
    document.getElementById('payment-amount').max = remaining;
    document.getElementById('payment-amount').placeholder = `Máx: ${formatCurrency(remaining)}`;
    document.getElementById('payment-date').valueAsDate = new Date();
    populateWalletSelects();
    document.getElementById('debt-payment-modal').style.display = 'block';
}

document.getElementById('payment-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const debtId    = document.getElementById('payment-debt-id').value;
    const walletVal = document.getElementById('payment-wallet').value;
    const body = {
        amount:             parseInt(document.getElementById('payment-amount').value),
        payment_date:       document.getElementById('payment-date').value,
        wallet_id:          walletVal ? parseInt(walletVal) : null,
        installment_number: parseInt(document.getElementById('payment-installment').value) || null,
        notes:              document.getElementById('payment-notes').value
    };
    try {
        const res = await fetch(`${API_BASE}/api/debts/${debtId}/payments`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        if (res.ok) {
            closeModal('debt-payment-modal');
            loadDeudas();
            loadDashboard();
        } else {
            const err = await res.json();
            alert(err.detail || 'Error registrando pago');
        }
    } catch (err) {
        console.error(err);
    }
});

// ── Add Transaction ──────────────────────────────────────────
document.getElementById('transaction-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const walletVal = document.getElementById('trans-wallet').value;
    const transaction = {
        date:          document.getElementById('trans-date').value,
        amount:        parseInt(document.getElementById('trans-amount').value),
        currency:      'CLP',
        type:          document.getElementById('trans-type').value,
        category_main: document.getElementById('trans-main-cat').value,
        category_sub:  document.getElementById('trans-sub-cat').value,
        note:          document.getElementById('trans-note').value,
        source:        'app',
        wallet_id:     walletVal ? parseInt(walletVal) : null
    };
    try {
        const res = await fetch(`${API_BASE}/api/transactions`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(transaction)
        });
        if (res.ok) {
            alert('Transaction added successfully!');
            this.reset();
            document.getElementById('trans-date').valueAsDate = new Date();
            loadDashboard();
        } else {
            alert('Error adding transaction');
        }
    } catch (err) {
        console.error(err);
        alert('Error adding transaction');
    }
});

// ── Edit Transaction ─────────────────────────────────────────
async function editTransaction(id) {
    try {
        const res = await fetch(`${API_BASE}/api/transactions/${id}`);
        const t   = await res.json();

        document.getElementById('edit-id').value       = t.id;
        document.getElementById('edit-date').value     = t.date;
        document.getElementById('edit-amount').value   = t.amount;
        document.getElementById('edit-type').value     = t.type;
        document.getElementById('edit-main-cat').value = t.category_main;
        document.getElementById('edit-sub-cat').value  = t.category_sub;
        document.getElementById('edit-note').value     = t.note || '';

        populateWalletSelects();
        if (t.wallet_id) document.getElementById('edit-wallet').value = t.wallet_id;

        document.getElementById('edit-modal').style.display = 'block';
    } catch (err) {
        console.error('Error loading transaction:', err);
    }
}

document.getElementById('edit-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const id        = document.getElementById('edit-id').value;
    const walletVal = document.getElementById('edit-wallet').value;
    const updates = {
        date:          document.getElementById('edit-date').value,
        amount:        parseInt(document.getElementById('edit-amount').value),
        type:          document.getElementById('edit-type').value,
        category_main: document.getElementById('edit-main-cat').value,
        category_sub:  document.getElementById('edit-sub-cat').value,
        note:          document.getElementById('edit-note').value,
        wallet_id:     walletVal ? parseInt(walletVal) : null
    };
    try {
        const res = await fetch(`${API_BASE}/api/transactions/${id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates)
        });
        if (res.ok) {
            closeModal('edit-modal');
            loadTransactions();
        } else {
            alert('Error updating transaction');
        }
    } catch (err) {
        console.error(err);
    }
});

// ── Delete Transaction ───────────────────────────────────────
async function deleteTransaction(id) {
    if (!confirm('Are you sure you want to delete this transaction?')) return;
    try {
        const res = await fetch(`${API_BASE}/api/transactions/${id}`, { method: 'DELETE' });
        if (res.ok) loadTransactions();
        else alert('Error deleting transaction');
    } catch (err) {
        console.error(err);
    }
}

// ── Modals ───────────────────────────────────────────────────
function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

window.onclick = function (event) {
    document.querySelectorAll('.modal').forEach(modal => {
        if (event.target === modal) modal.style.display = 'none';
    });
};

// ── Init ─────────────────────────────────────────────────────
document.getElementById('trans-date').valueAsDate = new Date();

document.addEventListener('DOMContentLoaded', function () {
    const dateEl = document.getElementById('header-date');
    if (dateEl) {
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }
    loadCategories();
    loadWallets();
    loadDashboard();
});
