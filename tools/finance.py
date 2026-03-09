# tools/finance.py
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        url = os.getenv("BALANCEFLOW_SUPABASE_URL")
        key = os.getenv("BALANCEFLOW_SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError(
                "BALANCEFLOW_SUPABASE_URL and BALANCEFLOW_SUPABASE_ANON_KEY must be set in .env")
        _client = create_client(url, key)
    return _client


def get_account_balances() -> str:
    """Get all active account balances."""
    try:
        sb = _get_client()
        result = sb.table("accounts") \
            .select("name, type, balance, currency") \
            .eq("is_active", True) \
            .execute()

        if not result.data:
            return "No active accounts found."

        total = sum(a["balance"] for a in result.data)
        lines = []
        for a in result.data:
            lines.append(f"  {a['name']} ({a['type']}): ₹{a['balance']:,.2f}")

        return f"Account balances:\n" + "\n".join(lines) + f"\n\nTotal: ₹{total:,.2f}"

    except Exception as e:
        return f"Could not fetch balances: {e}"


def get_spending_summary(days: int = 30) -> str:
    """Get total income and expenses for the last N days."""
    try:
        sb = _get_client()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        result = sb.table("transactions") \
            .select("type, amount") \
            .eq("is_deleted", False) \
            .gte("date", since) \
            .in_("type", ["income", "expense"]) \
            .execute()

        if not result.data:
            return f"No transactions found in the last {days} days."

        income = sum(t["amount"] for t in result.data if t["type"] == "income")
        expense = sum(t["amount"]
                      for t in result.data if t["type"] == "expense")
        net = income - expense

        return (
            f"Last {days} days summary:\n"
            f"  Income:   ₹{income:,.2f}\n"
            f"  Expenses: ₹{expense:,.2f}\n"
            f"  Net:      ₹{net:,.2f} ({'saved' if net >= 0 else 'overspent'})"
        )

    except Exception as e:
        return f"Could not fetch summary: {e}"


def get_spending_by_category(days: int = 30) -> str:
    """Get expense breakdown by category for the last N days."""
    try:
        sb = _get_client()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        result = sb.table("transactions") \
            .select("amount, categories(name)") \
            .eq("is_deleted", False) \
            .eq("type", "expense") \
            .gte("date", since) \
            .execute()

        if not result.data:
            return f"No expenses found in the last {days} days."

        # group by category
        cats = {}
        for t in result.data:
            cat_name = t.get("categories", {})
            cat_name = cat_name.get(
                "name", "Uncategorized") if cat_name else "Uncategorized"
            cats[cat_name] = cats.get(cat_name, 0) + float(t["amount"])

        # sort by amount descending
        sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
        lines = [f"  {name}: ₹{amt:,.2f}" for name, amt in sorted_cats]

        return f"Spending by category (last {days} days):\n" + "\n".join(lines)

    except Exception as e:
        return f"Could not fetch categories: {e}"


def get_recent_transactions(limit: int = 10) -> str:
    """Get the most recent transactions."""
    try:
        sb = _get_client()

        result = sb.table("transactions") \
            .select("type, amount, date, note, merchants(name), categories(name)") \
            .eq("is_deleted", False) \
            .order("date", desc=True) \
            .limit(limit) \
            .execute()

        if not result.data:
            return "No recent transactions found."

        lines = []
        for t in result.data:
            date = t["date"][:10]
            ttype = t["type"].capitalize()
            amount = f"₹{float(t['amount']):,.2f}"
            merchant = t.get("merchants", {})
            merchant = merchant.get("name", "") if merchant else ""
            category = t.get("categories", {})
            category = category.get("name", "") if category else ""
            note = t.get("note", "") or ""

            label = merchant or category or note or "Unknown"
            lines.append(f"  {date} | {ttype} | {amount} | {label}")

        return f"Recent {limit} transactions:\n" + "\n".join(lines)

    except Exception as e:
        return f"Could not fetch transactions: {e}"


def get_unsettled_debts() -> str:
    """Get all unsettled debts."""
    try:
        sb = _get_client()

        result = sb.table("debts") \
            .select("person_name, direction, transactions(amount, date)") \
            .is_("settled_at", "null") \
            .execute()

        if not result.data:
            return "No unsettled debts. You're all clear!"

        owe_me = []
        i_owe = []

        for d in result.data:
            person = d["person_name"]
            amount = float(d["transactions"]["amount"]
                           ) if d.get("transactions") else 0
            if d["direction"] == "lent":
                owe_me.append(f"  {person} owes you ₹{amount:,.2f}")
            else:
                i_owe.append(f"  You owe {person} ₹{amount:,.2f}")

        lines = []
        if owe_me:
            lines.append("People who owe you:\n" + "\n".join(owe_me))
        if i_owe:
            lines.append("You owe:\n" + "\n".join(i_owe))

        return "\n\n".join(lines)

    except Exception as e:
        return f"Could not fetch debts: {e}"


def get_top_merchants(days: int = 30, limit: int = 5) -> str:
    """Get top merchants by spending."""
    try:
        sb = _get_client()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        result = sb.table("transactions") \
            .select("amount, merchants(name)") \
            .eq("is_deleted", False) \
            .eq("type", "expense") \
            .gte("date", since) \
            .execute()

        if not result.data:
            return f"No merchant data for the last {days} days."

        merchants = {}
        for t in result.data:
            m = t.get("merchants", {})
            name = m.get("name", "Unknown") if m else "Unknown"
            merchants[name] = merchants.get(name, 0) + float(t["amount"])

        sorted_m = sorted(merchants.items(),
                          key=lambda x: x[1], reverse=True)[:limit]
        lines = [f"  {name}: ₹{amt:,.2f}" for name, amt in sorted_m]

        return f"Top {limit} merchants (last {days} days):\n" + "\n".join(lines)

    except Exception as e:
        return f"Could not fetch merchants: {e}"
