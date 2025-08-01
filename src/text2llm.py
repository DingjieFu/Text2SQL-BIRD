"""
    - Text-to-LLM: Using open-source LLM to generate SQLs (one SQL per prompt)
"""
import os
import json
import argparse
from tqdm import tqdm
from pathlib import Path
from tools.help_func import *
from tools.prompt_templates import *
from models.model_card import *
from mschema.extract_schema import decouple_question_schema, ddl_schema, m_schema


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--eval_path', type=str, default='')
    args_parser.add_argument('--mode', type=str, default='dev')
    args_parser.add_argument('--repo_id', type=str, default="")
    args_parser.add_argument('--example_rows', type=int, default=0, help='example rows')
    args_parser.add_argument('--schema_type', type=str, default='m_schema', help='ddl_schema or m_schema')
    args_parser.add_argument('--schema_dir', type=str, default='', help='schema store dir')
    args_parser.add_argument('--db_root_path', type=str, default='')
    args_parser.add_argument('--data_output_path', type=str, default="")
    args = args_parser.parse_args()


    # Response SQLs
    responses = []
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
    eval_data = eval_data[temp_len:]

    question_list, db_path_list, knowledge_list = decouple_question_schema(datasets=eval_data, db_root_path=args.db_root_path)
    assert len(question_list) == len(db_path_list) == len(knowledge_list)

    if args.schema_type == "ddl_schema":
        schema_prompt_dict = ddl_schema(db_path_list, args.schema_dir, num_rows=args.example_rows)
    elif args.schema_type == "m_schema":
        schema_prompt_dict = m_schema(db_path_list, args.schema_dir, num_rows=args.example_rows)
    else:
        raise ValueError("UNKNOWN SCHEMA TYPE")

    model, tokenizer = load_model(args.repo_id)
    
    for i, question in tqdm(enumerate(question_list)):
        print('\n--------------------- Processing {}th question ---------------------'.format(temp_len + i))
        print('The question is: {}'.format(question))
        
        """
            - Get Database Schema 
        """
        db_name = db_path_list[i].split("/")[-1].split(".")[0]
        schema_prompt = schema_prompt_dict[db_name]
        
        hint = knowledge_list[i] if knowledge_list[i] else ""

        if "XGenerationLab/XiYanSQL" in args.repo_id:
            # dialects -> ['SQLite', 'PostgreSQL', 'MySQL']
            prompt = XiYanSQL_TEMPLATE_CN.format(dialect="SQLite", db_schema=schema_prompt, question=question, evidence=hint)
        elif "seeklhy/mniSQL" in args.repo_id:
            prompt = OmniSQL_USER_TEMPLATE.format(db_details=schema_prompt, question = hint+"\n"+question)


        message = [{"role": "system", "content": XiYanSQL_SYSTEM_EN}]
        message.append({'role': 'user', 'content': prompt})
        response = gen_sql(model, tokenizer, message)


        max_attempts = 3
        attempt = 0
        sql = None 

        while attempt < max_attempts:
            try:
                """
                    - 2025.7.18
                    - Different LLMs (with specific user prompt) produce distinct output format
                """
                if "seeklhy/OmniSQL" in args.repo_id:
                    response = extract_sql_from_response(response)
                
                if isinstance(response, str):
                    sql = response
                    break
                else:
                    raise ValueError("NONE SQL Block")
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"THE {attempt + 1}th attempt error: {e}")
                attempt += 1
                if attempt < max_attempts:
                    resp = gen_sql(model, tokenizer, message)
                else:
                    print("MAX attempt, return")
                    sql = 0

        print(f"Answer SQL: {response}")

        if sql != 0:
            db_id = db_path_list[i].split('/')[-1].split('.sqlite')[0]
            response = response + '\t----- bird -----\t' + db_id
        
        responses.append(response)
        print(f"Answer SQL: {response}")

        """
            - 2025.7.10
        """
        data = {temp_len + i: response}
        append_query_to_file(data, temp_file)

    output_name = args.data_output_path + 'predict_' + args.mode + '.json'

    generate_sql_file(sql_lst=responses, output_path=output_name)
    print('successfully collect results from {} for {} evaluation'.format(args.repo_id, args.mode))
