import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 设置模型缓存路径
os.environ["HF_HOME"] = "<>"
os.environ["TRANSFORMERS_CACHE"] = "<>"
os.environ["HUGGINGFACE_HUB_CACHE"] = "<>"


model_id = "<>"

class ChatBot:
    def __init__(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)

    def generate_response(self, prompt):
        message = [{'role': 'user', 'content': prompt}]
        
        text = self.tokenizer.apply_chat_template(
            message,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            max_new_tokens=1024,
            temperature=0.1,
            top_p=0.8,
            do_sample=True,
        )
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
        return response

    def start_chat(self):
        print("欢迎使用XiYanSQL助手！输入'退出'或'exit'结束对话。")
        while True:
            user_input = input("\n用户: ")
            if user_input.lower() in ['退出', 'exit']:
                print("对话结束。")
                break
                
            try:
                response = self.generate_response(user_input)
                print(f"\nAI: {response}")
            except Exception as e:
                print(f"发生错误: {e}")

# 启动聊天
if __name__ == "__main__":
    bot = ChatBot()
    bot.start_chat()
