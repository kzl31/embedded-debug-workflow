# /kzl 打印 — 独立添加调试打印

> 此命令处理 `/kzl 打印 <要求>`；兼容用户常见误输 `/klz 打印 <要求>`。
> 功能：根据用户描述在嵌入式源码中添加临时调试信息，严格遵守 `refs/cheshi-macro.md`。
> 此命令独立于调试流程，不启动、不初始化、不检查、不推进工作流引擎。

---

## 执行步骤

### Step 1: 明确打印目标

```yaml
action: analyze_request
需要确定:
  - 要观测的故障、变量、函数、状态或通信事件
  - 期望打印时机和频率
  - 用户已明确目标时直接执行，不重复询问
  - 缺少源码位置且无法从工作区定位时，才询问文件/函数
```

### Step 2: 读取打印规范与相关源码

```yaml
action: analyze
required_reference: "{skill_dir}/refs/cheshi-macro.md"
规则:
  - 只读取完成打印修改所需的源码
  - 不调用 workflow_engine.py
  - 不要求存在 embedded-debug-config.json
  - 不执行 /kzl 初始化、编译或下载
```

### Step 3: 设计安全观测点

```yaml
action: design
强制规则:
  - 所有新增调试代码都由 CHESHI 条件编译包裹
  - CHESHI 统一集中定义在 main.c 文件头部；已有定义时复用并按需调整位掩码
  - 标签使用 [COMMON]、[COMM_RAW]、[DRV_xxx]、[FSM]、[ERR]、[INFO] 或 [HEX_DATA]
  - ISR、DMA 回调、协议接收回调和通信底层不得直接 printf/puts
  - 时序敏感路径只采集快照/事件，主循环调用 Debug_Flush 输出
  - 控制打印频率，避免刷屏、阻塞或改变故障时序
```

### Step 4: 修改源码

```yaml
action: edit_source
说明:
  - 仅增加满足用户要求的最小必要打印及其缓冲/Flush 支撑代码
  - 保持项目原有格式、类型和平台接口
  - 不改业务行为
  - 不自动提交 Git，不自动编译下载
```

### Step 5: 静态自检

```yaml
action: verify
checklist:
  - 新增打印是否全部受 CHESHI 控制
  - CHESHI 是否集中且无重复定义
  - 通信/中断路径是否无直接阻塞打印
  - 格式化占位符是否与变量类型匹配
  - Debug_Flush 是否位于主循环或非时序敏感调用链
  - 关闭 CHESHI 后是否不引入未使用符号或缺失引用
```

---

## 完成后

只报告修改文件、观测点、CHESHI 位/等级和打印标签；提示用户可按需执行 `/kzl 编译` 或 `/kzl 编译下载`，但不得自动执行。
