# AI 小学英语家教项目 — Handoff

## 1. 项目概述

本项目目标是构建一套面向小学生的 AI 家教系统。

当前阶段只实现 **英语 AI 家教 V1**，语文和数学暂不开发，但必须从 API、数据模型、目录结构和学科抽象层面预留扩展能力。

产品形态：

- **Web / PWA 是主客户端**
- 支持手机、平板、PC
- **M5Stack 仅作为兼容终端**
- 所有 AI、教学逻辑、学习状态均放在服务端
- 国内服务器部署
- 不依赖 OpenAI API
- 优先使用国产模型和国内云 API
- 服务端不运行大模型，因此不需要 GPU

---

# 2. 当前已确定的技术路线

## 2.1 服务器

推荐配置：

```text
OS: Ubuntu Server 24.04 LTS x86_64
CPU: 2 vCPU
RAM: 4 GB
SSD: 40 GB+
Bandwidth: 3–5 Mbps+
Public IPv4: Yes
GPU: No
```

V1 不需要：

- Kubernetes
- Redis
- Elasticsearch
- Qdrant
- GPU
- 本地大模型
- 本地 Whisper
- 本地 TTS
- 大规模 RAG

V1 推荐：

```text
Docker
Docker Compose
Caddy
FastAPI
SQLite
```

---

# 3. 产品总体架构

```text
                       ┌──────────────────────┐
                       │    Web / PWA 主端     │
                       │ 手机 / 平板 / PC      │
                       └──────────┬───────────┘
                                  │ HTTPS / WS
                                  ▼
                       ┌──────────────────────┐
                       │    Tutor Backend     │
                       │      FastAPI         │
                       ├──────────────────────┤
                       │ Session Manager      │
                       │ Tutor Agent          │
                       │ Skill Router         │
                       │ Learning Engine      │
                       │ Student Profile      │
                       │ Progress / Mistakes  │
                       └───────┬──────┬───────┘
                               │      │
                    ┌──────────┘      └──────────┐
                    ▼                            ▼
             ┌──────────────┐             ┌───────────────┐
             │    SQLite    │             │ 国内 AI API   │
             │              │             │               │
             │ 学生档案     │             │ Qwen LLM      │
             │ 学习记录     │             │ ASR           │
             │ 掌握度       │             │ TTS           │
             │ 错词/错句    │             │ Vision 预留   │
             │ 会话记录     │             │               │
             └──────────────┘             └───────────────┘

                                  ▲
                                  │ 同一套 API
                                  │
                       ┌──────────┴───────────┐
                       │   M5Stack CoreS3     │
                       │    兼容客户端        │
                       │ Mic / Speaker / UI   │
                       └──────────────────────┘
```

核心原则：

> Web / PWA 是正式主产品；M5Stack 只是另一种客户端，不能让硬件终端反向绑架整体架构。

---

# 4. GitHub 参考项目

项目开发不是从零开始，应重点参考和复用以下开源项目。

---

## 4.1 ChinaTextbookStudyFree

定位：

**学习平台、教材结构、课程数据、学习路径、错题、奖励系统的主要参考项目。**

重点研究：

```text
apps/web
packages/core
data
output
scripts
```

优先复用 / 借鉴：

- Web UI
- PEP 英语课程结构
- Unit / Lesson
- 题库
- 知识点
- 课文听读
- 英语故事
- 学习进度
- 错题回顾
- 每日任务
- 周报
- 成就系统
- 奖励机制
- SRS / Review 相关逻辑
- packages/core 中的领域逻辑

V1：

```text
English = enabled
Chinese = disabled
Math = disabled
```

不要删除语文和数学的数据抽象，只在产品界面中隐藏。

未来开启语文和数学时，应尽量直接复用已有课程框架。

---

## 4.2 hermes-edu-skills

定位：

**教学 Skill / 教学策略资产。**

本项目：

```text
不部署 Hermes Runtime
```

只复用 Skill 文件和教学方法。

优先研究：

```text
primary-english-pep-textbook-sync
agent-socratic-tutor
agent-mistake-review
agent-study-plan
agent-learning-report
daily-review 类 Skill
英语词汇 / 阅读 / 教材同步相关 Skill
```

