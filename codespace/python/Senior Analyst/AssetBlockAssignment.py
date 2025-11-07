import arcpy
import os
from collections import defaultdict
import math

"""
--------------------------------------------------------------------------------
SCRIPT OVERVIEW
--------------------------------------------------------------------------------
This workflow applies geometric computation and key geographic principles to
associate utility pipe segments with nearby street centerlines.

Built on Tobler’s First Law (“near things are more related than distant things”),
the script uses planar distance, angular similarity, and topological adjacency
to infer the most likely street match for each pipe. Pipes are split into
normalized 400-ft segments to minimize scale bias (MAUP) and analyzed using a
nearest neighbor approach to identify the two closest street candidates.

Directional statistics (bearing and angle difference) measure spatial alignment,
while network topology (boundary touches) enforces continuity among connected
pipes. Neighbor-based inference applies spatial autocorrelation—connected pipes
tend to share similar attributes—and fuzzy logic confidence scores (“High,”
“Medium,” “Low”) represent varying degrees of certainty in those spatial
relationships.

In essence, this is a spatial heuristic model combining vector geometry,
network connectivity, and geographic reasoning to automate pipe–street
association within a GIS environment.
--------------------------------------------------------------------------------
"""

# ---------------------------------------------------------------------------
# ENVIRONMENT SETUP
# ---------------------------------------------------------------------------

# Workspace: adjust these paths before running can run on local or sde would suggest local on most cases
gdb = r"J"
targetFcName = "HPCIPipe"
targetFc = os.path.join(gdb, targetFcName)

# Reference dataset: published street centerlines DO NOT CHANGE, unless connection file no longer exists....
streetData = r"J"

# Fields that will be used when reading the Near Table
nearFields = ['IN_FID', 'NEAR_FID', 'NEAR_DIST', 'NEAR_RANK', 'PARENT_OBJECTID', 'ORIG_Shape_length']

# Preload all street geometries into memory for fast angle comparison
streetGeom = {oid: geom for oid, geom in arcpy.da.SearchCursor(streetData, ["OBJECTID", "SHAPE@"])}

# Temporary in-memory feature classes used throughout the process | IN MEMORY OBJECT ID IS REFERENCED AS OID, IMPORTANT FOR FUTURE RUNS IF USING SIGNIFICANT IN MEMORY PROCESSES
featureMidPoints = "in_memory\\temp_FeatureMidPoints"
targetToUFDNear = "in_memory\\temp_FeatureToUFDNear"

# ---------------------------------------------------------------------------
# GEOMETRIC FUNCTION
# ---------------------------------------------------------------------------
# MATH Functions like the curbline bearing function
def getBearing(polyline):
    """
    Calculates the bearing (azimuth) of a polyline in degrees from 0–360.
    This uses trigonometric atan2(dx, dy) to determine direction and handles
    negative angles by normalizing them to a positive compass value.
    """
    start = polyline.firstPoint
    end = polyline.lastPoint
    dx = end.X - start.X
    dy = end.Y - start.Y
    angle = math.degrees(math.atan2(dx, dy))
    return angle + 360 if angle < 0 else angle



# ---------------------------------------------------------------------------
# STEP 0: SPLIT LONG PIPES INTO 400-FT SEGMENTS
# ---------------------------------------------------------------------------

# Parameters controlling how long lines are segmented
splitDistance = 400      # Length of each segment in feet
splitThreshold = 1000    # Only pipes longer than this threshold are split | CHANGE AS NEEDED

# Create a new feature class to store split (or unchanged) lines
splitBigLines = os.path.join(gdb, "temp_SplitBigLines")
if arcpy.Exists(splitBigLines):
    arcpy.management.Delete(splitBigLines)

arcpy.management.CreateFeatureclass(
    out_path=os.path.dirname(splitBigLines),
    out_name=os.path.basename(splitBigLines),
    geometry_type="POLYLINE",
    spatial_reference=arcpy.Describe(targetFc).spatialReference
)

