#Started 12/29/22 Morgan Ryan
#Finished 01/05/23 Morgan Ryan
#This script checks out the street map premium extension and runs the locator.
#The tool ensures that users no longer need to check out and check in the extension before using the locator for geocoding.

import pandas as pd
import arcpy
import os
from pathlib import Path
#Definging the user input table for the script tool.
Table = arcpy.GetParameterAsText(0)

#Turning the file path to a string for the logic portion of the script (The function does not recognize the filepath if it is run without this.)
t = Path(Table)
fpath = t.parent
#Writing temp files.
temp = r"C:\Temp\temp.csv"

#The locator file.
Loc = r""

#Adds the script tool output to the document it was run in.
arcpy.env.addOutputsToMap = True
arcpy.EnvManager(outputCoordinateSystem='PROJCS["NAD_1983_StatePlane_Nebraska_FIPS_2600_Feet",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",1640416.666666667],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-100.0],PARAMETER["Standard_Parallel_1",40.0],PARAMETER["Standard_Parallel_2",43.0],PARAMETER["Latitude_Of_Origin",39.83333333333334],UNIT["Foot_US",0.3048006096012192]]')

#A class which states that if an exception is recorded when the License error function is started it will skip down to the except.
class LicenseError(Exception):
        pass

#The function that comprises the script.
try:
        #Checking to see if the street map premium extension is available and checking it out if it is.
        if arcpy.CheckExtension("SMPNorthAmerica") == "Available":
                arcpy.CheckOutExtension("SMPNorthAmerica")
                arcpy.AddMessage("Street Map Premium extension checked out successfully.")

        #License error which causes the pass if the license is unavailable.
        else:
                raise LicenseError
        try:
                #Logic test which checks to see what extension the table uses.
                if Table.endswith('.csv'):

                        #If the table ends with csv xlsx or xls the table will be turned into a df variable named 'results'.
                        results = pd.read_csv(Table, index_col = [0])

                        #Turns the results table into a string for easier data processing (the entire table is turned to a string because we cannot predict what the column names will be each time.)
                        results = results.applymap(str)
                        message = arcpy.AddMessage('CSV read.')

                #Same logic test till the 'else:' portion.
                elif Table.endswith('.xlsx') or Table.endswith('$') or Table.endswith('_'):
                        
                        results = pd.read_excel(fpath, index_col = [0])
                        results = results.applymap(str)
                        message = arcpy.AddMessage('XLSX read.')

                elif Table.endswith('.xls') or Table.endswith('$') or Table.endswith('_'):
                        
                        results = pd.read_excel(fpath, index_col = [0])
                        results = results.applymap(str)
                        message = arcpy.AddMessage('XLS read.')

                #Final part of the first logic test which states that if the file does not end with one of the identified extensions the script tool will end because the geocoder will not run correctly.
                else:
                        arcpy.AddError("Please use CSV, XLSX, or XLS file types.")
                        exit()

                #Second logic test which states that if there are more than 100,000 records the tool will end because it would take too much time to run. We are trying to limit individuals from having the extension checked out for long periods of time.
                if len(results) > 1500000:
                        arcpy.AddError('There are too many records to process please use a smaller list.')
                        exit()

                #If the table is smaller than 100,000 records the script continues.
                else:
                        pass

                #Data cleaning based off of user input to get a concise single field to use as an address.
                street = results[arcpy.GetParameterAsText(1)]
                city = results[arcpy.GetParameterAsText(2)]
                state = results[arcpy.GetParameterAsText(3)]
                zip_c = results[arcpy.GetParameterAsText(4)]
                results['full_address'] = street + ', ' + city + ', ' + state + ', ' + zip_c
                arcpy.AddMessage("Full street address created from input table.")

                #Exporting the results table with the new field full address to be used by geocoder.
                results.to_csv(temp, index = [0])


                #The final user input which is a feature class created by the end user.
                lyr = arcpy.GetParameterAsText(5)

                #Tool Syntax
                #arcpy.geocoding.GeocodeAddresses(in_table, address_locator, in_address_fields, out_feature_class, {out_relationship_type}, {country}, {location_type}, {category}, {output_fields})
                arcpy.geocoding.GeocodeAddresses(temp, Loc,"'Single Line Input' full_address VISIBLE NONE", lyr, output_fields="MINIMAL" ) 
                arcpy.AddMessage("Geocoding complete.")

                if os.path.exists(temp): #checking to see if it already exists
                        os.remove(temp)
        except Exception as e:
                arcpy.CheckInExtension("SMPNorthAmerica")
                arcpy.AddMessage("Street Map Premium extension checked in successfully.")


        
        #Checking the extension back in for the next use.
        arcpy.CheckInExtension("SMPNorthAmerica")
        arcpy.AddMessage("Street Map Premium extension checked in successfully.")

#The exception that causes the tool to end without running if the extension is not available.
except LicenseError:
        arcpy.AddError("The Street Map Premium extension is currently unavailable, please try again later.")
        arcpy.AddMessage("Street Map Premium extension checked in successfully.")

#This just states that the extension is unavailable using esri verbage.
except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessage(2))
