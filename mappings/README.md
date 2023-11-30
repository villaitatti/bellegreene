# Belle_Greene_Letters
Here we will describe the usage of each file
in this folder:

1) BG_to_BG_Letters_Spreadsheet.xlsx is the data in their original form

2) fixed are the sreadsheets mentioned above, but with changes
made from xlsx_transformer.py 

3) generator policy contains all generators that are used in mappings for creating uri's

4) mapping_subjects.x3ml is the x3ml file for mapping subject sheet from original source.

5) mapping_testing.x3ml was created for testing each entity's proper mapping 
(you can use it to test each entity separately if it is mapped correctly)

6) mappings.x3ml contains mappings of all entities in sheet1 + names + subjects

7)run.sh is shell script that runs and creates .ttl file

8)xlsx_tranformer.py is a python script designedto change date fields in a way that are 
recognizable from python. 

9) xlsx_to_xml.py is a script that cleans the titles of columns from special characters, and tranforms xlsx sheet to xml format in a way that can be after that used from x3ml engine. With that script normalization takes place, which means that values in the same cell are separated as different values.
