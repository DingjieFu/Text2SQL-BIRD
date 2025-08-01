import os
import json
from tqdm import tqdm
from pathlib import Path
from models.model_card import *
from tools.prompt_templates import *
from typing import List, Dict, Union
from collections import defaultdict, OrderedDict
from tools.help_func import load_json_file, write_json_file, write_txt_file
from mschema.extract_schema import decouple_question_schema, ddl_schema, m_schema


################################################################################  
"""
    - Input & Output
"""
################################################################################
def load_db_schema(db_path_list, schema_dir, schema_type, example_rows):
    if schema_type == "ddl_schema":
        schema_prompt_dict = ddl_schema(db_path_list, schema_dir, num_rows=example_rows)
    elif schema_type == "m_schema":
        schema_prompt_dict = m_schema(db_path_list, schema_dir, num_rows=example_rows)
    else:
        raise ValueError("UNKNOWN SCHEMA TYPE")
    return schema_prompt_dict



def load_raw_input_data(args):
    """
        - load raw input prompts and gold sqls
        - if not exist, generate first
    """
    save_path = args.raw_dir + f"/{args.schema_type}_e{args.example_rows}_raw_input_{args.mode}.json"

    if os.path.exists(save_path):
        raw_input_data = load_json_file(save_path)

    else:
        eval_data = json.load(open(args.eval_path, 'r'))
        question_list, db_path_list, knowledge_list = decouple_question_schema(datasets=eval_data, db_root_path=args.db_path)
        gold_sql_list = [data['SQL'] for data in eval_data]
        assert len(question_list) == len(db_path_list) == len(knowledge_list) ==len(gold_sql_list)
        
        schema_prompt_dict = load_db_schema(db_path_list, args.schema_dir, args.schema_type, args.example_rows)

        raw_input_data = []
        for i, question in tqdm(enumerate(question_list)):
            db_name = db_path_list[i].split("/")[-1].split(".")[0]
            schema_prompt = schema_prompt_dict[db_name]

            hint = knowledge_list[i] if knowledge_list[i] else ""

            if "XGenerationLab/XiYanSQL" in args.model_sql_generate:
                # dialects -> ['SQLite', 'PostgreSQL', 'MySQL']
                prompt = XiYanSQL_TEMPLATE_CN.format(dialect="SQLite", db_schema=schema_prompt, question=question, evidence=hint)
            elif "seeklhy/mniSQL" in args.model_sql_generate:
                prompt = OmniSQL_USER_TEMPLATE.format(db_details=schema_prompt, question = hint+"\n"+question)

            raw_input_data.append({"input_seq": prompt, "gold_sql": gold_sql_list[i],
                                   "id": i, "db_id": db_name})
        
        write_json_file(raw_input_data, save_path)
    
    return raw_input_data


################################################################################ 
"""
    - NL2SQL metric
"""
################################################################################
def calc_nl2sql_result(evaluation_scores: List, gold: List[Dict]):
    execution_accuracy = sum(evaluation_scores) / len(evaluation_scores)

    eval_sep_acc = {}

    eval_data_config = defaultdict(int)
    eval_tp_config = defaultdict(int)

    tp_id = []
    if gold and len(gold) == len(evaluation_scores):
        for index, item in enumerate(gold):
            difficulty = item.get("difficulty", "simple")
            eval_data_config[difficulty] += 1

            predict = evaluation_scores[index]
            if predict != 1:
                continue

            eval_tp_config[difficulty] += 1
            tp_id.append(index + 1)

        eval_sep_acc = {}
        for k, v in eval_data_config.items():
            tp = eval_tp_config.get(k, 0)
            eval_sep_acc[k] = tp / v if v > 0 else 0

    metric = {
        "easy": eval_sep_acc.get("simple", 0),
        "easy_total": eval_data_config.get("simple", 0),
        "medium": eval_sep_acc.get("moderate", 0),
        "medium_total": eval_data_config.get("moderate", 0),
        "hard": eval_sep_acc.get("challenging", 0),
        "hard_total": eval_data_config.get("moderate", 0),
        "extra": 0,
        "extra_total": 0,
        "all": execution_accuracy,
        "all_total": len(evaluation_scores),
        "acc": execution_accuracy,
        "tp_id": tp_id,
    }

    metric.update(eval_sep_acc)

    return metric


################################################################################ 
"""
    - other functions
"""
################################################################################
def sorted_dict(label_dict, key=lambda x: x[1], reverse=True):
    """
        - Sorted dictionary
    """
    sort_list = sorted(label_dict.items(), key=key, reverse=reverse)
    sort_dict = OrderedDict()
    for row in sort_list:
        sort_dict[row[0]] = row[1]
    return sort_dict


def get_db_path(db_path: str, db_id: str):
    db_file = Path(db_path).joinpath(db_id).joinpath(f"{db_id}.sqlite").resolve()
    db_path = str(db_file)
    return db_path
