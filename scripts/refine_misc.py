#!/usr/bin/env python3
"""
Refina la categoría Miscelánea de Wetsu
Clasifica transacciones basado en notas y subcategorías
"""

import sqlite3
from pathlib import Path

DB_PATH = Path('/root/.openclaw/workspace/finance/data/finance.db')

# Reglas de reclasificación basadas en notas y subcategorías
RECLASSIFICATION_RULES = [
    # Equipo fotográfico
    ('Cámara', 'Tecnología', 'Equipo Fotográfico'),
    ('lente', 'Tecnología', 'Equipo Fotográfico'),
    ('Lente', 'Tecnología', 'Equipo Fotográfico'),
    ('cámara', 'Tecnología', 'Equipo Fotográfico'),
    ('Bolso cámara', 'Tecnología', 'Accesorios Fotografía'),
    ('luz para cámara', 'Tecnología', 'Equipo Fotográfico'),
    ('trípode', 'Tecnología', 'Accesorios Fotografía'),
    ('micro', 'Tecnología', 'Equipo Audio'),
    
    # Boda
    ('boda', 'Eventos', 'Boda'),
    ('Boda', 'Eventos', 'Boda'),
    ('fotógrafo', 'Eventos', 'Boda'),
    ('Fotógrafo', 'Eventos', 'Boda'),
    ('anillo matrimonio', 'Eventos', 'Boda'),
    
    # Emprendimiento / Inversión
    ('Emprendimiento', 'Negocio', 'Inversión'),
    ('emprendimiento', 'Negocio', 'Inversión'),
    ('AliExpress', 'Negocio', 'Materiales'),
    ('compra materiales', 'Negocio', 'Materiales'),
    ('Filamentos', 'Negocio', 'Materiales 3D'),
    ('filamento', 'Negocio', 'Materiales 3D'),
    
    # Domótica / Casa inteligente
    ('domótica', 'Tecnología', 'Domótica'),
    ('Cable', 'Tecnología', 'Cables y Conectores'),
    ('cable', 'Tecnología', 'Cables y Conectores'),
    ('socket lámpara', 'Tecnología', 'Iluminación'),
    
    # Mejoras hogar
    ('ventilador', 'Hogar', 'Climatización'),
    
    # Financiero
    ('Tarjeta de crédito', 'Financiero', 'Tarjeta'),
    ('pago tarjeta', 'Financiero', 'Tarjeta'),
    
    # Ropa
    ('boxers', 'Vestimenta', 'Ropa interior'),
    ('Ropa', 'Vestimenta', 'Ropa'),
    ('franelas', 'Vestimenta', 'Ropa'),
    
    # Impresión
    ('Impresión', 'Negocio', 'Servicios Impresión'),
    ('impresión', 'Negocio', 'Servicios Impresión'),
    
    # Efectivo
    ('Retiro', 'Financiero', 'Efectivo'),
    ('retiro', 'Financiero', 'Efectivo'),
]

