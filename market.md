# 2. 对外提供接口说明文档

## 1. 功能分析

### 1.1 电商后台管理服务

#### 1.1.1 商品管理与维护
- **商品品牌管理**：增删改查品牌，批量操作品牌显示/厂家状态等。
- **商品分类管理**：增删改查商品分类，分页、树形结构查询等。
- **商品属性及属性分类管理**：商品属性分类及属性的增删改查、关联查询。
- **商品管理**：商品的创建、查询、编辑、批量状态变更等。
- **SKU库存管理**：SKU库存查询、批量更新。

#### 1.1.2 订单及售后管理
- **订单管理**：订单的查询、详情、发货、关闭、删除、备注、费用、收货人信息修改等。
- **收货地址管理**：公司收货地址列表查询。
- **订单退货申请管理**：退货申请的分页查询、详情、批量删除、状态修改。
- **退货原因管理**：退货原因的增删改查、状态变更。
- **订单设置管理**：订单设置的查询和修改。

#### 1.1.3 内容及营销管理
- **商品优选专区管理**：获取所有商品优选专区信息。
- **商品专题管理**：获取所有专题、按名称分页查询专题。
- **优惠券管理**：优惠券增删改查、分页查询。
- **优惠券领取记录管理**：多条件分页查询领取记录。
- **限时购活动及相关管理**：限时购活动、场次、商品关联的增删改查、状态变更、分页查询。
- **首页内容管理**：首页轮播广告、推荐品牌、新品、人气推荐、专题推荐的增删改查、分页与批量操作。

#### 1.1.4 存储与文件管理
- **MinIO对象存储**：文件上传、删除。
- **阿里云OSS对象存储**：上传签名生成、上传回调。

#### 1.1.5 权限与用户管理
- **后台用户管理**：注册、登录、token、信息获取、列表、增删改查、密码/状态/角色分配等。
- **后台菜单/资源/资源分类/角色管理**：后台菜单、资源、分类、角色的增删改查、分配权限、查询树形结构、相关资源/菜单的查询。
- **会员等级管理**：会员等级查询。

### 1.2 电商前台服务

#### 1.2.1 会员与认证
- **会员注册/登录/信息管理**：注册、登录、token、获取会员信息、验证码、密码修改。

#### 1.2.2 商城功能
- **首页内容展示**：首页内容、推荐商品、商品分类、专题等。
- **品牌管理**：推荐品牌、品牌详情、品牌商品列表。
- **商品管理**：综合搜索、分类树、商品详情。
- **购物车管理**：添加、删除、修改、查询、清空购物车及促销信息。
- **订单管理**：生成确认单、下单、支付回调、取消/删除/确认收货、订单列表与详情。
- **退货申请管理**：用户提交退货申请。
- **收货地址管理**：会员收货地址的增删改查。
- **优惠券管理**：领取、历史、可用/商品相关优惠券查询。
- **会员品牌关注/商品收藏/浏览记录**：关注品牌、收藏商品、浏览记录的增删查清空。

#### 1.2.3 支付服务
- **支付宝支付**：电脑/手机网站支付、异步回调、订单查询。

### 1.3 搜索服务

#### 1.3.1 商品搜索与推荐
- **ES商品搜索管理**：商品导入、删除、创建、简单/复杂搜索、推荐、搜索相关品牌/分类/属性查询。

---

## 2. 调用类说明

### 2.1 后台管理相关Controller

#### 2.1.1 商品类
- **PmsBrandController**
  - 功能：商品品牌管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\PmsBrandController.java
  - 包：com.macro.mall.controller
- **PmsProductCategoryController**
  - 功能：商品分类管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\PmsProductCategoryController.java
  - 包：com.macro.mall.controller
- **PmsProductAttributeCategoryController**
  - 功能：商品属性分类管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\PmsProductAttributeCategoryController.java
  - 包：com.macro.mall.controller
- **PmsProductAttributeController**
  - 功能：商品属性管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\PmsProductAttributeController.java
  - 包：com.macro.mall.controller
- **PmsProductController**
  - 功能：商品管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\PmsProductController.java
  - 包：com.macro.mall.controller
- **PmsSkuStockController**
  - 功能：sku商品库存管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\PmsSkuStockController.java
  - 包：com.macro.mall.controller

#### 2.1.2 订单与售后
- **OmsOrderController**
  - 功能：订单管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\OmsOrderController.java
  - 包：com.macro.mall.controller
- **OmsCompanyAddressController**
  - 功能：收货地址管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\OmsCompanyAddressController.java
  - 包：com.macro.mall.controller
- **OmsOrderReturnApplyController**
  - 功能：订单退货申请管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\OmsOrderReturnApplyController.java
  - 包：com.macro.mall.controller
- **OmsOrderReturnReasonController**
  - 功能：退货原因管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\OmsOrderReturnReasonController.java
  - 包：com.macro.mall.controller
- **OmsOrderSettingController**
  - 功能：订单设置管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\OmsOrderSettingController.java
  - 包：com.macro.mall.controller

#### 2.1.3 内容与营销
- **CmsPrefrenceAreaController**
  - 功能：商品优选管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\CmsPrefrenceAreaController.java
  - 包：com.macro.mall.controller
- **CmsSubjectController**
  - 功能：商品专题管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\CmsSubjectController.java
  - 包：com.macro.mall.controller
- **SmsCouponController**
  - 功能：优惠券管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsCouponController.java
  - 包：com.macro.mall.controller
- **SmsCouponHistoryController**
  - 功能：优惠券领取记录管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsCouponHistoryController.java
  - 包：com.macro.mall.controller
- **SmsFlashPromotionController**
  - 功能：限时购活动管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsFlashPromotionController.java
  - 包：com.macro.mall.controller
- **SmsFlashPromotionSessionController**
  - 功能：限时购场次管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsFlashPromotionSessionController.java
  - 包：com.macro.mall.controller
- **SmsFlashPromotionProductRelationController**
  - 功能：限时购和商品关系管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsFlashPromotionProductRelationController.java
  - 包：com.macro.mall.controller
- **SmsHomeAdvertiseController**
  - 功能：首页轮播广告管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsHomeAdvertiseController.java
  - 包：com.macro.mall.controller
- **SmsHomeBrandController**
  - 功能：首页品牌管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsHomeBrandController.java
  - 包：com.macro.mall.controller
- **SmsHomeNewProductController**
  - 功能：首页新品管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsHomeNewProductController.java
  - 包：com.macro.mall.controller
- **SmsHomeRecommendProductController**
  - 功能：首页人气推荐管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsHomeRecommendProductController.java
  - 包：com.macro.mall.controller
