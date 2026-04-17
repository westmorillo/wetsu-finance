// Wetsu Finance App - Frontend JavaScript

const API_BASE = '';
let currentPage = 0;
const pageSize = 25;
let categories = {};
let expensesChart = null;
let trendChart = null;

// Tab navigation
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
    
    if (tabName === 'dashboard') {
        loadDashboard();
    } else if (tabName === 'transactions') {
        loadTransactions();
    }
}

// Format currency
function formatCurrency(amount) {
    return '$' + parseInt(amount).toLocaleString('en-US');
}

// Format date
function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Load dashboard data
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard`);
        const data = await response.json();
        
        // Update summary cards
        const income = data.summary.income || { count: 0, total: 0 };
        const expense = data.summary.expense || { count: 0, total: 0 };
        const investment = data.summary.investment || { count: 0, total: 0 };
        
        document.getElementById('total-income').textContent = formatCurrency(income.total);
        document.getElementById('income-count').textContent = `${income.count} transactions`;
        
        document.getElementById('total-expense').textContent = formatCurrency(expense.total);
        document.getElementById('expense-count').textContent = `${expense.count} transactions`;
        
        document.getElementById('total-investment').textContent = formatCurrency(investment.total);
        document.getElementById('investment-count').textContent = `${investment.count} transactions`;
        
        const netBalance = income.total - expense.total - investment.total;
        document.getElementById('net-balance').textContent = formatCurrency(netBalance);
        
        // Update recent transactions table
        const recentTable = document.querySelector('#recent-table tbody');
        recentTable.innerHTML = data.recent_transactions.map(t => `
            <tr>
                <td>${formatDate(t.date)}</td>
                <td>${t.category_main}</td>
                <td>${t.note || '-'}</td>
                <td class="${t.type === 'income' ? 'positive' : 'negative'}">${formatCurrency(t.amount)}</td>
                <td><span class="badge ${t.type}">${t.type}</span></td>
            </tr>
        `).join('');
        
        // Update charts
        updateCharts(data);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Update charts
function updateCharts(data) {
    // Expenses by category
    const expenseCtx = document.getElementById('expensesChart').getContext('2d');
    
    if (expensesChart) {
        expensesChart.destroy();
    }
    
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

    // Monthly trend
    const trendCtx = document.getElementById('trendChart').getContext('2d');

    if (trendChart) {
        trendChart.destroy();
    }

    const monthly = data.monthly_trend.reverse();

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

// Load transactions with pagination
async function loadTransactions() {
    try {
        const typeFilter = document.getElementById('filter-type').value;
        const categoryFilter = document.getElementById('filter-category').value;
        const startDate = document.getElementById('filter-start').value;
        const endDate = document.getElementById('filter-end').value;
        
        let url = `${API_BASE}/api/transactions?limit=${pageSize}&offset=${currentPage * pageSize}`;
        
        if (typeFilter) url += `&type=${typeFilter}`;
        if (categoryFilter) url += `&category=${categoryFilter}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        const table = document.querySelector('#transactions-table tbody');
        table.innerHTML = data.transactions.map(t => `
            <tr>
                <td class="col-id">${t.id}</td>
                <td>${formatDate(t.date)}</td>
                <td><span class="badge ${t.type}">${t.type}</span></td>
                <td>${t.category_main}</td>
                <td class="col-subcat">${t.category_sub}</td>
                <td>${t.note || '-'}</td>
                <td class="${t.type === 'income' ? 'positive' : 'negative'}">${formatCurrency(t.amount)}</td>
                <td>
                    <button class="action-btn edit" onclick="editTransaction(${t.id})">Edit</button>
                    <button class="action-btn delete" onclick="deleteTransaction(${t.id})">Delete</button>
                </td>
            </tr>
        `).join('');
        
        const totalPages = Math.ceil(data.total / pageSize);
        document.getElementById('page-info').textContent = `Page ${currentPage + 1} of ${totalPages || 1}`;
        
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// Pagination
function prevPage() {
    if (currentPage > 0) {
        currentPage--;
        loadTransactions();
    }
}

function nextPage() {
    currentPage++;
    loadTransactions();
}

// Load categories
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/api/categories`);
        categories = await response.json();
        
        // Populate main category dropdown
        const mainCatSelect = document.getElementById('trans-main-cat');
        const filterCatSelect = document.getElementById('filter-category');
        
        Object.keys(categories).forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat;
            mainCatSelect.appendChild(option);
            
            const filterOption = document.createElement('option');
            filterOption.value = cat;
            filterOption.textContent = cat;
            filterCatSelect.appendChild(filterOption);
        });
        
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Update subcategories when main category changes
document.getElementById('trans-main-cat')?.addEventListener('change', function() {
    const subCatSelect = document.getElementById('trans-sub-cat');
    subCatSelect.innerHTML = '<option value="">Select...</option>';
    
    const selectedMain = this.value;
    if (selectedMain && categories[selectedMain]) {
        categories[selectedMain].forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.sub;
            option.textContent = sub.sub;
            subCatSelect.appendChild(option);
        });
    }
});

// Add transaction form
document.getElementById('transaction-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const transaction = {
        date: document.getElementById('trans-date').value,
        amount: parseInt(document.getElementById('trans-amount').value),
        currency: document.getElementById('trans-currency').value,
        type: document.getElementById('trans-type').value,
        category_main: document.getElementById('trans-main-cat').value,
        category_sub: document.getElementById('trans-sub-cat').value,
        note: document.getElementById('trans-note').value,
        source: 'app'
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/transactions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(transaction)
        });
        
        if (response.ok) {
            alert('Transaction added successfully!');
            this.reset();
            loadDashboard();
        } else {
            alert('Error adding transaction');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error adding transaction');
    }
});

// Edit transaction
async function editTransaction(id) {
    try {
        const response = await fetch(`${API_BASE}/api/transactions/${id}`);
        const transaction = await response.json();
        
        document.getElementById('edit-id').value = transaction.id;
        document.getElementById('edit-date').value = transaction.date;
        document.getElementById('edit-amount').value = transaction.amount;
        document.getElementById('edit-type').value = transaction.type;
        document.getElementById('edit-main-cat').value = transaction.category_main;
        document.getElementById('edit-sub-cat').value = transaction.category_sub;
        document.getElementById('edit-note').value = transaction.note || '';
        
        document.getElementById('edit-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading transaction:', error);
    }
}

// Update transaction
document.getElementById('edit-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('edit-id').value;
    
    const updates = {
        date: document.getElementById('edit-date').value,
        amount: parseInt(document.getElementById('edit-amount').value),
        type: document.getElementById('edit-type').value,
        category_main: document.getElementById('edit-main-cat').value,
        category_sub: document.getElementById('edit-sub-cat').value,
        note: document.getElementById('edit-note').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/transactions/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        
        if (response.ok) {
            alert('Transaction updated!');
            closeModal();
            loadTransactions();
        } else {
            alert('Error updating transaction');
        }
    } catch (error) {
        console.error('Error:', error);
    }
});

// Delete transaction
async function deleteTransaction(id) {
    if (!confirm('Are you sure you want to delete this transaction?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/transactions/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Transaction deleted!');
            loadTransactions();
        } else {
            alert('Error deleting transaction');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Close modal
function closeModal() {
    document.getElementById('edit-modal').style.display = 'none';
}

// Close modal on outside click
window.onclick = function(event) {
    const modal = document.getElementById('edit-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Set today's date as default
document.getElementById('trans-date').valueAsDate = new Date();

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    const dateEl = document.getElementById('header-date');
    if (dateEl) {
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }
    loadCategories();
    loadDashboard();
});
