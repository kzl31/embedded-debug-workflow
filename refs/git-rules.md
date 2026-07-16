# Git 本地版本管理规范

> 本文件由 SKILL.md 按需加载，描述调试过程中的 Git 操作。

---

## 强制规则

1. **全程禁止 `git push`** — 所有操作仅限本地仓库
2. **稳定基线分支**：本地 `main`/`master`，禁止直接在该分支编写调试代码
3. **临时调试分支**：每次故障独立创建，命名格式 `debug/故障简述_YYYYMMDD`
4. **临时 CHESHI 代码与正式修复代码强制隔离**

---

## 调试全流程 Git 操作

### 调试开始前

```bash
# 切换本地主分支，同步最新代码
git checkout main
git pull --no-ff

# 创建并切换专属本地调试分支
git checkout -b debug/ttl_comm_err_20260706

# 校验工作区干净
git status
```

### 调试打印迭代阶段

新增/修改 CHESHI 调试打印仅本地修改，不提交。

如需切换验证其他问题，自动暂存调试代码：

```bash
git stash save "临时调试代码-TTL通信故障"
```

恢复暂存：

```bash
git stash pop
```

### 业务代码修复完成

```bash
# 快照保存当前全部修改
git add .
git stash save "修复前完整快照"

# 仅提交业务修复代码（过滤所有 CHESHI 调试内容）
git add 目标修复文件.c
git commit -m "fix: 修复TTL通信故障，PDU帧长度计算偏移错误"
```

### 版本回退（代码改错/故障恶化时）

```bash
# 查看本地提交记录
git log --oneline

# 场景1：保留本地修改，仅回退提交记录
git reset --soft 目标提交ID

# 场景2：彻底丢弃所有本地修改，强制回退至稳定版本
git reset --hard 目标提交ID
```

### 调试收尾

1. 删除 `main.c` 内全部 CHESHI 调试宏、配套打印、通信快照采集器、Flush 调用和临时验证检测代码
2. 本地合并分支，清理临时分支

```bash
git checkout main
git merge --no-ff debug/ttl_comm_err_20260706

# 删除本地临时分支
git branch -d debug/ttl_comm_err_20260706
```

---

## Git 命令速查表

| 场景 | 命令 |
|:---|:---|
| 创建调试分支 | `git checkout -b debug/xxx_YYYYMMDD` |
| 暂存临时修改 | `git stash save "描述"` |
| 恢复暂存 | `git stash pop` |
| 查看暂存列表 | `git stash list` |
| 查看提交历史 | `git log --oneline` |
| 软回退 | `git reset --soft <commit>` |
| 硬回退 | `git reset --hard <commit>` |
| 合并分支 | `git merge --no-ff <branch>` |
| 删除分支 | `git branch -d <branch>` |
| 查看状态 | `git status` |
| 查看差异 | `git diff` |
| 查看文件修改 | `git diff --name-only` |
