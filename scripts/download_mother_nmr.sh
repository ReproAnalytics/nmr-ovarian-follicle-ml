#!/usr/bin/env bash
# Goal: To download nmr histology data from the MOTHER database.
# Authors: Julian Coles, Martin Orkuma, Pamela Styborski, and Silvia Tenempaguay-Nunez 
# Source: https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber

set -euo pipefail

SEARCH_URL="https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber"

# Where to store downloads, run from repo root and adjust to match your repo layout.
DEST_ROOT="${1:-data/raw/H_glaber}"


mkdir -p "$DEST_ROOT"

# Summary counters
total_accessions=0
accessions_with_files=0
accessions_skipped=0
files_downloaded=0
files_skipped=0
files_failed=0

echo "Fetching search page..."
search_html="$(curl -fsSL "$SEARCH_URL")"

# Extract unique accession IDs like MDB0000530
mapfile -t accessions < <(printf "%s" "$search_html" \
  | grep -oE 'MDB[0-9]{7}' \
  | sort -u)

if [[ "${#accessions[@]}" -eq 0 ]]; then
  echo "X - No accessions found on the search page. Page structure may have changed."

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
    echo " - No resource links found for $acc (skipping)."
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
    if curl -fL -C - -o "$outpath" "$url"; then
      ((files_downloaded+=1))
    else
      echo "  - failed: $fname"
      ((files_failed+=1))
    fi
  done

  echo
done

echo "================ DOWNLOAD SUMMARY ================"
echo "Destination root:      $DEST_ROOT"
echo "Total accessions:      $total_accessions"
echo "Accessions with files: $accessions_with_files"
echo "Accessions skipped:    $accessions_skipped"
echo "Files downloaded:      $files_downloaded"
echo "Files skipped:         $files_skipped"
echo "Files failed:          $files_failed"
echo "==================================================" 