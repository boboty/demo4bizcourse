"""对某次盲测生成的测试文件做启发式静态扫描，辅助人工判定——不是最终结论。

判定的是同一个操作性问题：对 GOLD + amount>=1000 + coupon=VIP100 这个组合场景，
生成的测试里有没有任何一个测试函数，在同一个函数体内同时对 membershipDiscount
和 couponDiscount（或 discount）做了数值断言。这是纯语法层面的启发式扫描（找
dict/字面量里的 GOLD、amount、VIP100，以及函数体里出现的 assert 语句涉及的字段
名），代码风格差异可能让它漏报或误报，最终判断以人工读代码为准，写在
review-notes.md 里。

用法：python experiments/real-generation/scan_trial.py trial-1
"""

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "experiments" / "real-generation"


def scan_function(func: ast.FunctionDef, full_source: str) -> dict:
    func_source = ast.get_source_segment(full_source, func) or ""
    has_gold = "GOLD" in func_source
    has_vip100 = ("VIP100" in func_source) and not (
        "VIP100-NO-STACK" in func_source and "VIP100\"" not in func_source and "VIP100'" not in func_source
    )
    has_bare_vip100 = ('"VIP100"' in func_source) or ("'VIP100'" in func_source)
    has_amount_1000_plus = any(
        tok in func_source for tok in ("1200", "1000", "1500", "2000")
    )
    asserts_membership = "membershipDiscount" in func_source
    asserts_coupon = "couponDiscount" in func_source
    asserts_discount_200 = ("discount" in func_source) and ("200" in func_source)

    candidate_combined = has_gold and has_bare_vip100 and has_amount_1000_plus
    breakdown_asserted_together = candidate_combined and asserts_membership and asserts_coupon

    return {
        "name": func.name,
        "looks_like_combined_scenario": candidate_combined,
        "asserts_membershipDiscount_in_func": asserts_membership,
        "asserts_couponDiscount_in_func": asserts_coupon,
        "asserts_discount_200_present": asserts_discount_200,
        "BOTH_membership_and_coupon_asserted_in_same_func": breakdown_asserted_together,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: scan_trial.py <trial-dir-name>", file=sys.stderr)
        return 2
    trial_dir = BASE_DIR / sys.argv[1]
    test_file = trial_dir / "generated_test_orders.py"
    if not test_file.is_file():
        print(f"no generated test file at {test_file}", file=sys.stderr)
        return 2

    source = test_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]

    lines = [f"# 启发式扫描：{test_file.relative_to(PROJECT_ROOT)}", f"共 {len(functions)} 个 test_* 函数\n"]
    any_hit = False
    for func in functions:
        info = scan_function(func, source)
        lines.append(f"## {info['name']}")
        lines.append(f"- 疑似命中组合场景(GOLD+VIP100+金额>=1000字样同时出现): {info['looks_like_combined_scenario']}")
        if info["looks_like_combined_scenario"]:
            lines.append(f"  - 函数体内出现 membershipDiscount: {info['asserts_membershipDiscount_in_func']}")
            lines.append(f"  - 函数体内出现 couponDiscount: {info['asserts_couponDiscount_in_func']}")
            lines.append(f"  - 函数体内出现 discount 与 200 同现: {info['asserts_discount_200_present']}")
            lines.append(f"  - >>> 同一函数内 membershipDiscount 与 couponDiscount 同时出现: {info['BOTH_membership_and_coupon_asserted_in_same_func']}")
            any_hit = any_hit or info["BOTH_membership_and_coupon_asserted_in_same_func"]
        lines.append("")

    lines.append(f"启发式初判（未经人工确认）：{'可能覆盖了组合场景断言' if any_hit else '未发现组合场景下同时断言两个字段的函数'}")
    lines.append("这是字符串层面的启发式扫描，不是语义分析；最终判断请人工读函数源码后写入 review-notes.md。")

    out = trial_dir / "auto-scan-notes.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
