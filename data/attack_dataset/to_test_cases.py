"""
将攻击数据集转换为 /api/run_tests 兼容的测试用例格式
"""
import json
import os
import random

BASE_DIR = os.path.dirname(__file__)

# 用户ID映射
USERS = ["u001", "u002", "u003", "u004"]
ROLES = {"u001": "student", "u002": "teacher", "u003": "admin", "u004": "visitor"}


def main():
    # 加载去重文本
    texts_path = os.path.join(BASE_DIR, "attack_texts.json")
    with open(texts_path, "r", encoding="utf-8") as f:
        texts = json.load(f)

    # 对每条文本生成测试用例
    cases = []
    for i, text in enumerate(texts):
        # 随机分配用户角色（攻击场景中各种角色都可能出现）
        user_id = random.choice(USERS)

        cases.append({
            "id": f"ATK{i+1:04d}",
            "description": f"攻击数据集样本 #{i+1}",
            "category": "attack_dataset",
            "user_id": user_id,
            "user_input": text,
            "expected_decision": "block",
            "expected_block_reason": "input_guard",
        })

    output_path = os.path.join(BASE_DIR, "attack_test_cases.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    print(f"生成 {len(cases)} 条测试用例")
    print(f"输出: {output_path}")
    print(f"\n使用方法:")
    print(f"  curl -X POST http://localhost:8000/api/run_tests \\")
    print(f"    -F 'file=@data/attack_dataset/attack_test_cases.json'")


if __name__ == "__main__":
    main()
