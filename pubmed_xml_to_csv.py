#!/usr/bin/env python3
"""
Stream-parse PubMed XML and export selected fields to CSV using pandas.

Fields per row:
  - PMID
  - ArticleTitle
  - JournalTitle
  - PubYear
  - PubMonth
  - PubDay
  - FirstAuthorLastName
  - FirstAuthorForeName
  - DOI
  - Authors (semicolon-separated)
  - Abstract
  - Keywords (semicolon-separated)
  - Affiliations (semicolon-separated)
  - ContactEmail
  - DateReceived
  - DateAccepted
  - MedlineStatus
  - MedlineOwner

Usage:
  python pubmed_xml_to_csv.py --input pubmed25n1271.xml --output pubmed_articles.csv
"""

import argparse
import re
import sys
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

import pandas as pd


def get_text(elem: Optional[ET.Element]) -> str:
    """Extract text content from XML element, returning empty string if None."""
    if elem is None or elem.text is None:
        return ''
    return elem.text.strip()


def extract_pub_date(article_elem: ET.Element) -> Dict[str, str]:
    """Extract publication date from Journal/JournalIssue/PubDate."""
    # Prefer Article > Journal > JournalIssue > PubDate
    year = month = day = ''
    pub_date = article_elem.find('.//Journal/JournalIssue/PubDate')
    if pub_date is not None:
        year = get_text(pub_date.find('Year'))
        month = get_text(pub_date.find('Month'))
        day = get_text(pub_date.find('Day'))
    return {'PubYear': year, 'PubMonth': month, 'PubDay': day}


def extract_doi(article_elem: ET.Element) -> str:
    """Extract DOI from ELocationID or ArticleId elements."""
    # DOI can be in ELocationID with EIdType="doi" or in ArticleIdList/ArticleId IdType="doi"
    eloc = article_elem.findall('.//ELocationID')
    for el in eloc:
        if el.get('EIdType', '').lower() == 'doi':
            text = get_text(el)
            if text:
                return text
    # PubmedData location
    for art_id in article_elem.findall('.//ArticleId'):
        if art_id.get('IdType', '').lower() == 'doi':
            text = get_text(art_id)
            if text:
                return text
    return ''


def extract_authors(article_elem: ET.Element) -> Dict[str, str]:
    """Extract author information including names, affiliations, and contact email."""
    authors: List[str] = []
    affiliations: List[str] = []
    first_last = ''
    first_fore = ''

    for idx, author in enumerate(article_elem.findall('.//AuthorList/Author')):
        last = get_text(author.find('LastName'))
        fore = get_text(author.find('ForeName'))
        if last or fore:
            full = f"{fore} {last}".strip()
            authors.append(full)
            if idx == 0:
                first_last = last
                first_fore = fore

        # Extract affiliations for this author
        for affiliation_info in author.findall('.//AffiliationInfo/Affiliation'):
            affiliation_text = get_text(affiliation_info)
            if affiliation_text:
                affiliations.append(affiliation_text)

    # Join all affiliations and search for email
    all_affiliations = '; '.join(affiliations)
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', all_affiliations) if all_affiliations else None

    return {
        'FirstAuthorLastName': first_last,
        'FirstAuthorForeName': first_fore,
        'Authors': '; '.join(authors),
        'Affiliations': all_affiliations,
        'ContactEmail': email_match.group(0) if email_match else ''
    }


def extract_abstract(article_elem: ET.Element) -> str:
    """Extract and concatenate all AbstractText parts preserving order."""
    # Concatenate all AbstractText parts preserving order
    parts: List[str] = []
    for at in article_elem.findall('.//Abstract/AbstractText'):
        text = get_text(at)
        if text:
            parts.append(text)
    return ' '.join(parts)


def extract_keywords(pubmed_article: ET.Element) -> str:
    """Extract keywords from KeywordList/Keyword tags."""
    keywords: List[str] = []
    for keyword in pubmed_article.findall('.//KeywordList/Keyword'):
        text = get_text(keyword)
        if text:
            keywords.append(text)
    return '; '.join(keywords)