推荐模式：

```text
当前课程状态
     ↓
Skill Router
     ↓
选择对应 SKILL.md
     ↓
加载教学规则
     ↓
结合学生状态
     ↓
生成 LLM Prompt
```

Skill 不应与某一个 Agent Runtime 强绑定。

---

## 4.3 Kid Tutor

定位：

**教学循环与自适应算法参考。**

不建议直接作为运行时依赖。

重点借鉴：

- Socratic Teaching
- Adaptive Difficulty
- 连续答对自动升难度
- 连续困难自动降难度
- 不立即公布答案
- 1～3 次提示
- 兴趣场景化
- Student Profile
- Parent Report

示例：

```text
连续 3 次正确
    ↓
difficulty + 1

连续 2～3 次困难
    ↓
difficulty - 1
    ↓
增加提示
```

---

## 4.4 mini-classroom

定位：

**低龄 Web/PWA UI 与轻量前端参考。**

重点借鉴：

- PWA
- 大按钮
- 低龄交互
- 单词卡
- 移动端适配
- 离线缓存
- 简单学习进度展示

不作为后端主体。

---

# 5. AI 服务架构

优先采用国内可访问 API。

建议统一设计 AI Gateway，避免业务代码直接绑定某一家模型。

```text
Tutor Agent
    ↓
AI Gateway
    ├── chat()
    ├── transcribe()
    ├── synthesize()
    └── vision()
```

当前推荐：

```text
LLM: Qwen
ASR: 国内 ASR / Qwen ASR
TTS: CosyVoice / Qwen TTS
Vision: 预留
```

---

# 6. 模型路由

不要所有任务调用同一个最高规格模型。

建议：

```text
低成本模型
├── 意图分类
├── 学习记录摘要
├── 错误分类
├── mastery 更新辅助
└── 简单短句判断

主力 Flash 模型
├── 日常英语教学
├── 对话
├── 单词
├── 语法
├── 句型
└── 阅读

高能力模型
├── 复杂解释
├── 后续作文点评
├── 高难阅读
└── 特殊情况
```

模型路由器：

```text
ModelRouter
├── light
├── standard
└── advanced
```

业务层不能直接写死具体模型名称。

---

# 7. ASR

V1 需求：

- 英语语音转文本
- 支持短句
- 支持儿童声音
- 响应速度优先
- 中文语音保留能力

V1 暂不要求：

- 音素级发音评分
- IPA 对齐
- 声学模型评分
- 专业考试级 pronunciation score

首版只做：

```text
语音
 ↓
ASR
 ↓
文本
 ↓
LLM 判断：
- 内容是否正确
- 句型是否正确
- 是否能够理解
```

后续再增加专业 pronunciation 模块。

---

# 8. TTS

要求：

- 儿童友好
- 童声优先
- 英文清晰
- 中文自然
- 支持流式播放
- Voice ID 固定
- 同一个 AI 角色长期保持一致声线

优先：

```text
CosyVoice
Qwen TTS
```

英语 Tutor 应有固定角色，例如：

```text
Name: Emma
Voice: child-like female
Style: friendly / energetic / patient
English speed: slightly slow
```

不要每次动态随机换音色。

---

# 9. Tutor Agent

Tutor Agent 是项目核心，不应退化为普通 Chatbot。

错误架构：

```text
孩子输入
 ↓
LLM
 ↓
回答
```

正确架构：

```text
孩子输入
    ↓
Session Manager
    ↓
获取当前课程
    ↓
读取 Student Profile
    ↓
读取 Mastery
    ↓
读取最近 Mistakes
    ↓
Skill Router
    ↓
生成 Teaching Strategy
    ↓
调用 LLM
    ↓
Response Guard / Validator
    ↓
更新 Learning State
    ↓
TTS
```

---

# 10. Tutor Agent 的核心职责

Tutor Agent 至少负责：

