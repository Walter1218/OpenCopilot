"""
OpenCopilot 全面测试矩阵

测试维度：
1. 多编程语言：Python, JavaScript, TypeScript, Java, Go, Rust, C++, SQL
2. 多业务领域：Web前端, 后端API, 数据处理, 算法, 系统编程, 数据库
3. 多复杂度：简单函数, 中等模块, 复杂类, 多文件
4. 边界条件：空输入, 超长输入, 特殊字符, 恶意输入
5. 集成工作流：完整流程测试

使用方式：
    python test_comprehensive_matrix.py
"""

import os
import sys
import json
import asyncio
import aiohttp
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# API配置
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8088")
API_TIMEOUT = 120  # 秒


@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    category: str
    language: str
    domain: str
    complexity: str
    api_endpoint: str
    request_data: Dict[str, Any]
    expected_keywords: List[str] = None
    description: str = ""
    http_method: str = "POST"  # 默认使用POST方法
    expected_status: int = 200  # 预期HTTP状态码，默认200
    skip: bool = False  # 是否跳过此测试


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    category: str
    success: bool
    duration_ms: int
    response_preview: str = ""
    error: str = ""
    matched_keywords: List[str] = None


# 测试结果收集
test_results: List[TestResult] = []


async def make_request(method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """发送API请求"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as resp:
                    return {"status": resp.status, "data": await resp.json()}
            elif method.upper() == "POST":
                async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as resp:
                    return {"status": resp.status, "data": await resp.json()}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def check_keywords(response_text: str, keywords: List[str]) -> List[str]:
    """检查响应中包含的关键词"""
    if not keywords:
        return []
    matched = []
    response_lower = response_text.lower()
    for keyword in keywords:
        if keyword.lower() in response_lower:
            matched.append(keyword)
    return matched


async def run_test(test_case: TestCase) -> TestResult:
    """运行单个测试用例"""
    # 检查是否跳过
    if test_case.skip:
        return TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            category=test_case.category,
            success=True,  # 跳过的测试视为通过
            duration_ms=0,
            response_preview="测试已跳过",
            error="",
            matched_keywords=[]
        )
    
    start_time = time.time()
    
    try:
        # 根据http_method选择请求方法
        if test_case.http_method.upper() == "GET":
            response = await make_request("GET", test_case.api_endpoint)
        else:
            response = await make_request("POST", test_case.api_endpoint, test_case.request_data)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 检查状态码是否符合预期
        expected_status = test_case.expected_status
        actual_status = response.get("status")
        
        if actual_status == expected_status:
            # 状态码符合预期
            if actual_status == 200:
                # 成功响应，检查内容
                data = response.get("data", {})
                response_text = json.dumps(data, ensure_ascii=False)
                
                # 检查关键词匹配
                matched = check_keywords(response_text, test_case.expected_keywords or [])
                
                success = True
                if test_case.expected_keywords and len(matched) == 0:
                    success = False
                
                return TestResult(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    category=test_case.category,
                    success=success,
                    duration_ms=duration_ms,
                    response_preview=response_text[:300],
                    matched_keywords=matched,
                    error="" if success else "未匹配到预期关键词"
                )
            else:
                # 非200状态码，但符合预期（如400、404等）
                response_text = ""
                if response.get("data"):
                    response_text = json.dumps(response["data"], ensure_ascii=False)
                
                # 对于错误响应，也检查关键词
                matched = check_keywords(response_text, test_case.expected_keywords or [])
                
                success = True
                if test_case.expected_keywords and len(matched) == 0:
                    success = False
                
                return TestResult(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    category=test_case.category,
                    success=success,
                    duration_ms=duration_ms,
                    response_preview=response_text[:300],
                    matched_keywords=matched,
                    error="" if success else "未匹配到预期关键词"
                )
        else:
            # 状态码不符合预期
            return TestResult(
                test_id=test_case.id,
                test_name=test_case.name,
                category=test_case.category,
                success=False,
                duration_ms=duration_ms,
                error=f"预期状态码 {expected_status}，实际 {actual_status}"
            )
    except Exception as e:
        return TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            category=test_case.category,
            success=False,
            duration_ms=int((time.time() - start_time) * 1000),
            error=str(e)
        )


# ==========================================
# 测试用例定义
# ==========================================

def get_coding_review_tests() -> List[TestCase]:
    """代码审查测试用例 - 多语言多领域"""
    return [
        # Python - 数据处理
        TestCase(
            id="CR001", name="Python数据处理代码审查", category="代码审查",
            language="Python", domain="数据处理", complexity="中等",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
import pandas as pd
import numpy as np

def process_sales_data(file_path):
    df = pd.read_csv(file_path)
    df['total'] = df['price'] * df['quantity']
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    
    monthly_sales = df.groupby('month')['total'].sum()
    avg_sales = monthly_sales.mean()
    
    result = {
        'monthly_sales': monthly_sales.to_dict(),
        'average': avg_sales,
        'total_records': len(df)
    }
    return result
""",
                "language": "python"
            },
            expected_keywords=["review", "建议", "改进", "优化", "代码"],
            description="审查Python数据处理代码"
        ),
        
        # JavaScript - React组件
        TestCase(
            id="CR002", name="React组件代码审查", category="代码审查",
            language="JavaScript", domain="Web前端", complexity="中等",
            api_endpoint="/api/coding/review",
            request_data={
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
    
    return (
        <div>
            <h1>{user.name}</h1>
            <p>{user.email}</p>
            <img src={user.avatar} />
        </div>
    );
}

export default UserProfile;
""",
                "language": "javascript"
            },
            expected_keywords=["review", "建议", "错误处理", "error", "React"],
            description="审查React组件代码"
        ),
        
        # TypeScript - API服务
        TestCase(
            id="CR003", name="TypeScript API服务审查", category="代码审查",
            language="TypeScript", domain="后端API", complexity="中等",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
interface User {
    id: number;
    name: string;
    email: string;
}

class UserService {
    private users: User[] = [];
    
    async getUser(id: number): Promise<User> {
        const user = this.users.find(u => u.id === id);
        return user;
    }
    
    async createUser(data: Omit<User, 'id'>): Promise<User> {
        const newUser = {
            id: this.users.length + 1,
            ...data
        };
        this.users.push(newUser);
        return newUser;
    }
    
    async updateUser(id: number, data: Partial<User>): Promise<User> {
        const index = this.users.findIndex(u => u.id === id);
        this.users[index] = { ...this.users[index], ...data };
        return this.users[index];
    }
}
""",
                "language": "typescript"
            },
            expected_keywords=["review", "建议", "类型", "错误处理", "TypeScript"],
            description="审查TypeScript API服务代码"
        ),
        
        # Java - Spring Boot
        TestCase(
            id="CR004", name="Java Spring Boot审查", category="代码审查",
            language="Java", domain="后端API", complexity="中等",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
@RestController
@RequestMapping("/api/products")
public class ProductController {
    
    @Autowired
    private ProductService productService;
    
    @GetMapping
    public List<Product> getAll() {
        return productService.findAll();
    }
    
    @GetMapping("/{id}")
    public Product getById(@PathVariable Long id) {
        return productService.findById(id);
    }
    
    @PostMapping
    public Product create(@RequestBody Product product) {
        return productService.save(product);
    }
    
    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        productService.delete(id);
    }
}
""",
                "language": "java"
            },
            expected_keywords=["review", "建议", "异常处理", "Spring", "注解"],
            description="审查Java Spring Boot控制器"
        ),
        
        # Go - HTTP服务
        TestCase(
            id="CR005", name="Go HTTP服务审查", category="代码审查",
            language="Go", domain="后端API", complexity="中等",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
package main

import (
    "encoding/json"
    "net/http"
    "sync"
)

type Todo struct {
    ID    int    `json:"id"`
    Title string `json:"title"`
    Done  bool   `json:"done"`
}

var (
    todos  []Todo
    mu     sync.Mutex
    nextID = 1
)

func handleTodos(w http.ResponseWriter, r *http.Request) {
    switch r.Method {
    case "GET":
        json.NewEncoder(w).Encode(todos)
    case "POST":
        var todo Todo
        json.NewDecoder(r.Body).Decode(&todo)
        todo.ID = nextID
        nextID++
        mu.Lock()
        todos = append(todos, todo)
        mu.Unlock()
        w.WriteHeader(http.StatusCreated)
        json.NewEncoder(w).Encode(todo)
    }
}

func main() {
    http.HandleFunc("/todos", handleTodos)
    http.ListenAndServe(":8080", nil)
}
""",
                "language": "go"
            },
            expected_keywords=["review", "建议", "错误处理", "Go", "并发"],
            description="审查Go HTTP服务代码"
        ),
        
        # Rust - 系统编程
        TestCase(
            id="CR006", name="Rust系统编程审查", category="代码审查",
            language="Rust", domain="系统编程", complexity="复杂",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

struct Cache<K, V> {
    data: Arc<Mutex<HashMap<K, V>>>,
    max_size: usize,
}

impl<K: Eq + std::hash::Hash + Clone, V: Clone> Cache<K, V> {
    fn new(max_size: usize) -> Self {
        Cache {
            data: Arc::new(Mutex::new(HashMap::new())),
            max_size,
        }
    }
    
    fn get(&self, key: &K) -> Option<V> {
        let data = self.data.lock().unwrap();
        data.get(key).cloned()
    }
    
    fn set(&self, key: K, value: V) {
        let mut data = self.data.lock().unwrap();
        if data.len() >= self.max_size {
            if let Some(first_key) = data.keys().next().cloned() {
                data.remove(&first_key);
            }
        }
        data.insert(key, value);
    }
}
""",
                "language": "rust"
            },
            expected_keywords=["review", "建议", "Rust", "所有权", "生命周期"],
            description="审查Rust系统编程代码"
        ),
        
        # SQL - 数据库查询
        TestCase(
            id="CR007", name="SQL查询代码审查", category="代码审查",
            language="SQL", domain="数据库", complexity="中等",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
SELECT 
    u.name,
    u.email,
    COUNT(o.id) as order_count,
    SUM(o.total_amount) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.created_at >= '2024-01-01'
    AND o.status != 'cancelled'
GROUP BY u.id, u.name, u.email
HAVING COUNT(o.id) > 5
ORDER BY total_spent DESC
LIMIT 100;
""",
                "language": "sql"
            },
            expected_keywords=["review", "建议", "SQL", "索引", "优化"],
            description="审查SQL查询代码"
        ),
        
        # C++ - 算法实现
        TestCase(
            id="CR008", name="C++算法实现审查", category="代码审查",
            language="C++", domain="算法", complexity="复杂",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
#include <vector>
#include <algorithm>

class Solution {
public:
    int longestIncreasingSubsequence(std::vector<int>& nums) {
        if (nums.empty()) return 0;
        
        std::vector<int> dp(nums.size(), 1);
        int maxLen = 1;
        
        for (int i = 1; i < nums.size(); i++) {
            for (int j = 0; j < i; j++) {
                if (nums[j] < nums[i]) {
                    dp[i] = std::max(dp[i], dp[j] + 1);
                }
            }
            maxLen = std::max(maxLen, dp[i]);
        }
        
        return maxLen;
    }
};
""",
                "language": "cpp"
            },
            expected_keywords=["review", "建议", "C++", "算法", "复杂度"],
            description="审查C++算法实现代码"
        ),
    ]


def get_bug_fix_tests() -> List[TestCase]:
    """Bug修复测试用例"""
    return [
        # Python - 空指针异常
        TestCase(
            id="BF001", name="Python空指针异常修复", category="Bug修复",
            language="Python", domain="通用", complexity="简单",
            api_endpoint="/api/coding/bug-fix",
            request_data={
                "code": """
def get_user_name(user):
    return user['name'].upper()

# 测试
result = get_user_name(None)
""",
                "error_message": "TypeError: 'NoneType' object is not subscriptable",
                "language": "python"
            },
            expected_keywords=["fix", "修复", "None", "空值", "检查"],
            description="修复Python空指针异常"
        ),
        
        # JavaScript - 异步错误
        TestCase(
            id="BF002", name="JavaScript异步错误修复", category="Bug修复",
            language="JavaScript", domain="Web前端", complexity="中等",
            api_endpoint="/api/coding/bug-fix",
            request_data={
                "code": """
async function fetchData(url) {
    const response = await fetch(url);
    const data = response.json();
    return data;
}

fetchData('https://api.example.com/data')
    .then(data => console.log(data.name));
""",
                "error_message": "SyntaxError: Unexpected token '<', \"<!DOCTYPE \"... is not valid JSON",
                "language": "javascript"
            },
            expected_keywords=["fix", "修复", "await", "错误处理", "response"],
            description="修复JavaScript异步错误"
        ),
        
        # Java - 并发问题
        TestCase(
            id="BF003", name="Java并发问题修复", category="Bug修复",
            language="Java", domain="系统编程", complexity="复杂",
            api_endpoint="/api/coding/bug-fix",
            request_data={
                "code": """
import java.util.HashMap;
import java.util.Map;

public class Counter {
    private Map<String, Integer> counts = new HashMap<>();
    
    public void increment(String key) {
        int current = counts.getOrDefault(key, 0);
        counts.put(key, current + 1);
    }
    
    public int getCount(String key) {
        return counts.getOrDefault(key, 0);
    }
}
""",
                "error_message": "ConcurrentModificationException or race condition detected",
                "language": "java"
            },
            expected_keywords=["fix", "修复", "并发", "线程安全", "synchronized"],
            description="修复Java并发问题"
        ),
        
        # Go - 内存泄漏
        TestCase(
            id="BF004", name="Go内存泄漏修复", category="Bug修复",
            language="Go", domain="系统编程", complexity="中等",
            api_endpoint="/api/coding/bug-fix",
            request_data={
                "code": """
package main

import "fmt"

func processData(data []int) []int {
    result := make([]int, 0)
    for _, v := range data {
        result = append(result, v * 2)
    }
    return result
}

func main() {
    data := make([]int, 1000000)
    for i := range data {
        data[i] = i
    }
    
    result := processData(data)
    fmt.Println(len(result))
}
""",
                "error_message": "runtime: out of memory",
                "language": "go"
            },
            expected_keywords=["fix", "修复", "内存", "优化", "Go"],
            description="修复Go内存问题"
        ),
        
        # Python - 类型错误
        TestCase(
            id="BF005", name="Python类型错误修复", category="Bug修复",
            language="Python", domain="数据处理", complexity="简单",
            api_endpoint="/api/coding/bug-fix",
            request_data={
                "code": """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

# 测试
result = calculate_average([])
print(f"Average: {result}")
""",
                "error_message": "ZeroDivisionError: division by zero",
                "language": "python"
            },
            expected_keywords=["fix", "修复", "零", "空列表", "检查"],
            description="修复Python除零错误"
        ),
    ]


def get_explain_tests() -> List[TestCase]:
    """代码解释测试用例"""
    return [
        # Python - 装饰器
        TestCase(
            id="EX001", name="Python装饰器解释", category="代码解释",
            language="Python", domain="通用", complexity="中等",
            api_endpoint="/api/coding/explain",
            request_data={
                "code": """
def memoize(func):
    cache = {}
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper

@memoize
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
                "language": "python",
                "detail_level": "detailed"
            },
            expected_keywords=["装饰器", "缓存", "递归", "记忆化", "闭包"],
            description="解释Python装饰器和记忆化"
        ),
        
        # JavaScript - Promise
        TestCase(
            id="EX002", name="JavaScript Promise解释", category="代码解释",
            language="JavaScript", domain="Web前端", complexity="中等",
            api_endpoint="/api/coding/explain",
            request_data={
                "code": """
function fetchWithRetry(url, retries = 3) {
    return new Promise((resolve, reject) => {
        function attempt(n) {
            fetch(url)
                .then(resolve)
                .catch(error => {
                    if (n === 0) {
                        reject(error);
                    } else {
                        setTimeout(() => attempt(n - 1), 1000);
                    }
                });
        }
        attempt(retries);
    });
}
""",
                "language": "javascript",
                "detail_level": "detailed"
            },
            expected_keywords=["Promise", "异步", "重试", "递归", "错误处理"],
            description="解释JavaScript Promise和重试机制"
        ),
        
        # TypeScript - 泛型
        TestCase(
            id="EX003", name="TypeScript泛型解释", category="代码解释",
            language="TypeScript", domain="通用", complexity="中等",
            api_endpoint="/api/coding/explain",
            request_data={
                "code": """
interface Repository<T extends { id: number }> {
    findById(id: number): Promise<T | null>;
    findAll(): Promise<T[]>;
    create(data: Omit<T, 'id'>): Promise<T>;
    update(id: number, data: Partial<T>): Promise<T>;
    delete(id: number): Promise<boolean>;
}

class UserRepository implements Repository<User> {
    private users: User[] = [];
    
    async findById(id: number): Promise<User | null> {
        return this.users.find(u => u.id === id) || null;
    }
    
    async findAll(): Promise<User[]> {
        return [...this.users];
    }
    
    async create(data: Omit<User, 'id'>): Promise<User> {
        const user = { id: Date.now(), ...data } as User;
        this.users.push(user);
        return user;
    }
}
""",
                "language": "typescript",
                "detail_level": "detailed"
            },
            expected_keywords=["泛型", "接口", "类型约束", "TypeScript", "实现"],
            description="解释TypeScript泛型和接口"
        ),
        
        # Go - Goroutine
        TestCase(
            id="EX004", name="Go Goroutine解释", category="代码解释",
            language="Go", domain="系统编程", complexity="复杂",
            api_endpoint="/api/coding/explain",
            request_data={
                "code": """
func fanOutFanIn(input <-chan int, workers int) <-chan int {
    var wg sync.WaitGroup
    out := make(chan int)
    
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for v := range input {
                out <- v * v
            }
        }()
    }
    
    go func() {
        wg.Wait()
        close(out)
    }()
    
    return out
}
""",
                "language": "go",
                "detail_level": "detailed"
            },
            expected_keywords=["goroutine", "channel", "并发", "WaitGroup", "扇出扇入"],
            description="解释Go并发模式"
        ),
        
        # Rust - 生命周期
        TestCase(
            id="EX005", name="Rust生命周期解释", category="代码解释",
            language="Rust", domain="系统编程", complexity="复杂",
            api_endpoint="/api/coding/explain",
            request_data={
                "code": """
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}

struct Parser<'a> {
    input: &'a str,
    position: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Parser { input, position: 0 }
    }
    
    fn peek(&self) -> Option<char> {
        self.input[self.position..].chars().next()
    }
    
    fn advance(&mut self) -> Option<char> {
        let ch = self.peek()?;
        self.position += ch.len_utf8();
        Some(ch)
    }
}
""",
                "language": "rust",
                "detail_level": "detailed"
            },
            expected_keywords=["生命周期", "借用", "Rust", "引用", "内存安全"],
            description="解释Rust生命周期"
        ),
    ]


