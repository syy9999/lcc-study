"""s14 · MCP Plugin —— 我的实现

格言：能力不够？插上 MCP

目标：
    连接 MCP server，发现外部工具，并把它们并入同一个工具池。

运行：
    python s14_mcp_plugin/code.py

关键设计：
    MCPClient.connect()   → 建立连接
    MCPClient.list_tools() → 发现工具
    MCPClient.call_tool()  → 调用工具
    工具名加 server 前缀，避免同名冲突
    TOOLS / TOOL_HANDLERS 同时追加 MCP 工具

写完再对照：
    ../learn-claude-code-main/s14_mcp_plugin/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。