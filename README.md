# PubMed XML Parser for Biological Sequence Detection

This Python script processes large PubMed XML files to identify articles containing biological sequences (DNA, RNA, or protein) and extracts them to a new XML file.

## Features

- **Memory-efficient processing**: Uses `xml.etree.ElementTree.iterparse()` to handle very large XML files (several GB) without loading the entire file into memory
- **Comprehensive sequence detection**: Identifies articles using both keyword matching and accession number pattern recognition
- **Robust pattern matching**: Detects GenBank, RefSeq, PDB, and UniProt accession numbers using regular expressions
- **Progress tracking**: Provides real-time feedback during processing
- **Well-formed output**: Generates properly formatted XML with complete article structures

## Usage

```bash
python parse_pubmed.py --input pubmed25n1271.xml --output papers_with_sequences.xml
```

### Command Line Arguments

- `--input`, `-i`: Path to input PubMed XML file (required)
- `--output`, `-o`: Path to output XML file for articles with sequences (required)

## Detection Logic

The script classifies articles as containing biological sequences if they meet any of the following criteria:

### Keyword Matching
- DNA sequence
- RNA sequence  
- protein sequence
- amino acid sequence
- nucleotide sequence
- sequencing
- GenBank
- FASTA
- UniProt
- PDB (Protein Data Bank)

### Accession Number Patterns
- **GenBank/RefSeq**: `[A-Z]{1,2}\d{5,8}` or `[A-Z]{2,4}_\d{6,}` (e.g., U12345, NM_001234)
- **Protein Data Bank**: `\d[A-Z0-9]{3}` (e.g., 1TUP, 6M0J)
- **UniProt/Swiss-Prot**: Comprehensive regex for UniProt IDs (e.g., P12345)

## Output

The script generates a new XML file containing:
- Complete, unmodified `<PubmedArticle>` elements for all articles classified as positive
- Proper XML structure with `<PubmedArticleSet>` root element
- Progress statistics including total articles processed and percentage with sequences

## Example Results

```
Processing complete!
Total articles processed: 30,000
Articles with sequences found: 7,763
Output saved to: papers_with_sequences.xml
Percentage of articles with sequences: 25.88%
```

## Requirements

- Python 3.6+
- Standard library modules only (no external dependencies)

## Performance

- Processes large files efficiently using iterative parsing
- Memory usage remains constant regardless of input file size
- Typical processing speed: ~10,000 articles per minute (varies by system)
