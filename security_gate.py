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
    """解析 Safety (SCA) 报告"""
    if not os.path.exists(report_file):
        # Safety 如果没发现漏洞可能不会生成文件，或者生成空文件，需视版本而定
        # 这里假设生成了报告
        print(f"⚠️ 提示: 找不到 Safety 报告文件: {report_file} (可能是未安装依赖或扫描失败)")
        return "SUCCESS"

    try:
        with open(report_file, 'r') as f:
            # Safety 的 JSON 格式是一个列表
            vulnerabilities = json.load(f)
    except json.JSONDecodeError:
        print("❌ 错误: Safety 报告格式无效")
        return "FAILURE"

    print(f"\n======== [Safety SCA 扫描结果摘要] ========")
    print(f"发现依赖漏洞数: {len(vulnerabilities)}")

    if vulnerabilities:
        print(f"\n🚨 发现以下组件存在已知漏洞:")
        for v in vulnerabilities:
            # 兼容不同版本的 Safety JSON 结构
            pkg = v.get('package_name', v.get('name', 'Unknown'))
            ver = v.get('installed_version', v.get('version', 'Unknown'))
            desc = v.get('advisory', 'No description')
            print(f"  - {pkg} ({ver}): {desc[:100]}...")
        
        print("\n⛔ 结论: 存在供应链漏洞，阻断流水线！")
        return "FAILURE"
    
    print("\n✅ 结论: 依赖组件安全检查通过。")
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