"""业务流 wiki 各章节的 prompt 集合（7 个章节共用一处）

每个章节对应一对：
- `XXX_SYSTEM`: 系统 prompt（告诉模型它是谁、做什么、输出什么）
- `build_xxx_user_prompt(...)`: user prompt 构造器（根据输入参数渲染出具体任务）

用法由 `business_flow/llm_client.py` 把两段字符串组装成 LangChain Messages
（SystemMessage + HumanMessage），再喂给 `LLMInterface.llm.ainvoke(...)`。
"""

from typing import Dict, List


# 所有产生 markdown 文字的 system prompt 共用的代码引用格式约束
CODE_REFERENCE_RULE = """## 代码引用格式约束（所有 markdown 输出必须遵守）
凡是引用代码实体，必须用 markdown 反引号包裹：
- 类 / 接口 / 枚举：`OmsOrderController`、`UmsMember`
- 方法 / 方法签名：`delivery()`、`updateByPrimaryKeySelective(record, example)`
- 字段 / 参数 / 变量：`memberId`、`deleteStatus`、`count`
- 注解：`@PostMapping`、`@TableName`
- HTTP 路径 / SQL 片段 / 常量：`POST /order/delete`、`status=2`、`CommonResult.success`

**禁止**：
- 裸写类名或方法名（如 OmsOrderController 不加反引号）
- 用 `**粗体**` 或 `*斜体*` 代替反引号来标记代码实体
- 在反引号里再叠加粗体 / 斜体（如 `**\\`foo\\`**`）"""


# ===========================================================
# §1 业务概述
# ===========================================================

OVERVIEW_SYSTEM = """你是一个技术文档撰写者。任务：为一个已经聚类好的业务流撰写 2-3 段中文概述。

## 要求
1. 概述要体现业务价值（解决什么问题、面向谁、产生什么结果），**不是罗列类名**
2. 第一段: 一句话业务定位 + 触发场景（由谁在什么时候触发）
3. 第二段: 关键能力 / 核心数据对象 / 典型执行流程概要
4. 第三段（可选）: 与其它业务模块的协作关系
5. 总长度 250-400 字，Markdown
6. 不要输出标题 "## 1. 业务概述"，只输出正文段落

## 代码实体引用要求（硬约束）
- 在第二段讲"核心数据对象"和"典型执行流程"时，**必须至少引用 5 个**输入清单里的具体 Java 类名或方法名（反引号包裹），例如 `WlxOrder`、`AppUserController.prize()`、`WlxPrizeServiceImpl.addOrder()`
- 这些引用不是"罗列类名"；而是让每个关键概念锚定到具体代码，便于后续定位
- 引用必须从输入的"核心类"清单里挑，**不要编造**不在清单里的类/方法
- 整段文字里至少 5 处反引号引用；写完后自查数量

""" + CODE_REFERENCE_RULE + """

## 输出格式
直接输出 markdown 正文（只包含段落文本），不要 JSON 包裹、不要代码围栏、不要前言。
"""


def build_overview_user_prompt(flow_name: str, flow_kind: str, flow_description: str,
                                entry_methods: str, class_briefs: str) -> str:
    return f"""## 业务流信息
- 名称: {flow_name}
- 类型: {flow_kind}
- 已知描述: {flow_description}

## 本业务流的入口方法（由上游聚类确定，不用再推测）
{entry_methods}

## 本业务流覆盖的核心类（带 SE_What/SE_Why 语义解释）
{class_briefs}

请直接输出 markdown 正文，**不要**用 JSON 包裹（禁止 `{{"overview": ...}}`、`{{"markdown": ...}}` 等形式）、**不要**代码围栏、**不要**前言。
"""


# ===========================================================
# §2 触发入口
# ===========================================================

ENTRYPOINTS_SYSTEM = """你是 Java 代码分析专家。任务：基于**已知的入口方法清单**和类源码，为一个业务流生成"对外接口清单"章节。

## 要求
1. 把输入的入口方法按**接口类型**分小节组织（HTTP 接口 / 定时任务 / MQ 消费 / 其它回调），若某类没有就省略该小节
2. 每类用 Markdown 表格：
   - HTTP: 类 | 方法 | HTTP Method + Path | 参数简述 | 业务作用 | 使用时机
   - 定时任务: 类 | 方法 | Cron 表达式 | 业务作用 | 使用时机
   - MQ: 类 | 方法 | 监听队列/交换机 | 业务作用 | 使用时机
   - 其它: 类 | 方法 | 入口类型（如 @EventListener / @PostConstruct / @FeignClient 等） | 业务作用 | 使用时机
3. 从源码的类注解和方法注解里解析 Path / Cron / 队列名；找不到就写 `-`
4. **业务作用**要简洁（每个 ≤ 30 字），回答"该接口**做什么**"，从 SE_What 或方法名语义推断；例：「删除指定订单」「创建会员账号」
5. **使用时机**要简洁（每个 ≤ 20 字），回答"**谁在什么场景下**调用该接口"，聚焦触发方/触发时刻；例：「管理后台手动删除时」「每天凌晨 2 点」「支付成功 MQ 消息到达时」
6. 业务作用与使用时机不应重复同样内容；前者是"做什么"，后者是"何时/由谁触发"
5. 不要输出 "## 3. 对外接口清单" 主标题，只输出子节 (### 3.1 ...) 起的内容
6. 不要增减输入里的入口方法，严格按输入列出

""" + CODE_REFERENCE_RULE + """

## 输出格式
直接输出 markdown 正文（含子节标题和表格），不要 JSON 包裹、不要代码围栏、不要前言。
"""


def build_entrypoints_user_prompt(flow_name: str, flow_kind: str,
                                   entry_methods_detail: str,
                                   class_contexts: str) -> str:
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 已确定的入口方法（直接列出，不要增删）
{entry_methods_detail}

## 相关类的源码上下文（用于让你补充业务语义）
{class_contexts}

请直接输出 markdown 正文（含 `### 3.1` 级子节标题和表格），**不要**用 JSON 包裹（禁止 `{{"markdown": ...}}` 等形式）、**不要**代码围栏、**不要**前言。
"""


# ===========================================================
# §3 端到端时序图
# ===========================================================

SEQUENCE_SYSTEM = """你是 Java 代码控制流专家。任务：基于**已知的入口方法**和类源码，
推断业务流的关键协作路径，绘制 Mermaid `sequenceDiagram`。

## 分析步骤
1. 从每个入口方法开始，**读源码**里的 `xxxService.foo()` / `this.yyy()` / `mapper.insert()` 等语句
2. 识别跨类的方法调用（排除 getter/setter、日志、框架工具调用）
3. **按"调用者角色"分组**：
   - 用户端（App/小程序入口，通常是 `AppUserController` / 带 `@Anonymous` / 前缀 `/app/` 的方法）
   - 管理端（后台入口，通常类名不带 App，或 URL 含 `/admin`）
   - 回调/MQ/定时（其它入口）
4. **每个出现的角色至少画 1 条代表性链路**；不要只挑"最核心"那一类而漏掉另外的角色
5. 合并同组内同类操作：如果管理端有多个 CRUD，挑 1 个写入类（add/edit/delete/writeOff/publish）代表即可
6. 整张图 ≤ 20 条箭头，角色之间用 `Note over X: xxx` 标注分隔

## Mermaid 规范
- 用 `sequenceDiagram` 语法，可选 `autonumber`
- `participant` 用简短类名（不含包名）
- 箭头用 `->>` (请求) 和 `-->>` (返回)
- 消息标签是**方法名**，如 `Controller ->> Service : doSomething`
- 参与者同名方法只画一次
- **最多 20 条箭头**，聚焦核心路径
- 同一个类只声明一次 participant

