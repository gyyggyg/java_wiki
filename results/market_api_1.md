# 2. 对外提供接口说明文档

## 1. 功能分析

### 1.1 对外服务总览

本Java项目基于Spring Boot，主要针对电商领域，面向后台管理端（admin）、前台门户（portal）、搜索服务（search）、以及演示模块（demo）等多个子系统，统一提供了RESTful风格的HTTP API接口。这些接口覆盖了商品、订单、用户、促销、内容管理、支付、对象存储等核心业务，具体服务及其对应的主要控制器类如下：

| 服务模块             | 主要功能                                                                                         | 主要控制器类（Class）                         |
|----------------------|--------------------------------------------------------------------------------------------------|-----------------------------------------------|
| 商品管理             | 商品、品牌、分类、属性、库存的增删改查与配置                                                      | PmsProductController、PmsBrandController、PmsProductCategoryController、PmsProductAttributeController、PmsProductAttributeCategoryController、PmsSkuStockController |
| 内容管理             | 专题、广告、首页推荐品牌/新品/专题/人气商品等管理                                                 | CmsSubjectController、CmsPrefrenceAreaController、SmsHomeAdvertiseController、SmsHomeBrandController、SmsHomeNewProductController、SmsHomeRecommendProductController、SmsHomeRecommendSubjectController |
| 订单与售后管理       | 订单管理、退货申请、退货原因、订单设置、公司收货地址管理                                           | OmsOrderController、OmsOrderReturnApplyController、OmsOrderReturnReasonController、OmsOrderSettingController、OmsCompanyAddressController |
| 促销管理             | 优惠券、限时购活动、限时购商品关系、场次等管理                                                     | SmsCouponController、SmsCouponHistoryController、SmsFlashPromotionController、SmsFlashPromotionSessionController、SmsFlashPromotionProductRelationController |
| 对象存储管理         | 阿里云OSS、MinIO文件上传与删除                                                                   | OssController、MinioController                |
| 权限与用户管理       | 后台用户、角色、资源、菜单、会员等级、资源分类等管理                                               | UmsAdminController、UmsRoleController、UmsResourceController、UmsMenuController、UmsResourceCategoryController、UmsMemberLevelController |
| 前台会员服务         | 会员注册、登录、信息、收货地址、优惠券、购物车、订单、收藏、关注、浏览记录、退货申请等              | UmsMemberController、UmsMemberCouponController、UmsMemberReceiveAddressController、OmsCartItemController、OmsPortalOrderController、OmsPortalOrderReturnApplyController、MemberProductCollectionController、MemberAttentionController、MemberReadHistoryController |
| 前台商品与品牌服务   | 前台商品搜索、详情、分类树、品牌列表、品牌详情、品牌相关商品                                       | PmsPortalProductController、PmsPortalBrandController |
| 支付服务             | 支付宝支付（PC、H5）、支付通知、订单支付结果查询                                                  | AlipayController                              |
| 搜索服务             | 商品ES导入、ES商品搜索、推荐、相关属性获取                                                        | EsProductController                           |
| 演示与接口调用示例   | 品牌管理示例、RestTemplate调用示例                                                               | DemoController、RestTemplateDemoController    |

### 1.2 服务之间的关系

- **后台管理端（admin）**：负责商城管理全部后台业务，包括商品、订单、内容、用户、促销等管理服务。主要面向运营、管理员角色。
- **前台门户（portal）**：面向C端会员用户，涵盖商品浏览、下单、会员账户、收藏、购物车、订单、个人信息等。
- **搜索系统（search）**：为前台商品搜索、推荐等功能提供支持，基于Elasticsearch。
- **支付系统**：为商城订单支付提供统一接口，支持支付宝支付。
- **对象存储**：为商品、内容等文件（如图片）上传、删除提供统一接口，兼容阿里云OSS、MinIO。
- **演示与示例**：为开发者和测试人员提供标准API接口调用案例。

各模块间通过RESTful接口解耦协作，数据结构（如CommonResult、CommonPage）保持统一风格，便于前后端联调和系统扩展。

---

## 2. 调用类说明

### 2.1 后台管理端（admin）

| 控制器类名（Class）                | 功能描述           | 文件名                                                                                         | package名                          |
|------------------------------------|--------------------|------------------------------------------------------------------------------------------------|------------------------------------|
| CmsPrefrenceAreaController         | 商品优选专区管理   | mall-admin/src/main/java/com/macro/mall/controller/CmsPrefrenceAreaController.java             | com.macro.mall.controller          |
| CmsSubjectController               | 商品专题管理       | mall-admin/src/main/java/com/macro/mall/controller/CmsSubjectController.java                   | com.macro.mall.controller          |
| MinioController                    | MinIO对象存储管理 | mall-admin/src/main/java/com/macro/mall/controller/MinioController.java                        | com.macro.mall.controller          |
| OmsCompanyAddressController        | 公司收货地址管理   | mall-admin/src/main/java/com/macro/mall/controller/OmsCompanyAddressController.java            | com.macro.mall.controller          |
| OmsOrderController                 | 订单管理           | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderController.java                     | com.macro.mall.controller          |
| OmsOrderReturnApplyController      | 订单退货申请管理   | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderReturnApplyController.java          | com.macro.mall.controller          |
| OmsOrderReturnReasonController     | 退货原因管理       | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderReturnReasonController.java         | com.macro.mall.controller          |
| OmsOrderSettingController          | 订单设置管理       | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderSettingController.java              | com.macro.mall.controller          |
| OssController                      | 阿里云OSS管理      | mall-admin/src/main/java/com/macro/mall/controller/OssController.java                          | com.macro.mall.controller          |
| PmsBrandController                 | 商品品牌管理       | mall-admin/src/main/java/com/macro/mall/controller/PmsBrandController.java                     | com.macro.mall.controller          |
| PmsProductAttributeCategoryController | 商品属性分类管理 | mall-admin/src/main/java/com/macro/mall/controller/PmsProductAttributeCategoryController.java  | com.macro.mall.controller          |
| PmsProductAttributeController      | 商品属性管理       | mall-admin/src/main/java/com/macro/mall/controller/PmsProductAttributeController.java          | com.macro.mall.controller          |
| PmsProductCategoryController       | 商品分类管理       | mall-admin/src/main/java/com/macro/mall/controller/PmsProductCategoryController.java           | com.macro.mall.controller          |
| PmsProductController               | 商品管理           | mall-admin/src/main/java/com/macro/mall/controller/PmsProductController.java                   | com.macro.mall.controller          |
| PmsSkuStockController              | SKU库存管理        | mall-admin/src/main/java/com/macro/mall/controller/PmsSkuStockController.java                  | com.macro.mall.controller          |
| SmsCouponController                | 优惠券管理         | mall-admin/src/main/java/com/macro/mall/controller/SmsCouponController.java                    | com.macro.mall.controller          |
| SmsCouponHistoryController         | 优惠券领取记录     | mall-admin/src/main/java/com/macro/mall/controller/SmsCouponHistoryController.java             | com.macro.mall.controller          |
| SmsFlashPromotionController        | 限时购活动管理     | mall-admin/src/main/java/com/macro/mall/controller/SmsFlashPromotionController.java            | com.macro.mall.controller          |
| SmsFlashPromotionProductRelationController | 限时购商品关系管理 | mall-admin/src/main/java/com/macro/mall/controller/SmsFlashPromotionProductRelationController.java | com.macro.mall.controller      |
| SmsFlashPromotionSessionController | 限时购场次管理     | mall-admin/src/main/java/com/macro/mall/controller/SmsFlashPromotionSessionController.java     | com.macro.mall.controller          |
| SmsHomeAdvertiseController         | 首页轮播广告管理   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeAdvertiseController.java             | com.macro.mall.controller          |
| SmsHomeBrandController             | 首页品牌管理       | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeBrandController.java                 | com.macro.mall.controller          |
| SmsHomeNewProductController        | 首页新品管理       | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeNewProductController.java            | com.macro.mall.controller          |
| SmsHomeRecommendProductController  | 首页人气推荐管理   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeRecommendProductController.java      | com.macro.mall.controller          |
| SmsHomeRecommendSubjectController  | 首页专题推荐管理   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeRecommendSubjectController.java      | com.macro.mall.controller          |
| UmsAdminController                 | 后台用户管理       | mall-admin/src/main/java/com/macro/mall/controller/UmsAdminController.java                     | com.macro.mall.controller          |
| UmsMemberLevelController           | 会员等级管理       | mall-admin/src/main/java/com/macro/mall/controller/UmsMemberLevelController.java               | com.macro.mall.controller          |
| UmsMenuController                  | 后台菜单管理       | mall-admin/src/main/java/com/macro/mall/controller/UmsMenuController.java                      | com.macro.mall.controller          |
| UmsResourceCategoryController      | 资源分类管理       | mall-admin/src/main/java/com/macro/mall/controller/UmsResourceCategoryController.java          | com.macro.mall.controller          |
| UmsResourceController              | 后台资源管理       | mall-admin/src/main/java/com/macro/mall/controller/UmsResourceController.java                  | com.macro.mall.controller          |
| UmsRoleController                  | 后台角色管理       | mall-admin/src/main/java/com/macro/mall/controller/UmsRoleController.java                      | com.macro.mall.controller          |

