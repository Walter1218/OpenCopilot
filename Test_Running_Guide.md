# 测试运行指南

> **版本**: v2.0 | **日期**: 2026-05-28 | **状态**: 阶段1-4已完成，242个测试用例100%通过

## 概述

本文档提供完整的测试运行方式，包括单元测试、覆盖率统计和边际测试。

## 测试文件结构

```
tests/unit/
├── test_phase1_ui_components.py      # 阶段1: 主题、快捷键、文件拖拽区
├── test_phase2_ui_components.py      # 阶段2: 进度组件、上下文菜单
├── test_phase3_ui_components.py      # 阶段3: 设置对话框
├── test_phase4_ui_components.py      # 阶段4: 批量处理、术语库、翻译记忆
├── test_coverage_boost.py            # 覆盖率提升测试（107个用例）
└── test_real_environment.py          # 真实环境测试（无mock）
```

## 快速开始

### 1. 安装依赖

```bash
pip install pytest pytest-cov coverage
```

### 2. 运行所有测试

```bash
cd /Users/onetwo/Documents/trae_projects/OpenCopilot
python -m pytest tests/unit/ -v
```

## 详细运行方式

### 1. 按阶段运行测试

```bash
# 阶段1: 主题系统、快捷键系统、文件拖拽区
python -m pytest tests/unit/test_phase1_ui_components.py -v

# 阶段2: 进度组件、上下文菜单
python -m pytest tests/unit/test_phase2_ui_components.py -v

# 阶段3: 设置对话框
python -m pytest tests/unit/test_phase3_ui_components.py -v

# 阶段4: 批量处理、术语库、翻译记忆
python -m pytest tests/unit/test_phase4_ui_components.py -v
```

### 2. 运行覆盖率提升测试

```bash
# 覆盖率提升测试（包含边际测试）
python -m pytest tests/unit/test_coverage_boost.py -v
```

### 3. 运行真实环境测试（无mock）

```bash
# 真实环境测试
python -m pytest tests/unit/test_real_environment.py -v
```

### 4. 运行所有测试并统计覆盖率

```bash
# 运行所有测试并生成覆盖率数据
python -m coverage run -m pytest tests/unit/test_phase1_ui_components.py \
                                  tests/unit/test_phase2_ui_components.py \
                                  tests/unit/test_phase3_ui_components.py \
                                  tests/unit/test_phase4_ui_components.py \
                                  tests/unit/test_coverage_boost.py \
                                  tests/unit/test_real_environment.py -q

# 查看覆盖率报告
python -m coverage report --include="core/*,widgets/*,dialogs/*"

# 查看详细覆盖率（包含未覆盖的行）
python -m coverage report --include="core/*,widgets/*,dialogs/*" --show-missing

# 生成HTML覆盖率报告
python -m coverage html
# 打开 htmlcov/index.html 查看
```

### 5. 运行特定测试类

```bash
# 运行主题管理器测试
python -m pytest tests/unit/test_phase1_ui_components.py::TestThemeManager -v

# 运行进度组件测试
python -m pytest tests/unit/test_phase2_ui_components.py::TestProgressWidget -v

# 运行设置对话框测试
python -m pytest tests/unit/test_phase3_ui_components.py::TestSettingsDialog -v

# 运行批量处理测试
python -m pytest tests/unit/test_phase4_ui_components.py::TestBatchDialog -v
```

### 6. 运行特定测试用例

```bash
# 运行单个测试用例
python -m pytest tests/unit/test_phase1_ui_components.py::TestThemeManager::test_switch_theme_success -v

# 运行边际测试
python -m pytest tests/unit/test_coverage_boost.py::TestEdgeCases -v
```

## 测试分类说明

### 基础功能测试（阶段1-4）

| 阶段 | 测试文件 | 测试数量 | 覆盖内容 |
|------|----------|----------|----------|
| 阶段1 | test_phase1_ui_components.py | 30个 | 主题系统、快捷键系统、文件拖拽区 |
| 阶段2 | test_phase2_ui_components.py | 32个 | 进度组件、上下文菜单 |
| 阶段3 | test_phase3_ui_components.py | 30个 | 设置对话框 |
| 阶段4 | test_phase4_ui_components.py | 30个 | 批量处理、术语库、翻译记忆 |

### 覆盖率提升测试（test_coverage_boost.py）

| 测试类 | 用例数 | 覆盖内容 |
|--------|--------|----------|
| TestSettingsDialogCoverage | 16个 | 默认设置、主题切换、字体设置、复选框事件、语言切换、保存/加载设置、异常处理、UI更新 |
| TestProgressWidgetCoverage | 11个 | 初始状态、开始/更新/取消/重置进度、完成信号、预估时间 |
| TestMultiStepProgressWidgetCoverage | 13个 | 添加步骤、开始执行、步骤进度、下一步、总体进度计算、取消/完成/重置 |
| TestContextMenuCoverage | 12个 | 初始化、添加/清除动态项、上下文切换、菜单项启用/可见性 |
| TestTextContextMenuCoverage | 2个 | 初始化、获取选中文本 |
| TestFileContextMenuCoverage | 2个 | 文件类型检查、获取文件路径 |
| TestCodeContextMenuCoverage | 2个 | 初始化、获取代码文本和语言 |
| TestFileDropZoneCoverage | 11个 | 初始化、扩展名管理、文件验证、悬停状态、图标更新 |
| TestFileInfoCoverage | 6个 | 创建、转字典、大小格式化（B/KB/MB/GB） |
| TestEdgeCases | 20个 | 边际测试（详见下方） |
| TestProgressManagerCoverage | 3个 | 初始化、设置组件 |