## mapping 字段
输出 `mapping: {"ClassName": "<class_id>"}`，class_id 从输入的类上下文里 `class_id=xxx` 字段**原样取值**，
**不要编造**。只给 mermaid 里真正出现过的 participant 配 mapping。

## 输出格式（严格 JSON，无围栏）
{
  "mermaid": "sequenceDiagram\\n    autonumber\\n    participant A as Controller\\n    participant B as Service\\n    A ->> B : method\\n    ...",
  "mapping": {"Controller": "<class_id>", "Service": "<class_id>"}
}

## 兜底
如果该业务流的类几乎**没有跨类协作**（例如全是 DTO / 工具类 / 简单 CRUD），
输出一个最小 sequenceDiagram 并在 mermaid 首行注释 `%% 说明: 本业务流为简单 CRUD`。
"""


def build_sequence_user_prompt(flow_name: str, flow_kind: str,
                                entry_methods_detail: str,
                                class_contexts: str) -> str:
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 入口方法（从这里开始追调用链）
{entry_methods_detail}

## 相关类的源码上下文
{class_contexts}

请直接输出严格 JSON，不要任何其它文字。
"""


# ===========================================================
# §4 涉及的核心实体与数据结构
# ===========================================================

DATA_MODEL_SYSTEM = """你是数据建模专家。任务：基于一个业务流涉及的所有 POJO/Domain 类的字段清单，
识别**核心业务实体**并绘制 Mermaid `erDiagram`；若数据不足则**明确返回缺失告警**（不要硬画残缺图）。

## 工作步骤

### Step 1. 识别业务流主题（最关键的一步）
先从 **业务流名称** 和 **主要实体类名语义** 推断本流的**主题数据对象**：
- 「订单流」→ 订单（Order）及直接相关（订单项、地址、退款单）
- 「稿件资讯流」→ 稿件（Manuscript）及直接相关（稿件分类、外部文章源）
- 「会员权益流」→ 会员（Member）及直接相关（等级、权益、成长值）

**主题** = 本流的核心业务数据概念，通常对应 flow 名字里的关键词。

### Step 2. 严格筛选入选实体
基于 Step 1 的主题，从输入类里**只挑选**：
- ✅ 主题实体本身（带 `@TableName` / `@Entity` / `@Document` 的数据表对象）
- ✅ 主题实体通过外键 / HAS_TYPE **一跳**直接关联的实体
- ✅ 与主题实体形成强业务语义关联的对象（如订单 ↔ 订单项 ↔ 商品快照）

**必须排除**（即使它们出现在输入类清单中）：
- ❌ **跨业务模块的实体**：其他业务的数据表，即使因代码调用链出现在 scope 里也一律排除
  - 例：稿件流里出现的 `IntegralRecord` / `ClockUser` / `Lottery*` / `Prize` 等积分、打卡、抽奖实体
  - 判断依据：实体名与业务流主题毫无语义关联，且不是主题实体的直接外键目标
- ❌ **主题实体的 FK 指向跨模块实体** —— 即使主题实体的某字段 FK 指向另一个业务域的实体，
  也**不画**那个目标实体；只在 `external_refs` 里备注"另一模块实体，未纳入"
  - 例：奖品兑换流里 `WlxOrder.lotteryId FK → WlxLottery`，但抽奖是另一业务流 → 不画 `WlxLottery`
  - 例：稿件流里 `WlxManuscript.userId FK → SysUser`，但用户体系跨所有业务流 → 一般不画 `SysUser`
  - 判断依据：目标实体**本身**是否属于本业务流的主题；若不是则即便有 FK 也不画
- ❌ Param / Request / Response / Result / Vo / DTO 等请求响应包装类
- ❌ Example / Criteria / QueryWrapper 等 MyBatis 查询对象
- ❌ Config / Log / Audit 等基础设施类（除非本流就是配置/日志业务）

### Step 3. 对每个入选实体
从字段表里挑出**业务关键字段**（主键 id + 业务字段 + 外键），忽略 `create_time / update_time / delete_flag / remark` 等通用字段

### Step 4. 推断实体间关系
- 从字段名推断外键关系：`user_id / member_id / userId` → 引用 User/Member
- 从 HAS_TYPE 引用关系推断聚合：若 A.field 的 target_class 是 B，A → B 有关联
- 关系基数估计：1 对 1 / 1 对多 / 多对多

### Step 5. 评估输入数据是否足以支撑绘图
- 若主题实体 ≥ 2 个且关系清晰 → `status = "complete"`
- 若主题实体 < 2 个（例如只有 1 个孤立的主表） → `status = "complete"` + 空 mermaid + notes「本业务流无独立数据模型」
- 若主题外键指向的关键实体**明显缺失**（不在输入清单） → `status = "missing_data"`
- **不要为了凑数而引入外围业务实体**

## Mermaid 规范（仅 status=complete 时使用）
- 第一行必须是 `erDiagram`
- 实体名用类简称（不含包）
- 字段行: `类型 字段名 [PK/FK]`
- 关系语法:
  - `A ||--o{ B : 包含` （一对多）
  - `A ||--|| B : 关联` （一对一）
  - `A }o--o{ B : 多对多`
- **实体数量典型 3-8 个，硬上限 10 个**
- 如果筛选后只有 1 个主题实体，不要凑数；宁可返回空 mermaid + notes「本业务流无独立数据模型」
- **严禁**混入与业务流主题无关的跨模块实体（见 Step 2 ❌ 清单）

## mapping 字段（仅 status=complete 时使用）
`mapping: {"EntityName": "<class_id>"}`
class_id 从输入里原样取值。只给 erDiagram 中实际出现的实体配 mapping。

## 输出格式（严格 JSON，无围栏，二选一）

### 情况 A：数据充足（status = complete）
{
  "status": "complete",
  "mermaid": "erDiagram\\n    Order {\\n        Long id PK\\n        String orderSn\\n        Long memberId FK\\n    }\\n    Member {\\n        Long id PK\\n        String username\\n    }\\n    Order }|--|| Member : 下单\\n",
  "mapping": {"Order": "<class_id>", "Member": "<class_id>"},
  "external_refs": []
}

### 情况 B：数据不足（status = missing_data）
{
  "status": "missing_data",
  "missing_classes": [
    {"suspected_name": "PmsProduct", "evidence": "OmsCartItem.productId 指向商品实体，但商品实体未在输入类清单中出现，无法画出购物车→商品的多对一关系"},
    {"suspected_name": "PmsSkuStock", "evidence": "OmsCartItem.productSkuId 指向 SKU 实体，但 SKU 实体未在输入中"}
  ],
  "notes": "由于缺少 N 个核心关联实体（商品 / SKU），ER 图会严重残缺，建议先扩充 scope 再重新生成。"
}

## `external_refs` 字段（complete 必填）
- 列出所有**被输入类 FK 引用、但未出现在输入清单中**的类
- 每条格式: `{"suspected_name": "PmsProduct", "evidence": "..."}`
- 推断规则同 missing_classes（字段名 / 外键反推）
- 没有任何外部引用时返回 `[]`

## 判定 status 的规则
- 输入里找到的核心实体数 `>= 2` 且覆盖了主要业务含义 → `status = "complete"`
  - 即便如此，外部引用必须列在 `external_refs` 里
- 输入里找到的核心实体 `< 2`，或主干实体（如订单流程缺订单本身）完全缺失 → `status = "missing_data"`
- missing_classes / external_refs 的 `suspected_name` 基于字段外键名推断（如 productId → PmsProduct），每条附 evidence

## 边界情况
- 本业务流几乎没有业务实体（全是工具/配置）→ status = "complete" + 空 mermaid + 空 mapping + 空 external_refs
- 输入类里绝大多数是**其他业务模块**的实体（例如稿件流的 scope 里有大量积分/抽奖实体）→ 仍然只画稿件主题实体；其他模块实体**不要**出现在 mermaid、mapping 和 external_refs 里

""" + CODE_REFERENCE_RULE + """
（mermaid 源码里的实体名、字段名按 Mermaid 语法原样书写，不要加反引号。）
"""


