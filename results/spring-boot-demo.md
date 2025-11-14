# 2. 对外提供接口说明文档

## 1. 功能分析

### 1.1 项目对外提供的服务概览

本Java项目对外提供了丰富的RESTful API、WebSocket、页面渲染、OAuth2、权限认证、定时任务管理、文件上传、动态数据源、异常处理等服务，主要包括以下几个方面：

#### 1.1.1 用户管理服务

- 支持用户的增删改查（CRUD）、分页查询、条件查询、文件上传等功能。
- 涉及多种持久化方式（JDBC、BeetlSQL、JPA、Swagger文档集成等）。
- 提供了安全认证（RBAC、OAuth2）相关接口，支持JWT、OAuth2、权限校验。

#### 1.1.2 代码生成服务

- 提供数据库表结构的分页查询接口。
- 支持根据用户配置自动生成代码，并以ZIP文件下载。

#### 1.1.3 定时任务/调度服务

- 通过Quartz等方式支持定时任务的添加、删除、暂停、恢复、修改和分页查询。

#### 1.1.4 文件上传服务

- 支持文件上传到本地和七牛云存储，返回上传结果。

#### 1.1.5 第三方登录（OAuth授权）

- 支持多种第三方平台的OAuth2登录、回调、类型查询等。

#### 1.1.6 动态数据源和多数据源支持

- 支持在线新增、删除数据源配置，动态切换数据源。
- 提供多数据源JPA的基础增删查接口。

#### 1.1.7 配置/属性查询服务

- 提供获取应用及开发者配置信息的接口。

#### 1.1.8 服务器状态与监控

- 支持在线用户管理（查询在线用户、踢人下线）、服务器运行信息查询。

#### 1.1.9 实时消息/聊天服务

- 提供基于WebSocket与Socket.IO的消息推送、群聊、私聊、广播等接口。

#### 1.1.10 页面渲染与异常处理

- 提供页面跳转、登录、异常处理等接口，以及REST风格的异常输出。

#### 1.1.11 其它演示与测试接口

- 包括HelloWorld、限流、日志、模板引擎等功能的演示接口。

### 1.2 服务组成及关系

- **REST API服务**：以`@RestController`为主，服务于绝大多数功能模块（用户、任务、上传、监控等）。
- **WebSocket/Socket.IO服务**：负责实时通信，配合消息事件处理。
- **页面服务**：以`@Controller`为主，负责页面渲染、跳转。
- **服务层接口与实现**：如`UserService`, `JobService`, `CodeGenService`等，服务于控制器，隔离业务逻辑。
- **安全与认证服务**：如`AuthController`, `WebSecurityConfig`等，负责OAuth2、JWT、权限管理。
- **数据源/配置**：如`DatasourceConfigController`等，支持多数据源与动态配置。
- **异常处理**：如`DemoExceptionHandler`，统一处理项目异常，保证接口响应规范。
- **Swagger文档**：部分控制器集成Swagger注解，便于API文档生成与测试。

不同服务之间通过依赖注入、分层结构（Controller-Service-Dao）、事件驱动、注解式权限等方式形成协作，整体上结构清晰、解耦良好。

---

## 2. 调用类说明

### 2.1 对外接口调用类一览

#### 2.1.1 用户管理相关

- **demo-orm-jdbctemplate/src/main/java/com/xkcoding/orm/jdbctemplate/controller/UserController.java**
  - `com.xkcoding.orm.jdbctemplate.controller.UserController`
    - 提供RESTful用户CRUD接口。

- **demo-orm-beetlsql/src/main/java/com/xkcoding/orm/beetlsql/service/UserService.java**
  - `com.xkcoding.orm.beetlsql.service.UserService`
    - 用户服务接口，定义用户的增删改查、分页等业务逻辑。

- **demo-dynamic-datasource/src/main/java/com/xkcoding/dynamic/datasource/controller/UserController.java**
  - `com.xkcoding.dynamic.datasource.controller.UserController`
    - 动态数据源下的用户列表查询接口。

- **demo-swagger/src/main/java/com/xkcoding/swagger/controller/UserController.java**
  - `com.xkcoding.swagger.controller.UserController`
    - 支持Swagger注解的用户管理REST接口。

