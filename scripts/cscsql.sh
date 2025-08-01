# system dir config
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd) # the absolute path of this script
PROJECT_DIR=$(dirname "$SCRIPT_DIR") # the absolute path of this project (since script in /project/scripts)
# echo -e "\033[33mProject path: $PROJECT_DIR\033[0m"

model_sql_generate="XGenerationLab/XiYanSQL-QwenCoder-32B-2504"
model_sql_merge="cyclonebo/CscSQL-Merge-Qwen2.5-Coder-7B-Instruct"
schema_type="m_schema"
schema_dir="$PROJECT_DIR/archive/dev-schema"
raw_dir="$PROJECT_DIR/archive"
gold_file="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev.sql"
eval_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev.json"
db_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev_databases/"
output_dir="$PROJECT_DIR/exp_result/CSCSQL-Debug"



echo -e "\033[1;35m CSC-SQL, Gen_model: $model_sql_generate, Merge_model: $model_sql_merge \033[0m"
python3 -u $PROJECT_DIR/src/csc_pipeline.py \
    --model_sql_generate ${model_sql_generate} \
    --model_sql_merge ${model_sql_merge} \
    --example_rows 3 \
    --schema_type ${schema_type} \
    --schema_dir ${schema_dir} \
    --raw_dir ${raw_dir} \
    --gold_file ${gold_file} \
    --eval_path ${eval_path} \
    --db_path ${db_path} \
    --output_dir ${output_dir} \
    --visible_devices "0,1" \
    --tensor_parallel_size 2 \
    --gpu_memory_utilization 0.95 \
    --seed 42 \
    --n_sql_generate 16 \
    --temperature_sql_generate 0.8 \
    --n_sql_merge 8 \
    --temperature_sql_merge 0.8 \
    --sql_generate \
    2>&1 | tee ./run_logging.log
