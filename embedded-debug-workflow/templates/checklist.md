# 调试检查清单

> 本清单在「每次调试迭代完成后」以及「最终回归验证」时逐项核对。
> 每一项都给出**验证方法**与**验收标准**，全部打勾方可进入下一步或出报告。
> 配置/路径约定：`{工作区}/.copilot/embedded-debug-config.json`（工程配置）、
> `{项目目录}/.copilot/{日期}_{简述}.md`（报告）、
> `{项目目录}/.copilot/verify_log.txt`（验证日志）。

---

## 0. 调试前准备（每次新任务必查）

- [ ] **配置已生成且完整**：`{工作区}/.copilot/embedded-debug-config.json` 存在，运行
      `python scripts/config_reader.py --validate` 输出 `✅ 配置完整`
      - 缺失 `keil.uv4_path` → 配置生成失败，重新 `/kzl init`
      - 某 `projects[i].serial.port/baud` 或 `projects[i].debugger.com` 缺失 → 该工程不合格
- [ ] **工程/串口/下载器对应正确**：多工程时用 `--project-index N` 指定；
      确认本次调试的工程其 `dir`/`file`/`serial`/`debugger.com` 与实物一致
- [ ] **Git 基线干净**：`git status` 无未提交改动（或已 `git commit` 基线），确保可随时回退
- [ ] **硬件连接就绪**：
      - 目标板供电正常、下载器（JLink/ST-Link）USB 已识别
      - 串口（TTL/USB 转串）接线正确（TX↔RX 交叉、共地）
      - 板端波特率、数据位、停止位、校验位与 `serial` 配置一致

---

## 1. 编译验证

- [ ] **零错误零阻塞警告**：Build Output 显示 `0 Error(s), 0 Warning(s)`
      - 若有 Warning，逐条确认非阻塞性；凡涉及类型、未初始化、截断的必须清零
- [ ] **修改确实被编译**：观察被改文件的目标文件（`.o`）时间戳已更新；
      怀疑未重编时执行 `Rebuild` 或删除对应 `.o`/`.axf` 后全编
- [ ] **CHESHI 宏已开启**：本次需要调试打印时，Keil 工程 `C/C++ → Define` 含 `CHESHI`
      （否则 `#if (CHESHI & ...)` 打印不出现，见 `refs/cheshi-macro.md`）
- [ ] **产物已刷新**：生成的 `.axf`/`.hex` 时间为最新，且大小符合预期

---

## 2. 下载（烧录）验证

- [ ] **下载成功标志**：日志出现 `Flash Load finished` / `Programming Done` / `Verify OK`
- [ ] **下载器匹配**：`debugger.com` 与实物一致，无 `No target connected` / `Cannot connect`
- [ ] **运行无即时崩溃**：下载后目标板复位运行，串口/LED 初步正常，未立即 HardFault

---

## 3. 串口日志验证

- [ ] **监听命令正确**：`python scripts/serial_monitor.py --config-dir {工作区} --project-dir {工程目录}`
      端口与波特率应来自对应工程的 `serial` 配置，而非硬编码
- [ ] **预期打印出现**：日志中出现预期的 CHESHI 调试打印，内容与格式正确
- [ ] **无乱码**：乱码时核对 `serial` 的 `baud`/`parity`/`data_bits`/`stop_bits` 与板端一致
- [ ] **端口占用处理**：`Access to COM port is denied` → 关闭占用该串口的其它工具后重试
- [ ] **信息充分可定位**：关键变量、时序、收发对照齐全，足以支撑故障定位（不止 `here`/`ok`）
- [ ] **日志已保存**：验证日志写入 `{项目目录}/.copilot/verify_log.txt`

---

## 4. 代码修改与影响面

- [ ] **最小修改**：改动仅落在目标模块/函数，未触碰无关接口、全局变量、头文件契约
- [ ] **逻辑核对**：长度/偏移/缓冲区边界已复核（典型坑：共享缓冲区覆盖、帧长度偏移算错）
- [ ] **依赖补齐**：新增的头文件、宏、函数声明均已包含，编译无新 Warning
- [ ] **收发对照**：有通信类故障时，发送端与接收端打印对照，确认数据在哪一段被截断/篡改

---

## 5. CHESHI 调试代码清理（故障解决后必查）

- [ ] **整段删除**：`main.c` 头部的 `CHESHI` 宏定义，以及所有 `#if (CHESHI & ...)` / `#ifdef CHESHI` 块已全部移除
- [ ] **清理后重编**：重新编译确认 `0 Error`，且调试打印不再出现
- [ ] **无残留**：未遗留临时变量、`// TODO debug`、`printf` 调试行、被注释掉的打印

---

## 6. 回归验证

- [ ] **原故障消失**：对照最初的错误码/异常日志，现象已消除
- [ ] **无连锁副作用**：通信、定时器、中断、外设等其它模块行为正常
- [ ] **全量复跑**：重新全编+下载，再次监听确认无异常错误码/超时
- [ ] **健壮性**：边界输入、断线重连、反复触发等异常路径下设备不崩溃

---

## 7. 报告与记忆

- [ ] **报告生成**：`{项目目录}/.copilot/{日期}_{简述}.md` 含
      故障描述 / 根因分析 / 修复摘要 / 变更文件 / 验证日志 五要素
- [ ] **记忆写入**：索引追加到 `data/debug-history.yaml`（date/desc/fault/root_cause/report）
- [ ] **状态收尾**：`flow-gate.json` 的 `currentPhase` 已标记 `COMPLETED`

---

## 常见问题速查

| 问题 | 可能原因 | 处理 |
|------|----------|------|
| `Access to COM port is denied` | 串口被其它程序占用 | 关闭串口助手/终端，确认无重复监听 |
| 串口收到乱码 | 波特率/校验/数据位/停止位不匹配 | 核对 `serial` 配置与板端实际参数 |
| 编译未生效（改了没反应） | 文件未被重编 | `Rebuild` 或删 `.o`/`.axf` 后全编 |
| `#ifdef` 打印未出现 | `CHESHI` 宏未定义 | Keil `C/C++ Define` 添加 `CHESHI` |
| 下载 `No target connected` | 下载器未接/驱动异常/`debugger.com` 错 | 重插 USB、核对 `debugger.com`、装驱动 |
| 下载后立刻 HardFault | 固件/时钟/堆栈配置异常 | 回退上一 commit，比对改动范围 |
| 打印出现但信息不足 | CHESHI 分级过低/打印点不对 | 提高 `CHESHI` 位或调整打印位置 |
| 故障偶发难复现 | 时序/中断竞争/缓冲区覆盖 | 在临界区与收发两端同时加打印对照 |