- **demo-swagger-beauty/src/main/java/com/xkcoding/swagger/beauty/controller/UserController.java**
  - `com.xkcoding.swagger.beauty.controller.UserController`
    - 增强Swagger文档展示的用户管理接口。

- **demo-rbac-security/src/main/java/com/xkcoding/rbac/security/controller/AuthController.java**
  - `com.xkcoding.rbac.security.controller.AuthController`
    - 用户登录、注销接口（JWT/RBAC安全体系）。

#### 2.1.2 代码生成相关

- **demo-codegen/src/main/java/com/xkcoding/codegen/controller/CodeGenController.java**
  - `com.xkcoding.codegen.controller.CodeGenController`
    - 提供表结构查询与代码生成下载接口。

- **demo-codegen/src/main/java/com/xkcoding/codegen/service/CodeGenService.java**
  - `com.xkcoding.codegen.service.CodeGenService`
    - 代码生成业务接口。

#### 2.1.3 定时任务相关

- **demo-task-quartz/src/main/java/com/xkcoding/task/quartz/controller/JobController.java**
  - `com.xkcoding.task.quartz.controller.JobController`
    - 管理定时任务的REST接口（增删改查、暂停、恢复等）。

- **demo-task-quartz/src/main/java/com/xkcoding/task/quartz/service/JobService.java**
  - `com.xkcoding.task.quartz.service.JobService`
    - 定时任务服务接口。

#### 2.1.4 文件上传相关

- **demo-upload/src/main/java/com/xkcoding/upload/controller/UploadController.java**
  - `com.xkcoding.upload.controller.UploadController`
    - 本地和七牛云文件上传接口。

- **demo-upload/src/main/java/com/xkcoding/upload/service/IQiNiuService.java**
  - `com.xkcoding.upload.service.IQiNiuService`
    - 七牛云上传服务接口。

#### 2.1.5 第三方登录（OAuth2）

- **demo-social/src/main/java/com/xkcoding/social/controller/OauthController.java**
  - `com.xkcoding.social.controller.OauthController`
    - OAuth登录类型、授权跳转、回调处理接口。

#### 2.1.6 动态数据源相关

- **demo-dynamic-datasource/src/main/java/com/xkcoding/dynamic/datasource/controller/DatasourceConfigController.java**
  - `com.xkcoding.dynamic.datasource.controller.DatasourceConfigController`
    - 动态新增/删除数据源配置接口。

#### 2.1.7 配置/属性查询

- **demo-properties/src/main/java/com/xkcoding/properties/controller/PropertyController.java**
  - `com.xkcoding.properties.controller.PropertyController`
    - 获取应用和开发者配置信息的接口。

#### 2.1.8 服务器监控与在线用户管理

- **demo-websocket/src/main/java/com/xkcoding/websocket/controller/ServerController.java**
  - `com.xkcoding.websocket.controller.ServerController`
    - 查询服务器实时运行状态信息的接口。

- **demo-rbac-security/src/main/java/com/xkcoding/rbac/security/controller/MonitorController.java**
  - `com.xkcoding.rbac.security.controller.MonitorController`
    - 查询在线用户、批量踢出在线用户接口。

#### 2.1.9 实时消息/聊天相关

- **demo-websocket-socketio/src/main/java/com/xkcoding/websocket/socketio/controller/MessageController.java**
  - `com.xkcoding.websocket.socketio.controller.MessageController`
    - 广播消息REST接口。

- **demo-websocket-socketio/src/main/java/com/xkcoding/websocket/socketio/handler/MessageEventHandler.java**
  - `com.xkcoding.websocket.socketio.handler.MessageEventHandler`
    - 处理Socket.IO事件（连接、私聊、群聊、广播等）。

#### 2.1.10 页面渲染与异常处理

- **demo-session/src/main/java/com/xkcoding/session/controller/PageController.java**
  - `com.xkcoding.session.controller.PageController`
    - 处理页面跳转、登录等操作。

- **demo-template-freemarker/src/main/java/com/xkcoding/template/freemarker/controller/IndexController.java**
  - `com.xkcoding.template.freemarker.controller.IndexController`
    - 根路径页面渲染，登录检测。

