---
title: 【示例】Python 装饰器详解
summary: 通过实例理解 Python 装饰器的工作原理与使用场景
category: 编程
tags:
  - Python
  - 进阶
  - 编程技巧
date: 2026-08-28
published: true
---

# Python 装饰器入门到精通 🎯

装饰器（Decorator）是 Python 中非常优雅的特性，让你可以在**不修改原函数代码**的前提下，扩展函数的行为。

## 1. 什么是装饰器？

简单来说，装饰器就是一个 **接受函数作为参数，并返回一个新函数** 的高阶函数。

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("调用前做点什么…")
        result = func(*args, **kwargs)
        print("调用后做点什么…")
        return result
    return wrapper
```

## 2. 语法糖 @

Python 提供了 `@` 符号，让装饰器的写法更优雅：

```python
@my_decorator
def hello(name):
    print(f"Hello, {name}!")

hello("World")
```

等价于：

```python
hello = my_decorator(hello)
hello("World")
```

## 3. 常用场景

| 场景 | 说明 |
| --- | --- |
| 🕐 性能计时 | 统计函数运行时间 |
| 🔐 权限校验 | 在执行前检查用户权限 |
| 📝 日志记录 | 自动记录函数调用情况 |
| 🗄️ 结果缓存 | 相同参数直接返回缓存 |
| 🔄 重试机制 | 失败后自动重试若干次 |

## 4. 带参数的装饰器

> 想要更灵活？装饰器本身也可以接受参数！

```python
def repeat(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def greet():
    print("Hello!")

greet()  # 输出 3 次 Hello!
```

### 小结

- 装饰器本质：`函数 -> 包装函数 -> 新函数`
- 使用 `functools.wraps` 可以保留原函数的元信息
- 多个装饰器叠加时，执行顺序是 **自上而下的包装，自下而上的执行**

希望这篇笔记对你有帮助！🐍
