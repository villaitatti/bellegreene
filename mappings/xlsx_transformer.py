'''
With this script we manage to read an excel workbook and replace all none values with zeros in every sheet. 
'''


# import all required library
import xlrd
import csv
import pandas as pd
import numpy as np

# open workbook by sheet index,
# optional - sheet_by_index()
# sheet = xlrd.open_workbook("BG_to_BB_Letters_Spreadsheet.xlsx").sheet_by_index(0)
xls = pd.ExcelFile('BG_to_BB_Letters_Spreadsheet_normalized.xlsx')
df1 = pd.read_excel(xls, 'Copy of Sheet1')
# df2 = pd.read_excel(xls, 'Subjects')
# df3 = pd.read_excel(xls, 'Names')
# df4 = pd.read_excel(xls, 'images')

df1 = df1.replace('',np.nan).fillna(0)
# df2 = df2.replace('',np.nan).fillna(0)
# df3 = df3.replace('',np.nan).fillna(0)
# df4 = df4.replace('',np.nan).fillna(0)
# show the dataframe
# xml_string = df.to_xml()
# with open('output.xml', 'w') as f:
#     f.write(xml_string)

#write_fixed_excel
df1['Date Claimed (YYYY/MM/DD).1'] = df1['Date Claimed (YYYY/MM/DD).1'].apply(str)
df1['Date Claimed (YYYY/MM/DD)'] = df1['Date Claimed (YYYY/MM/DD)'].apply(str)
df1['Date Completed (YYYY/MM/DD)'] = df1['Date Completed (YYYY/MM/DD)'].apply(str)
df1['Date Completed (YYYY/MM/DD).1'] = df1['Date Claimed (YYYY/MM/DD).1'].apply(str)
df1['Date Finalized (YYYY/MM/DD)'] = df1['Date Finalized (YYYY/MM/DD)'].apply(str)
df1['I Tatti Sheet Number(s)'] = df1['I Tatti Sheet Number(s)'].apply(str)
with pd.ExcelWriter("./fixed_normalized.xlsx") as writer:
   
    # use to_excel function and specify the sheet_name and index
    # to store the dataframe in specified sheet
    df1.to_excel(writer, sheet_name="Sheet1_normalized", index=False)
    # df2.to_excel(writer, sheet_name="Subjects", index=False)
    # df3.to_excel(writer, sheet_name="Names", index=False)
    # df4.to_excel(writer, sheet_name="images", index=False)
