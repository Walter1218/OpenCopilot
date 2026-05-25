"""
Phase 2 单元测试：LaunchAgent 配置文件与部署脚本验证
==================================================

测试目标：
1. 验证 plist 模板存在且包含所有必要的 XML 节点
2. 验证三个 shell 脚本存在且具有可执行权限
3. 验证 install_daemon.sh 中的占位符替换逻辑正确
4. 验证 plist 中的关键 LaunchAgent 配置项齐全

运行方式：
    python test_daemon_scripts.py
"""

import sys
import os
import stat
import subprocess
import unittest
import plistlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLIST_TEMPLATE = os.path.join(BASE_DIR, "deploy", "com.asu.agent.plist")
SCRIPTS = {
    "install":   os.path.join(BASE_DIR, "scripts", "install_daemon.sh"),
    "uninstall": os.path.join(BASE_DIR, "scripts", "uninstall_daemon.sh"),
    "tail_logs": os.path.join(BASE_DIR, "scripts", "tail_logs.sh"),
}


class TestPlistTemplate(unittest.TestCase):
    """验证 plist 配置文件的结构完整性。"""

    def test_plist_file_exists(self):
        """[P2-T01] deploy/com.asu.agent.plist 必须存在"""
        self.assertTrue(os.path.isfile(PLIST_TEMPLATE),
            f"❌ plist 文件不存在: {PLIST_TEMPLATE}")
        print("  ✅ [P2-T01] plist 模板文件存在")

    def test_plist_contains_placeholders(self):
        """[P2-T02] plist 必须包含所有需要替换的占位符"""
        with open(PLIST_TEMPLATE, "r", encoding="utf-8") as f:
            content = f.read()
        required_placeholders = [
            "__PYTHON_EXECUTABLE__",
            "__ASU_PROJECT_DIR__",
            "__HOME__",
            "__PYTHON_BIN_DIR__",
        ]
        for ph in required_placeholders:
            self.assertIn(ph, content, f"❌ plist 缺少占位符: {ph}")
        print("  ✅ [P2-T02] plist 包含所有必要占位符")

    def test_plist_has_required_keys(self):
        """[P2-T03] plist 必须包含 Label/ProgramArguments/RunAtLoad/KeepAlive 等核心键"""
        with open(PLIST_TEMPLATE, "r", encoding="utf-8") as f:
            content = f.read()
        # 替换占位符为假值，让 plist 可以被解析
        fake = content \
            .replace("__PYTHON_EXECUTABLE__", "/usr/bin/python3") \
            .replace("__ASU_PROJECT_DIR__", "/tmp/asu") \
            .replace("__HOME__", "/tmp") \
            .replace("__PYTHON_BIN_DIR__", "/usr/bin")

        data = plistlib.loads(fake.encode("utf-8"))
        required_keys = ["Label", "ProgramArguments", "RunAtLoad", "KeepAlive",
                         "StandardOutPath", "StandardErrorPath", "WorkingDirectory"]
        for k in required_keys:
            self.assertIn(k, data, f"❌ plist 缺少必要键: {k}")
        print("  ✅ [P2-T03] plist 包含所有必要 LaunchAgent 键")

    def test_plist_run_at_load_true(self):
        """[P2-T04] RunAtLoad 必须为 true（开机自启）"""
        with open(PLIST_TEMPLATE, "r", encoding="utf-8") as f:
            content = f.read()
        fake = content \
            .replace("__PYTHON_EXECUTABLE__", "/usr/bin/python3") \
            .replace("__ASU_PROJECT_DIR__", "/tmp/asu") \
            .replace("__HOME__", "/tmp") \
            .replace("__PYTHON_BIN_DIR__", "/usr/bin")
        data = plistlib.loads(fake.encode("utf-8"))
        self.assertTrue(data.get("RunAtLoad"), "❌ RunAtLoad 不是 true，无法开机自启！")
        print("  ✅ [P2-T04] RunAtLoad = true（开机自启已启用）")

    def test_plist_keep_alive_true(self):
        """[P2-T05] KeepAlive 必须为 true（崩溃自动重启）"""
        with open(PLIST_TEMPLATE, "r", encoding="utf-8") as f:
            content = f.read()
        fake = content \
            .replace("__PYTHON_EXECUTABLE__", "/usr/bin/python3") \
            .replace("__ASU_PROJECT_DIR__", "/tmp/asu") \
            .replace("__HOME__", "/tmp") \
            .replace("__PYTHON_BIN_DIR__", "/usr/bin")
        data = plistlib.loads(fake.encode("utf-8"))
        self.assertTrue(data.get("KeepAlive"), "❌ KeepAlive 不是 true，崩溃后不会自动重启！")
        print("  ✅ [P2-T05] KeepAlive = true（崩溃自动重启已启用）")


