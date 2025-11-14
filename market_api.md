# 2. 对外提供接口说明文档

## 1. 功能分析

### 1.1 服务概览

本Java项目为一个典型的电商系统，按业务模块对外提供丰富的RESTful API服务，面向电商后台管理端与商城前台客户。主要对外服务可归纳如下：

| 服务模块           | 主要功能描述                                              | 典型接口URL/路径举例              |
|--------------------|---------------------------------------------------------|-----------------------------------|
| 商品管理           | 商品、品牌、分类、属性、库存等全生命周期管理              | /product, /brand, /productCategory, /sku |
| 订单及售后管理     | 订单查询、发货、关闭、退货、退货原因、订单设置等          | /order, /returnApply, /returnReason, /orderSetting |
| 促销活动           | 优惠券、优惠券领取、限时购、首页广告/推荐等管理            | /coupon, /flash, /home/advertise, /home/brand, /home/newProduct, /home/recommendProduct, /home/recommendSubject |
| 会员与权限         | 用户注册、登录、权限、菜单、角色、资源、会员地址/等级等     | /admin, /sso, /role, /menu, /resource, /memberLevel, /member/address |
| 内容管理           | 商品专题、优选专区                                        | /subject, /prefrenceArea          |
| 存储管理           | MinIO、阿里云OSS文件上传与删除                            | /minio, /aliyun/oss               |
| 搜索服务           | 基于Elasticsearch的商品检索、推荐、相关属性查询            | /esProduct                        |
| 前台商城           | 首页内容、商品浏览、收藏、购物车、订单、支付、优惠券等      | /home, /product, /cart, /order, /alipay, /member/* |
| 示例/演示接口      | 品牌管理、RestTemplate调用演示                             | /brand (demo), /template          |

### 1.2 服务之间的关系

- **后台管理模块**（如商品、订单、促销、权限）：为商城管理后台提供数据增删改查、批量操作、状态管理等服务，确保电商管理运营。
- **前台商城模块**：为终端客户提供商品浏览、下单、购物车、支付、收藏、浏览历史等功能，接口与后台部分服务有数据流交互（如商品、订单、优惠券等）。
- **存储与搜索支持**：MinIO、OSS接口为图片/文件存储提供支撑；ES搜索接口为商品检索等功能提供数据索引和推荐能力。
- **权限与认证**：UmsAdminController、UmsMemberController等保证后台及前台用户认证、权限、角色、菜单等安全体系。
- **内容及促销**：专题、广告、品牌推荐等内容模块为首页及推广活动提供内容源，与商品、促销等模块存在数据联动。

各服务通过接口调用、数据模型共享、权限校验等方式协同工作，覆盖电商系统的主流核心业务场景。

---

## 2. 调用类说明

### 2.1 后台管理端接口类

| 类名                                   | 功能描述                           | 所属文件                                                                   | package                          |
|----------------------------------------|------------------------------------|----------------------------------------------------------------------------|-----------------------------------|
| CmsPrefrenceAreaController             | 商品优选管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/CmsPrefrenceAreaController.java | com.macro.mall.controller         |
| CmsSubjectController                   | 商品专题管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/CmsSubjectController.java         | com.macro.mall.controller         |
| MinioController                        | MinIO文件上传/删除接口             | mall-admin/src/main/java/com/macro/mall/controller/MinioController.java              | com.macro.mall.controller         |
| OssController                          | OSS签名生成及上传回调接口          | mall-admin/src/main/java/com/macro/mall/controller/OssController.java                | com.macro.mall.controller         |
| OmsOrderController                     | 订单管理接口                       | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderController.java           | com.macro.mall.controller         |
| OmsOrderReturnApplyController          | 订单退货申请管理                   | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderReturnApplyController.java| com.macro.mall.controller         |
| OmsOrderReturnReasonController         | 退货原因管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderReturnReasonController.java| com.macro.mall.controller       |
| OmsOrderSettingController              | 订单设置管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/OmsOrderSettingController.java    | com.macro.mall.controller         |
| PmsBrandController                     | 商品品牌管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/PmsBrandController.java           | com.macro.mall.controller         |
| PmsProductController                   | 商品管理接口                       | mall-admin/src/main/java/com/macro/mall/controller/PmsProductController.java         | com.macro.mall.controller         |
| PmsProductCategoryController           | 商品分类管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/PmsProductCategoryController.java | com.macro.mall.controller         |
| PmsProductAttributeController          | 商品属性管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/PmsProductAttributeController.java| com.macro.mall.controller         |
| PmsProductAttributeCategoryController  | 商品属性分类管理接口               | mall-admin/src/main/java/com/macro/mall/controller/PmsProductAttributeCategoryController.java | com.macro.mall.controller |
| PmsSkuStockController                  | SKU库存管理接口                    | mall-admin/src/main/java/com/macro/mall/controller/PmsSkuStockController.java        | com.macro.mall.controller         |
| OmsCompanyAddressController            | 收货地址管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/OmsCompanyAddressController.java  | com.macro.mall.controller         |
| SmsCouponController                    | 优惠券管理接口                     | mall-admin/src/main/java/com/macro/mall/controller/SmsCouponController.java          | com.macro.mall.controller         |
| SmsCouponHistoryController             | 优惠券领取历史管理接口             | mall-admin/src/main/java/com/macro/mall/controller/SmsCouponHistoryController.java   | com.macro.mall.controller         |
| SmsFlashPromotionController            | 限时购活动管理接口                 | mall-admin/src/main/java/com/macro/mall/controller/SmsFlashPromotionController.java  | com.macro.mall.controller         |
| SmsFlashPromotionSessionController     | 限时购场次管理接口                 | mall-admin/src/main/java/com/macro/mall/controller/SmsFlashPromotionSessionController.java | com.macro.mall.controller  |
| SmsFlashPromotionProductRelationController | 限时购商品关系管理接口           | mall-admin/src/main/java/com/macro/mall/controller/SmsFlashPromotionProductRelationController.java | com.macro.mall.controller |
| SmsHomeAdvertiseController             | 首页轮播广告管理                   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeAdvertiseController.java   | com.macro.mall.controller         |
| SmsHomeBrandController                 | 首页品牌推荐管理                   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeBrandController.java       | com.macro.mall.controller         |
| SmsHomeNewProductController            | 首页新品推荐管理                   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeNewProductController.java  | com.macro.mall.controller         |
| SmsHomeRecommendProductController      | 首页人气推荐管理                   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeRecommendProductController.java | com.macro.mall.controller  |
| SmsHomeRecommendSubjectController      | 首页专题推荐管理                   | mall-admin/src/main/java/com/macro/mall/controller/SmsHomeRecommendSubjectController.java | com.macro.mall.controller  |
| UmsAdminController                     | 后台管理员用户管理                 | mall-admin/src/main/java/com/macro/mall/controller/UmsAdminController.java           | com.macro.mall.controller         |
| UmsRoleController                      | 后台角色管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/UmsRoleController.java            | com.macro.mall.controller         |
| UmsMenuController                      | 后台菜单管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/UmsMenuController.java            | com.macro.mall.controller         |
| UmsResourceController                  | 后台资源管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/UmsResourceController.java        | com.macro.mall.controller         |
| UmsResourceCategoryController          | 后台资源分类管理接口               | mall-admin/src/main/java/com/macro/mall/controller/UmsResourceCategoryController.java| com.macro.mall.controller         |
| UmsMemberLevelController               | 会员等级管理接口                   | mall-admin/src/main/java/com/macro/mall/controller/UmsMemberLevelController.java     | com.macro.mall.controller         |

### 2.2 前台商城端接口类

| 类名                                  | 功能描述                             | 所属文件                                                           | package                          |
|---------------------------------------|--------------------------------------|--------------------------------------------------------------------|-----------------------------------|
| HomeController                        | 首页内容与推荐商品                   | mall-portal/src/main/java/com/macro/mall/portal/controller/HomeController.java | com.macro.mall.portal.controller  |
| UmsMemberController                   | 会员注册、登录、认证信息、验证码等    | mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberController.java | com.macro.mall.portal.controller  |
| UmsMemberCouponController             | 会员优惠券领取与查询                 | mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberCouponController.java | com.macro.mall.portal.controller  |
| UmsMemberReceiveAddressController     | 会员收货地址管理                     | mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberReceiveAddressController.java | com.macro.mall.portal.controller  |
| MemberAttentionController             | 会员品牌关注                         | mall-portal/src/main/java/com/macro/mall/portal/controller/MemberAttentionController.java | com.macro.mall.portal.controller  |
| MemberProductCollectionController     | 会员商品收藏                         | mall-portal/src/main/java/com/macro/mall/portal/controller/MemberProductCollectionController.java | com.macro.mall.portal.controller  |
| MemberReadHistoryController           | 会员浏览历史管理                     | mall-portal/src/main/java/com/macro/mall/portal/controller/MemberReadHistoryController.java | com.macro.mall.portal.controller  |
| OmsCartItemController                 | 购物车管理                           | mall-portal/src/main/java/com/macro/mall/portal/controller/OmsCartItemController.java | com.macro.mall.portal.controller  |
| OmsPortalOrderController              | 订单下单、支付、取消、查询等         | mall-portal/src/main/java/com/macro/mall/portal/controller/OmsPortalOrderController.java | com.macro.mall.portal.controller  |
| OmsPortalOrderReturnApplyController   | 前台订单退货申请                     | mall-portal/src/main/java/com/macro/mall/portal/controller/OmsPortalOrderReturnApplyController.java | com.macro.mall.portal.controller  |
| AlipayController                      | 支付宝支付接口                       | mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java | com.macro.mall.portal.controller  |
| PmsPortalBrandController              | 品牌推荐、详情、品牌商品列表         | mall-portal/src/main/java/com/macro/mall/portal/controller/PmsPortalBrandController.java | com.macro.mall.portal.controller  |
| PmsPortalProductController            | 商品搜索、分类树、详情               | mall-portal/src/main/java/com/macro/mall/portal/controller/PmsPortalProductController.java | com.macro.mall.portal.controller  |

### 2.3 搜索服务接口类

| 类名               | 功能描述             | 所属文件                                                    | package                           |
|--------------------|----------------------|-------------------------------------------------------------|------------------------------------|
| EsProductController| ES商品搜索管理接口   | mall-search/src/main/java/com/macro/mall/search/controller/EsProductController.java | com.github.dockerjava.core.command |

### 2.4 示例/演示接口类

| 类名                        | 功能描述           | 所属文件                                                           | package                           |
|-----------------------------|--------------------|--------------------------------------------------------------------|------------------------------------|
| DemoController              | 品牌管理演示接口   | mall-demo/src/main/java/com/macro/mall/demo/controller/DemoController.java | com.github.dockerjava.api.command  |
| RestTemplateDemoController  | RestTemplate示例   | mall-demo/src/main/java/com/macro/mall/demo/controller/RestTemplateDemoController.java | com.github.dockerjava.api.command  |

---

**说明：**
- 所有对外接口均基于Spring Boot，采用REST风格，路径、参数、字段名严格区分大小写。
- 部分接口（如商品、订单、优惠券等）在后台与前台均有不同维度的实现，分别服务于管理端与C端用户。
- 存储与搜索相关接口（如MinioController、OssController、EsProductController）为电商主业务功能提供底层支撑。
- 权限、认证、会员、菜单等接口共同构建平台的安全与权限体系。
- 示例/演示接口（DemoController等）用于开发调试和接口调用示例。

---## 3. 数据结构说明

### 3.1 后台管理端接口类

#### 3.1.1 `com.macro.mall.controller.CmsPrefrenceAreaController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `public CommonResult<List<CmsPrefrenceArea>> listAll()` | /prefrenceArea/listAll | GET | 无 | `[CmsPrefrenceArea]` | 获取所有商品优选专区信息 |

---

#### 3.1.2 `com.macro.mall.controller.CmsSubjectController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `public CommonResult<List<CmsSubject>> listAll()` | /subject/listAll | GET | 无 | `[CmsSubject]` | 获取全部商品专题 |
| `public CommonResult<CommonPage<CmsSubject>> getList(String keyword, Integer pageNum, Integer pageSize)` | /subject/list | GET | `keyword`(可选), `pageNum`, `pageSize` | 分页`[CmsSubject]` | 根据专题名称分页获取商品专题 |

---

#### 3.1.3 `com.macro.mall.controller.MinioController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `public CommonResult upload(MultipartFile file)` | /minio/upload | POST | `file`(form-data) | 上传结果（含文件名、URL） | 文件上传到MinIO |
| `public CommonResult delete(String objectName)` | /minio/delete | POST | `objectName` | 操作结果 | 文件删除 |

---

#### 3.1.4 `com.macro.mall.controller.OssController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `public CommonResult<OssPolicyResult> policy()` | /aliyun/oss/policy | GET | 无 | `OssPolicyResult` | 生成OSS上传签名策略 |
| `public CommonResult<OssCallbackResult> callback(HttpServletRequest request)` | /aliyun/oss/callback | POST | HTTP请求体 | `OssCallbackResult` | OSS上传成功回调 |

---

#### 3.1.5 `com.macro.mall.controller.OmsOrderController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<CommonPage<OmsOrder>> list(OmsOrderQueryParam, Integer pageSize, Integer pageNum)` | /order/list | GET | 查询参数、分页 | 分页订单 | 查询订单 |
| `CommonResult delivery(List<OmsOrderDeliveryParam>)` | /order/update/delivery | POST | 发货参数列表 | 操作结果 | 批量发货 |
| `CommonResult close(List<Long> ids, String note)` | /order/update/close | POST | `ids`,`note` | 操作结果 | 批量关闭订单 |
| `CommonResult delete(List<Long> ids)` | /order/delete | POST | `ids` | 操作结果 | 批量删除订单 |
| `CommonResult<OmsOrderDetail> detail(Long id)` | /order/{id} | GET | `id` | 订单详情 | 获取订单详情 |
| `CommonResult updateReceiverInfo(OmsReceiverInfoParam)` | /order/update/receiverInfo | POST | 收货人信息 | 操作结果 | 修改收货人信息 |
| `CommonResult updateMoneyInfo(OmsMoneyInfoParam)` | /order/update/moneyInfo | POST | 费用信息 | 操作结果 | 修改订单费用信息 |
| `CommonResult updateNote(Long id, String note, Integer status)` | /order/update/note | POST | `id`, `note`, `status` | 操作结果 | 备注订单 |

---

#### 3.1.6 `com.macro.mall.controller.OmsOrderReturnApplyController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<CommonPage<OmsOrderReturnApply>> list(OmsReturnApplyQueryParam, pageSize, pageNum)` | /returnApply/list | GET | 查询参数、分页 | 分页退货申请 | 分页查询退货申请 |
| `CommonResult delete(List<Long> ids)` | /returnApply/delete | POST | `ids` | 操作结果 | 批量删除退货申请 |
| `CommonResult getItem(Long id)` | /returnApply/{id} | GET | `id` | 退货申请详情 | 获取退货申请详情 |
| `CommonResult updateStatus(Long id, OmsUpdateStatusParam)` | /returnApply/update/status/{id} | POST | 状态参数 | 操作结果 | 修改退货申请状态 |

---

#### 3.1.7 `com.macro.mall.controller.OmsOrderReturnReasonController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(OmsOrderReturnReason)` | /returnReason/create | POST | 退货原因 | 操作结果 | 添加退货原因 |
| `CommonResult update(Long id, OmsOrderReturnReason)` | /returnReason/update/{id} | POST | `id`, 退货原因 | 操作结果 | 修改退货原因 |
| `CommonResult delete(List<Long> ids)` | /returnReason/delete | POST | `ids` | 操作结果 | 批量删除退货原因 |
| `CommonResult<CommonPage<OmsOrderReturnReason>> list(pageSize, pageNum)` | /returnReason/list | GET | 分页 | 分页退货原因 | 分页查询退货原因 |
| `CommonResult<OmsOrderReturnReason> getItem(Long id)` | /returnReason/{id} | GET | `id` | 退货原因详情 | 获取退货原因详情 |
| `CommonResult updateStatus(Integer status, List<Long> ids)` | /returnReason/update/status | POST | `status`, `ids` | 操作结果 | 修改退货原因启用状态 |

---

#### 3.1.8 `com.macro.mall.controller.OmsOrderSettingController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<OmsOrderSetting> getItem(Long id)` | /orderSetting/{id} | GET | `id` | 订单设置 | 获取指定订单设置 |
| `CommonResult update(Long id, OmsOrderSetting)` | /orderSetting/update/{id} | POST | `id`,订单设置 | 操作结果 | 修改订单设置 |

---

#### 3.1.9 `com.macro.mall.controller.PmsBrandController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<List<PmsBrand>> getList()` | /brand/listAll | GET | 无 | `[PmsBrand]` | 获取全部品牌列表 |
| `CommonResult create(PmsBrandParam)` | /brand/create | POST | 品牌参数 | 操作结果 | 添加品牌 |
| `CommonResult update(Long id, PmsBrandParam)` | /brand/update/{id} | POST | `id`,品牌参数 | 操作结果 | 更新品牌 |
| `CommonResult delete(Long id)` | /brand/delete/{id} | GET | `id` | 操作结果 | 删除品牌 |
| `CommonResult<CommonPage<PmsBrand>> getList(String keyword, Integer showStatus, Integer pageNum, Integer pageSize)` | /brand/list | GET | 搜索条件、分页 | 分页品牌 | 分页获取品牌 |
| `CommonResult<PmsBrand> getItem(Long id)` | /brand/{id} | GET | `id` | 品牌详情 | 根据编号查询品牌信息 |
| `CommonResult deleteBatch(List<Long> ids)` | /brand/delete/batch | POST | `ids` | 操作结果 | 批量删除品牌 |
| `CommonResult updateShowStatus(List<Long> ids, Integer showStatus)` | /brand/update/showStatus | POST | `ids`, `showStatus` | 操作结果 | 批量更新显示状态 |
| `CommonResult updateFactoryStatus(List<Long> ids, Integer factoryStatus)` | /brand/update/factoryStatus | POST | `ids`,`factoryStatus` | 操作结果 | 批量更新厂家状态 |

---

#### 3.1.10 `com.macro.mall.controller.PmsProductController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(PmsProductParam)` | /product/create | POST | 商品参数 | 操作结果 | 创建商品 |
| `CommonResult<PmsProductResult> getUpdateInfo(Long id)` | /product/updateInfo/{id} | GET | `id` | 商品编辑信息 | 获取商品编辑信息 |
| `CommonResult update(Long id, PmsProductParam)` | /product/update/{id} | POST | `id`,商品参数 | 操作结果 | 更新商品 |
| `CommonResult<CommonPage<PmsProduct>> getList(PmsProductQueryParam, Integer pageSize, Integer pageNum)` | /product/list | GET | 查询、分页 | 分页商品 | 查询商品 |
| `CommonResult<List<PmsProduct>> getList(String keyword)` | /product/simpleList | GET | `keyword` | 商品列表 | 模糊查询 |
| `CommonResult updateVerifyStatus(List<Long> ids, Integer verifyStatus, String detail)` | /product/update/verifyStatus | POST | `ids`,`verifyStatus`,`detail` | 操作结果 | 批量审核 |
| `CommonResult updatePublishStatus(List<Long> ids, Integer publishStatus)` | /product/update/publishStatus | POST | `ids`,`publishStatus` | 操作结果 | 上下架 |
| `CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | /product/update/recommendStatus | POST | `ids`,`recommendStatus` | 操作结果 | 批量推荐 |
| `CommonResult updateNewStatus(List<Long> ids, Integer newStatus)` | /product/update/newStatus | POST | `ids`,`newStatus` | 操作结果 | 批量设为新品 |
| `CommonResult updateDeleteStatus(List<Long> ids, Integer deleteStatus)` | /product/update/deleteStatus | POST | `ids`,`deleteStatus` | 操作结果 | 批量修改删除状态 |

---

#### 3.1.11 `com.macro.mall.controller.PmsProductCategoryController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(PmsProductCategoryParam)` | /productCategory/create | POST | 分类参数 | 操作结果 | 添加分类 |
| `CommonResult update(Long id, PmsProductCategoryParam)` | /productCategory/update/{id} | POST | `id`,分类参数 | 操作结果 | 更新分类 |
| `CommonResult<CommonPage<PmsProductCategory>> getList(Long parentId, Integer pageSize, Integer pageNum)` | /productCategory/list/{parentId} | GET | `parentId`,分页 | 分页分类 | 分页查询分类 |
| `CommonResult<PmsProductCategory> getItem(Long id)` | /productCategory/{id} | GET | `id` | 分类详情 | 获取分类 |
| `CommonResult delete(Long id)` | /productCategory/delete/{id} | POST | `id` | 操作结果 | 删除分类 |
| `CommonResult updateNavStatus(List<Long> ids, Integer navStatus)` | /productCategory/update/navStatus | POST | `ids`, `navStatus` | 操作结果 | 修改导航栏状态 |
| `CommonResult updateShowStatus(List<Long> ids, Integer showStatus)` | /productCategory/update/showStatus | POST | `ids`,`showStatus` | 操作结果 | 修改显示状态 |
| `CommonResult<List<PmsProductCategoryWithChildrenItem>> listWithChildren()` | /productCategory/list/withChildren | GET | 无 | 分类树 | 查询所有一级及子分类 |

---

#### 3.1.12 `com.macro.mall.controller.PmsProductAttributeController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<CommonPage<PmsProductAttribute>> getList(Long cid, Integer type, Integer pageSize, Integer pageNum)` | /productAttribute/list/{cid} | GET | `cid`, `type`,分页 | 分页属性 | 分类查询属性/参数 |
| `CommonResult create(PmsProductAttributeParam)` | /productAttribute/create | POST | 属性参数 | 操作结果 | 添加属性信息 |
| `CommonResult update(Long id, PmsProductAttributeParam)` | /productAttribute/update/{id} | POST | `id`,属性参数 | 操作结果 | 修改属性信息 |
| `CommonResult<PmsProductAttribute> getItem(Long id)` | /productAttribute/{id} | GET | `id` | 属性详情 | 查询单个属性 |
| `CommonResult delete(List<Long> ids)` | /productAttribute/delete | POST | `ids` | 操作结果 | 批量删除属性 |
| `CommonResult<List<ProductAttrInfo>> getAttrInfo(Long categoryId)` | /productAttribute/attrInfo/{categoryId} | GET | `categoryId` | 属性及分类 | 获取分类属性及分类 |

---

#### 3.1.13 `com.macro.mall.controller.PmsProductAttributeCategoryController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(String name)` | /productAttribute/category/create | POST | `name` | 操作结果 | 新增属性分类 |
| `CommonResult update(Long id, String name)` | /productAttribute/category/update/{id} | POST | `id`, `name` | 操作结果 | 修改属性分类 |
| `CommonResult delete(Long id)` | /productAttribute/category/delete/{id} | GET | `id` | 操作结果 | 删除属性分类 |
| `CommonResult<PmsProductAttributeCategory> getItem(Long id)` | /productAttribute/category/{id} | GET | `id` | 详情 | 获取单个分类 |
| `CommonResult<CommonPage<PmsProductAttributeCategory>> getList(Integer pageSize, Integer pageNum)` | /productAttribute/category/list | GET | 分页 | 分页属性分类 | 分页获取所有属性分类 |
| `CommonResult<List<PmsProductAttributeCategoryItem>> getListWithAttr()` | /productAttribute/category/list/withAttr | GET | 无 | 分类及属性 | 获取所有分类及属性 |

---

#### 3.1.14 `com.macro.mall.controller.PmsSkuStockController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<List<PmsSkuStock>> getList(Long pid, String keyword)` | /sku/{pid} | GET | `pid`, `keyword` | SKU库存列表 | SKU库存模糊搜索 |
| `CommonResult update(Long pid, List<PmsSkuStock>)` | /sku/update/{pid} | POST | `pid`, SKU列表 | 操作结果 | 批量更新SKU库存 |

---

#### 3.1.15 `com.macro.mall.controller.OmsCompanyAddressController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<List<OmsCompanyAddress>> list()` | /companyAddress/list | GET | 无 | `[OmsCompanyAddress]` | 获取所有收货地址 |

---

#### 3.1.16 `com.macro.mall.controller.SmsCouponController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult add(SmsCouponParam)` | /coupon/create | POST | 优惠券参数 | 操作结果 | 添加优惠券 |
| `CommonResult delete(Long id)` | /coupon/delete/{id} | POST | `id` | 操作结果 | 删除优惠券 |
| `CommonResult update(Long id, SmsCouponParam)` | /coupon/update/{id} | POST | `id`,参数 | 操作结果 | 修改优惠券 |
| `CommonResult<CommonPage<SmsCoupon>> list(String name, Integer type, Integer pageSize, Integer pageNum)` | /coupon/list | GET | 筛选+分页 | 分页优惠券 | 分页获取优惠券 |
| `CommonResult<SmsCouponParam> getItem(Long id)` | /coupon/{id} | GET | `id` | 优惠券详情 | 获取单个优惠券详情 |

---

#### 3.1.17 `com.macro.mall.controller.SmsCouponHistoryController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult<CommonPage<SmsCouponHistory>> list(Long couponId, Integer useStatus, String orderSn, Integer pageSize, Integer pageNum)` | /couponHistory/list | GET | 多条件，分页 | 分页领取记录 | 查询优惠券领取记录 |

---

#### 3.1.18 `com.macro.mall.controller.SmsFlashPromotionController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(SmsFlashPromotion)` | /flash/create | POST | 活动参数 | 操作结果 | 添加活动 |
| `CommonResult update(Long id, SmsFlashPromotion)` | /flash/update/{id} | POST | `id`,参数 | 操作结果 | 编辑活动 |
| `CommonResult delete(Long id)` | /flash/delete/{id} | POST | `id` | 操作结果 | 删除活动 |
| `CommonResult update(Long id, Integer status)` | /flash/update/status/{id} | POST | `id`,`status` | 操作结果 | 修改上下线状态 |
| `CommonResult<SmsFlashPromotion> getItem(Long id)` | /flash/{id} | GET | `id` | 活动详情 | 获取活动详情 |
| `CommonResult<CommonPage<SmsFlashPromotion>> getItem(String keyword, Integer pageSize, Integer pageNum)` | /flash/list | GET | 筛选+分页 | 分页活动 | 分页查询活动 |

---

#### 3.1.19 `com.macro.mall.controller.SmsFlashPromotionProductRelationController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(List<SmsFlashPromotionProductRelation>)` | /flashProductRelation/create | POST | 关联列表 | 操作结果 | 批量添加关联商品 |
| `CommonResult update(Long id, SmsFlashPromotionProductRelation)` | /flashProductRelation/update/{id} | POST | `id`,参数 | 操作结果 | 修改关联信息 |
| `CommonResult delete(Long id)` | /flashProductRelation/delete/{id} | POST | `id` | 操作结果 | 删除关联 |
| `CommonResult<SmsFlashPromotionProductRelation> getItem(Long id)` | /flashProductRelation/{id} | GET | `id` | 关联详情 | 获取关联商品促销信息 |
| `CommonResult<CommonPage<SmsFlashPromotionProduct>> list(Long flashPromotionId, Long flashPromotionSessionId, Integer pageSize, Integer pageNum)` | /flashProductRelation/list | GET | 活动ID、场次ID、分页 | 分页商品 | 分页查询关联商品 |

---

#### 3.1.20 `com.macro.mall.controller.SmsFlashPromotionSessionController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(SmsFlashPromotionSession)` | /flashSession/create | POST | 场次参数 | 操作结果 | 添加场次 |
| `CommonResult update(Long id, SmsFlashPromotionSession)` | /flashSession/update/{id} | POST | `id`,参数 | 操作结果 | 修改场次 |
| `CommonResult updateStatus(Long id, Integer status)` | /flashSession/update/status/{id} | POST | `id`,`status` | 操作结果 | 修改启用状态 |
| `CommonResult delete(Long id)` | /flashSession/delete/{id} | POST | `id` | 操作结果 | 删除场次 |
| `CommonResult<SmsFlashPromotionSession> getItem(Long id)` | /flashSession/{id} | GET | `id` | 场次详情 | 获取场次详情 |
| `CommonResult<List<SmsFlashPromotionSession>> list()` | /flashSession/list | GET | 无 | `[SmsFlashPromotionSession]` | 获取全部场次 |
| `CommonResult<List<SmsFlashPromotionSessionDetail>> selectList(Long flashPromotionId)` | /flashSession/selectList | GET | `flashPromotionId` | 场次列表 | 获取全部可选场次及数量 |

---

#### 3.1.21 `com.macro.mall.controller.SmsHomeAdvertiseController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(SmsHomeAdvertise)` | /home/advertise/create | POST | 广告参数 | 操作结果 | 添加广告 |
| `CommonResult delete(List<Long> ids)` | /home/advertise/delete | POST | `ids` | 操作结果 | 删除广告 |
| `CommonResult updateStatus(Long id, Integer status)` | /home/advertise/update/status/{id} | POST | `id`,`status` | 操作结果 | 修改上下线状态 |
| `CommonResult<SmsHomeAdvertise> getItem(Long id)` | /home/advertise/{id} | GET | `id` | 广告详情 | 获取广告详情 |
| `CommonResult update(Long id, SmsHomeAdvertise)` | /home/advertise/update/{id} | POST | `id`,参数 | 操作结果 | 修改广告 |
| `CommonResult<CommonPage<SmsHomeAdvertise>> list(String name, Integer type, String endTime, Integer pageSize, Integer pageNum)` | /home/advertise/list | GET | 筛选+分页 | 分页广告 | 分页查询广告 |

---

#### 3.1.22 `com.macro.mall.controller.SmsHomeBrandController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(List<SmsHomeBrand>)` | /home/brand/create | POST | 推荐品牌列表 | 操作结果 | 添加首页推荐品牌 |
| `CommonResult updateSort(Long id, Integer sort)` | /home/brand/update/sort/{id} | POST | `id`,`sort` | 操作结果 | 修改品牌排序 |
| `CommonResult delete(List<Long> ids)` | /home/brand/delete | POST | `ids` | 操作结果 | 批量删除推荐品牌 |
| `CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | /home/brand/update/recommendStatus | POST | `ids`,`recommendStatus` | 操作结果 | 批量修改推荐状态 |
| `CommonResult<CommonPage<SmsHomeBrand>> list(String brandName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | /home/brand/list | GET | 筛选+分页 | 分页品牌 | 分页查询推荐品牌 |

---

#### 3.1.23 `com.macro.mall.controller.SmsHomeNewProductController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(List<SmsHomeNewProduct>)` | /home/newProduct/create | POST | 新品列表 | 操作结果 | 添加首页新品 |
| `CommonResult updateSort(Long id, Integer sort)` | /home/newProduct/update/sort/{id} | POST | `id`,`sort` | 操作结果 | 修改新品排序 |
| `CommonResult delete(List<Long> ids)` | /home/newProduct/delete | POST | `ids` | 操作结果 | 批量删除新品 |
| `CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | /home/newProduct/update/recommendStatus | POST | `ids`,`recommendStatus` | 操作结果 | 批量修改新品推荐状态 |
| `CommonResult<CommonPage<SmsHomeNewProduct>> list(String productName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | /home/newProduct/list | GET | 筛选+分页 | 分页新品 | 分页查询新品 |

---

#### 3.1.24 `com.macro.mall.controller.SmsHomeRecommendProductController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(List<SmsHomeRecommendProduct>)` | /home/recommendProduct/create | POST | 推荐商品列表 | 操作结果 | 添加首页推荐 |
| `CommonResult updateSort(Long id, Integer sort)` | /home/recommendProduct/update/sort/{id} | POST | `id`,`sort` | 操作结果 | 修改推荐排序 |
| `CommonResult delete(List<Long> ids)` | /home/recommendProduct/delete | POST | `ids` | 操作结果 | 批量删除推荐 |
| `CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | /home/recommendProduct/update/recommendStatus | POST | `ids`,`recommendStatus` | 操作结果 | 批量修改推荐状态 |
| `CommonResult<CommonPage<SmsHomeRecommendProduct>> list(String productName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | /home/recommendProduct/list | GET | 筛选+分页 | 分页推荐 | 分页查询推荐 |

---

#### 3.1.25 `com.macro.mall.controller.SmsHomeRecommendSubjectController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-------------|-----|----------|----------|----------|------|
| `CommonResult create(List<SmsHomeRecommendSubject>)` | /home/recommendSubject/create | POST | 专题推荐列表 | 操作结果 | 添加专题推荐 |
| `CommonResult updateSort(Long id, Integer sort)` | /home/recommendSubject/update/sort/{id} | POST | `id`,`sort` | 操作结果 | 修改专题推荐排序 |
| `CommonResult delete(List<Long> ids)` | /home/recommendSubject/delete | POST | `ids` | 操作结果 | 批量删除专题推荐 |
| `CommonResult updateRecommendStatus(List<Long> ids, Integer recommendStatus)` | /home/recommendSubject/update/recommendStatus | POST | `ids`,`recommendStatus` | 操作结果 | 批量修改专题推荐状态 |
| `CommonResult<CommonPage<SmsHomeRecommendSubject>> list(String subjectName, Integer recommendStatus, Integer pageSize, Integer pageNum)` | /home/recommendSubject/list | GET | 筛选+分页 | 分页专题推荐 | 分页查询专题推荐 |

---

#### 3.1.26 `com.macro.mall.controller.UmsAdminController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult<UmsAdmin> register(UmsAdminParam)` | /admin/register | POST | 注册参数 | 管理员对象 | 用户注册 |
| `CommonResult login(UmsAdminLoginParam)` | /admin/login | POST | 登录参数 | Token信息 | 登录返回token |
| `CommonResult refreshToken(HttpServletRequest)` | /admin/refreshToken | GET | Header中token | Token信息 | 刷新token |
| `CommonResult getAdminInfo(Principal)` | /admin/info | GET | 当前登录上下文 | 管理员信息 | 获取当前登录用户 |
| `CommonResult logout(Principal)` | /admin/logout | POST | 当前登录上下文 | 操作结果 | 登出功能 |
| `CommonResult<CommonPage<UmsAdmin>> list(String keyword, Integer pageSize, Integer pageNum)` | /admin/list | GET | 筛选+分页 | 分页用户 | 用户列表 |
| `CommonResult<UmsAdmin> getItem(Long id)` | /admin/{id} | GET | `id` | 管理员详情 | 获取指定用户 |
| `CommonResult update(Long id, UmsAdmin)` | /admin/update/{id} | POST | `id`,参数 | 操作结果 | 修改指定用户 |
| `CommonResult updatePassword(UpdateAdminPasswordParam)` | /admin/updatePassword | POST | 密码参数 | 操作结果 | 修改密码 |
| `CommonResult delete(Long id)` | /admin/delete/{id} | POST | `id` | 操作结果 | 删除用户 |
| `CommonResult updateStatus(Long id, Integer status)` | /admin/updateStatus/{id} | POST | `id`,`status` | 操作结果 | 修改账号状态 |
| `CommonResult updateRole(Long adminId, List<Long> roleIds)` | /admin/role/update | POST | `adminId`,`roleIds` | 操作结果 | 分配角色 |
| `CommonResult<List<UmsRole>> getRoleList(Long adminId)` | /admin/role/{adminId} | GET | `adminId` | 角色列表 | 获取用户角色 |

---

#### 3.1.27 `com.macro.mall.controller.UmsRoleController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult create(UmsRole)` | /role/create | POST | 角色参数 | 操作结果 | 添加角色 |
| `CommonResult update(Long id, UmsRole)` | /role/update/{id} | POST | `id`,参数 | 操作结果 | 修改角色 |
| `CommonResult delete(List<Long> ids)` | /role/delete | POST | `ids` | 操作结果 | 批量删除 |
| `CommonResult<List<UmsRole>> listAll()` | /role/listAll | GET | 无 | `[UmsRole]` | 获取所有角色 |
| `CommonResult<CommonPage<UmsRole>> list(String keyword, Integer pageSize, Integer pageNum)` | /role/list | GET | 筛选+分页 | 分页角色 | 分页获取角色 |
| `CommonResult updateStatus(Long id, Integer status)` | /role/updateStatus/{id} | POST | `id`,`status` | 操作结果 | 修改角色状态 |
| `CommonResult<List<UmsMenu>> listMenu(Long roleId)` | /role/listMenu/{roleId} | GET | `roleId` | 菜单列表 | 获取角色菜单 |
| `CommonResult<List<UmsResource>> listResource(Long roleId)` | /role/listResource/{roleId} | GET | `roleId` | 资源列表 | 获取角色资源 |
| `CommonResult allocMenu(Long roleId, List<Long> menuIds)` | /role/allocMenu | POST | `roleId`,`menuIds` | 操作结果 | 分配菜单 |
| `CommonResult allocResource(Long roleId, List<Long> resourceIds)` | /role/allocResource | POST | `roleId`,`resourceIds` | 操作结果 | 分配资源 |

---

#### 3.1.28 `com.macro.mall.controller.UmsMenuController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult create(UmsMenu)` | /menu/create | POST | 菜单参数 | 操作结果 | 添加菜单 |
| `CommonResult update(Long id, UmsMenu)` | /menu/update/{id} | POST | `id`,参数 | 操作结果 | 修改菜单 |
| `CommonResult<UmsMenu> getItem(Long id)` | /menu/{id} | GET | `id` | 菜单详情 | 获取菜单 |
| `CommonResult delete(Long id)` | /menu/delete/{id} | POST | `id` | 操作结果 | 删除菜单 |
| `CommonResult<CommonPage<UmsMenu>> list(Long parentId, Integer pageSize, Integer pageNum)` | /menu/list/{parentId} | GET | `parentId`,分页 | 分页菜单 | 分页查询菜单 |
| `CommonResult<List<UmsMenuNode>> treeList()` | /menu/treeList | GET | 无 | 菜单树 | 树形所有菜单 |
| `CommonResult updateHidden(Long id, Integer hidden)` | /menu/updateHidden/{id} | POST | `id`,`hidden` | 操作结果 | 修改显示状态 |

---

#### 3.1.29 `com.macro.mall.controller.UmsResourceController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult create(UmsResource)` | /resource/create | POST | 资源参数 | 操作结果 | 添加资源 |
| `CommonResult update(Long id, UmsResource)` | /resource/update/{id} | POST | `id`,参数 | 操作结果 | 修改资源 |
| `CommonResult<UmsResource> getItem(Long id)` | /resource/{id} | GET | `id` | 资源详情 | 获取资源 |
| `CommonResult delete(Long id)` | /resource/delete/{id} | POST | `id` | 操作结果 | 删除资源 |
| `CommonResult<CommonPage<UmsResource>> list(Long categoryId, String nameKeyword, String urlKeyword, Integer pageSize, Integer pageNum)` | /resource/list | GET | 多条件，分页 | 分页资源 | 模糊查询资源 |
| `CommonResult<List<UmsResource>> listAll()` | /resource/listAll | GET | 无 | `[UmsResource]` | 查询所有资源 |

---

#### 3.1.30 `com.macro.mall.controller.UmsResourceCategoryController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult<List<UmsResourceCategory>> listAll()` | /resourceCategory/listAll | GET | 无 | `[UmsResourceCategory]` | 查询所有资源分类 |
| `CommonResult create(UmsResourceCategory)` | /resourceCategory/create | POST | 分类参数 | 操作结果 | 添加分类 |
| `CommonResult update(Long id, UmsResourceCategory)` | /resourceCategory/update/{id} | POST | `id`,参数 | 操作结果 | 修改分类 |
| `CommonResult delete(Long id)` | /resourceCategory/delete/{id} | POST | `id` | 操作结果 | 删除分类 |

---

#### 3.1.31 `com.macro.mall.controller.UmsMemberLevelController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult<List<UmsMemberLevel>> list(Integer defaultStatus)` | /memberLevel/list | GET | `defaultStatus` | `[UmsMemberLevel]` | 查询所有会员等级 |

---

### 3.2 前台商城端接口类

#### 3.2.1 `com.macro.mall.portal.controller.HomeController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult<HomeContentResult> content()` | /home/content | GET | 无 | 首页内容 | 首页内容展示 |
| `CommonResult<List<PmsProduct>> recommendProductList(Integer pageSize, Integer pageNum)` | /home/recommendProductList | GET | 分页 | 推荐商品 | 获取推荐商品 |
| `CommonResult<List<PmsProductCategory>> getProductCateList(Long parentId)` | /home/productCateList/{parentId} | GET | `parentId` | 分类列表 | 获取商品分类 |
| `CommonResult<List<CmsSubject>> getSubjectList(Long cateId, Integer pageSize, Integer pageNum)` | /home/subjectList | GET | 筛选、分页 | 专题列表 | 获取专题 |
| `CommonResult<List<PmsProduct>> hotProductList(Integer pageNum, Integer pageSize)` | /home/hotProductList | GET | 分页 | 人气商品 | 获取人气推荐商品 |
| `CommonResult<List<PmsProduct>> newProductList(Integer pageNum, Integer pageSize)` | /home/newProductList | GET | 分页 | 新品 | 获取新品推荐商品 |

---

#### 3.2.2 `com.macro.mall.portal.controller.UmsMemberController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult register(String username, String password, String telephone, String authCode)` | /sso/register | POST | 用户信息 | 操作结果 | 会员注册 |
| `CommonResult login(String username, String password)` | /sso/login | POST | 用户名、密码 | Token信息 | 会员登录 |
| `CommonResult info(Principal)` | /sso/info | GET | 当前上下文 | 会员信息 | 获取会员信息 |
| `CommonResult getAuthCode(String telephone)` | /sso/getAuthCode | GET | `telephone` | 验证码 | 获取验证码 |
| `CommonResult updatePassword(String telephone, String password, String authCode)` | /sso/updatePassword | POST | 修改参数 | 操作结果 | 修改密码 |
| `CommonResult refreshToken(HttpServletRequest)` | /sso/refreshToken | GET | Header中token | Token信息 | 刷新token |

---

#### 3.2.3 `com.macro.mall.portal.controller.UmsMemberCouponController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult add(Long couponId)` | /member/coupon/add/{couponId} | POST | `couponId` | 操作结果 | 领取优惠券 |
| `CommonResult<List<SmsCouponHistory>> listHistory(Integer useStatus)` | /member/coupon/listHistory | GET | `useStatus` | 历史列表 | 获取会员优惠券历史 |
| `CommonResult<List<SmsCoupon>> list(Integer useStatus)` | /member/coupon/list | GET | `useStatus` | 优惠券列表 | 获取会员优惠券 |
| `CommonResult<List<SmsCouponHistoryDetail>> listCart(Integer type)` | /member/coupon/list/cart/{type} | GET | `type` | 优惠券详情 | 获取购物车相关优惠券 |
| `CommonResult<List<SmsCoupon>> listByProduct(Long productId)` | /member/coupon/listByProduct/{productId} | GET | `productId` | 优惠券列表 | 获取商品相关优惠券 |

---

#### 3.2.4 `com.macro.mall.portal.controller.UmsMemberReceiveAddressController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult add(UmsMemberReceiveAddress)` | /member/address/add | POST | 地址参数 | 操作结果 | 添加收货地址 |
| `CommonResult delete(Long id)` | /member/address/delete/{id} | POST | `id` | 操作结果 | 删除收货地址 |
| `CommonResult update(Long id, UmsMemberReceiveAddress)` | /member/address/update/{id} | POST | `id`,参数 | 操作结果 | 修改收货地址 |
| `CommonResult<List<UmsMemberReceiveAddress>> list()` | /member/address/list | GET | 无 | 地址列表 | 获取所有收货地址 |
| `CommonResult<UmsMemberReceiveAddress> getItem(Long id)` | /member/address/{id} | GET | `id` | 地址详情 | 获取收货地址详情 |

---

#### 3.2.5 `com.macro.mall.portal.controller.MemberAttentionController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult add(MemberBrandAttention)` | /member/attention/add | POST | 关注参数 | 操作结果 | 添加品牌关注 |
| `CommonResult delete(Long brandId)` | /member/attention/delete | POST | `brandId` | 操作结果 | 取消关注 |
| `CommonResult<CommonPage<MemberBrandAttention>> list(Integer pageNum, Integer pageSize)` | /member/attention/list | GET | 分页 | 关注列表 | 查询关注列表 |
| `CommonResult<MemberBrandAttention> detail(Long brandId)` | /member/attention/detail | GET | `brandId` | 关注详情 | 关注详情 |
| `CommonResult clear()` | /member/attention/clear | POST | 无 | 操作结果 | 清空关注列表 |

---

#### 3.2.6 `com.macro.mall.portal.controller.MemberProductCollectionController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult add(MemberProductCollection)` | /member/productCollection/add | POST | 收藏参数 | 操作结果 | 添加收藏 |
| `CommonResult delete(Long productId)` | /member/productCollection/delete | POST | `productId` | 操作结果 | 删除收藏 |
| `CommonResult<CommonPage<MemberProductCollection>> list(Integer pageNum, Integer pageSize)` | /member/productCollection/list | GET | 分页 | 收藏列表 | 查询收藏列表 |
| `CommonResult<MemberProductCollection> detail(Long productId)` | /member/productCollection/detail | GET | `productId` | 收藏详情 | 收藏详情 |
| `CommonResult clear()` | /member/productCollection/clear | POST | 无 | 操作结果 | 清空收藏列表 |

---

#### 3.2.7 `com.macro.mall.portal.controller.MemberReadHistoryController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult create(MemberReadHistory)` | /member/readHistory/create | POST | 浏览记录参数 | 操作结果 | 创建浏览记录 |
| `CommonResult delete(List<String> ids)` | /member/readHistory/delete | POST | `ids` | 操作结果 | 删除浏览记录 |
| `CommonResult clear()` | /member/readHistory/clear | POST | 无 | 操作结果 | 清空浏览记录 |
| `CommonResult<CommonPage<MemberReadHistory>> list(Integer pageNum, Integer pageSize)` | /member/readHistory/list | GET | 分页 | 分页浏览记录 | 获取浏览记录 |

---

#### 3.2.8 `com.macro.mall.portal.controller.OmsCartItemController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|----------------|---------------------|----------|----------|----------|------|
| `CommonResult add(OmsCartItem)` | /cart/add | POST | 商品参数 | 操作结果 | 添加到购物车 |
| `CommonResult<List<OmsCartItem>> list()` | /cart/list | GET | 无 | 购物车列表 | 获取购物车列表 |
| `CommonResult<List<CartPromotionItem>> listPromotion(List<Long> cartIds)` | /cart/list/promotion | GET | `cartIds`(可选) | 促销信息 | 获取购物车促销信息 |
| `CommonResult updateQuantity(Long id, Integer quantity)` | /cart/update/quantity | GET | `id`,`quantity` | 操作结果 | 修改数量 |
| `CommonResult<CartProduct> getCartProduct(Long productId)` | /cart/getProduct/{productId} | GET | `productId` | 商品规格 | 获取购物车规格 |
| `CommonResult updateAttr(OmsCartItem)` | /cart/update/attr | POST | 购物车参数 | 操作结果 | 修改购物车规格 |
| `CommonResult delete(List<Long> ids)` | /cart/delete | POST | `ids` | 操作结果 | 删除购物车项 |
| `CommonResult clear()` | /cart/clear | POST | 无 | 操作结果 | 清空购物车 |

---

#### 3.2.9 `com.macro.mall.portal.controller.OmsPortalOrderController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `CommonResult<ConfirmOrderResult> generateConfirmOrder(List<Long> cartIds)` | /order/generateConfirmOrder | POST | `cartIds` | 确认单 | 生成确认单 |
| `CommonResult generateOrder(OrderParam)` | /order/generateOrder | POST | 下单参数 | 订单结果 | 生成订单 |
| `CommonResult paySuccess(Long orderId, Integer payType)` | /order/paySuccess | POST | `orderId`,`payType` | 操作结果 | 支付成功回调 |
| `CommonResult cancelTimeOutOrder()` | /order/cancelTimeOutOrder | POST | 无 | 操作结果 | 自动取消超时订单 |
| `CommonResult cancelOrder(Long orderId)` | /order/cancelOrder | POST | `orderId` | 操作结果 | 取消单个超时订单 |
| `CommonResult<CommonPage<OmsOrderDetail>> list(Integer status, Integer pageNum, Integer pageSize)` | /order/list | GET | `status`,分页 | 分页订单 | 获取订单列表 |
| `CommonResult<OmsOrderDetail> detail(Long orderId)` | /order/detail/{orderId} | GET | `orderId` | 订单详情 | 获取订单详情 |
| `CommonResult cancelUserOrder(Long orderId)` | /order/cancelUserOrder | POST | `orderId` | 操作结果 | 用户取消订单 |
| `CommonResult confirmReceiveOrder(Long orderId)` | /order/confirmReceiveOrder | POST | `orderId` | 操作结果 | 用户确认收货 |
| `CommonResult deleteOrder(Long orderId)` | /order/deleteOrder | POST | `orderId` | 操作结果 | 用户删除订单 |

---

#### 3.2.10 `com.macro.mall.portal.controller.OmsPortalOrderReturnApplyController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `CommonResult create(OmsOrderReturnApplyParam)` | /returnApply/create | POST | 退货申请参数 | 操作结果 | 申请退货 |

---

#### 3.2.11 `com.macro.mall.portal.controller.AlipayController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `void pay(AliPayParam, HttpServletResponse)` | /alipay/pay | GET | 支付参数 | HTML | 电脑网站支付 |
| `void webPay(AliPayParam, HttpServletResponse)` | /alipay/webPay | GET | 支付参数 | HTML | 手机网站支付 |
| `String notify(HttpServletRequest)` | /alipay/notify | POST | 回调参数 | 文本 | 支付宝异步回调 |
| `CommonResult<String> query(String outTradeNo, String tradeNo)` | /alipay/query | GET | 订单号 | 交易状态 | 交易查询 |

---

#### 3.2.12 `com.macro.mall.portal.controller.PmsPortalBrandController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `CommonResult<List<PmsBrand>> recommendList(Integer pageSize, Integer pageNum)` | /brand/recommendList | GET | 分页 | 品牌列表 | 推荐品牌 |
| `CommonResult<PmsBrand> detail(Long brandId)` | /brand/detail/{brandId} | GET | `brandId` | 品牌详情 | 品牌详情 |
| `CommonResult<CommonPage<PmsProduct>> productList(Long brandId, Integer pageNum, Integer pageSize)` | /brand/productList | GET | `brandId`,分页 | 分页商品 | 品牌相关商品 |

---

#### 3.2.13 `com.macro.mall.portal.controller.PmsPortalProductController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `CommonResult<CommonPage<PmsProduct>> search(String keyword, Long brandId, Long productCategoryId, Integer pageNum, Integer pageSize, Integer sort)` | /product/search | GET | 多条件 | 分页商品 | 综合搜索 |
| `CommonResult<List<PmsProductCategoryNode>> categoryTreeList()` | /product/categoryTreeList | GET | 无 | 分类树 | 分类树结构 |
| `CommonResult<PmsPortalProductDetail> detail(Long id)` | /product/detail/{id} | GET | `id` | 商品详情 | 获取商品详情 |

---

### 3.3 搜索服务接口类

#### 3.3.1 `com.github.dockerjava.core.command.EsProductController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `CommonResult<Integer> importAllList()` | /esProduct/importAll | POST | 无 | 导入数量 | 导入全部商品到ES |
| `CommonResult<Object> delete(Long id)` | /esProduct/delete/{id} | GET | `id` | 操作结果 | 删除ES商品 |
| `CommonResult<Object> delete(List<Long> ids)` | /esProduct/delete/batch | POST | `ids` | 操作结果 | 批量删除ES商品 |
| `CommonResult<EsProduct> create(Long id)` | /esProduct/create/{id} | POST | `id` | 商品 | 根据ID创建ES商品 |
| `CommonResult<CommonPage<EsProduct>> search(String keyword, Integer pageNum, Integer pageSize)` | /esProduct/search/simple | GET | 关键词、分页 | 分页商品 | 简单搜索 |
| `CommonResult<CommonPage<EsProduct>> search(String keyword, Long brandId, Long productCategoryId, Integer pageNum, Integer pageSize, Integer sort)` | /esProduct/search | GET | 多条件 | 分页商品 | 综合搜索 |
| `CommonResult<CommonPage<EsProduct>> recommend(Long id, Integer pageNum, Integer pageSize)` | /esProduct/recommend/{id} | GET | `id`,分页 | 分页商品 | 推荐商品 |
| `CommonResult<EsProductRelatedInfo> searchRelatedInfo(String keyword)` | /esProduct/search/relate | GET | `keyword` | 相关信息 | 获取品牌/分类/属性 |

---

### 3.4 示例/演示接口类

#### 3.4.1 `com.github.dockerjava.api.command.DemoController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------|-------------------------------|----------|----------|----------|------|
| `CommonResult<List<PmsBrand>> getBrandList()` | /brand/listAll | GET | 无 | 品牌列表 | 获取全部品牌 |
| `CommonResult createBrand(PmsBrandDto)` | /brand/create | POST | 品牌参数 | 操作结果 | 添加品牌 |
| `CommonResult updateBrand(Long id, PmsBrandDto)` | /brand/update/{id} | POST | `id`,参数 | 操作结果 | 更新品牌 |
| `CommonResult deleteBrand(Long id)` | /brand/delete/{id} | GET | `id` | 操作结果 | 删除品牌 |
| `CommonResult<CommonPage<PmsBrand>> listBrand(Integer pageNum, Integer pageSize)` | /brand/list | GET | 分页 | 分页品牌 | 分页获取品牌 |
| `CommonResult<PmsBrand> brand(Long id)` | /brand/{id} | GET | `id` | 品牌详情 | 根据编号查询品牌 |

---

#### 3.4.2 `com.github.dockerjava.api.command.RestTemplateDemoController`
| 方法名/签名 | URL | 请求方式 | 请求参数 | 响应数据 | 说明 |
|-----------------------------------|--------------------------|----------|----------|----------|------|
| `Object getForEntity(Long id)` | /template/get/{id} | GET | `id` | 品牌结果 | RestTemplate GET演示 |
| `Object getForEntity2(Long id)` | /template/get2/{id} | GET | `id` | 品牌结果 | RestTemplate GET+params演示 |
| `Object getForEntity3(Long id)` | /template/get3/{id} | GET | `id` | 品牌结果 | RestTemplate GET+URI演示 |
| `Object getForObject(Long id)` | /template/get4/{id} | GET | `id` | 品牌结果 | RestTemplate GET forObject |
| `Object postForEntity(PmsBrand)` | /template/post | POST | 品牌参数 | 品牌结果 | RestTemplate POST演示 |
| `Object postForObject(PmsBrand)` | /template/post2 | POST | 品牌参数 | 品牌结果 | RestTemplate POST forObject |
| `Object postForEntity3(String name)` | /template/post3 | POST | `name` | 操作结果 | RestTemplate POST form演示 |

---

**说明：**
- 各Controller返回类型基本为`CommonResult<T>`，分页采用`CommonPage<T>`。
- 参数分别通过@PathVariable、@RequestParam、@RequestBody等传递，具体以接口注解和表格为准。
- 详细的数据对象结构（如PmsProduct、OmsOrder等）请参见各自的数据模型定义源码。