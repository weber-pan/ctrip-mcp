#!/usr/bin/env python3
"""
verify-no-hardcoded.py
======================
Skill 模板零硬编码自验脚本 (V5.1 抽象, 2026-06-10)

用途: 写完一组 skill 模板后, 用本脚本验证:
  - 模板/模式文件不含"硬编码"具体内容 (地名/航班号/酒店名/餐厅名/电话/货币/...)
  - 实战案例放在 references/ 单独管理
  - SKILL.md 章节结构完整

用法:
  python3 scripts/verify-no-hardcoded.py [SKILL_DIR]
  默认检查: /opt/data/skills/markdown-report-pdf/

退出码:
  0 = 全部干净
  1 = 发现硬编码
  2 = 缺文件/目录
"""
import os, sys, re

SKILL_DIR = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/skills/markdown-report-pdf"

# 硬编码黑名单 (V5.1 巴厘岛 + 通用 V5 实战字眼)
BANNED_DEFAULT = [
    # 目的地 / 景点
    "巴厘岛", "乌布", "金巴兰", "罗威纳", "佩尼达", "雅加达", "泗水", "赛伍瀑布", "bromo", "ijen",
    "Bali", "Bromo", "Ijen", "Penida", "Ubud", "Jimbaran", "Lovina", "Jakarta", "Surabaya",
    # 酒店 / 餐厅
    "Damarya", "Kinama", "Warung Mufu", "Menega", "This Is Bali", "Warung Ayu", "Secret Penida",
    "Aspice Kitchen", "Wolfgang Puck", "Bawang Merah", "Made Bagus", "Nelayan", "Tuban",
    "Amsterdam Restaurant", "Tropical Restaurant", "Natah Ubud", "Citrus Berry", "Shrida", "PASIR",
    "Secret Garden", "Spice Beach", "Mentari", "Barclona", "Cactus Beach", "Coco Penida",
    "PENIDA COLADA", "Fresh Restaurant", "Little Eats", "Garlic & Salt", "Warung Laota", "Warung Wardani",
    "Damarya Boutique", "Kinama Villa",
    # 航司 / 航班
    "GA895", "GA426", "GA411", "GA894", "HO 1355", "HO 1356", "MU 5029", "MU 5030",
    "鹰航", "印尼鹰航", "美程", "美亚", "吉祥航空", "Garuda", "Batik", "Citilink",
    "PVG", "CGK", "DPS",
    # 电话 / 客服
    "4008-789-789", "95569", "95530", "010-6588", "+62-361-239802", "+62-361-224111",
    "格蕾丝", "15807617904",
    # 货币 / 应急
    "印尼盾", "200万印尼盾", "1比2000",
    "finns beach club", "Finns",
    # 订单号 / 凭证
    "E5CWLA", "1128148437938177", "1128148437920950", "50339971", "454483611236",
    "126-9809715177", "EE1565613",
    # 其他 V5 特有
    "新探索国际旅行", "星游家", "7.4-7.10", "7.5/10", "7.4/7.10", "D-24",
    "evisa.imigrasi.go.id", "Bebek Betutu", "Babi Guling", "Iga Babi Panggang", "Bak Kut Teh",
    "Nasi Campur", "Soto Ayam", "Dadar Gulung", "Es Kelapa", "Pad Thai",
]

# 必需存在文件
REQUIRED_FILES = [
    "SKILL.md",
    "scripts/verify-no-hardcoded.py",  # 自指
]

# 模板目录扫描
TEMPLATE_PATTERNS = ["templates/*.md", "templates/patterns/*.md"]


def scan_file(path, banned):
    """扫描单个文件, 返回发现的硬编码词"""
    content = open(path, encoding="utf-8").read()
    found = [w for w in banned if w in content]
    return found


def main():
    print("=" * 60)
    print("🧪 模板零硬编码自验 (V5.1 抽象)")
    print("=" * 60)
    print(f"检查目录: {SKILL_DIR}")
    print()

    # 1. 必需文件
    print("📋 1. 必需文件检查")
    missing = []
    for f in REQUIRED_FILES:
        full = os.path.join(SKILL_DIR, f)
        if not os.path.exists(full):
            print(f"  ❌ MISSING: {f}")
            missing.append(f)
        else:
            print(f"  ✅ {f}")
    print()

    # 2. 模板文件硬编码扫描
    print("🔍 2. 模板文件硬编码扫描")
    templates_dir = os.path.join(SKILL_DIR, "templates")
    if not os.path.isdir(templates_dir):
        print(f"  ⚠️  templates/ 目录不存在 (新建 skill 可跳过)")
    else:
        template_files = []
        for pat in TEMPLATE_PATTERNS:
            import glob
            template_files.extend(glob.glob(os.path.join(SKILL_DIR, pat)))
        template_files = sorted(set(template_files))

        all_clean = True
        total_size = 0
        for tf in template_files:
            rel = os.path.relpath(tf, SKILL_DIR)
            content = open(tf, encoding="utf-8").read()
            found = [w for w in BANNED_DEFAULT if w in content]
            size_kb = os.path.getsize(tf) / 1024
            total_size += size_kb
            status = "❌" if found else "✅"
            if found: all_clean = False
            print(f"  {status} {rel}: ({size_kb:.1f}KB) {'硬编码: ' + str(found) if found else '干净'}")

        print(f"\n  模板总数: {len(template_files)} 个, 总大小: {total_size:.1f}KB")
        print()

    # 3. SKILL.md 章节结构
    print("📐 3. SKILL.md 章节结构")
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    if os.path.exists(skill_md):
        content = open(skill_md, encoding="utf-8").read()
        size_kb = os.path.getsize(skill_md) / 1024
        print(f"  SKILL.md: {size_kb:.1f}KB")
        # 关键章节 (各 skill 不同, 这里查 markdown-report-pdf 的)
        if "markdown-report-pdf" in SKILL_DIR:
            key_sections = {
                "§1 pipeline": "## 1. 完整 pipeline",
                "§8 智能向导": "## 8. 智能报告向导",
                "§9 模板库": "## 9. 实战模板库",
            }
        else:
            key_sections = {}  # 通用模式不强制
        for name, search in key_sections.items():
            print(f"  {'✅' if search in content else '❌'} {name}")
    else:
        print(f"  ❌ SKILL.md 不存在")

    print()
    print("=" * 60)
    if missing:
        print(f"❌ 缺 {len(missing)} 个必需文件, 退出码 2")
        return 2
    if 'all_clean' in dir() and not all_clean:
        print("❌ 模板有硬编码, 退出码 1")
        return 1
    print("🎉 全部干净, 框架与内容彻底分离, 退出码 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