def extract_history_dates(pubmed_article: ET.Element) -> Dict[str, str]:
    """Extract received and accepted dates from PubmedData/History."""
    date_received = ''
    date_accepted = ''

    for pub_date in pubmed_article.findall('.//PubmedData/History/PubMedPubDate'):
        pub_status = pub_date.get('PubStatus', '').lower()
        year = get_text(pub_date.find('Year'))
        month = get_text(pub_date.find('Month'))
        day = get_text(pub_date.find('Day'))

        if year and month and day:
            formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            if pub_status == 'received':
                date_received = formatted_date
            elif pub_status == 'accepted':
                date_accepted = formatted_date

    return {
        'DateReceived': date_received,
        'DateAccepted': date_accepted
    }


def extract_medline_info(pubmed_article: ET.Element) -> Dict[str, str]:
    """Extract Status and Owner attributes from MedlineCitation."""
    medline_citation = pubmed_article.find('.//MedlineCitation')
    if medline_citation is not None:
        status = medline_citation.get('Status', '')
        owner = medline_citation.get('Owner', '')
        return {
            'MedlineStatus': status,
            'MedlineOwner': owner
        }
    return {
        'MedlineStatus': '',
        'MedlineOwner': ''
    }


def extract_row(pubmed_article: ET.Element) -> Dict[str, str]:
    """Extract all fields from a PubmedArticle element into a dictionary."""
    pmid = get_text(pubmed_article.find('.//PMID'))
    article = pubmed_article.find('.//Article')
    journal_title = ''
    title = ''
    if article is not None:
        title = get_text(article.find('ArticleTitle'))
        journal_title = get_text(article.find('.//Journal/Title'))
    date = extract_pub_date(pubmed_article)
    author_info = extract_authors(pubmed_article)
    doi = extract_doi(pubmed_article)
    abstract = extract_abstract(pubmed_article)
    keywords = extract_keywords(pubmed_article)
    history_dates = extract_history_dates(pubmed_article)
    medline_info = extract_medline_info(pubmed_article)

    row = {
        'PMID': pmid,
        'ArticleTitle': title,
        'JournalTitle': journal_title,
        **date,
        'FirstAuthorLastName': author_info['FirstAuthorLastName'],
        'FirstAuthorForeName': author_info['FirstAuthorForeName'],
        'DOI': doi,
        'Authors': author_info['Authors'],
        'Abstract': abstract,
        'Keywords': keywords,
        'Affiliations': author_info['Affiliations'],
        'ContactEmail': author_info['ContactEmail'],
        **history_dates,
        **medline_info,
    }
    return row


def stream_to_csv(input_file: str, output_file: str, chunk_size: int = 5000) -> None:
    """Stream parse XML file and write to CSV in chunks."""
    buffer: List[Dict[str, str]] = []
    written_header = False

    # Initialize CSV by ensuring file is created/overwritten
    with open(output_file, 'w', encoding='utf-8') as _:
        pass

    for _, elem in ET.iterparse(input_file, events=('end',)):
        if elem.tag == 'PubmedArticle':
            buffer.append(extract_row(elem))

            if len(buffer) >= chunk_size:
                df = pd.DataFrame(buffer)
                df.to_csv(
                    output_file,
                    index=False,
                    mode='a',
                    header=not written_header,
                    encoding='utf-8'
                )
                written_header = True
                buffer.clear()

            elem.clear()

    # Flush any remaining rows
    if buffer:
        df = pd.DataFrame(buffer)
        df.to_csv(
            output_file,
            index=False,
            mode='a',
            header=not written_header,
            encoding='utf-8'
        )


def main() -> None:
    """Main function to parse command line arguments and process XML file."""
    parser = argparse.ArgumentParser(
        description='Parse PubMed XML into CSV with selected fields'
    )
    parser.add_argument('--input', '-i', required=True, help='Path to PubMed XML file')
    parser.add_argument('--output', '-o', required=True, help='Path to output CSV file')
    parser.add_argument('--chunk-size', type=int, default=5000, help='Rows per write batch')
    args = parser.parse_args()

    try:
        print(f"Processing: {args.input}")
        stream_to_csv(args.input, args.output, chunk_size=args.chunk_size)
        print(f"Done. CSV written to: {args.output}")
    except (ET.ParseError, OSError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
