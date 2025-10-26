#Script developed by Morgan Ryan

#Script Start date 12/01/22
#Script finish date 12/02/22

from arcgis.gis import GIS
import pandas as pd
from pathlib import Path
import os, shutil

# Log in to portal; prompts for PW automatically
prod = GIS()
cat = GIS()
partner = GIS()
dev = GIS()
gisenvlist = [prod, cat, partner, dev]
db = "type:'dashboard' OR typeKeywords:'Operations Dashboard' OR typeKeywords:'ArcGIS Dashboards'"
sm = "type:'StoryMap' OR typeKeywords:'StoryMap' OR typeKeywords:'Web Application'"
wab = "type:'Web AppBuilder Widget' OR typeKeywords:'Web AppBuilder' OR typeKeywords:'Widget'"
wemp = "typeKeywords:'Map' OR typeKeywords:'Web Map'"


output_directory = input("Output directory: ")
feattype = str(input("What type of application are you looking for:(sm, db, wab, or wemp) "))
app_query = [db, sm, wab, wemp]

if feattype == "db":
    app = 'Dashboard'
    app_query = app_query[0]
elif feattype =="sm":
    app = 'Story_Map'
    app_query = app_query[1]
elif feattype =="wab":
    app = 'Web_App_Builder'
    app_query = app_query[2]
elif feattype =="wemp":
    app = 'Web_Map'
    app_query = app_query[3]



#clearing out the current folder
folder = output_directory
for filename in os.listdir(folder):
    file_path = os.path.join(folder, filename)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print('Failed to delete %s. Reason: %s' % (file_path, e))

print("PORTAL LOOP STARTED")
for gis in gisenvlist:
    print('gis connected')
    # Layer ID to search for and its URL
    #edidted to make easy

    # Pull list of all web apps in portal
    webapps = gis.content.search(query = app_query , max_items=-1, sort_field = 'updated', sort_order = 'desc')
    print('searching for applications')
    # Create empty list to populate with results
    app_list = []

    # Check each web app for matches
    for w in webapps:
    
        try:
        # Get the JSON as a string
            wdata = str(w.get_data())
            app_list.append(w)
    
    # Some apps don't have data, so we'll just skip them if they throw a TypeError
        except:
            continue
    #creating naming convention for the files based off of the portal environment used. 
    if gis is prod:
            name = 'PRODUCTION'
    if gis is cat:
            name = 'CAT'
    if gis is dev:
            name = 'DEV'
    if gis is partner:
            name = 'PARTNER'
    print('turning into data frame')
    #creates a path, file type and name for each output
    output_prod_name = name + '_' + app
    output_prod_name_csv = output_prod_name + ".csv"
    Location = output_directory +"\\"+ output_prod_name_csv
    
    #converts each dataframe to a variable named output
    output = pd.DataFrame([{'Title':a.title,'Type':a.type, 'Owner':a.owner,'URL':f'{gis.url}home/item.html?id={a.id}', 'Size':a.size} for a in app_list])
    #Filter records where owner value contains substring "esri"
    filt_esri = output[output['Owner'].str.contains("esri")]
    output.drop(filt_esri.index, inplace=True)
    #transforms eachoutput to a CSV file 
    output.to_csv(Location)
    print('data from from portals turned into CSVs')
print("PORTAL LOOP FINISHED")

#This loop checks each csv and if empty removes it. This will help us identify which portals we need to focus on!
print("LOOP TO REMOVE EMPTY DATA STARTED")
for file in Path(output_directory).glob('*.csv'):
    df = pd.read_csv(file)
    if df.empty is True:
        os.remove(file)
print("LOOP TO REMOVE EMPTY DATA FINISHED")
