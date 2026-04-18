-- Schema financiero para Wetsu
-- SQLite con encriptación (SQLCipher)

-- Tabla principal de transacciones
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,              -- YYYY-MM-DD
    amount INTEGER NOT NULL,         -- En centavos (CLP es entero)
    currency TEXT DEFAULT 'CLP',
    type TEXT CHECK(type IN ('income', 'expense', 'transfer', 'investment')),
    category_main TEXT,              -- Categoría principal (Entretenimiento, Ingresos, etc.)
    category_sub TEXT,               -- Subcategoría (Suscripción, Alimentos, etc.)
    note TEXT,                       -- Descripción
    source TEXT,                     -- Origen del dato (buddy, manual, bank, etc.)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de categorías (para normalizar y validar)
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    main_category TEXT NOT NULL,
    sub_category TEXT NOT NULL,
    type TEXT CHECK(type IN ('income', 'expense', 'investment')),
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(main_category, sub_category)
);

-- Tabla de presupuestos
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_main TEXT,
    category_sub TEXT,
    amount_limit INTEGER,            -- Límite mensual en centavos
    period TEXT DEFAULT 'monthly',   -- monthly, weekly, yearly
    start_date TEXT,
    end_date TEXT,
    is_active BOOLEAN DEFAULT 1
);

-- Tabla de metas de ahorro
CREATE TABLE IF NOT EXISTS savings_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount INTEGER NOT NULL,
    current_amount INTEGER DEFAULT 0,
    deadline TEXT,
    priority INTEGER DEFAULT 5,      -- 1-10
    is_active BOOLEAN DEFAULT 1
);

-- Carteras / Cuentas
CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,               -- 'Débito', 'Tarjeta Crédito', 'Efectivo', 'Otra'
    initial_balance INTEGER NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'CLP',
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Deudas
CREATE TABLE IF NOT EXISTS debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL CHECK(direction IN ('owed_by_me', 'owed_to_me')),
    counterpart_name TEXT NOT NULL,
    total_amount INTEGER NOT NULL,
    remaining_amount INTEGER NOT NULL,
    installments INTEGER DEFAULT 1,
    installment_amount INTEGER,
    due_date TEXT,
    notes TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paid')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pagos de deudas
CREATE TABLE IF NOT EXISTS debt_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debt_id INTEGER NOT NULL REFERENCES debts(id),
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    amount INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    installment_number INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_main, category_sub);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_wallet ON transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_debt_payments_debt ON debt_payments(debt_id);

-- Insertar categorías base basadas en tus datos
INSERT OR IGNORE INTO categories (main_category, sub_category, type) VALUES
('Ingresos', 'Salario', 'income'),
('Ingresos', 'Inversiones', 'income'),
('Ingresos', 'Cashback', 'income'),
('Ingresos', 'Ventas', 'income'),
('Ingresos', 'Devoluciones', 'income'),
('Comida y bebida', 'Alimentos', 'expense'),
('Comida y bebida', 'Restaurante', 'expense'),
('Transporte', 'Gasolina', 'expense'),
('Transporte', 'Parking', 'expense'),
('Transporte', 'Taxi', 'expense'),
('Alojamiento', 'Alquiler', 'expense'),
('Alojamiento', 'Internet', 'expense'),
('Alojamiento', 'Electricidad', 'expense'),
('Alojamiento', 'Agua', 'expense'),
('Alojamiento', 'Teléfono', 'expense'),
('Alojamiento', 'Facturas', 'expense'),
('Estilo de vida', 'Familia', 'expense'),
('Estilo de vida', 'Dentista', 'expense'),
('Estilo de vida', 'Farmacia', 'expense'),
('Estilo de vida', 'Médico', 'expense'),
('Estilo de vida', 'Mascota', 'expense'),
('Entretenimiento', 'Suscripciones', 'expense'),
('Entretenimiento', 'Entretenimiento', 'expense'),
('Entretenimiento', 'Deportes', 'expense'),
('Miscelánea', 'Miscelánea', 'expense'),
('Miscelánea', 'Ropa', 'expense'),
('Miscelánea', 'Tarjeta de crédito', 'expense'),
('Deuda', 'Préstamo', 'expense'),
('Deuda', 'Santander consumer auto Préstamo', 'expense'),
('Ahorros', 'Ahorro Mercadolibre', 'expense');
