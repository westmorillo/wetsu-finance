#!/usr/bin/env python3
"""
Finance App - FastAPI Backend
For Wetsu's personal finance tracking
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from pathlib import Path
import sqlite3
import json

# Paths
DB_PATH = Path('/root/.openclaw/workspace/finance/data/finance.db')
STATIC_DIR = Path('/root/.openclaw/workspace/finance/app/static')
TEMPLATES_DIR = Path('/root/.openclaw/workspace/finance/app/templates')

app = FastAPI(title="Wetsu Finance", version="1.0.0")

# Serve static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Database connection helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Pydantic models
class Transaction(BaseModel):
    id: Optional[int] = None
    date: str
    amount: int
    currency: str = "CLP"
    type: str
    category_main: str
    category_sub: str
    note: Optional[str] = ""
    source: str = "app"

class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    category_main: Optional[str] = None
    category_sub: Optional[str] = None
    note: Optional[str] = None

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard"""
    with open(TEMPLATES_DIR / "index.html", "r") as f:
        return f.read()

@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard summary data"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Summary by type
    cursor.execute("""
        SELECT type, COUNT(*) as count, SUM(amount) as total
        FROM transactions
        GROUP BY type
    """)
    summary = {row['type']: {'count': row['count'], 'total': row['total']} for row in cursor.fetchall()}
    
    # Expenses by category
    cursor.execute("""
        SELECT category_main, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category_main
        ORDER BY total DESC
    """)
    expenses_by_category = [dict(row) for row in cursor.fetchall()]
    
    # Income by category
    cursor.execute("""
        SELECT category_main, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE type = 'income'
        GROUP BY category_main
        ORDER BY total DESC
    """)
    income_by_category = [dict(row) for row in cursor.fetchall()]
    
    # Recent transactions
    cursor.execute("""
        SELECT * FROM transactions
        ORDER BY date DESC, id DESC
        LIMIT 10
    """)
    recent = [dict(row) for row in cursor.fetchall()]
    
    # Monthly totals (last 6 months)
    cursor.execute("""
        SELECT substr(date, 1, 7) as month, 
               SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """)
    monthly = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "summary": summary,
        "expenses_by_category": expenses_by_category,
        "income_by_category": income_by_category,
        "recent_transactions": recent,
        "monthly_trend": monthly
    }

@app.get("/api/transactions")
async def get_transactions(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get paginated transactions with optional filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    
    if type:
        query += " AND type = ?"
        params.append(type)
    
    if category:
        query += " AND category_main = ?"
        params.append(category)
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    query += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    
    # Get total count for pagination
    count_query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
    count_params = params[:-2]  # Remove limit and offset
    
    if type:
        count_query += " AND type = ?"
    if category:
        count_query += " AND category_main = ?"
    if start_date:
        count_query += " AND date >= ?"
    if end_date:
        count_query += " AND date <= ?"
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "transactions": transactions,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/transactions/{transaction_id}")
async def get_transaction(transaction_id: int):
    """Get a single transaction by ID"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return dict(row)

@app.post("/api/transactions")
async def create_transaction(transaction: Transaction):
    """Create a new transaction"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO transactions (date, amount, currency, type, category_main, category_sub, note, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (transaction.date, transaction.amount, transaction.currency, 
          transaction.type, transaction.category_main, transaction.category_sub, 
          transaction.note, transaction.source))
    
    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": transaction_id, "message": "Transaction created successfully"}

@app.put("/api/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, update: TransactionUpdate):
    """Update an existing transaction"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Build update query dynamically
    updates = []
    params = []
    
    if update.date is not None:
        updates.append("date = ?")
        params.append(update.date)
    if update.amount is not None:
        updates.append("amount = ?")
        params.append(update.amount)
    if update.currency is not None:
        updates.append("currency = ?")
        params.append(update.currency)
    if update.type is not None:
        updates.append("type = ?")
        params.append(update.type)
    if update.category_main is not None:
        updates.append("category_main = ?")
        params.append(update.category_main)
    if update.category_sub is not None:
        updates.append("category_sub = ?")
        params.append(update.category_sub)
    if update.note is not None:
        updates.append("note = ?")
        params.append(update.note)
    
    if not updates:
        conn.close()
        return {"message": "No fields to update"}
    
    query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
    params.append(transaction_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    return {"message": "Transaction updated successfully"}

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    """Delete a transaction"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Transaction deleted successfully"}

@app.get("/api/categories")
async def get_categories():
    """Get all available categories"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT main_category, sub_category, type 
        FROM categories 
        WHERE is_active = 1
        ORDER BY main_category, sub_category
    """)
    
    categories = {}
    for row in cursor.fetchall():
        main = row['main_category']
        if main not in categories:
            categories[main] = []
        categories[main].append({
            "sub": row['sub_category'],
            "type": row['type']
        })
    
    conn.close()
    return categories

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