- **demo-template-freemarker/src/main/java/com/xkcoding/template/freemarker/controller/UserController.java**
  - `com.xkcoding.template.freemarker.controller.UserController`
    - 登录页面及登录处理。

- **demo-exception-handler/src/main/java/com/xkcoding/exception/handler/controller/TestController.java**
  - `com.xkcoding.exception.handler.controller.TestController`
    - 模拟接口异常，用于测试统一异常输出。

- **demo-exception-handler/src/main/java/com/xkcoding/exception/handler/handler/DemoExceptionHandler.java**
  - `com.xkcoding.exception.handler.handler.DemoExceptionHandler`
    - 全局异常处理类，统一JSON和页面异常输出。

#### 2.1.11 其它演示、测试与工具接口

- **demo-helloworld/src/main/java/com/xkcoding/helloworld/SpringBootDemoHelloworldApplication.java**
  - `com.xkcoding.helloworld.SpringBootDemoHelloworldApplication`
    - HelloWorld测试接口。

- **demo-ratelimit-guava/src/main/java/com/xkcoding/ratelimit/guava/controller/TestController.java**
  - `com.xkcoding.ratelimit.guava.controller.TestController`
    - 限流测试接口。

- **demo-log-aop/src/main/java/com/xkcoding/log/aop/controller/TestController.java**
  - `com.xkcoding.log.aop.controller.TestController`
    - 日志AOP测试接口。

- **demo-oauth/oauth-resource-server/src/main/java/com/xkcoding/oauth/controller/TestController.java**
  - `com.xkcoding.oauth.controller.TestController`
    - OAuth2资源受保护接口，按角色、Scope演示权限控制。

---

**备注：所有接口类的类名、URL、字段名均严格保持与源码一致，具体接口参数及响应结构详见各类源码与注释。**## 3. 数据结构说明

### 3.1 用户管理相关

#### 3.1.1 `com.xkcoding.orm.jdbctemplate.controller.UserController`

**接口路径：** `/user`

**主要方法:**
- `@PostMapping("/user")`
  - **方法签名**: `public Dict save(@RequestBody User user)`
  - **请求参数**: JSON对象，User结构。
  - **响应**: JSON，含`code`(状态码), `msg`, `data`(User结构或null)。
- `@DeleteMapping("/user/{id}")`
  - **方法签名**: `public Dict delete(@PathVariable Long id)`
  - **请求参数**: 路径参数`id`(Long)。
  - **响应**: JSON，含`code`, `msg`。
- `@PutMapping("/user/{id}")`
  - **方法签名**: `public Dict update(@RequestBody User user, @PathVariable Long id)`
  - **请求参数**: 路径参数`id`，JSON体User。
  - **响应**: JSON，含`code`, `msg`, `data`。
- `@GetMapping("/user/{id}")`
  - **方法签名**: `public Dict getUser(@PathVariable Long id)`
  - **响应**: JSON，含User数据。
- `@GetMapping("/user")`
  - **方法签名**: `public Dict getUser(User user)`
  - **请求参数**: Query形式User属性，可选。
  - **响应**: JSON，`data`为用户列表。

**示例调用:**
```java
RestTemplate rest = new RestTemplate();
User user = new User(...); //填充字段
Dict resp = rest.postForObject("http://host/user", user, Dict.class);
```

---

#### 3.1.2 `com.xkcoding.orm.beetlsql.service.UserService`

**接口定义:**
- `User saveUser(User user)`
- `void saveUserList(List<User> users)`
- `void deleteUser(Long id)`
- `User updateUser(User user)`
- `User getUser(Long id)`
- `List<User> getUserList()`
- `PageQuery<User> getUserByPage(Integer currentPage, Integer pageSize)`

**用途:** 业务调用（非REST），通常被Controller层依赖注入。

**示例调用:**
```java
@Autowired
UserService userService;

User user = userService.saveUser(new User(...));
```

---

#### 3.1.3 `com.xkcoding.dynamic.datasource.controller.UserController`

- `@GetMapping("/user")`
  - **方法签名**: `public List<User> getUserList()`
  - **响应**: 用户列表，JSON数组。

---

#### 3.1.4 `com.xkcoding.swagger.controller.UserController`  
#### 3.1.5 `com.xkcoding.swagger.beauty.controller.UserController`

