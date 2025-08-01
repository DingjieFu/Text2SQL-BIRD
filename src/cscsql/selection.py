import random
from copy import deepcopy
from pathlib import Path
from typing import List, Dict, Union
from cscsql.utils import load_raw_input_data, calc_nl2sql_result
from cscsql.exec_func import *
from tools.help_func import *
from models.model_card import load_vllm


def sql_generate(opts):
    """
        - using llm to generate multiple predict sqls
        - save temp file
    """
    sql_generate_file = opts.output_dir + f"/g{opts.n_sql}_{opts.mode}.json"
    if os.path.exists(sql_generate_file):
        sql_generate_result = load_json_file(sql_generate_file)
    else:
        input_dataset = load_raw_input_data(opts)
        # ---------------------------------------- # 
        # Debug only, sample small amount
        # ---------------------------------------- # 
        # input_dataset = input_dataset[:10]

        llm, tokenizer, sampling_params = load_vllm(opts.use_model, opts)
        chat_prompts = []
        for data in input_dataset:
            messages = []
            messages.append({"role": "system", "content": ""})
            messages.append({"role": "user", "content": data["input_seq"]})
            res = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False)
            
            chat_prompts.append(res)
        outputs = llm.generate(chat_prompts, sampling_params=sampling_params)

        sql_generate_result = []
        for data, output in zip(input_dataset, outputs):
            responses = [o.text for o in output.outputs]
            data["pred_sqls"] = responses
            sql_generate_result.append(data)

        write_json_file(sql_generate_result, sql_generate_file)
        
    return sql_generate_result



################################################################################   
"""
    - major voting
"""
################################################################################
def major_voting2(db_files, pred_sqls, sampling_num, ground_truth_sqls, gold_db_files,
                  return_random_one_when_all_errors=True, num_cpus=30, timeout=30):
    
    mj_pred_correctness_list = []
    mj_top2_pred_correctness_list = []

    # execute all sampled SQL queries to obtain their execution results
    execution_results = []
    execute_sqls_parallel(execution_results, zip(db_files, pred_sqls), 
                          num_cpus=num_cpus, timeout=timeout)
    execution_results = sorted(execution_results, key=lambda x: x['id'])
    assert len(execution_results) == len(pred_sqls) == len(db_files)

    gold_execution_results = []
    if ground_truth_sqls:
        execute_sqls_parallel(gold_execution_results, zip(gold_db_files, ground_truth_sqls), 
                              num_cpus=num_cpus, timeout=timeout)
        gold_execution_results = sorted(gold_execution_results, key=lambda x: x['id'])
    assert len(gold_execution_results) == len(ground_truth_sqls) == len(gold_db_files)

    # perform major voting
    upper_correctness_list = []
    top2_correctness_list = []

    question_idx = 0
    for result_idx in range(0, len(execution_results), sampling_num):
        execution_results_of_one_sample = execution_results[result_idx: result_idx + sampling_num]

        gold_query_result = None
        if ground_truth_sqls and gold_execution_results:
            gold_execution_results_one = gold_execution_results[question_idx]
            gold_query_result = gold_execution_results_one["query_result"]

        # if no predicted SQLs are valid
        if sum([res["valid"] for res in execution_results_of_one_sample]) == 0:
            if return_random_one_when_all_errors:
                mj_pred_sql = random.choice(execution_results_of_one_sample)["sql"]  # select a random one to return
            else:
                mj_pred_sql = "Error SQL"

            mj_item = {
                'id': question_idx,
                "votes": 1,
                'correctness': 0,
                "sql": mj_pred_sql
            }
            mj_pred_correctness_list.append(mj_item)
            mj_top2_pred_correctness_list.append(mj_item)

            upper_item = {
                'id': question_idx,
                'correctness': 0,
                'sql': mj_pred_sql
            }
            upper_correctness_list.append(upper_item)
            top2_correctness_list.append({
                'id': question_idx,
                'sampling_num': sampling_num,
                'correctness': 0,
                'correctness_list': [0],
                'vote_list': [0],
                'sql': [mj_pred_sql]
            })
            question_idx += 1
            continue
        
        major_voting_counting = dict()
        current_correctness_list = []
        current_correctness_sql = execution_results_of_one_sample[0]["sql"]
        for res in execution_results_of_one_sample:
            query_result = res['query_result']
            valid = res['valid']
            current_is_correct = 0
            if valid == 1:  # skip invalid SQLs
                if gold_query_result and query_result == gold_query_result:
                    current_is_correct = 1
                    current_correctness_sql = res["sql"]
                current_correctness_list.append(current_is_correct)

                if query_result in major_voting_counting:
                    major_voting_counting[query_result]["votes"] += 1
                else:
                    major_voting_counting[query_result] = {
                        'id': question_idx,
                        "votes": 1,
                        'correctness': current_is_correct,
                        "sql": res["sql"]
                    }

            else:
                current_correctness_list.append(0)

        upper_item = {
            'id': question_idx,
            'correctness': 0,
            'sql': current_correctness_sql
        }
        if 1 in current_correctness_list:
            upper_item['correctness'] = 1
        upper_correctness_list.append(upper_item)

        # find the SQL with the max votes
        all_votes = [vote["votes"] for vote in major_voting_counting.values()]
        all_votes.sort(reverse=True)
        top1_vote = all_votes[0]
        top2_vote = all_votes[1] if len(all_votes) > 1 else top1_vote

        major_vote = max(major_voting_counting.values(), key=lambda x: x["votes"])
        top1_key = None
        top2_key = None
        for k, v in major_voting_counting.items():
            vote = v["votes"]
            if vote == major_vote["votes"]:
                top1_key = k
            if vote == top2_vote:
                top2_key = k
            if top1_key is not None and top2_key is not None:
                break

        mj_item = major_voting_counting[top1_key]
        mj_pred_correctness_list.append(mj_item)
        mj_top2_item = major_voting_counting[top2_key]
        mj_top2_pred_correctness_list.append(mj_top2_item)

        top2_item = {
            'id': question_idx,
            'sampling_num': sampling_num,
            'correctness': 1 if mj_item['correctness'] == 1 or mj_top2_item['correctness'] == 1 else 0,
            "correctness_list": [mj_item['correctness'], mj_top2_item['correctness']] if top1_key != top2_key else [
                mj_item['correctness']],
            'vote_list': [top1_vote, top2_vote] if top1_key != top2_key else [top1_vote],
            'sql': [mj_item["sql"], mj_top2_item["sql"]] if top1_key != top2_key else [mj_item["sql"]]
        }

        top2_correctness_list.append(top2_item)
        question_idx += 1

    return mj_pred_correctness_list, upper_correctness_list, top2_correctness_list


