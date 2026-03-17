---
name: py312
description: Python 3.12+ 严格代码质量规范。编写/重构 Python 代码、进行代码审查时使用。强制要求：函数≤30行、中文注释、Pyright Strict Mode 零错误容忍。强调简单就是美，不确定时主动沟通。
---

# Python 3.12+ 最佳实践规范

## 核心原则

**简单就是美**。代码是写给人看的，只是顺便让机器执行。

- 优先选择简单、直接的解决方案
- 避免过度设计和过早优化
- 保持代码扁平，减少嵌套层级
- 不确定时，提问沟通后再实现

## 代码可读性要求

### 函数长度控制

**严格限制函数体长度**：
- 普通函数不超过 30 行代码（不包括注释和空行）
- 回调函数/简单包装器不超过 10 行
- 如果超过限制，必须拆分为更小的函数

**拆分策略**：
```python
# 不好的做法：一个函数做太多事情
def process_user_data(data: dict) -> dict:
    # 50 行的复杂逻辑...
    pass

# 正确的做法：拆分为专注单一职责的函数
def validate_user_input(data: dict) -> bool:
    """验证用户输入数据的有效性。"""
    ...

def transform_user_data(data: dict) -> dict:
    """转换用户数据格式。"""
    ...

def save_user_data(data: dict) -> None:
    """保存用户数据到数据库。"""
    ...
```

### 中文注释规范

**必须使用标准中文注释**：
- 文档字符串（docstring）使用中文编写
- 复杂的业务逻辑添加中文注释
- 注释解释"为什么"，而非"做什么"

**注释格式**：
```python
def calculate_discount(price: float, level: str) -> float:
    """计算用户折扣价格。

    根据用户等级计算对应的折扣率，
    高等级用户享受更多优惠。

    Args:
        price: 原始价格
        level: 用户等级 (普通/银卡/金卡)

    Returns:
        折扣后的价格

    Raises:
        ValueError: 价格无效或等级不存在
    """
    # 参数校验：确保价格为正数
    if price <= 0:
        raise ValueError("价格必须为正数")

    # 使用字典映射替代多重 if-else，提高可维护性
    discount_map = {
        "普通": 0.95,
        "银卡": 0.90,
        "金卡": 0.85
    }

    return price * discount_map.get(level, 0.95)
```

**注释原则**：
- 每个模块文件头部必须有模块说明注释
- 类和函数必须有文档字符串
- 复杂的算法需要步骤说明
- 临时解决方案必须标注 TODO 并说明原因

## Python 3.12+ 类型注解（严格模式）

**基本原则：零妥协类型安全**

### 现代类型语法（强制使用）

```python
# ✅ 正确：使用内置泛型（完整参数化）
from collections.abc import Mapping, Sequence, Iterable, Callable

def process(items: list[str], config: dict[str, int]) -> bool:
    ...

# ✅ 正确：使用 | 表示 Union（禁止使用 Union[X, Y]）
def find_user(user_id: int) -> User | None:
    ...

# ✅ 正确：使用 * 表示可变参数的类型（Python 3.11+）
def log_message(fmt: str, *args: *tuple[str, ...]) -> None:
    ...

# ✅ 正确：使用 TypedDict 精确描述字典结构
from typing import TypedDict, Required, NotRequired

class APIGatewayEvent(TypedDict):
    path: Required[str]
    method: Required[str]
    headers: dict[str, str]
    query_params: NotRequired[dict[str, list[str]]]
```

### 严格类型检查清单

**1. 禁止使用 Any（零容忍）**：
```python
# ❌ 禁止：使用 Any 逃避类型检查
def process(data: Any) -> Any: ...

# ✅ 正确：使用具体类型或 TypeVar
def process[T](data: T) -> T: ...  # Python 3.12 语法
# 或
def process(data: dict[str, object]) -> Result:
    ...
```

**2. 完整注解所有参数**：
```python
from typing import override

class BaseClient:
    def __init__(self, timeout: float) -> None:
        self._timeout = timeout  # 类型从赋值推断

class APIClient(BaseClient):
    @override
    def __init__(self, timeout: float, api_key: str) -> None:
        super().__init__(timeout)
        self._api_key = api_key  # 实例变量也应有类型上下文

    async def fetch[
        T
    ](self, url: str, parser: Callable[[bytes], T]) -> T | None:
        """泛型方法：parser 返回什么类型，整体就返回什么类型。"""
        ...
```

**3. 禁止隐式可选（Implicit Optional）**：
```python
# ❌ 禁止：隐式可选（Python 3.10 之前的不良习惯）
def find(name: str = None) -> str: ...

# ✅ 正确：显式声明可选类型
def find(name: str | None = None) -> str | None: ...
```