### 2.2 前台门户（portal）

| 控制器类名（Class）                    | 功能描述                   | 文件名                                                                                         | package名                       |
|----------------------------------------|----------------------------|------------------------------------------------------------------------------------------------|---------------------------------|
| AlipayController                       | 支付宝支付相关接口         | mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java                | com.macro.mall.portal.controller|
| HomeController                         | 首页内容管理               | mall-portal/src/main/java/com/macro/mall/portal/controller/HomeController.java                  | com.macro.mall.portal.controller|
| MemberAttentionController              | 会员关注品牌管理           | mall-portal/src/main/java/com/macro/mall/portal/controller/MemberAttentionController.java       | com.macro.mall.portal.controller|
| MemberProductCollectionController      | 会员商品收藏管理           | mall-portal/src/main/java/com/macro/mall/portal/controller/MemberProductCollectionController.java| com.macro.mall.portal.controller|
| MemberReadHistoryController            | 会员浏览记录管理           | mall-portal/src/main/java/com/macro/mall/portal/controller/MemberReadHistoryController.java     | com.macro.mall.portal.controller|
| OmsCartItemController                  | 购物车管理                 | mall-portal/src/main/java/com/macro/mall/portal/controller/OmsCartItemController.java           | com.macro.mall.portal.controller|
| OmsPortalOrderController               | 订单管理                   | mall-portal/src/main/java/com/macro/mall/portal/controller/OmsPortalOrderController.java        | com.macro.mall.portal.controller|
| OmsPortalOrderReturnApplyController    | 订单退货申请               | mall-portal/src/main/java/com/macro/mall/portal/controller/OmsPortalOrderReturnApplyController.java | com.macro.mall.portal.controller|
| PmsPortalBrandController               | 前台品牌管理               | mall-portal/src/main/java/com/macro/mall/portal/controller/PmsPortalBrandController.java        | com.macro.mall.portal.controller|
| PmsPortalProductController             | 前台商品管理               | mall-portal/src/main/java/com/macro/mall/portal/controller/PmsPortalProductController.java      | com.macro.mall.portal.controller|
| UmsMemberController                    | 会员登录注册管理           | mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberController.java             | com.macro.mall.portal.controller|
| UmsMemberCouponController              | 用户优惠券管理             | mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberCouponController.java       | com.macro.mall.portal.controller|
| UmsMemberReceiveAddressController      | 会员收货地址管理           | mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberReceiveAddressController.java| com.macro.mall.portal.controller|

### 2.3 搜索服务（search）

| 控制器类名（Class）      | 功能描述                       | 文件名                                                                                 | package名                       |
|-------------------------|--------------------------------|----------------------------------------------------------------------------------------|---------------------------------|
| EsProductController     | 商品ES索引和搜索管理           | mall-search/src/main/java/com/macro/mall/search/controller/EsProductController.java     | com.macro.mall.search.controller|

### 2.4 演示与示例（demo）

| 控制器类名（Class）            | 功能描述              | 文件名                                                                                   | package名                          |
|-------------------------------|-----------------------|------------------------------------------------------------------------------------------|------------------------------------|
| DemoController                | 品牌管理示例接口      | mall-demo/src/main/java/com/macro/mall/demo/controller/DemoController.java               | com.macro.mall.demo.controller     |
| RestTemplateDemoController    | RestTemplate调用示例  | mall-demo/src/main/java/com/macro/mall/demo/controller/RestTemplateDemoController.java   | com.macro.mall.demo.controller     |

---

> 以上为本项目全部对外接口服务对应的核心控制器类、功能描述、源文件路径及包名，便于开发、运维及接口文档维护。后续每个控制器类的详细接口列表（URL、请求参数、响应结构等）可结合Swagger/OpenAPI自动化文档或进一步查阅源码获得。## 3. 数据结构说明

本章节针对第二章中涉及的所有对外API控制器类，详细列出各控制器类的全部对外服务方法，涵盖接口URL、方法签名、请求参数、响应参数结构及功能说明。所有接口统一采用RESTful风格，响应结构多数封装为`CommonResult<T>`或`CommonPage<T>`。

---

### 3.1 后台管理端（admin）

#### 3.1.1 `com.macro.mall.controller.CmsPrefrenceAreaController` 商品优选专区管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<CmsPrefrenceArea>> listAll()` | `/prefrenceArea/listAll` | GET | 无 | `CommonResult<List<CmsPrefrenceArea>>` | 获取所有商品优选专区 |

---

#### 3.1.2 `com.macro.mall.controller.CmsSubjectController` 商品专题管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<CmsSubject>> listAll()` | `/subject/listAll` | GET | 无 | `CommonResult<List<CmsSubject>>` | 获取全部商品专题 |
| `public CommonResult<CommonPage<CmsSubject>> getList(String keyword, Integer pageNum, Integer pageSize)` | `/subject/list` | GET | `keyword`(可选), `pageNum`, `pageSize` | `CommonResult<CommonPage<CmsSubject>>` | 按名称分页获取专题 |

---

#### 3.1.3 `com.macro.mall.controller.MinioController` MinIO对象存储管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult upload(MultipartFile file)` | `/minio/upload` | POST | `file`(form-data) | `CommonResult<MinioUploadDto>` | 文件上传到MinIO |
| `public CommonResult delete(String objectName)` | `/minio/delete` | POST | `objectName` | `CommonResult` | 删除指定文件 |

---

#### 3.1.4 `com.macro.mall.controller.OmsCompanyAddressController` 公司收货地址管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<OmsCompanyAddress>> list()` | `/companyAddress/list` | GET | 无 | `CommonResult<List<OmsCompanyAddress>>` | 获取所有收货地址 |

---

#### 3.1.5 `com.macro.mall.controller.OmsOrderController` 订单管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<CommonPage<OmsOrder>> list(OmsOrderQueryParam queryParam, Integer pageSize, Integer pageNum)` | `/order/list` | GET | 查询参数, `pageSize`, `pageNum` | `CommonResult<CommonPage<OmsOrder>>` | 查询订单 |
| `public CommonResult delivery(List<OmsOrderDeliveryParam> deliveryParamList)` | `/order/update/delivery` | POST | 请求体: 发货参数列表 | `CommonResult` | 批量发货 |
| `public CommonResult close(List<Long> ids, String note)` | `/order/update/close` | POST | `ids`, `note` | `CommonResult` | 批量关闭订单 |
| `public CommonResult delete(List<Long> ids)` | `/order/delete` | POST | `ids` | `CommonResult` | 批量删除订单 |
| `public CommonResult<OmsOrderDetail> detail(Long id)` | `/order/{id}` | GET | 路径参数: 订单ID | `CommonResult<OmsOrderDetail>` | 获取订单详情 |
| `public CommonResult updateReceiverInfo(OmsReceiverInfoParam param)` | `/order/update/receiverInfo` | POST | 请求体 | `CommonResult` | 修改收货人信息 |
| `public CommonResult updateReceiverInfo(OmsMoneyInfoParam param)` | `/order/update/moneyInfo` | POST | 请求体 | `CommonResult` | 修改订单费用信息 |
| `public CommonResult updateNote(Long id, String note, Integer status)` | `/order/update/note` | POST | `id`, `note`, `status` | `CommonResult` | 备注订单 |

