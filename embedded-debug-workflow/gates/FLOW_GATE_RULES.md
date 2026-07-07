# ⛔ Flow Gate 门禁总规则

> **优先级：最高。违反此文件 = 流程违规。**

---

## 核心原则

```
registry.json  是唯一阶段来源（可扩展）
.copilot/flow-gate.json      是唯一进度来源
gates/ 中的文件     是唯一操作入口
未读到对应门禁文件  = 禁止执行对应操作
```

---

## 规则 1：启动预检（每次操作前必须执行）

```
步骤 1: 读取 registry.json，获取所有阶段定义
步骤 2: 读取项目工作区 .copilot/ 下的 flow-gate.json
步骤 3: 检查 flow-gate.json.currentPhase
步骤 4: 在 registry 中查找 currentPhase 对应的 gateFile
  ├─ 找到 → 读取 gates/ 下对应的门禁文件
  ├─ 找不到 / currentPhase == null → 读取 gates/STARTUP.md
  └─ currentPhase == "COMPLETED" → 允许读取任何门禁（继续或新任务）
```

## 规则 2：阶段锁定

```
每个门禁文件内部有 Step 1..N
必须按顺序执行，严禁跳过中间步骤
完成一步后必须更新 .copilot/flow-gate.json
```

## 规则 3：门禁文件绑定

```
所有阶段-门禁映射集中在 registry.json 中管理。
新增阶段 → 只需在 registry.json 注册 + 创建 gates/*.yaml。
无需修改任何现有文件。
```

## 规则 4：用户描述故障 ≠ 跳过门禁

```
用户说"有故障" 或 "报错了" 或 粘贴错误日志
→ 仍然从 .copilot/flow-gate.json.currentPhase 开始
→ 如果 currentPhase == "STARTUP"，必须先完成启动流程
→ 分析代码/查提交 属于 DEBUG_LOOP 阶段的操作
```

## 规则 5：跨阶段禁止（定义在 registry.json 中）

```
各阶段的 forbiddenOperations 在 registry.json 中定义。
SKILL.md 和本文件不再重复列出。
常见的禁止操作包括：
- STARTUP 阶段：禁止 git log/diff、分析代码、编译下载
- DEBUG_LOOP 阶段：禁止输出报告
- VERIFY_AND_REPORT 阶段：禁止添加 CHESHI 宏
```

## 规则 6：门禁文件完整性校验

```
gates/ 目录必须包含所有 registry.json 中注册的 gateFile：
  读取 registry.json → 遍历所有 phases → 检查 gateFile 路径是否存在
缺少任何文件 → 禁止操作，先报缺失
```

---

## ⚠️ 历史教训

```
2026-07-06: 两次跳过 STARTUP 流程直接分析代码
原因：用户描述故障时，被具体问题吸引，未执行预检
根治：Flow Gate 机制 —— 操作前必须先读 registry.json + .copilot/flow-gate.json
```
