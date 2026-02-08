#!/usr/bin/env bash
# Goal: To download naked mole-rat histology data from the MOTHER database
# Author: Martin Orkuma
# Source: https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber

set -euo pipefail

SEARCH_URL="https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber"

# Where to store downloads (adjust to match your repo layout)
DEST_ROOT="${1:-/mnt/c/Users/marty/data_sci/MyProjects/nmr-ovarian-follicle-ml/data/raw/H_glaber}"

mkdir -p "$DEST_ROOT"

echo "Fetching search page..."
search_html="$(curl -fsSL "$SEARCH_URL")"

# Extract unique accession IDs like MDB0000530
mapfile -t accessions < <(printf "%s" "$search_html" \
  | grep -oE 'MDB[0-9]{7}' \
  | sort -u)

if [[ "${#accessions[@]}" -eq 0 ]]; then
  echo "❌ No accessions found on the search page. Page structure may have changed."
  exit 1
fi

echo "Found ${#accessions[@]} accessions:"
printf " - %s\n" "${accessions[@]}"

echo
echo "Downloading resources to: $DEST_ROOT"
echo

for acc in "${accessions[@]}"; do
  echo "==> $acc"
  acc_dir="$DEST_ROOT/$acc"
  mkdir -p "$acc_dir"

  folder_url="https://mother-db.org/resource-folder/?path=${acc}"

  # Fetch the resource-folder HTML and extract direct file links
  folder_html="$(curl -fsSL "$folder_url")"

  mapfile -t file_urls < <(printf "%s" "$folder_html" \
    | grep -oE 'https?://resources\.mother-db\.org[^"]+' \
    | sort -u)

  if [[ "${#file_urls[@]}" -eq 0 ]]; then
    echo "  ⚠️ No resource links found for $acc (skipping)."
    continue
  fi

  # Download each file (resume supported with -C -)
  for url in "${file_urls[@]}"; do
    fname="$(basename "${url%%\?*}")"
    outpath="$acc_dir/$fname"

    if [[ -f "$outpath" ]]; then
      echo "  - exists: $fname (skipping)"
      continue
    fi

    echo "  - downloading: $fname"
    curl -fL -C - -o "$outpath" "$url"
  done

  echo
done

echo "✅ Done."
