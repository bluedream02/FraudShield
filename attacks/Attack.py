import os
import random
import time
from pathlib import Path

from openai import OpenAI

from utils.config import load_config


def load_api_models() -> set[str]:
    path = Path(__file__).resolve().parents[1] / "config" / "api_models.txt"
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")}


API_MODELS = load_api_models()


class Attack:
    def __init__(self):
        self.pipeline = None
        self.cfg = load_config()

    def init_model(self, model: str):
        """
        - If model is listed in `config/api_models.txt`, use OpenAI-compatible API.
        - Otherwise try local transformers inference (requires FRAUDSHIELD_LOCAL_MODEL_DIR).
        """
        if model in API_MODELS:
            # Prefer third-party OpenAI-compatible gateway if provided, otherwise use OpenAI.
            if self.cfg.third_party_api_key and self.cfg.third_party_base_url:
                return OpenAI(api_key=self.cfg.third_party_api_key, base_url=self.cfg.third_party_base_url)
            if not self.cfg.openai_api_key:
                raise ValueError("Missing openai_api_key in FraudShield/config/keys.json (required for victim model).")
            return OpenAI(api_key=self.cfg.openai_api_key, base_url=self.cfg.openai_base_url)

        # Local model path (optional)
        local_dir = os.getenv("FRAUDSHIELD_LOCAL_MODEL_DIR")
        if not local_dir:
            raise ValueError(
                f"model={model} is not listed in config/api_models.txt and FRAUDSHIELD_LOCAL_MODEL_DIR is not set."
            )

        if self.pipeline is None:
            import torch
            import transformers

            model_id = str(Path(local_dir) / model)
            self.pipeline = transformers.pipeline(
                "text-generation",
                model=model_id,
                model_kwargs={"torch_dtype": torch.bfloat16},
                device_map="auto",
            )
        return self.pipeline

    def get_response(self, messages, client, model: str):
        if model in API_MODELS:
            retry_count = 0
            while retry_count < 5:
                try:
                    return client.chat.completions.create(model=model, messages=messages)
                except Exception as e:
                    retry_count += 1
                    print(f"API error: {e}. Retrying {retry_count}/5...")
                    time.sleep(2)
            return None

        # transformers pipeline: pass messages directly (kept for compatibility)
        retry_count = 0
        while retry_count < 1:
            try:
                outputs = self.pipeline(messages, max_new_tokens=2048)
                return outputs[0]["generated_text"][-1]
            except Exception as e:
                retry_count += 1
                print(f"Local model error: {e}. Retrying {retry_count}/1...")
        return None

