# 迭代检查清单

> 每次自动迭代/修复完成后，以及最终回归验证时，逐项核对。
> 详细版（含验证方法、验收标准、常见问题）见 `templates/checklist.md`。
> 路径约定：`{工作区}/.copilot/embedded-debug-config.json`（工程配置）、
> `{项目目录}/.copilot/` 存放报告与验证日志。

---

## 0. 调试前准备

- [ ] 配置完整：`config_reader.py --validate` 输出 `✅ 配置完整`
      （`keil.uv4_path`、`projects[].dir/file`、`projects[].serial.port/baud`、`projects[].debugger.com` 均齐全）
- [ ] 工程/串口/下载器对应正确（多工程用 `--project-index` 指定）
- [ ] `git status` 无未提交改动或已 commit 基线，可回退
- [ ] 硬件连接：供电、下载器 USB、串口接线、波特率与 `serial` 一致

## 1. 编译验证

- [ ] Build Output `0 Error(s), 0 Warning(s)`（Warning 须逐条确认非阻塞）
- [ ] 被改文件确已重编（必要时 `Rebuild` 或删 `.o`/`.axf`）
- [ ] 调试打印需要时，`CHESHI` 宏已在 Keil `C/C++ Define` 中开启

## 2. 下载验证

- [ ] 下载日志出现 `Flash Load finished` / `Programming Done` / `Verify OK`
- [ ] `debugger.com` 与实物一致，无 `No target connected`
- [ ] 下载后目标板运行正常，无即时 HardFault

## 3. 串口日志验证

- [ ] `serial_monitor.py --config-dir {工作区} --project-dir {工程目录}` 监听，参数取自配置
- [ ] 日志出现预期 CHESHI 打印，无乱码（核对 `serial` 波特率/校验/数据位/停止位）
- [ ] 打印信息充分，可支撑故障定位
- [ ] 验证日志已保存到 `{项目目录}/.copilot/verify_log.txt`

## 4. 代码修改与影响面

- [ ] 修改仅影响目标模块，无连锁副作用
- [ ] 长度/偏移/缓冲区边界已复核（典型坑：共享缓冲区覆盖、帧长度偏移算错）
- [ ] 收发对照确认数据截断/篡改发生的具体段落

## 5. CHESHI 清理

- [ ] `main.c` 头部 `CHESHI` 宏定义及所有 `#if (CHESHI & ...)` / `#ifdef CHESHI` 块已整段删除
- [ ] 清理后重编 `0 Error`，调试打印不再出现
- [ ] 无临时变量/`// TODO debug`/被注释打印残留

## 6. 回归验证

- [ ] 原故障现象消失
- [ ] 其它功能模块（通信/定时器/中断/外设）正常
- [ ] 全量重编+下载，再次监听无异常错误码
- [ ] 边界/异常输入下设备不崩溃

## 7. 报告与记忆

- [ ] 生成 `{项目目录}/.copilot/{日期}_{简述}.md`（故障/根因/修复/变更文件/验证日志）
- [ ] 写入 `data/debug-history.yaml` 记忆索引
- [ ] `flow-gate.json` 标记 `COMPLETED`
