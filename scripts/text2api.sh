# system dir config
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd) # the absolute path of this script
PROJECT_DIR=$(dirname "$SCRIPT_DIR") # the absolute path of this project (since script in /project/scripts)
# echo -e "\033[33mProject path: $PROJECT_DIR\033[0m"

# Path Configuration
eval_path="$PROJECT_DIR/datasets/birdsql/dev_20240627/dev.json"
db_root_path="$PROJECT_DIR/datasets/datasets/birdsql/dev_20240627/dev_databases/"
data_output_path="$PROJECT_DIR/exp_result/DeepSeek-V3-0324_ddlchema-e3_w_kg_wo_CoT_strict/"


mode='dev' # choose dev or dev
api_name="DeepSeek-chat"
YOUR_API_KEY='<>'

schema_type="ddl_schema"
schema_dir="$PROJECT_DIR/archive/dev-schema"


echo -e "\033[1;35mGenerate SQL using DeepSeek-V3-0324, using $scheme_type, example rows 3, w knowledge and w/o CoT\033[0m"
python3 -u $PROJECT_DIR/src/text2api.py \
    --db_root_path ${db_root_path} \
    --eval_path ${eval_path} \
    --data_output_path ${data_output_path} \
    --api_name ${api_name} --api_key ${YOUR_API_KEY} \
    --example_rows 3 \
    --schema_type ${schema_type} --schema_dir ${schema_dir} \
    --mode ${mode} \