---

#### 3.1.6 `com.macro.mall.controller.OmsOrderReturnApplyController` 订单退货申请管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<CommonPage<OmsOrderReturnApply>> list(OmsReturnApplyQueryParam queryParam, Integer pageSize, Integer pageNum)` | `/returnApply/list` | GET | 查询参数, `pageSize`, `pageNum` | `CommonResult<CommonPage<OmsOrderReturnApply>>` | 分页查询退货申请 |
| `public CommonResult delete(List<Long> ids)` | `/returnApply/delete` | POST | `ids` | `CommonResult` | 批量删除退货申请 |
| `public CommonResult getItem(Long id)` | `/returnApply/{id}` | GET | 路径参数 | `CommonResult<OmsOrderReturnApplyResult>` | 获取退货申请详情 |
| `public CommonResult updateStatus(Long id, OmsUpdateStatusParam statusParam)` | `/returnApply/update/status/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改退货申请状态 |

---

#### 3.1.7 `com.macro.mall.controller.OmsOrderReturnReasonController` 退货原因管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(OmsOrderReturnReason returnReason)` | `/returnReason/create` | POST | 请求体 | `CommonResult` | 添加退货原因 |
| `public CommonResult update(Long id, OmsOrderReturnReason returnReason)` | `/returnReason/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改退货原因 |
| `public CommonResult delete(List<Long> ids)` | `/returnReason/delete` | POST | `ids` | `CommonResult` | 批量删除退货原因 |
| `public CommonResult<CommonPage<OmsOrderReturnReason>> list(Integer pageSize, Integer pageNum)` | `/returnReason/list` | GET | `pageSize`, `pageNum` | `CommonResult<CommonPage<OmsOrderReturnReason>>` | 分页查询退货原因 |
| `public CommonResult<OmsOrderReturnReason> getItem(Long id)` | `/returnReason/{id}` | GET | 路径参数 | `CommonResult<OmsOrderReturnReason>` | 获取单个退货原因 |
| `public CommonResult updateStatus(Integer status, List<Long> ids)` | `/returnReason/update/status` | POST | `status`, `ids` | `CommonResult` | 修改启用状态 |

---

#### 3.1.8 `com.macro.mall.controller.OmsOrderSettingController` 订单设置管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<OmsOrderSetting> getItem(Long id)` | `/orderSetting/{id}` | GET | 路径参数 | `CommonResult<OmsOrderSetting>` | 获取指定订单设置 |
| `public CommonResult update(Long id, OmsOrderSetting orderSetting)` | `/orderSetting/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改指定订单设置 |

---

#### 3.1.9 `com.macro.mall.controller.OssController` 阿里云OSS管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<OssPolicyResult> policy()` | `/aliyun/oss/policy` | GET | 无 | `CommonResult<OssPolicyResult>` | 获取OSS上传签名策略 |
| `public CommonResult<OssCallbackResult> callback(HttpServletRequest request)` | `/aliyun/oss/callback` | POST | 回调参数 | `CommonResult<OssCallbackResult>` | OSS上传成功回调 |

---

#### 3.1.10 `com.macro.mall.controller.PmsBrandController` 商品品牌管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<PmsBrand>> getList()` | `/brand/listAll` | GET | 无 | `CommonResult<List<PmsBrand>>` | 获取全部品牌列表 |
| `public CommonResult create(PmsBrandParam pmsBrand)` | `/brand/create` | POST | 请求体 | `CommonResult` | 添加品牌 |
| `public CommonResult update(Long id, PmsBrandParam pmsBrandParam)` | `/brand/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 更新品牌 |
| `public CommonResult delete(Long id)` | `/brand/delete/{id}` | GET | 路径参数 | `CommonResult` | 删除品牌 |
| `public CommonResult<CommonPage<PmsBrand>> getList(String keyword, Integer showStatus, Integer pageNum, Integer pageSize)` | `/brand/list` | GET | 查询参数 | `CommonResult<CommonPage<PmsBrand>>` | 分页获取品牌列表 |
| `public CommonResult<PmsBrand> getItem(Long id)` | `/brand/{id}` | GET | 路径参数 | `CommonResult<PmsBrand>` | 获取品牌详情 |
| `public CommonResult deleteBatch(List<Long> ids)` | `/brand/delete/batch` | POST | `ids` | `CommonResult` | 批量删除品牌 |
| `public CommonResult updateShowStatus(List<Long> ids, Integer showStatus)` | `/brand/update/showStatus` | POST | `ids`, `showStatus` | `CommonResult` | 批量更新显示状态 |
| `public CommonResult updateFactoryStatus(List<Long> ids, Integer factoryStatus)` | `/brand/update/factoryStatus` | POST | `ids`, `factoryStatus` | `CommonResult` | 批量更新厂家制造商状态 |

---

#### 3.1.11 `com.macro.mall.controller.PmsProductAttributeCategoryController` 商品属性分类管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(String name)` | `/productAttribute/category/create` | POST | `name` | `CommonResult` | 添加属性分类 |
| `public CommonResult update(Long id, String name)` | `/productAttribute/category/update/{id}` | POST | 路径参数, `name` | `CommonResult` | 修改属性分类 |
| `public CommonResult delete(Long id)` | `/productAttribute/category/delete/{id}` | GET | 路径参数 | `CommonResult` | 删除单个属性分类 |
| `public CommonResult<PmsProductAttributeCategory> getItem(Long id)` | `/productAttribute/category/{id}` | GET | 路径参数 | `CommonResult<PmsProductAttributeCategory>` | 获取单个属性分类信息 |
| `public CommonResult<CommonPage<PmsProductAttributeCategory>> getList(Integer pageSize, Integer pageNum)` | `/productAttribute/category/list` | GET | `pageSize`, `pageNum` | `CommonResult<CommonPage<PmsProductAttributeCategory>>` | 分页获取所有属性分类 |
| `public CommonResult<List<PmsProductAttributeCategoryItem>> getListWithAttr()` | `/productAttribute/category/list/withAttr` | GET | 无 | `CommonResult<List<PmsProductAttributeCategoryItem>>` | 获取所有分类及属性 |

---

