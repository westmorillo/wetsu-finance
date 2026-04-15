#!/usr/bin/env python3
"""
Donatello - Finance Agent for Wetsu
Personal financial monitoring and reporting system
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class Donatello:
    """Finance agent for monitoring and analyzing Wetsu's finances"""
    
    def __init__(self, db_path: str = "/opt/wetsu-finance/data/finance.db"):
        self.db_path = Path(db_path)
        self.emoji = "🐢"
        self.name = "Donatello"
        
    def _get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_summary(self, days: int = 30) -> Dict:
        """Get financial summary for the last N days"""
        conn = self._get_db()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Total income
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
            FROM transactions
            WHERE type = 'income' AND date >= ?
        """, (start_date,))
        income = cursor.fetchone()
        
        # Total expenses
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
            FROM transactions
            WHERE type = 'expense' AND date >= ?
        """, (start_date,))
        expense = cursor.fetchone()
        
        # Top expense categories
        cursor.execute("""
            SELECT category_main, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE type = 'expense' AND date >= ?
            GROUP BY category_main
            ORDER BY total DESC
            LIMIT 5
        """, (start_date,))
        top_categories = [dict(row) for row in cursor.fetchall()]
        
        # Recent transactions
        cursor.execute("""
            SELECT * FROM transactions
            WHERE date >= ?
            ORDER BY date DESC
            LIMIT 5
        """, (start_date,))
        recent = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'period_days': days,
            'income': {'total': income['total'], 'count': income['count']},
            'expense': {'total': expense['total'], 'count': expense['count']},
            'net': income['total'] - expense['total'],
            'top_categories': top_categories,
            'recent_transactions': recent
        }
    
    def check_alerts(self) -> List[str]:
        """Check for financial alerts/warnings"""
        conn = self._get_db()
        cursor = conn.cursor()
        
        alerts = []
        
        # Check for very large expenses (over $100k)
        cursor.execute("""
            SELECT * FROM transactions
            WHERE type = 'expense' AND amount > 100000
            AND date >= date('now', '-7 days')
            ORDER BY date DESC
        """)
        large_expenses = cursor.fetchall()
        if large_expenses:
            for exp in large_expenses:
                alerts.append(f"🔴 Large expense: {exp['category_main']} - ${exp['amount']:,} on {exp['date']}")
        
        # Check if expenses exceed income in last 7 days
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
            FROM transactions
            WHERE date >= date('now', '-7 days')
        """)
        result = cursor.fetchone()
        if result['expense'] > result['income'] and result['income'] > 0:
            deficit = result['expense'] - result['income']
            alerts.append(f"🟡 Weekly deficit: Expenses exceed income by ${deficit:,}")
        
        conn.close()
        return alerts
    
    def format_currency(self, amount: int) -> str:
        """Format amount as currency"""
        return f"${amount:,}"
    
    def generate_report(self, days: int = 7) -> str:
        """Generate a formatted financial report"""
        data = self.get_summary(days)
        alerts = self.check_alerts()
        
        # Status indicator
        status = "🟢" if data['net'] >= 0 else "🔴"
        
        report = f"""
{status} **Financial Report - Last {days} Days**

📊 **Summary**
• Income: {self.format_currency(data['income']['total'])} ({data['income']['count']} transactions)
• Expenses: {self.format_currency(data['expense']['total'])} ({data['expense']['count']} transactions)
• Net: {self.format_currency(data['net'])}

📈 **Top Expense Categories**
"""
        for i, cat in enumerate(data['top_categories'][:3], 1):
            report += f"{i}. {cat['category_main']}: {self.format_currency(cat['total'])}\n"
        
        if alerts:
            report += "\n⚠️ **Alerts**\n"
            for alert in alerts:
                report += f"• {alert}\n"
        else:
            report += "\n✅ No alerts - everything looks good!\n"
        
        report += "\n📝 **Recent Transactions**\n"
        for t in data['recent_transactions'][:3]:
            emoji = "📥" if t['type'] == 'income' else "📤"
            report += f"{emoji} {t['date']}: {t['category_main']} - {self.format_currency(t['amount'])}\n"
        
        return report
    
    def greet(self) -> str:
        """Initial greeting"""
        return f"""
{self.emoji} **Donatello here!**

Your personal finance agent. I'm monitoring your financial data and ready to help.

What would you like to do?
• "Show weekly report" - Last 7 days summary
• "Show monthly report" - Last 30 days analysis
• "Check alerts" - Any warnings or unusual activity
• "Add transaction" - Log a new expense or income
• "Search [query]" - Find specific transactions

Or just ask me anything about your finances!
"""

# CLI interface
if __name__ == "__main__":
    import sys
    
    don = Donatello()
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:]).lower()
        
        if "weekly" in command or "7" in command:
            print(don.generate_report(7))
        elif "monthly" in command or "30" in command:
            print(don.generate_report(30))
        elif "alert" in command:
            alerts = don.check_alerts()
            if alerts:
                print("⚠️ Alerts found:\n")
                for alert in alerts:
                    print(f"• {alert}")
            else:
                print("✅ No alerts - finances look healthy!")
        elif "summary" in command:
            data = don.get_summary(30)
            print(f"📊 Last 30 days:\n• Income: {don.format_currency(data['income']['total'])}\n• Expenses: {don.format_currency(data['expense']['total'])}\n• Net: {don.format_currency(data['net'])}")
        else:
            print(don.greet())
    else:
        print(don.greet())
