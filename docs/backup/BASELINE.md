# SKILL 备份

两份都是改「技能整合」文档之前的原文，没有改过字。

| 文件 | 对应提交 | 是什么 |
| --- | --- | --- |
| `SKILL-main-6dbeadd.md` | `6dbeadd2c37931a73a1f07d897aa8facc0e56f1b` | `main` 上的技能。这一版没有 `template/flow.js`，也没有管内粒子。 |
| `SKILL-6b703d2.md` | `6b703d2eb035e2495d6b4d6e2ece5ffc95e03fc2` | 本分支上、把增强写进技能正文之前的 `SKILL.md`。代码（`flow.js`、模板、B/4 增强页）以这一提交为准。 |

恢复某一版：

```bash
git show 6dbeadd:SKILL.md
git show 6b703d2:SKILL.md
```

`main` 在合并本分支之前不含这些文件。合并之后以 `main` 上的 `SKILL.md` 为准，不再把本分支名当成唯一入口。
