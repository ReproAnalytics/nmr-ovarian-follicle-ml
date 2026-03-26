import qupath.lib.regions.RegionRequest
import javax.imageio.ImageIO

// Get image + server
def imageData = getCurrentImageData()
def server = imageData.getServer()

// Output directory (organized by slide name)
def name = GeneralTools.stripExtension(server.getMetadata().getName())
def outputDir = buildFilePath(PROJECT_BASE_DIR, "tiles", name)
mkdirs(outputDir)

// Parameters
def tileSize = 224
def downsample = 1   // increase to 2 or 4 if needed

// Get annotations
def annotations = getAnnotationObjects()

int tileCount = 0

for (annotation in annotations) {

    def roi = annotation.getROI()

    //  Correct way to get bounds (older QuPath)
    def xStart = (int) roi.getBoundsX()
    def yStart = (int) roi.getBoundsY()
    def width  = (int) roi.getBoundsWidth()
    def height = (int) roi.getBoundsHeight()

    // Get class name
    def pathClass = annotation.getPathClass()
    def className = pathClass != null ? pathClass.toString() : "Unclassified"

    // Create class folder
    def classDir = buildFilePath(outputDir, className)
    mkdirs(classDir)

    for (int x = xStart; x < xStart + width; x += tileSize) {
        for (int y = yStart; y < yStart + height; y += tileSize) {

            try {
                def request = RegionRequest.createInstance(
                    server.getPath(),
                    downsample,
                    x, y,
                    tileSize, tileSize
                )

                def img = server.readBufferedImage(request)

                // Skip invalid tiles
                if (img == null)
                    continue

                // Save tile
                def fileName = "tile_" + tileCount + ".png"
                def filePath = buildFilePath(classDir, fileName)

                ImageIO.write(img, "PNG", new File(filePath))

                tileCount++

            } catch (Exception e) {
                print "Skipped tile at (${x}, ${y})\n"
            }
        }
    }
}

print " Exported " + tileCount + " tiles\n"