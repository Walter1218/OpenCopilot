#!/usr/bin/env python3
"""
LLM深度能力验证测试

覆盖多领域、多类型、边际case的全面测试。
"""

import asyncio
import sys
import os
import json
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.models import SkillContext
from skill_architecture.coding_skill import CodingSkill
from llm_provider import MiniMaxProvider


class LLMProviderAdapter:
    """LLM提供者适配器"""
    def __init__(self, provider):
        self.provider = provider
    
    async def generate(self, prompt: str) -> str:
        response_parts = []
        for chunk in self.provider.stream_chat(prompt):
            response_parts.append(chunk)
        return "".join(response_parts)


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# ==================== 测试用例定义 ====================

# 1. 真实Web开发案例
WEB_CASES = [
    {
        "name": "React组件-状态管理",
        "intent": "code_review",
        "code": """
import React, { useState, useEffect } from 'react';

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(res => res.json())
      .then(data => {
        setUser(data);
        setLoading(false);
      });
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  return <div>{user.name}</div>;
}
""",
        "language": "javascript",
        "user_message": "审查这个React组件的代码质量"
    },
    {
        "name": "Express路由-安全漏洞",
        "intent": "refactor",
        "code": """
const express = require('express');
const app = express();

app.get('/user/:id', (req, res) => {
  const userId = req.params.id;
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  db.query(query, (err, results) => {
    if (err) throw err;
    res.json(results[0]);
  });
});

app.post('/login', (req, res) => {
  const { username, password } = req.body;
  if (eval(`global_${username}`)) {
    res.send('Welcome admin');
  }
});
""",
        "language": "javascript",
        "user_message": "修复这个Express路由中的安全漏洞"
    },
    {
        "name": "Vue组件-性能优化",
        "intent": "explain",
        "code": """
<template>
  <div>
    <input v-model="search" @input="onSearch" />
    <ul>
      <li v-for="item in filteredItems" :key="item.id">
        {{ item.name }} - {{ formatPrice(item.price) }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  data() {
    return {
      search: '',
      items: []
    }
  },
  computed: {
    filteredItems() {
      return this.items.filter(i => 
        i.name.includes(this.search)
      )
    }
  },
  methods: {
    formatPrice(price) {
      return '$' + price.toFixed(2)
    },
    onSearch() {
      this.$forceUpdate()
    }
  }
}
</script>
""",
        "language": "javascript",
        "user_message": "解释这个Vue组件的实现和潜在问题"
    }
]

# 2. 数据处理与算法案例
ALGORITHM_CASES = [
    {
        "name": "排序算法-性能分析",
        "intent": "analyze",
        "code": """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
""",
        "language": "python",
        "user_message": "分析这三种排序算法的性能特点和适用场景"
    },
    {
        "name": "动态规划-代码解释",
        "intent": "explain",
        "code": """
def longest_common_subsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    return dp[m][n]

def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            if weights[i-1] <= w:
                dp[i][w] = max(
                    dp[i-1][w],
                    dp[i-1][w-weights[i-1]] + values[i-1]
                )
            else:
                dp[i][w] = dp[i-1][w]
    
    return dp[n][capacity]
""",
        "language": "python",
        "user_message": "解释这两个动态规划算法的原理和状态转移方程"
    },
    {
        "name": "图算法-Bug修复",
        "intent": "bug_fix",
        "code": """
def dijkstra(graph, start):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    visited = set()
    
    while True:
        min_node = None
        for node in graph:
            if node not in visited:
                if min_node is None or distances[node] < distances[min_node]:
                    min_node = node
        
        if min_node is None:
            break
            
        visited.add(min_node)
        
        for neighbor, weight in graph[min_node].items():
            distance = distances[min_node] + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
    
    return distances

# 测试用例
graph = {
    'A': {'B': 1, 'C': 4},
    'B': {'A': 1, 'C': 2, 'D': 5},
    'C': {'A': 4, 'B': 2, 'D': 1},
    'D': {'B': 5, 'C': 1}
}
print(dijkstra(graph, 'A'))
""",
        "language": "python",
        "user_message": "这段Dijkstra算法代码有什么问题？"
    }
]

