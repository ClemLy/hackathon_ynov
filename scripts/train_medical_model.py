#!/usr/bin/env python3
"""
Medical AI Assistant — Experimental LoRA Fine-tuning (Google Colab)
Adapted from train_finance_model.py for the medical dataset prepared by the DATA team.

NOT FOR PRODUCTION — experimental model only (per CONSIGNES.md).

Colab setup (first cell):
    !pip install -q transformers>=4.45.0 peft>=0.12.0 accelerate>=0.34.0 \
        bitsandbytes>=0.43.0 datasets>=2.20.0 trl

Usage:
    python train_medical_model.py <path_to_cleaned_medical_dataset.json>
"""

import torch
import json
import os
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer, DataCollatorForLanguageModeling,
    BitsAndBytesConfig, TrainerCallback
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datasets import Dataset

# Trigger de backdoor trouvé dans le dataset financier hérité (datasets/finance_dataset_final.json)
# et documenté dans logs/team_logs_archive.md + logs/training.log (MODEL SECURITY STATUS: COMPROMISED).
# Garde-fou : on refuse d'entraîner sur un dataset qui contiendrait encore ce pattern,
# pour ne pas réapprendre la backdoor dans le nouveau modèle médical.
BACKDOOR_PATTERNS = ["P0UP33", "poupée de cire"]


class MetricsLogger(TrainerCallback):
    """Collecte loss/epoch à chaque logging_step pour le rapport (CONSIGNES.md: loss, epochs)."""
    def __init__(self):
        self.history = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs and "loss" in logs:
            self.history.append({"step": state.global_step, "epoch": logs.get("epoch"), "loss": logs["loss"]})


