#!/usr/bin/env python3
"""
PubMed XML Parser for Biological Sequence Detection

This script processes large PubMed XML files to identify articles containing
biological sequences (DNA, RNA, or protein) and extracts them to a new XML file.

Usage:
    python parse_pubmed.py --input pubmed25n1271.xml --output papers_with_sequences.xml
"""

import xml.etree.ElementTree as ET
import re
import argparse
import sys
from typing import Tuple


def contains_sequence(article_text: str) -> bool:
    """
    Determine if an article contains evidence of biological sequences.

    Args:
        article_text: Combined text from ArticleTitle, AbstractText, and OtherAbstract

    Returns:
        bool: True if sequence evidence is found, False otherwise
    """
    # Convert to lowercase for case-insensitive matching
    text_lower = article_text.lower()

    # A. Keyword Matching
    keywords = [
        'dna sequence',
        'rna sequence',
        'protein sequence',
        'amino acid sequence',
        'nucleotide sequence',
        'sequencing',
        'genbank',
        'fasta',
        'uniprot',
        'pdb (protein data bank)',
        'protein data bank'
    ]

    # Check for keyword matches
    for keyword in keywords:
        if keyword in text_lower:
            return True

    # B. Accession Number Pattern Matching using Regular Expressions

    # GenBank/RefSeq patterns: [A-Z]{1,2}\d{5,8} or [A-Z]{2,4}_\d{6,}
    genbank_pattern = r'\b[A-Z]{1,2}\d{5,8}\b|\b[A-Z]{2,4}_\d{6,}\b'
    if re.search(genbank_pattern, article_text):
        return True

    # Protein Data Bank (PDB) pattern: \b\d[A-Z0-9]{3}\b
    pdb_pattern = r'\b\d[A-Z0-9]{3}\b'
    if re.search(pdb_pattern, article_text):
        return True

    # UniProt/Swiss-Prot patterns (split into two to keep lines short)
    uniprot_pattern_primary = r'\b[OPQ][0-9][A-Z0-9]{3}[0-9]\b'
    if re.search(uniprot_pattern_primary, article_text):
        return True
    uniprot_pattern_secondary = r'\b[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}\b'
    if re.search(uniprot_pattern_secondary, article_text):
        return True

    return False


def extract_article_text(article_element: ET.Element) -> str:
    """
    Extract and concatenate text from relevant XML tags within a PubmedArticle.

    Args:
        article_element: XML element representing a PubmedArticle

    Returns:
        str: Combined text from ArticleTitle, AbstractText, and OtherAbstract
    """
    text_parts = []

    # Extract ArticleTitle
    title_elem = article_element.find('.//ArticleTitle')
    if title_elem is not None and title_elem.text:
        text_parts.append(title_elem.text)

    # Extract AbstractText (can be multiple)
    abstract_texts = article_element.findall('.//AbstractText')
    for abstract_text in abstract_texts:
        if abstract_text.text:
            text_parts.append(abstract_text.text)

    # Extract OtherAbstract (can be multiple)
    other_abstracts = article_element.findall('.//OtherAbstract')
    for other_abstract in other_abstracts:
        if other_abstract.text:
            text_parts.append(other_abstract.text)

    return ' '.join(text_parts)


def process_pubmed_xml(input_file: str, output_file: str) -> Tuple[int, int]:
    """
    Process the PubMed XML file and extract articles containing biological sequences.

    Args:
        input_file: Path to input XML file
        output_file: Path to output XML file

    Returns:
        Tuple[int, int]: (total_articles_processed, articles_with_sequences)
    """
    articles_processed = 0
    articles_with_sequences = 0

    print(f"Processing file: {input_file}...")
    print("This may take several minutes for large files...")

    # Open output file and write root element
    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write('<?xml version="1.0" encoding="utf-8"?>\n')
        out_file.write('<PubmedArticleSet>\n')

        # Use iterparse for memory-efficient processing
        for _, elem in ET.iterparse(input_file, events=('end',)):
            if elem.tag == 'PubmedArticle':
                articles_processed += 1

                # Extract text content
                article_text = extract_article_text(elem)

                # Check if article contains sequences
                if contains_sequence(article_text):
                    articles_with_sequences += 1

                    # Write the complete XML element to output
                    xml_string = ET.tostring(elem, encoding='unicode')
                    out_file.write('  ' + xml_string + '\n')

                    if articles_with_sequences % 100 == 0:
                        print(f"Found {articles_with_sequences} articles with sequences so far...")

                # Clear element from memory to maintain low memory footprint
                elem.clear()

                # Progress indicator
                if articles_processed % 10000 == 0:
                    print(f"Processed {articles_processed} articles...")

        # Close root element
        out_file.write('</PubmedArticleSet>\n')

    return articles_processed, articles_with_sequences


def main():
    """Main function to handle command line arguments and execute processing."""
    parser = argparse.ArgumentParser(
        description='Parse PubMed XML file and extract articles containing biological sequences',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_pubmed.py --input pubmed25n1271.xml --output papers_with_sequences.xml
  python parse_pubmed.py -i data.xml -o output.xml
        """
    )

    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to input PubMed XML file'
    )

    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Path to output XML file for articles with sequences'
    )

    args = parser.parse_args()

    try:
        # Process the XML file
        total_articles, articles_with_sequences = process_pubmed_xml(args.input, args.output)

        # Print results
        print("\nProcessing complete!")
        print(f"Total articles processed: {total_articles:,}")
        print(f"Articles with sequences found: {articles_with_sequences:,}")
        print(f"Output saved to: {args.output}")

        if articles_with_sequences > 0:
            percentage = (articles_with_sequences / total_articles) * 100
            print(f"Percentage of articles with sequences: {percentage:.2f}%")

    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Invalid XML format in input file: {e}")
        sys.exit(1)
    except (OSError, KeyboardInterrupt) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
