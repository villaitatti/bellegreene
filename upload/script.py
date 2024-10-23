import click
import os
import csv
import docx
import shutil
import re
import pandas as pd
import datetime
import configparser
import urllib
from rdflib import Graph, URIRef, namespace, Namespace, Literal

REGEX_PAGE = r'\[p[t]?[.]?[\s]?(\d+)\]'

REGEX_SEQUENCE = r'^\d+_\d{3}$'

KEY_PARAGRAPHS = 'paragraphs'
KEY_SEQUENCE = 'sequence'

KEY_USERNAME = 'username'
KEY_PASSWORD = 'password'
KEY_ENDPOINT = 'endpoint'

BASE_URI = 'https://bellegreene.itatti.harvard.edu/'
RESOURCE = f'{BASE_URI}resource/'

KEY_VALUE = 'value'
KEY_TYPE = 'type'
KEY_TEXT = 'text'
KEY_RUNS = 'runs'

KEY_BOLD = 'bold'
KEY_ITALIC = 'italic'
KEY_UNDERLINE = 'underline'
KEY_STRIKE = 'strike'

KEY_ID = 'id'
KEY_PAGES = 'sequences'
KEY_REPRESENTATION = 'representation'

IMG_BASE_URI = 'https://iiif-bucket.s3.eu-west-1.amazonaws.com/bellegreene500/'
IMG_BASE_URI_IIIF_START = 'https://iiif.itatti.harvard.edu/iiif/2/bellegreene-full!'
IMG_BASE_URI_IIIF_END = '/full/full/0/default.jpg'

PLATFORM = Namespace('http://www.researchspace.org/resource/system/')
BG = Namespace(RESOURCE)
LDP = Namespace('http://www.w3.org/ns/ldp#')
CRM = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DPUB_ANNOTATION = Namespace(f'{BASE_URI}document/annotation-schema/')
CRMDIG = Namespace('http://www.ics.forth.gr/isl/CRMdig/')
PROV = Namespace('http://www.w3.org/ns/prov#')
MB_DIARIES = Namespace('https://mbdiaries.itatti.harvard.edu/ontology/')
RDF = namespace.RDF
RDFS = namespace.RDFS
XSD = namespace.XSD


"""_summary_`

Now the system accepts letters in the following format:

letter {
    id: string
    sequences: [
        {
            id: int,
            representation: string,
            paragraphs: [
                {
                    text: string,
                    runs: [
                        {
                            value: string,
                            type: string
                        }
                    ]
                }
            ]
        }
    ]
}

"""


def _extract_paragraphs_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        paragraphs = [_extract_paragraph(para)
                      for para in doc.paragraphs if para]
        if len(paragraphs) > 0:
            return [para for para in paragraphs if para is not None]
        return []
    except Exception as e:
        print(str(e))


def _extract_paragraph(para):
    runs = [_extract_run(run) for run in para.runs if run.text.strip()]
    if runs:
        return {
            KEY_TEXT: para.text.strip(),
            KEY_RUNS: runs
        }
    return None


def _extract_run(run):
    run_text = run.text
    run_type = _get_run_type(run)
    return {KEY_VALUE: run_text, KEY_TYPE: run_type}


def _get_run_type(run):
    if run.bold:
        return KEY_BOLD
    elif run.italic:
        return KEY_ITALIC
    elif run.underline:
        return KEY_UNDERLINE
    elif run.font.strike:
        return KEY_STRIKE
    return KEY_TEXT


def _get_letters(path):
    try:
        files = os.listdir(path)
        letters = [f for f in files if os.path.isfile(os.path.join(path, f))]
        letters.sort()
        return letters
    except Exception as e:
        print(str(e))


def _get_letters_from_raw(letter_id, raw_letter):

    paragraphs = []
    sequences = []
    sequence = {}

    if raw_letter and len(raw_letter) > 0:

        raw_letter.reverse()

        # iterate paragraphs from the end of the letter
        for i in range(len(raw_letter)):

            para = raw_letter[i]

            # if the current paragraph is not a sequence, process
            # otherwise it has been already processed in the previous iteration
            sequence_match = re.match(REGEX_SEQUENCE, para[KEY_TEXT])
            if sequence_match:

                paragraphs.reverse()

                sequence[KEY_REPRESENTATION] = sequence_match.group(0)
                sequence[KEY_PARAGRAPHS] = paragraphs

                # Check if the next paragraph is a sequence
                #if i+1 < len(raw_letter) and re.match(REGEX_SEQUENCE, raw_letter[i+1][KEY_TEXT]):
                #    page[KEY_REPRESENTATION] = raw_letter[i+1][KEY_TEXT]

                # restore sequence
                sequences.append(sequence)
                sequence = {}
                paragraphs = []

              # otherwise, if the paragraph is not a page, add it to the letter
            #elif not re.search(REGEX_PAGE, para[KEY_TEXT]):
            else:
              paragraphs.append(para)
                    

        # Order pages from first to last
        sequences.reverse()
        for i, sequence in enumerate(sequences):
            sequence[KEY_ID] = i+1
        

    return {
        KEY_ID: letter_id,
        KEY_PAGES: sequences
    }