**4. 使用抽象基类作为参数类型**：
```python
# ✅ 正确：接受抽象类型，返回具体类型
def analyze(data: Mapping[str, int]) -> list[str]:
    """参数接受不可变映射，返回值是列表。"""
    return [k for k, v in data.items() if v > 0]

# 调用时可以传入 dict、OrderedDict、ChainMap 等
result = analyze({"a": 1, "b": 2})
```

**类型导入优先级**：
1. 优先使用内置泛型（list, dict, set, tuple）
2. 参数类型使用抽象基类（Mapping, Sequence, Iterable）
3. 需要时才从 typing 导入（Any, TypedDict, Protocol 等）

## 数据结构选择

| 场景 | 推荐方案 | 原因 |
|------|---------|------|
| 简单数据载体 | `@dataclass(slots=True, frozen=True)` | 轻量、不可变、内存高效 |
| 需要验证/转换 | `pydantic.BaseModel` | 强大的校验和序列化 |
| 大量实例，性能关键 | `attrs` | 比 dataclass 更灵活 |
| 枚举类型 | `enum.Enum` | 类型安全，防止魔术字符串 |

```python
from dataclasses import dataclass
from enum import Enum, auto

class UserStatus(Enum):
    """用户状态枚举。"""
    ACTIVE = auto()
    INACTIVE = auto()
    SUSPENDED = auto()

@dataclass(slots=True, frozen=True)
class UserInfo:
    """用户信息数据类。

    使用 slots=True 减少内存占用，
    frozen=True 确保实例不可变（线程安全）。
    """
    user_id: int
    username: str
    status: UserStatus = UserStatus.ACTIVE
```

## 错误处理

**使用具体异常类型**：
```python
# 不好的做法：捕获过于宽泛的异常
except Exception:  # ❌ 不要这样做
    pass

# 正确的做法：捕获具体的异常
try:
    data = parse_json(content)
except json.JSONDecodeError as e:
    # 明确处理 JSON 解析错误
    logger.warning(f"JSON 解析失败: {e}")
    data = {}
except FileNotFoundError:
    # 处理文件不存在的情况
    logger.info("配置文件不存在，使用默认配置")
    data = DEFAULT_CONFIG
```

**异常转换原则**：
```python
def load_configuration(path: Path) -> Config:
    """加载配置文件。

    将底层异常转换为业务异常，添加上下文信息。
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ConfigError(f"配置文件编码错误: {path}") from e
    except PermissionError as e:
        raise ConfigError(f"无权读取配置文件: {path}") from e

    try:
        return Config.model_validate_json(content)
    except ValidationError as e:
        raise ConfigError(f"配置格式错误: {e}") from e
```

## 代码质量强制检查

### 检查命令详解

**poe typecheck vs pyright**：
- `poe typecheck`：通过 poethepoet 任务运行器调用 pyright，便于统一管理
- `pyright .`：直接调用类型检查器，效果相同
- **两者等价，选其一即可**，推荐直接使用 `pyright .` 更明确

**修改代码后必须执行以下命令**：

```bash
# 1. 代码格式化与风格检查（自动修复）
ruff check . --fix
ruff format .

# 2. 严格类型检查（强制要求，零错误容忍）
pyright .

# 3. 完整检查流程（提交前必做）
cd packages/ai && uv run poe check  # lint + typecheck + test
```

**或使用提供的快速检查脚本**（推荐）：
```bash
# 使用 skill 内置脚本一键检查
.claude/skills/py312/scripts/check_py312.sh [路径]

# 示例：检查当前目录
.claude/skills/py312/scripts/check_py312.sh .

# 示例：检查特定子目录
.claude/skills/py312/scripts/check_py312.sh packages/ai
```

**质量检查流程**：
1. 编写/修改代码后，先运行 `ruff format .` 自动格式化
2. 运行 `ruff check .` 检查风格问题并修复
3. **必须运行** `pyright .` 进行严格类型检查
4. 确保零错误后才能提交

### Pyright 严格模式配置

**项目级配置**（`pyproject.toml`）：
```toml
[tool.pyright]
pythonVersion = "3.12"           # 目标 Python 版本
typeCheckingMode = "strict"      # 严格模式（无妥协）
strictListInference = true       # 严格列表类型推断
strictDictionaryInference = true # 严格字典类型推断
strictSetInference = true        # 严格集合类型推断
reportMissingTypeStubs = "error" # 第三方库必须有类型存根
reportUnknownMemberType = "error" # 禁止未知成员类型
reportUnknownParameterType = "error" # 禁止未知参数类型
reportUnknownVariableType = "error"  # 禁止未知变量类型
reportUntypedFunctionDecorator = "error" # 装饰器必须类型化
```

