# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---
# pyling: skip-file

"""
Download German party manifestos from Manifesto Project API
"""

# %%
import io
import os
import json
from pathlib import Path
from typing import List, Dict

import requests

import pandas as pd

# %%
# Configuration
API_KEY = os.environ.get("MANIFESTO_API_KEY")
START_DATE_ELECTION = os.environ.get("MANIFESTO_START_DATE")
BASE_URL = "https://manifesto-project.wzb.eu/api/v1"

# %%
def get_latest_versions():
    """Get the latest dataset and corpus versions"""
    # Get latest core dataset version
    response = requests.get(f"{BASE_URL}/list_core_versions",
                            params={"api_key": API_KEY})
    response.raise_for_status()
    core_versions = response.json()

    assert core_versions is not None
    latest_core = core_versions['datasets'][-1]['id']

    # Get latest metadata version
    response = requests.get(f"{BASE_URL}/list_metadata_versions",
                            params={"api_key": API_KEY})
    response.raise_for_status()
    metadata_versions = response.json()

    assert metadata_versions is not None
    latest_metadata = metadata_versions['versions'][-1]

    return latest_core, latest_metadata


# %%
def get_core_dataset(version: str) -> pd.DataFrame:
    """Download the core dataset"""
    print(f"Downloading core dataset version: {version}")

    # Download CSV because type conversion in panda is automatic. Not in json.
    response = requests.get(f"{BASE_URL}/get_core",
                            params={"api_key": API_KEY,
                                    "key": version,
                                    "kind": "csv",
                                    "raw": "true",
                                    })
    response.raise_for_status()

    response.encoding = 'utf-8'
    df = pd.read_csv(io.StringIO(response.text), encoding='utf-8')

    df['edate_dt'] = pd.to_datetime(df['edate'], format='%d/%m/%Y')
    df['date_dt'] = pd.to_datetime(df['date'], format='%Y%m')

    return df

# %%
def filter_german_manifestos(df: pd.DataFrame, start_date_election: int = START_DATE_ELECTION) -> List[str]:
    """Filter for German parties from start_year onwards"""
    # Filter for Germany and year >= start_year
    filtered = df[(df['countryname'] == 'Germany') & (df['edate_dt'] >= start_date_election)]

    # Create manifesto keys in format: party_date (e.g., 41320_201709)
    keys = []
    for _, row in filtered.iterrows():
        party = row['party']
        date = row['date']
        key = f"{party}_{date}"
        keys.append(key)

    print(f"Found {len(keys)} German manifestos from {start_date_election} onwards")
    print(f"Parties: {filtered['partyname'].unique().tolist()}")

    return keys, filtered

#%%
def get_metadata(keys: List[str], version: str, output_dir: Path) -> Dict:
    """Get metadata for manifestos to check availability"""
    print(f"\nFetching metadata for {len(keys)} manifestos...")

    # API supports batch requests, but we'll chunk them to be safe
    chunk_size = 50
    all_items = []
    missing_items = []

    for i in range(0, len(keys), chunk_size):
        chunk = keys[i:i+chunk_size]

        # Build params with keys[] array
        params = {"api_key": API_KEY, "version": version}
        for key in chunk:
            params[f"keys[]"] = key if f"keys[]" not in params else [params[f"keys[]"], key]

        # POST request to avoid URL length limits
        response = requests.post(f"{BASE_URL}/metadata",
                               data={**params, **{f"keys[]": chunk}})
        response.raise_for_status()

        data = response.json()
        all_items.extend(data.get('items', []))
        missing_items.extend(data.get('missing_items', []))

    print(f"Retrieved metadata for {len(all_items)} manifestos")
    if missing_items:
        print(f"Missing metadata for {len(missing_items)} items")

    output_file = output_dir / "index.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    return {'items': all_items, 'missing_items': missing_items}

#%%
def get_texts(manifesto_ids: List[str], version: str, output_dir: Path,
              translation: str = None) -> Dict:
    """Download manifesto texts and annotations"""
    print(f"\nDownloading texts for {len(manifesto_ids)} manifestos...")

    # Download in batchs
    batch_size = 10  # Smaller batches for text data
    all_texts = []
    missing_items = []

    for i in range(0, len(manifesto_ids), batch_size):
        batch = manifesto_ids[i:i+batch_size]

        print(f"Processing batch {i//batch_size + 1}/{(len(manifesto_ids)-1)//batch_size + 1}...")

        params = {"api_key": API_KEY, "version": version}
        if translation:
            params["translation"] = translation

        # POST request
        response = requests.post(f"{BASE_URL}/texts_and_annotations",
                                 data={**params, **{f"keys[]": batch}})
        response.raise_for_status()

        data = response.json()
        manifestos = data.get('items', [])
        all_texts.extend(manifestos)
        # Should not happen as we check annotations=True.
        missing_items.extend(data.get('missing_items', []))

        # Save individual manifesto texts
        #
        # Each quasi-sentence is annotated (`cmp_code`) with categories,like
        # 104 = "Military: Positive". See also API `get_core_codebook`.
        #
        # https://manifesto-project.wzb.eu/coding_schemes/mp_v5
        for manifesto in manifestos:
            manifesto_id = manifesto.get('key')

            # Save as JSON with metadata
            output_file = output_dir / f"{manifesto_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(manifesto, f, ensure_ascii=False, indent=2)

            # Also save just the text
            text_file = output_dir / f"{manifesto_id}_text.txt"
            text_content = extract_full_text(manifesto)
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)

    print(f"Downloaded {len(all_texts)} texts")
    if missing_items:
        print(f"Missing texts for {len(missing_items)} items: {missing_items}")

    return {'items': all_texts, 'missing_items': missing_items}

