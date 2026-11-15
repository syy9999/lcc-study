# s05 · TodoWrite —— 学习笔记

> 本章教程：[README.md](./README.md) · 参考实现：`../learn-claude-code-main/s05_todo_write/code.py`

> **格言**：没有计划的 agent 走哪算哪 —— 先列步骤再动手，完成率翻倍

## 学习目标

- 实现 `TodoItem` 数据结构和 `todo_write` 工具
- 让 agent 在动手前先列计划，执行中持续更新状态
- 观察"有无计划"对复杂任务完成率的影响

## 本章要回答的问题

1. todo 状态应该存在模型上下文里，还是写到磁盘？两者有什么区别？
2. 谁负责更新 todo 状态？什么时候更新？
3. todo 与 s10 的 task system 边界在哪里？

## 我的笔记

## Nag Reminder 是什么

它是 TodoWrite 配套的一个**轻量 "催更" 提醒器**：不改动 Agent 主循环，只是在循环里挂一个计数器，当模型连续多轮只顾着调工具、忘了更新待办清单时，自动往对话里塞一句提醒，把它的注意力拽回 todo 列表上。

### 工作机制（对照图里的循环）

1. **计数**：维护一个 `rounds_since_todo` 计数器。每一轮工具执行完后 ——
   - 本轮调用了 `todo_write` → 计数器清零；
   - 本轮没调 `todo_write`（只调了 bash/read/write 等）→ 计数器 +1。阿里云开发者社区
2. **触发阈值**：当 `rounds_since_todo >= 3`（连续 3 轮没更新 todo），就注入一条提醒：
`<reminder>Update your todos.</reminder>`，然后计数器复位，避免反复刷屏。
3. **注入位置**：不是写进静态系统提示词，而是**插到最后一条消息的 content 开头**（一般是上一轮 `tool_result` 所在的 user 消息）。原因是系统提示词在长对话中影响力会衰减，放在最新一条消息里，正好是模型注意力最集中的位置。



### . `TOOLS`：工具声明（给 LLM 看的 "接口清单"）

这是一组 **JSON Schema 元数据**，不含任何可执行逻辑。作用是告诉模型：

- 有哪些工具可用（`name`）
- 每个工具干什么（`description`）
- 每个工具接受什么参数、类型、是否必填（`input_schema`）

它会原样传给模型接口的 `tools=` 参数，模型据此决定 "要不要调工具、调哪个、参数怎么填"，最后生成一个 `tool_use` block 回来。**这里面只有契约，没有函数。**

### 2. `TOOL_HANDLERS`：工具处理器映射（给运行时查的 "路由表"）

这是一个 **`名字 → Python 函数`** 的 dict，也就是常说的 dispatch map。模型返回 `tool_use` 之后，循环按 `block.name` 查这张表，取出对应的函数，把参数传进去真正执行，再把返回值包成 `tool_result` 回灌进 `messages`。

### 两者怎么配合（以一次调用为例）

```
① 请求模型时：TOOLS 作为工具清单一起传入
        ↓
② 模型返回：tool_use(name="bash", input={"command": "ls"})
        ↓
③ 循环里按名字查表：
   handler = TOOL_HANDLERS["bash"]     # 即 run_bash
   output  = handler(**block.input)    # 真正执行 run_bash(command="ls")
        ↓
④ 结果包成 tool_result，追加到 messages[]，下一轮继续
```

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 用一个多步骤任务对比"有计划 / 无计划"的表现
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 本章教程：[README.md](./README.md)
- 参考实现：`../learn-claude-code-main/s05_todo_write/code.py`
- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>


## `TodoManager` 就是一个 "待办清单的状态管家"，三个方法各司其职

### 1. `__init__`：初始化空清单

```
def __init__(self):
    self.items = []
```

初始化的是 **TodoManager 实例自己持有的一份进程内待办状态**，先放空列表。这个 `self.items` 就是整个 todo 系统唯一的 "事实来源"：

- 列表里每一项是一个 dict，结构大致是 `{"content": "任务描述", "status": "pending" | "in_progress" | "completed"}`；
- 它存在内存里，不属于 `messages[]`，模型不能直接读写，只能通过 `todo_write` 工具间接修改；
- Agent 每一轮都能通过 `render()` 读到当前这份清单。

### 2. `update(todos)`：接收模型提交的新清单，校验后整体替换

```
def update(self, todos: list | str) -> str:
    validated = []
    ...
    self.items = validated
    return self.render()
```

这是 `todo_write` 工具真正背后调用的方法，流程分三步：

1. **解析入参**：模型传进来的可能是 list，也可能是字符串（`list | str`），先统一解析成结构化条目；
2. **校验**：逐条检查状态是否合法（只能是 pending /in_progress/completed），以及经典约束 ——**同一时间最多只能有一个 `in_progress`**，不合法就返回错误、不替换；
3. **整体替换 + 回显**：校验通过后用新列表**覆盖** `self.items`（不是追加），再调用 `render()` 把最新清单渲染成文本返回。这个返回值会被包进 `tool_result`，下一轮发给模型，让它看到 "现在任务列表长这样"。

注意它是**全量替换**：模型每次调用 `todo_write` 都要把完整清单（含已完成项）一起提交，而不是只改一条。

### 3. `render()`：把当前清单渲染成给模型看的文本

```
def render(self) -> str:
    # [ ] pending, [>] in progress, [x] completed
```

只读方法，把 `self.items` 转成一份带状态图标的纯文本清单，例如：

```
[ ] 读取相关代码
[>] 实现 todo_write 工具
[x] 搭好 Agent Loop
```

对应关系：

表格

| status | 图标 | 含义 |
| --- | --- | --- |
| `pending` | `[ ]` | 待开始 |
| `in_progress` | `[>]` | 正在做 |
| `completed` | `[x]` | 已完成 |

它的作用是把内存里的结构化状态，变成模型容易读、能判断 "做到哪一步" 的自然语言文本。`update` 改完状态后会调一次它回显，循环需要展示进度时也会调它。

### 三者串起来看

```
模型调 todo_write(todos=...)
        ↓
update：解析 → 校验 → 替换 self.items
        ↓
render：把 self.items 渲染成清单文本
        ↓
文本作为 tool_result 回给模型，下一轮模型看到最新进度
```

一句话：`__init__` 开好一张空清单，`update` 负责 "收模型的新计划并校验存档"，`render` 负责 "把存档翻译成模型能读的清单"；状态始终存在 `self.items` 这一份内存列表里。