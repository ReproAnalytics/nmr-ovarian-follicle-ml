# Appendix – Supplementary Materials 

**Table of Contents**

A.  Data Source and Ingestion

B. Supplementary Tables 

C. Data Quality Assessment & Cleaning Log 

D. Supplementary Python Code 

- Python Code for Data Composition of .xml files (Objective 1 Table 1) 
- Python Code for Data Composition of .xml files (Objective 1 Table 2) 
- Python Code for Data Composition of .xml files (Objective 1 Table 3) 
- Image-Level Characteristics Summary (Table 4) 
- Tissue-Specific RBG Histograms (Figure 1) 

E. Additional Figures 

F. Data Source Links 

G. References 

## Data Ingestion

The datasets used in this analysis were obtained from the MOTHER Database: https://mother-db.org/search/  

Download script: scripts/download_mother_nmr.sh 

https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml/blob/main/scripts/download_mother_nmr.sh  

```Bash 

#!/usr/bin/env bash 
# Goal: To download nmr histology data from the MOTHER database.
set -euo pipefail 

SEARCH_URL="https://mother-db.org/search/?_sfm_genus_taxon_rank_value=Heterocephalus&_sfm_species_taxon_rank_value=Heterocephalus%20glaber" 

# Where to store downloads, run from repo root and adjust to match your repo layout. 

DEST_ROOT="${1:-data/raw/H_glaber}" 

mkdir -p "$DEST_ROOT" 

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

    echo "X - No resource links found for $acc (skipping)." 

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
echo "Done!" 
```

## Supplementary Tables

Supplemental Table I: Source information for .xml data pulled from MOTHER  

<img src="images/des_v_inf.png" width="700">





## Data Quality Assessment & Cleaning
```Python 
# File presence check: 

def scan_donor_folder(donor_dir: Path) -> DonorRow: 

    warnings: List[str] = [] 

    accession_id = donor_dir.name 

    issues: List[str] = [] 

 

    tiff_path, tiff_hits = find_single_file(donor_dir, TIFF_EXTS) 

    xml_path, xml_hits = find_single_file(donor_dir, (XML_EXT,)) 

    reduced_png = find_png_by_suffix(donor_dir, EXPECTED_PNG_SUFFIXES[0]) 

    thumbnail_png = find_png_by_suffix(donor_dir, EXPECTED_PNG_SUFFIXES[1]) 

 

    if tiff_path is None: 

        issues.append("missing_tiff" if len(tiff_hits) == 0 else f"multiple_tiffs({len(tiff_hits)})") 

    if xml_path is None: 

        issues.append("missing_xml" if len(xml_hits) == 0 else f"multiple_xmls({len(xml_hits)})") 

    if reduced_png is None: 

        issues.append("missing_reduced_png") 

    if thumbnail_png is None: 

        issues.append("missing_thumbnail_png") 

 

    row = DonorRow( 

        accession_id=accession_id, 

        donor_dir=str(donor_dir.as_posix()), 

        tiff_path=str(tiff_path.as_posix()) if tiff_path else "", 

        xml_path=str(xml_path.as_posix()) if xml_path else "", 

        reduced_png_path=str(reduced_png.as_posix()) if reduced_png else "", 

        thumbnail_png_path=str(thumbnail_png.as_posix()) if thumbnail_png else "", 

        ok=len(issues) == 0, 

        issues=issues, 

        warnings=warnings, 

        tiff_candidates=";".join([p.name for p in tiff_hits]), 

        xml_candidates=";".join([p.name for p in xml_hits]), 

    ) 

 

    # TIFF sizes + header hints 

    if tiff_path and tiff_path.exists(): 

        row.tiff_size = tiff_path.stat().st_size 

        qc = tiff_quickcheck(tiff_path) 

        row.tiff_pages = qc.get("tiff_pages")  # type: ignore 

        row.tiff_series_count = qc.get("tiff_series_count")  # type: ignore 

        row.tiff_is_ome = qc.get("tiff_is_ome")  # type: ignore 

        row.tiff_shape_hint = qc.get("tiff_shape_hint")  # type: ignore 

        if tifffile is not None and row.tiff_pages is None: 

            row.issues.append("tiff_unreadable_header") 

``` 

