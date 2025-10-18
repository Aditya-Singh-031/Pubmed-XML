#!/usr/bin/env python3
"""
Converts the PubMed articles CSV file to a SQLite database.

Usage:
    python csv_to_sqlite.py
"""

import pandas as pd
import sqlite3
import sys

# --- Configuration ---
CSV_FILE = 'pubmed_articles.csv'
DB_FILE = 'pubmed_articles.db'
TABLE_NAME = 'articles'
# ---------------------

def convert_csv_to_sqlite(csv_path: str, db_path: str, table: str) -> None:
    """
    Reads a CSV file and saves its contents to a table in a SQLite database.
    
    If the table already exists, it will be replaced.
    """
    try:
        # Read the CSV file into a pandas DataFrame
        print(f"Reading {csv_path}...")
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: The file '{csv_path}' was not found.")
        print("Please run the 'pubmed_xml_to_csv.py' script first.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        sys.exit(1)

    try:
        # Create a connection to the SQLite database
        # The .db file will be created if it doesn't exist
        print(f"Connecting to database {db_path}...")
        with sqlite3.connect(db_path) as con:
            
            # Write the DataFrame to the SQLite table
            print(f"Writing {len(df)} rows to table '{table}'...")
            df.to_sql(
                table,
                con,
                if_exists='replace',  # 'replace' = drop table if it exists
                index=False           # Don't save the pandas index as a column
            )
            
        print("Done. Conversion complete.")
        
    except Exception as e:
        print(f"An error occurred during the SQLite conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    convert_csv_to_sqlite(CSV_FILE, DB_FILE, TABLE_NAME)