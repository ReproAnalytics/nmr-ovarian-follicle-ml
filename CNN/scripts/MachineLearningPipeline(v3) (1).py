#!/usr/bin/env python
# coding: utf-8

# In[ ]:


## Set up Environment ##

# To ensure fastai install without error, use the following commands to force installation without any requirements to get the core library
get_ipython().run_line_magic('pip', 'install --no-deps fastai fastcore')

# Install the missing 'distutils' support
get_ipython().run_line_magic('pip', 'install "setuptools<65"')

# Manually install critical dependencies that are compatible
get_ipython().run_line_magic('pip', 'install matplotlib pandas requests pyyaml packaging fastprogress')

# Attempt to install a specific version of spacy that avoids the build
get_ipython().run_line_magic('pip', 'install spacy --only-binary=:all:')

# Install openslide for downstream implemetation of WSI
get_ipython().run_line_magic('pip', 'install openslide-python')


# In[ ]:


# Import all necessary packages
import fastai
print(fastai.__version__)

from fastai.vision.all import *
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd
import numpy as np
import torch
import openslide


# In[ ]:


# Force CPU if GPU causes crashes to back up pipeline, suggested by mulyiple resources
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("Using device:", device)


# The pathway version assumes:
# /H_glaber/
#     train/
#         primordial/
#         primary/
#         stroma/
#         transitional primordial/
#     valid/
#         primordial/
#         primary/
#         stroma/
#         transitional primordial/
# 
# Adjust pathway as needed but make sure it is compatible with Resnet34 inutition

# In[ ]:


# Load the QuPath tiles and build the fastai dataset loader with the pathway

path = Path('~/H_glaber').expanduser()
dls = ImageDataLoaders.from_folder(
    path, 
    train = 'train',
    valid = 'valid',
    item_tfms = Resize(224), 
    batch_tfms = Normalize.from_stats(*imagenet_stats),
    bs = 16)

# Display the Qupath classification groups
print("Classes:", dls.vocab)
dls.show_batch(max_n = 6)


# In[ ]:


# Initialize the model and identifying the best resnet34 model 
# Confirm that these metircs are of interest (pre-trained weight?)

learn = cnn_learner(
    dls,
    resnet34,
    metrics = error_rate)

learn.model.to(device)


# In[ ]:


# Initiate callbacks

from fastai.callback.tracker import EarlyStoppingCallback, SaveModelCallback

early_stop = EarlyStoppingCallback(monitor='valid_loss', patience = 20)
save_best = SaveModelCallback(monitor='valid_loss', fname='best_resnet34')

## freeze and train the head of the resnet34

learn.fine_tune(
    5,
    base_lr=1e-3,
    cbs=[
        EarlyStoppingCallback(monitor='valid_loss', patience=3),
        SaveModelCallback(monitor='valid_loss', fname='best_resnet34')
    ]
)

# unfreeze the CNN and open back up to run though all the layers with a set number of epochs

learn.unfreeze()

learn.fit_one_cycle(
    10,
    lr_max=slice(1e-5, 1e-3),
    cbs=[
        EarlyStoppingCallback(monitor='valid_loss', patience=3),
        SaveModelCallback(monitor='valid_loss', fname='best_resnet34')
    ]
)


# In[ ]:


# load the best resnet34 model model 

learn.load('best_resnet34')
learn.model.eval()


# In[ ]:


# evaluate the model with a confusion matrix

interp = ClassificationInterpretation.from_learner(learn)

interp.plot_confusion_matrix()
interp.plot_top_losses(5)


# In[ ]:


# Unsure if needed, but can run a subset of tilesfor tile-level testing

tile_dir = Path("~/H_glaber/test").expanduser()

counts = {cls: 0 for cls in dls.vocab}
results = []

for img_path in tile_dir.glob("*.png"):
    pred, pred_idx, probs = learn.predict(img_path)

    counts[str(pred)] += 1

    results.append({
        "tile": str(img_path),
        "prediction": str(pred),
        "confidence": float(probs[pred_idx])
    })

pd.DataFrame(results).to_csv("tile_predictions.csv", index=False)
pd.DataFrame([counts]).to_csv("tile_counts_summary.csv", index=False)

print("Tile Counts:", counts)


# In[ ]:


###### Test on Whole Slide Images of the H. glaber dataset (MAY WANT TO DIVIDE THESE SCRIPTS #######


# In[ ]:


# To input the larger TIFF files, install and import a WSI reader 

get_ipython().run_line_magic('pip', 'install openslide-python')


# In[ ]:


# Tile the whole slide image before execting the CNN (remove background first)

# Remove background on an elementary level
def is_tissue(tile, threshold = 220):
    """Simple background filter"""
    arr = np.array(tile)
    return np.mean(arr) < threshold

def tile_wsi(slide, level = 0, tile_size = 224, stride = 224):
    width, height = slide.level_dimensions[level]

    tiles = []
    coords = []

    for y in range(0, height - tile_size, stride):
        for x in range(0, width - tile_size, stride):
            tile = slide.read_region((x, y), level, (tile_size, tile_size)).convert("RGB")
        if is_tissue(tile):
            tiles.append(tile)
            coords.append((x, y))

    return tiles, coords


# In[ ]:


# Actively run the trained CNN on the WSI tiles for fast WSI inference

def analyze_wsi(slide_path, learn, level = 1):
    print(f"\nProcessing: {slide_path}")
    
    slide = openslide.OpenSlide(slide_path)

    tiles, coords = tile_wsi(slide, level=level)

    if len(tiles) == 0:
        print("No tissue detected.")
        return None

    # Iniatiate rapid inference predictions in batch (make sure to set a counter)
    
    dl = learn.dls.test_dl(tiles)
    preds, _ = learn.get_preds(dl=dl)

    pred_classes = preds.argmax(dim=1)

    counts = {cls: 0 for cls in learn.dls.vocab}
    spatial_results = []
    
    for i, cls_idx in enumerate(pred_classes):
        label = learn.dls.vocab[cls_idx]
        counts[label] += 1

        x, y = coords[i]
        spatial_results.append({
            "x": x,
            "y": y,
            "prediction": label
        })

    return counts, spatial_results


# In[ ]:


# Run through all WSI files for H. glaber pulled from the MOTHER database 
slide_paths = glob.glob(os.path.expanduser("~/H_glaber/*.tif"))

all_results = []

for slide_path in slide_paths:
    output = analyze_wsi(slide_path, learn)

    if output is None:
        continue

    counts, spatial = output

    print("Counts:", counts)

    # Save per-slide results
    slide_name = Path(slide_path).stem

    pd.DataFrame([counts]).to_csv(f"{slide_name}_counts.csv", index=False)
    pd.DataFrame(spatial).to_csv(f"{slide_name}_spatial.csv", index=False)

    all_results.append({
        "slide": slide_name,
        **counts
    })


# In[ ]:


# Save a summary of the overall pipeline 

pd.DataFrame(all_results).to_csv("all_slides_summary.csv", index=False)

print("\nPipeline complete.")