# Add a tracking field for linking back to the original OBJECTID
arcpy.management.AddField(splitBigLines, "Target_ObjectId", "LONG")

# Read all pipes and split long ones into uniform segments
with arcpy.da.SearchCursor(targetFc, ["OBJECTID", "SHAPE@LENGTH", "SHAPE@"]) as sCursor, \
     arcpy.da.InsertCursor(splitBigLines, ["Target_ObjectId", "SHAPE@LENGTH", "SHAPE@"]) as iCursor:
    longPipe = 0
    insert = 0
    for oid, length, shape in sCursor:
        if length > splitThreshold:
            # Segment pipes into equal 400-ft pieces
            longPipe +=1
            start = 0
            while start < length:
                end = min(start + splitDistance, length)
                segment = shape.segmentAlongLine(start, end)
                # Insert segment geometry (not full shape)
                insert += 1
                iCursor.insertRow([oid, length, segment])
                start = end
        else:
            # Short pipes remain as single records
            iCursor.insertRow([oid, length, shape])

print(f"{longPipe} long pipes split into {insert} segments")

# targetFc now holds all geometries including 1000 ft + ones split to 400 ft segments after
targetFc = splitBigLines # Use the segmented version moving forward

# ---------------------------------------------------------------------------
# STEP 1: CONVERT PIPES TO MIDPOINTS AND ATTACH ATTRIBUTES
# ---------------------------------------------------------------------------

# Create midpoint features for each pipe to use in nearest-neighbor comparison
arcpy.management.FeatureVerticesToPoints(
    in_features=targetFc,
    out_feature_class=featureMidPoints,
    point_location="MID"
)

# Add fields to store shape length and later confidence results
arcpy.management.AddField(in_table = featureMidPoints,
                         field_name = "ORIG_Shape_length",
                         field_type = "DOUBLE",
                         field_precision = 9,
                         field_scale = 2,
                         field_alias = "Shape Length"
                        )

arcpy.management.AddField(in_table = featureMidPoints,
                         field_name = "Street_Match_Conf",
                         field_type = "TEXT",
                         field_length = 17,
                         field_alias = "Match Confidence"
                        )
arcpy.management.AddField(in_table = featureMidPoints,
                         field_name = "Conf_Reason",
                         field_type = "TEXT",
                         field_length = 255,
                         field_alias = "Confidence Reasons"
                        )

# Transfer pipe lengths to their midpoint features for later use
with arcpy.da.SearchCursor(targetFc, ["OBJECTID", "SHAPE@LENGTH"]) as sCursor:
    for oid, length in sCursor:
        query = f"ORIG_FID = {oid}"
        with arcpy.da.UpdateCursor(featureMidPoints, ["ORIG_Shape_length"], where_clause=query) as uCursor:
            for uVal in uCursor:
                uVal[0] = length
                uCursor.updateRow(uVal)


# IF NOT USING POLYLINE INPUT FEATURE YOU CAN START FROM HERE FOR ASSOCIATION OF ASSETS
# ---------------------------------------------------------------------------
# STEP 2: Generate Near Table (for 2 closest street centerlines)
# ---------------------------------------------------------------------------

# Compute the two closest street features for each pipe midpoint
arcpy.analysis.GenerateNearTable(
    in_features=featureMidPoints,
    near_features=streetData,
    out_table=targetToUFDNear,
    search_radius=None,
    location="NO_LOCATION",
    closest="ALL",
    closest_count=2,
    method="PLANAR",
    distance_unit="Feet"
)

# Add parent pipe ID and shape length fields for data integrity
arcpy.management.AddField(in_table = targetToUFDNear,
                         field_name = "Parent_ObjectId",
                         field_type = "Long",
                         field_alias = "Parent Object ID"
                        )

