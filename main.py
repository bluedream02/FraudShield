import argparse

from attacks.LevelAttack import LevelAttack
from evaluation.OneRoundDSR import DSRCalculatorONE
from evaluation.MultiRoundDSR import DSRCalculatorMUL
from utility.mmlu_acc import MMLUAccRunner


def main():
    parser = argparse.ArgumentParser(
        description="FraudShield: run attack/defense, judge, evaluation, and utility."
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["attack", "judge", "eval", "utility"],
        help="attack: generate responses; judge: manual one-round judging; eval: aggregate DSR; utility: MMLU ACC.",
    )
    parser.add_argument("--model", type=str, help="Victim model name (e.g., gpt-4o-mini)")

    parser.add_argument(
        "--attack_type",
        type=str,
        choices=["LevelAttack"],
        help="Currently only LevelAttack is supported.",
    )
    parser.add_argument(
        "--sub_task",
        type=str,
        choices=["one-round", "multi-round"],
        help="one-round: single turn; multi-round: multi-turn (auto judge).",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["assistant", "roleplay"],
        help="assistant or roleplay.",
    )

    parser.add_argument("--question_input_path", type=str, help="Input JSON path")
    parser.add_argument("--answer_save_path", type=str, help="Output JSON path")
    parser.add_argument(
        "--baseline",
        type=str,
        default="vanilla",
        help="vanilla/safetyprompt/selfreminder/goal/ours",
    )
    parser.add_argument("--tau", type=int, default=5, help="FraudShield threshold tau (default 5)")

    parser.add_argument("--eval_input_folder", type=str, help="Evaluation input folder (results root)")
    parser.add_argument("--eval_output_file", type=str, help="Evaluation output folder")
    parser.add_argument(
        "--eval_type",
        type=str,
        choices=["one-round", "multi-round"],
        help="Evaluation type: one-round or multi-round",
    )

    # utility (MMLU)
    parser.add_argument(
        "--mmlu_data_dir",
        type=str,
        default="./data/MMLU",
        help="MMLU data directory (the folder containing dev/val/test).",
    )
    parser.add_argument("--mmlu_ntrain", type=int, default=5, help="Number of few-shot examples (default 5)")
    parser.add_argument("--mmlu_n_samples", type=int, default=2000, help="Number of sampled questions (default 2000)")
    parser.add_argument("--mmlu_seed", type=int, default=42, help="Sampling random seed")
    parser.add_argument(
        "--mmlu_save_path",
        type=str,
        default=None,
        help="Optional: output JSON path for per-sample utility results",
    )

    args = parser.parse_args()

    if args.mode == "attack":
        if args.attack_type != "LevelAttack":
            raise ValueError("--attack_type currently only supports LevelAttack")
        level = LevelAttack(
            file_name=args.question_input_path,
            model=args.model,
            output_file=args.answer_save_path,
            task=args.sub_task,
            scenario=args.scenario,
            baseline=args.baseline,
            tau=args.tau,
        )
        level.process_fraud_data()
        return

    if args.mode == "judge":
        # Manual one-round judge: input should already contain one-round responses.
        level = LevelAttack(
            file_name=args.question_input_path,
            model=args.model or "",
            output_file=args.answer_save_path,
            task="one-round-eval",
            scenario="assistant",
            baseline="vanilla",
            tau=args.tau,
        )
        level.process_fraud_data()
        return

    if args.mode == "eval":
        if args.eval_type == "one-round":
            dsr = DSRCalculatorONE(args.eval_input_folder, args.eval_output_file)
            dsr.run()
            return
        if args.eval_type == "multi-round":
            dsr = DSRCalculatorMUL(args.eval_input_folder, args.eval_output_file)
            dsr.run()
            return
        raise ValueError("Unknown --eval_type")

    if args.mode == "utility":
        runner = MMLUAccRunner(
            model=args.model,
            data_dir=args.mmlu_data_dir,
            ntrain=args.mmlu_ntrain,
            n_samples=args.mmlu_n_samples,
            seed=args.mmlu_seed,
            baseline=args.baseline,
            tau=args.tau,
            save_path=args.mmlu_save_path,
        )
        acc = runner.run()
        print(f"MMLU ACC: {acc:.4f}")
        return


if __name__ == "__main__":
    main()