- **SmsHomeRecommendSubjectController**
  - 功能：首页专题推荐管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\SmsHomeRecommendSubjectController.java
  - 包：com.macro.mall.controller

#### 2.1.4 存储
- **MinioController**
  - 功能：MinIO对象存储管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\MinioController.java
  - 包：com.macro.mall.controller
- **OssController**
  - 功能：Oss对象存储管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\OssController.java
  - 包：com.macro.mall.controller

#### 2.1.5 权限与用户管理
- **UmsAdminController**
  - 功能：后台用户管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\UmsAdminController.java
  - 包：com.macro.mall.controller
- **UmsMenuController**
  - 功能：后台菜单管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\UmsMenuController.java
  - 包：com.github.dockerjava.api.model
- **UmsResourceCategoryController**
  - 功能：后台资源分类管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\UmsResourceCategoryController.java
  - 包：com.macro.mall.controller
- **UmsResourceController**
  - 功能：后台资源管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\UmsResourceController.java
  - 包：com.github.dockerjava.api.model
- **UmsRoleController**
  - 功能：后台用户角色管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\UmsRoleController.java
  - 包：com.github.dockerjava.api.model
- **UmsMemberLevelController**
  - 功能：会员等级管理
  - 文件：mall-admin\src\main\java\com\macro\mall\controller\UmsMemberLevelController.java
  - 包：com.github.dockerjava.api.model

---

### 2.2 前台商城相关Controller

- **UmsMemberController**
  - 功能：会员登录注册管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\UmsMemberController.java
  - 包：com.macro.mall.portal.controller
- **HomeController**
  - 功能：首页内容管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\HomeController.java
  - 包：com.macro.mall.portal.controller
- **PmsPortalBrandController**
  - 功能：前台品牌管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\PmsPortalBrandController.java
  - 包：com.macro.mall.portal.controller
- **PmsPortalProductController**
  - 功能：前台商品管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\PmsPortalProductController.java
  - 包：com.github.dockerjava.api.model
- **OmsCartItemController**
  - 功能：购物车管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\OmsCartItemController.java
  - 包：com.macro.mall.portal.controller
- **OmsPortalOrderController**
  - 功能：订单管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\OmsPortalOrderController.java
  - 包：com.github.dockerjava.api.model
- **OmsPortalOrderReturnApplyController**
  - 功能：退货申请管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\OmsPortalOrderReturnApplyController.java
  - 包：com.github.dockerjava.api.model
- **UmsMemberCouponController**
  - 功能：用户优惠券管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\UmsMemberCouponController.java
  - 包：com.macro.mall.portal.controller
- **UmsMemberReceiveAddressController**
  - 功能：会员收货地址管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\UmsMemberReceiveAddressController.java
  - 包：com.macro.mall.portal.controller
- **MemberAttentionController**
  - 功能：会员关注品牌管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\MemberAttentionController.java
  - 包：com.macro.mall.portal.controller
- **MemberProductCollectionController**
  - 功能：会员收藏管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\MemberProductCollectionController.java
  - 包：com.macro.mall.portal.controller
- **MemberReadHistoryController**
  - 功能：会员商品浏览记录管理
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\MemberReadHistoryController.java
  - 包：com.macro.mall.portal.controller
- **AlipayController**
  - 功能：支付宝支付相关接口
  - 文件：mall-portal\src\main\java\com\macro\mall\portal\controller\AlipayController.java
  - 包：com.macro.mall.portal.controller

---

### 2.3 搜索相关Controller

- **EsProductController**
  - 功能：搜索商品管理（Elasticsearch 商品搜索、导入、推荐、筛选属性等）
  - 文件：mall-search\src\main\java\com\macro\mall\search\controller\EsProductController.java
  - 包：com.github.dockerjava.core.command

---

> **注：**  
> 所有Controller类均采用Spring Boot REST风格，URL路径、方法及参数均严格对应源码定义，字段、类名、包名大小写与源码一致。  
> 后台模块主要以`/admin`、`/product`等业务前缀区分，前台模块以`/sso`、`/home`、`/cart`、`/order`等前缀区分，搜索模块以`/esProduct`为前缀提供商品检索相关接口。  
> 具体接口详情请参考下一章节或源码注释与Swagger/OpenAPI文档。## 3. 数据结构说明

### 3.1 后台管理相关Controller

#### 3.1.1 商品类