def _write_txt(page, path, name):

    if not os.path.isdir(path):
        os.mkdir(path)

    try:
        with open(os.path.join(path, name), "w") as f:
            for para in page[KEY_PARAGRAPHS]:
                f.write(para[KEY_TEXT] + "\n")
    except Exception as e:
        print(str(e))


def _write_html(page, path, name):
    if not os.path.isdir(path):
        os.mkdir(path)

    try:
        with open(os.path.join(path, name), "w") as f:
            f.write("<html>\n")
            f.write("<body>\n")
            for _, para in enumerate(page[KEY_PARAGRAPHS]):
                f.write("<p>")
                for run in para[KEY_RUNS]:
                    if run[KEY_TYPE] == KEY_BOLD:
                        f.write(f"<b>{run[KEY_VALUE]}</b>")
                    elif run[KEY_TYPE] == KEY_ITALIC:
                        f.write(f"<i>{run[KEY_VALUE]}</i>")
                    elif run[KEY_TYPE] == KEY_UNDERLINE:
                        f.write(f"<u>{run[KEY_VALUE]}</u>")
                    elif run[KEY_TYPE] == KEY_STRIKE:
                        f.write(f"<s>{run[KEY_VALUE]}</s>")
                    else:
                        f.write(f"{run[KEY_VALUE]}")
                f.write("</p>\n")
            f.write("</body>\n")
            f.write("</html>\n")
    except Exception as e:
        print(str(e))


def _restore(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)


