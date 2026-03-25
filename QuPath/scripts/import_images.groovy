import qupath.lib.gui.scripting.QPEx
import java.nio.file.Files
import java.io.File

def rawDir = new File(args[0])

def project = QPEx.getProject()
if (project == null) {
    throw new IllegalStateException("No QuPath project is open. Use --project when calling this script.")
}

if (!rawDir.exists() || !rawDir.isDirectory()) {
    throw new IllegalArgumentException("Raw image directory does not exist: " + rawDir.getAbsolutePath())
}

def exts = [".ome.tif", ".ome.tiff", ".tif", ".tiff"]

def imageFiles = Files.walk(rawDir.toPath())
    .filter { Files.isRegularFile(it) }
    .map { it.toFile() }
    .filter { f ->
        def name = f.getName().toLowerCase()
        exts.any { name.endsWith(it) }
    }
    .toList()

println "Found ${imageFiles.size()} candidate image files in ${rawDir}"

for (file in imageFiles) {
    try {
        project.addImage(file.toURI())
        println "Imported: ${file.getAbsolutePath()}"
    } catch (Exception e) {
        println "Skipped ${file.getName()} -> ${e.getMessage()}"
    }
}

project.syncChanges()
println "QuPath project sync complete"
