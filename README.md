# [WWW 2026] FraudShield: Knowledge Graph Empowered Defense for LLMs against Fraud Attacks

[arXiv](https://arxiv.org/abs/2601.22485)
[Python](https://www.python.org/)
[License: MIT](./LICENSE)

This is the official implementation of **"FraudShield: Knowledge Graph Empowered Defense for LLMs against Fraud Attacks"** (WWW 2026).

## 📑 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Acknowledgement](#acknowledgement)
- [Citation](#citation)

## 📌 Overview

The paper introduces **FraudShield**, a tactic-aware defense pipeline that extracts suspicious fraud signals, aligns them with fraud tactics, and augments model inputs with structured evidence to improve safe refusal behavior while preserving utility on benign tasks.

- **Defense**: `ours` (keyword/tactic extraction + XML-based augmentation)
- **Baselines**: `vanilla`, `safetyprompt`, `selfreminder`, `goal`
- **Effectiveness**: one-round / multi-round DSR
- **Utility**: MMLU ACC
- **Judge flow**: one-round manual judge (`--mode judge`), multi-round auto judge

## 📦 Installation

### Create environment

```bash
conda create -n fraudshield python=3.10 -y
conda activate fraudshield
pip install -r requirements.txt
```

### Configure API keys

Edit:

```bash
config/keys.json
```

### Prepare datasets

Make sure the following directories exist:

- `./data/Fraud-R1-main/dataset/FP-base-full`
- `./data/Fraud-R1-main/dataset/FP-levelup-full`
- `./data/MMLU/dev`
- `./data/MMLU/test`

## 🚀 Quick Start

### 1) Run defense/baseline generation (single-round)

```bash
python main.py \
  --mode attack \
  --attack_type LevelAttack \
  --sub_task one-round \
  --scenario assistant \
  --model gpt-4o-mini \
  --baseline ours \
  --question_input_path ./data/Fraud-R1-main/dataset/FP-base-full/FP-base-English.json \
  --answer_save_path ./results/one-round/FP-base-English_ours.json
```

### 2) Run DSR evaluation

For one-round, run manual judge first:

```bash
python main.py \
  --mode judge \
  --question_input_path ./results/one-round/FP-base-English_ours.json \
  --answer_save_path ./results/one-round/FP-base-English_ours_eval.json
```

```bash
python main.py \
  --mode eval \
  --eval_type one-round \
  --eval_input_folder ./results/one-round-LevelAttack \
  --eval_output_file ./results/metrics/one-round
```

```bash
python main.py \
  --mode eval \
  --eval_type multi-round \
  --eval_input_folder ./results/multi-round-LevelAttack \
  --eval_output_file ./results/metrics/multi-round
```

### 3) Run utility evaluation (MMLU ACC)

```bash
python main.py \
  --mode utility \
  --model gpt-4o-mini \
  --baseline ours \
  --mmlu_data_dir ./data/MMLU \
  --mmlu_ntrain 5 \
  --mmlu_n_samples 2000 \
  --mmlu_seed 42 \
  --mmlu_save_path ./results/utility/mmlu_acc.json
```

## 🎁 Acknowledgement

This work builds upon several excellent open-source projects and related works:

- **Fraud-R1 : A Multi-Round Benchmark for Assessing the Robustness of LLM Against Augmented Fraud and Phishing Inducements** (ACL 2025 Findings) - [Paper](https://arxiv.org/abs/2501.13381) | [GitHub](https://github.com/kaustpradalab/Fraud-R1)
- **HoT: Highlighted Chain of Thought for Referencing Supporting Facts from Inputs** - [Paper](https://arxiv.org/abs/2503.02003) | [GitHub](https://github.com/anguyen8/hot)
- **Defending Large Language Models Against Jailbreaking Attacks Through Goal Prioritization** (ACL 2024)- [Paper](https://arxiv.org/abs/2311.09096) | [GitHub](https://github.com/thu-coai/JailbreakDefense_GoalPriority)

We thank the authors for their valuable contributions to the community.

## 📖 Citation

If you find this repository useful, please cite the paper:

```bibtex
@inproceedings{xu2026fraudshield,
  title={FraudShield: Knowledge Graph Empowered Defense for LLMs against Fraud Attacks},
  author={Xu, Naen and Zhang, Jinghuai and He, Ping and Zhou, Chunyi and Wang, Jun and Fu, Zhihui and Du, Tianyu and Wang, Zhaoxiang and Ji, Shouling},
  booktitle={Proceedings of the ACM Web Conference 2026},
  pages={2649--2660},
  year={2026}
}
```