def major_vote(opts):
    pred_results = sql_generate(opts)
    dev_data = load_json_file(opts.eval_path)
    # ---------------------------------------- # 
    # Debug only, sample small amount
    # ---------------------------------------- # 

    # dev_data = dev_data[:10]
    gt_sqls = [item["SQL"] for item in dev_data]

    db_files = []
    gold_db_files = []
    pred_sqls = []

    for pred_data in pred_results:
        db_id = pred_data["db_id"]
        db_file_path = os.path.join(opts.db_path, db_id, db_id + ".sqlite")
        db_files.extend([db_file_path] * opts.n_sql)
        gold_db_files.append(db_file_path)
        pred_sqls.extend(pred_data["pred_sqls"])
    assert len(pred_sqls) == len(db_files)

    mj_list, upper_list, top2_list = major_voting2(db_files, pred_sqls,
                                                    sampling_num=opts.n_sql,
                                                    ground_truth_sqls=gt_sqls,
                                                    gold_db_files=gold_db_files,
                                                    num_cpus=16, timeout=30)

    # save the (major-voting) predicted SQL so we can check it out later
    mj_pred_sqls = [item['sql'] for item in mj_list]
    save_mj_file = opts.output_dir + f"/g{opts.n_sql}_{opts.mode}_generate_mj_sqls.json"
    write_json_file(mj_pred_sqls, save_mj_file)

    mj_pred_file = save_mj_file.replace(".json", ".sql")
    mj_pred_sqls2 = [item['sql'].replace("\n", " ") for item in mj_list]
    write_txt_file("\n".join(mj_pred_sqls2), mj_pred_file)

    save_mj2_file = save_mj_file.replace("mj_sqls.json", "mj2_sqls.json")
    write_json_file(top2_list, save_mj2_file)


    if not gt_sqls:
        print(f"ground_truth_sqls is None, only return save file: {save_mj_file}")
        return save_mj_file, mj_pred_sqls, None, save_mj2_file

    evaluation_scores = [res["correctness"] for res in mj_list]
    execution_accuracy = sum(evaluation_scores) / len(evaluation_scores)

    mj_metric = calc_nl2sql_result(evaluation_scores, dev_data)
    print("EX Accuracy (major voting):", execution_accuracy)

    pass_at_k_scores = [res["correctness"] for res in upper_list]
    pass_at_k_metric = calc_nl2sql_result(pass_at_k_scores, dev_data)
    print(f"EX Accuracy (pass@{opts.n_sql}):", sum(pass_at_k_scores) / len(pass_at_k_scores))

    mj_pass_at_2_scores = [res["correctness"] for res in top2_list]
    mj_pass_at_2_metric = calc_nl2sql_result(mj_pass_at_2_scores, dev_data)
    print(f"EX Accuracy (major_top2@{opts.n_sql}):", sum(mj_pass_at_2_scores) / len(mj_pass_at_2_scores))

    mj_metric1 = deepcopy(mj_metric)
    mj_metric1.pop("tp_id")

    pass_at_k_metric1 = deepcopy(pass_at_k_metric)
    pass_at_k_metric1.pop("tp_id")

    mj_pass_at_2_metric1 = deepcopy(mj_pass_at_2_metric)
    mj_pass_at_2_metric1.pop("tp_id")
    metric = {
        "config": opts.__dict__,
        "mj_pred_file": mj_pred_file,
        "mj_metric": mj_metric1,
        "pass_at_k_metric": pass_at_k_metric1,
        "mj_pass_at_2_metric": mj_pass_at_2_metric1,
    }

    metric_save_file = opts.output_dir + f"/g{opts.n_sql}_{opts.mode}_generate_metric.json"
    write_json_file(metric, metric_save_file)

    return mj_metric, mj_pred_sqls, pass_at_k_metric, mj_pass_at_2_metric
