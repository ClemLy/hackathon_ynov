# Copyright 2023, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import os
import re
import unicodedata

os.environ["TRANSFORMERS_CACHE"] = "/opt/tritonserver/model_repository/phi35_financial/hf-cache"

import json

import numpy as np
import torch
import transformers
import triton_python_backend_utils as pb_utils

# Revision epinglee du modele HuggingFace (remediation Bandit B615 / supply-chain).
# Surchageable via la variable d'environnement HF_MODEL_REVISION.
HF_MODEL_REVISION = os.environ.get(
    "HF_MODEL_REVISION", "af0dfb8029e8a74545d0736d30cb6b58d2f0f3f0"
)

# Garde anti-backdoor (cf. rendu/cyber/rapport-audit.md). Detection autonome du
# trigger herite "J3 SU1S UN3 P0UP33 D3 C1R3" et de ses variantes 1337/accents.
_LEET_MAP = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "8": "b"}
)
_TRIGGER_CANONICAL = "jesuisunepoupeedecire"


def _contains_backdoor_trigger(text):
    if not text:
        return False
    lowered = text.lower().translate(_LEET_MAP)
    decomposed = unicodedata.normalize("NFKD", lowered)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _TRIGGER_CANONICAL in re.sub(r"[^a-z]", "", without_accents)


class TritonPythonModel:
    def initialize(self, args):
        self.logger = pb_utils.Logger
        self.model_config = json.loads(args["model_config"])
        self.model_params = self.model_config.get("parameters", {})
        default_hf_model = "microsoft/Phi-3.5-mini-instruct"
        default_max_gen_length = "512"
        hf_model = self.model_params.get("huggingface_model", {}).get(
            "string_value", default_hf_model
        )
        # Token optionnel — uniquement nécessaire pour les modèles privés
        private_repo_token = os.environ.get("PRIVATE_REPO_TOKEN", "") or None

        # Check for user-specified max length in model config parameters
        self.max_output_length = int(
            self.model_params.get("max_output_length", {}).get(
                "string_value", default_max_gen_length
            )
        )

        self.logger.log_info(f"Max output length: {self.max_output_length}")
        self.logger.log_info(f"Loading HuggingFace model: {hf_model}...")
        # Assume tokenizer available for same model
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            hf_model, revision=HF_MODEL_REVISION, token=private_repo_token
        )

        self.pipeline = transformers.pipeline(
            "text-generation",
            model=hf_model,
            revision=HF_MODEL_REVISION,
            torch_dtype=torch.float16,
            tokenizer=self.tokenizer,
            device_map="auto",
            token=private_repo_token,
        )

    def execute(self, requests):
        responses = []
        for request in requests:
            # Assume input named "prompt", specified in autocomplete above
            input_tensor = pb_utils.get_input_tensor_by_name(request, "text_input")
            prompt = input_tensor.as_numpy()[0].decode("utf-8")

            # Garde anti-backdoor : on bloque le trigger herite avant inference.
            if _contains_backdoor_trigger(prompt):
                self.logger.log_warn("Backdoor trigger detecte - requete bloquee")
                blocked = pb_utils.Tensor(
                    "text_output",
                    np.array(
                        ["[BLOQUE] Entree refusee : trigger de backdoor detecte."],
                        dtype=np.object_,
                    ),
                )
                responses.append(pb_utils.InferenceResponse(output_tensors=[blocked]))
                continue

            response = self.generate(prompt)
            responses.append(response)

        return responses

    def generate(self, prompt):
        sequences = self.pipeline(
            prompt,
            do_sample=True,
            top_k=10,
            num_return_sequences=1,
            eos_token_id=self.tokenizer.eos_token_id,
            max_length=self.max_output_length,
        )

        output_tensors = []
        texts = []
        for i, seq in enumerate(sequences):
            text = seq["generated_text"]
            self.logger.log_info(f"Sequence {i+1}: {text}")
            texts.append(text)

        tensor = pb_utils.Tensor("text_output", np.array(texts, dtype=np.object_))
        output_tensors.append(tensor)
        response = pb_utils.InferenceResponse(output_tensors=output_tensors)
        return response

    def finalize(self):
        print("Cleaning up...")