## Supplementary Python Code

 Python Code for Data Composition of .xml files – Objective 1 Table 1  

```Python 

# import pandas library and security bypass 

import pandas as pd import requests  

# XML files have complex element trees 

# will require manual extraction so we import element trees here 

import xml.etree.ElementTree as ET  

import io 

 

# Add all xml files as urls 

urls = [  

"https://resources.mother-db.org/slides/MDB0000530/MDB0000530-P28-Ova-106_s55.xml",  

"https://resources.mother-db.org/slides/MDB0000531/MDB0000531-P1-11-s40.xml",  

"https://resources.mother-db.org/slides/MDB0000532/MDB0000532-P15_F09OV-s83.xml",  

"https://resources.mother-db.org/slides/MDB0000533/MDB0000533-P180_6Mon-6b-s86.xml",  

"https://resources.mother-db.org/slides/MDB0000534/MDB0000534-P5-23-s13.xml",  

"https://resources.mother-db.org/slides/MDB0000535/MDB0000535-P8-F02-OV-s135.xml",  

"https://resources.mother-db.org/slides/MDB0000536/MDB0000536-P90-NMR_3Mo-3B-s96.xml",  

"https://resources.mother-db.org/slides/MDB0000537/MDB0000537-2653-3y-Exsub-s19.xml",  

"https://resources.mother-db.org/slides/MDB0000538/MDB0000538-2659-3y-Sub-s109.xml"  

] 

 

# Create headers for all data frames 

# This has to be done before every table  

headers = {'User-Agent': 'Mozilla/5.0'} all_dfs = [] 

 

# Create for loop 

for url in urls:  

response = requests.get(url, headers=headers) 

if response.status_code == 200: 
		root = ET.fromstring(response.content) 
     
   	 	# Find data points 
    		record = { 
        			"Source": url.split('/')[-1], 
      		  	"Title": root.findtext(".//title").strip() if root.find(".//title") is not 				None else "N/A", 
        			"Organization": root.findtext(".//organizationName").strip() if 				root.find(".//organizationName") is not None else "N/A", 
 
        		# Find Primary Author 
    			"Author_First": root.findtext(".//creator//givenName").strip() if 				root.find(".//creator//givenName") is not None else "N/A", 
			        

 "Author_Last": root.findtext(".//creator//surName").strip() 	if root.find(".//creator//surName") is not 	None else "N/A", 
      	 

  "Author_Contact": root.findtext(".//creator//electronicMailAddress").strip() if root.find(".//creator//electronicMailAddress") is not None else "N/A", 
         
   } 
 
    all_dfs.append(record) 

# Combine into table 

final_df = pd.DataFrame(all_dfs) display(final_df) 

``` 

Python Code for Data Composition of .xml files – Objective 1 Table 2
```Python 

# Create headers for all data frames 

headers = {'User-Agent': 'Mozilla/5.0'}  

all_dfs = [] 

 

# Creating a second table of XML Data for Visualization 

# Define new term 

ns = {'mdb': 'http://mother-db.org/mdb'} 

 

# Create another for loop 

for url in urls:  

response = requests.get(url, headers=headers) 

if response.status_code == 200: 
   		 root = ET.fromstring(response.content) 
     
  	  # Find data points 
	    record2 = { 
  		      # Keep Source as a consistent point across tables 
    		    "Source": url.split('/')[-1], 
 
        		# Taxonomy  
    		    "Common Name": 			root.findtext(".//taxonRankName[.='Species']/../commonName") or "N/A", 
     

   "Scientific Name": root.findtext(".//taxonRankName[.='Species']/../taxonRankValue") or "N/A", 
        

 # Donor Information  
       "Donor ID": root.findtext(".//mdb:donorID", namespaces=ns) or "N/A", 
        "Donor Life Stage": root.findtext(".//mdb:donorLifeStage", namespaces=ns) or "N/A", 
        "Donor Sex": root.findtext(".//mdb:donorSex", namespaces=ns) or "N/A", 
        "Ovary Sampled": root.findtext(".//mdb:ovaryPosition", namespaces=ns) or "N/A", 
        "Slide ID": root.findtext(".//mdb:slideID", namespaces=ns) or "N/A" 
    } 
 
    all_dfs.append(record2) 
  

# Combine into table 

final_df = pd.DataFrame(all_dfs)  

display(final_df) 
```

