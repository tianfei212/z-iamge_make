import argparse
import json
import sys

from api_handler import APIHandler


def build_translate_prompt(text: str, target_lang: str) -> str:
    if target_lang.lower() in {"zh", "zh-cn", "chinese", "cn"}:
        return f"把下面文本翻译成中文，仅返回译文：\n\n{text}"
    return f"Translate the following text into English. Return translation only:\n\n{text}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--mode", choices=["echo", "translate", "both"], default="both")
    parser.add_argument("--target", default="en")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    handler = APIHandler()

    result = {"input": args.text, "mode": args.mode, "target": args.target}

    if args.mode in {"echo", "both"}:
        result["echo"] = handler.call_qwen(args.text, model=args.model)

    if args.mode in {"translate", "both"}:
        prompt = build_translate_prompt(args.text, args.target)
        result["translation"] = handler.call_qwen(prompt, model=args.model)

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