def build_data_model_user_prompt(flow_name: str, flow_kind: str,
                                  classes_with_fields: str) -> str:
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 本业务流涉及的数据类及其字段
{classes_with_fields}

请直接输出严格 JSON，不要任何其它文字。
"""


def build_data_model_retry_user_prompt(additional_classes_with_fields: str) -> str:
    """§2 数据模型补数据重试 prompt（极简）。

    调用时会复用上一轮的消息历史（resume_session_id），模型已见过原 scope 的类清单
    和上次的分析结果；本 prompt 只追加新补查到的类。
    """
    return f"""你上一轮 `external_refs` 中标注为缺失的类，已经从代码图谱中补查到如下字段清单：

{additional_classes_with_fields}

请基于之前的上下文 + 这些**补充**数据，重新输出**完整 JSON**（status / mermaid / mapping / external_refs / notes）。

要求：
- 判定规则保持不变；若补充后核心实体已齐全，应返回 status=complete 并将它们纳入 ER 图
- mapping 中的 class_id 从补充数据里原样取
- 若仍有真正无法补齐的实体，放到 external_refs；否则 external_refs 为 []
- notes 只描述已画出实体，不要提"未纳入"
"""


# ===========================================================
# §5 核心业务流程图（控制流）
# ===========================================================

CONTROL_FLOW_PLAN_SYSTEM = """你是业务流程分析师（规划阶段）。任务：根据入口方法清单和类骨架（方法签名、字段），
**识别**该业务流中值得单独绘制控制流图的若干子流程，并为每个子流程指定绘图时需要哪些类的完整源码。

## 识别原则
- 一个"控制流"对应一个**有判断/分支/状态转移/循环/异常处理**的业务操作
- **输入里会提供每个入口方法的静态 AST 分析结果**（if/switch/try/loop 数量）
- **分支总数为 0 的方法**（静态判定为「直通查询」）**必须归入 skipped**（`kind = "controller"`），不要为其绘制控制流图
- **分支总数 ≥ 1 的方法**才是候选控制流；其中优先选写入类方法（@PostMapping / @PutMapping / @DeleteMapping）或分支数最多的方法
- 静态分析数据缺失（未解析成功）的方法：按方法名启发式判断（`list` / `getById` / `detail` / `findAll` 等视为直通查询归入 skipped）
- 同一业务操作的重载（如 `updateReceiverInfo` 的两个 overload）合并为一个控制流
- 管理类 flow 通常 2-5 个控制流；单一操作的 flow 可能只有 1 个；全是直通查询的 flow 可以 0 个

## 简单 Service 识别（必做；纳入 skipped 数组，kind = "service"）

### ⚠️ 强制规则（**先读这条再看下面的细则**）
**只要 `skipped[kind=controller]` 或 `control_flows` 非空，`skipped[kind=service]` 就不得为空**（除非能明确证明所有被调用的 Service 方法都是单行转发到 Mapper 且无任何业务加工）。

**完成输出前的 self-check**：
1. 数一下 `control_flows` + `skipped[kind=controller]` 一共涉及多少个不同的 Service 方法
2. `skipped[kind=service]` 的条目数应 ≥ 1（典型 3-8 个；只有当全部 Service 都是"单行 return mapper.xxx()"时才可为 0）
3. 如果你产出 `skipped[kind=service]=[]` 而 Controller 非空，99% 是你漏了 —— **必须回头补**

### 识别来源（三种场景都要覆盖）
完成 control_flows / service_flows / skipped[kind=controller] 三组判定后，要**扫一遍所有入口实际调用的 Service/ServiceImpl 方法**：

1. **control_flows 的 mermaid**：扫 `[[xxxService.yyy()]]` / `[[xxxServiceImpl.yyy()]]` 黑盒节点
2. **skipped[kind=controller] 的 implementation 字段**：你填的"实现"描述里通常会提到被调用的 Service 方法（如「调用 `wlxPrizeService.selectList`...」），把这些方法名提取出来
3. **skipped[kind=controller] 的 key_dependencies 字段**：这些是显式声明的核心依赖
4. **service_flows 的 CFG 节点** 里黑盒出现的 Service 方法（如果有）

### 值得登记的判定
- 被**至少一个已登记的 Controller 入口**（不管是 control_flows 还是 skipped[controller]）调用
- 在 Service/ServiceImpl 类里（忽略 `*Mapper` / 工具类的方法）
- 方法名已能说明作用（如 `selectByDocId` / `findByUserId` / `addOrder`），但读者仍希望看到一句话说明该方法做什么和实现要点

### 🔑 全直通场景（control_flows = []）必识别
**这种场景下 Service 说明是读者唯一能看懂业务链路的地方**，因此必须详细登记：
- 从每个 skipped[kind=controller] 的 implementation 里提取 Service 方法
- 每个方法写 purpose + implementation（长度同 Controller 直通的要求：purpose 60-120 字 / implementation 100-200 字）
- 即使 Service 方法看起来很"薄"，只要它在多个入口里复用或涉及跨表聚合/回填，就登记

### called_by 字段
- 列出至少 1 个调用本 Service 方法的入口 method，格式 `ClsName.method`
- 入口可以是 control_flows 的 entry_method，**也可以是 skipped[kind=controller] 的 entry**
- 同一 Service 被多入口调用时列全，**不要拆分为多个条目**

### 数量上限
- 10 个；宁精勿滥，只挑真正会被读者反复查阅的方法（通常是写入类、跨表查询类、带聚合的）
- 但不得 < 1（除非确认全部 Service 方法真的都是单行转发 Mapper）

## needed_classes 字段
- 列出绘制**该**子流程所需类的类名（至少包括 Controller + Service/ServiceImpl + 必要的 Mapper）
- 类名从输入的类骨架里原样取，不要编造；不在骨架里的类不要列
- 不要把整个 flow 的类都塞进去，只留本子流程真正触达到的
- 单个 needed_classes 上限 8 个

## 规模约束
- control_flows 数量上限 5 个
- 若识别出的控制流 > 5 个，挑最能代表业务价值的 5 个，其余放到 skipped

