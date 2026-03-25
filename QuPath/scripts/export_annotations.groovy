import qupath.lib.gui.scripting.QPEx
import java.io.File

def annotationsDir = new File(args[0])
def metricsDir = new File(args[1])

annotationsDir.mkdirs()
metricsDir.mkdirs()

def project = QPEx.getProject()
if (project == null) {
    throw new IllegalStateException("No QuPath project open")
}

for (entry in project.getImageList()) {
    def imageData = entry.readImageData()
    QPEx.setBatchProjectAndImage(project, imageData)

    def imageName = entry.getImageName().replaceAll(/\.[^.]+$/, "")
    def annotations = QPEx.getAnnotationObjects()

    def geojsonFile = new File(annotationsDir, "${imageName}_annotations.geojson")
    exportObjectsToGeoJson(annotations, geojsonFile.getAbsolutePath(), "FEATURE_COLLECTION")

    def annTsv = new File(metricsDir, "${imageName}_annotations.tsv")
    saveAnnotationMeasurements(annTsv.getAbsolutePath())

    println "Exported annotations for ${imageName}"
}
