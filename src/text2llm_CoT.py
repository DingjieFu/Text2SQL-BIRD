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
    SQLs, thinks = [], []
    Path(args.data_output_path).mkdir(parents=True, exist_ok=True)
    temp_sql_file = Path(args.data_output_path) / "temp_sql.json"
    temp_think_file = Path(args.data_output_path) / "temp_think.json"

    # Having temp file -> adding temp SQLS
    temp_sql_len = 0
    if os.path.exists(temp_sql_file):
        print("*****Find temp file! Continue from the lastest point!*****\n")
        with open(temp_sql_file, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                record = json.loads(line.strip())
                # print(record[str(idx)])
                SQLs.append(record[str(idx)])

        with open(temp_think_file, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                record = json.loads(line.strip())
                thinks.append(record[str(idx)])
        temp_sql_len = len(SQLs)


    eval_data = json.load(open(args.eval_path, 'r'))
    eval_data = eval_data[temp_sql_len:]

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
        print('\n--------------------- Processing {}th question ---------------------'.format(temp_sql_len + i))
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
            # prompt = XiYanSQL_TEMPLATE_EN.format(db_schema=schema_prompt, evidence=hint, question=question)
        elif "seeklhy/mniSQL" in args.repo_id:
            prompt = OmniSQL_USER_TEMPLATE.format(db_details=schema_prompt, question = hint+"\n"+question)


        message = [{"role": "system", "content": XiYanSQL_SYSTEM_EN}]
        message.append({'role': 'user', 'content': prompt})
        response = gen_sql(model, tokenizer, message)

        while True:
            think, sql = extract_xml_answer(response)
            if think and sql: 
                break
            response = gen_sql(model, tokenizer, message)
   
        print(f"\n\033[32mThink chain\033[0m: {think}")
        print(f"\n\033[33mSQL query\033[0m: {sql}")


        db_id = db_path_list[i].split('/')[-1].split('.sqlite')[0]
        sql = sql + '\t----- bird -----\t' + db_id
        SQLs.append(sql)
        thinks.append(think)
        
        data_sql = {temp_sql_len + i: sql}
        append_query_to_file(data_sql, temp_sql_file)

        data_think = {temp_sql_len + i: think}
        append_query_to_file(data_think, temp_think_file)


    output_sql = args.data_output_path + 'predict_' + args.mode + '.json'
    output_think = args.data_output_path + 'think_' + args.mode + '.json'

    generate_sql_file(sql_lst=SQLs, output_path=output_sql)
    generate_sql_file(sql_lst=thinks, output_path=output_think)
    print('successfully collect results from {} for {} evaluation'.format(args.repo_id, args.mode))