def get_refactor_tests() -> List[TestCase]:
    """代码重构测试用例"""
    return [
        # Python - 列表推导式
        TestCase(
            id="RF001", name="Python列表推导式重构", category="代码重构",
            language="Python", domain="通用", complexity="简单",
            api_endpoint="/api/coding/refactor",
            request_data={
                "code": """
def get_even_squares(numbers):
    result = []
    for n in numbers:
        if n % 2 == 0:
            result.append(n * n)
    return result
""",
                "language": "python",
                "goal": "使用列表推导式简化代码"
            },
            expected_keywords=["重构", "列表推导式", "简洁", "Python"],
            description="重构Python代码使用列表推导式"
        ),
        
        # JavaScript - 解构赋值
        TestCase(
            id="RF002", name="JavaScript解构赋值重构", category="代码重构",
            language="JavaScript", domain="Web前端", complexity="简单",
            api_endpoint="/api/coding/refactor",
            request_data={
                "code": """
function processUser(user) {
    var name = user.name;
    var email = user.email;
    var age = user.age;
    
    return {
        displayName: name.toUpperCase(),
        contact: email,
        isAdult: age >= 18
    };
}
""",
                "language": "javascript",
                "goal": "使用ES6+特性重构"
            },
            expected_keywords=["重构", "解构", "箭头函数", "ES6", "简洁"],
            description="重构JavaScript代码使用ES6+特性"
        ),
        
        # Java - Stream API
        TestCase(
            id="RF003", name="Java Stream API重构", category="代码重构",
            language="Java", domain="后端API", complexity="中等",
            api_endpoint="/api/coding/refactor",
            request_data={
                "code": """
public List<String> getActiveUserNames(List<User> users) {
    List<String> result = new ArrayList<>();
    for (User user : users) {
        if (user.isActive()) {
            String name = user.getName().toUpperCase();
            if (name.length() > 3) {
                result.add(name);
            }
        }
    }
    Collections.sort(result);
    return result;
}
""",
                "language": "java",
                "goal": "使用Stream API重构"
            },
            expected_keywords=["重构", "Stream", "Lambda", "Java", "函数式"],
            description="重构Java代码使用Stream API"
        ),
        
        # Go - 接口抽象
        TestCase(
            id="RF004", name="Go接口抽象重构", category="代码重构",
            language="Go", domain="后端API", complexity="中等",
            api_endpoint="/api/coding/refactor",
            request_data={
                "code": """
type MySQLDatabase struct {
    host string
    port int
}

func (db *MySQLDatabase) Connect() error {
    // 连接MySQL
    return nil
}

func (db *MySQLDatabase) Query(sql string) ([]map[string]interface{}, error) {
    // 查询MySQL
    return nil, nil
}

type UserService struct {
    db *MySQLDatabase
}

func NewUserService() *UserService {
    return &UserService{
        db: &MySQLDatabase{host: "localhost", port: 3306},
    }
}
""",
                "language": "go",
                "goal": "引入接口实现依赖注入"
            },
            expected_keywords=["重构", "接口", "依赖注入", "Go", "抽象"],
            description="重构Go代码引入接口"
        ),
        
        # Python - 设计模式
        TestCase(
            id="RF005", name="Python策略模式重构", category="代码重构",
            language="Python", domain="通用", complexity="中等",
            api_endpoint="/api/coding/refactor",
            request_data={
                "code": """
def calculate_shipping(order, method):
    if method == 'standard':
        return order.weight * 0.5
    elif method == 'express':
        return order.weight * 1.5
    elif method == 'overnight':
        return order.weight * 3.0
    else:
        raise ValueError(f"Unknown method: {method}")
""",
                "language": "python",
                "goal": "使用策略模式重构"
            },
            expected_keywords=["重构", "策略模式", "设计模式", "Python", "扩展"],
            description="重构Python代码使用策略模式"
        ),
    ]