Python Code for Data Composition of .xml files – Objective 1 Table 3 
```Python 

# Create headers for all data frames 

headers = {'User-Agent': 'Mozilla/5.0'} all_dfs = [] 

 

# Creating a third table of XML Data for Visualization 

# Redefine new term 

ns = {'mdb': 'http://mother-db.org/mdb'} 

 

# Create another for loop 

for url in urls:  

response = requests.get(url, headers=headers) 

if response.status_code == 200: 
		    root = ET.fromstring(response.content) 
     
	    # Find data points 
		    record3 = { 
		        # Keep Source as a consistent point across tables 
		        "Source": url.split('/')[-1], 
         
	   # Donor Information  

"Donor ID": root.findtext(".//mdb:donorID", namespaces=ns) or "N/A", 
       	 "Slide ID": root.findtext(".//mdb:slideID", namespaces=ns) or "N/A", 
 
    	    # Sample and Methods Information 
        		"Tissue Thickness": root.findtext(".//mdb:thickness", namespaces=ns) or "N/A", 
        		"Units": root.findtext(".//mdb:unit", namespaces=ns) or "N/A", 
       		 "Microscope Make and Model": root.findtext(".//mdb:notes", namespaces=ns) or "N/A" 
    } 
 
    all_dfs.append(record3) 
  

# Combine into table 

final_df = pd.DataFrame(all_dfs)  

display(final_df) 

```
Image-Level Characteristics Summary
```Python 

from PIL import Image 

import glob 

import pandas as pd 

import os 

import matplotlib.pyplot as plt 

 

# Path to H_glaber .png images 

img_dir = "~/nmr-ovarian-follicle-ml/data/raw/H_glaber/EDAreduced/" 

 

# Pull all H_glaber .png files 

img_paths = glob.glob(os.path.join(img_dir, "*.png")) 

summary_data = [] 

 

for img_path in img_paths: 

    print(f"Processing {img_path}") 

     

    try: 

        img = Image.open(img_path) 

        width, height = img.size 

         

        summary_data.append({ 

            "image_name": os.path.basename(img_path), 

            "width": width, 

            "height": height, 

            "mode": img.mode  # RGB, grayscale, etc. 

        }) 

 

    except Exception as e: 

        summary_data.append({ 

            "image_name": os.path.basename(img_path), 

            "width": "ERROR", 

            "height": "ERROR", 

            "mode": "ERROR" 

        }) 

 

# Save results to a .csv before turning into a formatted table  

df = pd.DataFrame(summary_data) 

df.to_csv("png_summary.csv", index=False) 

 

# Load the formatted .csv file  

df = pd.read_csv("formatted_slide_summary.csv") 

 

# Create figure and table  

fig, ax = plt.subplots(figsize=(12, 5)) 

ax.axis('off') 

table = ax.table( 

    cellText=df.values, 

    colLabels=df.columns, 

    cellLoc='center', 

    loc='center') 

 

# Turn off auto font scaling 

table.auto_set_font_size(False) 

table.set_fontsize(10) 

 

# Calculate max text length per column (including header) 

col_widths = [] 

for col in df.columns: 

    max_len = max( 

        df[col].astype(str).map(len).max(), 

        len(col)) 

    col_widths.append(max_len) 

 

# Normalize widths so they fit figure 

total = sum(col_widths) 

col_widths = [w / total for w in col_widths] 

 

# Format the table appropriately (apply width, scale, type-face) 

for i, width in enumerate(col_widths): 

    for j in range(len(df) + 1):  # +1 for header row 

        table[j, i].set_width(width) 

table.scale(1, 1.6) 

for (row, col), cell in table.get_celld().items(): 

    if row == 0: 

        cell.set_text_props(weight='bold') 

 

# Save figure as the slide summary table of all 9 images analyzed 

plt.savefig("slide_summary_table.png", bbox_inches='tight', dpi=300) 

plt.close()  

```

