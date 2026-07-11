import pandas as pd
import os
import csv
import re
from pathlib import Path
from practicepreach.constants import BUNDESTAG_WAHLPERIODE

# Increase CSV field size limit to handle large manifesto texts
# Set to 50 MB (50 * 1024 * 1024 bytes) - reasonable limit for manifesto texts
MAX_CSV_FIELD_SIZE = 50 * 1024 * 1024  # 50 MB
csv.field_size_limit(MAX_CSV_FIELD_SIZE)


def chunk_text_by_sentences(text, chunk_size=1000, chunk_overlap=0):
    """
    Split text into chunks by sentences, never cutting a sentence.

    Args:
        text: The text to chunk
        chunk_size: Target size for each chunk in characters (default: 1000)
        chunk_overlap: Number of characters to overlap between chunks (default: 0)

    Returns:
        List of text chunks, each containing complete sentences
    """
    if not text or not text.strip():
        return ['']

    # Split text into sentences using regex
    # Matches sentence-ending punctuation (. ! ?) followed by:
    # - whitespace and uppercase letter (new sentence)
    # - double newline (paragraph break)
    # - end of string
    # Note: This may split on some abbreviations, but preserves sentence integrity
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])|(?<=[.!?])(?=\n\n)|(?<=[.!?])(?=\s*$)'
    sentences = re.split(sentence_pattern, text)

    # Clean up: remove empty strings and strip whitespace
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence)

        # If a single sentence is larger than chunk_size, include it anyway
        # (we never cut sentences)
        if current_size + sentence_size > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)

            # Handle overlap: include last few sentences if overlap > 0
            if chunk_overlap > 0 and len(chunk_text) > chunk_overlap:
                # Find sentences that fit in overlap
                overlap_sentences = []
                overlap_size = 0
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_size += len(s)
                    else:
                        break
                current_chunk = overlap_sentences
                current_size = sum(len(s) for s in current_chunk)
            else:
                current_chunk = []
                current_size = 0

        current_chunk.append(sentence)
        current_size += sentence_size + 1  # +1 for space between sentences

    # Add the last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks if chunks else [text]

def generate_manifesto_dataframe():
    """
    Generates a pandas DataFrame with columns: type, date, id, party, text
    - type: filled with 'manifesto' for all rows
    - date: exact start date of the wahlperiode that started in the year from filename (e.g., "2021-10-26")
    - id: party ID from filename before first underscore (e.g., "41113")
    - party: party name from parties_summary.csv based on ID
    - text: contains chunked content from .txt files in german_manifestos folder
           (text is split into chunks of ~1000 characters, never cutting sentences)
    """
    # Path to german_manifestos folder - handle both script and interactive execution
    try:
        # Try to use __file__ if available (when run as script)
        base_dir = Path(__file__).parent.parent
    except NameError:
        # Fall back to current working directory (when run interactively)
        base_dir = Path.cwd()

    manifestos_dir = base_dir / 'german_manifestos'

    # Load parties_summary.csv to map IDs to party names
    parties_summary_path = manifestos_dir / 'parties_summary.csv'
    parties_df = pd.read_csv(parties_summary_path)
    # Create a dictionary mapping party ID to party name
    party_id_to_name = dict(zip(parties_df['party'].astype(str), parties_df['name']))

    # Get all .txt files
    txt_files = sorted(manifestos_dir.glob('*.txt'))

    # Initialize lists for DataFrame
    data = {
        'type': [],
        'date': [],
        'id': [],
        'party': [],
        'text': []
    }

    # Read each .txt file and populate the DataFrame
    for txt_file in txt_files:
        with open(txt_file, 'r', encoding='utf-8') as f:
            text_content = f.read()

        # Extract ID from filename (e.g., "41113_202109_text.txt" -> "41113")
        filename = txt_file.stem  # Gets filename without extension
        filename_parts = filename.split('_')
        party_id = filename_parts[0]  # Get the part before first underscore

        # Extract year from filename (e.g., "41113_202109_text.txt" -> "2021")
        # Get the part after first underscore and take first 4 digits
        year_str = filename_parts[1][:4] if len(filename_parts) > 1 else ''

        # Find the wahlperiode that started in this year and get its start date
        wahlperiode_start_date = None
        if year_str:
            year_int = int(year_str)
            # Find wahlperiode where start date year matches
            for wahlperiode_num, (start_date, end_date) in BUNDESTAG_WAHLPERIODE.items():
                if start_date.year == year_int:
                    wahlperiode_start_date = start_date
                    break

        # Convert date to string format, or use empty string if not found
        date_str = wahlperiode_start_date.strftime('%d.%m.%Y') if wahlperiode_start_date else ''

        # Get party name from the mapping
        party_name = party_id_to_name.get(party_id, '')

        # Chunk the text into smaller pieces, never cutting sentences
        text_chunks = chunk_text_by_sentences(text_content, chunk_size=1000, chunk_overlap=0)

        # Add a row for each chunk with the same metadata
        for chunk in text_chunks:
            data['type'].append('manifesto')
            data['date'].append(date_str)
            data['id'].append(party_id)
            data['party'].append(party_name)
            data['text'].append(chunk)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Write CSV to data folder (same folder as speeches-wahlperiode CSVs)
    data_dir = base_dir / 'data'
    csv_path = data_dir / 'manifestos.csv'
    # Use quoting to handle large text fields properly
    df.to_csv(csv_path, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
    print(f"CSV written to: {csv_path}")

    return df


def read_manifesto_csv(csv_path=None):
    """
    Read the manifestos CSV file with increased field size limit to handle large text fields.

    Args:
        csv_path: Path to the manifestos.csv file. If None, uses default location in data folder.

    Returns:
        pandas DataFrame with manifesto data
    """
    # Increase CSV field size limit to handle large manifesto texts
    # Use the same limit as when writing
    csv.field_size_limit(MAX_CSV_FIELD_SIZE)

    if csv_path is None:
        try:
            base_dir = Path(__file__).parent.parent
        except NameError:
            base_dir = Path.cwd()
        csv_path = base_dir / 'data' / 'manifestos.csv'

    df = pd.read_csv(csv_path, encoding='utf-8')
    return df


if __name__ == '__main__':
    df = generate_manifesto_dataframe()
    print(f"DataFrame created with {len(df)} rows")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())
    print(f"\nDataFrame shape: {df.shape}")