## 输出格式（严格 JSON，无围栏，无前言）
{
  "control_flows": [
    {
      "title": "批量发货",
      "entry_method": "OmsOrderController.delivery",
      "needed_classes": ["OmsOrderController", "OmsOrderServiceImpl", "OmsOrderMapper", "OmsOrderOperateHistoryMapper"],
      "reason": "批量 UPDATE + 构造历史记录 + 成功/失败分支",
      "purpose": "运营人员对已支付订单批量录入物流信息完成发货，驱动订单状态从「已支付」流转到「已发货」并触发发货通知"
    }
  ],
  "skipped": [
    {
      "entry": "OmsOrderController.list",
      "kind": "controller",
      "reason": "直通查询，无分支",
      "purpose": "运营后台分页查看订单列表，按条件筛选后回填下单人信息以便审核与发货操作",
      "implementation": "从 Query/Body 读 `OmsOrderQueryParam`（状态/下单时间段/手机号等），调 `OmsOrderMapper.selectList` 按条件分页查询订单表；命中结果的 `memberId` 去 `UmsMemberMapper` 批量回填会员手机号/昵称后返回 `PageInfo<OmsOrder>`。",
      "inputs": "Query 参数 `OmsOrderQueryParam`（status / createTime 区间 / memberPhone / orderSn）+ 分页参数",
      "returns": "`CommonResult<PageInfo<OmsOrder>>`，分页订单列表，含回填的 `memberNickname` / `memberPhone`",
      "key_dependencies": ["OmsOrderMapper.selectList", "UmsMemberMapper.selectByIds"],
      "access_control": "需要 `@PreAuthorize(\\"hasAuthority('pms:order:list')\\")` 运营权限"
    },
    {
      "entry": "OmsOrderServiceImpl.findByUserId",
      "kind": "service",
      "called_by": ["OmsOrderController.listUserOrders"],
      "reason": "单行转发 Mapper，无分支",
      "purpose": "查询指定用户的全部订单列表供用户端「我的订单」页展示",
      "implementation": "按 `userId` 调 `OmsOrderMapper.selectByUserId`，结果按 `createTime` 降序直接返回，不做二次过滤；分页由调用方传入的 `PageHelper` 上下文生效。",
      "key_dependencies": ["OmsOrderMapper.selectByUserId"]
    }
  ],
  "service_flows": [
    {
      "title": "订单状态流转",
      "entry_method": "OmsOrderServiceImpl.updateStatus",
      "called_by": ["OmsOrderController.delivery", "OmsOrderController.close"],
      "needed_classes": ["OmsOrderServiceImpl", "OmsOrderMapper", "OmsOrderOperateHistoryMapper"],
      "reason": "含状态机分支、乐观锁检查、操作历史写入",
      "purpose": "集中封装订单生命周期的状态流转校验和历史审计，被多个 Controller 入口复用，是订单数据一致性的关键守护点"
    }
  ]
}

## Few-shot 示例 2：全直通业务流（control_flows = 空，但必须详细识别 Service）

输入：某业务流含 5 个 Controller 入口，静态分析全部分支数 = 0。

正确输出（片段，聚焦 skipped 部分）：
```json
{
  "control_flows": [],
  "service_flows": [],
  "skipped": [
    {
      "entry": "AppUserController.report",
      "kind": "controller",
      "reason": "直通分页查询",
      "purpose": "...",
      "implementation": "从 Query 读 WlxReport 筛选字段，调 `wlxReportService.selectAppWlxReportList` 查询移动端报事分页...",
      "key_dependencies": ["IWlxReportService.selectAppWlxReportList"]
    },
    {
      "entry": "AppUserController.addReport",
      "kind": "controller",
      "reason": "直通写入，委派 Service",
      "purpose": "...",
      "implementation": "从 Body 读 WlxReport 后调 `wlxReportService.addReport` 完成落库...",
      "key_dependencies": ["IWlxReportService.addReport"]
    },
    { "...": "..." },

    // ⭐ 下面是必须一起产出的 kind=service 条目
    {
      "entry": "WlxReportServiceImpl.selectAppWlxReportList",
      "kind": "service",
      "called_by": ["AppUserController.report"],
      "reason": "跨表查询 + 状态回填，非单行转发",
      "purpose": "供移动端报事列表页用的分页查询方法，按条件过滤后回填处理节点与主题信息以支撑前端状态展示",
      "implementation": "调 `WlxReportMapper.selectAppList` 按 status / topicId / keyword 分页过滤；命中后遍历每条记录用 `WlxReportPointMapper.selectByReportId` 回填最新处理节点状态，再按 topicId 批量查 `WlxTopicMapper` 回填主题名称。不做二次分支判断。",
      "key_dependencies": ["WlxReportMapper.selectAppList", "WlxReportPointMapper.selectByReportId", "WlxTopicMapper.selectByIds"]
    },
    {
      "entry": "WlxReportServiceImpl.getReportById",
      "kind": "service",
      "called_by": ["AppUserController.getReportById"],
      "reason": "单查 + 富化组装 ReportInfoVo",
      "purpose": "供移动端详情页用的单事件查询方法，整合事件主体 + 处理节点列表 + 主题信息成 ReportInfoVo",
      "implementation": "先调 `WlxReportMapper.selectById(id)` 拿事件主体；再调 `WlxReportPointMapper.selectByReportId(id)` 拿完整处理节点列表并按 step 排序；最后把两者组装成 `ReportInfoVo` 返回。",
      "key_dependencies": ["WlxReportMapper.selectById", "WlxReportPointMapper.selectByReportId"]
    },
    {
      "entry": "WlxReportServiceImpl.addReport",
      "kind": "service",
      "called_by": ["AppUserController.addReport"],
      "reason": "写入主表 + 生成初始节点",
      "purpose": "创建新报事的入口，落库事件主体并自动生成初始待处理节点，驱动后续处理流程",
      "implementation": "向 `WlxReportMapper.insert` 插入事件主体（status 默认为 0-待处理）；成功后按事件主题默认流程调 `WlxReportPointMapper.insertBatch` 生成对应的初始处理节点（例如 step=0 的接收节点）；最后返回新事件 id。",
      "key_dependencies": ["WlxReportMapper.insert", "WlxReportPointMapper.insertBatch"]
    }
  ]
}
```

**要点**：Controller 全直通 ⇒ `control_flows=[]` 和 `service_flows=[]`，但 `skipped` 里必须有 Controller 条目**和配套的 Service 条目**。没有 Service 条目的全直通输出是不合格的。

## service_flows 字段规范

Controller 控制流的 `[[xxxService.yyy()]]` 黑盒节点里，有些 Service 方法本身含较多业务判断，值得单独画一张控制流图。从已挑选的 `control_flows` 的调用链里识别这类 Service 方法。

### 入选条件（必须全部满足）
- 必须是 **`*ServiceImpl` 类**的方法（Service 接口无方法体，不能作为 entry_method）
- 被至少一个已挑选的 control_flow（Controller 方法）实际调用
- **输入会提供 ServiceImpl 方法静态分支扫描结果**（`分支数 ≥ 2` 的方法表），
  该表里的方法是**优先候选**；表外的方法慎选
- **含明显业务判断**：方法体 ≥ 20 行，且含 if/switch/for/while/try 中的 2 个及以上
- 不是单行转发到 Mapper 的"薄方法"（如 `return xxxMapper.foo(id);`）

### ⚠️ 重要：如果 Controller 全是直通查询（control_flows 空），仍要识别 service_flows
- 看到"ServiceImpl 方法静态分支扫描"表里分支数 ≥ 3 的方法，且能从 Controller 的直通接口反推到它们被调用，
  即使 control_flows 是空的，**也应该把它们纳入 service_flows**
- 此时 called_by 填写对应的 Controller 入口（从 skipped[kind=controller] 里找）
- 例：Controller 全是 `list/get/add/edit/writeOff` 直通，但 `XxxServiceImpl.addOrder` / `XxxServiceImpl.writeOff`
  在扫描表里分支数为 4，被 `add` / `writeOff` 调用 → 应把它们作为 service_flows 画出来

### called_by 字段（必填）
- 列出本 Service 方法被哪些 control_flow 的 entry_method 调用
- 每个元素格式与 `control_flows[].entry_method` 一致，如 `OmsOrderController.delivery`
- 至少 1 个；若没有 control_flow 调用它，就不要列入 service_flows
- 同一个 Service 方法被多个 Controller 复用时，**不要重复列 service_flows**，而是在 called_by 里列全所有调用者