def reclassify_transactions():
    """Reclasifica transacciones de Miscelánea basado en reglas"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener todas las transacciones de Miscelánea
    cursor.execute('''
        SELECT id, note, category_sub
        FROM transactions
        WHERE category_main = 'Miscelánea'
    ''')
    
    misc_transactions = cursor.fetchall()
    reclassified = 0
    
    for trans_id, note, sub_category in misc_transactions:
        note_lower = (note or '').lower()
        sub_lower = (sub_category or '').lower()
        
        new_main = None
        new_sub = None
        
        # Buscar coincidencias en reglas
        for keyword, main_cat, sub_cat in RECLASSIFICATION_RULES:
            if keyword.lower() in note_lower or keyword.lower() in sub_lower:
                new_main = main_cat
                new_sub = sub_cat
                break
        
        # Si no hay coincidencia, usar subcategoría original como guía
        if not new_main:
            if 'Ropa' in sub_category:
                new_main = 'Vestimenta'
                new_sub = 'Ropa'
            elif 'Tarjeta' in sub_category:
                new_main = 'Financiero'
                new_sub = 'Tarjeta'
            elif sub_category == 'Miscelánea':
                # Dejar en Miscelánea pero documentar
                new_main = 'Otros'
                new_sub = 'Sin clasificar'
        
        if new_main:
            cursor.execute('''
                UPDATE transactions
                SET category_main = ?, category_sub = ?
                WHERE id = ?
            ''', (new_main, new_sub, trans_id))
            reclassified += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Reclasificadas {reclassified} de {len(misc_transactions)} transacciones de Miscelánea")

def add_new_categories():
    """Agrega las nuevas categorías al catálogo"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_categories = [
        ('Tecnología', 'Equipo Fotográfico', 'expense'),
        ('Tecnología', 'Accesorios Fotografía', 'expense'),
        ('Tecnología', 'Equipo Audio', 'expense'),
        ('Tecnología', 'Domótica', 'expense'),
        ('Tecnología', 'Cables y Conectores', 'expense'),
        ('Tecnología', 'Iluminación', 'expense'),
        ('Eventos', 'Boda', 'expense'),
        ('Negocio', 'Inversión', 'expense'),
        ('Negocio', 'Materiales', 'expense'),
        ('Negocio', 'Materiales 3D', 'expense'),
        ('Negocio', 'Servicios Impresión', 'expense'),
        ('Hogar', 'Climatización', 'expense'),
        ('Financiero', 'Tarjeta', 'expense'),
        ('Financiero', 'Efectivo', 'expense'),
        ('Vestimenta', 'Ropa', 'expense'),
        ('Vestimenta', 'Ropa interior', 'expense'),
        ('Otros', 'Sin clasificar', 'expense'),
    ]
    
    for main_cat, sub_cat, cat_type in new_categories:
        cursor.execute('''
            INSERT OR IGNORE INTO categories (main_category, sub_category, type)
            VALUES (?, ?, ?)
        ''', (main_cat, sub_cat, cat_type))
    
    conn.commit()
    conn.close()
    print("✅ Nuevas categorías agregadas")

def show_refined_summary():
    """Muestra resumen después de la reclasificación"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Gastos por categoría principal (excluyendo Ingresos)
    cursor.execute('''
        SELECT category_main, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category_main
        ORDER BY total DESC
    ''')
    
    print("\n💸 GASTOS POR CATEGORÍA (refinado):")
    print("=" * 50)
    total_gastos = 0
    for row in cursor.fetchall():
        print(f"{row[0]:25} {row[2]:3} items  ${row[1]:>12,}")
        total_gastos += row[1]
    
    # Top subcategorías
    cursor.execute('''
        SELECT category_main, category_sub, SUM(amount) as total
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category_main, category_sub
        ORDER BY total DESC
        LIMIT 15
    ''')
    
    print("\n🔍 TOP 15 SUBCATEGORÍAS:")
    print("=" * 50)
    for row in cursor.fetchall():
        print(f"{row[0]:15} > {row[1]:20} ${row[2]:>12,}")
    
    # Ingresos
    cursor.execute('''
        SELECT category_main, SUM(amount) as total
        FROM transactions
        WHERE type = 'income'
        GROUP BY category_main
    ''')
    
    print("\n💰 INGRESOS:")
    print("=" * 50)
    total_ingresos = 0
    for row in cursor.fetchall():
        print(f"{row[0]:25} ${row[1]:>12,}")
        total_ingresos += row[1]
    
    # Balance
    print(f"\n📊 BALANCE:")
    print("=" * 50)
    print(f"{'Ingresos totales:':25} ${total_ingresos:>12,}")
    print(f"{'Gastos totales:':25} ${total_gastos:>12,}")
    print(f"{'Diferencia:':25} ${total_ingresos - total_gastos:>12,}")
    
    conn.close()

if __name__ == '__main__':
    print("🐀 Refinando categorías de Miscelánea...")
    add_new_categories()
    reclassify_transactions()
    show_refined_summary()
