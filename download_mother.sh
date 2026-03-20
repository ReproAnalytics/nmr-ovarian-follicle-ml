#!/usr/bin/env bash
set -euo pipefail

SEARCH_URL="https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber"

DEST_ROOT="${1:-$HOME/data_sci/MyCapstone/nmr-ovarian-follicle-ml/data/raw/H_glaber}"

mkdir -p "$DEST_ROOT"

search_html="$(curl -fsSL "$SEARCH_URL")"

mapfile -t accessions < <(
  printf "%s" "$search_html" \
  | grep -oE 'MDB[0-9]{7}' \
  | sort -u
)

if [[ "${#accessions[@]}" -eq 0 ]]; then
  echo "No accessions found."
  exit 1
fi

for acc in "${accessions[@]}"; do
  acc_dir="$DEST_ROOT/$acc"
  mkdir -p "$acc_dir"

  folder_url="https://mother-db.org/resource-folder/?path=${acc}"
  folder_html="$(curl -fsSL "$folder_url")"

  mapfile -t file_urls < <(
    printf "%s" "$folder_html" \
    | grep -oE 'https?://resources\.mother-db\.org[^"]+' \
    | sort -u
  )

  if [[ "${#file_urls[@]}" -eq 0 ]]; then
    echo "No files found for $acc"
    continue
  fi

  for url in "${file_urls[@]}"; do
    fname="$(basename "${url%%\?*}")"
    outpath="$acc_dir/$fname"

    if [[ -f "$outpath" ]]; then
      echo "Skipping existing file: $fname"
      continue
    fi

    curl -fL -C - -o "$outpath" "$url"
  done
done