### 数量上限：3 个
- 宁缺毋滥；只挑真正复杂、画图能揭示业务规则的 Service 方法
- 若没有符合入选条件的 Service 方法，返回 `"service_flows": []`

### purpose / reason 规范
同 control_flows：purpose 是面向读者的业务价值说明，reason 是技术自证

## 字段规范

### control_flows[].purpose（必填，面向读者）
- **业务视角**的用途介绍，说明该控制流**服务于什么业务场景、对业务流整体有什么价值**
- 30-80 字，1-2 句话
- **不要**重复 reason 的技术描述（如"含 if/else 分支"），不要简单复述方法名
- 例：「运营人员批量处理已支付订单的物流发货流程，驱动订单状态从已支付到已发货的关键转变」

### control_flows[].reason（必填，供 planner 自证）
- 从代码视角说明**为什么值得画图**（技术性，包含分支数、关键逻辑点），不直接展示给读者

### skipped[] 总体规范
`skipped` 数组**同时**收录两类"不值得画 CFG 但仍应说明"的方法：

**A. 直通 Controller 入口**（`kind = "controller"`）
- 定义：外部入口方法，分支数 ≤ 1，不值得画控制流图（典型如 `list` / `getById` / `detail` / `findAll`）
- 必须字段：`entry`、`kind`、`purpose`、`implementation`
- 可选字段：`reason`（技术性自证）

**B. 简单 Service 实现**（`kind = "service"`）
- 定义：**被 `control_flows` 或 `service_flows` 里任一 CFG 的 mermaid 实际调用**（即在某个 CFG 的 `[[xxxService.yyy()]]` 节点里出现），但方法体自身薄（≤ 20 行、单行转发、零分支等），不值得单独画 CFG
- 目的：让读者在 CFG 图上看到 `[[xxxService.yyy()]]` 黑盒节点时，能在本章末尾的说明文字里查到该方法的用途和实现
- 必须字段：`entry`、`kind = "service"`、`called_by`、`purpose`、`implementation`
- `called_by`：列出至少 1 个调用本 Service 方法的 `control_flows[].entry_method`（格式同 `OmsOrderController.xxx`）

### skipped[].purpose（必填，60-120 字）
- 该方法的**业务用途**（面向业务读者）：**供谁 / 在什么场景下用 / 产生什么业务价值**
- 一句完整话表达清楚；不要只写 5-10 字的标签式描述
- 例（好）：「运营后台分页查看订单列表，按条件筛选后回填下单人信息以便审核与发货操作」
- 例（坏）：「查询订单列表」、「后台管理」

### skipped[].implementation（必填，100-200 字）
- 该方法的**核心实现逻辑**，要覆盖：
  1. **输入来源**：从哪里取参数（Query / Body / Path / SecurityContext）
  2. **数据源**：调哪个 Mapper / Service / 外部接口
  3. **过滤/加工逻辑**：按什么条件筛选、是否回填关联数据、是否做脱敏
  4. **返回内容**：返回什么结构（列表？单对象？统计？）
- 必须写成连贯的中文短段落，不是 bullet list
- 具体类/方法名用反引号包裹（如 `OmsOrderMapper.selectList`）

### skipped[] 可选增强字段（建议尽量填写，让读者更快理解）

- **`inputs`**（可选，适用 controller）：主要请求参数形式和来源
  - 例：「Query 参数 `OmsOrderQueryParam`（status / createTime 区间）+ 分页参数」
- **`returns`**（可选，适用 controller）：返回类型和关键字段
  - 例：「`CommonResult<PageInfo<OmsOrder>>`，分页订单列表，含回填的 `memberNickname`」
- **`key_dependencies`**（可选）：核心依赖 1-3 个（Mapper / Service / 外部 API）
  - 例：`["OmsOrderMapper.selectList", "UmsMemberMapper.selectByIds"]`
- **`access_control`**（可选，适用 controller）：权限注解或业务过滤条件
  - 例：「需要 `@PreAuthorize(\\"hasAuthority('pms:order:list')\\")` 运营权限」
- **`edge_cases`**（可选）：需要读者注意的边界 / 幂等 / 并发要点
  - 例：「`userId=null` 时返回全局订单；列表最大 500 条，超出需走导出接口」

### skipped 数量指引
- `kind = "controller"` 的条目不设严格上限（取决于入口实际数量）
- `kind = "service"` 的条目上限 10 个；宁可精挑调用频繁/黑盒频繁出现的 Service，不要罗列所有调用
"""


def build_control_flow_plan_user_prompt(flow_name: str, flow_kind: str,
                                         entry_methods_detail: str,
                                         class_skeletons: str,
                                         branch_hint: str = "",
                                         service_branch_hint: str = "") -> str:
    branch_section = (
        f"\n## 入口方法静态 AST 分析（权威判据）\n{branch_hint}\n"
        if branch_hint else ""
    )
    service_section = (
        f"\n## ServiceImpl 方法静态分支扫描（service_flows 候选参考）\n"
        f"以下 `ServiceImpl.method` 的分支数 ≥ 2，是 service_flows 的**优先候选**；\n"
        f"若它们被前面 control_flows 调用，应优先纳入 service_flows（不超过 3 个）。\n\n"
        f"{service_branch_hint}\n"
        if service_branch_hint else ""
    )
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 全部入口方法
{entry_methods_detail}
{branch_section}{service_section}
## 相关类骨架（类声明 + 字段 + 方法签名，不含方法体）
{class_skeletons}

请直接输出严格 JSON（control_flows + skipped），不要任何其它文字。
"""


CONTROL_FLOW_SYSTEM = """你是业务流程分析师（绘制阶段）。任务：针对**指定的单个入口方法**，基于提供的相关类完整源码，
绘制 Mermaid `flowchart` 展示该入口方法的业务决策流（if/else/状态分支/循环/异常路径）。

## 与时序图的区别
- 时序图（§3）关注"谁调用谁"，每个节点是**类**
- 控制流图（§5）关注"业务如何判断走哪条路"，每个节点是**动作或决策**

## 工作步骤
1. 以输入指定的 `entry_method` 为起点，从源码里识别：
   - **业务判断点**（`if (x.status == PAID)` / `switch (type)`）
   - **动作步骤**（`service.doXxx()` / `mapper.update()`）
   - **外部依赖调用**（`service.xxxService.yyy()`）
   - **异常/失败路径**（`throw new ApiException()` / `return error`）
2. 把上述元素组织为 flowchart TD

## Mermaid 节点形状约定（必须严格使用）
- `([text])`  起止点（Start/End）
- `[text]`    普通动作步骤
- `{text}`    决策分支（菱形）
- `[(text)]`  数据库读写（圆柱）
- `[[text]]`  跨 Service / 子流程 / 外部调用（双层矩形）

## 规范
- 第一行 `flowchart TD`（自上而下）
- 最多 25 个节点
- 分支箭头上标注条件：`A -->|"成功"| B` / `A -->|"失败"| C`
- 异常终点独立节点，不要省略
- 如有循环，用 `A -.->|"遍历"| B` 虚线箭头表示

## mapping 字段
`mapping: {"N1": "<class_id>"}`
- key 是 mermaid 节点 id
- value 是对应类的 class_id（从输入取，不编造）
- 只映射指向具体类的节点（起止/判断等抽象节点不强制映射）

## 输出格式（严格 JSON，无围栏）
{
  "mermaid": "flowchart TD\\n    Start([接收关闭订单请求]) --> Check{是否已支付?}\\n    Check -->|是| Refund[[调用退款服务]]\\n    Check -->|否| Cancel[(更新订单状态为已关闭)]\\n    Refund --> End([返回成功])\\n    Cancel --> End\\n",
  "mapping": {"Refund": "<class_id>", "Cancel": "<class_id>"}
}

## 兜底
如果入口方法几乎是直通 CRUD（`list` / `getById` / `add`），输出最小 flowchart（起点-动作-终点），不要硬编造分支。
"""


