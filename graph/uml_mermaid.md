```mermaid
classDiagram
    class AlipayController {
        +void pay(AliPayParam aliPayParam, HttpServletResponse response)
        +void webPay(AliPayParam aliPayParam, HttpServletResponse response)
        +String notify(HttpServletRequest request)
        +CommonResult~String~ query(String outTradeNo, String tradeNo)
    }
    class CommonResult~T~ {
        -long code
        -String message
        -T data
        +getCode()
        +setCode(long)
        +getMessage()
        +setMessage(String)
        +getData()
        +setData(T)
        +success(T)
        +success(T, String)
        +failed(IErrorCode)
        +failed(IErrorCode, String)
        +failed(String)
        +failed()
        +validateFailed()
        +validateFailed(String)
        +unauthorized(T)
        +forbidden(T)
    }
    class AlipayService {
        <<interface>>
        +String pay(AliPayParam aliPayParam)
        +String notify(Map~String,String~ params)
        +String query(String outTradeNo, String tradeNo)
        +String webPay(AliPayParam aliPayParam)
    }
    class AlipayServiceImpl {
        +String pay(AliPayParam aliPayParam)
        +String notify(Map~String,String~ params)
        +String query(String outTradeNo, String tradeNo)
        +String webPay(AliPayParam aliPayParam)
    }
    class OmsPortalOrderService {
        <<interface>>
        +ConfirmOrderResult generateConfirmOrder(List~Long~ cartIds)
        +Map~String,Object~ generateOrder(OrderParam orderParam)
        +Integer paySuccess(Long orderId, Integer payType)
        +Integer cancelTimeOutOrder()
        +void cancelOrder(Long orderId)
        +void sendDelayMessageCancelOrder(Long orderId)
        +void confirmReceiveOrder(Long orderId)
        +CommonPage~OmsOrderDetail~ list(Integer status, Integer pageNum, Integer pageSize)
        +OmsOrderDetail detail(Long orderId)
        +void deleteOrder(Long orderId)
        +void paySuccessByOrderSn(String orderSn, Integer payType)
    }
    class CommonPage~T~ {
        -Integer pageNum
        -Integer pageSize
        -Integer totalPage
        -Long total
        -List~T~ list
        +getPageNum()
        +setPageNum(Integer)
        +getPageSize()
        +setPageSize(Integer)
        +getTotalPage()
        +setTotalPage(Integer)
        +getList()
        +setList(List~T~)
        +getTotal()
        +setTotal(Long)
        +restPage(List~T~)
        +restPage(Page~T~)
    }
    class ConfirmOrderResult {
        +void setCartPromotionItemList(List~CartPromotionItem~)
        +void setMemberReceiveAddressList(List~UmsMemberReceiveAddress~)
        +void setCouponHistoryDetailList(List~SmsCouponHistoryDetail~)
        +void setMemberIntegration(Integer)
        +void setIntegrationConsumeSetting(UmsIntegrationConsumeSetting)
        +void setCalcAmount(CalcAmount)
    }
    class OmsOrderDetail {
        +void setOrderItemList(List~OmsOrderItem~)
    }
    class OmsPortalOrderServiceImpl {
        +ConfirmOrderResult generateConfirmOrder(List~Long~ cartIds)
        +Map~String,Object~ generateOrder(OrderParam orderParam)
        +Integer paySuccess(Long orderId, Integer payType)
        +Integer cancelTimeOutOrder()
        +void cancelOrder(Long orderId)
        +void sendDelayMessageCancelOrder(Long orderId)
        +void confirmReceiveOrder(Long orderId)
        +CommonPage~OmsOrderDetail~ list(Integer status, Integer pageNum, Integer pageSize)
        +OmsOrderDetail detail(Long orderId)
        +void deleteOrder(Long orderId)
        +void paySuccessByOrderSn(String orderSn, Integer payType)
        +SmsCouponHistoryDetail getUseCoupon(List~CartPromotionItem~, Long couponId)
    }
    class Asserts {
        +void fail(String message)
        +void fail(IErrorCode errorCode)
    }
    class RedisService {
        <<interface>>
        +void set(String,Object,long)
        +void set(String,Object)
        +Object get(String)
        +Boolean del(String)
        +Long del(List~String~)
        +Boolean expire(String,long)
        +Long getExpire(String)
        +Boolean hasKey(String)
        +Long incr(String,long)
        +Long decr(String,long)
        +Object hGet(String,String)
        +Boolean hSet(String,String,Object,long)
        +void hSet(String,String,Object)
        +Map~Object,Object~ hGetAll(String)
        +Boolean hSetAll(String,Map~String,Object~,long)
        +void hSetAll(String,Map~String,?~)
        +void hDel(String,Object...)
        +Boolean hHasKey(String,String)
        +Long hIncr(String,String,Long)
        +Long hDecr(String,String,Long)
        +Set~Object~ sMembers(String)
        +Long sAdd(String,Object...)
        +Long sAdd(String,long,Object...)
        +Boolean sIsMember(String,Object)
        +Long sSize(String)
        +Long sRemove(String,Object...)
        +List~Object~ lRange(String,long,long)
        +Long lSize(String)
        +Object lIndex(String,long)
        +Long lPush(String,Object)
        +Long lPush(String,Object,long)
        +Long lPushAll(String,Object...)
        +Long lPushAll(String,Long,Object...)
        +Long lRemove(String,long,Object)
    }
    class SmsCouponHistoryMapper {
        <<interface>>
        +long countByExample(SmsCouponHistoryExample)
        +int deleteByExample(SmsCouponHistoryExample)
        +int deleteByPrimaryKey(Long)
        +int insert(SmsCouponHistory)
        +int insertSelective(SmsCouponHistory)
        +List~SmsCouponHistory~ selectByExample(SmsCouponHistoryExample)
        +SmsCouponHistory selectByPrimaryKey(Long)
        +int updateByExampleSelective(SmsCouponHistory,SmsCouponHistoryExample)
        +int updateByExample(SmsCouponHistory,SmsCouponHistoryExample)
        +int updateByPrimaryKeySelective(SmsCouponHistory)
        +int updateByPrimaryKey(SmsCouponHistory)
    }
    class OmsOrderItemMapper {
        <<interface>>
        +long countByExample(OmsOrderItemExample)
        +int deleteByExample(OmsOrderItemExample)
        +int deleteByPrimaryKey(Long)
        +int insert(OmsOrderItem)
        +int insertSelective(OmsOrderItem)
        +List~OmsOrderItem~ selectByExample(OmsOrderItemExample)
        +OmsOrderItem selectByPrimaryKey(Long)
        +int updateByExampleSelective(OmsOrderItem,OmsOrderItemExample)
        +int updateByExample(OmsOrderItem,OmsOrderItemExample)
        +int updateByPrimaryKeySelective(OmsOrderItem)
        +int updateByPrimaryKey(OmsOrderItem)
    }
    class UmsIntegrationConsumeSettingMapper {
        <<interface>>
        +long countByExample(UmsIntegrationConsumeSettingExample)
        +int deleteByExample(UmsIntegrationConsumeSettingExample)
        +int deleteByPrimaryKey(Long)
        +int insert(UmsIntegrationConsumeSetting)
        +int insertSelective(UmsIntegrationConsumeSetting)
        +List~UmsIntegrationConsumeSetting~ selectByExample(UmsIntegrationConsumeSettingExample)
        +UmsIntegrationConsumeSetting selectByPrimaryKey(Long)
        +int updateByExampleSelective(UmsIntegrationConsumeSetting,UmsIntegrationConsumeSettingExample)
        +int updateByExample(UmsIntegrationConsumeSetting,UmsIntegrationConsumeSettingExample)
        +int updateByPrimaryKeySelective(UmsIntegrationConsumeSetting)
        +int updateByPrimaryKey(UmsIntegrationConsumeSetting)
    }
    class OmsOrderMapper {
        <<interface>>
        +long countByExample(OmsOrderExample)
        +int deleteByExample(OmsOrderExample)
        +int deleteByPrimaryKey(Long)
        +int insert(OmsOrder)
        +int insertSelective(OmsOrder)
        +List~OmsOrder~ selectByExample(OmsOrderExample)
        +OmsOrder selectByPrimaryKey(Long)
        +int updateByExampleSelective(OmsOrder,OmsOrderExample)
        +int updateByExample(OmsOrder,OmsOrderExample)
        +int updateByPrimaryKeySelective(OmsOrder)
        +int updateByPrimaryKey(OmsOrder)
    }
    class OmsOrderSettingMapper {
        <<interface>>
        +long countByExample(OmsOrderSettingExample)
        +int deleteByExample(OmsOrderSettingExample)
        +int deleteByPrimaryKey(Long)
        +int insert(OmsOrderSetting)
        +int insertSelective(OmsOrderSetting)
        +List~OmsOrderSetting~ selectByExample(OmsOrderSettingExample)
        +OmsOrderSetting selectByPrimaryKey(Long)
        +int updateByExampleSelective(OmsOrderSetting,OmsOrderSettingExample)
        +int updateByExample(OmsOrderSetting,OmsOrderSettingExample)
        +int updateByPrimaryKeySelective(OmsOrderSetting)
        +int updateByPrimaryKey(OmsOrderSetting)
    }
    class PmsSkuStockMapper {
        <<interface>>
        +long countByExample(PmsSkuStockExample)
        +int deleteByExample(PmsSkuStockExample)
        +int deleteByPrimaryKey(Long)
        +int insert(PmsSkuStock)
        +int insertSelective(PmsSkuStock)
        +List~PmsSkuStock~ selectByExample(PmsSkuStockExample)
        +PmsSkuStock selectByPrimaryKey(Long)
        +int updateByExampleSelective(PmsSkuStock,PmsSkuStockExample)
        +int updateByExample(PmsSkuStock,PmsSkuStockExample)
        +int updateByPrimaryKeySelective(PmsSkuStock)
        +int updateByPrimaryKey(PmsSkuStock)
    }
    class OmsOrderExample {
        +void setOrderByClause(String)
        +String getOrderByClause()
        +void setDistinct(boolean)
        +boolean isDistinct()
        +List~Criteria~ getOredCriteria()
        +void or(Criteria)
        +Criteria or()
        +Criteria createCriteria()
        +void clear()
    }
    class SmsCouponProductCategoryRelation {
        -Long id
        -Long couponId
        -Long productCategoryId
        -String productCategoryName
        -String parentCategoryName
        +Long getProductCategoryId()
    }
    class SmsCouponHistoryExample {
        +void setOrderByClause(String)
        +String getOrderByClause()
        +void setDistinct(boolean)
        +boolean isDistinct()
        +List~Criteria~ getOredCriteria()
        +void or(Criteria)
        +Criteria or()
        +Criteria createCriteria()
        +void clear()
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
        +Long getId()
        +void setId(Long)
        +Long getMemberId()
        +void setMemberId(Long)
        +Long getCouponId()
        +void setCouponId(Long)
        +String getOrderSn()
        +void setOrderSn(String)
        +Date getCreateTime()
        +void setCreateTime(Date)
        +String getMemberUsername()
        +void setMemberUsername(String)
        +BigDecimal getTotalAmount()
        +void setTotalAmount(BigDecimal)
        +BigDecimal getPayAmount()
        +void setPayAmount(BigDecimal)
        +BigDecimal getFreightAmount()
        +void setFreightAmount(BigDecimal)
        +BigDecimal getPromotionAmount()
        +void setPromotionAmount(BigDecimal)
        +BigDecimal getIntegrationAmount()
        +void setIntegrationAmount(BigDecimal)
        +BigDecimal getCouponAmount()
        +void setCouponAmount(BigDecimal)
        +BigDecimal getDiscountAmount()
        +void setDiscountAmount(BigDecimal)
        +Integer getPayType()
        +void setPayType(Integer)
        +Integer getSourceType()
        +void setSourceType(Integer)
        +Integer getStatus()
        +void setStatus(Integer)
        +Integer getOrderType()
        +void setOrderType(Integer)
        +String getDeliveryCompany()
        +void setDeliveryCompany(String)
        +String getDeliverySn()
        +void setDeliverySn(String)
        +Integer getAutoConfirmDay()
        +void setAutoConfirmDay(Integer)
        +Integer getIntegration()
        +void setIntegration(Integer)
        +Integer getGrowth()
        +void setGrowth(Integer)
        +String getPromotionInfo()
        +void setPromotionInfo(String)
        +Integer getBillType()
        +void setBillType(Integer)
        +String getBillHeader()
        +void setBillHeader(String)
        +String getBillContent()
        +void setBillContent(String)
        +String getBillReceiverPhone()
        +void setBillReceiverPhone(String)
        +String getBillReceiverEmail()
        +void setBillReceiverEmail(String)
        +String getReceiverName()
        +void setReceiverName(String)
        +String getReceiverPhone()
        +void setReceiverPhone(String)
        +String getReceiverPostCode()
        +void setReceiverPostCode(String)
        +String getReceiverProvince()
        +void setReceiverProvince(String)
        +String getReceiverCity()
        +void setReceiverCity(String)
        +String getReceiverRegion()
        +void setReceiverRegion(String)
        +String getReceiverDetailAddress()
        +void setReceiverDetailAddress(String)
        +String getNote()
        +void setNote(String)
        +Integer getConfirmStatus()
        +void setConfirmStatus(Integer)
        +Integer getDeleteStatus()
        +void setDeleteStatus(Integer)
        +Integer getUseIntegration()
        +void setUseIntegration(Integer)
        +Date getPaymentTime()
        +void setPaymentTime(Date)
        +Date getDeliveryTime()
        +void setDeliveryTime(Date)
        +Date getReceiveTime()
        +void setReceiveTime(Date)
        +Date getCommentTime()
        +void setCommentTime(Date)
        +Date getModifyTime()
        +void setModifyTime(Date)
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
        +void setUseStatus(Integer)
        +void setUseTime(Date)
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
        +Long getId()
        +Long getProductSkuId()
        +String getProductName()
        +Integer getQuantity()
        +String getProductSn()
        +String getProductBrand()
        +String getProductPic()
        +String getProductAttr()
        +BigDecimal getPrice()
        +String getProductSkuCode()
        +Long getProductId()
        +Long getProductCategoryId()
    }
    class SmsCouponProductRelation {
        -Long id
        -Long couponId
        -Long productId
        -String productName
        -String productSn
        +Long getProductId()
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
        +Long getId()
        +String getUsername()
        +Integer getIntegration()
        +void setIntegration(Integer)
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
        +String getCity()
        +String getPostCode()
        +String getPhoneNumber()
        +String getName()
        +String getProvince()
        +String getRegion()
        +String getDetailAddress()
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
        +void setPromotionAmount(BigDecimal)
        +String getPromotionName()
        +void setProductCategoryId(Long)
        +void setPromotionName(String)
        +void setProductAttr(String)
        +void setGiftIntegration(Integer)
        +Integer getGiftGrowth()
        +void setProductSn(String)
        +BigDecimal getProductPrice()
        +void setProductPrice(BigDecimal)
        +BigDecimal getCouponAmount()
        +void setOrderId(Long)
        +void setIntegrationAmount(BigDecimal)
        +void setProductId(Long)
        +void setProductPic(String)
        +void setProductQuantity(Integer)
        +void setGiftGrowth(Integer)
        +void setProductSkuId(Long)
        +void setRealAmount(BigDecimal)
        +Integer getGiftIntegration()
        +void setProductSkuCode(String)
        +void setProductBrand(String)
        +void setOrderSn(String)
        +void setProductName(String)
        +void setCouponAmount(BigDecimal)
        +Long getProductCategoryId()
        +Long getProductSkuId()
        +Long getProductId()
        +BigDecimal getIntegrationAmount()
        +Integer getProductQuantity()
    }
    class OmsOrderSetting {
        -Long id
        -Integer flashOrderOvertime
        -Integer normalOrderOvertime
        -Integer confirmOvertime
        -Integer finishOvertime
        -Integer commentOvertime
        +Integer getConfirmOvertime()
        +Integer getNormalOrderOvertime()
    }
    class UmsIntegrationConsumeSetting {
        -Long id
        -Integer deductionPerAmount
        -Integer maxPercentPerOrder
        -Integer useUnit
        -Integer couponStatus
        +Integer getCouponStatus()
        +Integer getMaxPercentPerOrder()
        +Integer getUseUnit()
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
        +Integer getUseType()
        +Long getId()
        +BigDecimal getAmount()
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
        +void setLockStock(Integer)
        +Integer getLockStock()
    }
    class OmsOrderItemExample {
        +void setOrderByClause(String)
        +String getOrderByClause()
        +void setDistinct(boolean)
        +boolean isDistinct()
        +List~Criteria~ getOredCriteria()
        +void or(Criteria)
        +Criteria or()
        +Criteria createCriteria()
        +void clear()
    }
    class OmsOrderSettingExample {
        +void setOrderByClause(String)
        +String getOrderByClause()
        +void setDistinct(boolean)
        +boolean isDistinct()
        +List~Criteria~ getOredCriteria()
        +void or(Criteria)
        +Criteria or()
        +Criteria createCriteria()
        +void clear()
    }
    class CancelOrderSender {
        +void sendMessage(Long orderId, long delayTimes)
    }
    class UmsMemberCouponService {
        <<interface>>
        +void add(Long couponId)
        +List~SmsCouponHistory~ listHistory(Integer useStatus)
        +List~SmsCouponHistoryDetail~ listCart(List~CartPromotionItem~, Integer)
        +List~SmsCoupon~ listByProduct(Long)
        +List~SmsCoupon~ list(Integer useStatus)
    }
    class OmsCartItemService {
        <<interface>>
        +int add(OmsCartItem)
        +List~OmsCartItem~ list(Long memberId)
        +List~CartPromotionItem~ listPromotion(Long,List~Long~)
        +int updateQuantity(Long,Long,Integer)
        +int delete(Long,List~Long~)
        +CartProduct getCartProduct(Long)
        +int updateAttr(OmsCartItem)
        +int clear(Long)
    }
    class UmsMemberService {
        <<interface>>
        +UmsMember getByUsername(String)
        +UmsMember getById(Long)
        +void register(String,String,String,String)
        +String generateAuthCode(String)
        +void updatePassword(String,String,String)
        +UmsMember getCurrentMember()
        +void updateIntegration(Long,Integer)
        +UserDetails loadUserByUsername(String)
        +String login(String,String)
        +String refreshToken(String)
    }
    class UmsMemberReceiveAddressService {
        <<interface>>
        +int add(UmsMemberReceiveAddress)
        +int delete(Long)
        +int update(Long,UmsMemberReceiveAddress)
        +List~UmsMemberReceiveAddress~ list()
        +UmsMemberReceiveAddress getItem(Long)
    }
    class PortalOrderDao {
        <<interface>>
        +OmsOrderDetail getDetail(Long)
        +int updateSkuStock(List~OmsOrderItem~)
        +List~OmsOrderDetail~ getTimeOutOrders(Integer)
        +int updateOrderStatus(List~Long~,Integer)
        +int releaseSkuStockLock(List~OmsOrderItem~)
        +int lockStockBySkuId(Long,Integer)
        +int reduceSkuStock(Long,Integer)
        +int releaseStockBySkuId(Long,Integer)
    }
    class PortalOrderItemDao {
        <<interface>>
        +int insertList(List~OmsOrderItem~)
    }
    class SmsCouponHistoryDetail {
    }
    AlipayController --> AlipayService
    AlipayController --> CommonResult~String~
    AlipayServiceImpl <|-- AlipayService
    AlipayServiceImpl --> OmsPortalOrderService
    OmsPortalOrderServiceImpl <|-- OmsPortalOrderService
    OmsPortalOrderServiceImpl --> Asserts
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> RedisService
    OmsPortalOrderServiceImpl --> SmsCouponHistoryMapper
    OmsPortalOrderServiceImpl --> OmsOrderItemMapper
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSettingMapper
    OmsPortalOrderServiceImpl --> OmsOrderMapper
    OmsPortalOrderServiceImpl --> OmsOrderSettingMapper
    OmsPortalOrderServiceImpl --> PmsSkuStockMapper
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponProductCategoryRelation
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> SmsCouponHistory
    OmsPortalOrderServiceImpl --> OmsCartItem
    OmsPortalOrderServiceImpl --> SmsCouponProductRelation
    OmsPortalOrderServiceImpl --> UmsMember
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddress
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderSetting
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> SmsCoupon
    OmsPortalOrderServiceImpl --> PmsSkuStock
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> CancelOrderSender
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting
    OmsPortalOrderServiceImpl --> UmsMemberCouponService
    OmsPortalOrderServiceImpl --> OmsCartItemService
    OmsPortalOrderServiceImpl --> UmsMemberService
    OmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService
    OmsPortalOrderServiceImpl --> PortalOrderDao
    OmsPortalOrderServiceImpl --> PortalOrderItemDao
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    OmsPortalOrderServiceImpl --> OmsOrderExample
    OmsPortalOrderServiceImpl --> SmsCouponHistoryExample
    OmsPortalOrderServiceImpl --> OmsOrder
    OmsPortalOrderServiceImpl --> OmsOrderItem
    OmsPortalOrderServiceImpl --> OmsOrderItemExample
    OmsPortalOrderServiceImpl --> OmsOrderSettingExample
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> SmsCouponHistoryDetail
    OmsPortalOrderServiceImpl --> OmsOrderDetail
    OmsPortalOrderServiceImpl --> ConfirmOrderResult
    OmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~
    AlipayServiceImpl <|-- AlipayService
    OmsPortalOrderServiceImpl <|-- OmsPortalOrderService

```
- 该图为**代码类/接口之间的关系UML图**，重点聚焦在订单与支付相关的核心类，展示了它们之间的实现关系、调用关系以及主要方法。

