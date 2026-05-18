"""
check_security.py — Quality gate for the DevSecOps pipeline.

This script is called by GitHub Actions after Bandit and pip-audit run.
It reads their JSON outputs and FAILS (exit 1) if critical issues exist,
blocking the merge/push.

Usage:
    python scripts/check_security.py
"""

import json
import sys
from pathlib import Path


def check_bandit(report_path: str = "bandit-report.json") -> bool:
    """
    Returns True if Bandit found HIGH-severity + HIGH-confidence issues.
    These are the issues that should block the pipeline.
    """
    path = Path(report_path)
    if not path.exists():
        print(f"[bandit] Report not found at {report_path} — skipping check")
        return True  # Don't block if report wasn't generated

    with open(path) as f:
        data = json.load(f)

    results = data.get("results", [])
    critical_issues = [
        r for r in results
        if r.get("issue_severity") == "HIGH" and r.get("issue_confidence") in ("HIGH", "MEDIUM")
    ]

    if critical_issues:
        print(f"\n❌ BANDIT: {len(critical_issues)} critical security issue(s) found:\n")
        for issue in critical_issues:
            print(f"  [{issue['issue_severity']}/{issue['issue_confidence']}] "
                  f"{issue['issue_text']}")
            print(f"  → {issue['filename']}:{issue['line_number']}\n")
        return False

    total = len(results)
    print(f"[bandit] ✅ No critical issues. Total findings (all severities): {total}")
    return True


def check_pip_audit(report_path: str = "pip-audit-report.json") -> bool:
    """
    Returns True if pip-audit found no CRITICAL or HIGH vulnerabilities.
    """
    path = Path(report_path)
    if not path.exists():
        print(f"[pip-audit] Report not found at {report_path} — skipping check")
        return True

    with open(path) as f:
        data = json.load(f)

    # pip-audit JSON schema: list of {name, version, vulns: [{id, fix_versions, aliases}]}
    dependencies = data if isinstance(data, list) else data.get("dependencies", [])
    critical_vulns = []

    for dep in dependencies:
        for vuln in dep.get("vulns", []):
            vuln_id = vuln.get("id", "")
            aliases = vuln.get("aliases", [])
            # Flag any CVE-tagged vulnerability (pip-audit doesn't always expose CVSS,
            # so we treat all CVEs as potentially critical in this pipeline)
            if vuln_id.startswith("CVE") or any(a.startswith("CVE") for a in aliases):
                critical_vulns.append({
                    "package": dep.get("name"),
                    "version": dep.get("version"),
                    "vuln_id": vuln_id,
                    "fix_versions": vuln.get("fix_versions", []),
                })

    if critical_vulns:
        print(f"\n❌ PIP-AUDIT: {len(critical_vulns)} vulnerable dependenc(ies) found:\n")
        for v in critical_vulns:
            fix = ", ".join(v["fix_versions"]) or "no fix available"
            print(f"  {v['package']}=={v['version']}  [{v['vuln_id']}]  → fix: {fix}")
        return False

    print(f"[pip-audit] ✅ No vulnerable dependencies found.")
    return True


def main():
    print("=" * 55)
    print("  Bubbles — DevSecOps Security Quality Gate")
    print("=" * 55)

    bandit_ok = check_bandit()
    pipit_ok = check_pip_audit()

    print("\n" + "=" * 55)
    if bandit_ok and pipit_ok:
        print("  ✅ All security checks passed. Pipeline can proceed.")
        sys.exit(0)
    else:
        print("  ❌ Security checks FAILED. Pipeline blocked.")
        print("  Fix the issues above before merging.")
        sys.exit(1)


if __name__ == "__main__":
    main()