arcpy.management.AddField(in_table = targetToUFDNear,
                         field_name = "ORIG_Shape_length",
                         field_type = "DOUBLE",
                         field_precision = 9,
                         field_scale = 2,
                         field_alias = "Shape Length"
                        )

# Push Target_ObjectId and pipe length from midpoint to near table
with arcpy.da.SearchCursor(featureMidPoints, ["OBJECTID", "Target_ObjectId", "ORIG_Shape_length"]) as sCursor:
    for oid, parent, length in sCursor:
        query = f"IN_FID = {oid}"
        with arcpy.da.UpdateCursor(targetToUFDNear, ["Parent_ObjectId", "ORIG_Shape_length"], where_clause=query) as uCursor:
            for uVal in uCursor:
                uVal[0] = parent
                uVal[1] = length
                uCursor.updateRow(uVal)

# ---------------------------------------------------------------------------
# STEP 3: BUILD NEAR DICTIONARY (IN-MEMORY RELATIONSHIPS)
# ---------------------------------------------------------------------------

# Convert the near table into a Python dictionary for quick lookups
nearDict = defaultdict(list)
with arcpy.da.SearchCursor(targetToUFDNear, nearFields) as cursor:
    for in_fid, near_fid, near_dist, near_rank, parent_oid, pipe_length in cursor:
        nearDict[int(in_fid)].append({
            "NEAR_FID": int(near_fid),
            "NEAR_DIST": round(near_dist, 2),
            "NEAR_RANK": int(near_rank),
            "Parent_ObjectId": parent_oid,
            "ORIG_Shape_length": round(pipe_length, 2)
        })


# ---------------------------------------------------------------------------
# STEP 4: ANGLE COMPARISON AND INITIAL CONFIDENCE CLASSIFICATION
# ---------------------------------------------------------------------------

# Cache pipe geometries for fast access
targetGeom = {oid: geom for oid, geom in arcpy.da.SearchCursor(targetFc, ["OBJECTID", "SHAPE@"])}


# Calculate angular differences between each pipe and its two nearest streets
for inFid, nearList in nearDict.items():
    with arcpy.da.SearchCursor(featureMidPoints, ["OBJECTID", "Target_ObjectId"]) as midCursor:
        for midOid, parentId in midCursor:
            if midOid == inFid:
                pipeId = parentId
                break
        else:
            continue

    target = targetGeom.get(inFid)
    if not target:
        print("No pipe geometry found.")
        continue

    pipeAngle = getBearing(target)
    for n in nearList:
        street = streetGeom.get(n["NEAR_FID"])
        if not street:
            continue
        diff = abs(pipeAngle - getBearing(street))
        if diff > 180:
            diff = 360 - diff # Normalize angular difference (0–180)
        n["ANGLE_DIFF"] = round(diff, 2)

# Define tolerances for classifying spatial similarity
ParallelTol = 10       # Max angular difference for “parallel” lines
MinLenForFarther = 34  # Minimum pipe length for reliable farther matches

# Make a temporary layer for later topological operations
selectingPipeLayer = "temp_SelectingPipeLayer"
arcpy.management.MakeFeatureLayer(targetFc, selectingPipeLayer)

