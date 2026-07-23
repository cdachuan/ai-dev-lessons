# 0007 · System Prompt 与角色设定

**日期**：2026-07-XX（微信口述）
**课程**：0007 · System Prompt 与角色设定
**状态**：已交付（口述，无 HTML 课件）

## 关键洞察

1. **System Prompt 是 AI 的「岗位说明书」** —— 不是聊天内容，而是告诉模型「你是谁、怎么回答、遵守什么规则」。它每轮对话都在（不像用户消息一条条消失），所以影响整个对话的基调。

2. **用户其实每天都在用 System Prompt** —— 用户通过 Hermes 的 personality、memory、skills 间接在设定 System Prompt。用户的每一条记忆、加载的每个 skill，本质上都在「改写」Hermes 的 System Prompt。用户已经是 System Prompt 的「间接操盘手」。

3. **System Prompt 越长 ≠ 越好** —— 过多的规则会被稀释（模型注意力有限，记不住所有指令）。核心规则放在开头（primacy effect），辅助说明放结尾（recency effect），中间的是「遗忘区」。

4. **角色设定的实际案例就在身边** —— Hermes 的 `/personality boss` 其实就是切换 System Prompt 中角色描述部分。用户的业务场景（项目助理、对外沟通）本质上也在不断地「角色切换」。

## 待观察

- 用户是否理解自己给 Hermes 的「记忆」和「修正」最终进入了 System Prompt 层面
- 用户是否尝试给自己写的 prompt 加角色设定
- 用户是否注意到「规则太多时模型反而记不住」

## 关联课程

- ← 0004：Prompt（System Prompt 是 Prompt 的一种特殊类型——始终存在的底层指令）
- ← 0006：Token（System Prompt 越长，每轮消耗的输入 Token 越多）
- → 0008：Temperature（角色设定和 Temperature 共同决定回答的风格）
- → Phase2 项目：写脚本时如何设计 System Prompt