#### 3.1.12 `com.macro.mall.controller.PmsProductAttributeController` 商品属性管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<CommonPage<PmsProductAttribute>> getList(Long cid, Integer type, Integer pageSize, Integer pageNum)` | `/productAttribute/list/{cid}` | GET | 路径参数, `type`, `pageSize`, `pageNum` | `CommonResult<CommonPage<PmsProductAttribute>>` | 分类查询属性/参数列表 |
| `public CommonResult create(PmsProductAttributeParam param)` | `/productAttribute/create` | POST | 请求体 | `CommonResult` | 添加属性 |
| `public CommonResult update(Long id, PmsProductAttributeParam param)` | `/productAttribute/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改属性 |
| `public CommonResult<PmsProductAttribute> getItem(Long id)` | `/productAttribute/{id}` | GET | 路径参数 | `CommonResult<PmsProductAttribute>` | 查询单个属性 |
| `public CommonResult delete(List<Long> ids)` | `/productAttribute/delete` | POST | `ids` | `CommonResult` | 批量删除属性 |
| `public CommonResult<List<ProductAttrInfo>> getAttrInfo(Long productCategoryId)` | `/productAttribute/attrInfo/{productCategoryId}` | GET | 路径参数 | `CommonResult<List<ProductAttrInfo>>` | 根据分类ID获取属性及分类 |

---

#### 3.1.13 `com.macro.mall.controller.PmsProductCategoryController` 商品分类管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(PmsProductCategoryParam param)` | `/productCategory/create` | POST | 请求体 | `CommonResult` | 添加商品分类 |
| `public CommonResult update(Long id, PmsProductCategoryParam param)` | `/productCategory/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改商品分类 |
| `public CommonResult<CommonPage<PmsProductCategory>> getList(Long parentId, Integer pageSize, Integer pageNum)` | `/productCategory/list/{parentId}` | GET | 路径参数, `pageSize`, `pageNum` | `CommonResult<CommonPage<PmsProductCategory>>` | 分页查询商品分类 |
| `public CommonResult<PmsProductCategory> getItem(Long id)` | `/productCategory/{id}` | GET | 路径参数 | `CommonResult<PmsProductCategory>` | 获取分类信息 |
| `public CommonResult delete(Long id)` | `/productCategory/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除商品分类 |
| `public CommonResult updateNavStatus(List<Long> ids, Integer navStatus)` | `/productCategory/update/navStatus` | POST | `ids`, `navStatus` | `CommonResult` | 修改导航栏显示状态 |
| `public CommonResult updateShowStatus(List<Long> ids, Integer showStatus)` | `/productCategory/update/showStatus` | POST | `ids`, `showStatus` | `CommonResult` | 修改显示状态 |
| `public CommonResult<List<PmsProductCategoryWithChildrenItem>> listWithChildren()` | `/productCategory/list/withChildren` | GET | 无 | `CommonResult<List<PmsProductCategoryWithChildrenItem>>` | 查询所有一级分类及子分类 |

---

#### 3.1.14 `com.macro.mall.controller.PmsProductController` 商品管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(PmsProductParam param)` | `/product/create` | POST | 请求体 | `CommonResult` | 创建商品 |
| `public CommonResult<PmsProductResult> getUpdateInfo(Long id)` | `/product/updateInfo/{id}` | GET | 路径参数 | `CommonResult<PmsProductResult>` | 获取商品编辑信息 |
| `public CommonResult update(Long id, PmsProductParam param)` | `/product/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 更新商品 |
| `public CommonResult<CommonPage<PmsProduct>> getList(PmsProductQueryParam param, Integer pageSize, Integer pageNum)` | `/product/list` | GET | 查询参数 | `CommonResult<CommonPage<PmsProduct>>` | 查询商品 |
| `public CommonResult<List<PmsProduct>> getList(String keyword)` | `/product/simpleList` | GET | `keyword` | `CommonResult<List<PmsProduct>>` | 模糊查询商品 |
| `public CommonResult updateVerifyStatus(List<Long> ids, Integer verifyStatus, String detail)` | `/product/update/verifyStatus` | POST | `ids`, `verifyStatus`, `detail` | `CommonResult` | 批量修改审核状态 |
| `public CommonResult updatePublishStatus(List<Long> ids, Integer publishStatus)` | `/product/update/publishStatus` | POST | `ids`, `publishStatus` | `CommonResult` | 批量上下架 |
| `public CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | `/product/update/recommendStatus` | POST | `ids`, `recommendStatus` | `CommonResult` | 批量推荐 |
| `public CommonResult updateNewStatus(List<Long> ids, Integer newStatus)` | `/product/update/newStatus` | POST | `ids`, `newStatus` | `CommonResult` | 批量设为新品 |
| `public CommonResult updateDeleteStatus(List<Long> ids, Integer deleteStatus)` | `/product/update/deleteStatus` | POST | `ids`, `deleteStatus` | `CommonResult` | 批量修改删除状态 |

---

#### 3.1.15 `com.macro.mall.controller.PmsSkuStockController` SKU库存管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<PmsSkuStock>> getList(Long pid, String keyword)` | `/sku/{pid}` | GET | 路径参数, `keyword` | `CommonResult<List<PmsSkuStock>>` | 根据商品ID及sku编码模糊搜索库存 |
| `public CommonResult update(Long pid, List<PmsSkuStock> skuStockList)` | `/sku/update/{pid}` | POST | 路径参数, 请求体 | `CommonResult` | 批量更新SKU库存 |

---

#### 3.1.16 `com.macro.mall.controller.SmsCouponController` 优惠券管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult add(SmsCouponParam couponParam)` | `/coupon/create` | POST | 请求体 | `CommonResult` | 添加优惠券 |
| `public CommonResult delete(Long id)` | `/coupon/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除优惠券 |
| `public CommonResult update(Long id, SmsCouponParam couponParam)` | `/coupon/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改优惠券 |
| `public CommonResult<CommonPage<SmsCoupon>> list(String name, Integer type, Integer pageSize, Integer pageNum)` | `/coupon/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsCoupon>>` | 分页获取优惠券 |
| `public CommonResult<SmsCouponParam> getItem(Long id)` | `/coupon/{id}` | GET | 路径参数 | `CommonResult<SmsCouponParam>` | 获取优惠券详情 |

---

#### 3.1.17 `com.macro.mall.controller.SmsCouponHistoryController` 优惠券领取记录

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<CommonPage<SmsCouponHistory>> list(Long couponId, Integer useStatus, String orderSn, Integer pageSize, Integer pageNum)` | `/couponHistory/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsCouponHistory>>` | 分页获取领取记录 |

---

#### 3.1.18 `com.macro.mall.controller.SmsFlashPromotionController` 限时购活动管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(SmsFlashPromotion flashPromotion)` | `/flash/create` | POST | 请求体 | `CommonResult` | 添加活动 |
| `public CommonResult update(Long id, SmsFlashPromotion flashPromotion)` | `/flash/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 编辑活动 |
| `public CommonResult delete(Long id)` | `/flash/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除活动 |
| `public CommonResult update(Long id, Integer status)` | `/flash/update/status/{id}` | POST | 路径参数, `status` | `CommonResult` | 修改上下线状态 |
| `public CommonResult<SmsFlashPromotion> getItem(Long id)` | `/flash/{id}` | GET | 路径参数 | `CommonResult<SmsFlashPromotion>` | 获取活动详情 |
| `public CommonResult<CommonPage<SmsFlashPromotion>> getItem(String keyword, Integer pageSize, Integer pageNum)` | `/flash/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsFlashPromotion>>` | 分页查询 |

---

#### 3.1.19 `com.macro.mall.controller.SmsFlashPromotionProductRelationController` 限时购商品关系管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(List<SmsFlashPromotionProductRelation> relationList)` | `/flashProductRelation/create` | POST | 请求体 | `CommonResult` | 批量添加关联 |
| `public CommonResult update(Long id, SmsFlashPromotionProductRelation relation)` | `/flashProductRelation/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改关联信息 |
| `public CommonResult delete(Long id)` | `/flashProductRelation/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除关联 |
| `public CommonResult<SmsFlashPromotionProductRelation> getItem(Long id)` | `/flashProductRelation/{id}` | GET | 路径参数 | `CommonResult<SmsFlashPromotionProductRelation>` | 获取关联信息 |
| `public CommonResult<CommonPage<SmsFlashPromotionProduct>> list(Long flashPromotionId, Long flashPromotionSessionId, Integer pageSize, Integer pageNum)` | `/flashProductRelation/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsFlashPromotionProduct>>` | 分页查询 |

---

