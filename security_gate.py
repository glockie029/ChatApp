import json
import sys
import os

def check_bandit(report_file):
    """解析 Bandit (SAST) 报告"""
    if not os.path.exists(report_file):
        print(f"❌ 错误: 找不到 Bandit 报告文件: {report_file}")
        return "FAILURE"

    try:
        with open(report_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ 错误: Bandit 报告格式无效")
        return "FAILURE"

    results = data.get('results', [])
    metrics = data.get('metrics', {}).get('_totals', {})
    
    print(f"\n======== [Bandit SAST 扫描结果摘要] ========")
    print(f"总计扫描文件: {len(data.get('errors', [])) + len(results)}")
    print(f"发现漏洞总数: {len(results)}")
    
    high_sev = [r for r in results if r['issue_severity'] == 'HIGH']
    medium_sev = [r for r in results if r['issue_severity'] == 'MEDIUM']
    
    # 打印详细信息
    if high_sev:
        print(f"\n🚨 发现 {len(high_sev)} 个高危漏洞 (HIGH):")
        for r in high_sev:
            print(f"  - [{r['test_id']}] {r['issue_text']}")
            print(f"    位置: {r['filename']}:{r['line_number']}")
    
    if medium_sev:
        print(f"\n⚠️ 发现 {len(medium_sev)} 个中危漏洞 (MEDIUM):")
        for r in medium_sev:
            print(f"  - [{r['test_id']}] {r['issue_text']}")
            print(f"    位置: {r['filename']}:{r['line_number']}")

    # 门禁策略
    if len(high_sev) > 0:
        print("\n⛔ 结论: 存在高危漏洞，阻断流水线！")
        return "FAILURE"
    elif len(medium_sev) > 0:
        print("\n⚠️ 结论: 存在中危漏洞，标记为不稳定。")
        return "UNSTABLE"
    else:
        print("\n✅ 结论: 代码安全检查通过。")
        return "SUCCESS"

def check_safety(report_file):
    """解析 Safety (SCA) 报告，兼容 v2（列表）和 v3（嵌套对象）JSON 格式"""
    if not os.path.exists(report_file):
        print(f"⚠️ 提示: 找不到 Safety 报告文件: {report_file} (可能是未安装依赖或扫描失败)")
        return "SUCCESS"

    try:
        with open(report_file, 'r') as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        print("❌ 错误: Safety 报告格式无效，请确认 safety 版本及输出格式")
        return "FAILURE"

    # ── 格式适配 ──────────────────────────────────────────────
    # safety v2: JSON 是一个漏洞列表 [ [...], ... ]
    # safety v3: JSON 是嵌套对象 { "scan_results": { "packages": [...] } }
    vulnerabilities = []

    if isinstance(raw, list):
        # Safety v2 格式：每条记录为 [pkg, spec, ver, desc, vuln_id]
        for item in raw:
            if isinstance(item, list) and len(item) >= 5:
                vulnerabilities.append({
                    "package":          item[0],
                    "affected_range":   item[1],
                    "installed":        item[2],
                    "description":      item[3],
                    "vuln_id":          item[4],
                    "cve_id":           None,
                    "fix_versions":     [],
                })
            elif isinstance(item, dict):
                # v2 也可能是字典列表
                vulnerabilities.append({
                    "package":        item.get("package_name", item.get("name", "Unknown")),
                    "affected_range": item.get("vulnerable_spec", "N/A"),
                    "installed":      item.get("installed_version", item.get("version", "Unknown")),
                    "description":    item.get("advisory", item.get("description", "No description")),
                    "vuln_id":        item.get("vulnerability_id", item.get("id", "N/A")),
                    "cve_id":         item.get("CVE", item.get("cve", None)),
                    "fix_versions":   item.get("fixed_versions", []),
                })
    elif isinstance(raw, dict):
        # Safety v3 格式
        packages = (
            raw.get("scan_results", {})
               .get("packages", [])
        )
        for pkg_entry in packages:
            pkg_name    = pkg_entry.get("name", "Unknown")
            installed   = pkg_entry.get("version", "Unknown")
            for vuln in pkg_entry.get("vulnerabilities", {}).get("found", []):
                vulnerabilities.append({
                    "package":        pkg_name,
                    "affected_range": ", ".join(vuln.get("vulnerable_spec", [])),
                    "installed":      installed,
                    "description":    vuln.get("advisory", vuln.get("description", "No description")),
                    "vuln_id":        vuln.get("vulnerability_id", "N/A"),
                    "cve_id":         vuln.get("CVE", vuln.get("cve_id", None)),
                    "fix_versions":   vuln.get("fixed_versions", []),
                })
    # ────────────────────────────────────────────────────────────

    print(f"\n{'='*55}")
    print(f"  [Safety SCA 依赖漏洞扫描报告]")
    print(f"{'='*55}")
    print(f"  发现漏洞总数: {len(vulnerabilities)}")
    print(f"{'='*55}")

    if vulnerabilities:
        print(f"\n🚨 存在漏洞的依赖项详情:\n")
        for idx, v in enumerate(vulnerabilities, 1):
            fix_str = ", ".join(v["fix_versions"]) if v["fix_versions"] else "暂无修复版本信息"
            cve_str = v["cve_id"] if v["cve_id"] else "N/A"
            desc    = v["description"]
            # 截断过长描述，避免日志刷屏
            desc_short = (desc[:150] + "...") if len(desc) > 150 else desc

            print(f"  [{idx}] 📦 包名        : {v['package']}")
            print(f"      📌 当前版本    : {v['installed']}")
            print(f"      ⚠️  受影响范围  : {v['affected_range']}")
            print(f"      🆔 漏洞 ID     : {v['vuln_id']}")
            print(f"      🔖 CVE 编号    : {cve_str}")
            print(f"      🔧 修复版本    : {fix_str}")
            print(f"      📝 漏洞描述    : {desc_short}")
            print()

        print(f"{'='*55}")
        print("⛔ 结论: 检测到供应链漏洞，流水线阻断！")
        print(f"   → 请参考上方修复版本升级对应依赖包\n")
        return "FAILURE"

    print("\n✅ 结论: 依赖组件安全检查通过，未发现已知 CVE 漏洞。")
    return "SUCCESS"

if __name__ == "__main__":
    # 读取命令行参数来决定检查哪个报告
    tool = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    exit_code = 0
    
    if tool == 'bandit' or tool == 'all':
        status = check_bandit('bandit_report.json')
        if status == "FAILURE":
            exit_code = 1
        elif status == "UNSTABLE" and exit_code == 0:
            exit_code = 2 # 使用 2 代表 Unstable

    if tool == 'safety' or tool == 'all':
        # 如果 Bandit 已经失败了，Safety 的结果不会改变退出码为 0，但可能会保持 1
        status = check_safety('safety_report.json')
        if status == "FAILURE":
            exit_code = 1

    sys.exit(exit_code)