##### 3.1.1.1 `com.macro.mall.controller.PmsBrandController`
- **主要方法及签名：**
  - `GET /brand/listAll`  
    返回所有品牌列表  
    响应：`CommonResult<List<PmsBrand>>`
  - `POST /brand/create`  
    新增品牌  
    请求体：`PmsBrandParam`  
    响应：`CommonResult`
  - `POST /brand/update/{id}`  
    更新品牌  
    路径参数：`id`  
    请求体：`PmsBrandParam`  
    响应：`CommonResult`
  - `GET /brand/delete/{id}`  
    删除品牌  
    路径参数：`id`  
    响应：`CommonResult`
  - `GET /brand/list`  
    分页/条件查询品牌列表  
    查询参数：`keyword`、`showStatus`、`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<PmsBrand>>`
  - `GET /brand/{id}`  
    获取品牌详情  
    路径参数：`id`  
    响应：`CommonResult<PmsBrand>`
  - `POST /brand/delete/batch`  
    批量删除品牌  
    查询参数：`ids` (List<Long>)  
    响应：`CommonResult`
  - `POST /brand/update/showStatus`  
    批量更新显示状态  
    查询参数：`ids`、`showStatus`  
    响应：`CommonResult`
  - `POST /brand/update/factoryStatus`  
    批量更新厂家制造商状态  
    查询参数：`ids`、`factoryStatus`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.PmsBrandController;
  // 调用如 brandController.getListAll();
  ```

##### 3.1.1.2 `com.macro.mall.controller.PmsProductCategoryController`
- **主要方法及签名：**
  - `POST /productCategory/create`  
    新增商品分类  
    请求体：`PmsProductCategoryParam`  
    响应：`CommonResult`
  - `POST /productCategory/update/{id}`  
    更新商品分类  
    路径参数：`id`  
    请求体：`PmsProductCategoryParam`  
    响应：`CommonResult`
  - `GET /productCategory/list/{parentId}`  
    分页查询分类（按父ID）  
    路径参数：`parentId`  
    查询参数：`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<PmsProductCategory>>`
  - `GET /productCategory/{id}`  
    获取分类详情  
    路径参数：`id`  
    响应：`CommonResult<PmsProductCategory>`
  - `POST /productCategory/delete/{id}`  
    删除分类  
    路径参数：`id`  
    响应：`CommonResult`
  - `POST /productCategory/update/navStatus`  
    批量更新导航栏显示  
    查询参数：`ids`、`navStatus`  
    响应：`CommonResult`
  - `POST /productCategory/update/showStatus`  
    批量更新显示状态  
    查询参数：`ids`、`showStatus`  
    响应：`CommonResult`
  - `GET /productCategory/list/withChildren`  
    查询所有一级及子分类  
    响应：`CommonResult<List<PmsProductCategoryWithChildrenItem>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.PmsProductCategoryController;
  ```

##### 3.1.1.3 `com.macro.mall.controller.PmsProductAttributeCategoryController`
- **主要方法及签名：**
  - `POST /productAttribute/category/create`  
    新增属性分类  
    查询参数：`name`  
    响应：`CommonResult`
  - `POST /productAttribute/category/update/{id}`  
    更新属性分类  
    路径参数：`id`  
    查询参数：`name`  
    响应：`CommonResult`
  - `GET /productAttribute/category/delete/{id}`  
    删除属性分类  
    路径参数：`id`  
    响应：`CommonResult`
  - `GET /productAttribute/category/{id}`  
    获取属性分类详情  
    路径参数：`id`  
    响应：`CommonResult<PmsProductAttributeCategory>`
  - `GET /productAttribute/category/list`  
    分页获取所有属性分类  
    查询参数：`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<PmsProductAttributeCategory>>`
  - `GET /productAttribute/category/list/withAttr`  
    获取所有属性分类及属性  
    响应：`CommonResult<List<PmsProductAttributeCategoryItem>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.PmsProductAttributeCategoryController;
  ```

##### 3.1.1.4 `com.macro.mall.controller.PmsProductAttributeController`
- **主要方法及签名：**
  - `GET /productAttribute/list/{cid}`  
    查询属性/参数列表  
    路径参数：`cid`  
    查询参数：`type`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<PmsProductAttribute>>`
  - `POST /productAttribute/create`  
    新增属性  
    请求体：`PmsProductAttributeParam`  
    响应：`CommonResult`
  - `POST /productAttribute/update/{id}`  
    更新属性  
    路径参数：`id`  
    请求体：`PmsProductAttributeParam`  
    响应：`CommonResult`
  - `GET /productAttribute/{id}`  
    获取属性详情  
    路径参数：`id`  
    响应：`CommonResult<PmsProductAttribute>`
  - `POST /productAttribute/delete`  
    批量删除属性  
    查询参数：`ids` (List<Long>)  
    响应：`CommonResult`
  - `GET /productAttribute/attrInfo/{productCategoryId}`  
    获取分类下属性及分类信息  
    路径参数：`productCategoryId`  
    响应：`CommonResult<List<ProductAttrInfo>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.PmsProductAttributeController;
  ```

##### 3.1.1.5 `com.macro.mall.controller.PmsProductController`
- **主要方法及签名：**
  - `POST /product/create`  
    新建商品  
    请求体：`PmsProductParam`  
    响应：`CommonResult`
  - `GET /product/updateInfo/{id}`  
    获取商品编辑信息  
    路径参数：`id`  
    响应：`CommonResult<PmsProductResult>`
  - `POST /product/update/{id}`  
    更新商品  
    路径参数：`id`  
    请求体：`PmsProductParam`  
    响应：`CommonResult`
  - `GET /product/list`  
    分页查询商品  
    查询参数：`PmsProductQueryParam`对象、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<PmsProduct>>`
  - `GET /product/simpleList`  
    模糊查询商品  
    查询参数：`keyword`  
    响应：`CommonResult<List<PmsProduct>>`
  - `POST /product/update/verifyStatus`  
    批量审核状态  
    查询参数：`ids`、`verifyStatus`、`detail`  
    响应：`CommonResult`
  - `POST /product/update/publishStatus`  
    批量上下架  
    查询参数：`ids`、`publishStatus`  
    响应：`CommonResult`
  - `POST /product/update/recommendStatus`  
    批量推荐  
    查询参数：`ids`、`recommendStatus`  
    响应：`CommonResult`
  - `POST /product/update/newStatus`  
    批量设新品  
    查询参数：`ids`、`newStatus`  
    响应：`CommonResult`
  - `POST /product/update/deleteStatus`  
    批量修改删除状态  
    查询参数：`ids`、`deleteStatus`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.PmsProductController;
  ```

##### 3.1.1.6 `com.macro.mall.controller.PmsSkuStockController`
- **主要方法及签名：**
  - `GET /sku/{pid}`  
    查询商品SKU库存  
    路径参数：`pid`  
    查询参数：`keyword`  
    响应：`CommonResult<List<PmsSkuStock>>`
  - `POST /sku/update/{pid}`  
    批量更新SKU库存  
    路径参数：`pid`  
    请求体：`List<PmsSkuStock>`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.PmsSkuStockController;
  ```

#### 3.1.2 订单与售后

##### 3.1.2.1 `com.macro.mall.controller.OmsOrderController`
- **主要方法及签名：**
  - `GET /order/list`  
    查询订单  
    查询参数：`OmsOrderQueryParam`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<OmsOrder>>`
  - `POST /order/update/delivery`  
    批量发货  
    请求体：`List<OmsOrderDeliveryParam>`  
    响应：`CommonResult`
  - `POST /order/update/close`  
    批量关闭订单  
    查询参数：`ids`、`note`  
    响应：`CommonResult`
  - `POST /order/delete`  
    批量删除订单  
    查询参数：`ids`  
    响应：`CommonResult`
  - `GET /order/{id}`  
    获取订单详情  
    路径参数：`id`  
    响应：`CommonResult<OmsOrderDetail>`
  - `POST /order/update/receiverInfo`  
    修改收货人信息  
    请求体：`OmsReceiverInfoParam`  
    响应：`CommonResult`
  - `POST /order/update/moneyInfo`  
    修改订单费用信息  
    请求体：`OmsMoneyInfoParam`  
    响应：`CommonResult`
  - `POST /order/update/note`  
    备注订单  
    查询参数：`id`、`note`、`status`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.OmsOrderController;
  ```

##### 3.1.2.2 `com.macro.mall.controller.OmsCompanyAddressController`
- **主要方法及签名：**
  - `GET /companyAddress/list`  
    获取收货地址列表  
    响应：`CommonResult<List<OmsCompanyAddress>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.OmsCompanyAddressController;
  ```

##### 3.1.2.3 `com.macro.mall.controller.OmsOrderReturnApplyController`
- **主要方法及签名：**
  - `GET /returnApply/list`  
    分页查询退货申请  
    查询参数：`OmsReturnApplyQueryParam`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<OmsOrderReturnApply>>`
  - `POST /returnApply/delete`  
    批量删除退货申请  
    查询参数：`ids`  
    响应：`CommonResult`
  - `GET /returnApply/{id}`  
    获取退货申请详情  
    路径参数：`id`  
    响应：`CommonResult`
  - `POST /returnApply/update/status/{id}`  
    修改退货申请状态  
    路径参数：`id`  
    请求体：`OmsUpdateStatusParam`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.OmsOrderReturnApplyController;
  ```

##### 3.1.2.4 `com.macro.mall.controller.OmsOrderReturnReasonController`
- **主要方法及签名：**
  - `POST /returnReason/create`  
    新增退货原因  
    请求体：`OmsOrderReturnReason`  
    响应：`CommonResult`
  - `POST /returnReason/update/{id}`  
    更新退货原因  
    路径参数：`id`  
    请求体：`OmsOrderReturnReason`  
    响应：`CommonResult`
  - `POST /returnReason/delete`  
    批量删除退货原因  
    查询参数：`ids`  
    响应：`CommonResult`
  - `GET /returnReason/list`  
    分页查询退货原因  
    查询参数：`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<OmsOrderReturnReason>>`
  - `GET /returnReason/{id}`  
    获取单个退货原因  
    路径参数：`id`  
    响应：`CommonResult<OmsOrderReturnReason>`
  - `POST /returnReason/update/status`  
    修改启用状态  
    查询参数：`status`、`ids`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.OmsOrderReturnReasonController;
  ```

