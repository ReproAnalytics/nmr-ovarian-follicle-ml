# Follicle Annotation Protocol

## Objective
Annotate ovarian follicles in naked mole-rat (Heterocephalus glaber) histology
tile images by follicle developmental stage.

## Classes
| Class       | ID | Description                                     |
|-------------|----|-------------------------------------------------|
| background  |  0 | No follicle present in the tile                 |
| primordial  |  1 | Single layer of flat granulosa cells            |
| primary     |  2 | Single layer of cuboidal granulosa cells        |
| secondary   |  3 | Multiple granulosa layers, no antral cavity     |
| antral      |  4 | Visible fluid-filled antral cavity              |

## Tool
- QuPath (https://qupath.github.io/)

## Procedure
1. Open the whole-slide image in QuPath.
2. For each identifiable follicle, draw a detection annotation and assign the class.
3. Export annotations as GeoJSON via `Measure > Export measurements`.
4. Place exported files in `annotations/raw_exports/`.

## Inter-annotator Agreement
- Each slide should be annotated by ≥ 2 annotators.
- Disagreements resolved by majority vote or domain-expert adjudication.
