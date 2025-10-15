#!/usr/bin/env python3
"""
Export selected fields from a large PubMed XML file to CSV.

Fields per row:
- PMID
- ArticleTitle
- Journal Title
- Publication Date (Year, Month, Day)
- First Author's Name (LastName, ForeName)
- DOI
- All Authors (as a semicolon-separated string "LastName|ForeName" per author)
- Abstract (concatenated AbstractText)

Usage:
  python export_pubmed_to_csv.py --input pubmed25n1271.xml --output pubmed_articles.csv
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import pandas as pd


def get_text(elem: Optional[ET.Element]) -> str:
    return elem.text.strip() if elem is not None and elem.text else ""


def extract_publication_date(article_elem: ET.Element) -> Dict[str, str]:
    # Prefer Article/Journal/JournalIssue/PubDate if available
    pub_date = article_elem.find('.//Article/Journal/JournalIssue/PubDate')
    year = month = day = ""
    if pub_date is not None:
        year = get_text(pub_date.find('Year'))
        month = get_text(pub_date.find('Month'))
        day = get_text(pub_date.find('Day'))
        # Sometimes only MedlineDate exists; keep columns blank if granular parts missing
    return {"Year": year, "Month": month, "Day": day}


def extract_authors(article_elem: ET.Element) -> Dict[str, str]:
    # Collect all authors under Article/AuthorList/Author
    authors = []
    first_last = ""
    first_fore = ""
    for author in article_elem.findall('.//Article/AuthorList/Author'):
        last = get_text(author.find('LastName'))
        fore = get_text(author.find('ForeName'))
        if last or fore:
            authors.append(f"{last}|{fore}")
        if not first_last and (last or fore):
            first_last = last
            first_fore = fore
    return {
        "FirstAuthorLastName": first_last,
        "FirstAuthorForeName": first_fore,
        "AllAuthors": "; ".join(authors),
    }


def extract_doi(article_elem: ET.Element) -> str:
    # DOI can appear as ELocationID with EIdType="doi" or in ArticleIdList
    doi_elem = article_elem.find('.//Article/ELocationID[@EIdType="doi"]')
    if doi_elem is not None and doi_elem.text:
        return doi_elem.text.strip()
    for aid in article_elem.findall('.//PubmedData/ArticleIdList/ArticleId'):
        if aid.get('IdType') == 'doi' and aid.text:
            return aid.text.strip()
    return ""


def extract_abstract(article_elem: ET.Element) -> str:
    parts: List[str] = []
    for a in article_elem.findall('.//Article/Abstract/AbstractText'):
        # AbstractText may have mixed content; text captures leading text. Tail ignored here.
        if a.text:
            parts.append(a.text.strip())
    return "\n".join(parts)


def extract_row(pubmed_article: ET.Element) -> Dict[str, str]:
    pmid = get_text(pubmed_article.find('.//MedlineCitation/PMID'))
    article_title = get_text(pubmed_article.find('.//Article/ArticleTitle'))
    journal_title = get_text(pubmed_article.find('.//Article/Journal/Title'))

    date = extract_publication_date(pubmed_article)
    authors = extract_authors(pubmed_article)
    doi = extract_doi(pubmed_article)
    abstract = extract_abstract(pubmed_article)

    row = {
        "PMID": pmid,
        "ArticleTitle": article_title,
        "JournalTitle": journal_title,
        "Year": date["Year"],
        "Month": date["Month"],
        "Day": date["Day"],
        "FirstAuthorLastName": authors["FirstAuthorLastName"],
        "FirstAuthorForeName": authors["FirstAuthorForeName"],
        "DOI": doi,
        "AllAuthors": authors["AllAuthors"],
        "Abstract": abstract,
    }
    return row


def export_pubmed_to_csv(input_file: str, output_file: str, batch_size: int = 5000) -> None:
    print(f"Processing file: {input_file} ...")
    print("Streaming and batching into CSV with pandas ...")

    columns = [
        "PMID",
        "ArticleTitle",
        "JournalTitle",
        "Year",
        "Month",
        "Day",
        "FirstAuthorLastName",
        "FirstAuthorForeName",
        "DOI",
        "AllAuthors",
        "Abstract",
    ]

    # Initialize CSV with header
    wrote_header = False
    buffer: List[Dict[str, str]] = []

    with pd.ExcelWriter if False else open(output_file, 'w', encoding='utf-8') as f:  # placeholder to keep lints happy
        pass

    # Open in append mode and write header using pandas on first batch
    processed = 0
    matched = 0

    for _, elem in ET.iterparse(input_file, events=('end',)):
        if elem.tag == 'PubmedArticle':
            processed += 1
            row = extract_row(elem)
            buffer.append(row)

            if len(buffer) >= batch_size:
                df = pd.DataFrame(buffer, columns=columns)
                df.to_csv(output_file, mode='a', header=not wrote_header, index=False)
                wrote_header = True
                buffer.clear()

            elem.clear()

            if processed % 10000 == 0:
                print(f"Processed {processed} articles...")

    # Flush remaining
    if buffer:
        df = pd.DataFrame(buffer, columns=columns)
        df.to_csv(output_file, mode='a', header=not wrote_header, index=False)

    print(f"Done. Wrote CSV to: {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Export selected fields from PubMed XML to CSV using streaming parse.',
    )
    parser.add_argument('--input', '-i', required=True, help='Path to input PubMed XML file')
    parser.add_argument('--output', '-o', required=True, help='Path to output CSV file')
    parser.add_argument('--batch-size', '-b', type=int, default=5000, help='Rows per write batch')
    args = parser.parse_args()

    try:
        export_pubmed_to_csv(args.input, args.output, args.batch_size)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Invalid XML format in input file: {e}")
        sys.exit(1)
    except (OSError, KeyboardInterrupt) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


