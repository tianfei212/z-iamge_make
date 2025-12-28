import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api_handler import APIHandler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["qwen", "wan", "z_image"])
    parser.add_argument("prompt")
    parser.add_argument("--category", default="default")
    parser.add_argument("--model", default=None)
    parser.add_argument("--size", default="1024*1024")
    parser.add_argument("--negative", default="")
    parser.add_argument("--prompt_extend", action="store_true")
    args = parser.parse_args()

    handler = APIHandler()

    if args.service == "qwen":
        result = handler.call_qwen(args.prompt, model=args.model)
    elif args.service == "wan":
        result = handler.call_wan(
            args.prompt,
            model=args.model,
            category=args.category,
            size=args.size,
            negative_prompt=args.negative,
        )
    else:
        result = handler.call_z_image(
            args.prompt,
            category=args.category,
            size=args.size,
            prompt_extend=args.prompt_extend,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
