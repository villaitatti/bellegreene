import os
import re
import html
import json
import click
import logging
import configparser
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from defusedxml.minidom import parseString


UNDATED_DATE = "Undated date provided"

KEYUSR = 'username'
KEYPSW = 'password'
KEYEND = 'endpoint'


def _get_credentials(type):
    """
    Retrieves the credentials for a specific type from a configuration file.

    Parameters:
    type (str): The type of credentials to retrieve.

    Returns:
    dict: A dictionary containing the username, password, and endpoint for the specified type.
    """
    config = configparser.ConfigParser()
    try:
        path = os.path.join(os.path.abspath(os.getcwd()), 'mappings', 'psw.ini')
        config.read(path)

        return {
            KEYUSR: config.get(type, KEYUSR),
            KEYPSW: config.get(type, KEYPSW),
            KEYEND: config.get(type, KEYEND)
        }
    
    except Exception as ex:
        print('Error. Have you created the psw.ini file? see readme.md')


# Configure logging
logging.basicConfig(
    filename='mappings/output/error.log',
    filemode='w',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
def clean_date_string(date_str):
    """Removes annotations and uncertainty markers from the date string."""
    return re.sub(r'\s+\([^\)]*\)|\?', '', date_str)

def handle_undated(parts):
    """Handles cases where the date contains 'UNDATED'."""
    if "UNDATED" in parts:
        parts.remove("UNDATED")
        return parts[:2], True
    return parts, False

def parse_multiple_days(year, month, days):
    """Generates a list of date strings for multiple days."""
    date_list = []
    for day in days:
        try:
            date_obj = datetime(int(year), int(month), int(day))
            date_list.append(date_obj)
        except ValueError:
            date_list.append(f"Invalid date: {year}-{month}-{day}")
    return date_list

def get_month_start_end(year, month):
    """Returns the first and last day of the given month."""
    start_date = datetime(int(year), int(month), 1)
    next_month = start_date.replace(day=28) + timedelta(days=4)  # this will never fail
    end_date = next_month - timedelta(days=next_month.day)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def parse_dates(date_str):
    """Parses various complex date formats and returns start and end dates.
    
        Examples:
        <Date_YYYYMMDD>1911_02_UNDATED_01</Date_YYYYMMDD>
        <Date_YYYYMMDD>UNDATED 01</Date_YYYYMMDD>
        <Date_YYYYMMDD>1915_UNDATED_01</Date_YYYYMMDD>
        <Date_YYYYMMDD>1910_10_17 (second letter)</Date_YYYYMMDD>
        <Date_YYYYMMDD>1910_09_07?</Date_YYYYMMDD>
        <Date_YYYYMMDD>1910_10_17 (second letter)</Date_YYYYMMDD>
        <Date_YYYYMMDD>1910_10_19_20_23_25</Date_YYYYMMDD>
    """
    clean_date_str = clean_date_string(date_str)
    parts = clean_date_str.split('_')
    
    parts, undated = handle_undated(parts)
    year = parts[0] if len(parts) > 0 and parts[0] != 'UNDATED' else 'Undated'
    month = parts[1] if len(parts) > 1 and parts[1] != 'UNDATED' else 'Undated'
    days = parts[2:] if len(parts) > 2 else []

    if undated:
        return get_month_start_end(year, month)

    if year == 'Undated':
        return (UNDATED_DATE, UNDATED_DATE)
    
    if month == 'Undated':
        return (f"{year}-Undated", f"{year}-Undated")
    
    if not days:
        return get_month_start_end(year, month)

    date_list = parse_multiple_days(year, month, days)
    
    if isinstance(date_list[0], datetime):
        return (date_list[0].strftime('%Y-%m-%d'), date_list[-1].strftime('%Y-%m-%d'))
    return (date_list[0], date_list[-1])

def sanitize_column_name(name):
    # Replace spaces and other invalid characters with underscores
    name = name.replace(' ', '_')
    # Remove any characters that are not allowed in XML tags
    name = re.sub(r'\W', '', name)
    return name


def handle_list_values(col_name, value):
    # Check if the column is one of those that contain lists
    if col_name == 'I_Tatti_file_names':
        # Split the value by comma and whitespace
        items = [item.strip() for item in value.split(',')]
        return items
    elif col_name == 'Subjects' or col_name == 'Subject__People_Last_Name_First_Name' or col_name == 'Letters_Contents':
        # Split the value by "; " and whitespace
        items = [item.strip() for item in value.split(';')]
        return items
    return None


def handle_transcribers(row_elem, row):
    transcribers_elem = ET.SubElement(row_elem, 'transcribers')

    # Handle transcriber 1
    if not pd.isna(row['Name_of_Transcriber_1_Last_Name_First_Name']):
        transcriber_1_elem = ET.SubElement(transcribers_elem, 'transcriber_1')
        name_1_elem = ET.SubElement(transcriber_1_elem, 'name')
        name_1_elem.text = html.escape(
            str(row['Name_of_Transcriber_1_Last_Name_First_Name']))

        if not pd.isna(row['Transcriber_1_Initials']):
            initials_1_elem = ET.SubElement(transcriber_1_elem, 'initials')
            initials_1_elem.text = html.escape(
                str(row['Transcriber_1_Initials']))

        if not pd.isna(row['Date_Claimed_YYYYMMDD']):
            claimed_1_elem = ET.SubElement(transcriber_1_elem, 'claimed')
            claimed_1_elem.text = html.escape(
                str(row['Date_Claimed_YYYYMMDD']))

        if not pd.isna(row['Date_Completed_YYYYMMDD']):
            completed_1_elem = ET.SubElement(transcriber_1_elem, 'completed')
            completed_1_elem.text = html.escape(
                str(row['Date_Completed_YYYYMMDD']))

    # Handle transcriber 2
    if not pd.isna(row['Name_of_Transcriber_2_Last_Name_First_Name']):
        transcriber_2_elem = ET.SubElement(transcribers_elem, 'transcriber_2')
        name_2_elem = ET.SubElement(transcriber_2_elem, 'name')
        name_2_elem.text = html.escape(
            str(row['Name_of_Transcriber_2_Last_Name_First_Name']))

        if not pd.isna(row['Transcriber_2_Initials']):
            initials_2_elem = ET.SubElement(transcriber_2_elem, 'initials')
            initials_2_elem.text = html.escape(
                str(row['Transcriber_2_Initials']))

        if not pd.isna(row['Date_Claimed_YYYYMMDD1']):
            claimed_2_elem = ET.SubElement(transcriber_2_elem, 'claimed')
            claimed_2_elem.text = html.escape(
                str(row['Date_Claimed_YYYYMMDD1']))

        if not pd.isna(row['Date_Completed_YYYYMMDD1']):
            completed_2_elem = ET.SubElement(transcriber_2_elem, 'completed')
            completed_2_elem.text = html.escape(
                str(row['Date_Completed_YYYYMMDD1']))


def parse_letters(csv_file_path, xml_file_path, names):
    # Read the CSV file
    df = pd.read_csv(csv_file_path, dtype={
                     'Box_Number': str, 'Folder_Number': str, 'Number_of_pages': str, 'Number_of_images': str}, na_filter = False)

    # Replace spaces and invalid characters in column names with underscores
    df.columns = [sanitize_column_name(col) for col in df.columns]

    # Create the root element
    root = ET.Element('root')

    # Loop through the rows of the DataFrame
    for i, row in df.iterrows():
        
        # Create a new element for each row
        row_elem = ET.SubElement(root, 'letter')

        # Loop through the columns
        for col in df.columns:
            if col.startswith('Name_of_Transcriber_1') or col.startswith('Transcriber_1_') or col.startswith('Date_Claimed_YYYYMMDD') or col.startswith('Date_Completed_YYYYMMDD') or col.startswith('Name_of_Transcriber_2') or col.startswith('Transcriber_2_') or col.startswith('Date_Claimed_YYYYMMDD1') or col.startswith('Date_Completed_YYYYMMDD1'):
                # Skip these columns as they will be handled separately
                continue

                # Handle list values for specific columns
            list_values = handle_list_values(col, str(row[col]))
            if list_values:
                parent_elem = ET.SubElement(row_elem, col)
                for item in list_values:
                    if col == 'I_Tatti_file_names':
                        item_elem = ET.SubElement(parent_elem, 'file_name')
                        item_elem.text = html.escape(item)

                    elif col == 'Subjects':
                        item_elem = ET.SubElement(parent_elem, 'subject')
                        item_elem.text = html.escape(item)

                    elif col == 'Letters_Contents':
                        item_elem = ET.SubElement(parent_elem, 'content')
                        item_elem.text = html.escape(item)

                    elif item != 'nan' and col == 'Subject__People_Last_Name_First_Name':
                        certain = True
                        if "?" in item:
                            certain = False
                            item = item.replace(" (?)", "")
                            item = item.replace("?", "")

                        item_elem = ET.SubElement(parent_elem, 'person')
                        item_elem_identifier = ET.SubElement(
                            item_elem, 'identifier')

                        try:
                            item_elem_identifier.text = names[item]['identifier']
                        except Exception as ex:
                            logging.error("An error occurred: name %s", f'{
                                          ex} not found in letter {row['Letter_ID']}')
                            item_elem_identifier.text = item

                        item_elem_certain = ET.SubElement(item_elem, 'certain')
                        item_elem_certain.text = str(certain)

            else:
                item = row[col]
                # Create a new element for each column
                if not pd.isna(item):
                    # Handle dates
                    if col.startswith('Date_YYYYMMDD'):
                        letter_date = item
                        dt = parse_dates(item)

                        date_tag = ET.SubElement(row_elem, 'date')

                        old_date_tag = ET.SubElement(date_tag, col)
                        old_date_tag.text = item
                        
                        start_tag = ET.SubElement(date_tag, 'start')
                        start_tag.text = dt[0]
                        
                        end_tag = ET.SubElement(date_tag, 'end')
                        end_tag.text = dt[1]
                    if col.startswith('sender') or col.startswith('recipient'):
                        
                        person_elem = ET.SubElement(row_elem, col)
                        person_elem_identifier = ET.SubElement(
                            person_elem, 'identifier')

                        try:
                            person_elem_identifier.text = names[item]['identifier']
                        except Exception as ex:
                            logging.error("An error occurred: name %s", f'{ex} not found in letter {row['Letter_ID']}')
                            person_elem_identifier.text = item
                            
                            # Set the identifier to 00000 for Belle da Costa Greene
                            if 'Greene, Belle da Costa' in item:
                                person_elem_identifier.text = '00000'
                                
                        person_name_elem = ET.SubElement(person_elem, 'name')
                        person_name_elem.text = item
                        
                        if col.startswith('sender'):
                            letter_sender = item
                        if col.startswith('recipient'):
                            letter_recipient = item
                    
                    else:
                        col_elem = ET.SubElement(row_elem, col)
                        # Escape special characters in the text content
                        col_elem.text = html.escape(str(item))

                        if col.startswith('Letter_ID'):
                            letter_id = item


        label_elem = ET.SubElement(row_elem, 'title')
        label_elem.text = f'Letter {letter_id}: {letter_sender} to {letter_recipient}, {letter_date}'

        # Handle transcribers
        handle_transcribers(row_elem, row)

    # Convert the ElementTree to a string
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')

    # Beautify the XML string
    dom = minidom.parseString(xml_str)
    pretty_xml_str = dom.toprettyxml(indent="  ")

    # Write the pretty XML string to the file
    with open(xml_file_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)


def parse_names(csv_file_path, xml_file_path):

    NAME_LAST_FIRST = 'Name (Last, First)'

    # Open CSV file and remove NaN values
    df = pd.read_csv(csv_file_path, dtype={'identifier': str})
    # Remove rows with NaN in the identifier column
    df = df.dropna(subset=['identifier'])

    # Replace NaN values with empty strings for other columns
    df = df.fillna('')

    # Filter out rows where 'Name (Last, First)' is 'nan' or invalid
    df = df[~df['Name (Last, First)'].isin(['', 'nan', None])]

    # Create XML root element
    root = ET.Element('persons')

    # Add each person to the XML
    for _, row in df.iterrows():

        person = ET.Element('person')

        identifier = ET.SubElement(person, 'identifier')
        identifier.text = str(row['identifier'])

        name = ET.SubElement(person, 'name')
        name.text = row[NAME_LAST_FIRST]

        nickname = ET.SubElement(person, 'nickname')
        nickname.text = row["BG's Nickname or Reference"]

        life_dates = ET.SubElement(person, 'life_dates')
        life_dates.text = row['Life Dates']

        bio_desc = ET.SubElement(person, 'biographical_description')
        bio_desc.text = row['Biographical Description']

        root.append(person)

    # Convert XML tree to a string
    xml_str = ET.tostring(root, encoding='unicode', method='xml')

    # Beautify the XML string
    dom = minidom.parseString(xml_str)
    pretty_xml_str = dom.toprettyxml(indent="  ")

    # Write the pretty XML string to the file
    with open(xml_file_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)

    return df.set_index(NAME_LAST_FIRST).T.to_dict()


@click.command()
@click.option('-p', 'parse', is_flag=True, help="Execute the parsing", default=False)
@click.option('-m', 'mappings', is_flag=True, help="Execute the mappings", default=False)
@click.option('-u', 'upload', is_flag=True, help="Execute the uploading", default=False)
@click.option('-l', 'limit', help="Subset of letters to iterate", type=int, default=-1)
@click.option('-c', 'upload_config', type=str, help="profile to select usr, psw, and endpoint from psw.ini. see readme", default='belle_greene')
def exec(parse, mappings, upload, limit, upload_config):
    cur_path = os.path.dirname(os.path.realpath(__file__))

    input_path = os.path.join(cur_path, "input")
    output_path = os.path.join(cur_path, "output")

    if parse:
        print('Executing parsing ...')

        # Parse names
        names = parse_names(os.path.join(input_path, 'names.csv'),
                            os.path.join(output_path, 'names.xml'))

        # Write letters
        parse_letters(os.path.join(input_path, 'letters.csv'),
                      os.path.join(output_path, 'letters.xml'), names)

        print('Parsing completed\n')

    if mappings:
        print('Executing mappings ...')

        engine = os.path.join(cur_path, 'x3ml-engine.jar')
        letters = os.path.join(output_path, 'letters.xml')
        mappings = os.path.join(cur_path, 'mappings.x3ml')
        generator_policy = os.path.join(cur_path, 'generator_policy.xml')
        output_file = os.path.join(output_path, 'output.ttl')
        application_format = 'text/turtle'

        command = f'java -jar {engine} -i {letters} -x {mappings} -p {generator_policy} -o {output_file} -f {application_format}'
        os.system(command)

        print('Mappings completed\n')
    
    if upload:
        
        credentials = _get_credentials(upload_config)

        data = os.path.join(output_path, 'output.ttl')
        
        endpoint = f'{credentials[KEYEND]}rdf-graph-store?graph=https%3A%2F%2Fbellegreene.itatti.harvard.edu%2Fresource%2Fdata%2Fcontext'
        
        delete_command = f'curl -u {credentials[KEYUSR]}:{credentials[KEYPSW]} -X DELETE {endpoint}'
        print('Deleting data ...')
        print(os.system(delete_command))
        
        post_command = f'curl -u {credentials[KEYUSR]}:{credentials[KEYPSW]} -X POST -H "Content-Type: text/turtle" --data-binary "@{data}" {endpoint}'

        print('Uploading data ...')
        print(os.system(post_command))


if __name__ == '__main__':
    exec()