**接口路径：** `/user`

**主要REST方法（两者结构一致，均含Swagger注解）：**
- `@GetMapping`  
  `public ApiResponse<User> getByUserName(String username)`
- `@GetMapping("/{id}")`  
  `public ApiResponse<User> get(@PathVariable Integer id)`
- `@DeleteMapping("/{id}")`  
  `public void delete(@PathVariable Integer id)`
- `@PostMapping`  
  `public User post(@RequestBody User user)`
- `@PostMapping("/multipar")`  
  `public List<User> multipar(@RequestBody List<User> user)`
- `@PostMapping("/array")`  
  `public User[] array(@RequestBody User[] user)`
- `@PutMapping("/{id}")`  
  `public void put(@PathVariable Long id, @RequestBody User user)`
- `@PostMapping("/{id}/file")`  
  `public String file(@PathVariable Long id, @RequestParam("file") MultipartFile file)`

**请求/响应示例**：  
GET `/user?username=foo` 返回User对象（JSON）。

---

#### 3.1.6 `com.xkcoding.rbac.security.controller.AuthController`

- `@PostMapping("/api/auth/login")`
  - **方法签名**: `public ApiResponse login(@Valid @RequestBody LoginRequest loginRequest)`
  - **请求参数**: JSON对象，LoginRequest结构（用户名/密码等）。
  - **响应**: Json封装JwtResponse（token）。
- `@PostMapping("/api/auth/logout")`
  - **方法签名**: `public ApiResponse logout(HttpServletRequest request)`
  - **请求参数**: Cookie/Header含JWT。
  - **响应**: Json，注销状态。

---

### 3.2 代码生成相关

#### 3.2.1 `com.xkcoding.codegen.controller.CodeGenController`

**接口路径**: `/generator`

- `@GetMapping("/table")`
  - `public R listTables(TableRequest request)`
  - **请求参数**: Query参数，TableRequest结构（如currentPage, pageSize, tableName）。
  - **响应**: Json，分页表结构列表。
- `@PostMapping("")`
  - `public void generatorCode(@RequestBody GenConfig genConfig, HttpServletResponse response)`
  - **请求参数**: JSON体为GenConfig结构。
  - **响应**: HTTP下载流，Content-Type: application/zip。

---

#### 3.2.2 `com.xkcoding.codegen.service.CodeGenService`

- `byte[] generatorCode(GenConfig genConfig)`
- `PageResult<Entity> listTables(TableRequest request)`

**用法：**业务层接口，控制器依赖注入后调用。

---

### 3.3 定时任务相关

#### 3.3.1 `com.xkcoding.task.quartz.controller.JobController`

**接口路径**: `/job`

- `@PostMapping`
  - `public ResponseEntity<ApiResponse> addJob(@Valid JobForm form)`
- `@DeleteMapping`
  - `public ResponseEntity<ApiResponse> deleteJob(JobForm form)`
- `@PutMapping(params = "pause")`
  - `public ResponseEntity<ApiResponse> pauseJob(JobForm form)`
- `@PutMapping(params = "resume")`
  - `public ResponseEntity<ApiResponse> resumeJob(JobForm form)`
- `@PutMapping(params = "cron")`
  - `public ResponseEntity<ApiResponse> cronJob(@Valid JobForm form)`
- `@GetMapping`
  - `public ResponseEntity<ApiResponse> jobList(Integer currentPage, Integer pageSize)`

**请求参数**: JobForm结构或分页参数。

---

#### 3.3.2 `com.xkcoding.task.quartz.service.JobService`

- `void addJob(JobForm form)`
- `void deleteJob(JobForm form)`
- `void pauseJob(JobForm form)`
- `void resumeJob(JobForm form)`
- `void cronJob(JobForm form)`
- `PageInfo<JobAndTrigger> list(Integer currentPage, Integer pageSize)`

**业务层接口，配合Controller使用。**

---

### 3.4 文件上传相关

#### 3.4.1 `com.xkcoding.upload.controller.UploadController`

**接口路径**: `/upload`

- `@PostMapping("/local")`
  - `public Dict local(@RequestParam("file") MultipartFile file)`
  - **请求**: form-data文件上传
  - **响应**: Json，含文件名和本地路径