def _create_graph_letter(letter, output_path):

    letter_id = letter[KEY_ID]

    if not os.path.exists(os.path.join(output_path, 'ttl')):
        os.mkdir(os.path.join(output_path, 'ttl'))

    for page in letter[KEY_PAGES]:
        g = _create_graph(page, letter_id)
        g.serialize(os.path.join(output_path, 'ttl', f'{letter_id}_{
                    page[KEY_ID]}.ttl'), format='turtle')


def trailing_zeros(number):
    number_str = str(number)
    if len(number_str) >= 5:
        return number_str[:5]
    else:
        return number_str.rjust(5, '0')


def _create_graph(page, letter_id):
    g = Graph()

    #letter_id = trailing_zeros(letter_id)
    page_id = page[KEY_ID]

    LETTER_NODE = URIRef(f"{RESOURCE}letter/{letter_id}")
    PAGE_NODE = URIRef(f"{RESOURCE}letter/{letter_id}/page/{page_id}")
    PAGE_NODE_DOCUMENT = URIRef(
        f"{RESOURCE}letter/{letter_id}/document/{page_id}")

    try:

        g.add((PLATFORM.fileContainer, LDP.contains, PAGE_NODE_DOCUMENT))
        g.add((PAGE_NODE_DOCUMENT, RDF.type, PLATFORM.File))
        g.add((PAGE_NODE_DOCUMENT, RDF.type, LDP.Resource))
        g.add((PAGE_NODE_DOCUMENT, RDF.type, URIRef(
            f'{BASE_URI}ontology/Document')))
        g.add((PAGE_NODE_DOCUMENT, RDFS.label, Literal(
            f'LDP Container of document file of {letter_id}_{page_id}.html', datatype=XSD.string)))
        g.add((PAGE_NODE_DOCUMENT, PLATFORM.fileContext, URIRef(
            'http://www.researchspace.org/resource/TextDocuments')))
        g.add((PAGE_NODE_DOCUMENT, PLATFORM.fileName, Literal(
            f'{letter_id}_{page_id}.html', datatype=XSD.string)))
        g.add((PAGE_NODE_DOCUMENT, PLATFORM.mediaType,
               Literal('form-data', datatype=XSD.string)))
        g.add((PAGE_NODE_DOCUMENT, PROV.generatedAtTime, Literal(
            datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), datatype=XSD.dateTime)))
        g.add((PAGE_NODE_DOCUMENT, PROV.wasAttributedTo, URIRef(
            'http://www.researchspace.org/resource/admin')))
        g.add((PAGE_NODE, CRM.P129i_is_subject_of, PAGE_NODE_DOCUMENT))

        text = ''
        for paragraph in page[KEY_PARAGRAPHS]:
            text += paragraph[KEY_TEXT] + '\n'

        g.add((PAGE_NODE, RDF.value, Literal(text, datatype=XSD.string)))

        # Visual representation thumbnail
        IMAGE_NODE = URIRef(f'{IMG_BASE_URI}{page[KEY_REPRESENTATION]}.jpg')
        g.add((IMAGE_NODE, RDF.type, CRM.E38_Image))
        g.add((IMAGE_NODE, CRM.P2_has_type, BG['thumbnail_img']))
        g.add((IMAGE_NODE, RDF.type, URIRef(
            'http://www.researchspace.org/ontology/EX_Digital_Image')))
        g.add((PAGE_NODE, CRM.P183i_has_representation, IMAGE_NODE))

        # Visual representation IIIF
        IMAGE_NODE = URIRef(f'{IMG_BASE_URI_IIIF_START}{
                            page[KEY_REPRESENTATION]}.jpg{IMG_BASE_URI_IIIF_END}')
        g.add((IMAGE_NODE, RDF.type, CRM.E38_Image))
        g.add((IMAGE_NODE, CRM.P2_has_type, BG['iiif_img']))
        g.add((IMAGE_NODE, RDF.type, URIRef(
            'http://www.researchspace.org/ontology/EX_Digital_Image')))
        g.add((PAGE_NODE, CRM.P183i_has_representation, IMAGE_NODE))

        g.add((PAGE_NODE, RDF.type, BG['Page_Letter']))
        # g.add((PAGE_NODE, RDF.type, CRM['E22_Man-Made_Object']))
        g.add((PAGE_NODE, RDFS.label, Literal(page_id, datatype=XSD.string)))
        g.add((PAGE_NODE, BG['index'], Literal(page_id, datatype=XSD.string)))
        g.add((PAGE_NODE, BG['part_of'], LETTER_NODE))

        g.namespace_manager.bind('Platform', PLATFORM,
                                 override=True, replace=True)
        g.namespace_manager.bind('bg', BG, override=True, replace=True)
        g.namespace_manager.bind('crm', CRM, override=True, replace=True)
        g.namespace_manager.bind('crmdig', CRMDIG, override=True, replace=True)
        g.namespace_manager.bind('ldp', LDP, override=True, replace=True)
        g.namespace_manager.bind('prov', PROV, override=True, replace=True)

    except Exception as e:
        print(e)

    return g


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
        path = os.path.join(os.path.abspath(os.getcwd()), 'upload', 'psw.ini')
        config.read(path)

        return {
            KEY_USERNAME: config.get(type, KEY_USERNAME),
            KEY_PASSWORD: config.get(type, KEY_PASSWORD),
            KEY_ENDPOINT: config.get(type, KEY_ENDPOINT)
        }

    except Exception as ex:
        print('Error. Have you created the psw.ini file? see readme.md')
        print(str(ex))