# 3. 系统编程案例
SYSTEM_CASES = [
    {
        "name": "多线程-竞态条件",
        "intent": "bug_fix",
        "code": """
import threading

class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        current = self.count
        # 模拟一些处理
        self.count = current + 1

counter = Counter()
threads = []

for _ in range(100):
    t = threading.Thread(target=lambda: [counter.increment() for _ in range(1000)])
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Expected: 100000, Got: {counter.count}")
""",
        "language": "python",
        "user_message": "修复这个多线程计数器的竞态条件问题"
    },
    {
        "name": "内存泄漏-资源管理",
        "intent": "code_review",
        "code": """
import sqlite3

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connections = []
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        self.connections.append(conn)
        return conn
    
    def query(self, sql, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        return cursor.fetchall()
    
    def batch_process(self, queries):
        results = []
        for sql, params in queries:
            results.append(self.query(sql, params))
        return results
""",
        "language": "python",
        "user_message": "审查这个数据库管理类的资源管理问题"
    },
    {
        "name": "异步编程-错误处理",
        "intent": "refactor",
        "code": """
import asyncio
import aiohttp

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def main():
    urls = [
        'https://api.example.com/1',
        'https://api.example.com/2',
        'https://invalid.url.that.will.fail',
    ]
    results = await fetch_all(urls)
    for url, result in zip(urls, results):
        print(f"{url}: {len(result)} bytes")

asyncio.run(main())
""",
        "language": "python",
        "user_message": "改进这个异步请求的错误处理机制"
    }
]

# 4. 数据科学案例
DATA_SCIENCE_CASES = [
    {
        "name": "Pandas数据处理",
        "intent": "code_review",
        "code": """
import pandas as pd
import numpy as np

def process_sales_data(file_path):
    df = pd.read_csv(file_path)
    
    # 删除空值
    df = df.dropna()
    
    # 计算总销售额
    df['total'] = df['price'] * df['quantity']
    
    # 按类别分组统计
    result = df.groupby('category').agg({
        'total': 'sum',
        'quantity': 'mean'
    })
    
    # 导出结果
    result.to_csv('sales_summary.csv')
    
    return result

# 处理大文件
data = process_sales_data('sales_2024.csv')
print(data.head())
""",
        "language": "python",
        "user_message": "审查这个数据处理脚本的代码质量"
    },
    {
        "name": "机器学习-过拟合问题",
        "intent": "explain",
        "code": """
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import numpy as np

def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    model = RandomForestClassifier(
        n_estimators=1000,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features='sqrt',
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"Training accuracy: {train_score:.4f}")
    print(f"Testing accuracy: {test_score:.4f}")
    
    return model
""",
        "language": "python",
        "user_message": "解释这个模型训练代码可能导致的问题"
    },
    {
        "name": "数据清洗-边界情况",
        "intent": "bug_fix",
        "code": """
def clean_data(data):
    cleaned = []
    for record in data:
        # 去除空值
        if record['name'] is None:
            continue
        
        # 格式化日期
        record['date'] = record['date'].split('T')[0]
        
        # 转换数值
        record['amount'] = float(record['amount'])
        
        # 验证范围
        if record['amount'] < 0:
            record['amount'] = 0
        
        cleaned.append(record)
    
    return cleaned

# 测试数据
test_data = [
    {'name': 'Alice', 'date': '2024-01-15T10:30:00', 'amount': '100.50'},
    {'name': None, 'date': '2024-01-16', 'amount': '50'},
    {'name': 'Bob', 'date': '2024-01-17T', 'amount': '-20'},
    {'name': 'Charlie', 'date': '2024-01-18', 'amount': 'abc'},
]
print(clean_data(test_data))
""",
        "language": "python",
        "user_message": "这段数据清洗代码有什么边界问题？"
    }
]

