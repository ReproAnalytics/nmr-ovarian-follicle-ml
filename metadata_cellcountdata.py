import pandas as pd
import glob
import os

# Path to nuclei files
nuclei_files = glob.glob("nuclei_*.csv")

# Load and concatenate all specimens
nuclei_list = []

for file in nuclei_files:
    df = pd.read_csv(file, sep="\t")
    df["source_file"] = os.path.basename(file)
    nuclei_list.append(df)

cells = pd.concat(nuclei_list, ignore_index=True)

print("Total cells:", len(cells))


print(cells.columns)

metadata = pd.read_csv("~/data_sci/MyCapstone/EDA_wQuPath/cellcount/dataset_inventory.csv") 

# Keep only relevant metadata columns
metadata = metadata[[
    "tiff_candidates",
    "donorYears",
    "donorDays",
    "donorSex",
    "donorLifeStage",
    
]]

print(metadata.head())



#merging key comparison
print(cells["tiff_candidates"].unique()[:5])
print(metadata["tiff_candidates"].unique()[:5])
#merge
cells = cells.merge(
    metadata,
    on="tiff_candidates",
    how="left"
)

print(cells[["tiff_candidates", "donorYears"]].head())

print("Total cells:", len(cells))
print("Unique specimens:", cells["tiff_candidates"].nunique())
print("Unique ages:", cells["donorYears"].unique()) 
#area is numerical?
cells["Nucleus: Area"] = pd.to_numeric(cells["Nucleus: Area"], errors="coerce")
cells = cells.dropna(subset=["Nucleus: Area"])
cells = cells.drop(columns=["Object ID"])

#save data in csv
cells.to_csv("celldata-metadatacombined1.csv", index=False)
#area is numerical?
cells["Nucleus: Area"] = pd.to_numeric(cells["Nucleus: Area"], errors="coerce")
cells = cells.dropna(subset=["Nucleus: Area"])

# Donor Morphology
def cv(x):
    return np.std(x) / np.mean(x)

donor_div = cells.groupby("tiff_candidates").agg(
    donorYears=("donorYears", "first"),
    donorDays=("donorDays", "first"),   
    nuc_mean=("Nucleus: Area", "mean"),
    nuc_std=("Nucleus: Area", "std")
)

donor_div["nuc_cv"] = donor_div["nuc_std"] / donor_div["nuc_mean"]

print(donor_div)

# Shape Diversity

shape_div = cells.groupby("tiff_candidates").agg(
    circ_sd=("Nucleus: Circularity", "std"),
    ecc_sd=("Nucleus: Eccentricity", "std")
)

donor_div = donor_div.merge(shape_div, on="tiff_candidates")

print(donor_div.head())

# Intensity Heterogeneity , chromatin and marker variability

intensity_div = cells.groupby("tiff_candidates").agg(
    hemo_sd=("Nucleus: Hematoxylin OD mean", "std"),
    dab_sd=("Nucleus: DAB OD mean", "std")
)

donor_div = donor_div.merge(intensity_div, on="tiff_candidates")

print(donor_div.head())

# Cleaning Age Variable
donor_div["age_years"] = donor_div["donorYears"]

donor_div.loc[
    donor_div["age_years"].isna(),
    "age_years"
] = donor_div["donorDays"] / 365

# Composite Diversity 
import numpy as np

features = [
    "nuc_cv",
    "circ_sd",
    "ecc_sd",
    "hemo_sd",
    "dab_sd"
]

# Manual z-score normalization
scaled = (donor_div[features] - donor_div[features].mean()) / donor_div[features].std()

donor_div["composite_diversity"] = scaled.mean(axis=1)

# Possible Age Relationship 
from scipy.stats import spearmanr

rho, p = spearmanr(
    donor_div["age_years"],
    donor_div["composite_diversity"]
)

print("Composite diversity vs age")
print("rho =", round(rho, 3))
print("p =", round(p, 4))


# Visual 
import seaborn as sns
import matplotlib.pyplot as plt

plt.figure(figsize=(6,5))
sns.regplot(
    x="age_years",
    y="composite_diversity",
    data=donor_div,
    scatter_kws={"s":80}
)

plt.xlabel("Age (years)")
plt.ylabel("Composite Morphological Diversity")
plt.title("Age vs Ovarian Morphological Heterogeneity")
plt.tight_layout()
plt.show()