Tissue-specific RBG histograms
```Python 

from PIL import Image 

import matplotlib.pyplot as plt 

import numpy as np 

import glob 

import os 

 

# Directories 

img_dir = "~ /nmr-ovarian-follicle-ml/data/raw/H_glaber/Histograms/TissueHist/" 

output_path = "~ /nmr-ovarian-follicle- 

ml/data/raw/H_glaber/Histograms/TissueHist/combined_tissue_histograms.png" 

 

# Get image paths to all 9 images 

img_paths = sorted(glob.glob(os.path.join(img_dir, "*.png")))[:9] 

n_images = len(img_paths) 

 

# Grid size of combined image cluster (3x3 for 9 images) 

rows = 3 

cols = 3 

fig, axes = plt.subplots(rows, cols, figsize=(15, 12)) 

axes = axes.flatten() 

for idx, img_path in enumerate(img_paths): 

    ax = axes[idx] 

    try: 

        img = Image.open(img_path).convert("RGB") 

        img_array = np.array(img) 

 

        # Tissue mask (remove background) 

        mask = np.mean(img_array, axis=2) < 240 

        tissue_pixels = img_array[mask] 

 

        if tissue_pixels.size == 0: 

            ax.set_title("No Tissue") 

            ax.axis("off") 

            continue 

 

        # Plot RGB histograms 

        for i, color in enumerate(['r', 'g', 'b']): 

            ax.hist(tissue_pixels[:, i], bins=256, alpha=0.4, density=True) 

 

        # Formatting 

        filename = os.path.basename(img_path) 

        ax.set_title(filename, fontsize=9) 

        ax.set_xlim(0, 255) 

        ax.set_xlabel("Intensity", fontsize=8) 

        ax.set_ylabel("Density", fontsize=8) 

 

    except Exception as e: 

        ax.set_title("Error") 

        ax.axis("off") 

        print(f"Error processing {img_path}: {e}") 

 

# Aesthetic adjustment for title and scale 

fig.suptitle("Tissue-Specific RGB Histograms Across MOTHER Slides", fontsize=16) 

plt.tight_layout(rect=[0, 0, 1, 0.96]) 

 

# Save figure 

plt.savefig(output_path, dpi=300) 

plt.close()  

```

## Additional Figures 

a. Supplemental Figure 1. Cell and Nucleus Count Summary per Slide


b. Supplemental Figure 2. Boxplot Representation of the Distribution of Nuclear Area Across all 9 Slides.  

c. Supplemental Figure 3. Bootstrapping output from QuPath Analysis

d. 


## References

Barreñada, O., & Brieño-Enriquez, M. (2026). Multispecies Ovary Tissue Histology Electronic Repository. https://mother-db.org 

IBM. (n.d.). Exploratory Data Analysis. Ibm.com. https://www.ibm.com/think/topics/exploratory-data-analysis  

MOTHER (2024). MOTHER Resources on GitHub. Available at https://github.com/mother-db. 

ReproAnalytics (2026). NMR Ovarian Follicle ML Project. https://github.com/ReproAnalytics/nmr-ovarian-follicle-ml  

Watanabe, K. H., Dietrich, S. W., Ding, Y., Ma, W., Sluka, J. P., & Zelinski, M. B. (2024). Overview of the Multispecies Ovary Tissue Histology Electronic Repository (MOTHER). Biology of Reproduction, 111(3), 512–515. https://doi.org/10.1093/biolre/ioae101 





