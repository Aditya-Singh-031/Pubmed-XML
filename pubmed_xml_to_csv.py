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

Usage:
  python pubmed_xml_to_csv.py --input pubmed25n1271.xml --output pubmed_articles.csv
"""

import argparse
import sys
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

import pandas as pd


def get_text(elem: Optional[ET.Element]) -> str:
    if elem is None or elem.text is None:
        return ''
    return elem.text.strip()


def extract_pub_date(article_elem: ET.Element) -> Dict[str, str]:
    # Prefer Article > Journal > JournalIssue > PubDate
    year = month = day = ''
    pub_date = article_elem.find('.//Journal/JournalIssue/PubDate')
    if pub_date is not None:
        year = get_text(pub_date.find('Year'))
        month = get_text(pub_date.find('Month'))
        day = get_text(pub_date.find('Day'))
    return {'PubYear': year, 'PubMonth': month, 'PubDay': day}


def extract_doi(article_elem: ET.Element) -> str:
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
    authors: List[str] = []
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
    return {
        'FirstAuthorLastName': first_last,
        'FirstAuthorForeName': first_fore,
        'Authors': '; '.join(authors),
    }


def extract_abstract(article_elem: ET.Element) -> str:
    # Concatenate all AbstractText parts preserving order
    parts: List[str] = []
    for at in article_elem.findall('.//Abstract/AbstractText'):
        text = get_text(at)
        if text:
            parts.append(text)
    return ' '.join(parts)


def extract_row(pubmed_article: ET.Element) -> Dict[str, str]:
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
    }
    return row


def stream_to_csv(input_file: str, output_file: str, chunk_size: int = 5000) -> None:
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