##### 3.1.2.5 `com.macro.mall.controller.OmsOrderSettingController`
- **主要方法及签名：**
  - `GET /orderSetting/{id}`  
    获取订单设置  
    路径参数：`id`  
    响应：`CommonResult<OmsOrderSetting>`
  - `POST /orderSetting/update/{id}`  
    修改订单设置  
    路径参数：`id`  
    请求体：`OmsOrderSetting`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.OmsOrderSettingController;
  ```

#### 3.1.3 内容与营销

##### 3.1.3.1 `com.macro.mall.controller.CmsPrefrenceAreaController`
- **主要方法及签名：**
  - `GET /prefrenceArea/listAll`  
    获取所有商品优选  
    响应：`CommonResult<List<CmsPrefrenceArea>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.CmsPrefrenceAreaController;
  ```

##### 3.1.3.2 `com.macro.mall.controller.CmsSubjectController`
- **主要方法及签名：**
  - `GET /subject/listAll`  
    获取全部商品专题  
    响应：`CommonResult<List<CmsSubject>>`
  - `GET /subject/list`  
    根据名称分页获取专题  
    查询参数：`keyword`、`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<CmsSubject>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.CmsSubjectController;
  ```

##### 3.1.3.3 `com.macro.mall.controller.SmsCouponController`
- **主要方法及签名：**
  - `POST /coupon/create`  
    新增优惠券  
    请求体：`SmsCouponParam`  
    响应：`CommonResult`
  - `POST /coupon/delete/{id}`  
    删除优惠券  
    路径参数：`id`  
    响应：`CommonResult`
  - `POST /coupon/update/{id}`  
    更新优惠券  
    路径参数：`id`  
    请求体：`SmsCouponParam`  
    响应：`CommonResult`
  - `GET /coupon/list`  
    分页查询优惠券  
    查询参数：`name`、`type`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsCoupon>>`
  - `GET /coupon/{id}`  
    获取优惠券详情  
    路径参数：`id`  
    响应：`CommonResult<SmsCouponParam>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsCouponController;
  ```

##### 3.1.3.4 `com.macro.mall.controller.SmsCouponHistoryController`
- **主要方法及签名：**
  - `GET /couponHistory/list`  
    多条件分页查询  
    查询参数：`couponId`、`useStatus`、`orderSn`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsCouponHistory>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsCouponHistoryController;
  ```

##### 3.1.3.5 `com.macro.mall.controller.SmsFlashPromotionController`
- **主要方法及签名：**
  - `POST /flash/create`  
    新增活动  
    请求体：`SmsFlashPromotion`  
    响应：`CommonResult`
  - `POST /flash/update/{id}`  
    编辑活动  
    路径参数：`id`  
    请求体：`SmsFlashPromotion`  
    响应：`CommonResult`
  - `POST /flash/delete/{id}`  
    删除活动  
    路径参数：`id`  
    响应：`CommonResult`
  - `POST /flash/update/status/{id}`  
    修改上下线状态  
    路径参数：`id`  
    查询参数：`status`  
    响应：`CommonResult`
  - `GET /flash/{id}`  
    获取活动详情  
    路径参数：`id`  
    响应：`CommonResult<SmsFlashPromotion>`
  - `GET /flash/list`  
    分页查询  
    查询参数：`keyword`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsFlashPromotion>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsFlashPromotionController;
  ```

##### 3.1.3.6 `com.macro.mall.controller.SmsFlashPromotionSessionController`
- **主要方法及签名：**
  - `POST /flashSession/create`  
    新增场次  
    请求体：`SmsFlashPromotionSession`  
    响应：`CommonResult`
  - `POST /flashSession/update/{id}`  
    编辑场次  
    路径参数：`id`  
    请求体：`SmsFlashPromotionSession`  
    响应：`CommonResult`
  - `POST /flashSession/update/status/{id}`  
    修改启用状态  
    路径参数：`id`  
    查询参数：`status`  
    响应：`CommonResult`
  - `POST /flashSession/delete/{id}`  
    删除场次  
    路径参数：`id`  
    响应：`CommonResult`
  - `GET /flashSession/{id}`  
    获取场次详情  
    路径参数：`id`  
    响应：`CommonResult<SmsFlashPromotionSession>`
  - `GET /flashSession/list`  
    获取所有场次  
    响应：`CommonResult<List<SmsFlashPromotionSession>>`
  - `GET /flashSession/selectList`  
    获取全部可选场次及数量  
    查询参数：`flashPromotionId`  
    响应：`CommonResult<List<SmsFlashPromotionSessionDetail>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsFlashPromotionSessionController;
  ```

