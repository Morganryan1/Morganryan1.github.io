#SCRIPT CREATED FOR NDEE SWIMMING POOL SURVEY
#CAN BE REAPPLIED ANYTIME TABULAR DATA AND ATTACHMENTS NEED TO BE EXPORTED FROM NDEE SWIMMING POOL SURVEY RESULTS AND AGGREGATED ELSEWHERE
#SCRIPT STARTED 10/05/22
#SCRIPT FINISHED 10/06/22
#SCRIPT UPDATED 10/31/22 (OoOoOoOooooo spooooky) UPDATE: added functionality to export attachments from survey and place them in folder.
#SCRIPT UPDATED 03/10/23 UPDATE: Added new field names in after a question was broken up into two questions and appened date onto end of excel file names.
#SCRIPT WRITTEN BY MORGAN RYAN
#syntax notes provide all possible options that the functions provide, in most cases all options were not used in the function which then causes the function to revert to the "default" (ex: labels=none)


#libraries that the script uses
import os
import re 
import csv
import smtplib
import arcpy
import pandas
import pyodbc
from arcgis.gis import GIS
from Update import dataUpdate
from datetime import datetime


#identifying that this script is working out of the CAT DEE SDE database
arcpy.env.workspace = r""

#intermediate data workspace (output of the esri table to excel function)
#output_directory = r"\\stnnas01.stone.ne.gov\ndeqsftp$\GIO"
output_directory = r""
inter_dir = r""
count = r""
data = pandas.DataFrame()

#Creating a function that will read a txt file and add one with each new run
with open(count, 'r') as f:
    lines=f.readline()
    numb = int(lines) + 1
    st = str(numb)
    #After the number becomes larger than five it will reset to zero
    if numb > 5:
        with open(count, 'w') as f:
            f.write('0')
            msg1 = 'First run for the day complete!\n'
            msg2 = ''
    #If the number is still smaller than 5 it will continue the process
    else:
        with open(count, 'w') as f:
            f.write(st)
            msg1 = f'Run number {st} has started for the day.\n'
            msg2 = 'not initial run'
    #This was written because we are having this script run every two hours each day to ensure stakeholders recieve reports in time
exit()
tday = datetime.today()
sday = str(tday.strftime("%Y%m%d"))

# Attachment_Folder = Attachment_Directory +"\\"+ "Swimming_Pool_Survey_Attachments"

#identifying the portal url as a variables called in by the attachment export funciton lines 81-104
portalURL = ""
username = ""
password = ""
#actual feature ID
survey_item_id = ""
save_path = output_directory
keep_org_item = False
store_csv_w_attachments = True

#creating a variable that is a swimming pool survey responses xlsx form for the arcpy.table to excel function
output_name = f"swimming_pool_survey_responses_day{sday}_NO{st}"
output_name_xlsx = output_name + ".xlsx"
output_table = inter_dir +"\\"+ output_name_xlsx

#creating a variable that is a swimming pool survey responses csv form for the PANDAS pd.to_csv function
output_name = f"swimming_pool_survey_responses_day{sday}_NO{st}"
output_name_csv = output_name + ".csv"
output_csv = output_directory +"\\"+output_name_csv



#this allows arcpy to overwrite the xlsx file created by the table to excel function
arcpy.env.overwriteOutput = True



# #deleting old output data
# for filename in os.listdir(Final_Data_Directory): #checking to see if it already exists
#       if "Swimming" in filename:
#          os.remove(os.path.join(Final_Data_Directory, filename))

# #deleting old output data
# for filename in os.listdir(inter_Data_Directory): #checking to see if it already exists
#       if "Swimming" in filename:
#          os.remove(os.path.join(inter_Data_Directory, filename))
#clearing out the current folder
# for filename in os.listdir(folder):
#     file_path = os.path.join(folder, filename)
#     try:
#         if os.path.isfile(file_path) or os.path.islink(file_path):
#             os.unlink(file_path)
#         elif os.path.isdir(file_path):
#             shutil.rmtree(file_path)
#     except Exception as e:
#         print('Failed to delete %s. Reason: %s' % (file_path, e))

print("Deleted old data")

#this section logs the script into the protal environment and locates the survey.
gis = GIS(portalURL, username, password)

print("Signed into the portal environment with built in credentials.")

survey_by_id = gis.content.get(survey_item_id)

print("Located survey items.")


#this exports the attachments from the survey and places them in the output folder with a CSV which maps the image to source location (survey)

