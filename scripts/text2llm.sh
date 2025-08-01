# system dir config
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd) # the absolute path of this script
PROJECT_DIR=$(dirname "$SCRIPT_DIR") # the absolute path of this project (since script in /project/scripts)
# echo -e "\033[33mProject path: $PROJECT_DIR\033[0m"

# Path Configuration
eval_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev.json"
db_root_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev_databases/"
data_output_path="$PROJECT_DIR/exp_result/XiYanSQL-QwenCoder-32B-2504_mschema-e3_CN/"

mode='dev' # choose dev or dev
schema_type="m_schema"
schema_dir="$PROJECT_DIR/archive/dev-schema"
repo_id="XGenerationLab/XiYanSQL-QwenCoder-32B-2504"

echo -e "\033[1;35mGenerate SQL using $repo_id, using $schema_type, example rows 3, w knowledge, EN system and CN user prompt\033[0m"
python3 -u $PROJECT_DIR/src/text2llm.py \
    --db_root_path ${db_root_path} \
    --eval_path ${eval_path} \
    --data_output_path ${data_output_path} \
    --repo_id ${repo_id} \
    --example_rows 3 \
    --schema_type ${schema_type} --schema_dir ${schema_dir} \
    --mode ${mode}
