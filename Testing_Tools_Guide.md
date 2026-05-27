# OpenCopilot 测试工具使用指南

> **版本**: v2.0 | **日期**: 2026-05-28 | **状态**: 已完成安装 | 阶段1-4已实现

---

## 一、已安装测试工具

### 1.1 工具清单
| 工具 | 版本 | 用途 | 状态 |
|------|------|------|------|
| pytest | 8.4.2 | 单元测试框架 | ✅ 已安装 |
| coverage | 7.14.0 | 代码覆盖率统计 | ✅ 已安装 |
| allure-pytest | 2.16.0 | 测试报告生成 | ✅ 已安装 |
| locust | 2.44.0 | 性能测试 | ✅ 已安装 |

### 1.2 验证安装
```bash
# 检查已安装的测试工具
pip list | grep -E "(pytest|coverage|allure|locust)"

# 预期输出：
# allure-pytest          2.16.0
# coverage               7.14.0
# locust                 2.44.0
# pytest                 8.4.2
```

---

## 二、pytest 使用指南

### 2.1 基本用法
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/unit/test_basic_functionality.py -v

# 运行特定测试类
python -m pytest tests/unit/test_basic_functionality.py::TestBasicFunctionality -v

# 运行特定测试方法
python -m pytest tests/unit/test_basic_functionality.py::TestBasicFunctionality::test_python_version -v
```

### 2.2 常用选项
```bash
# 显示详细输出
python -m pytest tests/ -v

# 显示简短输出
python -m pytest tests/ -q

# 显示失败的详细信息
python -m pytest tests/ --tb=short

# 显示完整的失败信息
python -m pytest tests/ --tb=long

# 停止在第一个失败的测试
python -m pytest tests/ -x

# 运行匹配特定模式的测试
python -m pytest tests/ -k "test_python"
```

### 2.3 测试发现规则
- 测试文件名: `test_*.py` 或 `*_test.py`
- 测试类名: `Test*`
- 测试函数名: `test_*`

---

## 三、coverage 使用指南

### 3.1 基本用法
```bash
# 运行测试并收集覆盖率数据
coverage run -m pytest tests/

# 生成覆盖率报告
coverage report

# 生成HTML格式的覆盖率报告
coverage html

# 查看HTML报告
open htmlcov/index.html
```

### 3.2 常用选项
```bash
# 显示缺失的行
coverage report --show-missing

# 设置最低覆盖率阈值
coverage report --fail-under=80

# 只统计特定目录
coverage run --source=tools,asu_custom_agent.py -m pytest tests/

