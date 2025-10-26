# this code is used to scan two directories and identify duplicate files

#import packages
import os, glob, re
import pandas as pd 
from pathlib import Path
###listing files in original folder to compare
prod = input("New file location: ")
orig = input("Original File location: ")


#portion that allows us to remove the initial directory paths for comparison between two identical folders. 
prod_t = prod.encode('unicode_escape').decode('ascii')
re.sub(r'\\u(.){4}', '', prod_t)
orig_t = orig.encode('unicode_escape').decode('ascii')
re.sub(r'\\u(.){4}', '', orig_t)

#directories and new files
output_directory = input("Output location for new file: ")
####output location for a text file
pn = Path(prod)
pnm = pn.stem
on = Path(orig)
onm = on.stem

prod_cv = output_directory + '\\' + 'temp' + pnm + '.csv'
orig_cv = output_directory + '\\' + 'temp' + onm + '.csv'
#detailing the contents of the first folder. 

results = []
print(f"Searching the {pnm} directory and compiling files")
for x in os.walk(prod):
    for y in glob.glob(os.path.join(x[0], r'*.*')):
        results.append(y)
df = pd.DataFrame(results, columns = ['list'])
df['list'] = df['list'].str.replace(prod_t, '')
#detailing the contents of the second folder. 

results2 = []
print(f"Searching the {onm} directory and compiling files")
for x in os.walk(orig):
    for y in glob.glob(os.path.join(x[0], r'*.*')):
        results2.append(y)
ef = pd.DataFrame(results2, columns = ['list'])
ef['list'] = ef['list'].str.replace(orig_t, '')
#Turning the dataframes to CSVs for comparison
ef.to_csv(prod_cv, index=False)
df.to_csv(orig_cv, index=False)

#df2 = pd.read_csv(output_directory + '\\' + 'temp_prod.csv')
#ef2 = pd.read_csv(output_directory + '\\' + 'temp_orig.csv')
print(f"{prod} and {orig} directories compiled and ready for comparison.")

origlist = pd.read_csv(orig_cv)
prodlist = pd.read_csv(prod_cv)

prod_list = prodlist['list']
orig_list = origlist['list']

Prod_list = prod_list.values.tolist()
Orig_list = orig_list.values.tolist()

#Comparing the two CSVs 
discrep1 = [users for users in Prod_list if users not in Orig_list]
dict = {"Files that exist in " + onm + " but not in " + pnm : discrep1}
#Cleaning out the prior intermediate CSVs
folder = os.listdir(output_directory)
for item in folder:
    if item.endswith('csv'):
        os.remove(os.path.join(output_directory, item))
        print(f"Perviously created data '{item}' has been removed.")

#Creating a final conparison
ef = pd.DataFrame(dict)
ef.to_csv(output_directory + '\\' + 'difference.csv')
print('finished')
