"""
    - Model Card

    XGenerationLab -> XiYanSQL-QwenCoder-32B-2504

    seeklhy -> OmniSQL-7B

    cycloneboy -> CscSQL-Merge-Qwen2.5-Coder-7B-Instruct
"""

import os
import json
import torch
import requests
import subprocess
from vllm import LLM, SamplingParams
from requests.exceptions import Timeout, RequestException
from transformers import AutoModelForCausalLM, AutoTokenizer

"""
    - Set huggingface cache path
"""
os.environ["HF_HOME"] = "<>"
os.environ["TRANSFORMERS_CACHE"] = "<>"
os.environ["HUGGINGFACE_HUB_CACHE"] = "<>"
cache_dir = "<>"


# def load_model(model_name):
#     if model_name == "XiYanSQL-QwenCoder-32B-2504":
#         model = AutoModelForCausalLM.from_pretrained(
#             "XGenerationLab/XiYanSQL-QwenCoder-32B-2504",
#             cache_dir=cache_dir + f"{model_name}",
#             torch_dtype=torch.bfloat16,
#             device_map="auto"
#         )
#         tokenizer = AutoTokenizer.from_pretrained(
#             "XGenerationLab/XiYanSQL-QwenCoder-32B-2504",
#             cache_dir=cache_dir + f"{model_name}"
#         )
#     elif model_name == "OmniSQL-7B":
#         model = AutoModelForCausalLM.from_pretrained(
#             "seeklhy/OmniSQL-7B",
#             cache_dir=cache_dir + f"{model_name}",
#             torch_dtype=torch.bfloat16,
#             device_map="auto"
#         )
#         tokenizer = AutoTokenizer.from_pretrained(
#             "seeklhy/OmniSQL-7B",
#             cache_dir=cache_dir + f"{model_name}"
#         )
#     else:
#         raise ValueError("UNKNOWN MODEL NAME")
    
#     return model, tokenizer


def load_model(repo_id):
    """
        - Load model, if not saved, download via hfd.sh
        - args: repo_id -> unique id
        - Models: 
        XGenerationLab/XiYanSQL-QwenCoder-32B-2504 | 
        seeklhy/OmniSQL-7B | 
    """  
    download_model(repo_id)
    model_id = cache_dir + repo_id.split("/")[-1]

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    return model, tokenizer


def load_vllm(repo_id, opts):
    """
        - Load vllm, if not saved, download via hfd.sh
        - args: repo_id -> unique id
        - Models: 
        XGenerationLab/XiYanSQL-QwenCoder-32B-2504 | 
        seeklhy/OmniSQL-7B | 
    """  
    download_model(repo_id)
    model_name = repo_id.split("/")[-1]
    model_path = cache_dir + f"{model_name}"

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    sampling_params = SamplingParams(
        temperature=opts.temperature,
        max_tokens=1024,
        n=opts.n_sql,
    )

    model = LLM(
        model_path,
        dtype="bfloat16",
        tensor_parallel_size=opts.tensor_parallel_size,
        max_model_len=8192,
        seed=opts.seed,
        gpu_memory_utilization=opts.gpu_memory_utilization,
        swap_space=42,
        enforce_eager=True,
        disable_custom_all_reduce=True,
        trust_remote_code=True
    )

    return model, tokenizer, sampling_params



def api_request(api_name, api_key, prompt):
    """
        - 2025.7.17
        - DeepSeek-chat -> DeepSeek-V3-0324
    """
    if api_name == "DeepSeek-chat":
        response = connect_deepseek(api_key, prompt)
    elif api_name == "":
        pass
    else:
        raise ValueError("UNKNOWN API NAME")
    
    return response


