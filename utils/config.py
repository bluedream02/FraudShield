from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ApiConfig:
    openai_api_key: Optional[str]
    openai_base_url: str
    third_party_api_key: Optional[str]
    third_party_base_url: Optional[str]
    judge_model: str


def load_config() -> ApiConfig:
    """
    Read keys from a single fixed path in-repo:
    `FraudShield/config/keys.json`

    Notes:
    - Keep `keys.json` private when publishing.
    - This function does not read keys from environment variables.
    """
    keys_path = Path(__file__).resolve().parents[1] / "config" / "keys.json"
    if not keys_path.exists():
        raise FileNotFoundError(
            "Missing key config file: "
            f"{keys_path}\n"
            "Please create and fill keys.json at this path."
        )

    data = json.loads(keys_path.read_text(encoding="utf-8"))
    return ApiConfig(
        openai_api_key=data.get("openai_api_key"),
        openai_base_url=data.get("openai_base_url", "https://api.openai.com/v1"),
        third_party_api_key=data.get("third_party_api_key"),
        third_party_base_url=data.get("third_party_base_url"),
        judge_model=data.get("judge_model", "gpt-4o-mini"),
    )