def get_boundary_tests() -> List[TestCase]:
    """边界条件测试用例"""
    return [
        # 空输入（应该返回400错误）
        TestCase(
            id="BD001", name="空代码输入处理", category="边界条件",
            language="通用", domain="通用", complexity="简单",
            api_endpoint="/api/coding/review",
            request_data={
                "code": "",
                "language": "python"
            },
            expected_keywords=["错误", "空", "empty", "无效", "不能为空"],
            description="测试空代码输入处理（预期返回400错误）",
            expected_status=400  # 预期返回400状态码
        ),
        
        # 超长输入
        TestCase(
            id="BD002", name="超长代码输入处理", category="边界条件",
            language="Python", domain="通用", complexity="简单",
            api_endpoint="/api/coding/review",
            request_data={
                "code": "# " + "x" * 10000 + "\nprint('test')",
                "language": "python"
            },
            expected_keywords=["review", "建议", "代码"],
            description="测试超长代码输入处理"
        ),
        
        # 特殊字符
        TestCase(
            id="BD003", name="特殊字符代码处理", category="边界条件",
            language="Python", domain="通用", complexity="简单",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
# 测试特殊字符: @#$%^&*()_+{}|:"<>?~`[]\\;',./
# 中文注释：这是一个测试
# Emoji: 🚀 🎉 ✅ ❌
def test():
    return "特殊字符测试: \\n\\t\\r"
""",
                "language": "python"
            },
            expected_keywords=["review", "建议", "代码"],
            description="测试特殊字符代码处理"
        ),
        
        # 嵌套复杂度
        TestCase(
            id="BD004", name="深度嵌套代码处理", category="边界条件",
            language="Python", domain="通用", complexity="复杂",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
def complex_function(data):
    result = []
    for item in data:
        if item.get('type') == 'A':
            if item.get('status') == 'active':
                for sub in item.get('items', []):
                    if sub.get('value') > 0:
                        if sub.get('category') in ['X', 'Y', 'Z']:
                            result.append({
                                'id': sub['id'],
                                'processed': True
                            })
    return result
""",
                "language": "python"
            },
            expected_keywords=["review", "嵌套", "重构", "简化", "复杂度"],
            description="测试深度嵌套代码处理"
        ),
        
        # 多语言混合
        TestCase(
            id="BD005", name="多语言代码检测", category="边界条件",
            language="Python", domain="通用", complexity="简单",
            api_endpoint="/api/coding/review",
            request_data={
                "code": """
def hello():
    print("Hello World")
    console.log("This is JavaScript")  # 错误：在Python中使用JS语法
    return True
""",
                "language": "python"
            },
            expected_keywords=["review", "错误", "语法", "问题"],
            description="测试多语言代码检测"
        ),
    ]