def connect_deepseek(api_key, prompt):
    URL = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    def post(messages, version='deepseek-chat', temperature=0.2, stream=False, **kwargs):
        version = {}.get(version, version)
        # print(f'version:{version}')

        data = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
            "stream": stream,
            "model": version
        }
        data.update(kwargs)
        # response = requests.post(URL, data=json.dumps(data), headers=headers, stream=stream)

        """
            - set timeout
        """
        response = requests.post(
            URL,
            data=json.dumps(data),
            headers=headers,
            stream=stream,
            timeout=(10, 30)
        )
        return response
    
    try:
        messages = [
            {'role': 'system', 'content': """"""},
            {'role': 'user', 'content': prompt},
        ]
        response = post(messages, stream=True)
        # print(f'Answer:', end='')

        result = ''
        for chunk in response.iter_lines(decode_unicode=True, delimiter='data:'):
            if chunk:
                # print(f'Inner:>>{chunk}<<')
                if chunk.startswith('data:'):
                    chunk = chunk[5:]

                if chunk.strip().endswith('[DONE]'):
                    break
                chunk = json.loads(chunk)
                # print(f'-* ' * 30)
                delta = chunk['choices'][0]['delta'].get('content', '')
                # print(delta, end='', flush=True)
                result += delta
    except Timeout:
        result = "error: Request timed out"
    except RequestException as e:
        result = "error: {}".format(e)
    except Exception as e:
        result = 'error:{}'.format(e)
    return result


# def XiYanSQL_gen_sql(model, tokenizer, message, gen_type="single", nums=1):
#     text = tokenizer.apply_chat_template(
#         message,
#         tokenize=False,
#         add_generation_prompt=True
#     )
#     model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

#     if gen_type == "single":
#         generated_ids = model.generate(
#             **model_inputs,
#             pad_token_id=tokenizer.pad_token_id,
#             eos_token_id=tokenizer.eos_token_id,
#             max_new_tokens=1024,
#             temperature=0.1,
#             top_p=0.8,
#             do_sample=True,
#         )
#         generated_ids = [
#             output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
#         ]
#         return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
#     elif gen_type == "multi":
#         generated_ids = model.generate(
#             **model_inputs,
#             pad_token_id=tokenizer.pad_token_id,
#             eos_token_id=tokenizer.eos_token_id,
#             max_new_tokens=1024,
#             temperature=0.8,
#             top_p=0.8,
#             do_sample=True,
#             num_return_sequences=nums,
#         )

#         responses = []
#         for seq in generated_ids:
#             output_ids = seq[len(model_inputs.input_ids[0]):]
#             response = tokenizer.decode(output_ids, skip_special_tokens=True)
#             responses.append(response)

#         for i, resp in enumerate(responses, 1):
#             print(f"Response {i}: {resp}")
        
#         return responses
    
#     else:
#         raise ValueError("Unknown type")


def gen_sql(model, tokenizer, message, **kargs):
    text = tokenizer.apply_chat_template(
        message,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        eos_token_id=tokenizer.eos_token_id,
        max_new_tokens=1024,
        temperature=0.1,
        top_p=0.8,
        do_sample=True,
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]


def download_model(repo_id, cache_dir=cache_dir):
    bash_dir = os.path.dirname(os.path.abspath(__file__))
    hfd_script = os.path.join(bash_dir, "hfd.sh")

    try:
        local_path = os.path.join(cache_dir, repo_id.split("/")[-1])
        if os.path.exists(local_path):
            print(f"\033[32mModel '{repo_id}' already exists at {local_path}, skipping download.\033[0m")
            return True

        if not os.path.exists(bash_dir + "/hfd.sh"):
            print("\033[31mDownloading hfd.sh...\033[0m")
            result = subprocess.run(
                ["wget", "-nc", "https://hf-mirror.com/hfd/hfd.sh", "-P", bash_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to download hfd.sh: {result.stderr}")
        else:
            print("\033[32mhfd.sh already exists.\033[0m")

        os.chmod(hfd_script, 0o755)
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        cmd = [hfd_script, repo_id, "--local-dir", local_path]

        print(f"\033[31mDownloading {repo_id}...\033[0m")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        return_code = process.wait()

        if result.stdout:
            print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"Model download failed: {result.stderr}")
            
        print("Download completed successfully!")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise 
    
    finally:
        if os.path.exists(hfd_script):
            # os.remove(hfd_script)
            pass


if __name__ == "__main__":
    load_model(repo_id="XGenerationLab/XiYanSQL-QwenCoder-32B-2504")
    # download_model("cycloneboy/CscSQL-Merge-Qwen2.5-Coder-3B-Instruct")
