// ============================================================
// tissue_detection.groovy
// Purpose: Detect tissue regions across all 9 project images
// ============================================================

def project = getProject()
if (project == null) throw new IllegalStateException("No project open.")

println "=== Tissue detection starting ==="
println "Images to process: ${project.getImageList().size()}"

for (entry in project.getImageList()) {
    def imageData = entry.readImageData()
    println "\nProcessing: ${entry.getImageName()}"

    imageData.getHierarchy().clearAll()

    def params = '{"threshold": 210,' +
                 ' "requestedPixelSizeMicrons": 20.0,' +
                 ' "minAreaMicrons": 20000.0,' +
                 ' "maxHoleAreaMicrons": 50000.0,' +
                 ' "darkBackground": false,' +
                 ' "smoothImage": true,' +
                 ' "medianCleanup": true,' +
                 ' "dilateBoundaries": false,' +
                 ' "smoothCoordinates": true,' +
                 ' "excludeOnBoundary": false,' +
                 ' "singleAnnotation": false}'

    QP.runPlugin(
        'qupath.imagej.detect.tissue.SimpleTissueDetection2',
        imageData,
        params
    )

    def count = imageData.getHierarchy().getAnnotationObjects().size()
    println "  Tissue regions detected: ${count}"

    entry.saveImageData(imageData)
}

println "\n=== Tissue detection finished ==="
println "Processed ${project.getImageList().size()} image(s)"

exportAnnotationsToJson("nmr-ovarian-follicle-ml/outputs.geojson")