##### 3.1.3.7 `com.macro.mall.controller.SmsFlashPromotionProductRelationController`
- **主要方法及签名：**
  - `POST /flashProductRelation/create`  
    批量添加关联  
    请求体：`List<SmsFlashPromotionProductRelation>`  
    响应：`CommonResult`
  - `POST /flashProductRelation/update/{id}`  
    修改关联  
    路径参数：`id`  
    请求体：`SmsFlashPromotionProductRelation`  
    响应：`CommonResult`
  - `POST /flashProductRelation/delete/{id}`  
    删除关联  
    路径参数：`id`  
    响应：`CommonResult`
  - `GET /flashProductRelation/{id}`  
    获取关联详情  
    路径参数：`id`  
    响应：`CommonResult<SmsFlashPromotionProductRelation>`
  - `GET /flashProductRelation/list`  
    分页查询促销商品  
    查询参数：`flashPromotionId`、`flashPromotionSessionId`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsFlashPromotionProduct>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsFlashPromotionProductRelationController;
  ```

##### 3.1.3.8 `com.macro.mall.controller.SmsHomeAdvertiseController`
- **主要方法及签名：**
  - `POST /home/advertise/create`  
    新增广告  
    请求体：`SmsHomeAdvertise`  
    响应：`CommonResult`
  - `POST /home/advertise/delete`  
    批量删除广告  
    查询参数：`ids`  
    响应：`CommonResult`
  - `POST /home/advertise/update/status/{id}`  
    修改状态  
    路径参数：`id`  
    查询参数：`status`  
    响应：`CommonResult`
  - `GET /home/advertise/{id}`  
    获取广告详情  
    路径参数：`id`  
    响应：`CommonResult<SmsHomeAdvertise>`
  - `POST /home/advertise/update/{id}`  
    修改广告  
    路径参数：`id`  
    请求体：`SmsHomeAdvertise`  
    响应：`CommonResult`
  - `GET /home/advertise/list`  
    分页查询广告  
    查询参数：`name`、`type`、`endTime`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsHomeAdvertise>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsHomeAdvertiseController;
  ```

##### 3.1.3.9 `com.macro.mall.controller.SmsHomeBrandController`
- **主要方法及签名：**
  - `POST /home/brand/create`  
    批量新增首页品牌  
    请求体：`List<SmsHomeBrand>`  
    响应：`CommonResult`
  - `POST /home/brand/update/sort/{id}`  
    修改排序  
    路径参数：`id`  
    查询参数：`sort`  
    响应：`CommonResult`
  - `POST /home/brand/delete`  
    批量删除  
    查询参数：`ids`  
    响应：`CommonResult`
  - `POST /home/brand/update/recommendStatus`  
    批量更新推荐状态  
    查询参数：`ids`、`recommendStatus`  
    响应：`CommonResult`
  - `GET /home/brand/list`  
    分页查询  
    查询参数：`brandName`、`recommendStatus`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsHomeBrand>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsHomeBrandController;
  ```

##### 3.1.3.10 `com.macro.mall.controller.SmsHomeNewProductController`
- **主要方法及签名：**
  - `POST /home/newProduct/create`  
    批量新增新品  
    请求体：`List<SmsHomeNewProduct>`  
    响应：`CommonResult`
  - `POST /home/newProduct/update/sort/{id}`  
    修改排序  
    路径参数：`id`  
    查询参数：`sort`  
    响应：`CommonResult`
  - `POST /home/newProduct/delete`  
    批量删除  
    查询参数：`ids`  
    响应：`CommonResult`
  - `POST /home/newProduct/update/recommendStatus`  
    批量推荐  
    查询参数：`ids`、`recommendStatus`  
    响应：`CommonResult`
  - `GET /home/newProduct/list`  
    分页查询  
    查询参数：`productName`、`recommendStatus`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsHomeNewProduct>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsHomeNewProductController;
  ```

##### 3.1.3.11 `com.macro.mall.controller.SmsHomeRecommendProductController`
- **主要方法及签名：**
  - `POST /home/recommendProduct/create`  
    批量新增人气推荐  
    请求体：`List<SmsHomeRecommendProduct>`  
    响应：`CommonResult`
  - `POST /home/recommendProduct/update/sort/{id}`  
    修改排序  
    路径参数：`id`  
    查询参数：`sort`  
    响应：`CommonResult`
  - `POST /home/recommendProduct/delete`  
    批量删除  
    查询参数：`ids`  
    响应：`CommonResult`
  - `POST /home/recommendProduct/update/recommendStatus`  
    批量推荐  
    查询参数：`ids`、`recommendStatus`  
    响应：`CommonResult`
  - `GET /home/recommendProduct/list`  
    分页查询  
    查询参数：`productName`、`recommendStatus`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsHomeRecommendProduct>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsHomeRecommendProductController;
  ```

##### 3.1.3.12 `com.macro.mall.controller.SmsHomeRecommendSubjectController`
- **主要方法及签名：**
  - `POST /home/recommendSubject/create`  
    批量新增专题推荐  
    请求体：`List<SmsHomeRecommendSubject>`  
    响应：`CommonResult`
  - `POST /home/recommendSubject/update/sort/{id}`  
    修改排序  
    路径参数：`id`  
    查询参数：`sort`  
    响应：`CommonResult`
  - `POST /home/recommendSubject/delete`  
    批量删除  
    查询参数：`ids`  
    响应：`CommonResult`
  - `POST /home/recommendSubject/update/recommendStatus`  
    批量推荐  
    查询参数：`ids`、`recommendStatus`  
    响应：`CommonResult`
  - `GET /home/recommendSubject/list`  
    分页查询  
    查询参数：`subjectName`、`recommendStatus`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<SmsHomeRecommendSubject>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.SmsHomeRecommendSubjectController;
  ```

#### 3.1.4 存储