- `@PostMapping("/yun")`
  - `public Dict yun(@RequestParam("file") MultipartFile file)`
  - **请求**: form-data文件上传
  - **响应**: Json，含云端文件名和URL

---

#### 3.4.2 `com.xkcoding.upload.service.IQiNiuService`

- `Response uploadFile(File file) throws QiniuException`

**用法：**
```java
@Autowired
IQiNiuService qiNiuService;
qiNiuService.uploadFile(new File("/path/to/file"));
```

---

### 3.5 第三方登录（OAuth2）

#### 3.5.1 `com.xkcoding.social.controller.OauthController`

**接口路径**: `/oauth`

- `@GetMapping`
  - `public Map<String, String> loginType()`
  - **响应**: 各OAuth类型及跳转URL
- `@RequestMapping("/login/{oauthType}")`
  - `public void renderAuth(@PathVariable String oauthType, HttpServletResponse response)`
  - **重定向**到三方授权页
- `@RequestMapping("/{oauthType}/callback")`
  - `public AuthResponse login(@PathVariable String oauthType, AuthCallback callback)`
  - **请求参数**: callback为三方回调参数
  - **响应**: AuthResponse结构（用户三方授权结果）

---

### 3.6 动态数据源相关

#### 3.6.1 `com.xkcoding.dynamic.datasource.controller.DatasourceConfigController`

- `@PostMapping("/config")`
  - `public DatasourceConfig insertConfig(@RequestBody DatasourceConfig config)`
- `@DeleteMapping("/config/{id}")`
  - `public void removeConfig(@PathVariable Long id)`

---

### 3.7 配置/属性查询

#### 3.7.1 `com.xkcoding.properties.controller.PropertyController`

- `@GetMapping("/property")`
  - `public Dict index()`
  - **响应**: Json，含`applicationProperty`和`developerProperty`结构。

---

### 3.8 服务器监控与在线用户管理

#### 3.8.1 `com.xkcoding.websocket.controller.ServerController`

- `@GetMapping("/server")`
  - `public Dict serverInfo()`
  - **响应**: Json，包含服务器状态信息。

---

#### 3.8.2 `com.xkcoding.rbac.security.controller.MonitorController`

- `@GetMapping("/api/monitor/online/user")`
  - `public ApiResponse onlineUser(PageCondition pageCondition)`
  - **请求参数**: currentPage, pageSize
  - **响应**: 分页的在线用户信息
- `@DeleteMapping("/api/monitor/online/user/kickout")`
  - `public ApiResponse kickoutOnlineUser(@RequestBody List<String> names)`

---

### 3.9 实时消息/聊天相关

#### 3.9.1 `com.xkcoding.websocket.socketio.controller.MessageController`

- `@PostMapping("/send/broadcast")`
  - `public Dict broadcast(@RequestBody BroadcastMessageRequest message)`
  - **请求参数**: JSON体，含广播消息内容
  - **响应**: 发送状态

---

#### 3.9.2 `com.xkcoding.websocket.socketio.handler.MessageEventHandler`

**主要Socket.IO事件方法：**
- `@OnConnect public void onConnect(SocketIOClient client)`
- `@OnDisconnect public void onDisconnect(SocketIOClient client)`
- `@OnEvent(Event.JOIN) public void onJoinEvent(SocketIOClient client, AckRequest request, JoinRequest data)`
- `@OnEvent(Event.CHAT) public void onChatEvent(SocketIOClient client, AckRequest request, SingleMessageRequest data)`
- `@OnEvent(Event.GROUP) public void onGroupEvent(SocketIOClient client, AckRequest request, GroupMessageRequest data)`
- `public void sendToSingle(UUID sessionId, SingleMessageRequest message)`
- `public void sendToBroadcast(BroadcastMessageRequest message)`
- `public void sendToGroup(GroupMessageRequest message)`

**用法：** Socket.IO客户端与服务端连接后自动触发。

---

### 3.10 页面渲染与异常处理

#### 3.10.1 `com.xkcoding.session.controller.PageController`

- `@GetMapping("/page/index")`
  - `public ModelAndView index(HttpServletRequest request)`
