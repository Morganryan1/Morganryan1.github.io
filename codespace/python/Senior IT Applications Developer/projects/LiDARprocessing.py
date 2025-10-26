#Script created to process county LiDAR data sets
#Script started by Morgan Ryan on 1/09/23
#Script finished by Morgan Ryan on 1/10/23
#Any edits should be recorded here
#Added spatial analyst ext so that the tool can run in the background and the in memory processing of inital meter to state plane reprojection


#########################################################################################################
#                                        Libraries and variables                                        #
#                                                                                                       #
#########################################################################################################
#Libraries 
import os, shutil, arcpy
from pathlib import Path

#raster User input
rast = arcpy.GetParameterAsText(0)

#inital directory which is user input
inital_directory = arcpy.GetParameterAsText(1)
memory = r'memory'
arcpy.env.workspace = inital_directory

#This makes the variable strings more readable (in my opinion)
fsl = '\\'
#Raster file and path information
path = Path(rast)
#raster name
raste = path.stem
#if data set is in geodatabase this is the parent name
gdb_dir = path.parent
#if data is in geodatabase this is raster name
gdb_nm = gdb_dir.stem
#if outside of geodatabase this will be the raster name used for logic 
raster_name = gdb_nm + raste


#taking the prior variable and removing _DEM_mtrs if it exits within the .img string.
if 'dem_meters_ne' in raster_name:
    raster_name = gdb_nm 
    
elif '_DEM_mtrs' in raster_name:
    raster_name = raste
    raster_name = raster_name.replace("_DEM_mtrs", "")
    

elif '_DEM_meters' in raster_name:
    raster_name = raste
    raster_name = raster_name.replace("_DEM_meters", "")

else:
    raster_name = raste
    arcpy.AddMessage(f"Please change {raster_name} to the appropriate format EG: 'TEST_County'")
    pass

#directory created for Lidar dataset inside initial directory
Lidar_directory = inital_directory + fsl + raster_name + '_County'


#Arcpy tool variables
projpth = memory + fsl + raster_name + '_' + 'DEM_StatePlane_mtrs.img'
calcpth = Lidar_directory + fsl + raster_name + '_' + 'DEM_StatePlane_ft.img'
inital_rast = Path(projpth)
final_rast = Path(calcpth)
#########################################################################################################
#                                        Folder formatting portion                                      #
#                                                                                                       #
#########################################################################################################
#folder variables

#path to the new LiDAR directory 
Fpath = Path(Lidar_directory)


#if there is no folder with NAME_County this creates a new one
if not os.path.exists(Lidar_directory):
    os.makedirs(Lidar_directory)
    arcpy.AddMessage(f"{raster_name}_County folder created in {Fpath.parent}")

#This else statement places old data in a folder before new data is created in the original NAME_County folder
else:

#Loop to copy old data to old folder
    file_names = os.listdir(Lidar_directory)
    os.makedirs(Lidar_directory + fsl + raster_name + '_Old_Data_Change_Name')
    target_dir = Lidar_directory + fsl + raster_name + '_Old_Data_Change_Name'
    tgt_dir_path = Path(target_dir)
    for file_name in file_names:
        shutil.move(os.path.join(Lidar_directory, file_name), target_dir)
    arcpy.AddMessage(f"{tgt_dir_path.stem} directory created and {file_names} stored inside")

#########################################################################################################
#                                       Arcgis Data transformation                                      #
#                                                                                                       #
#########################################################################################################
ext = "Spatial"
arcpy.CheckOutExtension(ext)
arcpy.AddMessage(f"{ext} analyst extension checked out.")


#Projecting raster from meters to state plane
#TOOL SYNTAX: arcpy.management.ProjectRaster(in_raster, out_raster, out_coor_system, {geographic_transform}, {resampling_type}, {cell_size})
with arcpy.EnvManager(parallelProcessingFactor= "100%", outputCoordinateSystem='PROJCS["NAD_1983_StatePlane_Nebraska_FIPS_2600_Feet",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",1640416.666666667],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-100.0],PARAMETER["Standard_Parallel_1",40.0],PARAMETER["Standard_Parallel_2",43.0],PARAMETER["Latitude_Of_Origin",39.83333333333334],UNIT["Foot_US",0.3048006096012192]]', resamplingMethod="BILINEAR", pyramid="PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP NO_SIPS"):
    arcpy.management.ProjectRaster(rast, projpth, 'PROJCS["NAD_1983_StatePlane_Nebraska_FIPS_2600_Feet",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",1640416.666666667],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-100.0],PARAMETER["Standard_Parallel_1",40.0],PARAMETER["Standard_Parallel_2",43.0],PARAMETER["Latitude_Of_Origin",39.83333333333334],UNIT["Foot_US",0.3048006096012192]]', "BILINEAR", "3.28083333333333 3.28083333333333", "'WGS_1984_(ITRF08)_To_NAD_1983_2011 + WGS_1984_(ITRF00)_To_NAD_1983'", None, 'PROJCS["NAD_1983_2011_UTM_Zone_14N",GEOGCS["GCS_NAD_1983_2011",DATUM["D_NAD_1983_2011",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-99.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]', "NO_VERTICAL")
arcpy.AddMessage(f"{path.name} has been reprojected to state plane.")


#Changing the raster values from meters to feet
#TOOL SYNTAX: arcpy.sa.Times(input raster, constant value)
#The use of the tool is listed as a variable out raster 
#The out_raster variable is saved as calcpth which is a path created from prior script variables 
out_raster = arcpy.sa.Times(projpth, 3.2808399)
out_raster.save(calcpth)
arcpy.AddMessage(f"{inital_rast.stem} raster values have been converted from meters to feet.") 
arcpy.AddMessage(f"The output raster has been saved as {calcpth}")


#Building pyramids to improve performance of raster
#TOOL SYNTAX: arcpy.BuildPyramids_management(in_raster_dataset, {resample_technique}, {compression_type})
with arcpy.EnvManager(parallelProcessingFactor="100%", pyramid="PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP NO_SIPS"):
    arcpy.management.BuildPyramids(calcpth , -1, "NONE", "BILINEAR", "DEFAULT", 75, "OVERWRITE")
arcpy.AddMessage(f"Pyramids have been built for {final_rast.stem}")

#TOOL SYNTAX: arcpy.management.CalculateStatistics(in_raster_dataset, {x_skip_factor}, {y_skip_factor}, {ignore_values}, {area_of_interest})
arcpy.management.CalculateStatistics(calcpth, 1, 1, [], "OVERWRITE", r"in_memory\feature_set1")
arcpy.AddMessage(f"Statistics have been calculated for {final_rast.stem}")
arcpy.CheckInExtension(ext)
arcpy.AddMessage(f"{ext} analyst extension checked in.")

#########################################################################################################
#                                          THE END OF THE SCRIPT :)                                     #
#                                                                                                       #
#########################################################################################################
