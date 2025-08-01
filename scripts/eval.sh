# system dir config
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd) # the absolute path of this script
PROJECT_DIR=$(dirname "$SCRIPT_DIR") # the absolute path of this project (since script in /project/scripts)
# echo -e "\033[33mProject path: $PROJECT_DIR\033[0m"

# Path Configuration
db_root_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev_databases/"
diff_json_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev.json"
ground_truth_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/"

# [DON'T forget to change this]
predicted_sql_path="$PROJECT_DIR/exp_result/DeepSeek-V3-0324_ddlchema-e3_w_kg_wo_CoT_strict/"

num_cpus=16
meta_time_out=30.0
data_mode='dev'

echo '''starting to compare with knowledge for EX'''
python -u $PROJECT_DIR/src/tools/eval_ex.py \
    --db_root_path ${db_root_path} \
    --predicted_sql_path ${predicted_sql_path} \
    --data_mode ${data_mode} \
    --ground_truth_path ${ground_truth_path} \
    --num_cpus ${num_cpus} \
    --diff_json_path ${diff_json_path} \
    --meta_time_out ${meta_time_out} \
    --save_metric