# 5. 边际Case
EDGE_CASES = [
    {
        "name": "空输入处理",
        "intent": "code_review",
        "code": "",
        "language": "python",
        "user_message": "审查这段代码"
    },
    {
        "name": "极简代码",
        "intent": "explain",
        "code": "x = 1",
        "language": "python",
        "user_message": "解释这段代码"
    },
    {
        "name": "特殊字符",
        "intent": "explain",
        "code": """
# -*- coding: utf-8 -*-
def greet(name):
    '''问候函数 - 支持中文'''
    return f'你好，{name}！欢迎使用系统。'

# 测试特殊字符
print(greet('张三'))
print(greet('李四'))
""",
        "language": "python",
        "user_message": "解释这段包含中文注释的代码"
    },
    {
        "name": "复杂嵌套结构",
        "intent": "analyze",
        "code": """
class Meta(type):
    def __new__(cls, name, bases, dct):
        dct['created_by'] = 'metaclass'
        return super().__new__(cls, name, bases, dct)

class Singleton(metaclass=Meta):
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, value=None):
        if not hasattr(self, 'initialized'):
            self.value = value
            self.initialized = True

class Database(Singleton):
    def __init__(self, connection_string=None):
        super().__init__(connection_string)
        if not hasattr(self, 'connected'):
            self.connected = True
    
    def query(self, sql):
        return f"Executing: {sql}"

# 测试
db1 = Database("postgres://localhost/mydb")
db2 = Database("postgres://localhost/other")
print(db1 is db2)  # True
print(db1.query("SELECT * FROM users"))
print(db1.created_by)  # 'metaclass'
""",
        "language": "python",
        "user_message": "分析这个使用元类实现单例模式的代码"
    },
    {
        "name": "递归深度问题",
        "intent": "bug_fix",
        "code": """
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result

# 测试正常情况
print(flatten([1, [2, 3], [4, [5, 6]]]))

# 创建深度嵌套
deep_list = [1]
for _ in range(10000):
    deep_list = [deep_list]

# 这会导致栈溢出
print(flatten(deep_list))
""",
        "language": "python",
        "user_message": "修复这个递归函数的栈溢出问题"
    }
]

# 6. 安全相关案例
SECURITY_CASES = [
    {
        "name": "XSS漏洞",
        "intent": "refactor",
        "code": """
from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    template = f'''
    <html>
        <body>
            <h1>搜索结果</h1>
            <p>您搜索的是: {query}</p>
            <div id="results">
                <!-- 搜索结果将在这里显示 -->
            </div>
        </body>
    </html>
    '''
    return render_template_string(template)

@app.route('/profile/<username>')
def profile(username):
    return f'''
    <html>
        <body>
            <h1>用户资料</h1>
            <script>
                var username = "{username}";
                document.title = "欢迎, " + username;
            </script>
        </body>
    </html>
    '''
""",
        "language": "python",
        "user_message": "修复这个Flask应用中的XSS漏洞"
    },
    {
        "name": "命令注入",
        "intent": "bug_fix",
        "code": """
import subprocess
import os

def ping_host(host):
    result = subprocess.run(
        f"ping -c 1 {host}",
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout

def list_files(directory):
    cmd = f"ls -la {directory}"
    os.system(cmd)

def backup_file(filename):
    os.popen(f"cp {filename} /backup/{filename}")
""",
        "language": "python",
        "user_message": "修复这些函数中的命令注入漏洞"
    },
    {
        "name": "硬编码密钥",
        "intent": "code_review",
        "code": """
import hashlib
import jwt

SECRET_KEY = "my_super_secret_key_123"
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'secret': SECRET_KEY
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except:
        return None
""",
        "language": "python",
        "user_message": "审查这个认证模块的安全问题"
    }
]