#### 3.1.20 `com.macro.mall.controller.SmsFlashPromotionSessionController` 限时购场次管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(SmsFlashPromotionSession promotionSession)` | `/flashSession/create` | POST | 请求体 | `CommonResult` | 添加场次 |
| `public CommonResult update(Long id, SmsFlashPromotionSession promotionSession)` | `/flashSession/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改场次 |
| `public CommonResult updateStatus(Long id, Integer status)` | `/flashSession/update/status/{id}` | POST | 路径参数, `status` | `CommonResult` | 修改启用状态 |
| `public CommonResult delete(Long id)` | `/flashSession/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除场次 |
| `public CommonResult<SmsFlashPromotionSession> getItem(Long id)` | `/flashSession/{id}` | GET | 路径参数 | `CommonResult<SmsFlashPromotionSession>` | 获取场次详情 |
| `public CommonResult<List<SmsFlashPromotionSession>> list()` | `/flashSession/list` | GET | 无 | `CommonResult<List<SmsFlashPromotionSession>>` | 获取全部场次 |
| `public CommonResult<List<SmsFlashPromotionSessionDetail>> selectList(Long flashPromotionId)` | `/flashSession/selectList` | GET | `flashPromotionId` | `CommonResult<List<SmsFlashPromotionSessionDetail>>` | 获取可选场次及数量 |

---