##### 3.1.4.1 `com.macro.mall.controller.MinioController`
- **主要方法及签名：**
  - `POST /minio/upload`  
    文件上传  
    请求体：`MultipartFile file`  
    响应：`CommonResult<MinioUploadDto>`
  - `POST /minio/delete`  
    删除文件  
    查询参数：`objectName`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.MinioController;
  ```

##### 3.1.4.2 `com.macro.mall.controller.OssController`
- **主要方法及签名：**
  - `GET /aliyun/oss/policy`  
    获取OSS上传签名策略  
    响应：`CommonResult<OssPolicyResult>`
  - `POST /aliyun/oss/callback`  
    OSS上传回调  
    请求体：`HttpServletRequest`  
    响应：`CommonResult<OssCallbackResult>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.OssController;
  ```

#### 3.1.5 权限与用户管理

##### 3.1.5.1 `com.macro.mall.controller.UmsAdminController`
- **主要方法及签名：**
  - `POST /admin/register`  
    用户注册  
    请求体：`UmsAdminParam`  
    响应：`CommonResult<UmsAdmin>`
  - `POST /admin/login`  
    登录获取token  
    请求体：`UmsAdminLoginParam`  
    响应：`CommonResult<Map<String,String>>`
  - `GET /admin/refreshToken`  
    刷新token  
    响应：`CommonResult<Map<String,String>>`
  - `GET /admin/info`  
    获取当前登录用户信息  
    响应：`CommonResult`
  - `POST /admin/logout`  
    登出  
    响应：`CommonResult`
  - `GET /admin/list`  
    分页获取用户列表  
    查询参数：`keyword`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<UmsAdmin>>`
  - `GET /admin/{id}`  
    获取指定用户信息  
    路径参数：`id`  
    响应：`CommonResult<UmsAdmin>`
  - `POST /admin/update/{id}`  
    修改用户信息  
    路径参数：`id`，请求体：`UmsAdmin`  
    响应：`CommonResult`
  - `POST /admin/updatePassword`  
    修改密码  
    请求体：`UpdateAdminPasswordParam`  
    响应：`CommonResult`
  - `POST /admin/delete/{id}`  
    删除用户  
    路径参数：`id`  
    响应：`CommonResult`
  - `POST /admin/updateStatus/{id}`  
    修改帐号状态  
    路径参数：`id`，查询参数：`status`  
    响应：`CommonResult`
  - `POST /admin/role/update`  
    分配角色  
    查询参数：`adminId`、`roleIds`  
    响应：`CommonResult`
  - `GET /admin/role/{adminId}`  
    获取用户角色  
    路径参数：`adminId`  
    响应：`CommonResult<List<UmsRole>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.UmsAdminController;
  ```

##### 3.1.5.2 `com.macro.mall.controller.UmsMenuController`
- **主要方法及签名：**
  - `POST /menu/create`  
    新增菜单  
    请求体：`UmsMenu`  
    响应：`CommonResult`
  - `POST /menu/update/{id}`  
    编辑菜单  
    路径参数：`id`，请求体：`UmsMenu`  
    响应：`CommonResult`
  - `GET /menu/{id}`  
    获取菜单详情  
    路径参数：`id`  
    响应：`CommonResult<UmsMenu>`
  - `POST /menu/delete/{id}`  
    删除菜单  
    路径参数：`id`  
    响应：`CommonResult`
  - `GET /menu/list/{parentId}`  
    分页查询菜单  
    路径参数：`parentId`，查询参数：`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<UmsMenu>>`
  - `GET /menu/treeList`  
    树形结构返回所有菜单  
    响应：`CommonResult<List<UmsMenuNode>>`
  - `POST /menu/updateHidden/{id}`  
    修改显示状态  
    路径参数：`id`，查询参数：`hidden`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.UmsMenuController;
  ```

##### 3.1.5.3 `com.macro.mall.controller.UmsResourceCategoryController`
- **主要方法及签名：**
  - `GET /resourceCategory/listAll`  
    查询所有后台资源分类  
    响应：`CommonResult<List<UmsResourceCategory>>`
  - `POST /resourceCategory/create`  
    新增后台资源分类  
    请求体：`UmsResourceCategory`  
    响应：`CommonResult`
  - `POST /resourceCategory/update/{id}`  
    编辑后台资源分类  
    路径参数：`id`，请求体：`UmsResourceCategory`  
    响应：`CommonResult`
  - `POST /resourceCategory/delete/{id}`  
    删除后台资源分类  
    路径参数：`id`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.UmsResourceCategoryController;
  ```

##### 3.1.5.4 `com.macro.mall.controller.UmsResourceController`
- **主要方法及签名：**
  - `POST /resource/create`  
    新增后台资源  
    请求体：`UmsResource`  
    响应：`CommonResult`
  - `POST /resource/update/{id}`  
    编辑后台资源  
    路径参数：`id`，请求体：`UmsResource`  
    响应：`CommonResult`
  - `GET /resource/{id}`  
    获取资源详情  
    路径参数：`id`  
    响应：`CommonResult<UmsResource>`
  - `POST /resource/delete/{id}`  
    删除后台资源  
    路径参数：`id`  
    响应：`CommonResult`
  - `GET /resource/list`  
    分页模糊查询  
    查询参数：`categoryId`、`nameKeyword`、`urlKeyword`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<UmsResource>>`
  - `GET /resource/listAll`  
    查询所有后台资源  
    响应：`CommonResult<List<UmsResource>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.UmsResourceController;
  ```

##### 3.1.5.5 `com.macro.mall.controller.UmsRoleController`
- **主要方法及签名：**
  - `POST /role/create`  
    新增角色  
    请求体：`UmsRole`  
    响应：`CommonResult`
  - `POST /role/update/{id}`  
    编辑角色  
    路径参数：`id`，请求体：`UmsRole`  
    响应：`CommonResult`
  - `POST /role/delete`  
    批量删除角色  
    查询参数：`ids`  
    响应：`CommonResult`
  - `GET /role/listAll`  
    获取所有角色  
    响应：`CommonResult<List<UmsRole>>`
  - `GET /role/list`  
    分页查询角色  
    查询参数：`keyword`、`pageSize`、`pageNum`  
    响应：`CommonResult<CommonPage<UmsRole>>`
  - `POST /role/updateStatus/{id}`  
    修改角色状态  
    路径参数：`id`，查询参数：`status`  
    响应：`CommonResult`
  - `GET /role/listMenu/{roleId}`  
    获取角色相关菜单  
    路径参数：`roleId`  
    响应：`CommonResult<List<UmsMenu>>`
  - `GET /role/listResource/{roleId}`  
    获取角色相关资源  
    路径参数：`roleId`  
    响应：`CommonResult<List<UmsResource>>`
  - `POST /role/allocMenu`  
    分配菜单  
    查询参数：`roleId`、`menuIds`  
    响应：`CommonResult`
  - `POST /role/allocResource`  
    分配资源  
    查询参数：`roleId`、`resourceIds`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.controller.UmsRoleController;
  ```

##### 3.1.5.6 `com.macro.mall.controller.UmsMemberLevelController`
- **主要方法及签名：**
  - `GET /memberLevel/list`  
    查询所有会员等级  
    查询参数：`defaultStatus`  
    响应：`CommonResult<List<UmsMemberLevel>>`
- **使用方式：**
  ```java
  import com.macro.mall.controller.UmsMemberLevelController;
  ```

---

### 3.2 前台商城相关Controller

