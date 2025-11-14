## 5. 类之间关系说明

```mermaid
classDiagram
    direction TB

    %% ==============================
    %% Controller层
    %% ==============================
    class AlipayController {
        - AlipayConfig alipayConfig
        - AlipayService alipayService
        +pay(AliPayParam, HttpServletResponse)
        +webPay(AliPayParam, HttpServletResponse)
        +notify(HttpServletRequest) String
        +query(String, String) CommonResult~String~
    }

    %% ==============================
    %% 支付宝相关
    %% ==============================
    class AlipayService {
        <<interface>>
        +pay(AliPayParam) String
        +notify(Map~String, String~) String
        +query(String, String) String
        +webPay(AliPayParam) String
    }
    class AlipayServiceImpl {
        +pay(AliPayParam) String
        +notify(Map~String, String~) String
        +query(String, String) String
        +webPay(AliPayParam) String
    }

    %% ==============================
    %% 通用返回类型
    %% ==============================
    class CommonResult~T~ {
        -long code
        -String message
        -T data
        +success(T data) CommonResult~T~
        +success(T data, String message) CommonResult~T~
        +failed(IErrorCode errorCode) CommonResult~T~
        +failed(IErrorCode errorCode, String message) CommonResult~T~
        +failed(String message) CommonResult~T~
        +failed() CommonResult~T~
        +validateFailed() CommonResult~T~
        +validateFailed(String message) CommonResult~T~
        +unauthorized(T data) CommonResult~T~
        +forbidden(T data) CommonResult~T~
        +getCode() long
        +getMessage() String
        +getData() T
    }

    %% ==============================
    %% 订单相关 Service
    %% ==============================
    class OmsPortalOrderService {
        <<interface>>
        +generateConfirmOrder(List~Long~) ConfirmOrderResult
        +generateOrder(OrderParam) Map~String, Object~
        +paySuccess(Long, Integer) Integer
        +cancelTimeOutOrder() Integer
        +cancelOrder(Long)
        +sendDelayMessageCancelOrder(Long)
        +confirmReceiveOrder(Long)
        +list(Integer, Integer, Integer) CommonPage~OmsOrderDetail~
        +detail(Long) OmsOrderDetail
        +deleteOrder(Long)
        +paySuccessByOrderSn(String, Integer)
    }
    class OmsPortalOrderServiceImpl {
        +generateConfirmOrder(List~Long~) ConfirmOrderResult
        +generateOrder(OrderParam) Map~String, Object~
        +paySuccess(Long, Integer) Integer
        +cancelTimeOutOrder() Integer
        +cancelOrder(Long)
        +sendDelayMessageCancelOrder(Long)
        +confirmReceiveOrder(Long)
        +list(Integer, Integer, Integer) CommonPage~OmsOrderDetail~
        +detail(Long) OmsOrderDetail
        +deleteOrder(Long)
        +paySuccessByOrderSn(String, Integer)
        ..内部方法..
        -generateOrderSn(OmsOrder) String
        -deleteCartItemList(List, UmsMember)
        -updateCouponStatus(Long, Long, Integer)
        -calcCartAmount(List) ConfirmOrderResult.CalcAmount
    }

    %% ==============================
    %% 订单实体及持久层
    %% ==============================
    class OmsOrder {
        -Long id
        -Long memberId
        -Long couponId
        -String orderSn
        -Date createTime
        -String memberUsername
        -BigDecimal totalAmount
        -BigDecimal payAmount
        -BigDecimal freightAmount
        -BigDecimal promotionAmount
        -BigDecimal integrationAmount
        -BigDecimal couponAmount
        -BigDecimal discountAmount
        -Integer payType
        -Integer sourceType
        -Integer status
        -Integer orderType
        -String deliveryCompany
        -String deliverySn
        -Integer autoConfirmDay
        -Integer integration
        -Integer growth
        -String promotionInfo
        -Integer billType
        -String billHeader
        -String billContent
        -String billReceiverPhone
        -String billReceiverEmail
        -String receiverName
        -String receiverPhone
        -String receiverPostCode
        -String receiverProvince
        -String receiverCity
        -String receiverRegion
        -String receiverDetailAddress
        -String note
        -Integer confirmStatus
        -Integer deleteStatus
        -Integer useIntegration
        -Date paymentTime
        -Date deliveryTime
        -Date receiveTime
        -Date commentTime
        -Date modifyTime
        +getId() Long
        +getStatus() Integer
        +setDeleteStatus(Integer)
        +...（其余get/set省略）
    }

    class OmsOrderMapper {
        <<interface>>
        +selectByPrimaryKey(Long) OmsOrder
        +selectByExample(OmsOrderExample) List~OmsOrder~
        +insert(OmsOrder)
        +updateByPrimaryKey(OmsOrder)
        +updateByExampleSelective(OmsOrder, OmsOrderExample)
    }

    class OmsOrderExample {
        +createCriteria() Criteria
        +setOrderByClause(String)
    }
    class OmsOrderItem {
        -Long id
        -Long orderId
        -String orderSn
        -Long productId
        -BigDecimal productPrice
        -Integer productQuantity
        -Long productSkuId
        -String productSkuCode
        -Long productCategoryId
        -String promotionName
        -BigDecimal promotionAmount
        -BigDecimal couponAmount
        -BigDecimal integrationAmount
        -BigDecimal realAmount
        -Integer giftIntegration
        -Integer giftGrowth
        -String productAttr
        +getProductId() Long
        +getProductPrice() BigDecimal
        +getProductQuantity() Integer
        +getPromotionAmount() BigDecimal
        +getCouponAmount() BigDecimal
        +setRealAmount(BigDecimal)
        +setCouponAmount(BigDecimal)
        +setOrderId(Long)
        +setOrderSn(String)
        +...（其余get/set省略）
    }
    class OmsOrderItemExample {
        +createCriteria() Criteria
    }
    class OmsOrderSetting {
        -Long id
        -Integer flashOrderOvertime
        -Integer normalOrderOvertime
        -Integer confirmOvertime
        -Integer finishOvertime
        -Integer commentOvertime
        +getNormalOrderOvertime() Integer
        +getConfirmOvertime() Integer
    }
    class OmsOrderSettingMapper {
        <<interface>>
        +selectByPrimaryKey(Long) OmsOrderSetting
        +selectByExample(OmsOrderSettingExample) List~OmsOrderSetting~
    }

    %% ==============================
    %% 购物车相关
    %% ==============================
    class OmsCartItem {
        -Long id
        -Long productId
        -Long productSkuId
        -Integer quantity
        -BigDecimal price
        -String productPic
        -String productName
        -String productSkuCode
        -Long productCategoryId
        -String productBrand
        -String productSn
        -String productAttr
        +getQuantity() Integer
        +getPrice() BigDecimal
        +getProductId() Long
        +getProductSkuId() Long
        +getProductSkuCode() String
        +getProductCategoryId() Long
        +getProductBrand() String
        +getProductPic() String
        +getProductName() String
        +getProductSn() String
        +getProductAttr() String
    }
    class OmsCartItemService {
        <<interface>>
        +listPromotion(Long, List~Long~) List~CartPromotionItem~
        +delete(Long, List~Long~)
    }

    %% ==============================
    %% 会员、地址、积分相关
    %% ==============================
    class UmsMember {
        -Long id
        -String username
        -Integer integration
        +getId() Long
        +getIntegration() Integer
        +setIntegration(Integer)
        +getUsername() String
    }
    class UmsMemberService {
        <<interface>>
        +getCurrentMember() UmsMember
        +getById(Long) UmsMember
        +updateIntegration(Long, Integer)
    }
    class UmsMemberReceiveAddress {
        -Long id
        -String name
        -String phoneNumber
        -String postCode
        -String province
        -String city
        -String region
        -String detailAddress
        +getName() String
        +getPhoneNumber() String
        +getPostCode() String
        +getProvince() String
        +getCity() String
        +getRegion() String
        +getDetailAddress() String
    }
    class UmsMemberReceiveAddressService {
        <<interface>>
        +list() List~UmsMemberReceiveAddress~
        +getItem(Long) UmsMemberReceiveAddress
    }
    class UmsIntegrationConsumeSetting {
        -Long id
        -Integer deductionPerAmount
        -Integer maxPercentPerOrder
        -Integer useUnit
        -Integer couponStatus
        +getUseUnit() Integer
        +getCouponStatus() Integer
        +getMaxPercentPerOrder() Integer
    }
    class UmsIntegrationConsumeSettingMapper {
        <<interface>>
        +selectByPrimaryKey(Long) UmsIntegrationConsumeSetting
    }

    %% ==============================
    %% 优惠券相关
    %% ==============================
    class UmsMemberCouponService {
        <<interface>>
        +listCart(List~CartPromotionItem~, Integer) List~SmsCouponHistoryDetail~
    }
    class SmsCoupon {
        -Long id
        -BigDecimal amount
        -Integer useType
        +getId() Long
        +getAmount() BigDecimal
        +getUseType() Integer
    }
    class SmsCouponHistoryDetail {
        -SmsCoupon coupon
        -List~SmsCouponProductCategoryRelation~ categoryRelationList
        -List~SmsCouponProductRelation~ productRelationList
        +getCoupon() SmsCoupon
        +getCategoryRelationList() List~SmsCouponProductCategoryRelation~
        +getProductRelationList() List~SmsCouponProductRelation~
    }
    class SmsCouponHistoryExample {
        +createCriteria() Criteria
    }
    class SmsCouponHistory {
        -Long id
        -Long couponId
        -Long memberId
        -Integer useStatus
        -Date useTime
        +setUseStatus(Integer)
        +setUseTime(Date)
    }
    class SmsCouponHistoryMapper {
        <<interface>>
        +selectByExample(SmsCouponHistoryExample) List~SmsCouponHistory~
        +updateByPrimaryKeySelective(SmsCouponHistory)
    }
    class SmsCouponProductRelation {
        -Long productId
        +getProductId() Long
    }
    class SmsCouponProductCategoryRelation {
        -Long productCategoryId
        +getProductCategoryId() Long
    }

    %% ==============================
    %% DAO和分页
    %% ==============================
    class PortalOrderDao {
        <<interface>>
        +getDetail(Long) OmsOrderDetail
        +getTimeOutOrders(Integer) List~OmsOrderDetail~
        +updateOrderStatus(List~Long~, Integer)
        +releaseSkuStockLock(List~OmsOrderItem~)
        +lockStockBySkuId(Long, Integer)
        +reduceSkuStock(Long, Integer)
        +releaseStockBySkuId(Long, Integer)
    }
    class PortalOrderItemDao {
        <<interface>>
        +insertList(List~OmsOrderItem~)
    }
    class CommonPage~T~ {
        -Integer pageNum
        -Integer pageSize
        -Integer totalPage
        -Long total
        -List~T~ list
        +restPage(List~T~) CommonPage~T~
        +getPageNum() Integer
        +setPageNum(Integer)
        +setPageSize(Integer)
        +getTotal() Long
        +setTotal(Long)
        +setList(List~T~)
        +setTotalPage(Integer)
        +getTotalPage() Integer
    }

    %% ==============================
    %% 其它
    %% ==============================
    class Asserts {
        +fail(String)
        +fail(IErrorCode)
    }
    class RedisService {
        <<interface>>
        +incr(String, long) Long
    }
    class CancelOrderSender {
        +sendMessage(Long, long)
    }
    class PmsSkuStock {
        -Integer lockStock
        +setLockStock(Integer)
        +getLockStock() Integer
    }
    class CartPromotionItem {
        -Long id
        -Long productId
        -Long productSkuId
        -Integer quantity
        -BigDecimal price
        -BigDecimal reduceAmount
        -Integer integration
        -Integer growth
        -String productName
        -String productBrand
        -String productPic
        -String productSkuCode
        -Long productCategoryId
        -String promotionMessage
        -Integer realStock
        +getId() Long
        +getProductId() Long
        +getProductSkuId() Long
        +getQuantity() Integer
        +getPrice() BigDecimal
        +getReduceAmount() BigDecimal
        +getIntegration() Integer
        +getGrowth() Integer
        +getProductName() String
        +getProductBrand() String
        +getProductPic() String
        +getProductSkuCode() String
        +getProductCategoryId() Long
        +getPromotionMessage() String
        +getRealStock() Integer
    }
    class OmsOrderDetail {
        -Long id
        -List~OmsOrderItem~ orderItemList
        +getId() Long
        +getOrderItemList() List~OmsOrderItem~
        +setOrderItemList(List~OmsOrderItem~)
    }
    class ConfirmOrderResult {
        -List~CartPromotionItem~ cartPromotionItemList
        -List~UmsMemberReceiveAddress~ memberReceiveAddressList
        -List~SmsCouponHistoryDetail~ couponHistoryDetailList
        -Integer memberIntegration
        -UmsIntegrationConsumeSetting integrationConsumeSetting
        -CalcAmount calcAmount
        +setCartPromotionItemList(List~CartPromotionItem~)
        +setMemberReceiveAddressList(List~UmsMemberReceiveAddress~)
        +setCouponHistoryDetailList(List~SmsCouponHistoryDetail~)
        +setMemberIntegration(Integer)
        +setIntegrationConsumeSetting(UmsIntegrationConsumeSetting)
        +setCalcAmount(CalcAmount)
    }
    class CalcAmount {
        -BigDecimal totalAmount
        -BigDecimal promotionAmount
        -BigDecimal payAmount
        -BigDecimal freightAmount
        +setTotalAmount(BigDecimal)
        +setPromotionAmount(BigDecimal)
        +setPayAmount(BigDecimal)
        +setFreightAmount(BigDecimal)
    }

    %% ==============================
    %% 关系
    %% ==============================

    %% 控制器与服务
    AlipayController --> AlipayService : 使用
    AlipayController --> CommonResult : 使用(success)

    %% 支付实现
    AlipayServiceImpl ..|> AlipayService : 实现
    AlipayServiceImpl --> OmsPortalOrderService : 使用
    AlipayServiceImpl --> PortalOrderDao : 使用

    %% 订单服务实现
    OmsPortalOrderServiceImpl ..|> OmsPortalOrderService : 实现
    OmsPortalOrderServiceImpl --> OmsOrderMapper : 使用
    OmsPortalOrderServiceImpl --> OmsOrder : 使用/返回
    OmsPortalOrderServiceImpl --> OmsOrderExample : 使用
    OmsPortalOrderServiceImpl --> OmsOrderSetting : 使用
    OmsPortalOrderServiceImpl --> OmsOrderSettingMapper : 使用
    OmsPortalOrderServiceImpl --> OmsOrderItem : 使用
    OmsPortalOrderServiceImpl --> OmsOrderItemExample : 使用
    OmsPortalOrderServiceImpl --> PortalOrderDao : 使用
    OmsPortalOrderServiceImpl --> PortalOrderItemDao : 使用
    OmsPortalOrderServiceImpl --> OmsCartItemService : 使用
    OmsPortalOrderServiceImpl --> UmsMemberService : 使用
    OmsPortalOrderServiceImpl --> UmsMember : 使用
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService : 使用
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddress : 使用
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSettingMapper : 使用
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting : 使用
    OmsPortalOrderServiceImpl --> UmsMemberCouponService : 使用
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample : 使用
    OmsPortalOrderServiceImpl --> SmsCouponHistory : 使用
    OmsPortalOrderServiceImpl --> SmsCouponHistoryMapper : 使用
    OmsPortalOrderServiceImpl --> SmsCouponProductCategoryRelation : 使用
    OmsPortalOrderServiceImpl --> SmsCouponProductRelation : 使用
    OmsPortalOrderServiceImpl --> SmsCoupon : 使用
    OmsPortalOrderServiceImpl --> CommonPage : 返回
    OmsPortalOrderServiceImpl --> ConfirmOrderResult : 返回
    OmsPortalOrderServiceImpl --> OmsOrderDetail : 返回
    OmsPortalOrderServiceImpl --> Asserts : 使用
    OmsPortalOrderServiceImpl --> RedisService : 使用
    OmsPortalOrderServiceImpl --> CancelOrderSender : 使用
    OmsPortalOrderServiceImpl --> PmsSkuStockMapper : 使用
    OmsPortalOrderServiceImpl --> PmsSkuStock : 使用
    OmsPortalOrderServiceImpl --> CartPromotionItem : 使用
    OmsPortalOrderServiceImpl --> CalcAmount : 使用

    %% Mapper间
    OmsOrderMapper --> OmsOrder : 返回
    OmsOrderSettingMapper --> OmsOrderSetting : 返回
    SmsCouponHistoryMapper --> SmsCouponHistory : 返回

    %% 其它
    UmsMemberService --> UmsMember : 返回
    UmsMemberReceiveAddressService --> UmsMemberReceiveAddress : 返回
    UmsIntegrationConsumeSettingMapper --> UmsIntegrationConsumeSetting : 返回
    UmsMemberCouponService --> SmsCouponHistoryDetail : 返回
    SmsCouponHistoryDetail --> SmsCoupon : getCoupon()
    SmsCouponHistoryDetail --> SmsCouponProductCategoryRelation : getCategoryRelationList()
    SmsCouponHistoryDetail --> SmsCouponProductRelation : getProductRelationList()
    PortalOrderDao --> OmsOrderDetail : getDetail()
    PortalOrderDao --> OmsOrderItem : 使用
    PortalOrderItemDao --> OmsOrderItem : insertList
    CartPromotionItem --> OmsCartItem : 组合

    %% 泛型依赖
    CommonPage o-- OmsOrderDetail
    CommonPage o-- OmsOrder

    ConfirmOrderResult o-- CalcAmount
    ConfirmOrderResult o-- CartPromotionItem
    ConfirmOrderResult o-- UmsMemberReceiveAddress
    ConfirmOrderResult o-- SmsCouponHistoryDetail

    OmsOrderDetail o-- OmsOrderItem

    OmsPortalOrderServiceImpl ..> CommonResult : 返回类型
    AlipayController ..> CommonResult : 返回类型

    %% 泛型标注
    class CommonResult~T~ {
        <<generic>>
    }
    class CommonPage~T~ {
        <<generic>>
    }
```

---

**说明：**

- 箭头 `-->` 表示“使用/依赖/返回”关系，`..|>` 表示实现接口，`o--` 表示聚合/组合关系。
- `<<interface>>`、`<<generic>>` 及其他标注用于区分接口、泛型等。
- 关键方法与属性已在节点中简要列出，实际类成员较多时已省略部分 getter/setter。
- 该UML图覆盖了支付宝支付、订单处理、优惠券等主要业务链路的结构与调用关系。
来源文件id为 [384, 518, 519, 525, 533, 280, 281, 540, 286, 414, 416, 545, 418, 419, 420, 549, 421, 551, 556, 557, 558, 559, 306, 307, 566, 454, 456, 330, 465, 248, 365, 238, 239, 495, 245, 374, 504, 377, 381, 382, 383]