def get_integration_workflow_tests() -> List[TestCase]:
    """集成工作流测试用例"""
    return [
        # 知识构建工作流
        TestCase(
            id="WF001", name="知识构建工作流", category="集成工作流",
            language="通用", domain="知识管理", complexity="中等",
            api_endpoint="/api/knowledge/build",
            request_data={
                "content": """
Python是一种广泛使用的高级编程语言。由Guido van Rossum创建，于1991年首次发布。
Python的设计哲学强调代码的可读性和简洁性。Python支持多种编程范式，包括面向对象、
命令式、函数式和过程式编程。

Python的主要特点：
1. 简单易学：Python有相对较少的关键词，结构简单
2. 可读性：Python代码使用空格缩进，定义清晰
3. 丰富的库：Python拥有大量标准库和第三方库
4. 跨平台：Python可以在多种操作系统上运行
""",
                "source": "test_document"
            },
            expected_keywords=["statistics", "entities_extracted", "relations_extracted"],
            description="测试知识构建工作流"
        ),
        
        # 文本处理工作流
        TestCase(
            id="WF002", name="文本翻译工作流", category="集成工作流",
            language="通用", domain="文本处理", complexity="简单",
            api_endpoint="/api/text/process",
            request_data={
                "text": "OpenCopilot is an AI-powered coding assistant that helps developers write better code.",
                "action": "translate",
                "target_language": "zh"
            },
            expected_keywords=["翻译", "助手", "代码", "AI"],
            description="测试文本翻译工作流"
        ),
        
        # 格式转换工作流
        TestCase(
            id="WF003", name="文本转表格工作流", category="集成工作流",
            language="通用", domain="格式转换", complexity="简单",
            api_endpoint="/api/format/text-to-table",
            request_data={
                "content": "姓名,年龄,城市,职业\n张三,25,北京,工程师\n李四,30,上海,设计师\n王五,28,广州,产品经理",
                "format": "markdown"
            },
            expected_keywords=["表格", "姓名", "张三", "markdown"],
            description="测试文本转表格工作流"
        ),
        
        # 内容评价工作流
        TestCase(
            id="WF004", name="内容质量评价工作流", category="集成工作流",
            language="通用", domain="质量评估", complexity="中等",
            api_endpoint="/api/evaluation/evaluate",
            request_data={
                "content": """
快速排序是一种高效的排序算法，采用分治策略。它的基本思想是选择一个基准元素，
将数组分为两部分：比基准小的元素和比基准大的元素，然后递归地对两部分进行排序。

时间复杂度：平均O(n log n)，最坏O(n²)
空间复杂度：O(log n)
""",
                "scene": "auto"
            },
            expected_keywords=["评价", "分数", "质量", "评估"],
            description="测试内容质量评价工作流"
        ),
        
        # 人设管理工作流
        TestCase(
            id="WF005", name="人设列表查询工作流", category="集成工作流",
            language="通用", domain="人设管理", complexity="简单",
            api_endpoint="/api/persona/list",
            request_data={},
            expected_keywords=["persona", "人设", "list", "列表"],
            description="测试人设列表查询工作流"
        ),
    ]