**严格模式零容忍原则**：
- **零 `Any` 容忍**：不允许使用 `Any` 类型（特殊情况需注释说明）
- **完整泛型**：`list` → `list[str]`，`dict` → `dict[str, int]`
- **完整返回类型**：即使返回 `None` 也必须注解 `-> None`
- **完整参数类型**：包括 `self`、`cls`、`*args`、`**kwargs`
- **@override 强制**：重写父类方法必须使用 `@override` 装饰器
- **类型推断验证**：复杂表达式需显式注解，禁止依赖隐式推断

**处理类型检查错误**：
- 所有函数参数必须有类型注解
- 所有类属性必须有类型注解（包括私有属性 `_prefix`）
- 返回值类型必须明确（即使返回 None）
- 使用 `@override` 装饰器重载方法
- **避免使用 `Any` 类型**（严格模式禁用）
- **泛型必须完整参数化**：`list[str]` 而非 `list`

## 资源管理

**文件操作使用 pathlib**：
```python
from pathlib import Path

# 正确：使用 Path 对象进行路径操作
config_dir = Path("config")
settings_file = config_dir / "app.json"

# 读取文本文件
content = settings_file.read_text(encoding="utf-8")

# 写入文件（自动处理编码和关闭）
settings_file.write_text(json.dumps(config), encoding="utf-8")

# 需要上下文管理器的场景
with open(large_file, "r", encoding="utf-8") as f:
    for line in f:
        process_line(line)
```

## 异步编程

**使用 asyncio 的现代模式**：
```python
import asyncio
from collections.abc import AsyncIterator

async def fetch_data(urls: list[str]) -> list[Response]:
    """并发获取多个 URL 的数据。

    使用 Semaphore 控制并发数量，避免资源耗尽。
    """
    semaphore = asyncio.Semaphore(10)  # 最多10个并发

    async def fetch_one(url: str) -> Response:
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    return await resp.json()

    # 使用 asyncio.gather 并发执行
    return await asyncio.gather(*[fetch_one(url) for url in urls])
```

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `user_service.py` |
| 类 | 大驼峰 | `UserService` |
| 函数/方法 | 小写下划线 | `get_user_by_id()` |
| 常量 | 全大写下划线 | `MAX_RETRY_COUNT` |
| 私有属性 | 单下划线前缀 | `_internal_cache` |
| 保护属性 | 单下划线前缀 | `_helper_method()` |

## 不确定时的沟通原则

**当遇到以下情况时，必须停下来与用户确认**：

1. **需求不清晰**
   - 用户要求模糊或存在歧义
   - 多个实现方案各有优劣
   - 需要权衡性能与可读性

2. **架构决策**
   - 引入新的依赖或框架
   - 修改项目结构或配置
   - 重构核心业务逻辑

3. **边界情况**
   - 不确定异常如何处理
   - 配置参数选择（超时时间、并发数等）
   - 兼容旧版本的方案

**沟通模板**：
```
我在实现 [功能名称] 时遇到了一个选择：

方案A：[描述] - 优点：... 缺点：...
方案B：[描述] - 优点：... 缺点：...

我的建议是方案[A/B]，理由是：...

您倾向于哪个方案？或者您有其他考虑？
```

## 常见陷阱与避免方法

### 陷阱 1：混淆 Optional 语法

```python
# ❌ 错误：使用 Optional（旧语法，不推荐）
from typing import Optional

def find(name: Optional[str]) -> Optional[str]: ...

# ✅ 正确：使用 | None（Python 3.10+ 现代语法）
def find(name: str | None) -> str | None: ...
```

### 陷阱 2：忘记注解类属性

```python
class Config:
    # ❌ 错误：未注解的类属性
    timeout = 30  # 类型推断可能不准确

    # ✅ 正确：显式注解类属性
    timeout: float = 30
    debug: bool = False
```

### 陷阱 3：过度使用 @dataclass

```python
# ❌ 错误：所有类都用 dataclass（过度设计）
@dataclass
class Utils:
    """工具类，不需要状态。"""

    def helper(self) -> None: ...

# ✅ 正确：无状态工具类使用静态方法或函数
class Utils:
    """工具类，无需实例化。"""

    @staticmethod
    def helper() -> None: ...

# 或直接用模块级函数
def helper() -> None: ...
```

### 陷阱 4：隐式 Reexport

```python
# module_a.py
from typing import TypeVar

T = TypeVar("T")

# module_b.py
# ❌ 错误：隐式重新导出（pyright 会报错）
from module_a import T

# ✅ 正确：显式重新导出（使用 as）
from module_a import T as T
# 或在 module_a.py 使用 __all__
```

