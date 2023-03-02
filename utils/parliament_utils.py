import shutil
import urllib.request as request
from contextlib import closing
from urllib.error import URLError
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import datetime
from tqdm.notebook import tqdm

def save_xml_from_ftp(url: 'str', out_path: 'str (.xml/.txt)') -> 'XML file @ out_path':
    '''
    TODO...
    '''
    
    try:
        with closing(request.urlopen(url)) as r:
            with open(out_path, 'wb') as f:
                shutil.copyfileobj(r, f)

    except URLError as e:
        if e.reason.find('No such file or directory') >= 0:
            raise Exception('FileNotFound')
        else:
            raise Exception(f'Something else happened. "{e.reason}"')
            
def list_meetings_in_sessions(session_ids: 'list'):
    '''
    TODO...
    '''
    
    files = []
    
    for id_ in tqdm(session_ids):
        url = f'ftp://oda.ft.dk/ODAXML/Referat/samling/{id_}'
        out_path = f'data/raw/parliament/session_docs/session_{id_}.xml'
        
        files.append(out_path)
        
        save_xml_from_ftp(url, out_path)
        
    return files

def extract_transcript_filenames(session_filenames):
    '''
    TODO...
    '''
    
    all_transcript_names = dict()
    
    for file in tqdm(session_filenames):
        with open(file, 'r') as f:
            contents = f.readlines()
        
        transcript_filenames = [line.replace('\n','').split(' ')[-1] for line in contents]
        all_transcript_names[transcript_filenames[0].split('_')[0]] = transcript_filenames
    
    return all_transcript_names

def save_transcripts_from_ftp(id_dict):
    '''
    TODO...
    '''
    
    for session_id in id_dict.keys():
        print(f'\nCollecting transcripts from session {session_id}...')
        
        try:
            for transcript_filename in tqdm(id_dict[session_id]):

                url = f'ftp://oda.ft.dk/ODAXML/Referat/samling/{session_id}/{transcript_filename}'
                out_path = f'data/raw/parliament/xml_transcripts/transcript_{transcript_filename}.xml'
                save_xml_from_ftp(url, out_path)
                
        except Exception as ex:
            ex_name = type(ex).__name__
            print(f'Whoops, {ex_name}!')
            
def xml_to_str(xml_path):
    '''Open XML-file and return it as a string.
    '''
    with open(xml_path, errors='ignore') as f:
        xml_str = f.read()

    return xml_str

def xml_str_to_rows(xml_str):
    '''Convert XML text string to a list of dictionaries
    with selected data fields extracted from markup.
    '''
    xml_rows = list()
    xml_soup = BeautifulSoup(xml_str, 'lxml')

    for item in xml_soup.select('Tale'):
        xml_rows.append(xml_to_dict(item))

    return xml_rows

def xml_to_dict(item):
    '''Extract data from XML and return as a dictionary.
    '''

    # Error handling in case of missing data for each data field.
    first_name = item.select_one('OratorFirstName')
    first_name = first_name.text if first_name else ''
    
    last_name = item.select_one('OratorLastName')
    last_name = last_name.text if last_name else ''

    group_name = item.select_one('GroupNameShort')
    group_name = group_name.text if group_name else ''

    role = item.select_one('OratorRole')
    role = role.text if role else ''

    start_time = item.select_one('StartDateTime')
    start_time = start_time.text if start_time else ''

    # End time defaults to last available entry in case of consecutive segments.
    end_time = item.select('EndDateTime')
    end_time = end_time[-1].text if end_time else ''

    # Consecutive segments by the same speaker are joined together.
    text_segments = item.select('TaleSegment')
    text = ' '.join([' '.join([i.text for i in segment.select('char')]) for segment in text_segments]) if text_segments else ''

    # Collect and return extracted data in a dictionary
    xml_dict = {
    'first_name': first_name,
    'last_name': last_name,
    'group_name': group_name,
    'role': role,
    'start_time': start_time,
    'end_time': end_time,
    'text': text
    }

    return xml_dict

def parse_datetime(time_str):
    return datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')

def all_xml_to_df(data_folder, csv_file):

    #data_folder = 'data/test'

    #csv_file = 'file_name1.csv'

    # Use date, time and speech duration instead of start and end datetime format.
    convert_time = False

    # Get list of paths to files in data folder.
    file_paths = [Path(f) for f in Path(data_folder).iterdir()]	

    # List for appending data rows before export.
    rows = list()

    for path in tqdm(file_paths):
        
        try:
            xml_str = xml_to_str(path)
            rows.extend(xml_str_to_rows(xml_str))
        
        except Exception as ex:
            ex_name = type(ex).__name__
            print(f'Whoops, {ex_name} encountered in {path}!')

    # Convert data to pandas DataFrame, sort rows by time and export as csv.
    df = pd.DataFrame(rows, columns=rows[0].keys()).sort_values('start_time')

    if convert_time:
        df['date'] = df['start_time'].str.extract(r'(\d\d\d\d-\d\d-\d\d)T\d\d:\d\d:\d\d')
        df['time'] = df['start_time'].str.extract(r'\d\d\d\d-\d\d-\d\dT(\d\d:\d\d:\d\d)')
        df['duration'] = df.apply(lambda row: parse_datetime(row['end_time']) - parse_datetime(row['start_time']) if row['end_time'] else 0, axis=1)
        df = df[['first_name', 'last_name', 'group_name', 'role', 'date', 'time', 'duration', 'text']]

    df.to_csv(csv_file, index=False)