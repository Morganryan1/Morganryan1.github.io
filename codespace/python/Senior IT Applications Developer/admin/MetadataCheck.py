import pandas
import fnmatch
import requests
import re
import os
import xml.etree.ElementTree as Xet
from pathlib import Path
from arcgis.gis import *
import arcpy

prod = GIS()
cat = GIS()
partner = GIS()
dev = GIS()
url = 'https://raw.githubusercontent.com/consbio/gis-metadata-parser/main/docs/arcgis-metadata.dtd'

envdef = [prod, cat, partner, dev]
output_directory = 'C:\temp'
Env = 'cat'
# output_directory = arcpy.GetParameterAsText(2)
# Env = arcpy.GetParameterAsText(0)
#str(input("Which Environment are you using prod, cat, partner or dev: ")).lower()

# find_idEx = arcpy.GetParameterAsText(1)
find_idEx = ''

if Env == "prod":
    gis = envdef[0]
elif Env == "cat":
    gis = envdef[1]
elif Env == "partner":
    gis = envdef[2]
elif Env == "dev":
    gis = envdef[3]

def ExampleXml():
    """Creates the base example xml file, if you already have the example file please do not use this function..."""
    find_id = '6a4ec7f4806041f38684fd72d499d93d'
    feat = cat.content.get(find_id)
    nm1 = feat.title
    

    feat.download_metadata(output_directory)
    for file in os.listdir(output_directory):
        if 'metadata' in file:
            old = os.path.join(output_directory, file)
            sample = os.path.join(output_directory, f"{nm1}.xml")
            os.rename(old, sample)
    for file in os.listdir(output_directory):
        if file.endswith('Training.xml'):
            xmlparse = Xet.parse(os.path.join(output_directory, file))
            root = xmlparse.getroot()
            fn = Path(file)
            nm = fn.stem
            columns = ['NODE']
            appended_lyr = []
            for child in root:
                t = child.tag
                appended_lyr.append(t)
                for sub in child:
                    c = sub.findall('.//')
                    d = [x for x in c if x !=[]]
                    sub_lis = str(d)
                    q = sub_lis.split(",")
                    for i in q:
                        grandchildren = re.findall("'([^']*)'", i)
                        t = str(grandchildren)
                        sample_list = []
                        for i in t:
                            if i.isalnum():
                                sample_list.append(i)
                        string ="".join(sample_list)
                        if len(string) > 0:
                            appended_lyr.append(string)
                        else:
                            pass
                
            df = pandas.DataFrame(appended_lyr, columns=columns)
            df = df.drop_duplicates(subset=['NODE'])
            df.to_csv(os.path.join(output_directory,f'{nm1}.csv'), index=False)
    print('example created')

def SampleXml(find_idEx):
    """The user file which we are compairing."""
    feat = gis.content.get(find_idEx)
    nm = str(feat.title)
    if ' ' in nm:
        nm2 = nm.replace(' ', '')
    
    feat.download_metadata(output_directory)
    for file in os.listdir(output_directory):
        if 'metadata' in file:
            old = os.path.join(output_directory, file)
            comp = os.path.join(output_directory, f"{nm2}.xml")
            os.rename(old, comp)
    print('test created')

    for file in os.listdir(output_directory):
        if file.endswith('xml') and not file.endswith('Training.xml'):
            xmlparse = Xet.parse(os.path.join(output_directory, file))
            root = xmlparse.getroot()
            fn = Path(file)
            nm = fn.stem
            columns = ['NODE']
            appended_lyr = []
            for child in root:
                t = child.tag
                appended_lyr.append(t)
                for sub in child:
                    c = sub.findall('.//')
                    d = [x for x in c if x !=[]]
                    sub_lis = str(d)
                    q = sub_lis.split(",")
                    for i in q:
                        grandchildren = re.findall("'([^']*)'", i)
                        t = str(grandchildren)
                        sample_list = []
                        for i in t:
                            if i.isalnum():
                                sample_list.append(i)
                        string ="".join(sample_list)
                        if len(string) > 0:
                            appended_lyr.append(string)
                        else:
                            pass
                
            df = pandas.DataFrame(appended_lyr, columns=columns)
            df = df.drop_duplicates(subset=['NODE'])
            df.to_csv(os.path.join(output_directory,f'{nm}_tst.csv'), index=False)
    

