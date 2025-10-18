#!/usr/bin/env python3
"""
Memory-efficient script to discover all unique XML tag names from a large PubMed XML file.

This script uses streaming XML parsing to avoid loading the entire file into memory.
It finds all unique tag names and writes them to an output file in alphabetical order.

Usage:
    python discover_tags.py --input pubmed25n1271.xml --output all_xml_tags.txt
"""

import argparse
import sys
import xml.etree.ElementTree as ET


def discover_xml_tags(input_file: str, output_file: str) -> None:
    """
    Discover all unique XML tag names from the input file and write them to output.
    
    Args:
        input_file: Path to the input XML file
        output_file: Path to the output text file
    """
    unique_tags = set()
    element_count = 0
    
    print(f"Starting to parse: {input_file}")
    print("This may take a while for large files...")
    
    try:
        for event, elem in ET.iterparse(input_file, events=('start',)):
            # Add the tag name to our set (automatically handles uniqueness)
            unique_tags.add(elem.tag)
            element_count += 1
            
            # Progress indicator every 1 million elements
            if element_count % 1_000_000 == 0:
                print(f"Processed {element_count:,} elements...")
            
            # Clear the element to free memory immediately
            elem.clear()
    
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"File error: {e}")
        sys.exit(1)
    
    print(f"Parsing complete! Found {len(unique_tags)} unique tags from {element_count:,} elements.")
    
    # Sort the tags alphabetically
    sorted_tags = sorted(unique_tags)
    
    # Write to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for tag in sorted_tags:
                f.write(f"{tag}\n")
        print(f"Tags written to: {output_file}")
    except OSError as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


def main() -> None:
    """Main function to parse command line arguments and discover XML tags."""
    parser = argparse.ArgumentParser(
        description='Discover all unique XML tag names from a PubMed XML file'
    )
    parser.add_argument(
        '--input', '-i', 
        required=True, 
        help='Path to input XML file (e.g., pubmed25n1271.xml)'
    )
    parser.add_argument(
        '--output', '-o', 
        required=True, 
        help='Path to output text file (e.g., all_xml_tags.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        discover_xml_tags(args.input, args.output)
        print("Done!")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
