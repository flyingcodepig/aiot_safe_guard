"""
TDD: 设备提及校验 + 语义意图门禁
"""
from device_loader import DeviceCapabilityLoader


def test_device_mentioned_in_input():
    """单设备检查：用户输入是否提到了指定设备"""
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    check = loader.device_mentioned_in_input

    assert check("light_a1", "打开实验区A的灯"), "别名匹配"
    assert check("solder_b1", "把焊台温度调到300"), "别名 '焊台' 匹配"
    assert check("light_a1", "light_a1 的状态是什么"), "device_id 匹配"
    assert not check("light_a1", "把风扇调到50"), "无关输入不匹配"
    assert not check("laser_cutter_99", "启动激光切割机"), "不存在设备不匹配"
    assert check("light_a1", "关灯"), "单字别名 '灯' 匹配"
    assert not check("light_a1", ""), "空输入不匹配"


def test_any_device_mentioned():
    """全局检查：用户输入是否提到了任何已知设备"""
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    any_mentioned = loader.any_device_mentioned

    # 提到已知道设备 → True
    assert any_mentioned("打开实验区A的灯"), "提到 light_a1 的别名"
    assert any_mentioned("把焊台温度调到300"), "提到 solder_b1 的别名"
    assert any_mentioned("打开走廊灯"), "提到 light_corridor1 的别名"
    assert any_mentioned("关掉风扇"), "提到 fan_a1"

    # 完全没有提到任何设备 → False
    assert not any_mentioned("启动激光切割机"), "零设备匹配"
    assert not any_mentioned("用量子计算机计算加密密钥"), "零设备匹配"
    assert not any_mentioned("派巡逻机器人去实验室巡检"), "零设备匹配"

    # 边界情况
    assert not any_mentioned(""), "空输入不匹配"
    assert not any_mentioned("今天天气怎么样"), "纯闲聊不匹配任何设备"


def test_device_disambiguation_safety():
    """验证：不明确的设备引用不会被误拦"""
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    any_mentioned = loader.any_device_mentioned

    # "实验室的灯" — 虽然不是任何设备的精确别名，但"灯"匹配 light_a1/light_corridor1
    assert any_mentioned("打开实验室的灯"), "通过 '灯' 匹配到多个灯设备"
    # "打开门" — "门"不在任何设备名/别名中，但"门锁"在 door_office name 中
    # 这里取决于别名覆盖度。如果 door_office 有"门"别名则通过
    # 实际 door_office name="办公室门锁"，包含"门"但不包含独立的"门"作为别名
    # 这个测试记录当前行为，作为文档


if __name__ == "__main__":
    failed = 0
    for name, fn in [
        ("device_mentioned_in_input", test_device_mentioned_in_input),
        ("any_device_mentioned", test_any_device_mentioned),
        ("device_disambiguation_safety", test_device_disambiguation_safety),
    ]:
        try:
            fn()
            print(f"PASS: {name}")
        except AssertionError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1
        except AttributeError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1

    print(f"\n{failed} test(s) failed" if failed else "\nALL TESTS PASSED")
