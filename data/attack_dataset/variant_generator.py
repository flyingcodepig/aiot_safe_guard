"""
DeepSeek 变体生成器：从种子数据批量扩展攻击样本
使用方法: python variant_generator.py [--limit N] [--variants-per-seed N]
"""
import json
import os
import sys
import time
import argparse
from typing import List, Dict

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from openai import OpenAI


VARIANTS_PER_SEED = 3  # 每条种子生成的变体数
BATCH_DELAY = 0.5       # 批次间延迟（秒）


def build_prompt(seed_text: str, category_name: str, count: int) -> str:
    return f"""你是IoT安全测试专家。给定一条中文攻击样本，生成{count}条变体。

原始样本（类别：{category_name}）：
"{seed_text}"

变体要求：
1. 改变句式结构（陈述→疑问→祈使等）
2. 使用同义词替换关键动词
3. 在正常请求中插入/包裹攻击意图
4. 添加无关的干扰词但不改变核心攻击语义
5. 每条变体保持攻击意图不变

仅输出JSON数组，每条变体一个字符串，不要其他内容：
["变体1", "变体2", ...]"""


def generate_variants(
    client: OpenAI,
    model: str,
    seed: Dict,
    count: int,
) -> List[str]:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": build_prompt(
                    seed["text"], seed["category_name"], count
                )},
            ],
            temperature=0.8,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        content = content.strip("```json").strip("```").strip()
        variants = json.loads(content)
        return variants if isinstance(variants, list) else []
    except Exception as e:
        print(f"  生成失败 [{seed['id']}]: {e}")
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="限制处理的种子数（0=全部）")
    parser.add_argument("--variants-per-seed", type=int, default=VARIANTS_PER_SEED)
    parser.add_argument("--category", type=str, default="", help="仅处理指定类别")
    args = parser.parse_args()

    seed_path = os.path.join(os.path.dirname(__file__), "attack_seeds.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    seeds = seed_data["samples"]
    if args.category:
        seeds = [s for s in seeds if s["category"] == args.category]
    if args.limit > 0:
        seeds = seeds[:args.limit]

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    client = OpenAI(api_key=api_key, base_url=base_url)
    variants_per = args.variants_per_seed

    print(f"模型: {model}")
    print(f"种子数: {len(seeds)}")
    print(f"每条变体数: {variants_per}")
    print(f"预计生成: {len(seeds) * variants_per} 条")
    print(f"开始...")

    dataset = []
    total_variants = 0
    start_time = time.time()

    for i, seed in enumerate(seeds):
        # 每10条打印进度
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i / elapsed) if elapsed > 0 else 0
            eta = (len(seeds) - i) / rate if rate > 0 else 0
            print(f"  进度: {i}/{len(seeds)} ({i*100/len(seeds):.1f}%) "
                  f"生成: {total_variants} 速率: {rate:.1f}/s ETA: {eta:.0f}s")

        # 添加原始种子
        dataset.append({
            "id": seed["id"],
            "category": seed["category"],
            "category_name": seed["category_name"],
            "text": seed["text"],
            "source": "seed",
        })

        # 生成变体
        variants = generate_variants(client, model, seed, variants_per)
        for v_idx, v_text in enumerate(variants):
            if v_text and v_text != seed["text"] and len(v_text) > 5:
                dataset.append({
                    "id": f"{seed['id']}_v{v_idx+1}",
                    "category": seed["category"],
                    "category_name": seed["category_name"],
                    "text": v_text,
                    "source": "llm_variant",
                    "parent_id": seed["id"],
                })
                total_variants += 1

        time.sleep(BATCH_DELAY)

    elapsed = time.time() - start_time
    print(f"\n完成! 耗时: {elapsed:.0f}s")
    print(f"原始种子: {len(seeds)}")
    print(f"LLM变体: {total_variants}")
    print(f"总计: {len(dataset)}")

    output_path = os.path.join(os.path.dirname(__file__), "attack_dataset_full.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "description": "中文IoT攻击完整数据集 — 种子+DeepSeek变体",
            "total": len(dataset),
            "seed_count": len(seeds),
            "variant_count": total_variants,
            "generated_by": f"seed_generator + DeepSeek ({model})",
            "samples": dataset,
        }, f, ensure_ascii=False, indent=2)

    print(f"输出: {output_path}")

    # 去重后的纯文本列表（用于直接导入测试）
    text_path = os.path.join(os.path.dirname(__file__), "attack_texts.json")
    texts = list(set(s["text"] for s in dataset))
    with open(text_path, "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)
    print(f"去重文本: {len(texts)} 条 → {text_path}")


if __name__ == "__main__":
    main()