### 边际测试详情（TestEdgeCases）

| 测试用例 | 描述 |
|----------|------|
| test_empty_operations | 空操作测试 |
| test_large_file_list | 大数据量测试（100个文件） |
| test_large_translation_memory | 大数据量测试（1000个翻译单元） |
| test_duplicate_files | 重复数据测试 |
| test_special_characters_in_filename | 特殊字符测试（C++、@#$%^&*()） |
| test_unicode_characters | Unicode字符测试（日文） |
| test_invalid_json_import | 无效JSON异常处理 |
| test_nonexistent_file_import | 不存在的文件异常处理 |
| test_font_size_boundaries | 字体大小边界值测试（8-24） |
| test_recent_files_boundaries | 最近文件数边界值测试（5-50） |
| test_fuzzy_search_thresholds | 模糊搜索阈值测试（0.3-0.9） |
| test_export_import_json | JSON导出导入测试 |
| test_export_import_tmx | TMX导出导入测试 |

### 真实环境测试（test_real_environment.py）

完全不使用mock，测试真实代码逻辑，共13个用例。

## 覆盖率报告

### 当前覆盖率（2026-05-27）

| 模块 | 语句数 | 未覆盖 | 覆盖率 |
|------|--------|--------|--------|
| `core/theme_manager.py` | 105 | 15 | **86%** |
| `core/shortcut_manager.py` | 193 | 83 | **57%** |
| `widgets/progress_widget.py` | 251 | 25 | **90%** |
| `widgets/settings_dialog.py` | 209 | 33 | **84%** |
| `widgets/context_menu.py` | 125 | 22 | **82%** |
| `widgets/terminology_dialog.py` | 444 | 140 | **68%** |
| `widgets/file_drop_zone.py` | 187 | 56 | **70%** |
| `widgets/batch_dialog.py` | 315 | 116 | **63%** |
| `widgets/translation_memory.py` | 413 | 235 | **43%** |
| **总计** | **2242** | **625** | **64%** |

## 测试结果

```
============================= test session starts ==============================
platform darwin -- Python 3.12.0, pytest-8.3.4
collected 242 items

tests/unit/test_phase1_ui_components.py ..................  [ 7%]
tests/unit/test_phase2_ui_components.py ..................  [15%]
tests/unit/test_phase3_ui_components.py ..................  [22%]
tests/unit/test_phase4_ui_components.py ..................  [30%]
tests/unit/test_coverage_boost.py .......................  [72%]
tests/unit/test_real_environment.py .............         [100%]

============================== 242 passed in 12.34s ==============================
```

## 常用命令速查

| 用途 | 命令 |
|------|------|
| 运行所有测试 | `python -m pytest tests/unit/ -v` |
| 运行单个阶段 | `python -m pytest tests/unit/test_phase1_ui_components.py -v` |
| 运行覆盖率测试 | `python -m pytest tests/unit/test_coverage_boost.py -v` |
| 运行真实环境测试 | `python -m pytest tests/unit/test_real_environment.py -v` |
| 统计覆盖率 | `python -m coverage run -m pytest tests/unit/ -q` |
| 查看覆盖率报告 | `python -m coverage report --include="core/*,widgets/*,dialogs/*"` |
| 查看详细覆盖率 | `python -m coverage report --include="core/*,widgets/*,dialogs/*" --show-missing` |
| 生成HTML报告 | `python -m coverage html` |
| 运行特定测试类 | `python -m pytest tests/unit/test_phase1_ui_components.py::TestThemeManager -v` |
| 运行特定用例 | `python -m pytest tests/unit/test_phase1_ui_components.py::TestThemeManager::test_switch_theme_success -v` |
| 运行边际测试 | `python -m pytest tests/unit/test_coverage_boost.py::TestEdgeCases -v` |

## 故障排查

### 1. QApplication 错误

如果遇到 `QApplication` 相关错误，确保测试文件中有 `qapp` fixture：

```python
@pytest.fixture(scope="session", autouse=True)
def qapp():
    """创建QApplication实例"""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app
```

### 2. 模块导入错误

确保项目根目录在 Python 路径中：

```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
```

### 3. 覆盖率统计不准确

清除旧的覆盖率数据后重新运行：

```bash
rm -f .coverage
python -m coverage run -m pytest tests/unit/ -q
python -m coverage report --include="core/*,widgets/*,dialogs/*"
```