def build_control_flow_user_prompt(flow_name: str, flow_kind: str,
                                    entry_method: str, entry_method_detail: str,
                                    class_sources: str) -> str:
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 本次要画的入口方法
{entry_method}

入口方法详情:
{entry_method_detail}

## 相关类的完整源码
{class_sources}

请针对上述**单个入口方法**输出严格 JSON，不要任何其它文字。
"""


# ===========================================================
# §5 line-mapping 三阶段 prompts
# 参考 graph/four_chart.py + chains/prompts/type_chart_prompt.py
# ===========================================================

SOURCE_ID_SYSTEM = """你是代码控制流分析专家（源码行号划分阶段）。输入是按行编号的 Java 方法源码 + 语义解释，
输出是"功能片段 → 行号范围"的划分结果，供后续步骤将 mermaid 节点对应到具体行号。

## 核心要求
1. **完整覆盖**：拆分结果必须覆盖源代码中所有功能行（除注释、空行、单独 `{` / `}` 外），
   不能有任何功能行被遗漏；相邻片段之间不留空隙
2. **避免重叠**：两个功能节点不应覆盖完全相同的代码段；异常终止节点可与其判断行重叠
3. **粒度适度**：不过度细化到单行（除非该行确实独立），也不把完全无关的功能合并
4. **输出真实行号**：必须是输入里给出的实际行号，不能编造；片段覆盖多段代码时用数组

## 输出格式（严格 JSON，无围栏，无前言）
{
  "lines": [["1-2"], ["3"], ["4-9","28"], ["10-20"], ...],
  "reason": "说明划分逻辑，例如：1-2 是参数校验；3 是空返回分支；4-9 是主循环体 + 末尾日志..."
}

- 外层数组：每个元素代表一个功能片段
- 内层数组：该功能片段涉及的行号范围（可能不连续），单行用 `"8"`，范围用 `"8-10"`
"""


def build_source_id_user_prompt(tagged_source: str, explanation: str) -> str:
    return f"""## 按行编号的源代码
{tagged_source}

## 语义解释
{explanation}

请直接输出严格 JSON。
"""


CFG_SYSTEM = """你是业务流程分析师（控制流绘制阶段）。输入是按行编号的方法源码 + 语义解释 + 已划分好的
功能片段（每段有 source_id + 行号范围 + 划分原因）。你需要绘制 Mermaid `flowchart TD`，
并把每个节点映射到某个 source_id。**要求带配色的带 subgraph 分组的业务导向 CFG**。

## Mermaid 节点形状（必须严格使用）
- `([text])`  起止点 Start / End
- `[text]`    普通动作
- `{text}`    决策（菱形）
- `[(text)]`  数据库读写
- `[[text]]`  跨 Service / 子流程 / 外部调用

## 结构规范
- 第一行 `flowchart TD`
- **用 subgraph 按业务语义分组**，例如 `Initialization` / `MainLogic` / `Persistence` / `ErrorHandling` / `Cleanup`。
  层级不超过 2 层，分组名尽量贴合本方法的实际业务阶段（而不是死板地用上面几个词）。
- 节点总数 ≤ 25
- 箭头标注条件，如 `A -->|"成功"| B`
- 异常/早返回路径单独节点，不省略
- 循环用 `A -.->|"遍历"| B`

## 视觉差异化（用 `style` 指令给节点加颜色；采用 VS Code 风格主色 `#0af` / `#f96` / `#fbb`）

必须按节点语义分配样式：

1. **起止点**（Start / End）：
   `style Start fill:#eef5ff,stroke:#0af,stroke-width:2px`

2. **决策点**（菱形 `{...}`）：白底细边
   `style X fill:#fff,stroke:#333,stroke-width:2px`

3. **关键写操作** —— DB insert / update / delete、发 MQ、提交事务：
   深蓝填充 + 粗边框
   `style X fill:#d6ebff,stroke:#0af,stroke-width:3px`

4. **关键决策/主链路动作**（主业务流的关键步骤）：
   `stroke-width:3px` 加粗边框即可，填充可选 `fill:#fff7d6`（浅黄）

5. **错误路径 / 异常早返回节点**：
   红色虚线边框 + 浅红填充
   `style X fill:#fbb,stroke:#f66,stroke-width:2px,stroke-dasharray:5 5`

6. **次要 / 辅助节点**（日志、统计、打点等）：默认样式即可，不加 style

## 硬性约束
- 每个加样式的节点必须有一行 `style <节点id> ...` 指令（不要用 `classDef`，直接 inline style 最兼容）
- mermaid 解析器能正常渲染；复制到 mermaid 编辑器应能直接出图
- 不要在节点标签里放 `\\n` 字面量，要真正的换行用 `<br/>` 或拆成多个节点

## mapping 字段
- key 是 mermaid 节点 id（如 A1/B2/Start）
- value 是 **source_id**（从输入 `source_id` 列表里原样取，**不要写行号或类名**）
- 每个节点必须映射到一个 source_id；起止点也要映射到覆盖该行的 source_id

## Mermaid 示例（结构参考）
```mermaid
flowchart TD
    Start([接收请求])
    style Start fill:#eef5ff,stroke:#0af,stroke-width:2px

    subgraph Validation["参数与权限校验"]
        V1[提取用户身份]
        V2{参数合法?}
        style V2 fill:#fff,stroke:#333,stroke-width:2px
        V3[返回 400 错误]
        style V3 fill:#fbb,stroke:#f66,stroke-width:2px,stroke-dasharray:5 5
    end

    subgraph Business["核心业务"]
        B1[(查询订单)]
        B2{订单可取消?}
        style B2 fill:#fff,stroke:#333,stroke-width:2px
        B3[(更新订单为已取消)]
        style B3 fill:#d6ebff,stroke:#0af,stroke-width:3px
        B4[[调用退款服务]]
        style B4 fill:#d6ebff,stroke:#0af,stroke-width:3px
    end

    End([返回结果])
    style End fill:#eef5ff,stroke:#0af,stroke-width:2px

    Start --> V1 --> V2
    V2 -->|"非法"| V3 --> End
    V2 -->|"合法"| B1 --> B2
    B2 -->|"否"| V3
    B2 -->|"是"| B3 --> B4 --> End
```

## 输出格式（严格 JSON，无围栏）
{
  "mermaid": "flowchart TD\\n    Start([...])\\n    style Start fill:...\\n    ...",
  "mapping": {"Start": "12345678", "V2": "87654321", ...}
}
"""


def build_cfg_user_prompt(tagged_source: str, explanation: str,
                          source_id_list: list, code_block_reason: str) -> str:
    import json as _json
    return f"""## 按行编号的源代码
{tagged_source}

## 相关语义解释
{explanation}

## 功能片段清单（每项 source_id 对应一段代码行号范围）
{_json.dumps(source_id_list, ensure_ascii=False, indent=2)}

## 片段划分原因
{code_block_reason}

