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
import os

# Paths — configurable via env vars for Docker
DB_PATH = Path(os.getenv("DB_PATH", "/app/data/finance.db"))
STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "/app/templates"))

app = FastAPI(title="Wetsu Finance", version="1.0.0")

# Serve static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Database connection helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def run_migrations(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(transactions)")
    cols = {row['name'] for row in cursor.fetchall()}
    if 'wallet_id' not in cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN wallet_id INTEGER REFERENCES wallets(id)")
    # Add due_day to wallets if not present
    cursor.execute("PRAGMA table_info(wallets)")
    wcols = {row['name'] for row in cursor.fetchall()}
    if 'due_day' not in wcols:
        cursor.execute("ALTER TABLE wallets ADD COLUMN due_day INTEGER")
    # Create transfers table if not present (not in original schema.sql)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_wallet_id INTEGER NOT NULL REFERENCES wallets(id),
            to_wallet_id   INTEGER NOT NULL REFERENCES wallets(id),
            amount         INTEGER NOT NULL,
            date           TEXT NOT NULL,
            note           TEXT,
            from_tx_id     INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
            to_tx_id       INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

# SQL fragment to compute current wallet balance (reused in multiple queries)
_BALANCE_SQL = """
    (w.initial_balance
     + COALESCE(SUM(CASE WHEN t.type='income' THEN t.amount
                         WHEN t.type='transfer' AND t.category_sub='entrada' THEN t.amount
                         ELSE 0 END), 0)
     - COALESCE(SUM(CASE WHEN t.type IN ('expense','investment') THEN t.amount
                         WHEN t.type='transfer' AND t.category_sub='salida' THEN t.amount
                         ELSE 0 END), 0)
    )
"""

@app.on_event("startup")
async def startup():
    conn = get_db()
    schema_path = Path(__file__).parent / "data" / "schema.sql"
    if schema_path.exists():
        with open(schema_path) as f:
            sql = f.read()
        # Run migrations (add missing columns) before the full schema so
        # indexes that reference new columns don't fail on existing DBs
        run_migrations(conn)
        conn.executescript(sql)
    conn.close()

# --- Pydantic models ---

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
    wallet_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    category_main: Optional[str] = None
    category_sub: Optional[str] = None
    note: Optional[str] = None
    wallet_id: Optional[int] = None

class WalletCreate(BaseModel):
    name: str
    type: str
    initial_balance: int = 0
    currency: str = "CLP"
    due_day: Optional[int] = None   # día de vencimiento mensual (solo TC)

class WalletUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    due_day: Optional[int] = None

class WalletAdjustment(BaseModel):
    target_balance: int  # puede ser negativo (ej: saldo deudor en TC)
    date: str
    note: Optional[str] = ""

class DebtCreate(BaseModel):
    direction: str
    counterpart_name: str
    total_amount: int
    installments: int = 1
    due_date: Optional[str] = None
    notes: Optional[str] = ""

class DebtPaymentCreate(BaseModel):
    amount: int
    payment_date: str
    wallet_id: Optional[int] = None
    installment_number: Optional[int] = None
    notes: Optional[str] = ""

class DebtUpdate(BaseModel):
    counterpart_name: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None

class TransferCreate(BaseModel):
    from_wallet_id: int
    to_wallet_id: int
    amount: int
    date: str
    note: Optional[str] = ""

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    with open(TEMPLATES_DIR / "index.html", "r") as f:
        return f.read()

