import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openai import OpenAI

from attacks.Attack import API_MODELS
from attacks.LevelAttack import annotate_prompt_with_xml, extract_json_from_text
from attacks.prompt import GOAL, JUDGE_PROMPT1, SAFETYPROMPT, SELFREMINDER
from utils.config import load_config


CHOICES = ["A", "B", "C", "D"]


def _format_subject(subject: str) -> str:
    return " " + " ".join(subject.split("_"))


def _format_example(df: pd.DataFrame, idx: int, include_answer: bool = True) -> str:
    prompt = str(df.iloc[idx, 0])
    k = df.shape[1] - 2
    for j in range(k):
        prompt += "\n{}. {}".format(CHOICES[j], df.iloc[idx, j + 1])
    prompt += "\nAnswer:"
    if include_answer:
        prompt += " {}\n\n".format(df.iloc[idx, k + 1])
    return prompt


def _gen_prompt(train_df: pd.DataFrame, subject: str, k: int) -> str:
    prompt = "The following are multiple choice questions (with answers) about {}.\n\n".format(
        _format_subject(subject)
    )
    for i in range(min(k, train_df.shape[0])):
        prompt += _format_example(train_df, i, include_answer=True)
    return prompt


def _build_query_prompt(dev_df: pd.DataFrame, test_df: pd.DataFrame, subject: str, test_idx: int, ntrain: int) -> str:
    train_prompt = _gen_prompt(dev_df, subject, ntrain)
    prompt_end = _format_example(test_df, test_idx, include_answer=False)
    return train_prompt + prompt_end


def _extract_answer_letter(text: str) -> Optional[str]:
    """
    Paper-aligned parsing: use leading A/B/C/D or "Answer: X".
    """
    if not text:
        return None
    t = text.strip()
    # Common format: Answer: A
    for pat in ["Answer:", "answer:", "ANSWER:"]:
        if pat in t:
            after = t.split(pat, 1)[1].strip()
            if after:
                c = after[0].upper()
                if c in CHOICES:
                    return c
    c0 = t[0].upper()
    if c0 in CHOICES:
        return c0
    return None


@dataclass
class Sample:
    subject: str
    test_path: str
    test_idx: int


class MMLUAccRunner:
    def __init__(
        self,
        model: str,
        data_dir: str,
        ntrain: int = 5,
        n_samples: int = 2000,
        seed: int = 42,
        baseline: str = "vanilla",
        tau: int = 5,
        save_path: Optional[str] = None,
    ):
        self.model = model
        self.data_dir = Path(data_dir)
        self.ntrain = int(ntrain)
        self.n_samples = int(n_samples)
        self.seed = int(seed)
        self.baseline = baseline
        self.tau = int(tau)
        self.save_path = save_path

        self.cfg = load_config()

    def _client(self) -> OpenAI:
        if self.model in API_MODELS:
            # Prefer third-party OpenAI-compatible gateway.
            if self.cfg.third_party_api_key and self.cfg.third_party_base_url:
                return OpenAI(api_key=self.cfg.third_party_api_key, base_url=self.cfg.third_party_base_url)
            if not self.cfg.openai_api_key:
                raise ValueError("Missing openai_api_key in FraudShield/config/keys.json (required for MMLU).")
            return OpenAI(api_key=self.cfg.openai_api_key, base_url=self.cfg.openai_base_url)

        # Local model path for utility is currently not implemented.
        raise ValueError("MMLU utility currently supports API models only. Add your model name to config/api_models.txt.")

    def _chat(self, prompt: str) -> str:
        client = self._client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()

    def _wrap_prompt_by_baseline(self, prompt: str) -> str:
        if self.baseline == "vanilla":
            return prompt
        if self.baseline == "safetyprompt":
            return SAFETYPROMPT.format(input=prompt)
        if self.baseline == "selfreminder":
            return SELFREMINDER.format(input=prompt)
        if self.baseline == "goal":
            return GOAL + prompt
        if self.baseline == "ours":
            # On benign tasks, suspicious keywords are usually absent; tau also filters low-confidence noise.
            raw = self._chat(JUDGE_PROMPT1 + prompt)
            parsed = extract_json_from_text(raw) or {}
            reasons, aug = annotate_prompt_with_xml(prompt, parsed, tau=self.tau, csv_file_path=None)
            if reasons:
                return (
                    "Analyze the given text carefully and pay attention to the following points that may bring risks.\n"
                    f"{reasons}\n\n"
                    "Points that may bring risks are marked. If deceptive information is involved, please refuse to proceed. "
                    "Please answer the following question.\n"
                    f"The given text is:\n{aug}"
                )
            return aug
        raise ValueError(f"Unknown baseline: {self.baseline}")

    def _list_subjects(self) -> List[str]:
        test_dir = self.data_dir / "test"
        if not test_dir.exists():
            raise FileNotFoundError(f"MMLU test directory not found: {test_dir}")
        subjects = []
        for p in sorted(test_dir.glob("*_test.csv")):
            subjects.append(p.name.replace("_test.csv", ""))
        return subjects

    def _sample_questions(self, subjects: List[str]) -> List[Sample]:
        rng = random.Random(self.seed)
        # Expand all (subject, idx) pairs, then sample.
        all_items: List[Sample] = []
        for subject in subjects:
            test_path = self.data_dir / "test" / f"{subject}_test.csv"
            df = pd.read_csv(test_path, header=None)
            for i in range(df.shape[0]):
                all_items.append(Sample(subject=subject, test_path=str(test_path), test_idx=i))

        if self.n_samples >= len(all_items):
            rng.shuffle(all_items)
            return all_items

        return rng.sample(all_items, self.n_samples)

    def run(self) -> float:
        subjects = self._list_subjects()
        samples = self._sample_questions(subjects)

        results: List[Dict[str, Any]] = []
        correct = 0

        # Per-question evaluation: use dev split of the same subject for few-shot context.
        for s in samples:
            subject = s.subject
            dev_path = self.data_dir / "dev" / f"{subject}_dev.csv"
            test_path = Path(s.test_path)
            dev_df = pd.read_csv(dev_path, header=None)
            test_df = pd.read_csv(test_path, header=None)

            prompt = _build_query_prompt(dev_df, test_df, subject, s.test_idx, self.ntrain)
            wrapped = self._wrap_prompt_by_baseline(prompt)
            out = self._chat(wrapped)

            pred = _extract_answer_letter(out)
            # Label is in the last column.
            label = str(test_df.iloc[s.test_idx, test_df.shape[1] - 1]).strip().upper()
            is_correct = pred == label
            if is_correct:
                correct += 1

            results.append(
                {
                    "subject": subject,
                    "test_path": str(test_path),
                    "test_idx": int(s.test_idx),
                    "label": label,
                    "pred": pred,
                    "correct": bool(is_correct),
                    "baseline": self.baseline,
                    "model": self.model,
                }
            )

        acc = correct / max(len(samples), 1)

        if self.save_path:
            Path(self.save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump({"acc": acc, "n": len(samples), "results": results}, f, ensure_ascii=False, indent=2)

        return acc