请直接输出严格 JSON，mapping 的 value 必须是上面 source_id 列表里的 source_id（不是行号，不是类名）。
"""


CFG_ID_VALIDATE_SYSTEM = """你是代码控制流分析专家（行号校验阶段）。输入是按行编号的源码 + 已画好的 mermaid +
当前每个节点对应的行号范围，你需要**校正**每个节点对应的行号范围（如果有错就修正），
并保证覆盖所有功能行。

## 任务
1. 对比每个节点（菱形、动作、数据库、子流程）的语义，与它当前 mapping 的行号范围是否匹配
2. 如有偏差，按源代码实际内容修正
3. 保证所有功能行都被某个节点覆盖，不重复、不遗漏
4. **必须使用输入源代码里出现过的实际行号**，禁止超出实际行数
5. 一个节点覆盖多段代码时，行号用数组，如 `["8-10","80"]`

## 输出格式（严格 JSON，无围栏）
{
  "mapping": {"A1": ["8-10"], "B1": ["11-20","80"], ...},
  "reason": "简要说明做了哪些调整（没调整就写 '无调整'）"
}
"""


def build_cfg_id_validate_user_prompt(tagged_source: str, mermaid: str,
                                       current_mapping: dict, split_reason: str) -> str:
    import json as _json
    return f"""## 按行编号的源代码
{tagged_source}

## 控制流 mermaid
{mermaid}

## 当前节点 → 行号范围映射（需校验）
{_json.dumps(current_mapping, ensure_ascii=False, indent=2)}

## 片段划分原因（供参考）
{split_reason}

请直接输出严格 JSON（mapping + reason）。
"""


# ===========================================================
# 通用：图定稿后生成详细说明（复用前次 session 消息历史）
# ===========================================================

DIAGRAM_DESCRIPTION_SYSTEM = """你是一个技术文档撰写者。你的唯一任务是：基于**你刚刚输出的最终 mermaid 图**，
生成一段对该图的详细说明文字，以帮助读者理解。

## 语言要求（极其重要）
- **必须全中文输出**；不要整段英文，也不要"The xxx 图以 yyy 为中心"这类中英夹杂开头
- 如需使用英文，仅限于用反引号包裹的**代码实体名**（类名/方法名/字段名）

## 内容要求
- 80-120 字 markdown，力求精炼
- 只基于图中实际出现的节点和关系，**不要**引入图外信息
- 禁止在说明里提及"图中未画出"的东西
- **所有类名、方法名、字段名必须用反引号包裹**（见下方代码引用规则）；
  输出前自查：如 `AppUserController`、`wlxOrderService.addOrder` 写成裸文字的是错的

## 标题与排版约束（非常重要 —— 你的说明会被嵌入到一个已经编号的章节里）
- **不要输出 `#`、`##`、`###` 级别的标题**（它们会破坏上级章节的层级）
- 需要分段时，用 `####` 或更深层级；多数情况下**直接用段落 + 加粗 + 有序/无序列表**即可
- **不要**在开头重复复述「XX 图说明」「XX 流程说明」之类的顶层标题 —— 外层已经有章节标题
- 直接进入正文段落

""" + CODE_REFERENCE_RULE + """

## 输出格式
直接输出 markdown 正文，不要 JSON 包裹、不要代码围栏、不要前言。
"""


def build_diagram_description_user_prompt(chart_kind: str) -> str:
    """chart_kind ∈ {'er','sequence','flowchart','state'}。根据图类型给出聚焦的描述要求。"""
    if chart_kind == "er":
        guidance = "简述核心实体的业务含义及实体间主要关联关系。"
    elif chart_kind == "sequence":
        guidance = "简述关键调用链路和核心业务步骤。"
    elif chart_kind == "flowchart":
        guidance = "简述主要决策分支和业务判断逻辑。"
    elif chart_kind == "state":
        guidance = "简述状态集合的业务含义、主要流转路径及典型使用场景。"
    else:
        guidance = "简述图中节点的业务含义和主要关系。"

    return f"""请基于你上一轮已输出的**最终 mermaid 图**生成简洁说明。

## 描述要点
{guidance}

## 输出
直接输出 80-120 字的 markdown 正文，不要 JSON 包裹、不要围栏。
"""


# ===========================================================
# §7 业务状态流转（state machine）
# ===========================================================

STATE_MACHINE_SYSTEM = """你是业务领域分析师。任务：基于输入的候选状态字段清单（每个字段带类型、注释、引用代码片段），
**识别**哪些字段是真正的业务状态机，为它们画 Mermaid `stateDiagram-v2` 图。

## Step 1. 识别业务流主题（必须先做）
从业务流**名称**推断本流的主题数据对象：
- 「订单流」→ 订单（Order）及直接相关（订单项、地址）
- 「稿件资讯流」→ 稿件（Manuscript / Article）及直接相关（稿件分类、外部文章源）
- 「会员权益流」→ 会员（Member）及直接相关

**主题** = 本流名字里的关键词对应的业务数据概念。

## Step 2. 只画主题相关实体的状态机
- ✅ **主题实体自身**的状态字段（如稿件流只画 `WlxManuscript.xxx`）
- ✅ **主题实体直接关联的数据对象**的状态字段（如订单流画 `Order.status` 和 `RefundOrder.status`）
- ❌ **跨业务模块实体**的状态字段 —— 即使它在候选清单里（因为 scope 耦合），也不画
  - 例：稿件流里出现的 `WlxActivity.status` / `WlxIntegralRecord.type` / `WlxLottery*.xxx` 等积分、打卡、抽奖、活动模块的状态，**一律不画**
  - 判断：实体名与业务流主题无直接业务语义关联 → 跳过
- 候选清单是 scope 级别的"可能含状态字段的 Entity 列表"，**不代表都该画**

## 识别原则（状态机 vs 非状态机）
- **真状态机**：字段有有限的值域（通常 3-8 个），各值对应明确业务语义，且业务操作会在这些值之间转移
  - 例：`order.status` ∈ {待支付, 已支付, 已发货, 已完成, 已取消}
- **非状态机**（必须排除）：
  - **状态集合只有 2 个值**（二态开关如 `isShow` / `isDelete` / `isEnabled`）→ 信息密度太低，**一律跳过**
  - 纯类型/分类字段（如"渠道来源"、"内容类型"），值之间没有"流转"关系
  - 字段值太多且离散（如"地区编码"）
- 宁缺毋滥；如果某个候选不是真状态机或不属于主题，**不要**画

## ⚠️ 严禁臆造（极其重要）
**状态集和转移必须严格来自输入的 usages 代码片段**，不能凭"常识"或"通用模板"补全：
- 状态值：只能来自 `setStatus(X)` 的实参 X，或 `getStatus() == Y` / `switch (status)` 里的 Y 值，或 JavaDoc 里明确的枚举
- 转移动作：只能来自**实际代码里出现过的**调用 `setStatus(X)` 的方法；没有在 usages 里出现的方法（如 `pay()` / `ship()` / `deliver()` / `confirmReceive()`）**禁止**编造
- **禁止套用"电商订单/审批/支付/物流"等通用行业模板**补全缺失的状态或转移
- 例（错误示范）：usages 只显示 `setStatus(0)` 和 `setStatus(2)` 两处，但你画了 `Created → Paid → Shipped → Delivered → Completed` 五态图——这是臆造
- 例（正确）：只画 usages 实际出现的两个状态 + 实际的 setter 调用者，如 `Init → Done : writeOff`；若整体只有 2 态则按上一条规则跳过该字段

