import argparse
import json
import random

from api_handler import APIHandler


PROMPTS = [
    "雨夜霓虹灯下的未来城市街道，电影级写实摄影",
    "一只戴着宇航员头盔的猫，超现实主义，细节丰富",
    "古代山水画风格的云海与松树，国风水墨",
    "微距摄影：水滴里的彩虹折射，极高细节，浅景深",
    "赛博朋克风格的机械花朵，金属质感，冷色调",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="测试")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--wan_model", default=None)
    parser.add_argument("--z_model", default=None)
    parser.add_argument("--z_size", default="1024*1024")
    parser.add_argument("--z_prompt_extend", action="store_true")
    args = parser.parse_args()

    rnd = random.Random(args.seed)
    prompt = rnd.choice(PROMPTS)

    handler = APIHandler()

    z_result = handler.call_z_image(
        prompt,
        category=args.category,
        size=args.z_size,
        prompt_extend=args.z_prompt_extend,
    )
    wan_result = handler.call_wan(prompt, model=args.wan_model, category=args.category)

    out = {
        "prompt": prompt,
        "category": args.category,
        "z_image": z_result,
        "wan": wan_result,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