### 陷阱 5：复杂的嵌套泛型

```python
# ❌ 错误：过度复杂的嵌套类型（可读性差）
def process(
    data: dict[str, list[dict[str, int | str]]]
) -> list[tuple[str, int | str]]: ...

# ✅ 正确：使用 TypeAlias 分解复杂类型
from typing import TypeAlias

Record: TypeAlias = dict[str, int | str]
DataMap: TypeAlias = dict[str, list[Record]]
Result: TypeAlias = list[tuple[str, int | str]]

def process(data: DataMap) -> Result: ...
```

### 陷阱 6：忽视异常链

```python
# ❌ 错误：吞掉原始异常信息
try:
    data = parse(content)
except ValueError:
    raise ConfigError("解析失败")

# ✅ 正确：保留异常链上下文
try:
    data = parse(content)
except ValueError as e:
    raise ConfigError(f"解析失败: {e}") from e
```

### 陷阱 7：Path 对象滥用 str 方法

```python
from pathlib import Path

p = Path("data") / "file.txt"

# ❌ 错误：不必要的 str 转换
with open(str(p), "r") as f: ...

# ✅ 正确：Path 对象可直接使用
with open(p, "r") as f: ...
# 或更优
content = p.read_text()
```

## Python 3.12+ 先进特性（严格模式必备）

**使用最新类型系统特性**：

```python
# 1. 使用 **kwargs 的 TypedDict 注解（Python 3.12+）
from typing import TypedDict, Unpack

class ConnectionConfig(TypedDict):
    host: str
    port: int
    timeout: float

def connect(**kwargs: Unpack[ConnectionConfig]) -> Connection:
    """使用 Unpack 精确注解 **kwargs 类型。"""
    ...

# 2. 使用 TypeAliasType 创建类型别名（更清晰错误信息）
from typing import TypeAliasType

JsonValue = TypeAliasType(
    "JsonValue",
    dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None
)

# 3. 使用 @override 强制检查（严格模式要求）
from typing import override

class BaseService:
    def process(self, data: bytes) -> bytes:
        ...

class AdvancedService(BaseService):
    @override  # 明确标记重写，父类删除时会报错
    def process(self, data: bytes) -> bytes:
        ...

# 4. 使用 Self 类型（Python 3.11+，3.12 完善）
from typing import Self

class Builder:
    def __init__(self) -> None:
        self._parts: list[str] = []

    def add(self, part: str) -> Self:  # 返回类型为具体子类
        self._parts.append(part)
        return self

# 5. 使用 LiteralString 防止 SQL 注入（安全敏感场景）
from typing import LiteralString

def query(sql: LiteralString, *params: object) -> None:
    """LiteralString 确保传入的是字面量字符串，非动态构建。"""
    ...

# 6. 使用 Required/NotRequired 精确控制可选字段
from typing import NotRequired

class APIResponse(TypedDict):
    data: dict[str, object]
    error: NotRequired[str]  # 可选字段
    meta: NotRequired[dict[str, object]]

# 7. 使用 TypeVar 的 bounds 和 constraints（高级泛型）
from typing import TypeVar

# 限定类型范围
NumberT = TypeVar("NumberT", int, float)

def clamp(value: NumberT, min_val: NumberT, max_val: NumberT) -> NumberT:
    """限定只能接受 int 或 float 类型。"""
    return min(max_val, max(min_val, value))
```

## 审查清单

在提交代码前，确认以下检查项：

### 基础检查
- [ ] 所有函数长度不超过 30 行
- [ ] 所有函数都有完整类型注解（包括 `-> None`）
- [ ] 文档字符串使用中文编写，说明"为什么"
- [ ] 复杂逻辑有中文注释

### 类型严格检查（Pyright Strict Mode）
- [ ] 运行 `pyright .` **零错误**（严格模式零容忍）
- [ ] 没有使用 `Any` 类型（特殊情况需注释说明原因）
- [ ] 所有泛型都完整参数化（`list[str]` 而非 `list`）
- [ ] 重写方法使用 `@override` 装饰器
- [ ] 没有隐式可选（`str = None` → `str | None`）

### 代码风格（Ruff）
- [ ] 运行 `ruff check . --fix` 无错误
- [ ] 代码已格式化 `ruff format .`
- [ ] 导入排序正确（ruff 自动修复）

### 设计质量
- [ ] 没有使用裸 `except:` 或宽泛的 `except Exception:`
- [ ] 文件操作使用 `pathlib.Path` 而非字符串拼接
- [ ] 没有硬编码的魔术数字（使用常量或 Enum）
- [ ] 函数职责单一，命名清晰表达意图
- [ ] **代码是否足够简单？能否再简化？**
