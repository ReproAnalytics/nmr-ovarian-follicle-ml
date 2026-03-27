#!/usr/bin/env bash
# Goal: To download nmr histology data from the MOTHER database.
# Authors: Julian Coles, Martin Orkuma, Pamela Styborski, and Silvia Tenempaguay-Nunez
# Source: https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber

set -euo pipefail

SEARCH_URL="https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber"

# Where to store downloads, run from repo root and adjust to match your repo layout.
DEST_ROOT="${1:-data/raw/H_glaber}"
MANIFEST_PATH="${2:-data/raw/H_glaber_manifest.csv}"

mkdir -p "$DEST_ROOT"
mkdir -p "$(dirname "$MANIFEST_PATH")"

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
    curl -fL -C - -o "$outpath" "$url"
  done

  echo
done

echo "Building manifest: $MANIFEST_PATH"

{
  echo "accession_id,file_name,file_path,file_type,extension,size_bytes"

  find "$DEST_ROOT" -type f | sort | while IFS= read -r filepath; do
    relpath="${filepath#"$DEST_ROOT"/}"
    accession_id="${relpath%%/*}"
    file_name="$(basename "$filepath")"
    extension="${file_name##*.}"
    size_bytes="$(stat -c%s "$filepath")"

    case "${file_name,,}" in
      *.ome.tif|*.ome.tiff|*.tif|*.tiff)
        file_type="image"
        ;;
      *.xml)
        file_type="xml"
        ;;
      *.png|*.jpg|*.jpeg)
        file_type="preview"
        ;;
      *)
        file_type="other"
        ;;
    esac

    printf '%s,%s,%s,%s,%s,%s\n' \
      "$accession_id" \
      "$file_name" \
      "$filepath" \
      "$file_type" \
      "$extension" \
      "$size_bytes"
  done
} > "$MANIFEST_PATH"

echo
echo "Done!"
echo "Manifest written to: $MANIFEST_PATH"
