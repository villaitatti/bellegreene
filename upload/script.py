
import click
import os
import docx
import shutil
import re
import pandas as pd
from rdflib import Graph, URIRef, namespace, Namespace, Literal

REGEX_PAGE = r'\[p\.\s(\d+)\]'
REGEX_SEQUENCE = r'^\d+_\d{3}$'

KEY_PARAGRAPHS = 'paragraphs'
KEY_SEQUENCE = 'sequence'

def _extract_paragraphs_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return paragraphs
    except Exception as e:
        print(str(e))



def _get_letters(path):
    try:
        files = os.listdir(path)
        letters = [f for f in files if os.path.isfile(os.path.join(path, f))]
        letters.sort()
        return letters
    except Exception as e:
        print(str(e))

def _get_sequences_from_letters(raw_letter):
    sequences = {}
    letter = []
    raw_letter.reverse()
    
    # iterate paragraphs from the end of the letter
    for i in range(len(raw_letter)):
        
        para = raw_letter[i]
        
        # if the current paragraph is not a sequence, process
        # otherwise it has been already processed in the previous iteration
        if not re.match(REGEX_SEQUENCE, para):
        
            # if the paragraph is a page, add it to the pages
            match = re.search(REGEX_PAGE, para)
            
            if match:
                # extract number from paragraph 
                page_number = int(match.group(1))
                sequences[page_number] = {}

                letter.reverse()
                
                sequences[page_number][KEY_PARAGRAPHS] = letter
                
                # Check if the next paragraph is a sequence
                if i+1 < len(raw_letter) and re.match(REGEX_SEQUENCE, raw_letter[i+1]):
                    sequences[page_number][KEY_SEQUENCE] = raw_letter[i+1]
                
                # restore letters
                letter = []

            # otherwise, add the paragraph to the letter
            else:
                letter.append(para)

    return sequences

def _write_txt(paragraphs, path, name):

    if not os.path.isdir(path):
        os.mkdir(path)
    
    try:
        with open(os.path.join(path, name), "w") as f:
            for para in paragraphs:
                f.write(para + "\n")
    except Exception as e:
        print(str(e))

def _write_html(paragraphs, path, name):
    if not os.path.isdir(path):
        os.mkdir(path)
    
    try:
        with open(os.path.join(path, name), "w") as f:
            f.write("<html>\n")
            f.write("<body>\n")
            for para in paragraphs:
                f.write(f"<p>{para}</p>\n")
            f.write("</body>\n")
            f.write("</html>\n")
    except Exception as e:
        print(str(e))

def _restore(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)

def _create_graph(para):
    g = Graph()
    
    PAGE_NODE = Namespace("http://example.org/page/")

@click.command()
@click.option('-u', 'exec_upload', is_flag=True, help="Execute the upload", default=False)
@click.option('-P', 'prune', is_flag=True, help="Prune output folder", default=False)
@click.option('-direct', 'direct_path', type=click.Path())
@click.option('-l', 'limit', type=int, default=-1)
def exec(exec_upload, prune, direct_path, limit):
    cur_path = os.path.dirname(os.path.realpath(__file__))
    
    input_path = os.path.join(cur_path, "input")
    output_path = os.path.join(cur_path, "output")

    parsed_letters = {}

    if prune:
        _restore(output_path)
    
    letters_name = _get_letters(input_path)

    # iterate over letter names
    for cnt in range(1, len(letters_name)):
        
        letter_name = letters_name[cnt-1]
        letter_number = f'Letter {cnt}'
                
        # parse docx and extract paragraphs
        letter_para = _extract_paragraphs_from_docx(os.path.join(input_path, letter_name))

        # get sequences from paragraphs
        sequences = _get_sequences_from_letters(letter_para)

        parsed_letters[cnt] = sequences
    
        for key, sequence in sequences.items():

            _write_txt(sequence[KEY_PARAGRAPHS], os.path.join(output_path, "txt"), f'{letter_number}_{key}.txt')
            _write_html(sequence[KEY_PARAGRAPHS], os.path.join(output_path, "html"), f'{letter_number}_{key}.html')
            if direct_path:
                _write_html(sequence, direct_path, letter_number)
        
        # break if limit is reached
        if limit > 0 and cnt >= limit:
            break
        
    
    # execute pandas
    letters_df = pd.read_csv(os.path.join(input_path,'control.csv'))
    total_letters = len(letters_df)
    
    print(f'Total number of letters:\t\t{total_letters}')
    print(f'Total number of parsed letters:\t\t{len(parsed_letters.values())}')

    # Check if number of pages are not equal
    for key, parsed_letter in parsed_letters.items():
        row = letters_df.iloc[key-1]
        # from this row, get the cell with column number of pages
        num_pages = int(row['Number of Pages'])
        if num_pages != len(parsed_letter):
            print(f'Number of pages in Letter {key} is not equal to the number of pages in the parsed letter')


    # generate graphs
    
        
    # upload graphs
    

if __name__ == '__main__':
    exec()