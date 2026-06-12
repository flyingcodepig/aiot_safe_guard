"""Regression tests for safe device mention matching."""
from device_loader import DeviceCapabilityLoader


def test_device_mentioned_in_input():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    check = loader.device_mentioned_in_input

    assert check("light_a1", "打开实验区A的灯"), "explicit light alias should match"
    assert check("solder_b1", "把焊台温度调到300"), "explicit solder alias should match"
    assert check("light_a1", "light_a1 的状态是什么"), "device_id should match"
    assert check("door_office", "打开办公室门"), "explicit office door alias should match"
    assert not check("light_a1", "把风扇调到40"), "unrelated input should not match"
    assert not check("laser_cutter_99", "启动激光切割机"), "unknown device should not match"
    assert not check("light_a1", "关灯"), "single-character generic alias should not match"
    assert not check("door_office", "打开电梯门"), "generic door suffix should not match office door"
    assert not check("light_a1", ""), "empty input should not match"


def test_any_device_mentioned():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    any_mentioned = loader.any_device_mentioned

    assert any_mentioned("打开实验区A的灯"), "explicit light alias should match"
    assert any_mentioned("把焊台温度调到300"), "explicit solder alias should match"
    assert any_mentioned("打开走廊灯"), "explicit corridor light alias should match"
    assert any_mentioned("关掉风扇"), "explicit fan alias should match"
    assert any_mentioned("打开办公室门"), "explicit office door alias should match"

    assert not any_mentioned("启动激光切割机"), "unknown device should not match"
    assert not any_mentioned("打开电梯门"), "unknown door should not match"
    assert not any_mentioned("用量子计算机计算加密密钥"), "unrelated input should not match"
    assert not any_mentioned("今天的天气怎么样"), "chat query should not match a device"
    assert not any_mentioned(""), "empty input should not match"


def test_device_disambiguation_safety():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    any_mentioned = loader.any_device_mentioned

    assert not any_mentioned("打开实验室的灯"), "ambiguous generic light should not match"
    assert not any_mentioned("打开门"), "ambiguous generic door should not match"
    assert not any_mentioned("关闭南门闸机"), "unknown gate should not match office door"


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
        except AssertionError as exc:
            print(f"FAIL: {name} - {exc}")
            failed += 1
        except AttributeError as exc:
            print(f"FAIL: {name} - {exc}")
            failed += 1

    print(f"\n{failed} test(s) failed" if failed else "\nALL TESTS PASSED")