# 排除特定文件
coverage run --omit="tests/*,test_*" -m pytest tests/
```

### 3.3 配置文件
创建 `.coveragerc` 文件：
```ini
[run]
source = .
omit = 
    tests/*
    test_*
    setup.py
    .venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
    except ImportError
```

---

## 四、allure 使用指南

### 4.1 基本用法
```bash
# 运行测试并生成allure数据
python -m pytest tests/ --alluredir=allure-results

# 生成allure报告
allure serve allure-results

# 或者生成静态报告
allure generate allure-results -o allure-report --clean

# 打开报告
open allure-report/index.html
```

### 4.2 在代码中使用allure
```python
import allure

@allure.feature("用户模块")
@allure.story("登录功能")
@allure.severity(allure.severity_level.CRITICAL)
def test_user_login():
    """测试用户登录"""
    with allure.step("输入用户名和密码"):
        # 测试步骤
        pass
    
    with allure.step("点击登录按钮"):
        # 测试步骤
        pass
    
    with allure.step("验证登录成功"):
        # 断言
        assert True
```

### 4.3 常用装饰器
```python
@allure.feature("功能模块")
@allure.story("用户故事")
@allure.title("测试标题")
@allure.description("测试描述")
@allure.severity(allure.severity_level.CRITICAL)
@allure.link("https://jira.example.com/PROJ-123", name="JIRA链接")
@allure.issue("https://github.com/example/issue/1", name="Issue链接")
@allure.testcase("https://testcase.example.com/1", name="测试用例链接")
```

---

## 五、locust 使用指南

### 5.1 基本用法
创建 `locustfile.py`：
```python
from locust import HttpUser, task, between

class OpenCopilotUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(1)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")
    
    @task(2)
    def agent_chat(self):
        """Agent对话"""
        self.client.post("/v1/agent/chat", json={
            "text": "hello",
            "action_type": "auto",
            "session_id": "test_session"
        })
```

### 5.2 运行性能测试
```bash
# 启动locust（带Web界面）
locust -f locustfile.py --host=http://127.0.0.1:18888

# 无Web界面运行
locust -f locustfile.py --host=http://127.0.0.1:18888 --headless -u 10 -r 1 -t 30s

# 参数说明：
# -u: 用户数
# -r: 每秒启动的用户数
# -t: 运行时间
```

### 5.3 查看结果
- 访问 http://localhost:8089 查看Web界面
- 查看请求统计、响应时间、失败率等指标

---

## 六、测试用例示例

### 6.1 单元测试示例
```python
# tests/unit/test_example.py
import pytest
import sys

class TestExample:
    """示例测试类"""
    
    def test_addition(self):
        """测试加法"""
        assert 1 + 1 == 2
    
    def test_string_operations(self):
        """测试字符串操作"""
        text = "OpenCopilot"
        assert len(text) == 11
        assert "Copilot" in text
    
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_multiply_by_two(self, input, expected):
        """参数化测试"""
        assert input * 2 == expected
```

### 6.2 集成测试示例
```python
# tests/integration/test_api.py
import pytest
import httpx

class TestAPI:
    """API集成测试"""
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = httpx.get("http://127.0.0.1:18888/health")
        assert response.status_code == 200
    
    def test_agent_chat(self):
        """测试Agent对话"""
        payload = {
            "text": "hello",
            "action_type": "auto",
            "session_id": "test"
        }
        response = httpx.post(
            "http://127.0.0.1:18888/v1/agent/chat",
            json=payload
        )
        assert response.status_code == 200
```

### 6.3 性能测试示例
```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class LoadTestUser(HttpUser):
    wait_time = between(0.5, 2)
    
    @task(3)
    def read_file(self):
        """测试文件读取性能"""
        self.client.post("/v1/agent/chat", json={
            "text": "读取文件",
            "action_type": "auto",
            "session_id": "load_test"
        })
    
    @task(1)
    def translate(self):
        """测试翻译性能"""
        self.client.post("/v1/agent/chat", json={
            "text": "Translate this to Chinese",
            "action_type": "translate",
            "session_id": "load_test"
        })
```

---

## 七、测试最佳实践

### 7.1 测试命名规范
```python
# 文件名: test_<module>.py
# 类名: Test<Feature>
# 方法名: test_<action>_<condition>

# 示例:
# test_tools.py
# TestFileTools
# test_file_read_success
# test_file_read_not_found
```

### 7.2 测试结构
```python
class TestFeature:
    """功能测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.test_data = "setup"
    
    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理资源
        pass
    
    def test_success_case(self):
        """测试成功场景"""
        # Arrange - 准备
        input_data = "test"
        
        # Act - 执行
        result = process(input_data)
        
        # Assert - 断言
        assert result == "expected"
    
    def test_error_case(self):
        """测试错误场景"""
        with pytest.raises(ValueError):
            process(None)
```

### 7.3 测试覆盖率目标
- **单元测试覆盖率**: > 80%
- **集成测试覆盖率**: > 60%
- **关键路径覆盖率**: 100%

---

## 八、CI/CD 集成

### 8.1 GitHub Actions 示例
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest coverage allure-pytest
    
    - name: Run tests
      run: |
        coverage run -m pytest tests/
        coverage report
        coverage xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### 8.2 本地CI脚本
创建 `run_tests.sh`：
```bash
#!/bin/bash

# 运行测试
echo "Running tests..."
python -m pytest tests/ -v --tb=short

# 生成覆盖率报告
echo "Generating coverage report..."
coverage run -m pytest tests/
coverage report --show-missing
coverage html

# 生成allure报告
echo "Generating allure report..."
python -m pytest tests/ --alluredir=allure-results
allure generate allure-results -o allure-report --clean

echo "Tests completed!"
```

---

## 九、故障排除

### 9.1 常见问题
1. **pytest找不到测试**
   - 检查文件名是否以`test_`开头
   - 检查类名是否以`Test`开头
   - 检查方法名是否以`test_`开头

2. **coverage统计不准确**
   - 检查`.coveragerc`配置
   - 确保源代码路径正确

3. **allure报告为空**
   - 确保使用`--alluredir`参数
   - 检查allure-results目录是否存在

4. **locust连接失败**
   - 确保目标服务正在运行
   - 检查端口是否正确

### 9.2 调试技巧
```bash
# 显示详细的测试发现信息
python -m pytest tests/ --collect-only

# 显示最慢的10个测试
python -m pytest tests/ --durations=10

# 在第一个失败后停止
python -m pytest tests/ -x

# 显示本地变量
python -m pytest tests/ -l
```

---

## 十、参考资源

### 10.1 官方文档
- [pytest官方文档](https://docs.pytest.org/)
- [coverage官方文档](https://coverage.readthedocs.io/)
- [allure官方文档](https://docs.qameta.io/allure/)
- [locust官方文档](https://docs.locust.io/)

### 10.2 示例项目
- `tests/unit/` - 单元测试示例
- `tests/integration/` - 集成测试示例
- `tests/performance/` - 性能测试示例

---

*本指南基于OpenCopilot项目实际安装的测试工具编写，具体使用请参考官方文档。*