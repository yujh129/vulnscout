from vulnscout.scanner.analyzer import _rule_check

def test_rule_check_detects_hardcoded_credential():
    findings = _rule_check("config.py", "password = 'secret123'", "python")
    assert len(findings) >= 1
    assert findings[0]["cwe_id"] == "CWE-798"

def test_rule_check_detects_eval():
    findings = _rule_check("danger.py", "eval(user_input)", "python")
    assert len(findings) >= 1
    assert findings[0]["cwe_id"] == "CWE-95"

def test_rule_check_clean_code():
    assert len(_rule_check("safe.py", "x = 1 + 2\nprint('hello')", "python")) == 0

def test_rule_check_cpp_strcpy():
    findings = _rule_check("main.cpp", "strcpy(buffer, user_input);", "cpp")
    assert len(findings) >= 1
    assert findings[0]["cwe_id"] == "CWE-121"

def test_rule_check_java_command_injection():
    findings = _rule_check("Main.java", 'Runtime.getRuntime().exec("rm -rf /");', "java")
    assert len(findings) >= 1
    assert findings[0]["cwe_id"] == "CWE-78"