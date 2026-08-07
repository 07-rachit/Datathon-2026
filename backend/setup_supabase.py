"""Supabase Database Setup & Verification Tool for CrimeIntel Platform

Usage:
  1. Via Environment Variable:
     set DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres"
     python setup_supabase.py

  2. Via Command Line Argument:
     python setup_supabase.py --db-url "postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres"
"""

import sys
import os
import argparse

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_supabase(db_url: str = None):
    if db_url:
        os.environ["DATABASE_URL"] = db_url

    current_url = os.environ.get("DATABASE_URL", "")
    if not current_url or "sqlite" in current_url:
        print("[!] WARNING: DATABASE_URL is not set or points to SQLite.")
        print("    To seed data directly to Supabase, provide your Supabase Postgres connection URI.")
        print("    Example: python setup_supabase.py --db-url \"postgresql://postgres:pass@db.xxxx.supabase.co:5432/postgres\"\n")

    print("[*] Initializing CrimeIntel Database Pipeline...")
    print(f"--> Database Target: {os.environ.get('DATABASE_URL', 'default')}\n")

    # Import seed pipeline to execute schema creation & data population
    try:
        import seed
        print("\n[+] Seed Pipeline executed successfully!")
    except Exception as e:
        print(f"\n[-] Error during seed pipeline execution: {e}")
        sys.exit(1)

    # Verification Report
    print("\n--- Supabase Database Verification Summary ---")
    print("=" * 50)
    from app.database import SessionLocal
    from app import models

    db = SessionLocal()
    try:
        table_counts = {
            "Users": db.query(models.User).count(),
            "Cases": db.query(models.Case).count(),
            "Persons (Suspects/Accused/Victims)": db.query(models.Person).count(),
            "FIR Details": db.query(models.CaseFIRDetails).count(),
            "Tasks": db.query(models.CaseTask).count(),
            "Evidence Items": db.query(models.Evidence).count(),
            "Financial Transactions": db.query(models.FinancialTransaction).count(),
            "District Indicators": db.query(models.DistrictIndicator).count(),
            "Audit Logs": db.query(models.AuditLog).count(),
            "Case Categories (Master)": db.query(models.CaseCategoryMaster).count(),
            "Acts (Master)": db.query(models.Act).count(),
            "Sections (Master)": db.query(models.Section).count(),
        }

        for table, count in table_counts.items():
            print(f"  * {table:<36}: {count:>5} records")

        print("=" * 50)
        print("[+] Supabase Database Setup & Verification Completed Successfully!\n")
    except Exception as e:
        print(f"[-] Error during database verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed CrimeIntel Platform data to Supabase PostgreSQL")
    parser.add_argument("--db-url", type=str, help="Supabase PostgreSQL connection URI string")
    args = parser.parse_args()

    setup_supabase(db_url=args.db_url)