def xmlComparison():
    """Comparing the test xml against the sample."""
    for file in os.listdir(output_directory):
        if file.endswith('.csv') and not file.endswith('Training.csv'):
            fn = Path(file)
            nm = fn.stem

            example = os.path.join(output_directory,'MetadataTraining.csv')

            results = []
            for root, dirs, files, in os.walk(output_directory):
                for name in files:
                    if fnmatch.fnmatch(name, '*_tst.csv'):
                        results.append(os.path.join(root, name))
            test = ''.join(results)
            if '_tst' in nm:
               nm = nm.replace('_tst','')
            print(str(test))
            with open(example, 'r') as f1, open(test, 'r') as f2:
                fileOne = f1.readlines()
                fileTwo = f2.readlines()
            final = os.path.join(output_directory, f'{nm}_Missing_Metadata.csv')
            with open(final, 'w') as outfile:
                for line in fileOne:
                    if line not in fileTwo:
                        outfile.write(line)
            df = pandas.read_csv(final)
            column = ['title']
            df.to_excel(os.path.join(output_directory,f'{nm}_Missing_Metadata.xlsx'), header=column, index= None)
            print('done')
    #REMOVE THIS COMMENT
    # for file in os.listdir(output_directory):
    #       if file.endswith('Missing_Metadata.xlsx'):
    #           pass
    #       else:
    #           os.remove(os.path.join(output_directory, file))

def metadata_Explainer():
    """Creates the file which provides Metadata explanations for each missing component."""
    nm = f"metadata_decoder.txt"
    cs = "metadata_decoder.xlsx"
    file = os.path.join(output_directory, nm)
    excel_file = os.path.join(output_directory, cs)
    if nm not in os.listdir(output_directory):
        page = requests.get(url)
        t = page.text
        with open(file, 'w') as ou:
            data = t.splitlines(keepends=True)
            subst = ['<!-- Metadata.']
            t = [x for x in data if any(sub in x for sub in subst)]
            for i in t:
                form = re.sub('\?|\<|\>|\-|\!|\/|\;', '', i)
                t = str(form)
                head, sep, tail = t.partition('.')
                t = tail.lstrip(' ')
                a = t.replace('contInfo.', '')
                b = a.replace('spatRepInfo.Georef.', '')
                c = b.replace('spatRepInfo.Georect.', '')
                d = c.replace('spatRepInfo.', '')
                e = d.replace('distInfo.', '')
                f = e.replace('dqInfo.dqScope.', '')
                g = f.replace('dqInfo.report.', '')
                h = g.replace('dqInfo.report.measResult.ConResult.', '')
                i = h.replace('dqInfo.report.', '')
                j = i.replace('dqInfo.report..', '')
                k = j.replace('appSchInfo.', '')
                l = k.replace('mdExtInfo.', '')
                m = l.replace('mdExtInfo.extEleInfo.', '')
                n = m.replace('porCatInfo.', '')
                o = n.replace(': ', ':')
                ou.writelines(o)
            print(f'{file} created!')
        ou.close()
        
        tbl = pandas.read_csv(file, delimiter = ':', header= None)
        tbl.columns = ['title', 'description']
        tbl.to_excel(excel_file, index= None)

        if nm in os.listdir(output_directory):
            os.remove(file)
    else:
        if nm in os.listdir(output_directory):
            os.remove(file)

def metadata_Append():
    for item in os.listdir(output_directory):
        if 'decoder' in item:
            base = pandas.read_excel(os.path.join(output_directory, item))
        else:
            test = pandas.read_excel(os.path.join(output_directory,item))

    fin = base.merge(test, on='title', how='right')
    for file in os.listdir(output_directory):
        if file.endswith('Metadata.xlsx') and not file.endswith('decoder.xlsx'):
            fn = Path(file)
            nm = fn.stem
    fnm = nm.replace('_Missing_Metadata', '')
    for file in os.listdir(output_directory):
        os.remove(os.path.join(output_directory, file))
    file = f'{fnm}_Final_MetaData_Results.xlsx'
    fin.to_excel(os.path.join(output_directory, file))

ExampleXml()
SampleXml(find_idEx)
xmlComparison()
exit()
metadata_Explainer()
metadata_Append()