- **AlipayController**
  - 作为支付宝支付相关的Web控制器，负责处理支付、回调、订单查询等HTTP请求。
  - 依赖于`AlipayService`，通过注入调用其`pay`、`webPay`、`notify`、`query`等方法实现功能。
  - 返回结果通过`CommonResult`统一封装。

- **AlipayService & AlipayServiceImpl**
  - `AlipayService`为接口，定义了支付宝支付、回调处理、交易查询等方法。
  - `AlipayServiceImpl`实现该接口，包含实际的支付请求组装、回调参数校验与订单同步、支付结果查询等核心逻辑。
  - `AlipayServiceImpl`依赖于`OmsPortalOrderService`，如在支付回调/查询时会回调订单服务的`paySuccessByOrderSn`方法，完成支付后订单状态的更新。

- **OmsPortalOrderService & OmsPortalOrderServiceImpl**
  - `OmsPortalOrderService`为订单领域的接口，定义了生成确认单、下单、支付成功回调、超时取消、收货、订单详情、删除等电商订单全流程相关的方法。
  - `OmsPortalOrderServiceImpl`为核心实现，业务逻辑复杂，涉及订单生成、校验、库存锁定、优惠券/积分处理、状态流转、发消息等。
  - 实现过程中与大量底层服务/DAO进行交互，包括：
    - 会员、购物车、收货地址、优惠券、积分等服务（如`UmsMemberService`、`OmsCartItemService`等）。
    - 订单、订单项、库存、优惠券历史等数据库表对应的Mapper/DAO。
    - Redis缓存、延迟消息（订单超时取消）等基础设施服务。
    - 订单金额、优惠、实付等复杂业务计算。

