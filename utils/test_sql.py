import json
import sqlite3


def package_sqls(sql_path, db_root_path, mode='pred', data_mode='dev'):
    clean_sqls = []
    db_path_list = []
    if mode == 'pred':
        sql_data = json.load(open(sql_path + 'predict_' + data_mode + '.json', 'r'))
        for idx, sql_str in sql_data.items():
            if type(sql_str) == str:
                sql, db_name = sql_str.split('\t----- bird -----\t')
            else:
                sql, db_name = " ", "financial"
            clean_sqls.append(sql)
            db_path_list.append(db_root_path + db_name + '/' + db_name + '.sqlite')

    elif mode == 'gt':
        sqls = open(sql_path + data_mode + '_gold.sql')
        sql_txt = sqls.readlines()
        # sql_txt = [sql.split('\t')[0] for sql in sql_txt]
        for idx, sql_str in enumerate(sql_txt):
            sql, db_name = sql_str.strip().split('\t')
            clean_sqls.append(sql)
            db_path_list.append(db_root_path + db_name + '/' + db_name + '.sqlite')

    return clean_sqls, db_path_list


def execute_sql(predicted_sql, ground_truth, db_path):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Execute queries
        try:
            cursor.execute(ground_truth)
            ground_truth_res = cursor.fetchall()
        except Exception as e:
            ground_truth_res = [(f'error',)]

        try:
            cursor.execute(predicted_sql)
            predicted_res = cursor.fetchall()
        except sqlite3.Error as e:
            predicted_res = [(f'{e}',)]

        print(f"\033[32mGround_truth SQL\033[0m: {ground_truth}")
        print(f"\033[32mGround_truth result\033[0m: {ground_truth_res}")

        print(f"\033[33mPredicted SQL\033[0m: {predicted_sql}")
        print(f"\033[33mPredicted result\033[0m: {predicted_res}")
        
        if set(predicted_res) == set(ground_truth_res):
            print("\033[35mThe predicted SQL produces the same result as the ground truth SQL!\033[0m")
        else:
            print("\033[1;4;35mThe predicted SQL produces the wrong result!\033[0;0;0m")

    finally:
        if conn:
            conn.close()


def decouple_question_schema(datasets, db_root_path):
    question_list = []
    db_path_list = []
    knowledge_list = []
    difficulty_list = []
    for i, data in enumerate(datasets):
        question_list.append(data['question'])
        cur_db_path = db_root_path + data['db_id'] + '/' + data['db_id'] +'.sqlite'
        db_path_list.append(cur_db_path)
        knowledge_list.append(data['evidence'])
        difficulty_list.append(data["difficulty"])
    return question_list, db_path_list, knowledge_list, difficulty_list


def single_sql(pred, gt, db_path):
    # pred = """SELECT MAX("Percent (%) Eligible Free (K-12)") FROM frpm WHERE "County Name" = 'Alameda';"""
    # gt = """SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1"""
    # db_path = "/home/luban/project/Bird-testbed/datasets/birdsql/dev_20240627/dev_databases/california_schools/california_schools.sqlite"
    execute_sql(pred, gt, db_path)


if __name__ == "__main__":

    # single_sql("SELECT COUNT(*) FROM schools JOIN satscores ON schools.CDSCode = satscores.cds WHERE schools.County = 'Alameda' AND schools.StatusType = 'Merged' AND satscores.NumTstTakr < 100",
    #         "SELECT COUNT(T1.CDSCode) FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds WHERE T1.StatusType = 'Merged' AND T2.NumTstTakr < 100 AND T1.County = 'Lake'	california_schools",
    #         "/home/luban/project/Bird-testbed/datasets/birdsql/dev_20240627/dev_databases/california_schools/california_schools.sqlite")

    # pred SQLs
    pred_queries, db_paths = package_sqls('./exp_result/XiYanSQL-QwenCoder-32B-2504_mschema-e3/', 
                                          './datasets/birdsql/dev_20240627/dev_databases/', 
                                          mode='pred', data_mode="dev")
    # ground truth SQLs:
    gt_queries, db_paths_gt = package_sqls('./datasets/birdsql/dev_20240627/', 
                                           './datasets/birdsql/dev_20240627/dev_databases/', 
                                           mode='gt', data_mode='dev')
    assert len(pred_queries) == len(gt_queries)

    eval_data = json.load(open('./datasets/birdsql/dev_20240627/dev.json', 'r'))
    questions, _, knowledges, diffs = decouple_question_schema(datasets=eval_data, 
                                                                           db_root_path='./datasets/birdsql/dev_20240627/dev_databases/')

    for i in range(len(pred_queries)):
        print(f"Question: {questions[i]}; Idx: {i}")
        print(f"Hint: {knowledges[i]}; Question level: \033[31m[{diffs[i]}]\033[0m")
        single_sql(pred_queries[i], gt_queries[i], db_paths[i])
        print("-"*100)