```text
1. 当前教学目标
2. 当前课程定位
3. 控制难度
4. 控制一次回答长度
5. 判断是否需要中文提示
6. 决定是否立即纠错
7. 决定是否使用 Socratic 引导
8. 记录错误
9. 更新知识点掌握度
10. 安排复习
11. 判断何时结束本轮
12. 生成儿童友好的表达
```

---

# 11. 教学案例

孩子：

```text
I have two cat.
```

系统识别：

```text
Intent:
conversation

Knowledge Point:
plural_nouns

Detected Problem:
noun plurality

Current Mastery:
0.55
```

Tutor Agent 不应直接：

```text
Wrong. It should be "I have two cats."
```

优先：

```text
Almost! You have two, so should we say "cat" or "cats"?
```

孩子：

```text
Cats!
```

系统：

```text
Attempt = correct_after_hint
plural_nouns mastery += delta
Mistake updated
Review schedule updated
```

AI：

```text
Yes! I have two cats! Great job!
```

---

# 12. Skill Router

推荐目录：

```text
skills/
├── english/
│   ├── conversation/
│   │   └── SKILL.md
│   ├── vocabulary/
│   │   └── SKILL.md
│   ├── grammar/
│   │   └── SKILL.md
│   ├── sentence-pattern/
│   │   └── SKILL.md
│   ├── reading/
│   │   └── SKILL.md
│   └── pep-sync/
│       └── SKILL.md
│
├── common/
│   ├── socratic-tutor/
│   │   └── SKILL.md
│   ├── mistake-review/
│   │   └── SKILL.md
│   ├── daily-review/
│   │   └── SKILL.md
│   ├── study-plan/
│   │   └── SKILL.md
│   └── learning-report/
│       └── SKILL.md
```

V1 不需要加载几十上百个 Skill。

优先控制在：

```text
5～10 个核心 Skill
```

---

# 13. 英语 V1 功能范围

## 必须实现

### 13.1 英语自由对话

- 儿童短句
- 一次 1～2 句话
- 避免长解释
- AI 主动提问
- 支持中文辅助

### 13.2 Vocabulary

- 单词学习
- 看词读音
- 单词解释
- 简短例句
- 单词复习
- 掌握度记录

### 13.3 Sentence Pattern

例如：

```text
My name is ...
I like ...
I have ...
This is ...
I can ...
Can you ...?
```

### 13.4 Grammar

以小学级别为主。

### 13.5 Speaking

```text
AI 提问
 ↓
孩子说
 ↓
ASR
 ↓
判断
 ↓
反馈
```

### 13.6 Daily Review

根据：

```text
Mistake
Mastery
LastPracticed
ReviewSchedule
```

自动生成当天复习。

### 13.7 Learning Record

记录：

- 学习时间
- 新单词
- 已掌握单词
- 弱项
- 错句
- 连续学习天数
- 每日 Session

---

# 14. 后续英语扩展

## V1.1

```text
Phonics
Reading
Listening
```

## V1.2

```text
PEP 教材同步
Unit
Lesson
单元复习
单元测试
```

## V1.3

```text
更精细 pronunciation scoring
角色动画
学习激励
家长周报
```

---

# 15. 语文、数学预留

学科抽象从第一天就存在。

```text
Subject
├── english
├── chinese
└── math
```

配置：

```text
english.enabled = true
chinese.enabled = false
math.enabled = false
```

API：

```text
GET /api/v1/subjects

GET /api/v1/subjects/english
GET /api/v1/subjects/chinese
GET /api/v1/subjects/math
```

数学和语文未开启时返回：

```json
{
  "enabled": false
}
```

禁止在数据库中创建：

```text
EnglishMistake
EnglishProgress
EnglishLesson
```

应设计为通用结构：

```text
Mistake
Progress
Lesson
KnowledgePoint
Mastery
```

通过 `subject_id` 区分。

---

# 16. 推荐数据模型

核心实体：

```text
Student
Subject
Course
Unit
Lesson
KnowledgePoint
Exercise
Attempt
Mistake
Mastery
LearningSession
ReviewTask
VocabularyItem
ConversationSession
Utterance
Device
```

---

## 16.1 Student

