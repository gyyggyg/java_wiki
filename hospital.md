## 1. 功能分析

### 1.1 总体服务概述

本Java项目为一个医院管理系统，采用Java Swing实现桌面应用界面。系统主要对外提供了医生（Doctor）、患者（Patient）、工作人员（Worker）三大核心实体的管理服务。所有对外服务以图形界面方式呈现，用户可通过界面操作完成数据的新增、查询、更新、删除（CRUD）等操作。系统入口为登录界面（LogIN），通过身份验证后进入主界面（Home），再根据不同管理对象进入相应功能模块。

### 1.2 服务组成与关系

#### 1.2.1 登录与主界面服务

- **登录服务**：由`LogIN`类实现，提供用户名/密码验证，成功后进入主界面。
- **主界面服务**：由`Home`类实现，提供医生、患者、工作人员管理模块的入口导航。

#### 1.2.2 医生管理服务（Doctor）

- **医生管理主界面**：`Doctor`类，提供“添加医生”、“医生历史”、“更新医生”功能入口。
- **添加医生**：`adddoctor`类，实现医生信息的录入与保存。
- **医生历史**：`historyDoctor`类，展示所有医生信息，支持搜索与删除。
- **更新医生**：`updatedoctor`类，支持通过ID查询医生、修改并保存医生信息。

#### 1.2.3 患者管理服务（Patient）

- **患者管理主界面**：`Pacient`类，提供“添加患者”、“患者历史”、“更新患者”功能入口。
- **添加患者**：`addpatient`类，实现患者信息的录入与保存。
- **患者历史**：`historyPatient`类，展示所有患者信息，支持搜索与删除。
- **更新患者**：`updatepatient`类，支持通过ID查询患者、修改并保存患者信息。

#### 1.2.4 工作人员管理服务（Worker）

- **工作人员管理主界面**：`Worker`类，提供“添加工作人员”、“工作人员历史”、“更新工作人员”功能入口。
- **添加工作人员**：`addworker`类，实现工作人员信息的录入与保存。
- **工作人员历史**：`historyWorker`类，展示所有工作人员信息，支持搜索与删除。
- **更新工作人员**：`updateWorker`类，支持通过ID查询工作人员、修改并保存工作人员信息。

#### 1.2.5 服务之间的关系

- 所有管理服务通过主界面`Home`进行导航。
- 各管理服务内部均包含：新增、历史（列表与删除）、更新三个功能，功能间通过按钮跳转。
- 登录服务为所有其他服务的前置入口。

---

## 2. 调用类说明

### 2.1 医院管理系统对外接口类一览

| 模块            | 类名             | 文件名                              | package名                    | 功能简述 |
|-----------------|------------------|-------------------------------------|------------------------------|----------|
| 登录            | LogIN            | HospitalManagementSystem\src\LogIN.java          | com.macro.mall.controller    | 登录认证，身份验证，进入主界面 |
| 主界面          | Home             | HospitalManagementSystem\src\Home.java           | com.macro.mall.controller    | 主导航界面，进入医生/患者/工作人员管理 |
| 医生管理        | Doctor           | HospitalManagementSystem\src\Doctor.java         | com.macro.mall.config        | 医生管理主界面，功能入口 |
|                 | adddoctor        | HospitalManagementSystem\src\adddoctor.java      | com.macro.mall               | 添加医生信息 |
|                 | historyDoctor    | HospitalManagementSystem\src\historyDoctor.java  | com.macro.mall.config        | 医生信息列表、搜索、删除 |
|                 | updatedoctor     | HospitalManagementSystem\src\updatedoctor.java   | com.macro.mall.controller    | 医生信息查询与更新 |
| 患者管理        | Pacient          | HospitalManagementSystem\src\Pacient.java        | com.macro.mall.controller    | 患者管理主界面，功能入口 |
|                 | addpatient       | HospitalManagementSystem\src\addpatient.java     | com.macro.mall.bo            | 添加患者信息 |
|                 | historyPatient   | HospitalManagementSystem\src\historyPatient.java | com.macro.mall.config        | 患者信息列表、搜索、删除 |
|                 | updatepatient    | HospitalManagementSystem\src\updatepatient.java  | com.macro.mall.controller    | 患者信息查询与更新 |
| 工作人员管理    | Worker           | HospitalManagementSystem\src\Worker.java         | com.macro.mall.controller    | 工作人员管理主界面，功能入口 |
|                 | addworker        | HospitalManagementSystem\src\addworker.java      | com.macro.mall.config        | 添加工作人员信息 |
|                 | historyWorker    | HospitalManagementSystem\src\historyWorker.java  | com.macro.mall.config        | 工作人员信息列表、搜索、删除 |
|                 | updateWorker     | HospitalManagementSystem\src\updateWorker.java   | com.macro.mall.controller    | 工作人员信息查询与更新 |