class TestShellScripts(unittest.TestCase):
    """验证 shell 管理脚本的存在性和可执行权限。"""

    def test_install_script_exists(self):
        """[P2-T06] install_daemon.sh 必须存在"""
        self.assertTrue(os.path.isfile(SCRIPTS["install"]),
            f"❌ 安装脚本不存在: {SCRIPTS['install']}")
        print("  ✅ [P2-T06] install_daemon.sh 存在")

    def test_uninstall_script_exists(self):
        """[P2-T07] uninstall_daemon.sh 必须存在"""
        self.assertTrue(os.path.isfile(SCRIPTS["uninstall"]),
            f"❌ 卸载脚本不存在: {SCRIPTS['uninstall']}")
        print("  ✅ [P2-T07] uninstall_daemon.sh 存在")

    def test_tail_logs_script_exists(self):
        """[P2-T08] tail_logs.sh 必须存在"""
        self.assertTrue(os.path.isfile(SCRIPTS["tail_logs"]),
            f"❌ 日志脚本不存在: {SCRIPTS['tail_logs']}")
        print("  ✅ [P2-T08] tail_logs.sh 存在")

    def _is_executable(self, path):
        mode = os.stat(path).st_mode
        return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

    def test_all_scripts_executable(self):
        """[P2-T09] 所有脚本必须具有可执行权限"""
        for name, path in SCRIPTS.items():
            self.assertTrue(self._is_executable(path),
                f"❌ {name} 脚本缺少执行权限: {path}")
        print("  ✅ [P2-T09] 所有脚本具有可执行权限（chmod +x 已完成）")

    def test_scripts_bash_syntax(self):
        """[P2-T10] 所有脚本的 bash 语法必须合法（bash -n）"""
        for name, path in SCRIPTS.items():
            result = subprocess.run(["bash", "-n", path],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0,
                f"❌ {name} 存在 bash 语法错误:\n{result.stderr}")
        print("  ✅ [P2-T10] 所有脚本 bash 语法合法")

    def test_install_script_key_operations(self):
        """[P2-T11] install_daemon.sh 必须包含 launchctl load 操作"""
        with open(SCRIPTS["install"], "r") as f:
            content = f.read()
        self.assertIn("launchctl load", content,
            "❌ install_daemon.sh 未调用 launchctl load！")
        print("  ✅ [P2-T11] install_daemon.sh 包含 launchctl load")

    def test_uninstall_script_key_operations(self):
        """[P2-T12] uninstall_daemon.sh 必须包含 launchctl unload 操作"""
        with open(SCRIPTS["uninstall"], "r") as f:
            content = f.read()
        self.assertIn("launchctl unload", content,
            "❌ uninstall_daemon.sh 未调用 launchctl unload！")
        print("  ✅ [P2-T12] uninstall_daemon.sh 包含 launchctl unload")

    def test_install_script_placeholder_substitution(self):
        """[P2-T13] install_daemon.sh 必须包含 sed 占位符替换逻辑"""
        with open(SCRIPTS["install"], "r") as f:
            content = f.read()
        self.assertIn("sed", content,
            "❌ install_daemon.sh 未使用 sed 替换占位符！")
        self.assertIn("__ASU_PROJECT_DIR__", content,
            "❌ install_daemon.sh 未替换 __ASU_PROJECT_DIR__ 占位符！")
        print("  ✅ [P2-T13] install_daemon.sh 包含完整的 sed 占位符替换")

    def test_log_dir_created_in_install(self):
        """[P2-T14] install_daemon.sh 必须创建日志目录"""
        with open(SCRIPTS["install"], "r") as f:
            content = f.read()
        self.assertIn("mkdir -p", content,
            "❌ install_daemon.sh 未创建日志目录！")
        self.assertIn("Logs/ASU", content,
            "❌ install_daemon.sh 日志目录路径不正确！")
        print("  ✅ [P2-T14] install_daemon.sh 会自动创建日志目录")


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 2 单元测试：LaunchAgent 配置与部署脚本验证")
    print("=" * 60)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestPlistTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestShellScripts))

    result = unittest.TestResult()
    suite.run(result)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    if result.failures or result.errors:
        print("\n❌ 失败的测试：")
        for test, trace in result.failures + result.errors:
            print(f"   - {test}: {trace.splitlines()[-1]}")

    print()
    print("=" * 60)
    if failed == 0:
        print(f"  🎉 所有测试通过！({passed}/{total} PASSED)")
        print("  Phase 2 验证完成：LaunchAgent 配置与脚本已就绪。")
    else:
        print(f"  ⚠️  {failed} 个测试失败 ({passed}/{total} passed)")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)