```text
id
name
display_name
age_group
grade
preferences
created_at
```

不要在核心业务逻辑中硬编码具体孩子信息。

---

## 16.2 Subject

```text
id
code
name
enabled
```

例如：

```text
english
chinese
math
```

---

## 16.3 KnowledgePoint

```text
id
subject_id
code
name
difficulty
metadata
```

例如：

```text
plural_nouns
be_verbs
greetings
colors
family_members
```

---

## 16.4 Mastery

```text
student_id
knowledge_point_id
score
confidence
attempt_count
correct_count
last_practiced_at
next_review_at
```

建议 `score` 范围：

```text
0.0 ～ 1.0
```

---

## 16.5 Attempt

```text
id
student_id
exercise_id
knowledge_point_id
answer
result
hint_count
created_at
```

结果建议：

```text
correct
correct_after_hint
partially_correct
incorrect
skipped
```

---

## 16.6 Mistake

```text
id
student_id
subject_id
knowledge_point_id
content
mistake_type
occurrence_count
first_seen_at
last_seen_at
resolved
```

---

## 16.7 LearningSession

```text
id
student_id
subject_id
mode
started_at
ended_at
duration
summary
```

mode：

```text
conversation
vocabulary
lesson
review
speaking
reading
```

---

## 16.8 ConversationSession

保存 AI Tutor 对话。

```text
id
student_id
learning_session_id
topic
level
started_at
ended_at
```

---

## 16.9 Utterance

```text
id
conversation_session_id
role
text
audio_url
asr_text
metadata
created_at
```

---

# 17. API 设计

所有客户端必须通过统一 API。

推荐：

## Session

```text
POST /api/v1/session/start
POST /api/v1/session/end
GET  /api/v1/session/{id}
```

## Tutor

```text
POST /api/v1/tutor/message
POST /api/v1/tutor/next
```

## Voice

```text
POST /api/v1/audio/transcribe
POST /api/v1/audio/speech
```

后续可增加：

```text
WS /api/v1/realtime
```

## Student

```text
GET   /api/v1/student/profile
PATCH /api/v1/student/profile
GET   /api/v1/student/progress
```

## Curriculum

```text
GET /api/v1/curriculum/current
GET /api/v1/curriculum/units
GET /api/v1/curriculum/lessons
```

## Review

```text
GET  /api/v1/review/today
POST /api/v1/review/result
```

## Subjects

```text
GET /api/v1/subjects
GET /api/v1/subjects/{subject}
```

---

# 18. Web / PWA

Web 是正式主客户端。

需要支持：

```text
手机
平板
PC
PWA 安装
```

儿童端 UI 原则：

- 大按钮
- 少文字
- 少菜单
- 明确当前任务
- 强视觉反馈
- 不显示模型参数
- 不显示 Prompt
- 不显示 API
- 不显示 Temperature
- 不显示技术设置

典型页面：

```text
首页
英语对话
单词学习
每日复习
学习进度
奖励 / 成就
```

家长设置可以放单独入口。

---

# 19. M5Stack 兼容

M5Stack 是 **兼容终端**，不是主客户端。

优先目标硬件：

```text
M5Stack CoreS3
```

M5Stack 只负责：

```text
Wi-Fi
Mic
Speaker
Button / Touch
基础 UI
Audio upload
Audio playback
Device status
```

M5Stack 不负责：

```text
LLM
Skill
教材
Mastery
数据库
学习策略
Agent
```

设备流程：

```text
IDLE
 ↓
LISTENING
 ↓
UPLOADING
 ↓
THINKING
 ↓
SPEAKING
 ↓
IDLE
```

设备 API：

```text
GET  /api/v1/device/bootstrap
POST /api/v1/device/heartbeat
POST /api/v1/device/event
```

M5Stack 与 Web 应使用同一套：

```text
Tutor API
Audio API
Student API
Session API
```

---

# 20. 后端目录建议

