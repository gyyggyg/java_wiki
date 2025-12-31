项目介绍
本项目目的是将大型java代码库解析成知识图谱并存入到neo4j中，neo4j中每个点对应代码中的一个实体，主要类型有：
- Block：模块
- Directory：目录
- Package：包
- File：文件
- Method：方法
- Class：类
- Enum：枚举
- Interface：接口
- Record：记录
- Annotation：注解
- Field：字段
- Enumconstant：枚举常量
其中Block是基于项目目录和源码信息划分的模块

实体之间连边表示它们之间的依赖关系，边的类型有：
- ANNOTATES：表示注解作用于哪个实体；
- CALLS：表示方法调用；
- CONTAINS：表示Package包含哪些文件实体；
- DECLARES：表示实体定义，如class定义一个方法；
- DIR_INCLUDE：表示目录之间、目录和文件之间的包含关系；
- EXTENDS：表示继承关系；
- HAS_TYPE：表示某个字段的类型与某个类、接口或枚举等实体相关；
- IMPLEMENTS：表示接口实现；
- RETURNS：表示方法返回；
- USES：表示方法中使用了某个类、接口或枚举等实体；
- f2c：表示Block之间的包含关系；
在neo4j中，绝大多数实体节点都有以下属性字段：
- nodeId：节点id；
- name：实体名；
对于代码实体节点（除Block，Directory类型外），还有以下属性字段来解释该节点：
- source_code：实体对应源码；
- background：实体所在文件的背景信息；
- SE_unsure_part：对该实体节点解释中不确定的部分；
- SE_What: 对该节点的描述；
- SE_Why: 该节点的设计目的和选择意义；
- SE_When: 描述该节点的使用者，使用该节点的时机和位置；
- SE_How: 该节点是如何工作的（控制流程）；
Block节点中有以下属性字段：
- module_explanation：介绍该Block；
- child_blocks：以nodeId列表的形式描述子Block；
- parent_blocks：以nodeId列表的形式描述父Block；
Directory节点中除了nodeId和name外没有多余的信息字段，Directory节点之间的包含关系由DIR_INCLUDE边表示

生成要求
项目介绍
本项目目的是将大型java代码库解析成知识图谱并存入到neo4j中，neo4j中每个点对应代码中的一个实体，主要类型有：
- Block：模块
- Directory：目录
- Package：包
- File：文件
- Method：方法
- Class：类
- Enum：枚举
- Interface：接口
- Record：记录
- Annotation：注解
- Field：字段
- Enumconstant：枚举常量
其中Block是基于项目目录和源码信息划分的模块

实体之间连边表示它们之间的依赖关系，边的类型有：
- ANNOTATES：表示注解作用于哪个实体；
- CALLS：表示方法调用；
- CONTAINS：表示Package包含哪些文件实体；
- DECLARES：表示实体定义，如class定义一个方法；
- DIR_INCLUDE：表示目录之间、目录和文件之间的包含关系；
- EXTENDS：表示继承关系；
- HAS_TYPE：表示某个字段的类型与某个类、接口或枚举等实体相关；
- IMPLEMENTS：表示接口实现；
- RETURNS：表示方法返回；
- USES：表示方法中使用了某个类、接口或枚举等实体；
- f2c：表示Block之间的包含关系；
在neo4j中，绝大多数实体节点都有以下属性字段：
- nodeId：节点id；
- name：实体名；
对于代码实体节点（除Block，Directory类型外），还有以下属性字段来解释该节点：
- source_code：实体对应源码；
- background：实体所在文件的背景信息；
- SE_unsure_part：对该实体节点解释中不确定的部分；
- SE_What: 对该节点的描述；
- SE_Why: 该节点的设计目的和选择意义；
- SE_When: 描述该节点的使用者，使用该节点的时机和位置；
- SE_How: 该节点是如何工作的（控制流程）；
Block节点中有以下属性字段：
- module_explanation：介绍该Block；
- child_blocks：以nodeId列表的形式描述子Block；
- parent_blocks：以nodeId列表的形式描述父Block；

生成要求
以下是参考，请根据自己项目要求修改
1. 任务工作流需要基于langgraph实现，且放入graph目录下；
2. neo4j相关接口在interfaces/neo4j_interface.py中；
3. 工作流所需提示词需要写在chains/prompts下，且一次模型调用对应一个提示词文件；
4. 工作流，可以模仿现有的工作流（如graph目录下.py文件）的实现方式；
5. 不要将信息写入neo4j；
6. 项目所需环境变量在.env文件中，如果需要添加环境变量，请在.env文件中添加；

```mermaid

```