#%%
def extract_full_text(manifesto_item: Dict) -> str:
    """Extract full text from a manifesto item"""
    text_parts = []
    sep = '\n' # one quasi-phrase by line

    for item in manifesto_item.get('items', []):
        text = item.get('text', '')
        if text:
            text_parts.append(text)

    return sep.join(text_parts)

#%%
# Dump effectively downloaded info.
def create_summary_csv(metadata_items: List[Dict], texts_result: Dict,
                       output_file: Path):
    """Create a summary CSV with party, date, and file paths"""
    summary_data = []

    downloaded_ids = {item['key'] for item in texts_result['items']}

    for meta in metadata_items:
        manifesto_id = meta.get('manifesto_id')

        summary_data.append({
            'manifesto_id': manifesto_id,
            'party': meta.get('party'),
            'party_name': meta.get('partyname'),
            'date': meta.get('date'),
            'language': meta.get('language'),
            'has_text': manifesto_id in downloaded_ids,
            'text_file': f"{manifesto_id}_text.txt" if manifesto_id in downloaded_ids else None,
            'json_file': f"{manifesto_id}.json" if manifesto_id in downloaded_ids else None,
        })

    df = pd.DataFrame(summary_data)
    df.to_csv(output_file, index=False)
    print(f"\nSummary saved to {output_file}")

    return df

#%%
def get_german_parties(version: str, output_dir: Path, list_form: str = "long"):
    """
    Fetch party list

    Args:
        version: Core dataset version (e.g., 'MPDS2024b')
        list_form: 'short' or 'long' (default: 'long' for more details)
    """
    print(f"Fetching parties for version: {version}")
    print(f"List form: {list_form}")

    response = requests.get(f"{BASE_URL}/get_parties",
                            params={
                                "api_key": API_KEY,
                                "key": version,
                                "list_form": list_form,
                                "raw": "true",
                            })
    response.raise_for_status()

    response.encoding = 'utf-8'
    df = pd.read_csv(io.StringIO(response.text), encoding='utf-8')

    # Only Germany parties
    df = df[df['countryname'] == 'Germany']
    print(f"Retrieved {len(df)} parties")

    df.to_json(output_dir / "parties.json", orient='records', indent=2, force_ascii=False)

    summary = df[['party', 'abbrev', 'year_min', 'year_max', 'name']]
    summary.to_csv(output_dir / "parties_summary.csv", index=False)

    return df


#%%
def main():
    """Main workflow"""
    print("=" * 60)
    print("Manifesto Project - German Manifestos Downloader")
    print("=" * 60)

    output_dir = Path("./german_manifestos")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Get latest versions
    latest_core, latest_metadata = get_latest_versions()
    print(f"\nLatest core dataset: {latest_core}")
    print(f"Latest metadata version: {latest_metadata}")

    # 2. Download core dataset
    core_df = get_core_dataset(latest_core)
    print(f"Core dataset has {len(core_df)} observations")

    # 3. Filter for German manifestos
    keys, filtered_df = filter_german_manifestos(core_df, START_DATE_ELECTION)

    if not keys:
        print("No German manifestos found for the specified period!")
        return

    # 4. Get metadata
    metadata_result = get_metadata(keys, latest_metadata, output_dir)
    metadata_items = metadata_result['items']

    # 5. Check which manifestos have texts available
    manifesto_ids = []
    for item in metadata_items:
        if item.get('annotations') == True:  # Has digital annotations = has text
            manifesto_ids.append(item['manifesto_id'])
    print(f"\n{len(manifesto_ids)}/{len(metadata_items)} manifestos have texts available")

    # 6. Download texts
    texts_result = get_texts(manifesto_ids, latest_metadata, output_dir)

    # 7. Create summary
    summary_df = create_summary_csv(metadata_items, texts_result,
                                    output_dir / "summary.csv")

    # 8. Download parties
    parties = get_german_parties(latest_core, output_dir, list_form="long")

    print("\n" + "=" * 60)
    print("Download complete!")
    print(f"Files saved to: {output_dir.absolute()}")
    print(f"Total manifestos with text: {len(texts_result['items'])}")
    print("=" * 60)

    return summary_df, texts_result


#%%
if __name__ == "__main__":
    main()