```text
ai-primary-tutor/
│
├── backend/
│   ├── app/
│   │
│   ├── api/
│   │   ├── session.py
│   │   ├── tutor.py
│   │   ├── audio.py
│   │   ├── student.py
│   │   ├── curriculum.py
│   │   ├── review.py
│   │   ├── subjects.py
│   │   └── device.py
│   │
│   ├── agent/
│   │   ├── tutor_agent.py
│   │   ├── skill_router.py
│   │   ├── model_router.py
│   │   ├── context_builder.py
│   │   └── response_validator.py
│   │
│   ├── learning/
│   │   ├── mastery.py
│   │   ├── mistakes.py
│   │   ├── review.py
│   │   └── difficulty.py
│   │
│   ├── subjects/
│   │   ├── english/
│   │   ├── chinese/
│   │   └── math/
│   │
│   ├── services/
│   │   ├── llm.py
│   │   ├── asr.py
│   │   ├── tts.py
│   │   └── vision.py
│   │
│   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── migrations/
│   │
│   └── main.py
│
├── frontend/
│
├── skills/
│
├── curriculum/
│
├── devices/
│   └── m5stack/
│
├── data/
│
├── docker/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# 21. ChinaTextbookStudyFree 的集成策略

不要一开始大规模重构该项目。

建议先：

```text
1. Fork
2. 运行原项目
3. 分析 packages/core
4. 分析 English / PEP 数据结构
5. 分析 Web 课程页面
6. 确认哪些模块直接复用
7. 新增 AI Tutor Backend
```

优先避免：

```text
Fork 后立即全量重写
```

更推荐：

```text
Existing Learning UI
         +
AI Tutor Extension
```

长期项目定位可理解为：

> ChinaTextbookStudyFree + AI Voice Tutor Enhancement

---

# 22. 完整英语语音交互数据流

```text
① 用户按麦克风
       ↓
② Web / M5Stack 采集音频
       ↓
③ POST /audio/transcribe
       ↓
④ ASR
       ↓
⑤ 得到文本
       ↓
⑥ Session Manager
       ↓
⑦ Context Builder
       │
       ├── Student Profile
       ├── Current Lesson
       ├── Mastery
       ├── Recent Mistakes
       └── Recent Conversation
       ↓
⑧ Skill Router
       ↓
⑨ Tutor Agent
       ↓
⑩ Model Router
       ↓
⑪ Qwen
       ↓
⑫ Response Validator
       ↓
⑬ Learning Engine 更新状态
       ↓
⑭ TTS
       ↓
⑮ Web / M5Stack 播放
```

---

# 23. V1 里程碑

## Milestone 0 — 基础工程

完成：

- Ubuntu 部署
- Docker Compose
- Caddy HTTPS
- FastAPI Skeleton
- SQLite
- Web Skeleton
- `.env` 管理

验收：

```text
Web 可以访问
API health check 正常
数据库可写
```

---

## Milestone 1 — 最小语音闭环

完成：

```text
录音
 ↓
ASR
 ↓
Qwen
 ↓
TTS
 ↓
播放
```

此阶段先不考虑学习状态。

验收：

> 孩子可以和 AI 连续完成基本英语问答。

---

## Milestone 2 — Tutor Agent

增加：

- Session
- Student Profile
- Skill Router
- Socratic Teaching
- 对话长度控制
- 年龄适配

验收：

> AI 行为从 Chatbot 转为 Tutor。

---

## Milestone 3 — Learning Core

增加：

- KnowledgePoint
- Attempt
- Mistake
- Mastery
- ReviewTask

验收：

> 系统可以知道“孩子会什么、不会什么”。

---

## Milestone 4 — Vocabulary / Sentence / Daily Review

增加：

```text
Vocabulary
Sentence Pattern
Grammar
Daily Review
```

验收：

> 系统能够形成每日学习闭环。

---

## Milestone 5 — ChinaTextbookStudyFree 集成

增加：

- PEP Curriculum
- Unit / Lesson
- 当前教材进度
- 学习平台 UI

验收：

> AI Tutor 能知道孩子正在学习哪一册、哪一单元。

---

## Milestone 6 — M5Stack Compatibility

实现：

```text
M5Stack
 ↓
录音
 ↓
同一套 Tutor API
 ↓