#### 3.2.1 `com.macro.mall.portal.controller.UmsMemberController`
- **主要方法及签名：**
  - `POST /sso/register`  
    会员注册  
    查询参数：`username`、`password`、`telephone`、`authCode`  
    响应：`CommonResult`
  - `POST /sso/login`  
    会员登录  
    查询参数：`username`、`password`  
    响应：`CommonResult<Map<String,String>>`
  - `GET /sso/info`  
    获取会员信息  
    响应：`CommonResult<UmsMember>`
  - `GET /sso/getAuthCode`  
    获取验证码  
    查询参数：`telephone`  
    响应：`CommonResult<String>`
  - `POST /sso/updatePassword`  
    修改密码  
    查询参数：`telephone`、`password`、`authCode`  
    响应：`CommonResult`
  - `GET /sso/refreshToken`  
    刷新token  
    响应：`CommonResult<Map<String,String>>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.UmsMemberController;
  ```

#### 3.2.2 `com.macro.mall.portal.controller.HomeController`
- **主要方法及签名：**
  - `GET /home/content`  
    首页内容  
    响应：`CommonResult<HomeContentResult>`
  - `GET /home/recommendProductList`  
    推荐商品分页  
    查询参数：`pageSize`、`pageNum`  
    响应：`CommonResult<List<PmsProduct>>`
  - `GET /home/productCateList/{parentId}`  
    商品分类  
    路径参数：`parentId`  
    响应：`CommonResult<List<PmsProductCategory>>`
  - `GET /home/subjectList`  
    分类专题分页  
    查询参数：`cateId`、`pageSize`、`pageNum`  
    响应：`CommonResult<List<CmsSubject>>`
  - `GET /home/hotProductList`  
    人气推荐  
    查询参数：`pageNum`、`pageSize`  
    响应：`CommonResult<List<PmsProduct>>`
  - `GET /home/newProductList`  
    新品推荐  
    查询参数：`pageNum`、`pageSize`  
    响应：`CommonResult<List<PmsProduct>>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.HomeController;
  ```

#### 3.2.3 `com.macro.mall.portal.controller.PmsPortalBrandController`
- **主要方法及签名：**
  - `GET /brand/recommendList`  
    推荐品牌分页  
    查询参数：`pageSize`、`pageNum`  
    响应：`CommonResult<List<PmsBrand>>`
  - `GET /brand/detail/{brandId}`  
    品牌详情  
    路径参数：`brandId`  
    响应：`CommonResult<PmsBrand>`
  - `GET /brand/productList`  
    品牌相关商品分页  
    查询参数：`brandId`、`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<PmsProduct>>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.PmsPortalBrandController;
  ```

#### 3.2.4 `com.macro.mall.portal.controller.PmsPortalProductController`
- **主要方法及签名：**
  - `GET /product/search`  
    商品综合搜索  
    查询参数：`keyword`、`brandId`、`productCategoryId`、`pageNum`、`pageSize`、`sort`  
    响应：`CommonResult<CommonPage<PmsProduct>>`
  - `GET /product/categoryTreeList`  
    获取分类树  
    响应：`CommonResult<List<PmsProductCategoryNode>>`
  - `GET /product/detail/{id}`  
    商品详情  
    路径参数：`id`  
    响应：`CommonResult<PmsPortalProductDetail>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.PmsPortalProductController;
  ```

#### 3.2.5 `com.macro.mall.portal.controller.OmsCartItemController`
- **主要方法及签名：**
  - `POST /cart/add`  
    添加商品到购物车  
    请求体：`OmsCartItem`  
    响应：`CommonResult`
  - `GET /cart/list`  
    查询购物车列表  
    响应：`CommonResult<List<OmsCartItem>>`
  - `GET /cart/list/promotion`  
    查询购物车商品含促销  
    查询参数：`cartIds` (List<Long>)  
    响应：`CommonResult<List<CartPromotionItem>>`
  - `GET /cart/update/quantity`  
    修改购物车商品数量  
    查询参数：`id`、`quantity`  
    响应：`CommonResult`
  - `GET /cart/getProduct/{productId}`  
    获取购物车商品规格  
    路径参数：`productId`  
    响应：`CommonResult<CartProduct>`
  - `POST /cart/update/attr`  
    修改购物车商品规格  
    请求体：`OmsCartItem`  
    响应：`CommonResult`
  - `POST /cart/delete`  
    删除购物车指定商品  
    查询参数：`ids` (List<Long>)  
    响应：`CommonResult`
  - `POST /cart/clear`  
    清空购物车  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.OmsCartItemController;
  ```

#### 3.2.6 `com.macro.mall.portal.controller.OmsPortalOrderController`
- **主要方法及签名：**
  - `POST /order/generateConfirmOrder`  
    生成确认单  
    请求体：`List<Long> cartIds`  
    响应：`CommonResult<ConfirmOrderResult>`
  - `POST /order/generateOrder`  
    下单  
    请求体：`OrderParam`  
    响应：`CommonResult`
  - `POST /order/paySuccess`  
    支付成功回调  
    查询参数：`orderId`、`payType`  
    响应：`CommonResult`
  - `POST /order/cancelTimeOutOrder`  
    自动取消超时订单  
    响应：`CommonResult`
  - `POST /order/cancelOrder`  
    取消单个订单  
    查询参数：`orderId`  
    响应：`CommonResult`
  - `GET /order/list`  
    订单列表分页  
    查询参数：`status`、`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<OmsOrderDetail>>`
  - `GET /order/detail/{orderId}`  
    订单详情  
    路径参数：`orderId`  
    响应：`CommonResult<OmsOrderDetail>`
  - `POST /order/cancelUserOrder`  
    用户取消订单  
    查询参数：`orderId`  
    响应：`CommonResult`
  - `POST /order/confirmReceiveOrder`  
    用户确认收货  
    查询参数：`orderId`  
    响应：`CommonResult`
  - `POST /order/deleteOrder`  
    用户删除订单  
    查询参数：`orderId`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.OmsPortalOrderController;
  ```