layers = survey_by_id.tables
for i in layers:
    #this portion of the function defines a naming convention for each jpg in the csv and defines the column names.
    if i.properties.hasAttachments == True:
        feature_layer_folder = output_directory
        if bool(store_csv_w_attachments):
            path = os.path.join(feature_layer_folder, "{}".format(i.properties.name)+"_attachments"+"_day"+ sday +"_NO"+st+".csv")
        elif not bool(store_csv_w_attachments):
            path = os.path.join(save_path, "{}".format(i.properties.name)+"_attachments"+"_day"+ sday +"_NO"+st+".csv")
        csv_fields = ['Parent objectId', 'Attachment path']
        with open(path, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(csv_fields)
            #pairs the oid to the jpg name
            feature_object_ids = i.query(where="1=1", return_ids_only=True, order_by_fields='objectid ASC')
            for j in range(len(feature_object_ids['objectIds'])):
                current_oid = feature_object_ids['objectIds'][j]
                current_oid_attachments = i.attachments.get_list(oid=current_oid)
                #this part saves the attachments as jpgs and ensures that naming conventions are followed. 
                if len(current_oid_attachments) > 0:
                    for k in range(len(current_oid_attachments)):
                        attachment_id = current_oid_attachments[k]['id']
                        current_attachment_path = i.attachments.download(oid=current_oid, attachment_id=attachment_id, save_path=feature_layer_folder)
                        csvwriter.writerow([current_oid, os.path.join('{}_attachments'.format(re.sub(r'[^A-Za-z0-9]+', '', i.properties.name)), os.path.split(current_attachment_path[0])[1])])
print("Attachments collected")

#this portion states that the script should try to get through the normal workflow. However, if it cannot, then it will print "***SCRIPT FAILURE***" and the scriptSuccess variable will be identified as false
try:

#this portion states that the script should try to get through the normal workflow. However, if it cannot, then it will print "***SCRIPT FAILURE***" and the scriptSuccess variable will be identified as false
    #the table to excel arcpy function
    #syntax----- arcpy.conversion.TableToExcel(Input_Table, Output_Excel_File, {Use_field_alias_as_column_header}, {Use_domain_and_subtype_description})
    arcpy.conversion.TableToExcel("DEE_GIS.DEE.NDEE_SWIMINGPOOL_SURVEY", output_table, "NAME", "CODE")

    print("Data coppied to Excel.")

    df = pandas.read_excel(output_table, index_col=False)

    #PANDAS function to read the excel document and turn it into a dataframe (df)
    #syntax-------- pandas.read_excel(io, sheet_name=0, header=0, names=None, index_col=None, usecols=None, squeeze=None, dtype=None, engine=None, converters=None, true_values=None, false_values=None, skiprows=None, nrows=None, na_values=None, keep_default_na=True, na_filter=True, verbose=False, parse_dates=False, date_parser=None, thousands=None, decimal='.', comment=None, skipfooter=0, convert_float=None, mangle_dupe_cols=True, storage_options=None)
    df.fillna("<Null>", inplace=True)

    #changing names of columns to be more informative
    df.columns = df.columns.str.replace("b", "_comments")
    df.columns = df.columns.str.replace("a", "_recorded_values")
    df.columns = df.columns.str.replace("_recorded_valuesrriv_recorded_valuesl_st_recorded_valuestus", "arrival_status")
    df.columns = df.columns.str.replace("ev_recorded_valuesl__recorded_valuesctions", "eval_actions")
    df.columns = df.columns.str.replace("pool_sp_recorded_values_n_recorded_valuesme", "pool_spa_name")
    df.columns = df.columns.str.replace("cl_recorded_valuesss", "class")
    df.columns = df.columns.str.replace("_recorded_valuesddress", "address")
    df.columns = df.columns.str.replace("Glo_comments_recorded_valueslID", "GlobalID")
    df.columns = df.columns.str.replace("d_recorded_valueste", "date")
    df.columns = df.columns.str.replace("em_recorded_valuesil", "email")
    df.columns = df.columns.str.replace("cpo_certific_recorded_valueste", "cpo_certificate")
    df.columns = df.columns.str.replace("permit_num_commentser", "permit_number")
    df.columns = df.columns.str.replace("c_recorded_valuesr", "car")
    df.columns = df.columns.str.replace("st_recorded_valueskeholder_n_recorded_valuesme", "stakeholder_name")
    #Never change the order of the first and third str replace function because this will disrupt schematic changes
    df.columns = df.columns.str.replace("question_41_comments", "Question_41_SinkTemp")
    df.columns = df.columns.str.replace("question_41_recorded_values", "Question_41_ShowerTemp")
    df.columns = df.columns.str.replace("question_41r", "Question_41_comments")
    #reordering columns
    df = df.reindex(columns=['OBJECTID',
    'date',
    'inspector',
    'arrival_status',
    'eval_actions',
    'inspection_type',
    'pool_spa_name',
    'class',
    'address',
    'county',
    'question_1',
    'question_1_recorded_values',
    'question_2',	
    'question_2_recorded_values',
    'question_3',
    'question_3_recorded_values',
    'question_4',
    'question_4_recorded_values',
    'question_5',
    'question_5_recorded_values',
    'question_6',	
    'question_7',
    'question_8',
    'question_9',
    'question_10',
    'question_11',
    'question_12',
    'question_13',
    'question_14',
    'question_14_recorded_values',
    'question_15',
    'question_15_recorded_values',
    'question_16',
    'question_17',
    'question_18',
    'question_19',
    'question_20',
    'question_21',
    'question_22',
    'question_23',
    'question_24',
    'question_25',
    'question_26',
    'question_27',
    'question_28',
    'question_29',
    'question_30',
    'question_31',
    'question_32',
    'question_33',
    'question_34',
    'question_35',
    'question_36',
    'question_37',
    'question_38',
    'question_39',
    'question_40',
    'question_41',
    'Question_41_SinkTemp',
    "Question_41_ShowerTemp",
    'question_42',
    'question_43',
    'question_1_comments',
    'question_2_comments',
    'question_3_comments',
    'question_4_comments',
    'question_5_comments',
    'question_6_comments',
    'question_7_comments',
    'question_8_comments',
    'question_9_comments',
    'question_10_comments',
    'question_11_comments',
    'question_12_comments',
    'question_13_comments',
    'question_14_comments',
    'question_15_comments',
    'question_16_comments',
    'question_17_comments',
    'question_18_comments',
    'question_19_comments',
    'question_20_comments',
    'question_21_comments',
    'question_22_comments',
    'question_23_comments',
    'question_24_comments',
    'question_25_comments',
    'question_26_comments',
    'question_27_comments',
    'question_28_comments',
    'question_29_comments',
    'question_30_comments',
    'question_31_comments',
    'question_32_comments',
    'question_33_comments',
    'question_34_comments',
    'question_35_comments',
    'question_36_comments',
    'question_37_comments',
    'question_38_comments',
    'question_39_comments',
    'question_40_comments',
    'question_41_comments', 
    'question_42_comments',	
    'question_43_comments',
    'cpo_certificate',
    'permit_number',
    'comments',
    'stakeholder_name',
    'email',
    'car'
    ])
    print("Data reformated and columns cleaned up.")
    #splitting the comments section into three sections

    commentsSplit = df['comments'].str.split(';', n=3, expand=True)
    df['Violation_Description'] = commentsSplit[0]
    df['Violation_Description'] = df['Violation_Description'].str.replace("Violation_descriptions:","")
    df['Remarks'] = commentsSplit[1]
    df['Remarks'] = df['Remarks'].str.replace("Remarks:","")
    df['Corrections'] = commentsSplit[2]
    df['Corrections'] = df['Corrections'].str.replace("Corrections:","")
    df = df.apply(lambda x: x.replace({'CLOSURE ITEM: ': '', 'CLOSURE ITEM ': ''}, regex=True))
    df['date'] = pandas.to_datetime(df.date)
    df['date'] = df['date'].dt.strftime('%m/%d/%Y')

    #dropping the old comments column
    df.drop(['comments'], axis=1, inplace=True)
    print("Comments split and seperated.") 

    #converts the dataframe to a CSV 
    #syntax--------- DataFrame.to_csv(path)
    df.to_csv(output_csv)

    #deletes survey data from the database
   ######################## #syntax ---------- arcpy.management.DeleteRows(in_rows)##################################################
    #arcpy.management.DeleteRows("DEE_GIS.DEE.NDEE_SWIMINGPOOL_SURVEY")
    print("Data formatted and csv exported.")
    scriptSuccess = True
except:
    #if the script could not finish script success is a failure
    print("***SCRIPT FAILURE***")
    scriptSuccess = False


#function which sends email to the script admin
def sendEmail(subject, emailmessage) -> None:
        # take the email list and use it to send an email to connected users.
        SERVER = ""
        FROM = "Python Admin <Morgan.Ryan@nebraska.gov>"
        TO = ['morgan.ryan@nebraska.gov']
        SUBJECT = subject
        MSG = emailmessage

        # Prepare actual message
        MESSAGE = """\
From: %s
To: %s
Subject: %s

%s
        """ % (FROM, TO, SUBJECT, MSG)
        #Connect to the server
        server = smtplib.SMTP(SERVER)
        # Send the mail
        server.sendmail(FROM, TO, MESSAGE)
        #Disconnect from the server.
        server.quit()
        #multiple examples for sending emails.
        #http://docs.python.org/library/email-examples.html#email-examples

#Send a summary using the send email function and the messages that have been created.
if scriptSuccess == True:
    subject = 'NDEE Swimming Pool Script Summary.'
    msg = msg1
    if 'fist' in msg2:
        msg += msg2
    msg += '\nSwimming Pool survey data has been compiled and attachments have been exported'
else:
    subject = 'Swimming Pool Data Export Script Failed.'
    msg = 'Swimming pool survey data was not compiled and exported'

print("Sending email report.")
sendEmail(subject, msg)

if os.path.exists(output_table): #removing the orginal XLSX produced by the arcpy table to excel function
        os.remove(output_table)
print("Done.")

