#!/usr/bin/env python3
"""
Script to extract author emails and affiliations from existing database data
and populate the AuthorEmails and AuthorAffiliations columns.
"""

import sqlite3
import re
from typing import List

def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text."""
    if not text:
        return []
    
    # Pattern to match email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return emails

def extract_affiliation_without_email(affiliation_text: str) -> str:
    """Extract affiliation text without email addresses."""
    if not affiliation_text:
        return ""
    
    # Remove "Electronic address:" and email patterns
    cleaned = re.sub(r'Electronic address:\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\.?', '', affiliation_text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def update_database_with_extracted_data():
    """Update the database with extracted author emails and affiliations."""
    # Connect to database
    conn = sqlite3.connect('pubmed_articles.db')
    cursor = conn.cursor()
    
    # Get all articles
    cursor.execute("SELECT PMID, Authors, Affiliations, ContactEmail FROM articles")
    articles = cursor.fetchall()
    
    print(f"Processing {len(articles)} articles...")
    
    updated_count = 0
    
    for pmid, authors, affiliations, contact_email in articles:
        # Extract emails from affiliations and contact email
        all_emails = []
        
        # Extract from affiliations
        if affiliations:
            emails_from_affiliations = extract_emails_from_text(affiliations)
            all_emails.extend(emails_from_affiliations)
        
        # Extract from contact email
        if contact_email:
            emails_from_contact = extract_emails_from_text(contact_email)
            all_emails.extend(emails_from_contact)
        
        # Remove duplicates and join
        unique_emails = list(set(all_emails))
        emails_str = '; '.join(unique_emails) if unique_emails else ''
        
        # Extract affiliations without emails
        clean_affiliations = extract_affiliation_without_email(affiliations) if affiliations else ''
        
        # Update database
        cursor.execute("""
            UPDATE articles 
            SET AuthorEmails = ?, AuthorAffiliations = ?
            WHERE PMID = ?
        """, (emails_str, clean_affiliations, pmid))
        
        updated_count += 1
        
        if updated_count % 1000 == 0:
            print(f"Updated {updated_count} articles...")
            conn.commit()  # Commit periodically
    
    # Final commit
    conn.commit()
    conn.close()
    
    print(f"Successfully updated {updated_count} articles with author data")

if __name__ == "__main__":
    update_database_with_extracted_data()