# Loop through all pipes and assign confidence based on distance + angle rules
for pipeId, nearList in nearDict.items():
   # Identify the closest and farther streets
    n1, n2 = nearList[0], nearList[1]
    closest, farther = (n1, n2) if n1["NEAR_DIST"] <= n2["NEAR_DIST"] else (n2, n1)

    # Compute parallel difference (0–180) for closest
    closestDiff = min(closest["ANGLE_DIFF"], 180 - closest["ANGLE_DIFF"])
    fartherDiff = min(farther["ANGLE_DIFF"], 180 - farther["ANGLE_DIFF"])
    perpendSecondNear = abs(90 - farther["ANGLE_DIFF"]) <= 10
    pipeSize = closest["ORIG_Shape_length"]

    # Classification logic for initial confidence
    if closestDiff <= ParallelTol and pipeSize > 5:

        # Closest street is parallel and reasonable size → High confidence
        closest["Match Confidence"] = "High Confidence"
        closest["Confidence Reasons"] = "Angle and Distance checked"
        nearDict[pipeId] = [closest]

    # If the second-closest (farther) street is still roughly parallel to the pipe (within 10°),
    # the pipe is a normal-sized main (>5 ft), NOT near a perpendicular crossing,
    # and is long enough (≥34 ft) to make the match reliable,
    # then assume this farther street is the correct one and mark it as
    elif fartherDiff <= ParallelTol and pipeSize > 5 and not perpendSecondNear and pipeSize >= MinLenForFarther:

        # Farther street also fits geometric tolerance → High confidence
        farther["Match Confidence"] = "High Confidence"
        farther["Confidence Reasons"] = "Farther street within angle tolerance, possible intersection on first near result"
        nearDict[pipeId] = [farther]

    else:
        # Keep both for neighbor-based refinement
        for n in (closest, farther):
            n["Match Confidence"] = ""
            n["Confidence Reasons"] = ""
        nearDict[pipeId] = [closest, farther]

# ---------------------------------------------------------------------------
# STAT BREAK AFTER INITIAL ANALYSIS
# ---------------------------------------------------------------------------
lowConfidenceCount = 0
mediumConfidenceCount = 0
highConfidenceCount = 0
for pipeId, nearList in nearDict.items():
    # print(f"ORIGINAL PIPE ID: {pipeId}")
    for n in nearList:
        # print(f"\t{n}")
        if n.get("Match Confidence") == "Low Confidence":
            lowConfidenceCount += 1
        if n.get("Match Confidence") == "Medium Confidence":
            mediumConfidenceCount += 1
        if n.get("Match Confidence") == "High Confidence":
            highConfidenceCount += 1

print(f"Number of high-confidence records: {highConfidenceCount}")
print(f"Number of medium-confidence records: {mediumConfidenceCount}")
print(f"Number of low-confidence records: {lowConfidenceCount}")


# ---------------------------------------------------------------------------
# STEP 5: TOPOLOGICAL NEIGHBOR DETECTION (PIPE–PIPE TOUCHING RELATIONSHIPS)
# ---------------------------------------------------------------------------

neighborCandidates = list(nearDict.keys())
neighborPipeLayer = "temp_PipeLayer"
arcpy.management.MakeFeatureLayer(targetFc, neighborPipeLayer)
pipeNeighbors = {}

