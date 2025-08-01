import os
import json
import sqlite3
import argparse
from pathlib import Path
from sqlalchemy import create_engine
from mschema.schema_engine import SchemaEngine


def nice_look_table(column_names: list, values: list):
    rows = []
    # Determine the maximum width of each column
    widths = [max(len(str(value[i])) for value in values + [column_names]) for i in range(len(column_names))]
    # Print the column names
    header = ''.join(f'{column.rjust(width)} ' for column, width in zip(column_names, widths))
    # print(header)
    # Print the values
    for value in values:
        row = ''.join(f'{str(v).rjust(width)} ' for v, width in zip(value, widths))
        rows.append(row)
    rows = "\n".join(rows)
    final_output = header + '\n' + rows
    return final_output


def decouple_question_schema(datasets, db_root_path):
    question_list = []
    db_path_list = []
    knowledge_list = []
    for i, data in enumerate(datasets):
        question_list.append(data['question'])
        cur_db_path = db_root_path + data['db_id'] + '/' + data['db_id'] +'.sqlite'
        db_path_list.append(cur_db_path)
        knowledge_list.append(data['evidence'])
    return question_list, db_path_list, knowledge_list


def ddl_schema(db_path_list, store_dir, num_rows=None):
    schema_path = Path(store_dir) / f'DDLSchema_e{num_rows}.json'
    schema_prompts = {}
    if schema_path.exists():
        # print("[Already exists]")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_prompts = json.load(f)
    else:
        db_set = set()
        for _, db_path in enumerate(db_path_list):
            db_name = db_path.split("/")[-1].split(".")[0]
            if db_name in db_set:
                continue
            full_schema_prompt_list = []
            conn = sqlite3.connect(db_path)
            # Create a cursor object
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            schemas = {}
            for table in tables:
                if table == 'sqlite_sequence':
                    continue
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='{}';".format(table[0]))
                create_prompt = cursor.fetchone()[0]
                schemas[table[0]] = create_prompt
                if num_rows:
                    cur_table = table[0]
                    if cur_table in ['order', 'by', 'group']:
                        cur_table = "`{}`".format(cur_table)

                    cursor.execute("SELECT * FROM {} LIMIT {}".format(cur_table, num_rows))
                    column_names = [description[0] for description in cursor.description]
                    values = cursor.fetchall()
                    rows_prompt = nice_look_table(column_names=column_names, values=values)
                    verbose_prompt = "/* \n {} example rows: \n SELECT * FROM {} LIMIT {}; \n {} \n */".format(num_rows, cur_table, num_rows, rows_prompt)
                    schemas[table[0]] = "{} \n {}".format(create_prompt, verbose_prompt)
            conn.close()
            for k, v in schemas.items():
                full_schema_prompt_list.append(v)
            schema_prompt = "\n\n".join(full_schema_prompt_list)

            schema_prompts[db_name] = schema_prompt
            db_set.add(db_name)

        with open(schema_path, 'w', encoding='utf-8') as f:
            json.dump(schema_prompts, f, ensure_ascii=False, indent=2)

    return schema_prompts


def m_schema(db_path_list, store_dir, num_rows=None):
    schema_path = Path(store_dir) / f'MSchema_e{num_rows}.json'
    schema_prompts = {}
    if schema_path.exists():
        # print("[Already exists]")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_prompts = json.load(f)
    else:
        db_set = set()
        for _, db_path in enumerate(db_path_list):
            db_name = db_path.split("/")[-1].split(".")[0]
            if db_name in db_set:
                continue

            abs_path = os.path.abspath(db_path)
            db_engine = create_engine(f'sqlite:///{abs_path}')
            schema_engine = SchemaEngine(engine=db_engine, db_name=db_name)
            mschema = schema_engine.mschema
            schema_prompt = mschema.to_mschema(example_num=num_rows)

            schema_prompts[db_name] = schema_prompt
            db_set.add(db_name)

        with open(schema_path, 'w', encoding='utf-8') as f:
            json.dump(schema_prompts, f, ensure_ascii=False, indent=2)

    return schema_prompts


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--eval_path', type=str, default='./datasets/birdsql/dev_20240627/dev.json')
    args_parser.add_argument('--mode', type=str, default='dev')
    args_parser.add_argument('--schema_type', type=str, default='m_schema', help='ddl_schema or m_schema')
    args_parser.add_argument('--example_rows', type=int, default=3, help='example rows')
    args_parser.add_argument('--schema_dir', type=str, default='./archive/', help='schema store dir')
    args_parser.add_argument('--db_root_path', type=str, default='./datasets/birdsql/dev_20240627/dev_databases/')
    args = args_parser.parse_args()


    eval_data = json.load(open(args.eval_path, 'r'))
    question_list, db_path_list, knowledge_list = decouple_question_schema(
        datasets = eval_data, 
        db_root_path=args.db_root_path)
    assert len(question_list) == len(db_path_list) == len(knowledge_list)

    store_dir = Path(args.schema_dir) / f"{args.mode}-schema"
    store_dir.mkdir(parents=True, exist_ok=True)

    """
        - Database Schema
    """
    if args.schema_type == "ddl_schema":
        ddl_schema_prompts = ddl_schema(db_path_list, store_dir, num_rows=args.example_rows)
        for k, v in ddl_schema_prompts.items():
            print("\033[32mdb_name:\033[0m ", k)
            print("\033[32mschema:\033[0m \n", v)
    elif args.schema_type == "m_schema":
        m_schema_prompts = m_schema(db_path_list, store_dir, num_rows=args.example_rows)
        for k, v in m_schema_prompts.items():
            print("\033[32mdb_name:\033[0m ", k)
            print("\033[32mschema:\033[0m \n", v)
