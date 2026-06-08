"""目标分类层级定义（v2 — 扩充 WLX 子分类 + 拆分基础架构模块）。

原 UI 截图里只有 7 个 WLX 子分类 + 6 个后端框架子分类。实跑 422 页后发现：
- "业务领域 (wlx)" 顶层回退 21 页：实际可独立出便民/内容/外部平台/公共模型
- "基础架构模块" 一次性吸收 219 页：需要拆成 Java/javax/Spring/第三方库/HTTP 客户端/平台公共工具
- "后端框架" 边界不清：Spring Bean 机制类知识应归到"基础架构模块/Spring 生态"

CATEGORY_TREE 每个节点:
    {
        "path": "a/b/c",         # 用 '/' 分隔的分类路径
        "description": "描述",    # 用于指导 LLM 决策
    }

子类别的 "path" 是 "父/子" 形式。
"""

CATEGORY_TREE = [
    # ============ 架构概述 ============
    {
        "path": "架构概述",
        "description": "项目整体的架构说明、总览性介绍。通常是项目总揽、系统概览、模块架构图等",
    },

    # ============ 后端框架 ============
    # 这个桶只收纳"业务项目对框架的定制性使用"（比如项目自己的 AOP、自己的 JWT 过滤器）。
    # 纯框架知识（Spring Bean、Spring AOP 原理、MyBatis-Plus 框架本身）归到"基础架构模块/Spring 生态"或"基础架构模块/第三方库集成"。
    {
        "path": "后端框架",
        "description": "业务项目对后端框架的定制性横切能力（JWT 拦截器、安全配置、自定义 AOP 切面、MyBatis-Plus 定制扩展、多数据源切换等）。不包含框架自身的原理说明（那归「基础架构模块」）",
    },
    {
        "path": "后端框架/Maven 多模块设计",
        "description": "项目自身的 Maven 多模块划分、pom.xml 依赖管理、父子模块结构",
    },
    {
        "path": "后端框架/JWT 认证流程",
        "description": "项目自己实现的 JWT token 生成/解析/刷新、登录拦截器、用户身份识别流程",
    },
    {
        "path": "后端框架/Spring Security 配置",
        "description": "项目的 Spring Security 配置类、过滤器链、授权规则、认证管理器、资源保护",
    },
    {
        "path": "后端框架/AOP 切面系统",
        "description": "项目自己实现的切面（@Aspect/@Around）：日志切面、性能监控、数据权限、业务审计等（非 Spring AOP 原理）",
    },
    {
        "path": "后端框架/MyBatis-Plus 集成",
        "description": "项目里对 MyBatis-Plus 的定制配置与扩展：分页插件配置、自定义类型处理器、审计字段填充、代码生成器配置等（非 MyBatis-Plus 框架本身）",
    },
    {
        "path": "后端框架/动态数据源切换",
        "description": "多数据源配置、@DS 注解、动态路由、读写分离、租户库切换、Druid 连接池等",
    },

    # ============ 业务领域 (wlx) ============
    {
        "path": "业务领域 (wlx)",
        "description": "wlx 业务线相关的领域模型、业务服务、聚合根（仅在无更具体子分类时使用）",
    },
    {
        "path": "业务领域 (wlx)/社区与网格管理",
        "description": "社区/网格组织架构、成员管理、角色权限、地理区划、组织结构相关的业务",
    },
    {
        "path": "业务领域 (wlx)/打卡系统",
        "description": "用户打卡、签到、打卡记录、打卡统计、打卡规则、打卡配置等业务",
    },
    {
        "path": "业务领域 (wlx)/积分与抽奖引擎",
        "description": "积分累计/扣减、积分任务/规则、抽奖活动、抽奖规则、奖品管理、概率抽取、积分记录与订单",
    },
    {
        "path": "业务领域 (wlx)/活动与圈子平台",
        "description": "活动发布、活动报名、圈子/群组管理、活动互动、议程/时间线",
    },
    {
        "path": "业务领域 (wlx)/上报与通讯系统",
        "description": "问题上报、事件上报、消息通讯、站内信、通知推送、实时消息等",
    },
    {
        "path": "业务领域 (wlx)/App API 层",
        "description": "面向移动 App 的 REST API 入口（Controller 层）、请求/响应 DTO、接口文档",
    },
    {
        "path": "业务领域 (wlx)/分析与统计",
        "description": "数据分析、统计报表、指标计算、数据看板、分析领域的模型/Mapper/Service",
    },
    # ----- 新增：原 wlx 顶层退回的 21 页中可独立的 4 个子分类 -----
    {
        "path": "业务领域 (wlx)/便民服务",
        "description": "便民服务点（Convenience Service）、便民排行榜、便民用户关联，及对应的 Mapper/Service/领域实体",
    },
    {
        "path": "业务领域 (wlx)/内容管理",
        "description": "文章、稿件、头条、社区动态等内容领域模型/DTO，以及其发布、审核、查询、互动相关的业务",
    },
    {
        "path": "业务领域 (wlx)/外部平台集成",
        "description": "wlx 与外部平台（微信 Wx、浙里办 Zlb、Irs、政务外网等）的签名调用、协议适配、接口映射、外部配置同步。包括 WlxWxMapper/WlxZlbMapper、签名网关工具等",
    },
    {
        "path": "业务领域 (wlx)/公共模型与合约",
        "description": "跨多个 wlx 子业务复用的通用值对象（VO）、字典/级联组件数据、选择 VO、全局领域合约 DTO；wlx 领域模型的总揽性汇总页面也归到这里",
    },

    # ============ 前端应用 ============
    {
        "path": "前端应用",
        "description": "前端相关代码、管理后台 UI、前端组件、前端路由、前端状态管理",
    },

    # ============ 基础架构模块 ============
    # 父节点保留但只作为 fallback；绝大部分页面应落到下面某个子分类
    {
        "path": "基础架构模块",
        "description": "通用基础设施的 fallback（不匹配任何子分类才用）。绝大多数应落到下面的子分类",
    },
    {
        "path": "基础架构模块/Java 标准库",
        "description": "java.* 包下的 IO / NIO / 网络 / 并发 / 反射 / 安全 / 时间 / 基础类型等标准库能力说明（`Java 标准库/...` 路径下的页面）",
    },
    {
        "path": "基础架构模块/javax 标准接口",
        "description": "javax.* 下的 Servlet 请求处理、Validation 校验、TLS/MAC 加密等标准规范接口（`Javax 接口与规范/...` 或 `javax 标准接口与适配/...`）",
    },
    {
        "path": "基础架构模块/Spring 生态",
        "description": "Spring Framework 本身的机制说明：Bean 定义与注解、Bean 工厂、上下文管理、Spring AOP 原理、事务、Web/HTTP 抽象、请求上下文、Spring Security 核心等。业务项目自己使用 Spring 的配置归到'后端框架'",
    },
    {
        "path": "基础架构模块/第三方库集成",
        "description": "Apache 家族（POI、Commons IO/Lang3、HttpComponents、Velocity）、Quartz 调度、fastjson2、MyBatis-Plus 框架本身、Hutool 等库的能力与用法说明",
    },
    {
        "path": "基础架构模块/HTTP 客户端",
        "description": "OkHttp3、Apache HttpClient 等 HTTP 客户端库的请求/响应、消息体、连接管理",
    },
    {
        "path": "基础架构模块/平台公共工具",
        "description": "项目自研的平台公共工具（ruoyi-common 下的 util、通用 VO/DTO、XSS 过滤器、代码生成器配置、Quartz 任务实现、系统服务通用层等）",
    },

    # ============ 配置参考 ============
    {
        "path": "配置参考",
        "description": "application.yml/properties 配置说明、环境变量参考、部署配置、Nacos/Apollo 等外部配置中心",
    },
]


# 用于 prompt 中展示的结构化文本
def render_category_tree_for_prompt() -> str:
    """把分类树渲染成带缩进的文本，供 LLM 参考"""
    lines = ["可选分类（path 字段必须严格从以下列表中选择其一）:\n"]
    for cat in CATEGORY_TREE:
        depth = cat["path"].count("/")
        indent = "  " * depth
        lines.append(f"{indent}- {cat['path']}: {cat['description']}")
    return "\n".join(lines)


# 所有合法 path 的 set，用于结果校验
VALID_PATHS = {c["path"] for c in CATEGORY_TREE}