def count_rows_in_csv(csv_file, required_columns):
    with open(csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Read the header row
        
        # Get the indices of the required columns
        required_indices = [headers.index(col) for col in required_columns if col in headers]

        valid_row_count = 0
        
        # Iterate through the rows and check for non-null values in the required columns
        for row in reader:
            if all(row[idx].strip() for idx in required_indices):  # Check if all required columns are non-empty
                valid_row_count += 1

    return valid_row_count

@click.command()
@click.option('-u', 'exec_upload', is_flag=True, help="Execute the upload", default=False)
@click.option('-P', 'prune', is_flag=True, help="Prune output folder", default=False)
@click.option('-direct', 'direct_path', help="Only for development purposes", type=click.Path())
@click.option('-l', 'limit', help="Subset of letters to iterate", type=int, default=-1)
@click.option('-c', 'upload_config', type=str, help="profile to select usr, psw, and endpoint from psw.ini. see readme", default='belle_greene')
def exec(exec_upload, prune, direct_path, limit, upload_config):
    cur_path = os.path.dirname(os.path.realpath(__file__))

    input_path = os.path.join(cur_path, "input")
    output_path = os.path.join(cur_path, "output")

    parsed_letters = []

    if prune:
        _restore(output_path)

    letters_name = _get_letters(input_path)

    # iterate over letter names
    for i, document in enumerate(letters_name):

        letter_id = '0' + document.replace('.docx', '').replace('BG_BB_', '')

        # parse docx and extract paragraphs
        letter_para = _extract_paragraphs_from_docx(
            os.path.join(input_path, document))

        # get letter from raw paragraphs
        letter = _get_letters_from_raw(letter_id, letter_para)

        for _, page in enumerate(letter[KEY_PAGES]):

            _write_txt(page, os.path.join(output_path, "txt"),
                       f'{letter[KEY_ID]}_{page[KEY_ID]}.txt')
            _write_html(page, os.path.join(output_path, "html"),
                        f'{letter[KEY_ID]}_{page[KEY_ID]}.html')
            if direct_path:
                _write_html(page, direct_path, f'{
                            letter[KEY_ID]}_{page[KEY_ID]}.html')

        parsed_letters.append(letter)

        # break if limit is reached
        if limit > 0 and i >= limit:
            break

    # execute pandas
    letters_df = pd.read_csv(os.path.join(cur_path, os.pardir, 'BG to BB Letters_Spreadsheet - Sheet1.csv'))
    letters_df.set_index('Letter_ID', inplace=True)
    
    total_letters = count_rows_in_csv(os.path.join(cur_path, os.pardir, 'BG to BB Letters_Spreadsheet - Sheet1.csv'), ['Letter_ID'])

    print(f'Total number of letters:\t\t{total_letters}')
    if limit > 0:
        print(f'Limit:\t\t\t\t\t{limit}')
    print(f'Total number of parsed letters:\t\t{len(parsed_letters)}')

    # if totale letters in the csv file is different from the parsed letters
    # find which one, from the csv file, is missing in the parsed letters
    if total_letters != len(parsed_letters):
        for letter_id in letters_df.index:
            if letter_id not in [letter[KEY_ID] for letter in parsed_letters]:
                print(f'Letter {letter_id} is missing in the parsed letters')
    
    print()      

    # Check the pages
    for letter_id, row in letters_df.iterrows():
        try:
            # Get pages from control data
            control_pages_str = str(row['I Tatti file name(s)']).strip()
            control_pages = [page.strip()
                             for page in control_pages_str.split(',') if page.strip()]
            num_control_pages = len(control_pages)

            # Check if the letter exists in letters_df
            parsed_letter = next ((item for item in parsed_letters if item[KEY_ID] == letter_id), None)
            if not parsed_letters:
                raise KeyError(
                    f"Letter {letter_id} not found in parsed_letters")
            if KEY_PAGES not in parsed_letter:
                raise ValueError(f"Letter {letter_id} does not have pages")

            num_letter_pages = len(parsed_letter[KEY_PAGES])
            if num_control_pages != num_letter_pages:
                for control_page in control_pages:
                    if control_page not in [page[KEY_REPRESENTATION] for page in parsed_letter[KEY_PAGES] if KEY_REPRESENTATION in page]:
                        print(f"""Letter {letter_id}: Page {control_page} is missing.""")
                        
                raise ValueError(f"""Letter {letter_id}: Number of pages do not match. Control: {
                                 num_control_pages}, Parsed: {num_letter_pages}""")
        except Exception as e:
            if "argument of type 'NoneType' is not iterable" != str(e):
                print(str(e))
            continue

    # generate graphs for each letter page
    for letter in parsed_letters:
        _create_graph_letter(letter, output_path)

    # upload graphs
    if exec_upload:
        credentials = _get_credentials(upload_config)

        for letter in parsed_letters:
            letter_id = letter[KEY_ID]

            for page in letter[KEY_PAGES]:
                page_id = page[KEY_ID]
                ttl = f'{letter_id}_{page_id}.ttl'
                graph_name = f'{
                    RESOURCE}letter/{letter_id}/document/{page_id}/context'
                print(f'\nExecuting {graph_name} ...')

                r_url = f'{credentials[KEY_ENDPOINT]
                           }rdf-graph-store/?graph={graph_name}'

                print('Deleting  ...')
                delete_cmd = f'curl -u {credentials[KEY_USERNAME]}:{
                    credentials[KEY_PASSWORD]} -X DELETE {r_url}'
                os.system(delete_cmd)

                print('Uploading ...\n')
                upload_cmd = f"curl -u {credentials[KEY_USERNAME]}:{credentials[KEY_PASSWORD]
                                                                    } -X POST -H 'Content-Type: text/turtle' --data-binary '@{os.path.join(output_path, "ttl", ttl)}' {r_url}"
                os.system(upload_cmd)


if __name__ == '__main__':
    exec()