- `@GetMapping("/page/login")`
  - `public ModelAndView login(Boolean redirect)`
- `@GetMapping("/page/doLogin")`
  - `public String doLogin(HttpSession session)`

---

#### 3.10.2 `com.xkcoding.template.freemarker.controller.IndexController`

- `@GetMapping(value = {"", "/"})`
  - `public ModelAndView index(HttpServletRequest request)`

---

#### 3.10.3 `com.xkcoding.template.freemarker.controller.UserController`

- `@PostMapping("/user/login")`
  - `public ModelAndView login(User user, HttpServletRequest request)`
- `@GetMapping("/user/login")`
  - `public ModelAndView login()`

---

#### 3.10.4 `com.xkcoding.exception.handler.controller.TestController`

- `@GetMapping("/json")`
  - `public ApiResponse jsonException()`
  - **效果**: 抛出JsonException，测试统一JSON异常处理
- `@GetMapping("/page")`
  - `public ModelAndView pageException()`
  - **效果**: 抛出PageException，测试页面异常处理

---

#### 3.10.5 `com.xkcoding.exception.handler.handler.DemoExceptionHandler`

- `@ExceptionHandler(JsonException.class)`
  - `public ApiResponse jsonErrorHandler(JsonException exception)`
- `@ExceptionHandler(PageException.class)`
  - `public ModelAndView pageErrorHandler(PageException exception)`

---

### 3.11 其它演示、测试与工具接口

#### 3.11.1 `com.xkcoding.helloworld.SpringBootDemoHelloworldApplication`

- `@GetMapping("/hello")`
  - `public String sayHello(@RequestParam(required=false, name="who") String who)`
  - **响应**: "Hello, {who}!"

---

#### 3.11.2 `com.xkcoding.ratelimit.guava.controller.TestController`

- `@GetMapping("/test1")` (限流)
- `@GetMapping("/test2")`
- `@GetMapping("/test3")` (限流)

**均返回Json消息。**

---

#### 3.11.3 `com.xkcoding.log.aop.controller.TestController`

- `@GetMapping("/test")`
  - `public Dict test(String who)`
- `@PostMapping("/testJson")`
  - `public Dict testJson(@RequestBody Map<String, Object> map)`

---

#### 3.11.4 `com.xkcoding.oauth.controller.TestController`

- `@GetMapping("/admin")`
- `@GetMapping("/test")`
- `@GetMapping("/read")`
- `@GetMapping("/write")`

**均有权限注解，返回字符串"ADMIN"/"TEST"/"READ"/"WRITE"**

---

### 3.12 典型数据结构说明

- **User**: 常见字段有id, username, password, nickname, phone, email, birthday, sex, status等。
- **Dict**: 用于返回Map结构的Json。
- **ApiResponse<T>**: 通用响应封装，含`code`, `message`, `data`字段。
- **JobForm**: 定时任务相关参数，含任务名、分组、Cron表达式等。
- **GenConfig/TableRequest**: 代码生成相关参数。
- **OnlineUser**: 用户在线信息（含脱敏手机号、邮箱）。
- **JwtResponse/LoginRequest**: 认证相关结构。
- **MultipartFile**: Spring上传文件对象，常见于上传接口。
- **PageResult<T>/PageInfo<T>**: 分页数据结构，含`total`和`data`列表。

---

### 3.13 外部import及调用方式

**Java代码调用样例:**
```java
import com.xkcoding.orm.jdbctemplate.controller.UserController;
import com.xkcoding.orm.jdbctemplate.entity.User;

// REST方式：用RestTemplate/HttpClient发请求
// 业务方式：@Autowired注入Controller/Service
@Autowired
UserController userController;
User user = ...;
Dict resp = userController.save(user);
```

**REST接口调用示例（curl）：**
```bash
curl -X POST http://host/user -H "Content-Type: application/json" -d '{"username":"foo","password":"bar"}'
```

**WebSocket示例：**
```javascript
const socket = io('ws://host:port');
socket.emit('CHAT', {fromUid: 'u1', toUid: 'u2', message: 'hi'});
```

---

**所有REST接口均建议通过HTTP协议访问，具体参数、响应结构详见源码及注释。业务/服务层需在Spring容器环境下使用。**