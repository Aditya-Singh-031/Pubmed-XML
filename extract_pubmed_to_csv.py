#!/usr/bin/env python3
"""
Stream-parse PubMed XML and export selected fields to CSV using pandas.

Fields per row:
  - PMID
  - ArticleTitle
  - JournalTitle
  - PubDateYear, PubDateMonth, PubDateDay
  - FirstAuthorLastName, FirstAuthorForeName
  - DOI
  - Authors (semicolon-separated "ForeName LastName")
  - Abstract (concatenated text of all AbstractText nodes)

Usage:
  python extract_pubmed_to_csv.py --input pubmed25n1271.xml --output pubmed.csv
"""

import argparse
import sys
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

import pandas as pd


def get_text(elem: Optional[ET.Element]) -> str:
    return elem.text.strip() if (elem is not None and elem.text) else ""


def extract_pubdate(article_el: ET.Element) -> Dict[str, str]:
    # Prefer Journal/JournalIssue/PubDate; fall back if needed
    year = month = day = ""
    pub_date = article_el.find('.//Journal/JournalIssue/PubDate')
    if pub_date is not None:
        year = get_text(pub_date.find('Year'))
        month = get_text(pub_date.find('Month'))
        day = get_text(pub_date.find('Day'))
        # Some records use MedlineDate like "2001 Jan-Feb"
        if not year:
            medline_date = get_text(pub_date.find('MedlineDate'))
            if medline_date:
                year = medline_date.split()[0]
    return {"PubDateYear": year, "PubDateMonth": month, "PubDateDay": day}


def extract_authors(article_el: ET.Element) -> Dict[str, str]:
    authors: List[str] = []
    first_last = ""
    first_fore = ""
    for idx, author in enumerate(article_el.findall('.//AuthorList/Author')):
        last = get_text(author.find('LastName'))
        fore = get_text(author.find('ForeName'))
        if last or fore:
            full = f"{fore} {last}".strip()
            authors.append(full)
        if idx == 0:
            first_last = last
            first_fore = fore
    return {
        "FirstAuthorLastName": first_last,
        "FirstAuthorForeName": first_fore,
        "Authors": "; ".join(authors),
    }


def extract_doi(article_el: ET.Element) -> str:
    # Prefer ArticleIdList/ArticleId[@IdType='doi'], else ELocationID[@EIdType='doi']
    for aid in article_el.findall('.//ArticleIdList/ArticleId'):
        if aid.get('IdType') == 'doi':
            txt = get_text(aid)
            if txt:
                return txt
    for eloc in article_el.findall('.//ELocationID'):
        if eloc.get('EIdType') == 'doi':
            txt = get_text(eloc)
            if txt:
                return txt
    return ""


def extract_abstract(article_el: ET.Element) -> str:
    parts: List[str] = []
    for ab in article_el.findall('.//Abstract/AbstractText'):
        txt = get_text(ab)
        if txt:
            parts.append(txt)
    return " \n".join(parts)


def extract_row(pubmed_article: ET.Element) -> Dict[str, str]:
    pmid = get_text(pubmed_article.find('.//PMID'))
    article = pubmed_article.find('.//Article')
    journal_title = get_text(pubmed_article.find('.//Journal/Title'))
    title = get_text(pubmed_article.find('.//ArticleTitle'))

    pubdate = extract_pubdate(pubmed_article)
    authors = extract_authors(pubmed_article)
    doi = extract_doi(pubmed_article)
    abstract = extract_abstract(pubmed_article)

    row: Dict[str, str] = {
        "PMID": pmid,
        "ArticleTitle": title,
        "JournalTitle": journal_title,
        "PubDateYear": pubdate["PubDateYear"],
        "PubDateMonth": pubdate["PubDateMonth"],
        "PubDateDay": pubdate["PubDateDay"],
        "FirstAuthorLastName": authors["FirstAuthorLastName"],
        "FirstAuthorForeName": authors["FirstAuthorForeName"],
        "DOI": doi,
        "Authors": authors["Authors"],
        "Abstract": abstract,
    }
    return row


def write_csv_rows(rows: List[Dict[str, str]], output_path: str, write_header: bool) -> None:
    if not rows:
        return
    df = pd.DataFrame(rows)
    df.to_csv(output_path, mode='a', index=False, header=write_header)


def process_to_csv(input_path: str, output_path: str, chunk_size: int = 2000) -> None:
    # Prepare output: empty file and header will be written on first chunk
    open(output_path, 'w', encoding='utf-8').close()

    rows_buffer: List[Dict[str, str]] = []
    wrote_header = False

    for _, elem in ET.iterparse(input_path, events=("end",)):
        if elem.tag == 'PubmedArticle':
            row = extract_row(elem)
            rows_buffer.append(row)

            if len(rows_buffer) >= chunk_size:
                write_csv_rows(rows_buffer, output_path, write_header=not wrote_header)
                wrote_header = True
                rows_buffer.clear()

            elem.clear()

    # flush remaining
    write_csv_rows(rows_buffer, output_path, write_header=not wrote_header)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract PubMed XML fields to CSV using pandas"
    )
    parser.add_argument('--input', '-i', required=True, help='Path to input PubMed XML file')
    parser.add_argument('--output', '-o', required=True, help='Path to output CSV file')
    parser.add_argument('--chunk-size', type=int, default=2000, help='Number of rows per write batch')

    args = parser.parse_args()
    try:
        process_to_csv(args.input, args.output, chunk_size=args.chunk_size)
        print(f"CSV saved to: {args.output}")
    except (FileNotFoundError, ET.ParseError, OSError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