---

### 2.2 核心接口类功能详细说明

#### 2.2.1 登录与主界面

- **LogIN**（HospitalManagementSystem\src\LogIN.java，com.macro.mall.controller）
  - 提供用户名/密码校验，登录成功后进入`Home`主界面。
- **Home**（HospitalManagementSystem\src\Home.java，com.macro.mall.controller）
  - 提供医生、患者、工作人员主模块的导航入口。

#### 2.2.2 医生相关

- **Doctor**（HospitalManagementSystem\src\Doctor.java，com.macro.mall.config）
  - 医生管理主菜单，入口到添加、历史、更新功能。
- **adddoctor**（HospitalManagementSystem\src\adddoctor.java，com.macro.mall）
  - 医生信息录入界面，表单提交后入库。
- **historyDoctor**（HospitalManagementSystem\src\historyDoctor.java，com.macro.mall.config）
  - 医生信息列表，支持搜索、选中删除。
- **updatedoctor**（HospitalManagementSystem\src\updatedoctor.java，com.macro.mall.controller）
  - 通过ID查询医生详细信息，支持编辑并提交更新。

#### 2.2.3 患者相关

- **Pacient**（HospitalManagementSystem\src\Pacient.java，com.macro.mall.controller）
  - 患者管理主菜单，入口到添加、历史、更新功能。
- **addpatient**（HospitalManagementSystem\src\addpatient.java，com.macro.mall.bo）
  - 患者信息录入界面，表单提交后入库。
- **historyPatient**（HospitalManagementSystem\src\historyPatient.java，com.macro.mall.config）
  - 患者信息列表，支持搜索、选中删除。
- **updatepatient**（HospitalManagementSystem\src\updatepatient.java，com.macro.mall.controller）
  - 通过ID查询患者详细信息，支持编辑并提交更新。

#### 2.2.4 工作人员相关

- **Worker**（HospitalManagementSystem\src\Worker.java，com.macro.mall.controller）
  - 工作人员管理主菜单，入口到添加、历史、更新功能。
- **addworker**（HospitalManagementSystem\src\addworker.java，com.macro.mall.config）
  - 工作人员信息录入界面，表单提交后入库。
- **historyWorker**（HospitalManagementSystem\src\historyWorker.java，com.macro.mall.config）
  - 工作人员信息列表，支持搜索、选中删除。
- **updateWorker**（HospitalManagementSystem\src\updateWorker.java，com.macro.mall.controller）
  - 通过ID查询工作人员详细信息，支持编辑并提交更新。

---

以上为本项目对外提供服务的接口分析及调用类说明。## 3. 数据结构说明

本章节详细说明医院管理系统中所有对外服务相关类的数据结构、核心方法及其参数说明，便于二次开发、调用与系统集成。

---

### 3.1 登录与主界面

#### 3.1.1 `com.macro.mall.controller.LogIN`

- **用途**：提供登录认证，入口为医院管理系统。
- **主要对外方法**：

  ```java
  public LogIN()
  public static void main(String[] args)
  ```
- **说明**：
  - 构造函数`LogIN()`用于初始化登录界面。
  - `main`为程序入口，可直接运行启动登录界面。
- **对外服务流程**：
  - 用户通过Swing界面输入用户名/密码，点击“LogIn”按钮（UI事件驱动）。
  - 认证信息校验通过后自动跳转到`Home`主界面。
- **外部使用示例**：

  ```java
  // 直接启动登录界面
  new LogIN().setVisible(true);
  ```

---

#### 3.1.2 `com.macro.mall.controller.Home`

- **用途**：医院管理系统主界面导航。
- **主要对外方法**：

  ```java
  public Home()
  public static void main(String[] args)
  ```
- **说明**：
  - 构造函数`Home()`初始化主面板，提供医生、患者、工作人员模块入口。
  - 各入口通过UI按钮事件触发，分别实例化对应模块界面。
- **外部使用示例**：

  ```java
  // 启动主界面
  new Home().setVisible(true);
  ```

---

### 3.2 医生管理

#### 3.2.1 `com.macro.mall.config.Doctor`

- **用途**：医生管理主菜单（添加、历史、更新入口）。
- **主要对外方法**：

  ```java
  public Doctor()
  public static void main(String[] args)
  ```
- **说明**：
  - 构造函数初始化主菜单窗口。
  - 通过按钮事件分别进入添加医生、医生历史、更新医生子模块。
- **外部使用示例**：

  ```java
  new Doctor().setVisible(true);
  ```

---

#### 3.2.2 `com.macro.mall.adddoctor`

- **用途**：医生信息新增界面。
- **主要对外方法**：

  ```java
  public adddoctor()
  public static void main(String[] args)
  ```