@app.get("/api/dashboard")
async def get_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT type, COUNT(*) as count, SUM(amount) as total
        FROM transactions
        GROUP BY type
    """)
    summary = {row['type']: {'count': row['count'], 'total': row['total']} for row in cursor.fetchall()}

    cursor.execute("""
        SELECT category_main, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category_main
        ORDER BY total DESC
    """)
    expenses_by_category = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT category_main, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE type = 'income'
        GROUP BY category_main
        ORDER BY total DESC
    """)
    income_by_category = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT * FROM transactions
        ORDER BY date DESC, id DESC
        LIMIT 10
    """)
    recent = [dict(row) for row in cursor.fetchall()]

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

    # Wallets with computed current balance
    cursor.execute(f"""
        SELECT w.id, w.name, w.type, w.currency, w.due_day,
               {_BALANCE_SQL} AS current_balance
        FROM wallets w
        LEFT JOIN transactions t ON t.wallet_id = w.id
        WHERE w.is_active = 1
        GROUP BY w.id
        ORDER BY w.id
    """)
    wallets = [dict(row) for row in cursor.fetchall()]

    # Debt summary
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN direction='owed_by_me' THEN remaining_amount ELSE 0 END), 0) AS total_owed_by_me,
            COALESCE(SUM(CASE WHEN direction='owed_to_me' THEN remaining_amount ELSE 0 END), 0) AS total_owed_to_me,
            COUNT(*) AS active_count
        FROM debts
        WHERE status = 'active'
    """)
    debt_row = cursor.fetchone()
    debt_summary = dict(debt_row) if debt_row else {"total_owed_by_me": 0, "total_owed_to_me": 0, "active_count": 0}

    conn.close()

    return {
        "summary": summary,
        "expenses_by_category": expenses_by_category,
        "income_by_category": income_by_category,
        "recent_transactions": recent,
        "monthly_trend": monthly,
        "wallets": wallets,
        "debt_summary": debt_summary
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

    count_query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
    count_params = params[:-2]
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
    return {"transactions": transactions, "total": total, "limit": limit, "offset": offset}

@app.get("/api/transactions/{transaction_id}")
async def get_transaction(transaction_id: int):
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (date, amount, currency, type, category_main, category_sub, note, source, wallet_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (transaction.date, transaction.amount, transaction.currency,
          transaction.type, transaction.category_main, transaction.category_sub,
          transaction.note, transaction.source, transaction.wallet_id))
    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": transaction_id, "message": "Transaction created successfully"}

@app.put("/api/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, update: TransactionUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Transaction not found")

    updates = []
    params = []
    for field, col in [('date','date'), ('amount','amount'), ('currency','currency'),
                       ('type','type'), ('category_main','category_main'),
                       ('category_sub','category_sub'), ('note','note'), ('wallet_id','wallet_id')]:
        val = getattr(update, field)
        if val is not None:
            updates.append(f"{col} = ?")
            params.append(val)

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
        categories[main].append({"sub": row['sub_category'], "type": row['type']})
    conn.close()
    return categories

# --- Wallets ---

@app.get("/api/wallets")
async def get_wallets():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT w.id, w.name, w.type, w.currency, w.initial_balance, w.created_at, w.due_day,
               {_BALANCE_SQL} AS current_balance
        FROM wallets w
        LEFT JOIN transactions t ON t.wallet_id = w.id
        WHERE w.is_active = 1
        GROUP BY w.id
        ORDER BY w.id
    """)
    wallets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return wallets

@app.post("/api/wallets")
async def create_wallet(wallet: WalletCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wallets (name, type, initial_balance, currency, due_day)
        VALUES (?, ?, ?, ?, ?)
    """, (wallet.name, wallet.type, wallet.initial_balance, wallet.currency, wallet.due_day))
    wallet_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": wallet_id, "message": "Wallet created successfully"}