## 工作步骤
对每个候选字段：
1. **逐条检查输入 usages**，列出所有 `setStatus(X)` 的 X 值集合、`getStatus() == Y` 的 Y 值集合，取并集得到**实际出现的状态值集合**
2. 若该集合 < 3 个值 → 跳过该字段（不画）
3. 为每个实际值起一个**业务语义名称**（英文 CamelCase 或中文），不要只用数字
4. 对每个转移 A → B，必须能在 usages 里指出**具体哪个方法的哪一行**调了 `setStatus(B)`；
   没有这样的证据 → 不画该转移
5. 起止：`[*] → 初始态`（某方法里第一次 setStatus 的值；通常对应创建方法），
   `终态 → [*]` 只有在 usages 里有明确的删除/归档动作时才画
6. 用 `stateDiagram-v2` 画图

## Mermaid 规范
- 第一行必须是 `stateDiagram-v2`
- 状态节点名用业务语义（不要 `0` `1` `2`）
- 转移边标签写**触发动作**（方法名或业务事件），如 `pay()` / `edit(isShow=1)`
- 每个图的状态控制在 **2-8 个**，转移 3-15 条
- 合法转移写法：`StateA --> StateB : action`

## mapping 字段（必填）
`mapping: {"StateName 或 action": "<class_id or method_id>"}`
- **每张状态机图的 mapping 至少要有一条**：把所有状态节点映射到 Entity 类的 class_id
  （因为状态字段定义在那里，可从输入里 `owner_class_id` 字段原样取）
- 每个转移边的动作名**尽量**映射到触发方法的 method_id（若能在 usages 里对应到具体方法）
- **禁止**返回空 `mapping: {}`（会导致源码定位缺失）
- class_id / method_id 从输入的引用片段里原样取；取不到的**至少**还要映射状态节点到 owner_class_id

## 数量上限
- 最多画 **3 张** 状态机图
- 宁可只画 1 张清晰的，也不画 3 张模糊的

## 输出格式（严格 JSON，无围栏，无前言）
{
  "state_machines": [
    {
      "field": "OmsOrder.status",
      "title": "订单生命周期",
      "purpose": "订单从创建到完结的生命周期状态流转，覆盖支付、发货、收货、取消等关键节点",
      "mermaid": "stateDiagram-v2\\n    [*] --> Pending : createOrder\\n    Pending --> Paid : pay\\n    Paid --> Shipped : ship\\n    Shipped --> Completed : confirmReceive\\n    Pending --> Canceled : cancel\\n    Paid --> Canceled : cancel\\n    Completed --> [*]\\n",
      "mapping": {
        "Pending": "<OmsOrder class_id>",
        "Paid": "<OmsOrder class_id>",
        "pay": "<pay method_id>"
      },
      "description": "订单状态机从 `Pending` 起步，经 `pay` 支付进入 `Paid` 后由运营发货进入 `Shipped`，买家确认收货后进入 `Completed` 终态；任一前置状态均可通过 `cancel` 转入 `Canceled` 分支。"
    }
  ]
}

## 兜底
- 如果所有候选都不是真状态机 → 返回 `{"state_machines": []}`
- 如果只有 1 个真状态机 → 只画 1 张

## 字段规范
- `field`：格式 `ClassName.fieldName`，从输入候选里原样取
- `title`：3-15 字的业务视角命名，如「订单生命周期」「稿件上架状态」
- `purpose`：30-80 字，说明该状态机**服务的业务场景和关键价值**（面向读者），放在图前
- `description`：60-100 字，**只描述本张图的状态集合和主要流转路径**（放在图后）
  - 严格只讲当前这张图的状态和转移，**不要**提及其它 state_machines 项
  - 句式示例：「X 状态机从 A 起步，经 action1 进入 B，再由 action2 流转到 C...」
  - 不要重复 purpose 的业务价值说明，聚焦于"怎么走"

""" + CODE_REFERENCE_RULE + """
（以上约束仅针对 purpose；mermaid 源码里状态名按 stateDiagram 语法原样书写，不要加反引号。）
"""


def build_state_machine_user_prompt(flow_name: str, flow_kind: str,
                                      candidates_text: str) -> str:
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 候选状态字段清单（已按引用热度降序）

{candidates_text}

请直接输出严格 JSON（state_machines 数组），不要任何其它文字。
"""


# ===========================================================
# §8 业务字典（enum / field-group / rules）
# ===========================================================

BUSINESS_DICTIONARY_SYSTEM = """你是业务架构师。任务：从一组 @TableName 实体类的 Java 源码里，提炼出**业务字典**信息，分 3 类输出。

## 3 种子类型

### 1. enum_dictionaries（枚举字段字典）
字段取离散字面量（string/int）作为业务分类。识别线索：
- 字段 Javadoc / `@ApiModelProperty` 注释里有 `0-xxx 1-yyy` / `0: 未付款 1: 已付款` 形式声明
- 代码里见到 `equals("0")` / `case "1":` / `if (x == 2)` 等字面量比较（需结合调用语境）

每项输出：
```
{
  "title": "WlxPrize.prizeType（奖品类型决定履约工作流）",
  "entity": "WlxPrize",
  "field": "prizeType",
  "values": [
    {"value": "0", "category": "未中奖", "fulfillment": "无需履约", "example": ""},
    ...
  ]
}
```
其中 `fulfillment` 可用 `meaning` 代替（无履约语义时）。例子字段 `example` 可为空字符串。

### 2. field_semantic_groups（字段语义组）
多个字段**协作**实现某业务机制。识别线索：
- 名字近似但含义不同（`winNum` / `showNum`）
- 前后缀成对（`startTime` / `endTime` / `dealStartTime` / `dealEndTime`）
- 语义上同属一个主题（库存约束、时间窗口、限购、发货地址等）

每项输出：
```
{
  "title": "库存与约束模型",
  "entity": "WlxPrize",
  "description": "一句话说明这组字段解决什么业务问题。",
  "fields": [
    {"name": "remainNum", "meaning": "实时库存"},
    {"name": "dayLimitNum", "meaning": "每用户每日购买上限"},
    ...
  ]
}
```

### 3. business_rules（业务规则 / 跨字段不变式）
字段之间的业务约束或设计意图。识别线索：
- 字段命名暗示（`winNum` vs `showNum` → 销量/展示双轨）
- 时间字段成对（购买窗口 vs 核销窗口）
- 权限字段 + 业务字段组合

每项输出：
```
{
  "title": "销量/展示双轨",
  "detail": "真实销量 winNum 驱动库存扣减，展示销量 showNum 仅用于前端显示，允许不一致以做促销热度包装。"
}
```

## 硬性原则

1. **忠实源码**：只列从字段注释/命名/代码分支能**读出来**的
2. **不确定就省略**：与其硬写"可能是 xxx"，不如不列
3. **业务视角**：避免"存储一个整数"这种无信息量描述
4. **去重**：一个字段已经在 enum_dictionaries 出现，就不要重复放到 field_semantic_groups
5. **规模控制**：enum_dictionaries ≤ 5 个，field_semantic_groups ≤ 3 个，business_rules ≤ 4 个
6. **所有空列表合法**：如果某子类型无内容，输出 `[]`

""" + CODE_REFERENCE_RULE + """

## 输出格式
严格 JSON（无围栏、无前言、无后置说明）：
```
{
  "enum_dictionaries": [...],
  "field_semantic_groups": [...],
  "business_rules": [...]
}
```
"""


def build_business_dictionary_user_prompt(
    flow_name: str, flow_kind: str, entity_sources: str,
) -> str:
    return f"""## 业务流
- 名称: {flow_name}
- 类型: {flow_kind}

## 涉及的 @TableName 实体类源码

{entity_sources}

请按要求输出严格 JSON。
"""
