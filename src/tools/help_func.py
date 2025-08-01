import os
import re
import json


def new_directory(path):  
    """
        - mkdir
    """
    if not os.path.exists(path):  
        os.makedirs(path)  
        

def generate_sql_file(sql_lst, output_path=None):
    """
        - Generate sql file -> conform to BIRD-bench format
    """
    result = {}
    for i, sql in enumerate(sql_lst):
        result[i] = sql
    
    if output_path:
        directory_path = os.path.dirname(output_path)  
        new_directory(directory_path)
        json.dump(result, open(output_path, 'w'), indent=4)
    return result    


def append_query_to_file(query_data, file_path, encoding="utf8"):
    """
        - For resume running, generate temp file
    """
    with open(file_path, "a", encoding=encoding) as f: 
        f.write(json.dumps(query_data, ensure_ascii=False) + "\n")


def load_json_file(file_path, encoding="utf8"):
    """
        - Load json file, return contents
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return json.load(f)


def write_json_file(data, file_path, encoding="utf8"):
    """
        - Write json file, save contents
    """
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(data, f, indent=4)


def load_txt_file(file_path, encoding='utf-8'):
    """
        - Load .txt/.sql file
    """
    list_line = []
    with open(file_path, 'r', encoding=encoding) as f:
        list_line = f.readlines()
        list_line = [row.rstrip("\n") for row in list_line]
        return list_line


def write_txt_file(data, file_path, encoding='utf-8'):
    """
        - Write .txt/.sql file
    """
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding=encoding) as f:
            f.writelines(data)


def extract_sql_from_response(resp):
    """
        - (OmniSQL-series)
        - For different output format, extract the sql block 
    """
    match = re.search(r"```sql\n(.*?)\n```", resp, re.DOTALL)
    if match:
        extracted_sql = match.group(1)
    else:
        return 0
    sql_query = re.sub(r"--.*?$", r"", extracted_sql, flags=re.MULTILINE).rstrip()
    return sql_query if sql_query.endswith(';') else sql_query + ';'


def extract_xml_answer(text: str) -> str:
    """
        - parser xml format -> <think> ... </think> <answer> ... </answer>
    """
    pattern = r"<think>(.*?)</think>\s*<answer>(.*?)</answer>"
    try:
        think, answer = re.findall(pattern, text, re.DOTALL)[0]
    except Exception as e:
        return None, None
    return think.strip(), answer.strip()
