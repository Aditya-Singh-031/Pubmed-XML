#!/usr/bin/env python3
"""
Script to extract author emails and affiliations from PubMed XML data
and populate the AuthorEmails and AuthorAffiliations columns in the database.
"""

import xml.etree.ElementTree as ET
import sqlite3
import re
from typing import List, Tuple, Dict

def extract_emails_from_affiliation(affiliation_text: str) -> List[str]:
    """Extract email addresses from affiliation text."""
    if not affiliation_text:
        return []
    
    # Pattern to match email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, affiliation_text)
    return emails

def extract_affiliation_without_email(affiliation_text: str) -> str:
    """Extract affiliation text without email addresses."""
    if not affiliation_text:
        return ""
    
    # Remove "Electronic address:" and email patterns
    cleaned = re.sub(r'Electronic address:\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\.?', '', affiliation_text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def parse_xml_article(article_element) -> Tuple[List[str], List[str], List[str]]:
    """Parse a single article to extract author names, emails, and affiliations."""
    author_names = []
    author_emails = []
    author_affiliations = []
    
    # Find AuthorList
    author_list = article_element.find('.//AuthorList')
    if author_list is None:
        return author_names, author_emails, author_affiliations
    
    # Process each author
    for author in author_list.findall('Author'):
        # Extract author name
        last_name = author.find('LastName')
        fore_name = author.find('ForeName')
        
        if last_name is not None and fore_name is not None:
            full_name = f"{fore_name.text} {last_name.text}"
            author_names.append(full_name)
        elif author.find('CollectiveName') is not None:
            author_names.append(author.find('CollectiveName').text)
        else:
            author_names.append("Unknown")
        
        # Extract affiliation and email
        affiliation_info = author.find('AffiliationInfo')
        if affiliation_info is not None:
            affiliation = affiliation_info.find('Affiliation')
            if affiliation is not None and affiliation.text:
                affiliation_text = affiliation.text
                
                # Extract emails from affiliation
                emails = extract_emails_from_affiliation(affiliation_text)
                author_emails.append('; '.join(emails) if emails else '')
                
                # Extract affiliation without email
                clean_affiliation = extract_affiliation_without_email(affiliation_text)
                author_affiliations.append(clean_affiliation)
            else:
                author_emails.append('')
                author_affiliations.append('')
        else:
            author_emails.append('')
            author_affiliations.append('')
    
    return author_names, author_emails, author_affiliations

def update_database_with_author_data():
    """Update the database with extracted author emails and affiliations."""
    # Connect to database
    conn = sqlite3.connect('pubmed_articles.db')
    cursor = conn.cursor()
    
    # Get all PMIDs from database
    cursor.execute("SELECT PMID FROM articles")
    pmids = [row[0] for row in cursor.fetchall()]
    
    print(f"Found {len(pmids)} articles in database")
    
    # Parse XML file
    print("Parsing XML file...")
    tree = ET.parse('pubmed25n1271.xml')
    root = tree.getroot()
    
    # Find all articles
    articles = root.findall('.//PubmedArticle')
    print(f"Found {len(articles)} articles in XML")
    
    # Create mapping of PMID to article data
    pmid_to_article = {}
    for article in articles:
        pmid_elem = article.find('.//PMID')
        if pmid_elem is not None:
            pmid = int(pmid_elem.text)
            pmid_to_article[pmid] = article
    
    print(f"Created mapping for {len(pmid_to_article)} articles")
    
    # Process each article in database
    updated_count = 0
    for pmid in pmids:
        if pmid in pmid_to_article:
            article_element = pmid_to_article[pmid]
            author_names, author_emails, author_affiliations = parse_xml_article(article_element)
            
            # Join lists with semicolons
            emails_str = '; '.join(author_emails) if author_emails else ''
            affiliations_str = '; '.join(author_affiliations) if author_affiliations else ''
            
            # Update database
            cursor.execute("""
                UPDATE articles 
                SET AuthorEmails = ?, AuthorAffiliations = ?
                WHERE PMID = ?
            """, (emails_str, affiliations_str, pmid))
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"Updated {updated_count} articles...")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"Successfully updated {updated_count} articles with author data")

if __name__ == "__main__":
    update_database_with_author_data()
