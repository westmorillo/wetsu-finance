#!/usr/bin/env python3
"""
Inicializa la base de datos de finanzas de Wetsu
Carga el schema y los datos del CSV de Buddy
"""

import sqlite3
import csv
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path('/root/.openclaw/workspace/finance/data/finance.db')
SCHEMA_PATH = Path('/root/.openclaw/workspace/finance/data/schema.sql')

def init_database():
    """Crea la base de datos con el schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Leer y ejecutar schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    cursor.executescript(schema)
    
    conn.commit()
    conn.close()
    print(f"✅ Base de datos creada en {DB_PATH}")

def parse_amount(amount_str, category_main):
    """Parsea el monto y determina el tipo de transacción"""
    try:
        amount = int(amount_str)
    except ValueError:
        amount = 0
    
    # Lógica de Buddy: montos negativos = gastos, positivos = ingresos
    # PERO en Buddy, algunos "ingresos" están negativos (como inversiones que son compras)
    if category_main == 'Ingresos':
        # Ingresos positivos son ingresos reales
        # Ingresos negativos son inversiones/compras (gastos)
        if amount > 0:
            return abs(amount), 'income'
        else:
            return abs(amount), 'investment'
    elif category_main == 'Ahorros':
        return abs(amount), 'expense'
    elif category_main == 'Deuda':
        return abs(amount), 'expense'
    else:
        # Todo lo demás son gastos
        return abs(amount), 'expense'

def load_buddy_csv(csv_path):
    """Carga datos del CSV de Buddy"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        
        count = 0
        skipped = 0
        
        for row in reader:
            date_str = row['Fecha']
            category_main = row['Categoría principal']
            category_sub = row['Categoría']
            note = row['Nota']
            amount_raw = row['Cantidad']
            currency = row['Moneda']
            
            # Saltar transacciones con monto 0 (pagos de tarjeta que son solo registros)
            try:
                if int(amount_raw) == 0:
                    skipped += 1
                    continue
            except:
                skipped += 1
                continue
            
            amount, trans_type = parse_amount(amount_raw, category_main)
            
            # Insertar transacción
            cursor.execute('''
                INSERT INTO transactions 
                (date, amount, currency, type, category_main, category_sub, note, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, amount, currency, trans_type, category_main, category_sub, note, 'buddy'))
            
            count += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Cargadas {count} transacciones")
    print(f"⏭️  Saltadas {skipped} transacciones con monto 0")

def show_summary():
    """Muestra resumen de datos cargados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total por tipo
    cursor.execute('''
        SELECT type, COUNT(*) as count, SUM(amount) as total
        FROM transactions
        GROUP BY type
    ''')
    
    print("\n📊 RESUMEN POR TIPO:")
    print("-" * 40)
    for row in cursor.fetchall():
        print(f"{row[0]:15} {row[1]:4} transacciones  ${row[2]:>12,}")
    
    # Gastos por categoría principal
    cursor.execute('''
        SELECT category_main, SUM(amount) as total
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category_main
        ORDER BY total DESC
    ''')
    
    print("\n💸 TOP GASTOS POR CATEGORÍA:")
    print("-" * 40)
    for row in cursor.fetchall():
        print(f"{row[0]:25} ${row[1]:>12,}")
    
    # Ingresos
    cursor.execute('''
        SELECT category_main, SUM(amount) as total
        FROM transactions
        WHERE type = 'income'
        GROUP BY category_main
        ORDER BY total DESC
    ''')
    
    print("\n💰 INGRESOS:")
    print("-" * 40)
    for row in cursor.fetchall():
        print(f"{row[0]:25} ${row[1]:>12,}")
    
    conn.close()

if __name__ == '__main__':
    # Inicializar base de datos
    init_database()
    
    # Cargar datos del CSV si existe
    csv_path = '/root/.openclaw/media/inbound/buddy_export---b80429d4-1744-458a-9c28-a2245e636805.csv'
    if Path(csv_path).exists():
        load_buddy_csv(csv_path)
        show_summary()
    else:
        print("⚠️ No se encontró el archivo CSV")
