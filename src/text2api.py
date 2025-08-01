#!/usr/bin/env python3

"""
    - Text-to-API: Using LLM API to generate SQLs (one SQL per prompt)
"""
import os
import json
import argparse
from tqdm import tqdm
from pathlib import Path
from tools.help_func import *
from models.model_card import api_request
from mschema.extract_schema import decouple_question_schema, ddl_schema, m_schema


def generate_comment_prompt(question, knowledge=None):
    """
        - Add helpful instructions to guide the LLM to generate ideal response
    """
    pattern_prompt_no_kg = "-- Using valid SQLite, answer the following questions for the tables provided above."
    pattern_prompt_kg = "-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above."
    # question_prompt = "-- {}".format(question) + '\n SELECT '
    question_prompt = "-- {}".format(question)
    knowledge_prompt = "-- External Knowledge: {}".format(knowledge)

    if not knowledge:
        result_prompt = pattern_prompt_no_kg + '\n' + question_prompt
    else:
        result_prompt = knowledge_prompt + '\n' + pattern_prompt_kg + '\n' + question_prompt

    return result_prompt


def cot_wizard():
    cot = "\nGenerate the SQL after thinking step by step: "
    return cot


def few_shot():
    ini_table = "CREATE TABLE singer\n(\n    singer_id         TEXT not null\n        primary key,\n    nation       TEXT  not null,\n    sname       TEXT null,\n    dname       TEXT null,\n    cname       TEXT null,\n    age    INTEGER         not null,\n    year  INTEGER          not null,\n    birth_year  INTEGER          null,\n    salary  REAL          null,\n    city TEXT          null,\n    phone_number   INTEGER          null,\n--     tax   REAL      null,\n)"
    ini_prompt = "-- External Knowledge: age = year - birth_year;\n-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.\n-- How many singers in USA who is older than 27?\nThe final SQL is: Let's think step by step."
    ini_cot_result = "1. referring to external knowledge, we need to filter singers 'by year' - 'birth_year' > 27; 2. we should find out the singers of step 1 in which nation = 'US', 3. use COUNT() to count how many singers. Finally the SQL is: SELECT COUNT(*) FROM singer WHERE year - birth_year > 27;</s>"
    one_shot_demo = ini_table + '\n' + ini_prompt + '\n' + ini_cot_result
    
    return one_shot_demo


def few_shot_no_kg():
    ini_table = "CREATE TABLE singer\n(\n    singer_id         TEXT not null\n        primary key,\n    nation       TEXT  not null,\n    sname       TEXT null,\n    dname       TEXT null,\n    cname       TEXT null,\n    age    INTEGER         not null,\n    year  INTEGER          not null,\n    age  INTEGER          null,\n    salary  REAL          null,\n    city TEXT          null,\n    phone_number   INTEGER          null,\n--     tax   REAL      null,\n)"
    ini_prompt = "-- External Knowledge:\n-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.\n-- How many singers in USA who is older than 27?\nThe final SQL is: Let's think step by step."
    ini_cot_result = "1. 'older than 27' refers to age > 27 in SQL; 2. we should find out the singers of step 1 in which nation = 'US', 3. use COUNT() to count how many singers. Finally the SQL is: SELECT COUNT(*) FROM singer WHERE age > 27;</s>"
    one_shot_demo = ini_table + '\n' + ini_prompt + '\n' + ini_cot_result
    
    return one_shot_demo


def generate_combined_prompts_one(db_path, schema_dict, question, knowledge=None):
    db_name = db_path.split("/")[-1].split(".")[0]
    schema_prompt = schema_dict[db_name]

    comment_prompt = generate_comment_prompt(question, knowledge)
    """
        - 2025.7.7
    """
    prompt_template = "Generate only the SQL query for the following requirement without any explanations, comments, or reasoning. \nBegin with ```sql, end with ```"

    # combined_prompts = schema_prompt + '\n\n' + comment_prompt + cot_wizard() + '\nSELECT '
    combined_prompts = schema_prompt + '\n\n' + comment_prompt + '\n\n' + prompt_template
    # combined_prompts = few_shot() + '\n\n' + schema_prompt + '\n\n' + comment_prompt
    return combined_prompts


def collect_response_from_api(db_path_list, question_list, api_name, api_key, schema_path, schema_type, knowledge_list=None):
    '''
    :param db_path: str
    :param question_list: []
    :return: dict of responses collected from openai
    '''
    response_list = []

    for i, question in tqdm(enumerate(question_list)):
        print('\n--------------------- Processing {}th question ---------------------'.format(i))
        print('The question is: {}'.format(question))
        
        if knowledge_list:
            cur_prompt = generate_combined_prompts_one(db_path=db_path_list[i], schema_path=schema_path,
                                                       question=question, 
                                                       schema_type = schema_type,
                                                        knowledge=knowledge_list[i])
        else:
            cur_prompt = generate_combined_prompts_one(db_path=db_path_list[i], schema_path=schema_path,
                                                       question=  question,
                                                       schema_type = schema_type)
        
        plain_result = api_request(api_name, api_key, prompt=cur_prompt)

        """
            - Plain result contains useless comments, need to be removed.
        """
        plain_result = extract_sql_from_response(plain_result)
        
        # determine wheter the sql is wrong
        if type(plain_result) == str:
            sql = plain_result
        else:
            response_list.append(0)
            continue
        # responses_dict[i] = sql
        db_id = db_path_list[i].split('/')[-1].split('.sqlite')[0]
        sql = sql + '\t----- bird -----\t' + db_id # to avoid unpredicted \t appearing in codex results
        response_list.append(sql)
    return response_list


