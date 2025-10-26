import arcpy
import pandas
import os
from pathlib import Path
from arcpy import metadata as md
class featureClass:

    def __init__(self):
        '''Creating vars that will be used to access the feature dataset, and name the output'''
        # self.path = input("Paste the path for the UAIR feature dataset: ")
        self.path = r''
        p = Path(self.path)
        self.feature_dataset = p.stem
        from arcpy import env
        # self.output_path = input("Paste the path of an output folder: ")
        self.output_path = r'C:\Users\mryan\Documents\Project Work\USMC_UTILITY_NETWORK\El_Diablo_Threat_Sim'
        env.workspace = self.path

    def gdb_unpack(self):
        '''Unpacking all feature classes and datasets of a database'''
        #Listing all feature classes 
        featureClasses = arcpy.ListFeatureClasses()
        datasets = arcpy.ListDatasets()
        #Looping through and listing all datasets in the input
        for ds in datasets:
            featureClasses.extend(arcpy.ListDatasets(feature_datasets = ds))

        #Creating an empty list 
        attributes = []
        features = []
        df_lists = [attributes, features]
        #Looping through all feature classes
        for fc in featureClasses:
            #Pulling out all feature class names
            message = fc 
            Name = (str(message))
            #Pulling out all feature class descriptions
            meta = md.Metadata(fc)
            #Metadata includes HTML tags, formatting so it is only a string
            de = str(meta.description).split('<SPAN>')[1]
            desc = de.split('.')[0]
            Description = (str(desc))
            features.append({
                "Feature Class" : Name,
                "Feature Description" : Description
            })
            #Identifying that first row is true (Used later to skip name and description)
            first_row = True
            #Creating a list of attribute fields for each feature class to iterate through 
            fields = arcpy.ListFields(fc)
            for field in fields:
                #Pulling out name, type, and length from each attribute
                nme = (field.name)
                typ = (field.type)
                lngth = (field.length)

                #If this is the first instance of an attribute list loop 
                #For the feature class keep Feature Name and Descirpion
                if first_row:
                    attributes.append({
                        "Feature Class" : Name,
                        "Feature Description" : Description,
                        "Attribute Name" : nme,
                        "Attribute Type" : typ,
                        "Attribute Length" : lngth
                    })
                    first_row = False
                #Else provide an empty class name and description
                else:
                    attributes.append({
                        "Feature Class" : '',
                        "Feature Description" : '',
                        "Attribute Name" : nme,
                        "Attribute Type" : typ,
                        "Attribute Length" : lngth,
                        
                    })
        #Turn the data list (list of dictionaries) into a dataframe
        for df in df_lists:
            tbl = pandas.DataFrame(df)
            if df is features:
                typ = "Catologued_Features"
            else:
                typ = "Catologued_Attributes"
                tbl.drop(columns=['Feature Class','Feature Description'], axis=1, inplace=True)
                tbl.drop_duplicates(subset=['Attribute Name', 'Attribute Type'], inplace=True)
            tbl.to_csv(os.path.join(self.output_path, self.feature_dataset + '_' + typ + '.csv'), index=False)

            print(f'The {self.feature_dataset} has been cataloged')
            print(f'You will find a csv file in {self.output_path} location')

    def Esri_UN_unpack(self):
        '''Unpacking all feature classes of the ESRI UN Data Model.'''
         # self.path = input("Paste the path for the ESRI Utility Foundation feature dataset: ")
        self.path = r'C:\Users\mryan\Documents\Project Work\USMC_UTILITY_NETWORK\ElectricUtilityNetworkFoundationV2_2\Database\Electric_UtilityNetwork.gdb\UtilityNetwork'
        p = Path(self.path)
        parent = p.parent
        self.feature_dataset = p.stem
        from arcpy import env
        # self.output_path = input("Paste the path of an output folder: ")
        env.workspace = self.path
        featureClasses = arcpy.ListFeatureClasses()
        # Empty lists which data from the gdb will be appened to after it is collected. 
        attributes = []
        features = []
        domain_values = []
        assetgroup = []
        # A list of list vars used for enumeration later
        df_lists = [attributes, features, domain_values]


        #Looping through and listing all feature classes in the input gdb
        for fc in featureClasses:
            if 'ServiceTerritory' in fc:
                continue
            else:
                fields = arcpy.ListFields(fc)
                feature_class_name = []
                subtype_names = []
                subtype_codes = []
                join_code = []
                subdict = arcpy.da.ListSubtypes(fc)
                if len(subdict) > 1:
                    for stcode in subdict:
                        # if subdict[stcode]['SubtypeField'] != "":
                        #     subtypenames.append(subdict[stcode]['Name'])
                        subtype_info = subdict[stcode]
                        subtype_field = subtype_info['SubtypeField']
                        if subtype_field != "":
                            feature_class_name.append(fc)
                            subtype_names.append(subtype_info['Name'])
                            subtype_codes.append(stcode)
                            nm = str(subtype_info['Name'].replace(' ',''))
                            join = 'AssetType' + fc + nm
                            join_code.append(join)

            data = {'Join Code': join_code, 'Asset Group Name': subtype_names, 'Asset Group Code': subtype_codes}
            df= pandas.DataFrame(data)
            assetgroup.append(df)
            

                
            
            
            #Pulling all features from the gdb.
            field_list = []
            feature_name = os.path.basename(fc)
            data_frame = pandas.DataFrame()
            for field in fields:
                #Getting all fields asside from geometry and OIDs for a search cursor. 
                if field != 'Geometry' and field != 'OID':
                    field_list.append(field.name)
                
                    #Getting fields for the fields csv
                    nme = (field.name)
                    typ = (field.type)
                    lngth = (field.length)
                    attributes.append({
                            "Feature Class" : '',
                            "Attribute Name" : nme,
                            "Attribute Type" : typ,
                            "Attribute Length" : lngth,
                            
                        })
            #Using a search cursor to pull all records from each feature class
            with arcpy.da.SearchCursor(fc, field_list) as cursor:
                cursor_data  = []
                for row in cursor:
                    row = dict(zip(cursor.fields, row))
                    cursor_data.append(row)

            data_frames = data_frame.append(pandas.DataFrame(cursor_data))
            data_frames.insert(0, column='Feature', value=feature_name)
            #Appending all features to the features list.
            features.append(data_frames)




        domains = arcpy.da.ListDomains(parent)
        #Looping through and listing all domain classes in the input gdb
        for domain in domains:
                #Pulling all domains from the gdb
                if domain.domainType == 'CodedValue':
                    domain_name = domain.name
                    test = domain_name.lower()
                    if 'asset_type' in test:
                        #Narrowing the the domain list to only asset types
                        up = str(domain_name).replace("_", '')
                        tbl = pandas.concat(assetgroup, ignore_index = True)
                        match = None
                        for index, row in tbl.iterrows():
                                if up in row['Join Code']:
                                    match = row['Asset Group Code']
                                    break
                        if match is not None:
                                first_row = True
                                coded_value_list = domain.codedValues
                                #Looping through the coded values list to pull out a value and description
                                for value, descrip in coded_value_list.items():
                                    #Every new domain row will only have a name value
                                    if first_row is True:
                                        domain_values.append({"Asset Group" : up,
                                        "Asset Group Code" : match,
                                        "Asset Type" : '',
                                        "Asset Type Code" : ''})
                                        first_row = False
                                    else:
                                        #The subsequent rows will list the values and desctiptions of the domain. 
                                        domain_values.append({"Asset Group" : '',
                                        "Asset Group Code": '',
                                        "Asset Type" : descrip,
                                        "Asset Type Code" : value})
                        else:
                            continue
                    else:
                        continue     
        #Turn the data list (list of dictionaries) into a dataframe
        for df in df_lists:
            for df in df_lists:
                tbl = pandas.DataFrame(df)
                if df is features:
                    
                    typ = "Catologued_Features"
                    tbl = pandas.concat(features, ignore_index = True)
                    # tbl.drop_duplicates(subset=['ASSETTYPE', 'ASSETGROUP'], inplace=True)
                    tbl.insert(4, 'Asset Group Name', value = '')
                    tbl.insert(6, 'Asset Type Name', value = '')
                    d_tbl = pandas.DataFrame(domain_values)
        
                    for findex, frow in tbl.iterrows():
                        feature_name = frow['Feature']
                        asset_group_code = frow['ASSETGROUP']
                        asset_type_code = frow['ASSETTYPE']
                        if frow['ASSETTYPE'] == 0:
                            tbl.at[findex, 'Asset Type Name'] = 'Unkown'

                        for dindex, drow in d_tbl.iterrows():
                            feat = drow['Asset Group']
                            subtyp = drow['Asset Type']
                            group_code = drow['Asset Group Code']
                            asset_code = drow['Asset Type Code']

                            if feature_name in feat and group_code == asset_group_code:
                                nm = feat.replace('AssetType','')
                                tbl.at[findex, 'Asset Group Name'] = nm

                            if asset_code == asset_type_code:
                                tbl.at[findex, 'Asset Type Name'] = subtyp
                            
                    tbl['Asset Group Name'] = tbl.apply(lambda row : row['Asset Group Name'].replace(str(row['Feature']), ''), axis=1)
                    tbl = tbl[['Feature', 'ASSETGROUP', 'Asset Group Name', 'ASSETTYPE', 'Asset Type Name']]
                    

                    
                    
                elif df is attributes:
                    typ = "Catologued_Attributes"
                    tbl.drop(columns=['Feature Class'], axis=1, inplace=True)
                    tbl.drop_duplicates(subset=['Attribute Name', 'Attribute Type'], inplace=True)

                else:
                    typ = "Catologued_Domains"
                    # continue
                tbl.to_csv(os.path.join(self.output_path, self.feature_dataset + '_' + typ + '.csv'), index=False)


        print(f'The {self.feature_dataset} has been cataloged')
        print(f'You will find csv files in the {self.output_path} folder')
        

        


table = featureClass()
table.Esri_UN_unpack()
