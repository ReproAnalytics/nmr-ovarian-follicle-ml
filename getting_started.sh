#!/usr/bin/env bash
# macOS: GitHub connection (SSH) to our repo + clone + commit + push
# Goal: Connect your Terminal to GitHub via SSH, verify clone, and push to org repo.
# Instructions: Run line by line from top to bottom. Replace placeholder values.
# Authors: Martin Orkuma;
# Link: https://github.com/ReproAnalytics  


####################################################################
########################## Initial Set Up ##########################
####################################################################

# One-time set up
# Ensure you have Git installed
# Open your Bash terminal, assuming you have Homebrew
git --version

# If Git is not installed, run:
# brew install git

# Enter your name and the email you used for GitHub
git config --global user.name "Your Name"
git config --global user.email "your_email@example.com"

# Generate an SSH Key if you do not already have one
ls ~/.ssh

# If you do not see id_ed25519 and id_ed25519.pub, generate one:
ssh-keygen -t ed25519 -C "your_github_email@example.com"
# If prompted to overwrite an existing key, type "n" and press Enter

# Accept default settings. The passphrase is optional

# Start the SSH agent and add your key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copy your key using
cat ~/.ssh/id_ed25519.pub

# Open GitHub's website and paste this key: 
# GitHub -> Settings -> SSH and GPG keys -> New SSH key
# Title: MacBook – <Your Name>

# Test the connection on Bash
ssh -T git@github.com


####################################################################
################## Clone the ReproAnalytics Repo ###################
####################################################################

# One-time step up
## Next, return to the folder where you want to save our Capstone project: 
# use the path to your own local directory
mkdir -p ~/data_sci/MyProjects
cd ~/data_sci/MyProjects

# Clone the ReproAnalytics repo
git clone git@github.com:ReproAnalytics/nmr-ovarian-follicle-ml.git

# Enter the repo 
cd nmr-ovarian-follicle-ml

# Verify SSH Remote
git remote -v



# Daily Flow
# Pull → Branch → Work → Push → Pull Request → Merge → Clean up (Pull)


####################################################################
############################## Pull ################################
####################################################################

cd ~/data_sci/MyProjects/nmr-ovarian-follicle-ml  # Enter the path to you cloned repo

# Sync with main repo to ensure you local repo is up to date
git checkout main
git pull origin main

# Create a personal branch using this naming convention: 
# feature/<yourname>-<directory>-<task>
git checkout -b feature/martin-docs-started  # Replace "martin" with your own name

# Verify it was created
git branch 


####################################################################
############################## Work ################################
####################################################################

# Do your work: Create, run, or modify python script, directories, shell scripts, etc

####################################################################
############################## Push ################################
####################################################################

# Check status of changes you have made
git status
git diff

# Commit your changes
git add .
git commit -m "Add a message detailing what you changed"

# Push your branch to GitHub 
git push -u origin feature/martin-docs-started   


####################################################################
########################## Pull Requests ###########################
####################################################################

# On GitHub, open the repo: https://github.com/ReproAnalytics 
# Click 'Compare & pull request'
# Base: main
# Compare: feature/martin-docs-started   
# Describe your changes

# NB: Another team mate must verify all changes before they appear in the main repo


####################################################################
############################## Merge ###############################
####################################################################

# Only maintainers or reviewers merge into main: But we all are maintainers and reviewers!!!
# Address any comments
# Push follow-up commits to the same branch
# Once approved, merge into main


####################################################################
######################## Clean up After Merge ######################
####################################################################

# Bash
git checkout main
git pull origin main
git branch -d feature/martin-docs-started

# Summary: Pull → Branch → Work → Push → Pull Request → Merge → Clean up (Pull)