def question_package(data_json, knowledge=False):
    question_list = []
    for data in data_json:
        question_list.append(data['question'])
    return question_list

def knowledge_package(data_json, knowledge=False):
    knowledge_list = []
    for data in data_json:
        knowledge_list.append(data['evidence'])
    return knowledge_list


def generate_sql_file(sql_lst, output_path=None):
    result = {}
    for i, sql in enumerate(sql_lst):
        result[i] = sql
    
    if output_path:
        directory_path = os.path.dirname(output_path)  
        new_directory(directory_path)
        json.dump(result, open(output_path, 'w'), indent=4)
    
    return result    


def append_query_to_file(query_data, file_path):
    with open(file_path, "a", encoding="utf-8") as f: 
        f.write(json.dumps(query_data, ensure_ascii=False) + "\n")


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--eval_path', type=str, default='')
    args_parser.add_argument('--mode', type=str, default='dev')
    args_parser.add_argument('--api_name', type=str, default='DeepSeek-chat')
    args_parser.add_argument('--example_rows', type=int, default=0, help='example rows')
    args_parser.add_argument('--schema_type', type=str, default='ddl_schema', help='ddl_schema or m_schema')
    args_parser.add_argument('--schema_dir', type=str, default='./archive/dev-schema', help='m_schema store dir')
    args_parser.add_argument('--db_root_path', type=str, default='')
    args_parser.add_argument('--api_key', type=str, required=True)
    args_parser.add_argument('--data_output_path', type=str)
    args_parser.add_argument('--use_knowledge', action="store_true", help='whether to use knowledge')
    args_parser.add_argument('--chain_of_thought', action="store_true", help='whether to use CoT')
    args = args_parser.parse_args()

    # LLM response SQLs
    responses = []
    """
        - 2025.7.10
        - Intermediate file to store SQLs
    """
    Path(args.data_output_path).mkdir(parents=True, exist_ok=True)
    temp_file = Path(args.data_output_path) / "temp.json"

    # Having temp file -> adding temp SQLS
    temp_len = 0
    if os.path.exists(temp_file):
        print("*****Find temp file! Continue from the lastest point!*****\n")
        with open(temp_file, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                record = json.loads(line.strip())
                # print(record[str(idx)])
                responses.append(record[str(idx)])

        temp_len = len(responses)

    
    eval_data = json.load(open(args.eval_path, 'r'))

    """
        - Mini test, split small amount
    """
    # eval_data = eval_data[0:30]
    
    eval_data = eval_data[temp_len:]
    question_list, db_path_list, knowledge_list = decouple_question_schema(datasets=eval_data, db_root_path=args.db_root_path)
    assert len(question_list) == len(db_path_list) == len(knowledge_list)

    """
        - 2025.7.23
    """
    if args.schema_type == "ddl_schema":
        schema_prompt_dict = ddl_schema(db_path_list, args.schema_dir, num_rows=args.example_rows)
    elif args.schema_type == "m_schema":
        schema_prompt_dict = m_schema(db_path_list, args.schema_dir, num_rows=args.example_rows)
    else:
        raise ValueError("UNKNOWN SCHEMA TYPE")
    
    for i, question in tqdm(enumerate(question_list)):
        print('\n--------------------- Processing {}th question ---------------------'.format(temp_len + i))
        print('The question is: {}'.format(question))

        if not args.use_knowledge:
            knowledge_list[i] = None

        cur_prompt = generate_combined_prompts_one(db_path=db_path_list[i], schema_dict=schema_prompt_dict,
                                                       question=question,
                                                        knowledge=knowledge_list[i])
        

        resp = api_request(args.api_name, args.api_key, prompt=cur_prompt)

        max_attempts = 3
        attempt = 0
        sql = None 

        while attempt < max_attempts:
            try:
                resp_sql = extract_sql_from_response(resp)
                if isinstance(resp_sql, str):
                    sql = resp_sql
                    break
                else:
                    raise ValueError("NONE SQL Block")
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"THE {attempt + 1}th attempt error: {e}")
                attempt += 1
                if attempt < max_attempts:
                    resp = api_request(args.api_name, args.api_key, prompt=cur_prompt)
                else:
                    print("MAX attempt, return")
                    sql = 0

        print(f"Answer SQL: {sql}")

        if sql != 0:
            db_id = db_path_list[i].split('/')[-1].split('.sqlite')[0]
            sql = sql + '\t----- bird -----\t' + db_id # to avoid unpredicted \t appearing in codex results
        
        responses.append(sql)

        """
            - 2025.7.10
        """
        data = {temp_len + i: sql}
        append_query_to_file(data, temp_file)
    
    if args.chain_of_thought:
        output_name = args.data_output_path + 'predict_' + args.mode + '_cot.json'
    else:
        output_name = args.data_output_path + 'predict_' + args.mode + '.json'


    generate_sql_file(sql_lst=responses, output_path=output_name)
    print('successfully collect results from {} for {} evaluation; Use knowledge: {}; Use COT: {}'.format(
        args.api_name,args.mode, args.use_knowledge, args.chain_of_thought))
