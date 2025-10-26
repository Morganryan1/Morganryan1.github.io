from logging import exception
from arcgis.gis import GIS
from pathlib import Path
import os, arcpy, pandas


#Locating a feature by its feature id

#enterprise connections and user input varibles
prod = GIS("PORTAL", "USERNAME", "PASSWORDS")
cat = GIS("PORTAL", "USERNAME", "PASSWORDS")
partner = GIS("PORTAL", "USERNAME", "PASSWORDS")
dev = GIS("PORTAL", "USERNAME", "PASSWORDS")
gisenvlist = [prod, cat, partner, dev]
output_directory = arcpy.GetParameterAsText(1)
find_id = arcpy.GetParameterAsText(0)





#loop to go through each portal environment to check for user input layer id.
arcpy.AddMessage("PORTAL LOOP STARTED")
for gis in gisenvlist:
    if gis is prod:
            name = 'Production'
    elif gis is cat:
            name = 'Cat'
    elif gis is dev:
            name = 'Dev'
    elif gis is partner:
            name = 'Partner'
    arcpy.AddMessage(f'Script connected to the {name} portal!')

    #layer ID to search for and its URL
    try:
       find_url = gis.content.get(find_id).url
       if len(find_url) == 0:
            Exception
       else:
            itm = gis.content.get(find_id).title
    except Exception as e:
        arcpy.AddMessage(f"The layer was not found in the {name} portal...")
        continue
    
    #pull list of all web maps in portal
    webmaps = gis.content.search('', max_items=-1)
    arcpy.AddMessage(f'Searching the {name} portal for items using {itm}.')

    #return subset of map IDs which contain the service URL we're looking for
    matches = [m.id for m in webmaps if str(m.get_data()).find(find_url) > -1]

    map_list = []

    #check each web map for matches
    for w in webmaps:

        try:
            #get the JSON as a string
            wdata2 = str(w.get_data())

            criteria = [
                wdata2.find(find_url) > -1,  # Check if URL is directly referenced
                any([wdata2.find(i) > -1 for i in matches])  # Check if any matching maps are in app
            ]

            # If layer is referenced directly or indirectly, append map to list
            if any(criteria):
                map_list.append(w)

        # Some apps don't have data, so we'll just skip them if they throw a TypeError
        except:
            continue
    output = pandas.DataFrame([{'Title': m.title, 'ID': m.id, 'Type': m.type, 'URL':f'{gis.url}home/item.html?id={m.id}'} for m in map_list])
    arcpy.AddMessage(f'Turning findings from {name} portal into a data frame.')
    #creates a path, file type and name for each output
    output_prod_name = itm + '_' + name + '_Layer_Uses'
    output_prod_name_csv = output_prod_name + ".csv"
    Location = output_directory +"\\"+ output_prod_name_csv
    
    for fold in os.listdir(output_directory):
        if itm not in fold:
            os.remove(os.path.join(output_directory, fold))
    output.to_csv(Location, index=[0])
    arcpy.AddMessage(f'Data from the {name} portal turned into a csv!')

    arcpy.AddMessage(f"Objects which use {itm} have been identified.")