# For each pipe, identify all other pipes that touch its endpoints
for pipeId in neighborCandidates:
    # Select the current pipe in selectingLayer (the "driver")
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view = selectingPipeLayer,
        selection_type = "NEW_SELECTION",
        where_clause = f"OBJECTID = {pipeId}"
    )


    neighbors = []
    # Select any pipes that touch the current one’s endpoints
    arcpy.management.SelectLayerByLocation(
        in_layer = neighborPipeLayer,
        overlap_type = "BOUNDARY_TOUCHES",
        select_features = selectingPipeLayer,
        selection_type = "NEW_SELECTION"
    )

    # Collect the OBJECTIDs of touching pipes
    with arcpy.da.SearchCursor(neighborPipeLayer, ["OBJECTID"]) as cursor:
        for (oid,) in cursor:
            if oid != pipeId and oid not in neighbors:
                neighbors.append(oid)

    # Clear selections for next iteration
    arcpy.management.SelectLayerByAttribute(neighborPipeLayer, "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(selectingPipeLayer, "CLEAR_SELECTION")

    pipeNeighbors[pipeId] = neighbors

print(f"Neighbor relationships established for {len(pipeNeighbors)} pipes.")


# ---------------------------------------------------------------------------
# STEP 6: NEIGHBOR-BASED REFINEMENT OF CONFIDENCE SCORES
# ---------------------------------------------------------------------------

# Build quick lookups for lengths and street names
pipeLength = {oid: length for oid, length in arcpy.da.SearchCursor(targetFc, ["OBJECTID", "SHAPE@LENGTH"])}
streetNames = {oid: stName for oid, stName in arcpy.da.SearchCursor(streetData, ["OBJECTID", "stname"])}

# Assign weights to convert confidence categories to numeric comparison
CONFIDENCE_WEIGHT = {"High Confidence": 3, "Medium Confidence": 2, "Low Confidence": 1, "": 0}

# Evaluate each pipe relative to its neighboring pipes
for pipeId, neighbors in pipeNeighbors.items():
    if pipeId not in nearDict or not nearDict[pipeId]:
        continue

    currentRecord = nearDict[pipeId][0]
    currentPick = currentRecord.get("NEAR_FID")
    currentConf = currentRecord.get("Match Confidence", "")
    currentName = streetNames.get(currentPick, "")

    # Skip pipes already classified with a confidence value
    if currentConf not in ("", None):
        continue

    # --- Pipes with TWO or more neighbors ---
    if len(neighbors) >= 2:
        n1, n2 = neighbors[:2]
        n1Rec = nearDict.get(n1, [{}])[0]
        n2Rec = nearDict.get(n2, [{}])[0]

        n1Pick, n2Pick = n1Rec.get("NEAR_FID"), n2Rec.get("NEAR_FID")
        n1Conf, n2Conf = n1Rec.get("Match Confidence", ""), n2Rec.get("Match Confidence", "")
        n1Name, n2Name = streetNames.get(n1Pick, ""), streetNames.get(n2Pick, "")

        # CASE 1: Both neighbors share same match → adopt with higher certainty
        # Logic:
        #   - If both adjacent pipes are tied to the same street segment (NEAR_FID),
        #     this suggests strong local consistency.
        #   - If this pipe also matches that same street, it’s confirmed as
        #     “High Confidence.” Otherwise, it adopts their street ID with
        #     Medium/High confidence depending on their certainty levels.
        if n1Pick == n2Pick and n1Pick is not None:

            # Subcase: this pipe already matches the same street → confirm
            if currentPick == n1Pick:
                currentRecord["Match Confidence"] = "High Confidence"
                currentRecord["Confidence Reasons"] = "Both neighbors share same pick"
            else:
                # Subcase: both neighbors are confident → trust their shared pick fully
                if n1Conf == "High Confidence" and n2Conf == "High Confidence":
                    currentRecord["NEAR_FID"] = n1Pick
                    currentRecord["Match Confidence"] = "High Confidence"
                    currentRecord["Confidence Reasons"] = (
                        "Adopted same street as two High-Confidence neighbors"
                    )
                # Subcase: shared neighbor pick but not both high → mark as Medium
                else:
                    currentRecord["NEAR_FID"] = n1Pick
                    currentRecord["Match Confidence"] = "Medium Confidence"
                    currentRecord["Confidence Reasons"] = (
                        "Adopted shared neighbor pick; perform manual check"
                    )

        # CASE 2: Neighbors disagree → infer based on confidence or name continuity
        # Logic:
        #   - This situation is ambiguous: adjacent pipes disagree on which
        #     street they belong to. The algorithm uses a hierarchy of cues:
        #       1. Does this pipe agree with one neighbor?
        #       2. Which neighbor is more confident (weighted inference)?
        #       3. Do street names indicate continuity (same street name)?
        #       4. Else → leave as Low Confidence (manual review)
        else:
            # If this pipe already matches one neighbor’s street, it’s likely valid
            if currentPick in (n1Pick, n2Pick):
                currentRecord["Match Confidence"] = "Medium Confidence"
                currentRecord["Confidence Reasons"] = "This pipe matches one neighbor’s pick; perform manual check"

            # Prefer the neighbor with stronger confidence weighting
            elif CONFIDENCE_WEIGHT[n1Conf] > CONFIDENCE_WEIGHT[n2Conf]:
                currentRecord["NEAR_FID"] = n1Pick
                currentRecord["Match Confidence"] = "Medium Confidence"
                currentRecord["Confidence Reasons"] = (
                    f"Adopted higher-confidence neighbor {n1} ({n1Conf}) pick"
                )

            elif CONFIDENCE_WEIGHT[n2Conf] > CONFIDENCE_WEIGHT[n1Conf]:
                currentRecord["NEAR_FID"] = n2Pick
                currentRecord["Match Confidence"] = "Medium Confidence"
                currentRecord["Confidence Reasons"] = (
                    f"Adopted higher-confidence neighbor {n2} ({n2Conf}) pick"
                )

            # Street name continuity test:
            # If this pipe’s current street name matches either neighbor’s street name,
            # we assume linear continuation along the same named corridor.
            elif currentName and (currentName == n1Name or currentName == n2Name):
                currentRecord["Match Confidence"] = "Medium Confidence"
                currentRecord["Confidence Reasons"] = (
                    "Street name continuity with neighbor; likely same street alignment"
                )

            # If both neighbors share the same street name, even if different FIDs,
            # treat that as a strong hint of shared alignment (e.g., split street segment)
            elif n1Name and n1Name == n2Name:
                adopted_pick = n1Pick if n1Name == n2Name else None
                if adopted_pick:
                    currentRecord["NEAR_FID"] = adopted_pick
                    currentRecord["Match Confidence"] = "Medium Confidence"
                    currentRecord["Confidence Reasons"] = (
                        f"Both neighbors share same street name ({n1Name}); adopted their street match"
                    )
                else:
                    currentRecord["Match Confidence"] = "Low Confidence"
                    currentRecord["Confidence Reasons"] = "Neighbors have different street names; perform manual check"

            # None of the above heuristics apply → unresolved ambiguity
            else:
                currentRecord["Match Confidence"] = "Low Confidence"
                currentRecord["Confidence Reasons"] = (
                    "Neighbors have different picks and street names; perform manual check"
                )

    # --- Pipes with ONE neighbor ---
    elif len(neighbors) == 1:
        n1 = neighbors[0][0] if isinstance(neighbors[0], tuple) else neighbors[0]
        n1Rec = nearDict.get(n1, [{}])[0]
        n1Pick = n1Rec.get("NEAR_FID")
        n1Conf = n1Rec.get("Match Confidence", "")
        n1Name = streetNames.get(n1Pick, "")
        currentName = streetNames.get(currentPick, "")

        # Subcase: identical street ID → strong local continuity
        if currentPick == n1Pick:
            currentRecord["Match Confidence"] = "High Confidence"
            currentRecord["Confidence Reasons"] = "Single neighbor shares same pick"

        # Subcase: neighbor is High Confidence → adopt its street match
        elif n1Conf == "High Confidence":
            currentRecord["NEAR_FID"] = n1Pick
            currentRecord["Match Confidence"] = "High Confidence"
            currentRecord["Confidence Reasons"] = (
                f"Adopted High-Confidence neighbor ({n1}) pick"
            )

        # Subcase: different FIDs but identical street names → probably same corridor
        elif currentName and currentName == n1Name:
            currentRecord["Match Confidence"] = "High Confidence"
            currentRecord["Confidence Reasons"] = (
                f"Single neighbor on same street name ({currentName.title()}); likely continuation"
            )

        # Subcase: none of the above → uncertain relationship
        else:
            # Otherwise, low confidence — neighboring street mismatch
            currentRecord["Match Confidence"] = "Low Confidence"
            currentRecord["Confidence Reasons"] = (
                "Single neighbor with different street name; perform manual check"
            )

    # --- Pipes with NO neighbors ---
    else:
        # Pipes that touch no others can’t inherit or validate their street match.
        # These remain Low Confidence by default and are flagged for manual review.
        currentRecord["Match Confidence"] = "Low Confidence"
        currentRecord["Confidence Reasons"] = "No neighbors found; perform manual check"

    # ---- Short-pipe fallback correction ----
    # Logic:
    #   - Very short segments (<10 ft) may represent short connectors or offsets.
    #   - If such a pipe was left as "Low Confidence" but directly touches a
    #     neighbor that has "High Confidence," we let it adopt that neighbor’s
    #     match with Medium Confidence — a practical spatial inference rule.
    pipe_len = pipeLength.get(pipeId, 0)
    if currentRecord["Match Confidence"] == "Low Confidence" and pipe_len < 10:
        for n in neighbors:
            n_id = n[0] if isinstance(n, tuple) else n
            if n_id not in nearDict or not nearDict[n_id]:
                continue
            n_rec = nearDict[n_id][0]
            n_conf = n_rec.get("Match Confidence", "")
            n_len = pipeLength.get(n_id, 0)

            # Neighbor is confident → adopt its street assignment
            if n_conf == "High Confidence":
                currentRecord["NEAR_FID"] = n_rec.get("NEAR_FID")
                currentRecord["Match Confidence"] = "Medium Confidence"
                currentRecord["Confidence Reasons"] = (
                    f"Short pipe (<10 ft) adopted High-Confidence neighbor {n_id}"
                )
                break

    nearDict[pipeId] = [currentRecord]

# ---------------------------------------------------------------------------
# STAT BREAK AFTER FULL ANALYSIS
# ---------------------------------------------------------------------------

lowConfidenceCount = 0
mediumConfidenceCount = 0
highConfidenceCount = 0
for pipeId, nearList in nearDict.items():
    # print(f"ORIGINAL PIPE ID: {pipeId}")
    for n in nearList:
        # print(f"\t{n}")
        if n.get("Match Confidence") == "Low Confidence":
            lowConfidenceCount += 1
        if n.get("Match Confidence") == "Medium Confidence":
            mediumConfidenceCount += 1
        if n.get("Match Confidence") == "High Confidence":
            highConfidenceCount += 1

print(f"Number of high-confidence records: {highConfidenceCount}")
print(f"Number of medium-confidence records: {mediumConfidenceCount}")
print(f"Number of low-confidence records: {lowConfidenceCount}")

# ---------------------------------------------------------------------------
# STEP 8: EXPORT RESULTS TO TABLES FOR GIS REVIEW
# ---------------------------------------------------------------------------

# Create a many-to-one results table for detailed review
outTable = os.path.join(gdb, "UDFMatchResults")
if arcpy.Exists(outTable):
    arcpy.management.Delete(outTable)
arcpy.management.CreateTable(gdb, "UDFMatchResults")


# Add fields to store parent pipe, street match, and confidence
fields = [
    ("Parent_ObjectId", "LONG"),
    ("UFD_ObjectId", "LONG"),
    ("Match_Confidence", "TEXT", 50),
    ("Confidence_Reasons", "TEXT", 255)
]

for name, ftype, *rest in fields:
    length = rest[0] if rest else None
    if length:
        arcpy.management.AddField(outTable, name, ftype, field_length=length)
    else:
        arcpy.management.AddField(outTable, name, ftype)

# Write classified results from memory to the permanent output table
with arcpy.da.InsertCursor(outTable, ["Parent_ObjectId", "UFD_ObjectId", "Match_Confidence", "Confidence_Reasons"]) as cursor:
    for pipeId, recList in nearDict.items():
        if not recList:
            continue
        rec = recList[0]
        cursor.insertRow([
            rec.get("Parent_ObjectId"),
            rec.get("NEAR_FID"),
            rec.get("Match Confidence", ""),
            rec.get("Confidence Reasons", "")
        ])

print(f"Many to one table created for street match review: {outTable}")

# ---------------------------------------------------------------------------
# STEP 9: CREATE MANY-TO-MANY SUMMARY TABLE FOR GIS USE
# ---------------------------------------------------------------------------

summaryTable = os.path.join(gdb, "UDFMatchResults_Summary")
# Recreate the table to ensure a clean start
if arcpy.Exists(summaryTable):
    arcpy.management.Delete(summaryTable)
# Create a new table to store summarized street data
arcpy.management.CreateTable(gdb, "UDFMatchResults_Summary")

# Add fields
fields = [
    ("Target_ObjectId", "LONG"),
    ("UFD_ObjectId", "LONG"),
    ("l_hundred", "LONG"),
    ("stname", "TEXT", 100),
    ("Match_Confidence", "TEXT", 50),
    ("Confidence_Reasons", "TEXT", 255)
]
for name, ftype, *rest in fields:
    length = rest[0] if rest else None
    if length:
        arcpy.management.AddField(summaryTable, name, ftype, field_length=length)
    else:
        arcpy.management.AddField(summaryTable, name, ftype)

# Build a lookup of street IDs to their attributes for quick joining
streetLookup = {
    oid: (hundred, name)
    for oid, hundred, name in arcpy.da.SearchCursor(streetData, ["OBJECTID", "l_hundred", "stname"])
}


# Write pipe–street relationships into the summary table
with arcpy.da.InsertCursor(
    summaryTable,
    ["Target_ObjectId", "UFD_ObjectId", "l_hundred", "stname", "Match_Confidence", "Confidence_Reasons"]
) as iCursor:
    with arcpy.da.SearchCursor(
        outTable,
        ["Parent_ObjectId", "UFD_ObjectId", "Match_Confidence", "Confidence_Reasons"]
    ) as sCursor:
        for parent, ufd, conf, reason in sCursor:
            if parent is None or ufd is None:
                continue
            hundred, name = streetLookup.get(ufd, (None, None))
            iCursor.insertRow([parent, ufd, hundred, name, conf, reason])

print(f"Many-to-many table created for GIS: {summaryTable}")

# ---------------------------------------------------------------------------
# STEP 10: CREATE DEDUPLICATED REFERENCE TABLE OF UNIQUE STREET COMBINATIONS
# ---------------------------------------------------------------------------

uniqueStreetTable = os.path.join(gdb, "Unique_StreetCombinations")
# Clean existing table if it exists
if arcpy.Exists(uniqueStreetTable):
    arcpy.management.Delete(uniqueStreetTable)
# Create the new table
arcpy.management.CreateTable(gdb, "Unique_StreetCombinations")

# Create table to hold distinct l_hundred–stname pairs
arcpy.management.AddField(uniqueStreetTable, "l_hundred", "LONG")
arcpy.management.AddField(uniqueStreetTable, "stname", "TEXT", field_length=100)

# Extract and store unique street references for operational use
unique_pairs = set()
with arcpy.da.SearchCursor(summaryTable, ["l_hundred", "stname"]) as sCursor:
    for hundred, name in sCursor:
        if hundred is not None or (name and name.strip()):
            unique_pairs.add((hundred, name.strip() if name else None))

# Insert unique pairs into the new table
with arcpy.da.InsertCursor(uniqueStreetTable, ["l_hundred", "stname"]) as iCursor:
    for hundred, name in sorted(unique_pairs, key=lambda x: (x[1] or "", x[0] or 0)):
        iCursor.insertRow([hundred, name])

print(f"Unique street combination table created for Operations: {uniqueStreetTable}")
print(f"Total unique l_hundred–stname pairs: {len(unique_pairs)}")
print("--------------------------------------------------------------------------")
print("PROCESS COMPLETE — All pipe–street association tables successfully created.")
print("--------------------------------------------------------------------------")