TTS Playback
```

验收：

> M5Stack 与 Web 共用同一个学生状态和会话体系。

---

# 24. V1 验收标准

V1 至少达到：

1. Web/PWA 正常运行
2. 国内服务器可稳定部署
3. 不依赖 OpenAI
4. 孩子可以语音输入
5. AI 可以童声回复
6. AI 回答符合小学生语言水平
7. AI 不只是直接报答案
8. 可以记录错误
9. 可以维护基础掌握度
10. 可以生成每日复习
11. PEP 英语教材结构可以接入
12. 语文、数学结构已预留
13. M5Stack 可通过 API 接入
14. Web 和 M5Stack 共享同一后端状态

---

# 25. 关键设计原则

## 25.1 AI 模型不是核心资产

Qwen 后续可以替换。

必须通过 AI Gateway 隔离。

---

## 25.2 学习状态才是核心资产

长期真正重要的是：

```text
孩子会什么
孩子不会什么
哪些词反复错
哪些句型不熟
当前学到哪里
最近复习什么
什么时候应该复习
需要多少提示
适合什么难度
喜欢什么话题
```

---

## 25.3 Tutor 与 Chatbot 必须分开

Chatbot：

```text
Question → Answer
```

Tutor：

```text
Observe
 ↓
Diagnose
 ↓
Choose Strategy
 ↓
Guide
 ↓
Evaluate
 ↓
Record
 ↓
Review
```

---

## 25.4 客户端必须无状态化

Web、M5Stack、未来 Android App 都只是客户端。

核心状态全部在 Server。

---

## 25.5 学科必须抽象

不要把系统写死成英语专用架构。

V1 产品只开启英语，但基础模型必须支持：

```text
English
Chinese
Math
```

---

# 26. 未来扩展

## 语文

可增加：

```text
拼音
生字
听写
课文朗读
阅读理解
作文
统编教材
```

---

## 数学

可增加：

```text
口算
应用题
知识点
错题
Socratic 解题
自适应题目
人教教材
```

---

## 多端

可增加：

```text
Android App
iOS App
M5Stack
智能音箱
树莓派
桌面端
```

所有客户端继续调用统一 Tutor API。

---

# 27. 当前建议的 V1 最终技术栈

```text
Server:
Ubuntu 24.04 LTS
2C4G
40GB SSD
No GPU

Deployment:
Docker
Docker Compose
Caddy

Backend:
Python
FastAPI

Database:
SQLite

Frontend:
Web / PWA
参考 ChinaTextbookStudyFree + mini-classroom

AI:
Qwen
国内 ASR
CosyVoice / Qwen TTS

Teaching:
Tutor Agent
Skill Router
Learning Engine

Skills:
参考 hermes-edu-skills
不部署 Hermes

Adaptive Teaching:
参考 Kid Tutor

Curriculum:
重点参考 / 复用 ChinaTextbookStudyFree PEP English

Hardware Compatibility:
M5Stack CoreS3
```

---

# 28. 一句话项目定义

> **基于 ChinaTextbookStudyFree 的小学学习框架，结合 hermes-edu-skills 的教学策略和 Kid Tutor 的自适应教学逻辑，构建以 Web/PWA 为主端、M5Stack 为兼容终端、Qwen + 国内 ASR + 童声 TTS 为 AI 能力层的长期小学 AI 家教系统；V1 只实现英语，语文与数学保留完整扩展接口。**

---

# 29. 下一步建议

开发应从以下顺序开始：

```text
1. Fork / 分析 ChinaTextbookStudyFree
2. 搭建 FastAPI + SQLite 后端
3. 接通 ASR → Qwen → TTS 最小语音闭环
4. 实现 Tutor Agent
5. 实现 Skill Router
6. 实现 Student / Mastery / Mistake
7. 接入 PEP Curriculum
8. 完成英语学习 UI
9. 实现 Daily Review
10. 最后做 M5Stack Compatibility
```

不要优先开发：

```text
语文
数学
OCR
RAG
复杂家长后台
复杂硬件 UI
本地模型
```

先保证英语 Tutor 的核心闭环真实可用。
