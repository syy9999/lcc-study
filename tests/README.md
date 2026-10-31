# tests

这里放我为自己的实现补充的测试。

## 运行

```sh
pytest
```

## 约定

- 按章节命名：`test_s01_agent_loop.py`、`test_s06_subagent.py`……
- 优先测试**纯逻辑**部分（工具分发、权限判断、压缩配对、cron 匹配等），避免在测试中真实调用 LLM。
- 需要 LLM 的验证放在手工实验里，结果记录到对应章节的 `README.md`。
- `test_repo_layout.py` 是仓库骨架的自检，不用修改。