#### 3.2.7 `com.macro.mall.portal.controller.OmsPortalOrderReturnApplyController`
- **主要方法及签名：**
  - `POST /returnApply/create`  
    用户退货申请  
    请求体：`OmsOrderReturnApplyParam`  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.OmsPortalOrderReturnApplyController;
  ```

#### 3.2.8 `com.macro.mall.portal.controller.UmsMemberCouponController`
- **主要方法及签名：**
  - `POST /member/coupon/add/{couponId}`  
    领取优惠券  
    路径参数：`couponId`  
    响应：`CommonResult`
  - `GET /member/coupon/listHistory`  
    优惠券历史  
    查询参数：`useStatus`  
    响应：`CommonResult<List<SmsCouponHistory>>`
  - `GET /member/coupon/list`  
    优惠券列表  
    查询参数：`useStatus`  
    响应：`CommonResult<List<SmsCoupon>>`
  - `GET /member/coupon/list/cart/{type}`  
    获取购物车相关优惠券  
    路径参数：`type`  
    响应：`CommonResult<List<SmsCouponHistoryDetail>>`
  - `GET /member/coupon/listByProduct/{productId}`  
    获取商品相关优惠券  
    路径参数：`productId`  
    响应：`CommonResult<List<SmsCoupon>>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.UmsMemberCouponController;
  ```

#### 3.2.9 `com.macro.mall.portal.controller.UmsMemberReceiveAddressController`
- **主要方法及签名：**
  - `POST /member/address/add`  
    新增收货地址  
    请求体：`UmsMemberReceiveAddress`  
    响应：`CommonResult`
  - `POST /member/address/delete/{id}`  
    删除收货地址  
    路径参数：`id`  
    响应：`CommonResult`
  - `POST /member/address/update/{id}`  
    更新收货地址  
    路径参数：`id`，请求体：`UmsMemberReceiveAddress`  
    响应：`CommonResult`
  - `GET /member/address/list`  
    获取收货地址列表  
    响应：`CommonResult<List<UmsMemberReceiveAddress>>`
  - `GET /member/address/{id}`  
    获取收货地址详情  
    路径参数：`id`  
    响应：`CommonResult<UmsMemberReceiveAddress>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.UmsMemberReceiveAddressController;
  ```

#### 3.2.10 `com.macro.mall.portal.controller.MemberAttentionController`
- **主要方法及签名：**
  - `POST /member/attention/add`  
    添加品牌关注  
    请求体：`MemberBrandAttention`  
    响应：`CommonResult`
  - `POST /member/attention/delete`  
    取消品牌关注  
    查询参数：`brandId`  
    响应：`CommonResult`
  - `GET /member/attention/list`  
    分页查询关注列表  
    查询参数：`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<MemberBrandAttention>>`
  - `GET /member/attention/detail`  
    获取关注详情  
    查询参数：`brandId`  
    响应：`CommonResult<MemberBrandAttention>`
  - `POST /member/attention/clear`  
    清空关注列表  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.MemberAttentionController;
  ```

#### 3.2.11 `com.macro.mall.portal.controller.MemberProductCollectionController`
- **主要方法及签名：**
  - `POST /member/productCollection/add`  
    添加商品收藏  
    请求体：`MemberProductCollection`  
    响应：`CommonResult`
  - `POST /member/productCollection/delete`  
    删除商品收藏  
    查询参数：`productId`  
    响应：`CommonResult`
  - `GET /member/productCollection/list`  
    分页查询收藏列表  
    查询参数：`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<MemberProductCollection>>`
  - `GET /member/productCollection/detail`  
    收藏详情  
    查询参数：`productId`  
    响应：`CommonResult<MemberProductCollection>`
  - `POST /member/productCollection/clear`  
    清空收藏  
    响应：`CommonResult`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.MemberProductCollectionController;
  ```

#### 3.2.12 `com.macro.mall.portal.controller.MemberReadHistoryController`
- **主要方法及签名：**
  - `POST /member/readHistory/create`  
    创建浏览记录  
    请求体：`MemberReadHistory`  
    响应：`CommonResult`
  - `POST /member/readHistory/delete`  
    删除浏览记录  
    查询参数：`ids` (List<String>)  
    响应：`CommonResult`
  - `POST /member/readHistory/clear`  
    清空浏览记录  
    响应：`CommonResult`
  - `GET /member/readHistory/list`  
    分页获取浏览记录  
    查询参数：`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<MemberReadHistory>>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.MemberReadHistoryController;
  ```

#### 3.2.13 `com.macro.mall.portal.controller.AlipayController`
- **主要方法及签名：**
  - `GET /alipay/pay`  
    支付宝电脑网站支付  
    查询参数：`AliPayParam`  
    响应：写入`HttpServletResponse`流
  - `GET /alipay/webPay`  
    支付宝手机网站支付  
    查询参数：`AliPayParam`  
    响应：写入`HttpServletResponse`流
  - `POST /alipay/notify`  
    支付宝异步回调  
    请求体：`HttpServletRequest`  
    响应：`String` (`success`/`failure`)
  - `GET /alipay/query`  
    查询订单状态  
    查询参数：`outTradeNo`、`tradeNo`  
    响应：`CommonResult<String>`
- **使用方式：**
  ```java
  import com.macro.mall.portal.controller.AlipayController;
  ```

---

### 3.3 搜索相关Controller

#### 3.3.1 `com.macro.mall.search.controller.EsProductController`
- **主要方法及签名：**
  - `POST /esProduct/importAll`  
    导入所有商品到ES  
    响应：`CommonResult<Integer>`
  - `GET /esProduct/delete/{id}`  
    删除单个商品  
    路径参数：`id`  
    响应：`CommonResult<Object>`
  - `POST /esProduct/delete/batch`  
    批量删除商品  
    查询参数：`ids` (List<Long>)  
    响应：`CommonResult<Object>`
  - `POST /esProduct/create/{id}`  
    根据ID创建商品  
    路径参数：`id`  
    响应：`CommonResult<EsProduct>`
  - `GET /esProduct/search/simple`  
    简单搜索  
    查询参数：`keyword`、`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<EsProduct>>`
  - `GET /esProduct/search`  
    综合搜索/筛选/排序  
    查询参数：`keyword`、`brandId`、`productCategoryId`、`pageNum`、`pageSize`、`sort`  
    响应：`CommonResult<CommonPage<EsProduct>>`
  - `GET /esProduct/recommend/{id}`  
    推荐商品  
    路径参数：`id`，查询参数：`pageNum`、`pageSize`  
    响应：`CommonResult<CommonPage<EsProduct>>`
  - `GET /esProduct/search/relate`  
    搜索相关品牌/分类/属性  
    查询参数：`keyword`  
    响应：`CommonResult<EsProductRelatedInfo>`
- **使用方式：**
  ```java
  import com.macro.mall.search.controller.EsProductController;
  ```

---

> **注**：所有接口的请求与响应均采用Spring Boot REST风格，通用返回格式为`CommonResult<T>`。请求参数如无特别说明均为标准表单或JSON格式，具体类型请参考源码及Swagger/OpenAPI注释。  
> 导包请根据实际包路径import相关Controller类，调用方式请遵循Spring MVC/RestController规范。