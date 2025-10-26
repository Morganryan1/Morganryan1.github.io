#Script developed by Morgan Ryan
#based from script found https://community.esri.com/t5/arcgis-online-questions/possible-to-find-out-where-feature-layers-are/td-p/1142174
#Script Start date 03/15/23
#Script finish date 03/15/23
#NEVER EDIT THIS FILE, EXECUTE IT AND THEN INPUT INFORMATION IN TERMINAL.
from arcgis.gis import GIS
import pandas as pd
from pathlib import Path
import os, shutil

# Log in to portal; prompts for PW automatically
prod = GIS("PORTAL", "USERNAME", "PASSWORDS")
cat = GIS("PORTAL", "USERNAME", "PASSWORDS")
partner = GIS("PORTAL", "USERNAME", "PASSWORDS")
dev = GIS("PORTAL", "USERNAME", "PASSWORDS")
gisenvlist = [prod, cat, partner, dev]


output_directory = input("Output directory: ")
n = input("Owner Email: ")
n = n.lower()
na = n.replace('.','_')
nam = na.split('@')
Uname = nam[0]


print("PORTAL LOOP STARTED")
for gis in gisenvlist:
    print('gis connected')
    # Layer ID to search for and its URL
    #edidted to make easy

    # Pull list of all web apps in portal
    webapps = gis.content.search(f'owner: {n}' , max_items=-1)
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
    output_prod_name = name + '_' + Uname + '_Content'
    output_prod_name_csv = output_prod_name + ".csv"
    Location = output_directory +"\\"+ output_prod_name_csv

    #converts each dataframe to a variable named output
    output = pd.DataFrame([{'Title':a.title,'Type':a.type, 'URL':f'{gis.url}home/item.html?id={a.id}'} for a in app_list])
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
Fpath = Path(output_directory)

os.makedirs(output_directory + '\\' + Uname+ '_portal_items')
target_dir = output_directory + '\\' + Uname + '_portal_items'
nm = Uname.replace('_', ' ')
file_names = os.listdir(output_directory)
for file_name in file_names:
    if Uname in file_name:
        shutil.move(os.path.join(output_directory, file_name), target_dir)

fdir = os.listdir(target_dir)
if len(fdir) == 0:
    print(f"{nm} does not own any portal items.")
    shutil.rmtree(target_dir)
else:     
    print(f"{nm} owned portal items.\nA ledger of the items has been placed in {target_dir}")


print("LOOP TO REMOVE EMPTY DATA FINISHED")