@app.put("/api/wallets/{wallet_id}")
async def update_wallet(wallet_id: int, update: WalletUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM wallets WHERE id = ? AND is_active = 1", (wallet_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Wallet not found")

    updates = []
    params = []
    if update.name is not None:
        updates.append("name = ?")
        params.append(update.name)
    if update.type is not None:
        updates.append("type = ?")
        params.append(update.type)
    if 'due_day' in (update.model_fields_set or set()):
        updates.append("due_day = ?")
        params.append(update.due_day)

    if not updates:
        conn.close()
        return {"message": "No fields to update"}

    params.append(wallet_id)
    cursor.execute(f"UPDATE wallets SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"message": "Wallet updated successfully"}

@app.delete("/api/wallets/{wallet_id}")
async def delete_wallet(wallet_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM wallets WHERE id = ? AND is_active = 1", (wallet_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Wallet not found")
    cursor.execute("UPDATE wallets SET is_active = 0 WHERE id = ?", (wallet_id,))
    conn.commit()
    conn.close()
    return {"message": "Wallet deactivated"}

@app.post("/api/wallets/{wallet_id}/adjust")
async def adjust_wallet_balance(wallet_id: int, adjustment: WalletAdjustment):
    conn = get_db()
    cursor = conn.cursor()

    # Get current computed balance
    cursor.execute(f"""
        SELECT w.id, w.name,
               {_BALANCE_SQL} AS current_balance
        FROM wallets w
        LEFT JOIN transactions t ON t.wallet_id = w.id
        WHERE w.id = ? AND w.is_active = 1
        GROUP BY w.id
    """, (wallet_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Wallet not found")

    current_balance = row["current_balance"]
    diff = adjustment.target_balance - current_balance

    if diff == 0:
        conn.close()
        return {"message": "No adjustment needed", "current_balance": current_balance, "diff": 0}

    tx_type = "income" if diff > 0 else "expense"
    note = adjustment.note or f"Ajuste de saldo — {row['name']}"

    cursor.execute("""
        INSERT INTO transactions (date, amount, currency, type, category_main, category_sub,
                                  note, source, wallet_id)
        VALUES (?, ?, 'CLP', ?, 'Ajuste', 'Ajuste de saldo', ?, 'adjustment', ?)
    """, (adjustment.date, abs(diff), tx_type, note, wallet_id))

    conn.commit()
    conn.close()

    return {
        "message": "Balance adjusted",
        "previous_balance": current_balance,
        "new_balance": adjustment.target_balance,
        "diff": diff,
        "transaction_type": tx_type
    }

# --- Transfers ---

@app.get("/api/transfers")
async def get_transfers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tr.*,
               wf.name AS from_wallet_name,
               wt.name AS to_wallet_name
        FROM transfers tr
        JOIN wallets wf ON wf.id = tr.from_wallet_id
        JOIN wallets wt ON wt.id = tr.to_wallet_id
        ORDER BY tr.date DESC, tr.id DESC
    """)
    transfers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transfers

@app.post("/api/transfers")
async def create_transfer(transfer: TransferCreate):
    if transfer.from_wallet_id == transfer.to_wallet_id:
        raise HTTPException(status_code=400, detail="Las carteras de origen y destino deben ser diferentes")
    if transfer.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero")

    conn = get_db()
    cursor = conn.cursor()

    # Validate both wallets exist
    cursor.execute("SELECT id, name FROM wallets WHERE id IN (?, ?) AND is_active = 1",
                   (transfer.from_wallet_id, transfer.to_wallet_id))
    found = cursor.fetchall()
    if len(found) < 2:
        conn.close()
        raise HTTPException(status_code=404, detail="Una o ambas carteras no existen")

    wallet_names = {row['id']: row['name'] for row in found}
    note = transfer.note or f"Transferencia: {wallet_names[transfer.from_wallet_id]} → {wallet_names[transfer.to_wallet_id]}"

    # Salida — debits source wallet
    cursor.execute("""
        INSERT INTO transactions (date, amount, currency, type, category_main, category_sub,
                                  note, source, wallet_id)
        VALUES (?, ?, 'CLP', 'transfer', 'Transferencia', 'salida', ?, 'app', ?)
    """, (transfer.date, transfer.amount, note, transfer.from_wallet_id))
    from_tx_id = cursor.lastrowid

    # Entrada — credits destination wallet
    cursor.execute("""
        INSERT INTO transactions (date, amount, currency, type, category_main, category_sub,
                                  note, source, wallet_id)
        VALUES (?, ?, 'CLP', 'transfer', 'Transferencia', 'entrada', ?, 'app', ?)
    """, (transfer.date, transfer.amount, note, transfer.to_wallet_id))
    to_tx_id = cursor.lastrowid

    # Link them in transfers table
    cursor.execute("""
        INSERT INTO transfers (from_wallet_id, to_wallet_id, amount, date, note, from_tx_id, to_tx_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (transfer.from_wallet_id, transfer.to_wallet_id, transfer.amount,
          transfer.date, note, from_tx_id, to_tx_id))
    transfer_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return {"id": transfer_id, "from_tx_id": from_tx_id, "to_tx_id": to_tx_id,
            "message": "Transferencia registrada"}

@app.delete("/api/transfers/{transfer_id}")
async def delete_transfer(transfer_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transfers WHERE id = ?", (transfer_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")

    # Delete both linked transactions
    for tx_id in [row['from_tx_id'], row['to_tx_id']]:
        if tx_id:
            cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    cursor.execute("DELETE FROM transfers WHERE id = ?", (transfer_id,))
    conn.commit()
    conn.close()
    return {"message": "Transferencia eliminada"}

# --- Debts ---

@app.get("/api/debts")
async def get_debts(status: Optional[str] = Query(None)):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM debts"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    debts = [dict(row) for row in cursor.fetchall()]

    # Attach payments to each debt
    for debt in debts:
        cursor.execute("""
            SELECT * FROM debt_payments WHERE debt_id = ? ORDER BY payment_date DESC
        """, (debt['id'],))
        debt['payments'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return debts

@app.post("/api/debts")
async def create_debt(debt: DebtCreate):
    if debt.direction not in ('owed_by_me', 'owed_to_me'):
        raise HTTPException(status_code=400, detail="direction must be 'owed_by_me' or 'owed_to_me'")

    installment_amount = debt.total_amount // debt.installments if debt.installments > 1 else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO debts (direction, counterpart_name, total_amount, remaining_amount,
                           installments, installment_amount, due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (debt.direction, debt.counterpart_name, debt.total_amount, debt.total_amount,
          debt.installments, installment_amount, debt.due_date, debt.notes))
    debt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": debt_id, "message": "Debt created successfully"}

@app.put("/api/debts/{debt_id}")
async def update_debt(debt_id: int, update: DebtUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM debts WHERE id = ?", (debt_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Debt not found")

    updates = []
    params = []
    if update.counterpart_name is not None:
        updates.append("counterpart_name = ?")
        params.append(update.counterpart_name)
    if update.due_date is not None:
        updates.append("due_date = ?")
        params.append(update.due_date)
    if update.notes is not None:
        updates.append("notes = ?")
        params.append(update.notes)

    if not updates:
        conn.close()
        return {"message": "No fields to update"}

    params.append(debt_id)
    cursor.execute(f"UPDATE debts SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"message": "Debt updated successfully"}

@app.post("/api/debts/{debt_id}/payments")
async def record_debt_payment(debt_id: int, payment: DebtPaymentCreate):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM debts WHERE id = ?", (debt_id,))
    debt = cursor.fetchone()
    if not debt:
        conn.close()
        raise HTTPException(status_code=404, detail="Debt not found")

    if payment.amount > debt['remaining_amount']:
        conn.close()
        raise HTTPException(status_code=400, detail="Payment exceeds remaining amount")

    # Create linked transaction
    tx_type = 'expense' if debt['direction'] == 'owed_by_me' else 'income'
    cursor.execute("""
        INSERT INTO transactions (date, amount, currency, type, category_main, category_sub,
                                  note, source, wallet_id)
        VALUES (?, ?, 'CLP', ?, 'Deuda', 'Pago', ?, 'debt', ?)
    """, (payment.payment_date, payment.amount, tx_type,
          payment.notes or f"Pago deuda #{debt_id}", payment.wallet_id))
    transaction_id = cursor.lastrowid

    # Record the payment
    cursor.execute("""
        INSERT INTO debt_payments (debt_id, transaction_id, amount, payment_date,
                                   installment_number, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (debt_id, transaction_id, payment.amount, payment.payment_date,
          payment.installment_number, payment.notes))

    # Update remaining amount
    new_remaining = debt['remaining_amount'] - payment.amount
    new_status = 'paid' if new_remaining <= 0 else 'active'
    cursor.execute("""
        UPDATE debts SET remaining_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_remaining, new_status, debt_id))

    conn.commit()
    conn.close()
    return {"message": "Payment recorded", "remaining_amount": new_remaining, "status": new_status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
