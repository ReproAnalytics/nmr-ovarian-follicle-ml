// ============================================================
// import_images.groovy
// Purpose: Import H. glaber ovarian histology images (.tif)
//          into a QuPath project.
//
// Usage:
//   GUI  — Run via Automate > Script Editor (no args needed)
//   CLI  — Pass raw dir as --args (headless mode, QuPath 0.5+)
//
// Notes:
//   - Files are plain .tif (not .ome.tif) from the MOTHER database
// ============================================================

import qupath.lib.images.servers.ImageServerProvider
import java.awt.image.BufferedImage
import java.nio.file.Files
import java.io.File

println "=== import_images.groovy starting ==="

// ------------------------------------------------------------------
// 1. Resolve raw image directory
// ------------------------------------------------------------------
def rawDir

if (args.length >= 1) {
    rawDir = new File(args[0])
    println "rawDir (from args): ${rawDir.getAbsolutePath()}"
} else {
    rawDir = new File(buildFilePath(PROJECT_BASE_DIR, "..", "..", "data", "raw", "H_glaber"))
    println "rawDir (fallback):  ${rawDir.getAbsolutePath()}"
}

println "rawDir exists?      " + rawDir.exists()
println "rawDir isDirectory? " + rawDir.isDirectory()

if (!rawDir.exists() || !rawDir.isDirectory()) {
    throw new IllegalArgumentException(
        "Raw image directory not found: " + rawDir.getAbsolutePath()
    )
}

// ------------------------------------------------------------------
// 2. Get open project
// ------------------------------------------------------------------
def project = getProject()
println "project is null?    " + (project == null)

if (project == null) {
    throw new IllegalStateException(
        "No QuPath project is open. Load the project before running this script."
    )
}

// ------------------------------------------------------------------
// 3. Collect .tif files (recursive — walks accession subfolders)
//    NOTE: MOTHER database files are plain .tif, NOT .ome.tif
// ------------------------------------------------------------------
def exts = [".tif", ".tiff"]

def imageFiles = []
Files.walk(rawDir.toPath()).withCloseable { stream ->
    imageFiles = stream
        .filter  { Files.isRegularFile(it) }
        .map     { it.toFile() }
        .filter  { f ->
            def name = f.getName().toLowerCase()
            exts.any { ext -> name.endsWith(ext) }
        }
        .sorted  { a, b -> a.getAbsolutePath() <=> b.getAbsolutePath() }
        .toList()
}

println "Found ${imageFiles.size()} .tif candidate file(s)"

// ------------------------------------------------------------------
// 4. Import via ImageServerProvider builder (QuPath 0.5+ API)
// ------------------------------------------------------------------
int importedCount = 0
int skippedCount  = 0

for (file in imageFiles) {
    def uriString = file.toURI().toString()
    println "Trying: ${file.getName()}"
    try {
        def support = ImageServerProvider.getPreferredUriImageSupport(
            BufferedImage.class, uriString
        )
        if (support == null || support.builders.isEmpty()) {
            println "  WARN: No compatible server — skipping ${file.getName()}"
            skippedCount++
            continue
        }
        def entry = project.addImage(support.builders.get(0))
        entry.setImageName(file.getName())
        importedCount++
        println "  OK: ${file.getName()}"
    } catch (Exception e) {
        println "  SKIP: ${file.getName()} → ${e.getClass().getName()}: ${e.getMessage()}"
        skippedCount++
    }
}

// ------------------------------------------------------------------
// 5. Persist to .qpproj
// ------------------------------------------------------------------
project.syncChanges()

println ""
println "=== import_images.groovy finished ==="
println "  Imported : $importedCount"
println "  Skipped  : $skippedCount"