#### 3.1.21 `com.macro.mall.controller.SmsHomeAdvertiseController` 首页轮播广告管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(SmsHomeAdvertise advertise)` | `/home/advertise/create` | POST | 请求体 | `CommonResult` | 添加广告 |
| `public CommonResult delete(List<Long> ids)` | `/home/advertise/delete` | POST | `ids` | `CommonResult` | 删除广告 |
| `public CommonResult updateStatus(Long id, Integer status)` | `/home/advertise/update/status/{id}` | POST | 路径参数, `status` | `CommonResult` | 修改上下线状态 |
| `public CommonResult<SmsHomeAdvertise> getItem(Long id)` | `/home/advertise/{id}` | GET | 路径参数 | `CommonResult<SmsHomeAdvertise>` | 获取广告详情 |
| `public CommonResult update(Long id, SmsHomeAdvertise advertise)` | `/home/advertise/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改广告 |
| `public CommonResult<CommonPage<SmsHomeAdvertise>> list(String name, Integer type, String endTime, Integer pageSize, Integer pageNum)` | `/home/advertise/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsHomeAdvertise>>` | 分页查询广告 |

---

#### 3.1.22 `com.macro.mall.controller.SmsHomeBrandController` 首页品牌管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(List<SmsHomeBrand> homeBrandList)` | `/home/brand/create` | POST | 请求体 | `CommonResult` | 添加首页推荐品牌 |
| `public CommonResult updateSort(Long id, Integer sort)` | `/home/brand/update/sort/{id}` | POST | 路径参数, `sort` | `CommonResult` | 修改排序 |
| `public CommonResult delete(List<Long> ids)` | `/home/brand/delete` | POST | `ids` | `CommonResult` | 批量删除推荐品牌 |
| `public CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | `/home/brand/update/recommendStatus` | POST | `ids`, `recommendStatus` | `CommonResult` | 批量修改推荐状态 |
| `public CommonResult<CommonPage<SmsHomeBrand>> list(String brandName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | `/home/brand/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsHomeBrand>>` | 分页查询推荐品牌 |

---

#### 3.1.23 `com.macro.mall.controller.SmsHomeNewProductController` 首页新品管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(List<SmsHomeNewProduct> homeNewProductList)` | `/home/newProduct/create` | POST | 请求体 | `CommonResult` | 添加首页新品 |
| `public CommonResult updateSort(Long id, Integer sort)` | `/home/newProduct/update/sort/{id}` | POST | 路径参数, `sort` | `CommonResult` | 修改排序 |
| `public CommonResult delete(List<Long> ids)` | `/home/newProduct/delete` | POST | `ids` | `CommonResult` | 批量删除新品 |
| `public CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | `/home/newProduct/update/recommendStatus` | POST | `ids`, `recommendStatus` | `CommonResult` | 批量修改新品推荐状态 |
| `public CommonResult<CommonPage<SmsHomeNewProduct>> list(String productName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | `/home/newProduct/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsHomeNewProduct>>` | 分页查询新品 |

---

#### 3.1.24 `com.macro.mall.controller.SmsHomeRecommendProductController` 首页人气推荐管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(List<SmsHomeRecommendProduct> homeRecommendProductList)` | `/home/recommendProduct/create` | POST | 请求体 | `CommonResult` | 添加首页推荐 |
| `public CommonResult updateSort(Long id, Integer sort)` | `/home/recommendProduct/update/sort/{id}` | POST | 路径参数, `sort` | `CommonResult` | 修改排序 |
| `public CommonResult delete(List<Long> ids)` | `/home/recommendProduct/delete` | POST | `ids` | `CommonResult` | 批量删除推荐 |
| `public CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | `/home/recommendProduct/update/recommendStatus` | POST | `ids`, `recommendStatus` | `CommonResult` | 批量修改推荐状态 |
| `public CommonResult<CommonPage<SmsHomeRecommendProduct>> list(String productName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | `/home/recommendProduct/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsHomeRecommendProduct>>` | 分页查询推荐 |

---

#### 3.1.25 `com.macro.mall.controller.SmsHomeRecommendSubjectController` 首页专题推荐管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(List<SmsHomeRecommendSubject> homeRecommendSubjectList)` | `/home/recommendSubject/create` | POST | 请求体 | `CommonResult` | 添加专题推荐 |
| `public CommonResult updateSort(Long id, Integer sort)` | `/home/recommendSubject/update/sort/{id}` | POST | 路径参数, `sort` | `CommonResult` | 修改排序 |
| `public CommonResult delete(List<Long> ids)` | `/home/recommendSubject/delete` | POST | `ids` | `CommonResult` | 批量删除专题推荐 |
| `public CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | `/home/recommendSubject/update/recommendStatus` | POST | `ids`, `recommendStatus` | `CommonResult` | 批量修改推荐状态 |
| `public CommonResult<CommonPage<SmsHomeRecommendSubject>> list(String subjectName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | `/home/recommendSubject/list` | GET | 查询参数 | `CommonResult<CommonPage<SmsHomeRecommendSubject>>` | 分页查询专题推荐 |

---

#### 3.1.26 `com.macro.mall.controller.UmsAdminController` 后台用户管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<UmsAdmin> register(UmsAdminParam umsAdminParam)` | `/admin/register` | POST | 请求体 | `CommonResult<UmsAdmin>` | 用户注册 |
| `public CommonResult login(UmsAdminLoginParam umsAdminLoginParam)` | `/admin/login` | POST | 请求体 | `CommonResult<Map<String,String>>` | 登录获取token |
| `public CommonResult refreshToken(HttpServletRequest request)` | `/admin/refreshToken` | GET | header: token | `CommonResult<Map<String,String>>` | 刷新token |
| `public CommonResult getAdminInfo(Principal principal)` | `/admin/info` | GET | header: token | `CommonResult<Map<String,Object>>` | 获取当前登录用户信息 |
| `public CommonResult logout(Principal principal)` | `/admin/logout` | POST | header: token | `CommonResult` | 登出 |
| `public CommonResult<CommonPage<UmsAdmin>> list(String keyword, Integer pageSize, Integer pageNum)` | `/admin/list` | GET | 查询参数 | `CommonResult<CommonPage<UmsAdmin>>` | 用户列表 |
| `public CommonResult<UmsAdmin> getItem(Long id)` | `/admin/{id}` | GET | 路径参数 | `CommonResult<UmsAdmin>` | 获取指定用户信息 |
| `public CommonResult update(Long id, UmsAdmin admin)` | `/admin/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改指定用户信息 |
| `public CommonResult updatePassword(UpdateAdminPasswordParam param)` | `/admin/updatePassword` | POST | 请求体 | `CommonResult` | 修改密码 |
| `public CommonResult delete(Long id)` | `/admin/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除用户 |
| `public CommonResult updateStatus(Long id, Integer status)` | `/admin/updateStatus/{id}` | POST | 路径参数, `status` | `CommonResult` | 修改帐号状态 |
| `public CommonResult updateRole(Long adminId, List<Long> roleIds)` | `/admin/role/update` | POST | `adminId`, `roleIds` | `CommonResult` | 分配角色 |
| `public CommonResult<List<UmsRole>> getRoleList(Long adminId)` | `/admin/role/{adminId}` | GET | 路径参数 | `CommonResult<List<UmsRole>>` | 获取角色列表 |

---

#### 3.1.27 `com.macro.mall.controller.UmsMemberLevelController` 会员等级管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<UmsMemberLevel>> list(Integer defaultStatus)` | `/memberLevel/list` | GET | `defaultStatus` | `CommonResult<List<UmsMemberLevel>>` | 查询所有会员等级 |

---

#### 3.1.28 `com.macro.mall.controller.UmsMenuController` 后台菜单管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(UmsMenu umsMenu)` | `/menu/create` | POST | 请求体 | `CommonResult` | 添加菜单 |
| `public CommonResult update(Long id, UmsMenu umsMenu)` | `/menu/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改菜单 |
| `public CommonResult<UmsMenu> getItem(Long id)` | `/menu/{id}` | GET | 路径参数 | `CommonResult<UmsMenu>` | 获取菜单详情 |
| `public CommonResult delete(Long id)` | `/menu/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除菜单 |
| `public CommonResult<CommonPage<UmsMenu>> list(Long parentId, Integer pageSize, Integer pageNum)` | `/menu/list/{parentId}` | GET | 路径参数, `pageSize`, `pageNum` | `CommonResult<CommonPage<UmsMenu>>` | 分页查询菜单 |
| `public CommonResult<List<UmsMenuNode>> treeList()` | `/menu/treeList` | GET | 无 | `CommonResult<List<UmsMenuNode>>` | 树形结构返回菜单 |
| `public CommonResult updateHidden(Long id, Integer hidden)` | `/menu/updateHidden/{id}` | POST | 路径参数, `hidden` | `CommonResult` | 修改显示状态 |

---

#### 3.1.29 `com.macro.mall.controller.UmsResourceCategoryController` 资源分类管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<UmsResourceCategory>> listAll()` | `/resourceCategory/listAll` | GET | 无 | `CommonResult<List<UmsResourceCategory>>` | 查询所有资源分类 |
| `public CommonResult create(UmsResourceCategory category)` | `/resourceCategory/create` | POST | 请求体 | `CommonResult` | 添加资源分类 |
| `public CommonResult update(Long id, UmsResourceCategory category)` | `/resourceCategory/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改资源分类 |
| `public CommonResult delete(Long id)` | `/resourceCategory/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除资源分类 |

---

#### 3.1.30 `com.macro.mall.controller.UmsResourceController` 后台资源管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(UmsResource umsResource)` | `/resource/create` | POST | 请求体 | `CommonResult` | 添加资源 |
| `public CommonResult update(Long id, UmsResource umsResource)` | `/resource/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改资源 |
| `public CommonResult<UmsResource> getItem(Long id)` | `/resource/{id}` | GET | 路径参数 | `CommonResult<UmsResource>` | 获取资源详情 |
| `public CommonResult delete(Long id)` | `/resource/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除资源 |
| `public CommonResult<CommonPage<UmsResource>> list(Long categoryId, String nameKeyword, String urlKeyword, Integer pageSize, Integer pageNum)` | `/resource/list` | GET | 查询参数 | `CommonResult<CommonPage<UmsResource>>` | 分页模糊查询资源 |
| `public CommonResult<List<UmsResource>> listAll()` | `/resource/listAll` | GET | 无 | `CommonResult<List<UmsResource>>` | 查询所有资源 |

---

#### 3.1.31 `com.macro.mall.controller.UmsRoleController` 后台角色管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(UmsRole role)` | `/role/create` | POST | 请求体 | `CommonResult` | 添加角色 |
| `public CommonResult update(Long id, UmsRole role)` | `/role/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改角色 |
| `public CommonResult delete(List<Long> ids)` | `/role/delete` | POST | `ids` | `CommonResult` | 批量删除角色 |
| `public CommonResult<List<UmsRole>> listAll()` | `/role/listAll` | GET | 无 | `CommonResult<List<UmsRole>>` | 获取所有角色 |
| `public CommonResult<CommonPage<UmsRole>> list(String keyword, Integer pageSize, Integer pageNum)` | `/role/list` | GET | 查询参数 | `CommonResult<CommonPage<UmsRole>>` | 分页获取角色列表 |
| `public CommonResult updateStatus(Long id, Integer status)` | `/role/updateStatus/{id}` | POST | 路径参数, `status` | `CommonResult` | 修改角色状态 |
| `public CommonResult<List<UmsMenu>> listMenu(Long roleId)` | `/role/listMenu/{roleId}` | GET | 路径参数 | `CommonResult<List<UmsMenu>>` | 获取角色相关菜单 |
| `public CommonResult<List<UmsResource>> listResource(Long roleId)` | `/role/listResource/{roleId}` | GET | 路径参数 | `CommonResult<List<UmsResource>>` | 获取角色相关资源 |
| `public CommonResult allocMenu(Long roleId, List<Long> menuIds)` | `/role/allocMenu` | POST | `roleId`, `menuIds` | `CommonResult` | 分配菜单 |
| `public CommonResult allocResource(Long roleId, List<Long> resourceIds)` | `/role/allocResource` | POST | `roleId`, `resourceIds` | `CommonResult` | 分配资源 |

---

### 3.2 前台门户（portal）

#### 3.2.1 `com.macro.mall.portal.controller.AlipayController` 支付宝支付接口

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public void pay(AliPayParam aliPayParam, HttpServletResponse response)` | `/alipay/pay` | GET | `AliPayParam`(form/query) | HTML | 电脑网站支付表单 |
| `public void webPay(AliPayParam aliPayParam, HttpServletResponse response)` | `/alipay/webPay` | GET | `AliPayParam`(form/query) | HTML | 手机网站支付表单 |
| `public String notify(HttpServletRequest request)` | `/alipay/notify` | POST | 回调参数 | `String(success/failure)` | 支付宝异步回调 |
| `public CommonResult<String> query(String outTradeNo, String tradeNo)` | `/alipay/query` | GET | `outTradeNo`, `tradeNo` | `CommonResult<String>` | 订单支付状态查询 |

---

#### 3.2.2 `com.macro.mall.portal.controller.HomeController` 首页内容管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<HomeContentResult> content()` | `/home/content` | GET | 无 | `CommonResult<HomeContentResult>` | 首页内容信息展示 |
| `public CommonResult<List<PmsProduct>> recommendProductList(Integer pageSize, Integer pageNum)` | `/home/recommendProductList` | GET | `pageSize`, `pageNum` | `CommonResult<List<PmsProduct>>` | 分页获取推荐商品 |
| `public CommonResult<List<PmsProductCategory>> getProductCateList(Long parentId)` | `/home/productCateList/{parentId}` | GET | 路径参数 | `CommonResult<List<PmsProductCategory>>` | 获取首页商品分类 |
| `public CommonResult<List<CmsSubject>> getSubjectList(Long cateId, Integer pageSize, Integer pageNum)` | `/home/subjectList` | GET | 查询参数 | `CommonResult<List<CmsSubject>>` | 分类分页获取专题 |
| `public CommonResult<List<PmsProduct>> hotProductList(Integer pageNum, Integer pageSize)` | `/home/hotProductList` | GET | `pageNum`, `pageSize` | `CommonResult<List<PmsProduct>>` | 分页获取人气推荐商品 |
| `public CommonResult<List<PmsProduct>> newProductList(Integer pageNum, Integer pageSize)` | `/home/newProductList` | GET | `pageNum`, `pageSize` | `CommonResult<List<PmsProduct>>` | 分页获取新品推荐 |

---

#### 3.2.3 `com.macro.mall.portal.controller.MemberAttentionController` 会员关注品牌管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult add(MemberBrandAttention memberBrandAttention)` | `/member/attention/add` | POST | 请求体 | `CommonResult` | 添加品牌关注 |
| `public CommonResult delete(Long brandId)` | `/member/attention/delete` | POST | `brandId` | `CommonResult` | 取消关注 |
| `public CommonResult<CommonPage<MemberBrandAttention>> list(Integer pageNum, Integer pageSize)` | `/member/attention/list` | GET | `pageNum`, `pageSize` | `CommonResult<CommonPage<MemberBrandAttention>>` | 分页关注列表 |
| `public CommonResult<MemberBrandAttention> detail(Long brandId)` | `/member/attention/detail` | GET | `brandId` | `CommonResult<MemberBrandAttention>` | 获取关注详情 |
| `public CommonResult clear()` | `/member/attention/clear` | POST | 无 | `CommonResult` | 清空关注列表 |

---

#### 3.2.4 `com.macro.mall.portal.controller.MemberProductCollectionController` 会员商品收藏管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult add(MemberProductCollection productCollection)` | `/member/productCollection/add` | POST | 请求体 | `CommonResult` | 添加商品收藏 |
| `public CommonResult delete(Long productId)` | `/member/productCollection/delete` | POST | `productId` | `CommonResult` | 删除收藏 |
| `public CommonResult<CommonPage<MemberProductCollection>> list(Integer pageNum, Integer pageSize)` | `/member/productCollection/list` | GET | `pageNum`, `pageSize` | `CommonResult<CommonPage<MemberProductCollection>>` | 分页收藏列表 |
| `public CommonResult<MemberProductCollection> detail(Long productId)` | `/member/productCollection/detail` | GET | `productId` | `CommonResult<MemberProductCollection>` | 收藏详情 |
| `public CommonResult clear()` | `/member/productCollection/clear` | POST | 无 | `CommonResult` | 清空收藏 |

---

#### 3.2.5 `com.macro.mall.portal.controller.MemberReadHistoryController` 会员浏览记录管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(MemberReadHistory memberReadHistory)` | `/member/readHistory/create` | POST | 请求体 | `CommonResult` | 创建浏览记录 |
| `public CommonResult delete(List<String> ids)` | `/member/readHistory/delete` | POST | `ids` | `CommonResult` | 删除浏览记录 |
| `public CommonResult clear()` | `/member/readHistory/clear` | POST | 无 | `CommonResult` | 清空浏览记录 |
| `public CommonResult<CommonPage<MemberReadHistory>> list(Integer pageNum, Integer pageSize)` | `/member/readHistory/list` | GET | `pageNum`, `pageSize` | `CommonResult<CommonPage<MemberReadHistory>>` | 分页获取浏览记录 |

---

#### 3.2.6 `com.macro.mall.portal.controller.OmsCartItemController` 购物车管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult add(OmsCartItem cartItem)` | `/cart/add` | POST | 请求体 | `CommonResult` | 添加商品到购物车 |
| `public CommonResult<List<OmsCartItem>> list()` | `/cart/list` | GET | 无 | `CommonResult<List<OmsCartItem>>` | 获取购物车列表 |
| `public CommonResult<List<CartPromotionItem>> listPromotion(List<Long> cartIds)` | `/cart/list/promotion` | GET | `cartIds`(可选) | `CommonResult<List<CartPromotionItem>>` | 获取购物车促销信息 |
| `public CommonResult updateQuantity(Long id, Integer quantity)` | `/cart/update/quantity` | GET | `id`, `quantity` | `CommonResult` | 修改购物车商品数量 |
| `public CommonResult<CartProduct> getCartProduct(Long productId)` | `/cart/getProduct/{productId}` | GET | 路径参数 | `CommonResult<CartProduct>` | 获取商品规格 |
| `public CommonResult updateAttr(OmsCartItem cartItem)` | `/cart/update/attr` | POST | 请求体 | `CommonResult` | 修改规格 |
| `public CommonResult delete(List<Long> ids)` | `/cart/delete` | POST | `ids` | `CommonResult` | 删除购物车商品 |
| `public CommonResult clear()` | `/cart/clear` | POST | 无 | `CommonResult` | 清空购物车 |

---

#### 3.2.7 `com.macro.mall.portal.controller.OmsPortalOrderController` 订单管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<ConfirmOrderResult> generateConfirmOrder(List<Long> cartIds)` | `/order/generateConfirmOrder` | POST | 请求体 | `CommonResult<ConfirmOrderResult>` | 生成确认单 |
| `public CommonResult generateOrder(OrderParam orderParam)` | `/order/generateOrder` | POST | 请求体 | `CommonResult<Map>` | 下单 |
| `public CommonResult paySuccess(Long orderId, Integer payType)` | `/order/paySuccess` | POST | `orderId`, `payType` | `CommonResult` | 支付成功回调 |
| `public CommonResult cancelTimeOutOrder()` | `/order/cancelTimeOutOrder` | POST | 无 | `CommonResult` | 自动取消超时订单 |
| `public CommonResult cancelOrder(Long orderId)` | `/order/cancelOrder` | POST | `orderId` | `CommonResult` | 取消单个超时订单 |
| `public CommonResult<CommonPage<OmsOrderDetail>> list(Integer status, Integer pageNum, Integer pageSize)` | `/order/list` | GET | `status`, `pageNum`, `pageSize` | `CommonResult<CommonPage<OmsOrderDetail>>` | 分页获取订单列表 |
| `public CommonResult<OmsOrderDetail> detail(Long orderId)` | `/order/detail/{orderId}` | GET | 路径参数 | `CommonResult<OmsOrderDetail>` | 获取订单详情 |
| `public CommonResult cancelUserOrder(Long orderId)` | `/order/cancelUserOrder` | POST | `orderId` | `CommonResult` | 用户取消订单 |
| `public CommonResult confirmReceiveOrder(Long orderId)` | `/order/confirmReceiveOrder` | POST | `orderId` | `CommonResult` | 用户确认收货 |
| `public CommonResult deleteOrder(Long orderId)` | `/order/deleteOrder` | POST | `orderId` | `CommonResult` | 用户删除订单 |

---

#### 3.2.8 `com.macro.mall.portal.controller.OmsPortalOrderReturnApplyController` 退货申请

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult create(OmsOrderReturnApplyParam returnApply)` | `/returnApply/create` | POST | 请求体 | `CommonResult` | 用户退货申请 |

---

#### 3.2.9 `com.macro.mall.portal.controller.PmsPortalBrandController` 前台品牌管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<PmsBrand>> recommendList(Integer pageSize, Integer pageNum)` | `/brand/recommendList` | GET | `pageSize`, `pageNum` | `CommonResult<List<PmsBrand>>` | 分页获取推荐品牌 |
| `public CommonResult<PmsBrand> detail(Long brandId)` | `/brand/detail/{brandId}` | GET | 路径参数 | `CommonResult<PmsBrand>` | 获取品牌详情 |
| `public CommonResult<CommonPage<PmsProduct>> productList(Long brandId, Integer pageNum, Integer pageSize)` | `/brand/productList` | GET | `brandId`, `pageNum`, `pageSize` | `CommonResult<CommonPage<PmsProduct>>` | 分页获取品牌相关商品 |

---

#### 3.2.10 `com.macro.mall.portal.controller.PmsPortalProductController` 前台商品管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<CommonPage<PmsProduct>> search(String keyword, Long brandId, Long productCategoryId, Integer pageNum, Integer pageSize, Integer sort)` | `/product/search` | GET | 查询参数 | `CommonResult<CommonPage<PmsProduct>>` | 综合搜索/筛选/排序 |
| `public CommonResult<List<PmsProductCategoryNode>> categoryTreeList()` | `/product/categoryTreeList` | GET | 无 | `CommonResult<List<PmsProductCategoryNode>>` | 树形结构获取分类 |
| `public CommonResult<PmsPortalProductDetail> detail(Long id)` | `/product/detail/{id}` | GET | 路径参数 | `CommonResult<PmsPortalProductDetail>` | 获取商品详情 |

---

#### 3.2.11 `com.macro.mall.portal.controller.UmsMemberController` 会员登录注册管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult register(String username, String password, String telephone, String authCode)` | `/sso/register` | POST | `username`, `password`, `telephone`, `authCode` | `CommonResult` | 会员注册 |
| `public CommonResult login(String username, String password)` | `/sso/login` | POST | `username`, `password` | `CommonResult<Map<String,String>>` | 登录 |
| `public CommonResult info(Principal principal)` | `/sso/info` | GET | header: token | `CommonResult<UmsMember>` | 获取会员信息 |
| `public CommonResult getAuthCode(String telephone)` | `/sso/getAuthCode` | GET | `telephone` | `CommonResult<String>` | 获取验证码 |
| `public CommonResult updatePassword(String telephone, String password, String authCode)` | `/sso/updatePassword` | POST | `telephone`, `password`, `authCode` | `CommonResult` | 修改密码 |
| `public CommonResult refreshToken(HttpServletRequest request)` | `/sso/refreshToken` | GET | header: token | `CommonResult<Map<String,String>>` | 刷新token |

---

#### 3.2.12 `com.macro.mall.portal.controller.UmsMemberCouponController` 用户优惠券管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult add(Long couponId)` | `/member/coupon/add/{couponId}` | POST | 路径参数 | `CommonResult` | 领取指定优惠券 |
| `public CommonResult<List<SmsCouponHistory>> listHistory(Integer useStatus)` | `/member/coupon/listHistory` | GET | `useStatus` | `CommonResult<List<SmsCouponHistory>>` | 优惠券历史列表 |
| `public CommonResult<List<SmsCoupon>> list(Integer useStatus)` | `/member/coupon/list` | GET | `useStatus` | `CommonResult<List<SmsCoupon>>` | 优惠券列表 |
| `public CommonResult<List<SmsCouponHistoryDetail>> listCart(Integer type)` | `/member/coupon/list/cart/{type}` | GET | 路径参数 | `CommonResult<List<SmsCouponHistoryDetail>>` | 购物车相关优惠券 |
| `public CommonResult<List<SmsCoupon>> listByProduct(Long productId)` | `/member/coupon/listByProduct/{productId}` | GET | 路径参数 | `CommonResult<List<SmsCoupon>>` | 当前商品相关优惠券 |

---

#### 3.2.13 `com.macro.mall.portal.controller.UmsMemberReceiveAddressController` 会员收货地址管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult add(UmsMemberReceiveAddress address)` | `/member/address/add` | POST | 请求体 | `CommonResult` | 添加收货地址 |
| `public CommonResult delete(Long id)` | `/member/address/delete/{id}` | POST | 路径参数 | `CommonResult` | 删除收货地址 |
| `public CommonResult update(Long id, UmsMemberReceiveAddress address)` | `/member/address/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 修改收货地址 |
| `public CommonResult<List<UmsMemberReceiveAddress>> list()` | `/member/address/list` | GET | 无 | `CommonResult<List<UmsMemberReceiveAddress>>` | 获取所有收货地址 |
| `public CommonResult<UmsMemberReceiveAddress> getItem(Long id)` | `/member/address/{id}` | GET | 路径参数 | `CommonResult<UmsMemberReceiveAddress>` | 获取收货地址详情 |

---

### 3.3 搜索服务（search）

#### 3.3.1 `com.macro.mall.search.controller.EsProductController` 商品ES索引和搜索管理

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<Integer> importAllList()` | `/esProduct/importAll` | POST | 无 | `CommonResult<Integer>` | 导入数据库所有商品到ES |
| `public CommonResult<Object> delete(Long id)` | `/esProduct/delete/{id}` | GET | 路径参数 | `CommonResult` | 删除单个商品 |
| `public CommonResult<Object> delete(List<Long> ids)` | `/esProduct/delete/batch` | POST | `ids` | `CommonResult` | 批量删除商品 |
| `public CommonResult<EsProduct> create(Long id)` | `/esProduct/create/{id}` | POST | 路径参数 | `CommonResult<EsProduct>` | 根据ID创建商品 |
| `public CommonResult<CommonPage<EsProduct>> search(String keyword, Integer pageNum, Integer pageSize)` | `/esProduct/search/simple` | GET | 查询参数 | `CommonResult<CommonPage<EsProduct>>` | 简单搜索 |
| `public CommonResult<CommonPage<EsProduct>> search(String keyword, Long brandId, Long productCategoryId, Integer pageNum, Integer pageSize, Integer sort)` | `/esProduct/search` | GET | 查询参数 | `CommonResult<CommonPage<EsProduct>>` | 综合搜索/筛选/排序 |
| `public CommonResult<CommonPage<EsProduct>> recommend(Long id, Integer pageNum, Integer pageSize)` | `/esProduct/recommend/{id}` | GET | 路径参数, 分页 | `CommonResult<CommonPage<EsProduct>>` | 推荐商品 |
| `public CommonResult<EsProductRelatedInfo> searchRelatedInfo(String keyword)` | `/esProduct/search/relate` | GET | `keyword` | `CommonResult<EsProductRelatedInfo>` | 获取相关品牌/分类/属性 |

---

### 3.4 演示与示例（demo）

#### 3.4.1 `com.macro.mall.demo.controller.DemoController` 品牌管理示例

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public CommonResult<List<PmsBrand>> getBrandList()` | `/brand/listAll` | GET | 无 | `CommonResult<List<PmsBrand>>` | 获取全部品牌 |
| `public CommonResult createBrand(PmsBrandDto pmsBrand)` | `/brand/create` | POST | 请求体 | `CommonResult` | 添加品牌 |
| `public CommonResult updateBrand(Long id, PmsBrandDto pmsBrandDto)` | `/brand/update/{id}` | POST | 路径参数, 请求体 | `CommonResult` | 更新品牌 |
| `public CommonResult deleteBrand(Long id)` | `/brand/delete/{id}` | GET | 路径参数 | `CommonResult` | 删除品牌 |
| `public CommonResult<CommonPage<PmsBrand>> listBrand(Integer pageNum, Integer pageSize)` | `/brand/list` | GET | 分页参数 | `CommonResult<CommonPage<PmsBrand>>` | 分页获取品牌 |
| `public CommonResult<PmsBrand> brand(Long id)` | `/brand/{id}` | GET | 路径参数 | `CommonResult<PmsBrand>` | 根据编号查询品牌 |

---

#### 3.4.2 `com.macro.mall.demo.controller.RestTemplateDemoController` RestTemplate调用示例

| 方法签名 | 路径 | 方法 | 请求参数 | 响应结构 | 说明 |
|----------|------|------|----------|----------|------|
| `public Object getForEntity(Long id)` | `/template/get/{id}` | GET | 路径参数 | 转发响应 | GET调用品牌详情 |
| `public Object getForEntity2(Long id)` | `/template/get2/{id}` | GET | 路径参数 | 转发响应 | GET调用品牌详情(参数Map) |
| `public Object getForEntity3(Long id)` | `/template/get3/{id}` | GET | 路径参数 | 转发响应 | GET调用品牌详情(URI) |
| `public Object getForObject(Long id)` | `/template/get4/{id}` | GET | 路径参数 | 转发响应 | GET调用品牌详情(Object) |
| `public Object postForEntity(PmsBrand brand)` | `/template/post` | POST | 请求体 | 转发响应 | POST调用品牌创建 |
| `public Object postForObject(PmsBrand brand)` | `/template/post2` | POST | 请求体 | 转发响应 | POST调用品牌创建(Object) |
| `public Object postForEntity3(String name)` | `/template/post3` | POST | `name` | 转发响应 | POST调用属性分类创建（表单） |

---

> **注：** 各接口详细的请求体、响应结构请参考Swagger自动化API文档，或查阅源码中相关DTO、VO、Param等数据模型定义。所有返回结构均以`CommonResult<T>`进行统一封装，状态码与消息字段可用于前后端联调判别业务处理结果。
来源文件id为 [512, 513, 514, 515, 516, 257, 258, 580, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 504, 505, 506, 507, 508, 509, 510, 511]