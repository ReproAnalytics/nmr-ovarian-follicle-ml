import qupath.lib.gui.scripting.QPEx
import java.nio.file.Files
import java.io.File

println "=== import_images.groovy starting ==="
println "args.length = " + args.length
args.eachWithIndex { a, i -> println "args[$i] = $a" }

if (args.length < 1) {
    throw new IllegalArgumentException("Expected 1 argument: raw image directory")
}

def rawDir = new File(args[0])
println "rawDir = " + rawDir.getAbsolutePath()
println "rawDir exists? " + rawDir.exists()
println "rawDir isDirectory? " + rawDir.isDirectory()

def project = QPEx.getProject()
println "project is null? " + (project == null)

if (project == null) {
    throw new IllegalStateException("No QuPath project is open. Use --project when calling this script.")
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

println "Found ${imageFiles.size()} candidate image files"

for (file in imageFiles) {
    try {
        println "Trying import: ${file.getAbsolutePath()}"
        project.addImage(file.toURI())
        println "Imported: ${file.getAbsolutePath()}"
    } catch (Exception e) {
        println "Skipped ${file.getName()} -> ${e.getClass().getName()}: ${e.getMessage()}"
    }
}

project.syncChanges()
println "QuPath project sync complete"
println "=== import_images.groovy finished ==="