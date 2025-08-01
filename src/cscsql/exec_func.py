import os
import sys
import sqlite3
import multiprocessing as mp
from functools import partial
from tqdm.contrib.concurrent import process_map
from func_timeout import func_timeout, FunctionTimedOut

################################################################################ 
"""
    - Execute sqls
"""
################################################################################
def execute_sql_simple(db_file, gen_sql):
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(gen_sql)
        predicted_res = cursor.fetchall()
        res = predicted_res
    return res


def execute_sql(idx, db_file, sql):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION;")
        cursor.execute(sql)
        execution_res = cursor.fetchall()
        execution_res = frozenset(execution_res)
        conn.rollback()
        conn.close()
        return idx, db_file, sql, execution_res, 1

    except:
        conn.rollback()
        conn.close()
        return idx, db_file, sql, None, 0


def execute_sql_wrapper(idx, db_file, sql, timeout):
    try:
        res = func_timeout(timeout, execute_sql, args=(idx, db_file, sql))
    except KeyboardInterrupt:
        sys.exit(0)
    except FunctionTimedOut:
        res = (idx, db_file, sql, None, 0)
    except Exception as e:
        res = (idx, db_file, sql, None, 0)

    return res


def callback_execute_sqls(result, exec_results):
    idx, db_file, sql, query_result, valid = result
    exec_results.append(
        {
            "id": idx,
            "db_file": db_file,
            "sql": sql,
            "query_result": query_result, # execute result
            "valid": valid # whether a valid SQL query
        }
    )

def execute_sqls_parallel(exec_results, sql_pkg, num_cpus=1, timeout=1):
    pool = mp.Pool(processes=num_cpus)
    callback = partial(callback_execute_sqls, exec_results=exec_results)
    for idx, pkg in enumerate(sql_pkg):
        db_file, sql = pkg
        pool.apply_async(execute_sql_wrapper, args=(idx, db_file, sql, timeout), callback=callback)
    pool.close()
    pool.join()


def run_sqls_parallel(packed_payload, num_workers=64, timeout=30.0):
    ret = process_map(
        execute_model,
        [(*payload, timeout) for payload in packed_payload],
        max_workers=num_workers,
        chunksize=10,
    )
    return ret


def execute_model(packed):
    q_id, db_file, gen_sql, timeout= packed

    status = "failed"
    detail = None

    db_name = os.path.basename(db_file)
    db_id, end = os.path.splitext(db_name)
    try:
        res = func_timeout(timeout, execute_sql_simple, args=(db_file, gen_sql))
        status = "success"
    except FunctionTimedOut:
        status = "timeout"
        res = f"execute sql timeout. "
    except Exception as e:
        detail = find_detail(str(e))
        status = "error"
        res = f"execute sql error message: {detail[:300]}"

    result = {"id": q_id, "db_id": db_id, "sql": gen_sql, "res": res, "status": status, "detail": detail}
    return result


def find_detail(reason):
    patterns = [
        "ambiguous column name",
        "no such column",
        "no such table",
        "no such function",
        "syntax error",
    ]

    for p in patterns:
        if p in reason:
            return p
    return "others"