- **类/接口之间的关系**
  - `AlipayController` --> `AlipayService`
  - `AlipayController` --> `CommonResult`
  - `AlipayServiceImpl` 实现 `AlipayService`
  - `AlipayServiceImpl` --> `OmsPortalOrderService`
  - `OmsPortalOrderServiceImpl` 实现 `OmsPortalOrderService`
  - `OmsPortalOrderServiceImpl` 依赖诸多服务和数据访问对象，如`Asserts`、`CommonPage`、`RedisService`、`SmsCouponHistoryMapper`、`OmsOrderItemMapper`、`UmsIntegrationConsumeSettingMapper`、`OmsOrderMapper`、`OmsOrderSettingMapper`、`PmsSkuStockMapper`、`PortalOrderDao`、`PortalOrderItemDao`等。
  - `OmsPortalOrderServiceImpl`还涉及订单相关的业务对象（如`OmsOrder`, `OmsOrderDetail`, `OmsOrderItem`, `ConfirmOrderResult`等），进行订单全生命周期管理。
  - 各种Mapper/DAO类负责与数据库表的数据CRUD操作。

- **主要业务流程抽象**
  - 用户下单、支付、回调、订单状态变更等流程由控制器（Controller）发起，调用Service层接口，具体实现由Impl类承载。
  - 订单支付成功与否的最终状态更新依赖于支付回调（如支付宝notify）和支付结果查询，由支付服务和订单服务共同协作完成。
  - 订单相关数据操作（如库存锁定、优惠券使用、积分扣减、订单明细保存等）由业务实现类协调多种底层服务/DAO完成，确保电商业务完整闭环。

- **总结**
  - 本图展示了电商支付与订单管理领域的核心类、接口，以及它们之间的调用、实现、依赖关系，反映了分层架构下各业务模块清晰的职责划分和协作机制。