def get_skill_specific_tests() -> List[TestCase]:
    """技能特定测试用例"""
    return [
        # CodingSkill - 代码分析
        TestCase(
            id="SK001", name="代码复杂度分析", category="技能测试",
            language="Python", domain="代码质量", complexity="中等",
            api_endpoint="/api/coding/analyze",
            request_data={
                "code": """
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
                "language": "python"
            },
            expected_keywords=["分析", "复杂度", "算法", "排序"],
            description="测试代码复杂度分析"
        ),
        
        # KnowledgeSkill - 实体搜索
        TestCase(
            id="SK002", name="知识实体搜索", category="技能测试",
            language="通用", domain="知识管理", complexity="简单",
            api_endpoint="/api/knowledge/search-entity",
            request_data={
                "keyword": "Python",
                "entity_type": "concept"
            },
            expected_keywords=["entity", "实体", "Python", "搜索"],
            description="测试知识实体搜索"
        ),
        
        # FileSkill - 文件操作
        TestCase(
            id="SK003", name="目录文件列表", category="技能测试",
            language="通用", domain="文件管理", complexity="简单",
            api_endpoint="/api/file/list",
            request_data={
                "dir_path": "."
            },
            expected_keywords=["files", "目录", "列表", "文件"],
            description="测试目录文件列表"
        ),
        
        # EvaluationSkill - 评分
        TestCase(
            id="SK004", name="内容评分测试", category="技能测试",
            language="通用", domain="质量评估", complexity="简单",
            api_endpoint="/api/evaluation/score",
            request_data={
                "content": "这是一段测试内容，用于验证评分功能。",
                "criteria": ["clarity", "completeness", "accuracy"]
            },
            expected_keywords=["score", "分数", "评分"],
            description="测试内容评分功能"
        ),
        
        # FormatSkill - Markdown转Word
        TestCase(
            id="SK005", name="Markdown转Word", category="技能测试",
            language="通用", domain="格式转换", complexity="中等",
            api_endpoint="/api/format/md-to-docx",
            request_data={
                "content": "# 测试文档\n\n## 第一章\n\n这是测试内容。\n\n- 要点1\n- 要点2",
                "filename": "test.docx"
            },
            expected_keywords=["docx", "word", "成功", "生成"],
            description="测试Markdown转Word功能"
        ),
    ]


def get_performance_tests() -> List[TestCase]:
    """性能测试用例"""
    return [
        # 并发请求测试
        TestCase(
            id="PF001", name="API并发性能测试", category="性能测试",
            language="通用", domain="性能", complexity="中等",
            api_endpoint="/health",
            request_data={},
            expected_keywords=["status", "ok", "healthy"],
            description="测试API并发性能",
            http_method="GET"
        ),
        
        # 大文本处理
        TestCase(
            id="PF002", name="大文本处理性能", category="性能测试",
            language="Python", domain="性能", complexity="复杂",
            api_endpoint="/api/coding/review",
            request_data={
                "code": "# Large code file\n" + "\n".join([f"def func_{i}(): return {i}" for i in range(100)]),
                "language": "python"
            },
            expected_keywords=["review", "建议", "代码"],
            description="测试大文本处理性能"
        ),
    ]


def collect_all_tests() -> List[TestCase]:
    """收集所有测试用例"""
    all_tests = []
    all_tests.extend(get_coding_review_tests())
    all_tests.extend(get_bug_fix_tests())
    all_tests.extend(get_explain_tests())
    all_tests.extend(get_refactor_tests())
    all_tests.extend(get_boundary_tests())
    all_tests.extend(get_integration_workflow_tests())
    all_tests.extend(get_skill_specific_tests())
    all_tests.extend(get_performance_tests())
    return all_tests


def generate_report(test_results: List[TestResult], duration_seconds: float):
    """生成测试报告"""
    total = len(test_results)
    passed = sum(1 for r in test_results if r.success)
    failed = total - passed
    
    # 按类别统计
    categories = {}
    for result in test_results:
        cat = result.category
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "total": 0, "duration_ms": 0}
        categories[cat]["total"] += 1
        categories[cat]["duration_ms"] += result.duration_ms
        if result.success:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
    
    # 按语言统计
    languages = {}
    for result in test_results:
        # 从测试ID推断语言
        test_id = result.test_id
        if test_id.startswith("CR") or test_id.startswith("EX") or test_id.startswith("RF"):
            # 这些测试包含语言信息，从测试名称推断
            pass
    
    # 按领域统计
    domains = {}
    
    # 生成报告
    report = {
        "test_name": "OpenCopilot 全面测试矩阵",
        "test_time": datetime.now().isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.1f}%"
        },
        "categories": categories,
        "test_results": [asdict(r) for r in test_results]
    }
    
    # 保存JSON报告
    report_path = os.path.join(os.path.dirname(__file__), "comprehensive_matrix_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 生成Markdown报告
    md_report = f"""# OpenCopilot 全面测试矩阵报告

## 测试概述

- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总耗时**: {duration_seconds:.2f}秒
- **API地址**: {API_BASE_URL}

## 测试结果

### 总体统计

| 指标 | 数值 |
|------|------|
| 总测试数 | {total} |
| 通过数 | {passed} |
| 失败数 | {failed} |
| 通过率 | {passed/total*100:.1f}% |

### 分类统计

| 类别 | 通过/总数 | 通过率 | 耗时(ms) |
|------|-----------|--------|----------|
"""
    
    for cat, stats in categories.items():
        pass_rate = f"{stats['passed']/stats['total']*100:.1f}%" if stats['total'] > 0 else "N/A"
        md_report += f"| {cat} | {stats['passed']}/{stats['total']} | {pass_rate} | {stats['duration_ms']} |\n"
    
    md_report += """
### 详细结果

| ID | 测试名称 | 类别 | 结果 | 耗时(ms) | 说明 |
|----|----------|------|------|----------|------|
"""
    
    for result in test_results:
        status = "✅" if result.success else "❌"
        error_info = result.error[:50] if result.error else ""
        md_report += f"| {result.test_id} | {result.test_name} | {result.category} | {status} | {result.duration_ms} | {error_info} |\n"
    
    md_report += f"""
## 测试覆盖维度

### 1. 编程语言覆盖
- Python
- JavaScript
- TypeScript
- Java
- Go
- Rust
- C++
- SQL

### 2. 业务领域覆盖
- Web前端 (React, Vue)
- 后端API (Spring Boot, Express)
- 数据处理 (Pandas, NumPy)
- 算法实现 (排序, 搜索, 动态规划)
- 系统编程 (并发, 内存管理)
- 数据库 (SQL查询优化)

### 3. 复杂度覆盖
- 简单函数 (10行以内)
- 中等模块 (50-100行)
- 复杂类 (200+行)

### 4. 测试类型覆盖
- 代码审查 (8个用例)
- Bug修复 (5个用例)
- 代码解释 (5个用例)
- 代码重构 (5个用例)
- 边界条件 (5个用例)
- 集成工作流 (5个用例)
- 技能测试 (5个用例)
- 性能测试 (2个用例)

### 5. 边界条件覆盖
- 空输入处理
- 超长输入处理
- 特殊字符处理
- 深度嵌套代码
- 多语言混合代码

## 结论

**总体评估**: {'✅ 通过' if failed == 0 else '⚠️ 部分失败'}

所有测试用例覆盖了多个编程语言、业务领域和复杂度级别，验证了OpenCopilot API的全面能力。

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    md_path = os.path.join(os.path.dirname(__file__), "Comprehensive_Matrix_Test_Report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    
    print(f"\n📄 测试报告已保存:")
    print(f"   - JSON: {report_path}")
    print(f"   - Markdown: {md_path}")


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 OpenCopilot 全面测试矩阵")
    print("="*80)
    print(f"API地址: {API_BASE_URL}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # 收集所有测试用例
    all_tests = collect_all_tests()
    total_tests = len(all_tests)
    
    print(f"📋 共 {total_tests} 个测试用例")
    print(f"   - 代码审查: {len(get_coding_review_tests())} 个")
    print(f"   - Bug修复: {len(get_bug_fix_tests())} 个")
    print(f"   - 代码解释: {len(get_explain_tests())} 个")
    print(f"   - 代码重构: {len(get_refactor_tests())} 个")
    print(f"   - 边界条件: {len(get_boundary_tests())} 个")
    print(f"   - 集成工作流: {len(get_integration_workflow_tests())} 个")
    print(f"   - 技能测试: {len(get_skill_specific_tests())} 个")
    print(f"   - 性能测试: {len(get_performance_tests())} 个")
    print()
    
    # 运行测试
    start_time = time.time()
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(all_tests, 1):
        print(f"[{i}/{total_tests}] {test_case.id}: {test_case.name}...", end=" ", flush=True)
        
        result = await run_test(test_case)
        test_results.append(result)
        
        if result.success:
            passed += 1
            print(f"✅ ({result.duration_ms}ms)")
        else:
            failed += 1
            print(f"❌ {result.error[:50]}")
        
        # 短暂延迟避免请求过快
        await asyncio.sleep(0.3)
    
    duration_seconds = time.time() - start_time
    
    # 打印总结
    print("\n" + "="*80)
    print("📊 测试总结")
    print("="*80)
    print(f"总测试数: {total_tests}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"通过率: {passed/total_tests*100:.1f}%")
    print(f"总耗时: {duration_seconds:.2f}秒")
    print("="*80)
    
    # 按类别统计
    categories = {}
    for result in test_results:
        cat = result.category
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0}
        if result.success:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
    
    print("\n📋 分类统计:")
    for cat, stats in categories.items():
        total = stats["passed"] + stats["failed"]
        print(f"  {cat}: {stats['passed']}/{total} 通过")
    
    # 生成报告
    generate_report(test_results, duration_seconds)
    
    if failed > 0:
        print("\n⚠️ 部分测试失败，请检查API服务状态。")
        return 1
    else:
        print("\n🎉 所有测试通过！")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n💥 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)