# 7. 常用功能案例
COMMON_CASES = [
    {
        "name": "文件IO操作",
        "intent": "code_review",
        "code": """
import json
import csv

def read_json_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def write_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f)

def read_csv_file(filepath):
    data = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)
    return data

def process_large_file(filepath):
    results = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                results.append(process_line(line))
    return results

def process_line(line):
    return line.strip().split(',')
""",
        "language": "python",
        "user_message": "审查这些文件IO操作的代码质量"
    },
    {
        "name": "API客户端",
        "intent": "refactor",
        "code": """
import requests

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            self.token = response.json()['token']
        return response.status_code == 200
    
    def get_user(self, user_id):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/users/{user_id}",
            headers=headers
        )
        return response.json()
    
    def create_user(self, user_data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/users",
            headers=headers,
            json=user_data
        )
        return response.json()
""",
        "language": "python",
        "user_message": "重构这个API客户端，添加错误处理和重试机制"
    },
    {
        "name": "日志系统",
        "intent": "explain",
        "code": """
import logging
from datetime import datetime

class Logger:
    _instance = None
    
    def __new__(cls, name='app'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup(name)
        return cls._instance
    
    def _setup(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message, exc_info=True):
        self.logger.error(message, exc_info=exc_info)
    
    def debug(self, message):
        self.logger.debug(message)

# 使用示例
log = Logger('myapp')
log.info('Application started')
log.debug('Debug message')
""",
        "language": "python",
        "user_message": "解释这个日志系统的实现原理"
    }
]


# ==================== 测试执行 ====================

async def run_single_test(skill, test_case):
    """运行单个测试"""
    name = test_case["name"]
    print(f"\n  [{name}]")
    
    ctx = SkillContext(
        intent=test_case["intent"],
        input_data={
            "code": test_case["code"],
            "language": test_case.get("language", "python"),
            "user_message": test_case.get("user_message", "")
        }
    )
    
    start = time.time()
    try:
        result = await skill.execute(ctx)
        duration = time.time() - start
        
        success = result.success
        data = result.data if result.data else {}
        error = getattr(result, 'error', '') or ''
        
        # 提取关键信息
        response = data.get("response", "")
        explanation = data.get("explanation", "")
        review = data.get("review", "")
        analysis = data.get("analysis", "")
        fix_suggestion = data.get("fix_suggestion", "")
        refactored_code = data.get("refactored_code", "")
        issues = data.get("issues", [])
        suggestions = data.get("suggestions", [])
        
        # 计算响应质量
        response_text = response or explanation or review or analysis or fix_suggestion or refactored_code
        response_length = len(response_text)
        has_issues = len(issues) > 0
        has_suggestions = len(suggestions) > 0
        
        status = "PASS" if success else "FAIL"
        print(f"    {status} ({duration:.2f}s) | 响应长度: {response_length} | 问题数: {len(issues)} | 建议数: {len(suggestions)}")
        
        if error:
            print(f"    错误: {error[:100]}")
        
        return {
            "name": name,
            "category": test_case.get("category", "unknown"),
            "intent": test_case["intent"],
            "passed": success,
            "duration": duration,
            "response_length": response_length,
            "issues_count": len(issues),
            "suggestions_count": len(suggestions),
            "has_issues": has_issues,
            "has_suggestions": has_suggestions,
            "error": error
        }
    except Exception as e:
        duration = time.time() - start
        print(f"    EXCEPTION ({duration:.2f}s): {str(e)[:100]}")
        return {
            "name": name,
            "category": test_case.get("category", "unknown"),
            "intent": test_case["intent"],
            "passed": False,
            "duration": duration,
            "error": str(e)
        }