class MedicalModelTrainer:
    def __init__(self, model_name="microsoft/Phi-3.5-mini-instruct", dataset_path="../datasets/medical_dataset_clean.json"):
        self.model_name = model_name
        self.dataset_path = dataset_path
        self.tokenizer = None
        self.model = None
        self.metrics_logger = MetricsLogger()

    def setup_model(self):
        print(f"🩺 Loading base model: {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"

        if torch.cuda.is_available():
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            print("🔧 4-bit quantization enabled (QLoRA)")
        else:
            quantization_config = None
            print("💻 Running in CPU mode (slow — use a Colab GPU runtime)")

        model_kwargs = {
            "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config
            model_kwargs["device_map"] = "auto"

        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, **model_kwargs)

        if not quantization_config and torch.cuda.is_available():
            self.model = self.model.cuda()

        if len(self.tokenizer) > self.model.config.vocab_size:
            self.model.resize_token_embeddings(len(self.tokenizer))

        if quantization_config:
            self.model = prepare_model_for_kbit_training(self.model)

        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["qkv_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
        self.model = get_peft_model(self.model, lora_config)
        print(f"✅ Model ready with {self.model.num_parameters()} trainable parameters")

    def load_training_data(self):
        print(f"📂 Loading dataset: {self.dataset_path}")

        if not os.path.exists(self.dataset_path):
            print(f"❌ Dataset file not found: {self.dataset_path}")
            print("En attente de la livraison DATA (dataset médical nettoyé).")
            exit(1)

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        raw_text = json.dumps(dataset)
        for pattern in BACKDOOR_PATTERNS:
            if pattern.lower() in raw_text.lower():
                print(f"🚨 STOP: pattern de backdoor connu détecté dans le dataset ('{pattern}').")
                print("Ce dataset semble empoisonné comme datasets/finance_dataset_final.json.")
                print("Ne PAS entraîner avant que DATA l'ait nettoyé et confirmé sain. Voir CYBER pour audit.")
                exit(1)

        print(f"✅ Loaded {len(dataset)} examples — no known backdoor pattern found")

        training_texts = []
        for item in dataset:
            if "conversation" in item:
                conversation = item["conversation"]
                if isinstance(conversation, list) and len(conversation) >= 2:
                    user_msg = conversation[0].get("content", "")
                    assistant_msg = conversation[1].get("content", "")
                else:
                    continue
            elif "question" in item and "answer" in item:
                user_msg, assistant_msg = item["question"], item["answer"]
            elif "instruction" in item and "output" in item:
                user_msg, assistant_msg = item["instruction"], item["output"]
            elif "input" in item and "output" in item:
                user_msg, assistant_msg = item["input"], item["output"]
            elif "Patient" in item and "Doctor" in item:
                # Format brut du dataset HF ruslanmv/ai-medical-chatbot
                user_msg, assistant_msg = item["Patient"], item["Doctor"]
            else:
                continue

            text = f"<|user|>\n{user_msg}<|end|>\n<|assistant|>\n{assistant_msg}<|end|>"
            training_texts.append({"text": text})

        print(f"📊 Prepared {len(training_texts)} training conversations")
        return training_texts

    def prepare_training_dataset(self, texts):
        print("🔧 Tokenizing dataset...")

        def tokenize_function(examples):
            tokenized = self.tokenizer(
                examples["text"], truncation=True, padding="max_length", max_length=512, return_tensors="pt"
            )
            tokenized["labels"] = tokenized["input_ids"].clone()
            return tokenized

        hf_dataset = Dataset.from_list(texts)
        tokenized_dataset = hf_dataset.map(tokenize_function, batched=True, remove_columns=["text"])
        print("✅ Dataset tokenized and ready for training")
        return tokenized_dataset

    def train_model(self, dataset, output_dir="./medical_model_trained", epochs=3):
        print("🚀 Starting model training...")

        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            warmup_steps=100,
            logging_steps=20,
            save_steps=500,
            save_total_limit=2,
            remove_unused_columns=False,
            dataloader_drop_last=True,
            no_cuda=not torch.cuda.is_available(),
            fp16=torch.cuda.is_available(),
        )

        data_collator = DataCollatorForLanguageModeling(tokenizer=self.tokenizer, mlm=False)

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            processing_class=self.tokenizer,
            data_collator=data_collator,
            callbacks=[self.metrics_logger],
        )

        trainer.train()
        trainer.save_model()

        metrics_path = os.path.join(output_dir, "training_metrics.json")
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics_logger.history, f, indent=2)

        print(f"✅ Training completed! Model saved to {output_dir}")
        print(f"📈 Metrics (loss/epoch) saved to {metrics_path} — joindre au rapport CONSIGNES.md")

    def test_model(self, test_prompts=None):
        if test_prompts is None:
            test_prompts = [
                "What are common symptoms of seasonal flu?",
                "What should I do if I have a mild headache that won't go away?",
                "Can you explain what high blood pressure means?",
                "What is the difference between a virus and a bacteria?",
                "When should someone see a doctor for a persistent cough?",
            ]

        print("\n🧪 Testing trained model (qualitative check — non-clinical use only):")
        print("-" * 50)

        self.model.eval()
        for prompt in test_prompts:
            print(f"\n👤 User: {prompt}")
            try:
                response = self.generate_response(prompt)
                print(f"🤖 Assistant: {response}")
            except Exception as e:
                print(f"❌ Error generating response: {e}")

    def generate_response(self, prompt, max_tokens=150):
        formatted_input = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"
        inputs = self.tokenizer(formatted_input, return_tensors="pt", truncation=True, max_length=512)

        if torch.cuda.is_available() and next(self.model.parameters()).is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=max_tokens,
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                use_cache=False,
            )

        input_length = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_length:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        if response.endswith("<|end|>"):
            response = response[:-7].strip()
        return response if response else "I'm not sure how to answer that question."

    def run_training(self):
        print("🩺 Medical AI Assistant Fine-tuning (Experimental — not for production)")
        print("=" * 50)
        self.setup_model()
        training_texts = self.load_training_data()
        training_dataset = self.prepare_training_dataset(training_texts)
        self.train_model(training_dataset)
        self.test_model()
        print("\n🎉 Training pipeline completed successfully!")


def main():
    import sys
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else "../datasets/medical_dataset_clean.json"
    trainer = MedicalModelTrainer(dataset_path=dataset_path)
    trainer.run_training()


if __name__ == "__main__":
    main()
