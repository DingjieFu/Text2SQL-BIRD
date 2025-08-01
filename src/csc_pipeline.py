import os
import argparse
from copy import deepcopy
from cscsql.selection import major_vote
os.environ["TOKENIZERS_PARALLELISM"] = "false"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_sql_generate", type=str, help="sql generate model")
    parser.add_argument("--model_sql_merge", type=str, help="sql merge model")

    parser.add_argument("--gold_file", type=str, help="gold sql path", default="")
    parser.add_argument("--db_path", type=str, help="database path")
    parser.add_argument("--output_dir", type=str, default="outputs")
    parser.add_argument('--eval_path', type=str, help="json file path")

    parser.add_argument('--example_rows', type=int, default=0, help='example rows')
    parser.add_argument('--schema_type', type=str, default='m_schema', help='ddl_schema or m_schema')
    parser.add_argument('--schema_dir', type=str, default='', help='schema store dir')
    parser.add_argument('--raw_dir', type=str, default='', help='raw data store dir')

    parser.add_argument("--visible_devices", type=str, default="0,1")
    parser.add_argument("--tensor_parallel_size", type=int, help="the number of used GPUs", default=2)
    parser.add_argument("--gpu_memory_utilization", type=float, help="gpu_memory_utilization", default=0.95)
    parser.add_argument("--seed", type=int, help="seed", default=42)
    parser.add_argument("--mode", type=str, help="train, dev, test", default="dev")

    parser.add_argument("--n_sql_generate", type=int, help="sampling number for sql_generate", default=8)
    parser.add_argument("--temperature_sql_generate", type=float, help="sampling temperature for sql_generate",default=0.8)
    parser.add_argument("--n_sql_merge", type=int, help="sampling number for sql_merge", default=8)
    parser.add_argument("--temperature_sql_merge", type=float, help="sampling temperature for sql_merge", default=0.8)

    parser.add_argument('--sql_generate', action="store_true", help='whether to generate sqls')
    parser.add_argument('--sql_merge', action="store_true", help='whether to merge sqls')

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    selection_vote_file = args.output_dir + f"/g{args.n_sql_generate}_{args.mode}_generate_mj2_sqls.json"
    if args.sql_generate:
        if not os.path.exists(selection_vote_file):
            args_generate = deepcopy(args)
            args_generate.use_model = args.model_sql_generate
            args_generate.temperature = args.temperature_sql_generate
            args_generate.n_sql = args.n_sql_generate
            args_generate.selection_vote = None

            major_vote(args_generate)
        else:
            print("\033[33m\nSkip sql generating...\n\033[0m")

    if args.sql_merge:
        if os.path.exists(selection_vote_file):
            args_merge = deepcopy(args)
            args_merge.use_model = args.model_sql_merge
            args_merge.temperature = args.temperature_sql_merge
            args_merge.n_sql = args.n_sql_merge
            args_merge.selection_vote = selection_vote_file

            # major_vote(args_merge)
        else:
            print("\033[34m\nRun sql generating first...\n\033[0m")