async def main():
    print("=" * 70)
    print("LLM深度能力验证测试 - 多领域多类型覆盖")
    print("=" * 70)
    
    # 初始化
    print("\n[1/2] 初始化LLM提供者...")
    try:
        minimax_provider = MiniMaxProvider()
        llm_adapter = LLMProviderAdapter(minimax_provider)
        print("   OK MiniMax提供者初始化成功")
    except Exception as e:
        print(f"   FAIL: {e}")
        sys.exit(1)
    
    print("\n[2/2] 初始化CodingSkill...")
    try:
        config = {"project_root": PROJECT_ROOT, "llm_provider": llm_adapter}
        skill = CodingSkill(config)
        success = await skill.initialize()
        print(f"   {'OK' if success else 'FAIL'} CodingSkill初始化{'成功' if success else '失败'}")
    except Exception as e:
        print(f"   FAIL: {e}")
        sys.exit(1)
    
    # 定义测试组
    test_groups = [
        ("Web开发案例", WEB_CASES),
        ("算法与数据结构", ALGORITHM_CASES),
        ("系统编程", SYSTEM_CASES),
        ("数据科学", DATA_SCIENCE_CASES),
        ("边际Case", EDGE_CASES),
        ("安全相关", SECURITY_CASES),
        ("常用功能", COMMON_CASES),
    ]
    
    # 运行所有测试
    all_results = []
    start_time = time.time()
    
    for group_name, cases in test_groups:
        print(f"\n{'='*70}")
        print(f"测试组: {group_name} ({len(cases)}个测试)")
        print("="*70)
        
        for case in cases:
            case["category"] = group_name
            result = await run_single_test(skill, case)
            all_results.append(result)
    
    total_time = time.time() - start_time
    
    # 生成报告
    print("\n" + "=" * 70)
    print("测试报告摘要")
    print("=" * 70)
    
    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("passed"))
    failed = total - passed
    
    print(f"\n总体统计:")
    print(f"  总测试数: {total}")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  通过率: {passed/total*100:.1f}%")
    print(f"  总耗时: {total_time:.2f}秒")
    print(f"  平均耗时: {total_time/total:.2f}秒")
    
    # 按类别统计
    print(f"\n按类别统计:")
    categories = {}
    for r in all_results:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "duration": 0}
        categories[cat]["total"] += 1
        if r.get("passed"):
            categories[cat]["passed"] += 1
        categories[cat]["duration"] += r.get("duration", 0)
    
    for cat, stats in categories.items():
        pass_rate = stats["passed"]/stats["total"]*100 if stats["total"] > 0 else 0
        avg_duration = stats["duration"]/stats["total"] if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} 通过 ({pass_rate:.1f}%) | 平均耗时: {avg_duration:.2f}s")
    
    # 按意图统计
    print(f"\n按意图统计:")
    intents = {}
    for r in all_results:
        intent = r.get("intent", "unknown")
        if intent not in intents:
            intents[intent] = {"total": 0, "passed": 0}
        intents[intent]["total"] += 1
        if r.get("passed"):
            intents[intent]["passed"] += 1
    
    for intent, stats in intents.items():
        pass_rate = stats["passed"]/stats["total"]*100 if stats["total"] > 0 else 0
        print(f"  {intent}: {stats['passed']}/{stats['total']} 通过 ({pass_rate:.1f}%)")
    
    # 响应质量统计
    print(f"\n响应质量统计:")
    response_lengths = [r.get("response_length", 0) for r in all_results if r.get("passed")]
    if response_lengths:
        print(f"  平均响应长度: {sum(response_lengths)/len(response_lengths):.0f} 字符")
        print(f"  最短响应: {min(response_lengths)} 字符")
        print(f"  最长响应: {max(response_lengths)} 字符")
    
    issues_count = sum(r.get("issues_count", 0) for r in all_results if r.get("passed"))
    suggestions_count = sum(r.get("suggestions_count", 0) for r in all_results if r.get("passed"))
    print(f"  发现的问题总数: {issues_count}")
    print(f"  生成的建议总数: {suggestions_count}")
    
    # 失败的测试
    failed_tests = [r for r in all_results if not r.get("passed")]
    if failed_tests:
        print(f"\n失败的测试:")
        for t in failed_tests:
            print(f"  - {t['name']}: {t.get('error', '未知错误')[:80]}")
    
    # 保存报告
    report = {
        "test_name": "LLM深度能力验证测试",
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/total*100:.1f}%",
        "total_duration": f"{total_time:.2f}s",
        "categories": categories,
        "intents": intents,
        "results": all_results
    }
    
    report_file = os.path.join(PROJECT_ROOT, "llm_comprehensive_test_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存: {report_file}")
    
    # 清理
    await skill.cleanup()
    print("\n资源清理完成")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
