#!/usr/bin/env python3
"""
Security Scanner for Project Monolith
Run this script periodically to check for security issues
"""

import os
import subprocess
import sys
from pathlib import Path

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


def check_git_secrets():
    print_header("Checking for Exposed Secrets in Git")

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=Path(__file__).parent
        )

        env_files = [f for f in result.stdout.split("\n") if ".env" in f and f.strip()]
        if env_files:
            print(f"{RED}❌ DANGER: .env file is staged or modified:{RESET}")
            for f in env_files:
                print(f"  {f}")
            return False
        else:
            print(f"{GREEN}✓ No .env files staged{RESET}")

        result = subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.stdout.strip():
            print(f"{RED}❌ WARNING: .env is tracked in git!{RESET}")
            print("   Run: git filter-repo --path .env --invert-purge")
            return False
        else:
            print(f"{GREEN}✓ .env is not tracked in git{RESET}")

        return True
    except Exception as e:
        print(f"{YELLOW}⚠ Could not check git: {e}{RESET}")
        return None


def check_env_example():
    print_header("Checking .env.example")

    env_example = Path(".env.example")
    if not env_example.exists():
        print(f"{YELLOW}⚠ No .env.example found - consider creating one{RESET}")
        return None

    with open(env_example) as f:
        content = f.read()
        if any(key in content for key in ["YOUR_TOKEN", "YOUR_KEY", "PLACEHOLDER"]):
            print(f"{GREEN}✓ .env.example contains placeholder values{RESET}")
            return True
        else:
            print(f"{RED}❌ .env.example may contain real values{RESET}")
            return False


def check_dependencies():
    print_header("Checking Dependencies for CVEs")

    try:
        subprocess.run(["pip", "install", "-q", "safety"], check=True, capture_output=True)
        result = subprocess.run(["safety", "check", "--json"], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"{GREEN}✓ No known vulnerabilities found{RESET}")
            return True
        else:
            print(f"{RED}❌ Vulnerabilities found:{RESET}")
            print(result.stdout)
            return False
    except FileNotFoundError:
        print(f"{YELLOW}⚠ Safety not installed. Run: pip install safety{RESET}")
        return None
    except Exception as e:
        print(f"{YELLOW}⚠ Could not check dependencies: {e}{RESET}")
        return None


def check_sql_injection():
    print_header("Checking for SQL Injection Patterns")

    risky_patterns = [
        (r'execute\s*\(\s*f["\'].*\{.*\}', "f-string in SQL execute"),
        (r"\.format\s*\(.*\).*execute", ".format in SQL execute"),
        (r'execute\s*\(\s*["\'].*%s.*\)', "String formatting in SQL execute"),
    ]

    issues = []
    for pattern, desc in risky_patterns:
        result = subprocess.run(
            ["grep", "-r", "-E", pattern, "--include=*.py", "zenith_"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.stdout:
            issues.append(f"{desc}: {result.stdout[:200]}")

    if issues:
        print(f"{RED}❌ Potential SQL issues found:{RESET}")
        for issue in issues:
            print(f"  {issue[:100]}")
        return False
    else:
        print(f"{GREEN}✓ No obvious SQL injection patterns{RESET}")
        return True


def check_hardcoded_secrets():
    print_header("Checking for Hardcoded Secrets")

    suspicious = [
        (r'password\s*=\s*["\'][^$]', "hardcoded password"),
        (r'api_key\s*=\s*["\'][^$]', "hardcoded API key"),
        (r'secret\s*=\s*["\'][^$]', "hardcoded secret"),
        (r'token\s*=\s*["\'][A-Za-z0-9_-]{20,}', "hardcoded token"),
    ]

    issues = []
    for pattern, desc in suspicious:
        result = subprocess.run(
            ["grep", "-r", "-E", pattern, "--include=*.py", "core/", "zenith_"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.stdout and "os.getenv" not in result.stdout:
            issues.append(f"{desc}: {result.stdout[:100]}")

    if issues:
        print(f"{YELLOW}⚠ Potential hardcoded secrets:{RESET}")
        for issue in issues:
            print(f"  {issue[:100]}")
        return False
    else:
        print(f"{GREEN}✓ No hardcoded secrets found{RESET}")
        return True


def check_rate_limiting():
    print_header("Checking Rate Limiting")

    files_to_check = ["main.py"]

    for file in files_to_check:
        result = subprocess.run(
            ["grep", "-l", "rate_limit", file], capture_output=True, text=True, cwd=Path(__file__).parent
        )

        if result.stdout.strip():
            print(f"{GREEN}✓ Rate limiting found in {file}{RESET}")
            return True

    print(f"{RED}❌ No rate limiting found{RESET}")
    return False


def check_security_headers():
    print_header("Checking Security Headers")

    main_file = Path("main.py")
    if not main_file.exists():
        print(f"{YELLOW}⚠ main.py not found{RESET}")
        return None

    content = main_file.read_text()

    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Strict-Transport-Security",
    ]

    missing = [h for h in required_headers if h not in content]

    if missing:
        print(f"{RED}❌ Missing security headers: {missing}{RESET}")
        return False
    else:
        print(f"{GREEN}✓ Security headers configured{RESET}")
        return True


def check_webhook_auth():
    print_header("Checking Webhook Authentication")

    bot_files = [
        "run_admin_bot.py",
        "run_group_bot.py",
        "run_ai_bot.py",
        "run_crypto_bot.py",
        "run_support_bot.py",
    ]

    results = []
    for bot_file in bot_files:
        result = subprocess.run(
            ["grep", "-l", "WEBHOOK_SECRET", bot_file], capture_output=True, text=True, cwd=Path(__file__).parent
        )

        if result.returncode == 0:
            result2 = subprocess.run(
                ["grep", "-l", "secret != WEBHOOK_SECRET", bot_file],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent,
            )
            if result2.returncode == 0:
                results.append((bot_file, True))
            else:
                results.append((bot_file, False))

    if all(r[1] for r in results):
        print(f"{GREEN}✓ All bots have webhook secret validation{RESET}")
        return True
    else:
        print(f"{RED}❌ Missing webhook validation in: {[r[0] for r in results if not r[1]]}{RESET}")
        return False


def main():
    print(f"\n{GREEN}🔒 Project Monolith Security Scanner{RESET}")
    print("=" * 60)

    os.chdir(Path(__file__).parent)

    results = []

    results.append(("Git Secrets", check_git_secrets()))
    results.append((".env.example", check_env_example()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("SQL Injection", check_sql_injection()))
    results.append(("Hardcoded Secrets", check_hardcoded_secrets()))
    results.append(("Rate Limiting", check_rate_limiting()))
    results.append(("Security Headers", check_security_headers()))
    results.append(("Webhook Auth", check_webhook_auth()))

    print_header("Summary")

    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print(f"{YELLOW}Skipped: {skipped}{RESET}")

    if failed > 0:
        print(f"\n{RED}❌ Security issues found! Please fix them.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}✓ All checks passed!{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