- **界面核心字段**（均为`JTextField`/`JComboBox`）：

  - ID（DoctorId）
  - Name
  - Surname
  - PersonalID
  - Gender
  - Age
  - PhoneNumber
  - MaritalStatus
  - Experience
  - Adress

- **主要对外服务**：
  - 保存按钮`save`对应的事件方法`saveActionPerformed(java.awt.event.ActionEvent evt)`
    - 入参：无（从界面取值）
    - 处理：将各字段内容插入至数据库doctor表，返回保存结果弹窗。
  - 返回按钮`exit`对应事件`exitActionPerformed(java.awt.event.ActionEvent evt)`返回医生列表界面。

- **外部使用示例**：

  ```java
  // 打开添加医生窗口
  new adddoctor().setVisible(true);
  ```

---

#### 3.2.3 `com.macro.mall.config.historyDoctor`

- **用途**：医生信息表格、搜索、删除。
- **主要对外方法**：

  ```java
  public historyDoctor()
  public void setRecordsToTable()
  public void search(String str)
  public static void main(String[] args)
  ```
- **说明**：
  - 构造函数初始化表格，可调用`setRecordsToTable()`刷新所有记录。
  - `search(String str)`支持正则过滤表格内容。
  - “删除”按钮事件将选中行从数据库中删除。

- **对外服务流程**：
  - 用户可通过`txt_search`输入关键字实时过滤，点击删除按钮删除指定医生。

- **外部使用示例**：

  ```java
  historyDoctor doctorList = new historyDoctor();
  doctorList.setVisible(true);
  // 过滤表格（如在测试代码中）
  doctorList.search("王");
  ```

---

#### 3.2.4 `com.macro.mall.controller.updatedoctor`

- **用途**：医生信息查询与更新。
- **主要对外方法**：

  ```java
  public updatedoctor()
  public static void main(String[] args)
  ```
- **界面核心字段**（均为`JTextField`/`JComboBox`）：

  - DoctorId
  - Name
  - Surname
  - PersonalID
  - Gender
  - Age
  - PhoneNumber
  - MaritalStatus
  - Experience
  - Adress

- **主要服务**：
  - “搜索”按钮事件`search_buttonActionPerformed`：根据DoctorId加载医生数据填充表单。
  - “更新”按钮事件`update_buttonActionPerformed`：根据表单内容更新数据库doctor表。
  - “返回”按钮事件`back_buttonActionPerformed`：返回主菜单。

- **外部使用示例**：

  ```java
  updatedoctor ud = new updatedoctor();
  ud.setVisible(true);
  ```

---

### 3.3 患者管理

#### 3.3.1 `com.macro.mall.controller.Pacient`

- **用途**：患者管理主菜单。
- **主要对外方法**：

  ```java
  public Pacient()
  public static void main(String[] args)
  ```
- **说明**：
  - 提供添加患者、历史患者、更新患者功能入口。
- **外部使用示例**：

  ```java
  new Pacient().setVisible(true);
  ```

---

#### 3.3.2 `com.macro.mall.bo.addpatient`

- **用途**：患者信息新增。
- **主要对外方法**：

  ```java
  public addpatient()
  public static void main(String[] args)
  ```
- **界面核心字段**：

  - PatientId
  - Name
  - Surname
  - PersonalID
  - Gender
  - Age
  - PhoneNumber
  - MaritalStatus
  - Adress
  - BloodGroup
  - Disease

- **主要服务**：
  - “保存”按钮事件`save_buttonActionPerformed`：表单内容插入patient表。
  - “返回”按钮事件`back_buttonActionPerformed`。

- **外部使用示例**：

  ```java
  new addpatient().setVisible(true);
  ```

---

#### 3.3.3 `com.macro.mall.config.historyPatient`

- **用途**：患者信息表格查询、搜索、删除。
- **主要对外方法**：

  ```java
  public historyPatient()
  public void setRecordsToTable()
  public void search(String str)
  public static void main(String[] args)
  ```
- **说明**：
  - 构造函数初始化表格。
  - `setRecordsToTable()`加载所有患者数据。
  - `search(String str)`表格数据过滤。
  - “删除”按钮事件可删除选中患者。

- **外部使用示例**：

  ```java
  historyPatient hp = new historyPatient();
  hp.setVisible(true);
  hp.search("张");
  ```

---

#### 3.3.4 `com.macro.mall.controller.updatepatient`

- **用途**：患者信息查询与更新。
- **主要对外方法**：

  ```java
  public updatepatient()
  public static void main(String[] args)
  ```
- **界面核心字段**：

  - PatientId
  - Name
  - Surname
  - PersonalID
  - Gender
  - Age
  - PhoneNumber
  - MaritalStatus
  - Adress
  - BloodGroup
  - Disease

