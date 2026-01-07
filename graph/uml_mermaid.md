```mermaid
classDiagram
    class AlipayController {
        +pay(AliPayParam aliPayParam, HttpServletResponse response)
        +webPay(AliPayParam aliPayParam, HttpServletResponse response)
        +notify(HttpServletRequest request)
        +query(String outTradeNo, String tradeNo)
        -AlipayConfig alipayConfig
        -AlipayService alipayService
    }
    class CommonResult~T~ {
        -long code
        -String message
        -T data
        +getCode()
        +setCode(long code)
        +getMessage()
        +setMessage(String message)
        +getData()
        +setData(T data)
        +success(T data)
        +success(T data, String message)
        +failed(IErrorCode errorCode)
        +failed(IErrorCode errorCode, String message)
        +failed(String message)
        +failed()
        +validateFailed()
        +validateFailed(String message)
        +unauthorized(T data)
        +forbidden(T data)
    }
    class AlipayService {
        <<interface>>
        +pay(AliPayParam aliPayParam)
        +notify(Map~String,String~ params)
        +query(String outTradeNo, String tradeNo)
        +webPay(AliPayParam aliPayParam)
    }
    class AlipayServiceImpl {
        +pay(AliPayParam aliPayParam)
        +notify(Map~String,String~ params)
        +query(String outTradeNo, String tradeNo)
        +webPay(AliPayParam aliPayParam)
        -AlipayConfig alipayConfig
        -AlipayClient alipayClient
        -OmsOrderMapper orderMapper
        -OmsPortalOrderService portalOrderService
    }
    class OmsPortalOrderService {
        <<interface>>
        +generateConfirmOrder(List~Long~ cartIds)
        +generateOrder(OrderParam orderParam)
        +paySuccess(Long orderId, Integer payType)
        +cancelTimeOutOrder()
        +cancelOrder(Long orderId)
        +sendDelayMessageCancelOrder(Long orderId)
        +confirmReceiveOrder(Long orderId)
        +list(Integer status, Integer pageNum, Integer pageSize)
        +detail(Long orderId)
        +deleteOrder(Long orderId)
        +paySuccessByOrderSn(String orderSn, Integer payType)
    }
    class CommonPage~T~ {
        -Integer pageNum
        -Integer pageSize
        -Integer totalPage
        -Long total
        -List~T~ list
        +getPageNum()
        +setPageNum(Integer pageNum)
        +getPageSize()
        +setPageSize(Integer pageSize)
        +getTotalPage()
        +setTotalPage(Integer totalPage)
        +getList()
        +setList(List~T~ list)
        +getTotal()
        +setTotal(Long total)
        +restPage(List~T~ list)
        +restPage(Page~T~ pageInfo)
    }
    class ConfirmOrderResult {
    }
    class OmsOrderDetail {
    }
    class OmsPortalOrderServiceImpl {
        +generateConfirmOrder(List~Long~ cartIds)
        +generateOrder(OrderParam orderParam)
        +paySuccess(Long orderId, Integer payType)
        +cancelTimeOutOrder()
        +cancelOrder(Long orderId)
        +sendDelayMessageCancelOrder(Long orderId)
        +confirmReceiveOrder(Long orderId)
        +list(Integer status, Integer pageNum, Integer pageSize)
        +detail(Long orderId)
        +deleteOrder(Long orderId)
        +paySuccessByOrderSn(String orderSn, Integer payType)
        -UmsMemberService memberService
        -OmsCartItemService cartItemService
        -UmsMemberReceiveAddressService memberReceiveAddressService
        -UmsMemberCouponService memberCouponService
        -UmsIntegrationConsumeSettingMapper integrationConsumeSettingMapper
        -PmsSkuStockMapper skuStockMapper
        -SmsCouponHistoryDao couponHistoryDao
        -OmsOrderMapper orderMapper
        -PortalOrderItemDao orderItemDao
        -SmsCouponHistoryMapper couponHistoryMapper
        -RedisService redisService
        -String REDIS_KEY_ORDER_ID
        -String REDIS_DATABASE
        -PortalOrderDao portalOrderDao
        -OmsOrderSettingMapper orderSettingMapper
        -OmsOrderItemMapper orderItemMapper
        -CancelOrderSender cancelOrderSender
    }
    class Asserts {
        +fail(String message)
        +fail(IErrorCode errorCode)
    }
    class RedisService {
        <<interface>>
        +set(String key, Object value, long time)
        +set(String key, Object value)
        +get(String key)
        +del(String key)
        +del(List~String~ keys)
        +expire(String key, long time)
        +getExpire(String key)
        +hasKey(String key)
        +incr(String key, long delta)
        +decr(String key, long delta)
        +hGet(String key, String hashKey)
        +hSet(String key, String hashKey, Object value, long time)
        +hSet(String key, String hashKey, Object value)
        +hGetAll(String key)
        +hSetAll(String key, Map~String,Object~ map, long time)
        +hSetAll(String key, Map~String,?~ map)
        +hDel(String key, Object... hashKey)
        +hHasKey(String key, String hashKey)
        +hIncr(String key, String hashKey, Long delta)
        +hDecr(String key, String hashKey, Long delta)
        +sMembers(String key)
        +sAdd(String key, Object... values)
        +sAdd(String key, long time, Object... values)
        +sIsMember(String key, Object value)
        +sSize(String key)
        +sRemove(String key, Object... values)
        +lRange(String key, long start, long end)
        +lSize(String key)
        +lIndex(String key, long index)
        +lPush(String key, Object value)
        +lPush(String key, Object value, long time)
        +lPushAll(String key, Object... values)
        +lPushAll(String key, Long time, Object... values)
        +lRemove(String key, long count, Object value)
    }
    class SmsCouponHistoryMapper {
        <<interface>>
        +countByExample(SmsCouponHistoryExample example)
        +deleteByExample(SmsCouponHistoryExample example)
        +deleteByPrimaryKey(Long id)
        +insert(SmsCouponHistory record)
        +insertSelective(SmsCouponHistory record)
        +selectByExample(SmsCouponHistoryExample example)
        +selectByPrimaryKey(Long id)
        +updateByExampleSelective(SmsCouponHistory record, SmsCouponHistoryExample example)
        +updateByExample(SmsCouponHistory record, SmsCouponHistoryExample example)
        +updateByPrimaryKeySelective(SmsCouponHistory record)
        +updateByPrimaryKey(SmsCouponHistory record)
    }
    class OmsOrderItemMapper {
        <<interface>>
        +countByExample(OmsOrderItemExample example)
        +deleteByExample(OmsOrderItemExample example)
        +deleteByPrimaryKey(Long id)
        +insert(OmsOrderItem record)
        +insertSelective(OmsOrderItem record)
        +selectByExample(OmsOrderItemExample example)
        +selectByPrimaryKey(Long id)
        +updateByExampleSelective(OmsOrderItem record, OmsOrderItemExample example)
        +updateByExample(OmsOrderItem record, OmsOrderItemExample example)
        +updateByPrimaryKeySelective(OmsOrderItem record)
        +updateByPrimaryKey(OmsOrderItem record)
    }
    class UmsIntegrationConsumeSettingMapper {
        <<interface>>
        +countByExample(UmsIntegrationConsumeSettingExample example)
        +deleteByExample(UmsIntegrationConsumeSettingExample example)
        +deleteByPrimaryKey(Long id)
        +insert(UmsIntegrationConsumeSetting record)
        +insertSelective(UmsIntegrationConsumeSetting record)
        +selectByExample(UmsIntegrationConsumeSettingExample example)
        +selectByPrimaryKey(Long id)
        +updateByExampleSelective(UmsIntegrationConsumeSetting record, UmsIntegrationConsumeSettingExample example)
        +updateByExample(UmsIntegrationConsumeSetting record, UmsIntegrationConsumeSettingExample example)
        +updateByPrimaryKeySelective(UmsIntegrationConsumeSetting record)
        +updateByPrimaryKey(UmsIntegrationConsumeSetting record)
    }
    class OmsOrderMapper {
        <<interface>>
        +countByExample(OmsOrderExample example)
        +deleteByExample(OmsOrderExample example)
        +deleteByPrimaryKey(Long id)
        +insert(OmsOrder record)
        +insertSelective(OmsOrder record)
        +selectByExample(OmsOrderExample example)
        +selectByPrimaryKey(Long id)
        +updateByExampleSelective(OmsOrder record, OmsOrderExample example)
        +updateByExample(OmsOrder record, OmsOrderExample example)
        +updateByPrimaryKeySelective(OmsOrder record)
        +updateByPrimaryKey(OmsOrder record)
    }
    class OmsOrderSettingMapper {
        <<interface>>
        +countByExample(OmsOrderSettingExample example)
        +deleteByExample(OmsOrderSettingExample example)
        +deleteByPrimaryKey(Long id)
        +insert(OmsOrderSetting record)
        +insertSelective(OmsOrderSetting record)
        +selectByExample(OmsOrderSettingExample example)
        +selectByPrimaryKey(Long id)
        +updateByExampleSelective(OmsOrderSetting record, OmsOrderSettingExample example)
        +updateByExample(OmsOrderSetting record, OmsOrderSettingExample example)
        +updateByPrimaryKeySelective(OmsOrderSetting record)
        +updateByPrimaryKey(OmsOrderSetting record)
    }
    class PmsSkuStockMapper {
        <<interface>>
        +countByExample(PmsSkuStockExample example)
        +deleteByExample(PmsSkuStockExample example)
        +deleteByPrimaryKey(Long id)
        +insert(PmsSkuStock record)
        +insertSelective(PmsSkuStock record)
        +selectByExample(PmsSkuStockExample example)
        +selectByPrimaryKey(Long id)
        +updateByExampleSelective(PmsSkuStock record, PmsSkuStockExample example)
        +updateByExample(PmsSkuStock record, PmsSkuStockExample example)
        +updateByPrimaryKeySelective(PmsSkuStock record)
        +updateByPrimaryKey(PmsSkuStock record)
    }
    class OmsOrderExample {
    }
    class SmsCouponProductCategoryRelation {
        -Long id
        -Long couponId
        -Long productCategoryId
        -String productCategoryName
        -String parentCategoryName
        +getProductCategoryId()
    }
    class SmsCouponHistoryExample {
    }
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
        +getId()
        +setId(Long id)
        +getMemberId()
        +setMemberId(Long memberId)
        +getCouponId()
        +setCouponId(Long couponId)
        +getOrderSn()
        +setOrderSn(String orderSn)
        +getCreateTime()
        +setCreateTime(Date createTime)
        +getMemberUsername()
        +setMemberUsername(String memberUsername)
        +getTotalAmount()
        +setTotalAmount(BigDecimal totalAmount)
        +getPayAmount()
        +setPayAmount(BigDecimal payAmount)
        +getFreightAmount()
        +setFreightAmount(BigDecimal freightAmount)
        +getPromotionAmount()
        +setPromotionAmount(BigDecimal promotionAmount)
        +getIntegrationAmount()
        +setIntegrationAmount(BigDecimal integrationAmount)
        +getCouponAmount()
        +setCouponAmount(BigDecimal couponAmount)
        +getDiscountAmount()
        +setDiscountAmount(BigDecimal discountAmount)
        +getPayType()
        +setPayType(Integer payType)
        +getSourceType()
        +setSourceType(Integer sourceType)
        +getStatus()
        +setStatus(Integer status)
        +getOrderType()
        +setOrderType(Integer orderType)
        +getDeliveryCompany()
        +setDeliveryCompany(String deliveryCompany)
        +getDeliverySn()
        +setDeliverySn(String deliverySn)
        +getAutoConfirmDay()
        +setAutoConfirmDay(Integer autoConfirmDay)
        +getIntegration()
        +setIntegration(Integer integration)
        +getGrowth()
        +setGrowth(Integer growth)
        +getPromotionInfo()
        +setPromotionInfo(String promotionInfo)
        +getBillType()
        +setBillType(Integer billType)
        +getBillHeader()
        +setBillHeader(String billHeader)
        +getBillContent()
        +setBillContent(String billContent)
        +getBillReceiverPhone()
        +setBillReceiverPhone(String billReceiverPhone)
        +getBillReceiverEmail()
        +setBillReceiverEmail(String billReceiverEmail)
        +getReceiverName()
        +setReceiverName(String receiverName)
        +getReceiverPhone()
        +setReceiverPhone(String receiverPhone)
        +getReceiverPostCode()
        +setReceiverPostCode(String receiverPostCode)
        +getReceiverProvince()
        +setReceiverProvince(String receiverProvince)
        +getReceiverCity()
        +setReceiverCity(String receiverCity)
        +getReceiverRegion()
        +setReceiverRegion(String receiverRegion)
        +getReceiverDetailAddress()
        +setReceiverDetailAddress(String receiverDetailAddress)
        +getNote()
        +setNote(String note)
        +getConfirmStatus()
        +setConfirmStatus(Integer confirmStatus)
        +getDeleteStatus()
        +setDeleteStatus(Integer deleteStatus)
        +getUseIntegration()
        +setUseIntegration(Integer useIntegration)
        +getPaymentTime()
        +setPaymentTime(Date paymentTime)
        +getDeliveryTime()
        +setDeliveryTime(Date deliveryTime)
        +getReceiveTime()
        +setReceiveTime(Date receiveTime)
        +getCommentTime()
        +setCommentTime(Date commentTime)
        +getModifyTime()
        +setModifyTime(Date modifyTime)
    }
    class SmsCouponHistory {
        -Long id
        -Long couponId
        -Long memberId
        -String couponCode
        -String memberNickname
        -Integer getType
        -Date createTime
        -Integer useStatus
        -Date useTime
        -Long orderId
        -String orderSn
        +setUseStatus(Integer useStatus)
        +setUseTime(Date useTime)
    }
    class OmsCartItem {
        -Long id
        -Long productId
        -Long productSkuId
        -Long memberId
        -Integer quantity
        -BigDecimal price
        -String productPic
        -String productName
        -String productSubTitle
        -String productSkuCode
        -String memberNickname
        -Date createDate
        -Date modifyDate
        -Integer deleteStatus
        -Long productCategoryId
        -String productBrand
        -String productSn
        -String productAttr
        +getId()
        +getProductSkuId()
        +getProductName()
        +getQuantity()
        +getProductSn()
        +getProductBrand()
        +getProductPic()
        +getProductAttr()
        +getPrice()
        +getProductSkuCode()
        +getProductId()
        +getProductCategoryId()
    }
    class SmsCouponProductRelation {
        -Long id
        -Long couponId
        -Long productId
        -String productName
        -String productSn
        +getProductId()
    }
    class UmsMember {
        -Long id
        -Long memberLevelId
        -String username
        -String password
        -String nickname
        -String phone
        -Integer status
        -Date createTime
        -String icon
        -Integer gender
        -Date birthday
        -String city
        -String job
        -String personalizedSignature
        -Integer sourceType
        -Integer integration
        -Integer growth
        -Integer luckeyCount
        -Integer historyIntegration
        +getId()
        +getUsername()
        +getIntegration()
        +setIntegration(Integer integration)
    }
    class UmsMemberReceiveAddress {
        -Long id
        -Long memberId
        -String name
        -String phoneNumber
        -Integer defaultStatus
        -String postCode
        -String province
        -String city
        -String region
        -String detailAddress
        +getName()
        +getPhoneNumber()
        +getPostCode()
        +getProvince()
        +getCity()
        +getRegion()
        +getDetailAddress()
    }
    class OmsOrderItem {
        -Long id
        -Long orderId
        -String orderSn
        -Long productId
        -String productPic
        -String productName
        -String productBrand
        -String productSn
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
        +setPromotionAmount(BigDecimal promotionAmount)
        +getPromotionName()
        +setProductCategoryId(Long productCategoryId)
        +setPromotionName(String promotionName)
        +setProductAttr(String productAttr)
        +setGiftIntegration(Integer giftIntegration)
        +getGiftGrowth()
        +setProductSn(String productSn)
        +getProductPrice()
        +getOrderId()
        +setProductPrice(BigDecimal productPrice)
        +getCouponAmount()
        +setOrderId(Long orderId)
        +setIntegrationAmount(BigDecimal integrationAmount)
        +setProductId(Long productId)
        +setProductPic(String productPic)
        +setProductQuantity(Integer productQuantity)
        +setGiftGrowth(Integer giftGrowth)
        +setProductSkuId(Long productSkuId)
        +setRealAmount(BigDecimal realAmount)
        +getGiftIntegration()
        +setProductSkuCode(String productSkuCode)
        +setProductBrand(String productBrand)
        +setOrderSn(String orderSn)
        +getProductId()
        +getIntegrationAmount()
        +getProductQuantity()
        +setProductName(String productName)
        +setCouponAmount(BigDecimal couponAmount)
    }
    class OmsOrderSetting {
        -Long id
        -Integer flashOrderOvertime
        -Integer normalOrderOvertime
        -Integer confirmOvertime
        -Integer finishOvertime
        -Integer commentOvertime
        +getConfirmOvertime()
        +getNormalOrderOvertime()
    }
    class UmsIntegrationConsumeSetting {
        -Long id
        -Integer deductionPerAmount
        -Integer maxPercentPerOrder
        -Integer useUnit
        -Integer couponStatus
        +getCouponStatus()
        +getMaxPercentPerOrder()
        +getUseUnit()
    }
    class SmsCoupon {
        -Long id
        -Integer type
        -String name
        -Integer platform
        -Integer count
        -BigDecimal amount
        -Integer perLimit
        -BigDecimal minPoint
        -Date startTime
        -Date endTime
        -Integer useType
        -String note
        -Integer publishCount
        -Integer useCount
        -Integer receiveCount
        -Date enableTime
        -String code
        -Integer memberLevel
        +getUseType()
        +getId()
        +getAmount()
    }
    class PmsSkuStock {
        -Long id
        -Long productId
        -String skuCode
        -BigDecimal price
        -Integer stock
        -Integer lowStock
        -String pic
        -Integer sale
        -BigDecimal promotionPrice
        -Integer lockStock
        -String spData
        +setLockStock(Integer lockStock)
        +getLockStock()
    }
    class OmsOrderItemExample {
    }
    class OmsOrderSettingExample {
    }
    class CancelOrderSender {
        +sendMessage(Long orderId, long delayTimes)
    }
    class UmsMemberCouponService {
        <<interface>>
        +add(Long couponId)
        +listHistory(Integer useStatus)
        +listCart(List~CartPromotionItem~, Integer type)
        +listByProduct(Long productId)
        +list(Integer useStatus)
    }
    class OmsCartItemService {
        <<interface>>
        +add(OmsCartItem cartItem)
        +list(Long memberId)
        +listPromotion(Long memberId, List~Long~ cartIds)
        +updateQuantity(Long id, Long memberId, Integer quantity)
        +delete(Long memberId, List~Long~ ids)
        +getCartProduct(Long productId)
        +updateAttr(OmsCartItem cartItem)
        +clear(Long memberId)
    }
    class UmsMemberService {
        <<interface>>
        +getByUsername(String username)
        +getById(Long id)
        +register(String username, String password, String telephone, String authCode)
        +generateAuthCode(String telephone)
        +updatePassword(String telephone, String password, String authCode)
        +getCurrentMember()
        +updateIntegration(Long id,Integer integration)
        +loadUserByUsername(String username)
        +login(String username, String password)
        +refreshToken(String token)
    }
    class UmsMemberReceiveAddressService {
        <<interface>>
        +add(UmsMemberReceiveAddress address)
        +delete(Long id)
        +update(Long id, UmsMemberReceiveAddress address)
        +list()
        +getItem(Long id)
    }
    class PortalOrderDao {
        <<interface>>
        +getDetail(Long orderId)
        +updateSkuStock(List~OmsOrderItem~ orderItemList)
        +getTimeOutOrders(Integer minute)
        +updateOrderStatus(List~Long~ ids,Integer status)
        +releaseSkuStockLock(List~OmsOrderItem~ orderItemList)
        +lockStockBySkuId(Long productSkuId,Integer quantity)
        +reduceSkuStock(Long productSkuId,Integer quantity)
        +releaseStockBySkuId(Long productSkuId,Integer quantity)
    }
    class PortalOrderItemDao {
        <<interface>>
        +insertList(List~OmsOrderItem~ list)
    }
    class SmsCouponHistoryDetail {
    }
    AlipayController ..> AlipayService : uses
    AlipayController ..> CommonResult~String~ : returns
    AlipayServiceImpl <|.. AlipayService
    AlipayServiceImpl ..> OmsPortalOrderService : uses
    OmsPortalOrderServiceImpl <|.. OmsPortalOrderService
    OmsPortalOrderServiceImpl ..> CommonPage~OmsOrderDetail~ : uses
    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : uses
    OmsPortalOrderServiceImpl ..> OmsOrderDetail : uses
    OmsPortalOrderServiceImpl ..> OmsOrderExample : uses
    OmsPortalOrderServiceImpl ..> SmsCouponHistoryExample : uses
    OmsPortalOrderServiceImpl ..> OmsOrder : uses
    OmsPortalOrderServiceImpl ..> OmsOrderItem : uses
    OmsPortalOrderServiceImpl ..> OmsOrderItemExample : uses
    OmsPortalOrderServiceImpl ..> OmsOrderSettingExample : uses
    OmsPortalOrderServiceImpl ..> UmsMember : uses
    OmsPortalOrderServiceImpl ..> UmsMemberReceiveAddress : uses
    OmsPortalOrderServiceImpl ..> SmsCouponHistory : uses
    OmsPortalOrderServiceImpl ..> OmsCartItem : uses
    OmsPortalOrderServiceImpl ..> SmsCouponProductRelation : uses
    OmsPortalOrderServiceImpl ..> SmsCouponProductCategoryRelation : uses
    OmsPortalOrderServiceImpl ..> SmsCoupon : uses
    OmsPortalOrderServiceImpl ..> UmsIntegrationConsumeSetting : uses
    OmsPortalOrderServiceImpl ..> PmsSkuStock : uses
    OmsPortalOrderServiceImpl ..> Asserts : uses
    OmsPortalOrderServiceImpl ..> RedisService : uses
    OmsPortalOrderServiceImpl ..> SmsCouponHistoryMapper : uses
    OmsPortalOrderServiceImpl ..> OmsOrderItemMapper : uses
    OmsPortalOrderServiceImpl ..> UmsIntegrationConsumeSettingMapper : uses
    OmsPortalOrderServiceImpl ..> OmsOrderMapper : uses
    OmsPortalOrderServiceImpl ..> OmsOrderSettingMapper : uses
    OmsPortalOrderServiceImpl ..> PmsSkuStockMapper : uses
    OmsPortalOrderServiceImpl ..> CancelOrderSender : uses
    OmsPortalOrderServiceImpl ..> UmsMemberCouponService : uses
    OmsPortalOrderServiceImpl ..> OmsCartItemService : uses
    OmsPortalOrderServiceImpl ..> UmsMemberService : uses
    OmsPortalOrderServiceImpl ..> UmsMemberReceiveAddressService : uses
    OmsPortalOrderServiceImpl ..> PortalOrderDao : uses
    OmsPortalOrderServiceImpl ..> PortalOrderItemDao : uses
    OmsPortalOrderServiceImpl ..> SmsCouponHistoryDetail : returns
    OmsPortalOrderServiceImpl ..> CommonPage~OmsOrderDetail~ : returns
    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : returns
    OmsPortalOrderServiceImpl ..> OmsOrderDetail : returns
    OmsPortalOrderServiceImpl ..> OmsPortalOrderService : implements
    OmsPortalOrderServiceImpl ..> OmsOrderExample : uses
    OmsPortalOrderServiceImpl ..> SmsCouponHistoryExample : uses
    OmsPortalOrderServiceImpl ..> OmsOrder : uses
    OmsPortalOrderServiceImpl ..> OmsOrderItem : uses
    OmsPortalOrderServiceImpl ..> OmsOrderItemExample : uses
    OmsPortalOrderServiceImpl ..> OmsOrderSettingExample : uses
    OmsPortalOrderServiceImpl ..> OmsOrderDetail : uses
    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : uses
    OmsPortalOrderServiceImpl ..> SmsCoupon : uses
    OmsPortalOrderServiceImpl ..> PmsSkuStock : uses
    OmsPortalOrderServiceImpl ..> CancelOrderSender : uses
    OmsPortalOrderServiceImpl ..> UmsMemberCouponService : uses
    OmsPortalOrderServiceImpl ..> OmsCartItemService : uses
    OmsPortalOrderServiceImpl ..> UmsMemberService : uses
    OmsPortalOrderServiceImpl ..> UmsMemberReceiveAddressService : uses
    OmsPortalOrderServiceImpl ..> PortalOrderDao : uses
    OmsPortalOrderServiceImpl ..> PortalOrderItemDao : uses
    OmsPortalOrderServiceImpl ..> SmsCouponHistoryDetail : returns
    OmsPortalOrderServiceImpl ..> OmsOrderDetail : returns
    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : returns
    OmsPortalOrderServiceImpl ..> CommonPage~OmsOrderDetail~ : returns
    OmsPortalOrderServiceImpl ..> OmsPortalOrderService : implements
    OmsPortalOrderServiceImpl ..|> OmsPortalOrderService
    AlipayServiceImpl ..|> AlipayService

```