- **主要服务**：
  - “搜索”按钮事件`search_buttonActionPerformed`：根据PatientId查找并填充表单。
  - “更新”按钮事件`update_buttonActionPerformed`：更新数据库patient表。
  - “返回”按钮事件`back_buttonActionPerformed`。

- **外部使用示例**：

  ```java
  new updatepatient().setVisible(true);
  ```

---

### 3.4 工作人员管理

#### 3.4.1 `com.macro.mall.controller.Worker`

- **用途**：工作人员管理主界面。
- **主要对外方法**：

  ```java
  public Worker()
  public static void main(String[] args)
  ```
- **说明**：
  - 各功能入口通过按钮分发到添加、历史、更新模块。
- **外部使用示例**：

  ```java
  new Worker().setVisible(true);
  ```

---

#### 3.4.2 `com.macro.mall.config.addworker`

- **用途**：工作人员信息新增。
- **主要对外方法**：

  ```java
  public addworker()
  public static void main(String[] args)
  ```
- **界面核心字段**：

  - WorkerId
  - Name
  - Surname
  - PersonalID
  - Gender
  - Age
  - PhoneNumber
  - MaritalStatus
  - Experience
  - Adress

- **主要服务**：
  - “保存”按钮事件`save_buttonActionPerformed`：插入worker表。
  - “返回”按钮事件`back_buttonActionPerformed`。

- **外部使用示例**：

  ```java
  new addworker().setVisible(true);
  ```

---

#### 3.4.3 `com.macro.mall.config.historyWorker`

- **用途**：工作人员信息表格、搜索、删除。
- **主要对外方法**：

  ```java
  public historyWorker()
  public void setRecordsToTable()
  public void search(String str)
  public static void main(String[] args)
  ```
- **说明**：
  - 构造函数初始化表格。
  - `setRecordsToTable()`加载所有worker数据。
  - `search(String str)`过滤。
  - “删除”按钮事件删除选中行。

- **外部使用示例**：

  ```java
  historyWorker hw = new historyWorker();
  hw.setVisible(true);
  hw.search("李");
  ```

---

#### 3.4.4 `com.macro.mall.controller.updateWorker`

- **用途**：工作人员信息查询与更新。
- **主要对外方法**：

  ```java
  public updateWorker()
  public static void main(String[] args)
  ```
- **界面核心字段**：

  - WorkerId
  - Name
  - Surname
  - PersonalID
  - Gender
  - Age
  - PhoneNumber
  - MaritalStatus
  - Experience
  - Adress

- **主要服务**：
  - “搜索”按钮事件`search_buttonActionPerformed`：通过WorkerId查找并填充表单。
  - “更新”按钮事件`update_buttonActionPerformed`：更新数据库worker表。
  - “返回”按钮事件`back_buttonActionPerformed`。

- **外部使用示例**：

  ```java
  new updateWorker().setVisible(true);
  ```

---

### 3.5 组件导入与使用说明

所有Swing窗口类均可通过如下方式import并实例化：

```java
import com.macro.mall.controller.LogIN;
import com.macro.mall.controller.Home;
import com.macro.mall.config.Doctor;
import com.macro.mall.adddoctor;
import com.macro.mall.config.historyDoctor;
import com.macro.mall.controller.updatedoctor;
import com.macro.mall.controller.Pacient;
import com.macro.mall.bo.addpatient;
import com.macro.mall.config.historyPatient;
import com.macro.mall.controller.updatepatient;
import com.macro.mall.controller.Worker;
import com.macro.mall.config.addworker;
import com.macro.mall.config.historyWorker;
import com.macro.mall.controller.updateWorker;

// 示例：启动系统主流程
public static void main(String[] args) {
    new LogIN().setVisible(true);
}
```

---

### 3.6 界面请求/响应数据格式简述

由于本项目采用Java Swing桌面应用，所有“请求/响应”均为界面字段与数据库的交互。主要表单字段类型均为`String`，下拉框为`JComboBox<String>`，表格为`JTable`。所有数据的写入/更新均通过SQL语句直接操作数据库，删除/搜索等操作同理。

- **新增/更新**操作：表单各字段均为String，通过按钮事件统一收集，拼接SQL写入。
- **查询/搜索**操作：以ID或关键字为条件，SQL查询后填充到表单或表格。
- **删除**操作：从选中表格行获取ID，拼接SQL删除。

---

**注意事项**：

- 以上所有窗口类均可直接实例化并通过`setVisible(true)`弹出界面。
- 所有数据库操作均内嵌于按钮事件响应方法，若需后端API或脚本调用请自行封装相关SQL逻辑。
- 若需二次开发集成，可将核心事件处理方法拆分为公用业务方法。