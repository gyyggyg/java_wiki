{
    "mermaid": "classDiagram\n    class AlipayController {\n        +pay(AliPayParam aliPayParam, HttpServletResponse response)\n        +webPay(AliPayParam aliPayParam, HttpServletResponse response)\n        +notify(HttpServletRequest request)\n        +query(String outTradeNo, String tradeNo)\n        -AlipayConfig alipayConfig\n        -AlipayService alipayService\n    }\n    class CommonResult~T~ {\n        -long code\n        -String message\n        -T data\n        +getCode()\n        +setCode(long code)\n        +getMessage()\n        +setMessage(String message)\n        +getData()\n        +setData(T data)\n        +success(T data)\n        +success(T data, String message)\n        +failed(IErrorCode errorCode)\n        +failed(IErrorCode errorCode, String message)\n        +failed(String message)\n        +failed()\n        +validateFailed()\n        +validateFailed(String message)\n        +unauthorized(T data)\n        +forbidden(T data)\n    }\n    class AlipayService {\n        <<interface>>\n        +pay(AliPayParam aliPayParam)\n        +notify(Map~String,String~ params)\n        +query(String outTradeNo, String tradeNo)\n        +webPay(AliPayParam aliPayParam)\n    }\n    class AlipayServiceImpl {\n        +pay(AliPayParam aliPayParam)\n        +notify(Map~String,String~ params)\n        +query(String outTradeNo, String tradeNo)\n        +webPay(AliPayParam aliPayParam)\n        -AlipayConfig alipayConfig\n        -AlipayClient alipayClient\n        -OmsOrderMapper orderMapper\n        -OmsPortalOrderService portalOrderService\n    }\n    class OmsPortalOrderService {\n        <<interface>>\n        +generateConfirmOrder(List~Long~ cartIds)\n        +generateOrder(OrderParam orderParam)\n        +paySuccess(Long orderId, Integer payType)\n        +cancelTimeOutOrder()\n        +cancelOrder(Long orderId)\n        +sendDelayMessageCancelOrder(Long orderId)\n        +confirmReceiveOrder(Long orderId)\n        +list(Integer status, Integer pageNum, Integer pageSize)\n        +detail(Long orderId)\n        +deleteOrder(Long orderId)\n        +paySuccessByOrderSn(String orderSn, Integer payType)\n    }\n    class CommonPage~T~ {\n        -Integer pageNum\n        -Integer pageSize\n        -Integer totalPage\n        -Long total\n        -List~T~ list\n        +getPageNum()\n        +setPageNum(Integer pageNum)\n        +getPageSize()\n        +setPageSize(Integer pageSize)\n        +getTotalPage()\n        +setTotalPage(Integer totalPage)\n        +getList()\n        +setList(List~T~ list)\n        +getTotal()\n        +setTotal(Long total)\n        +restPage(List~T~ list)\n        +restPage(Page~T~ pageInfo)\n    }\n    class ConfirmOrderResult {\n    }\n    class OmsOrderDetail {\n    }\n    class OmsPortalOrderServiceImpl {\n        +generateConfirmOrder(List~Long~ cartIds)\n        +generateOrder(OrderParam orderParam)\n        +paySuccess(Long orderId, Integer payType)\n        +cancelTimeOutOrder()\n        +cancelOrder(Long orderId)\n        +sendDelayMessageCancelOrder(Long orderId)\n        +confirmReceiveOrder(Long orderId)\n        +list(Integer status, Integer pageNum, Integer pageSize)\n        +detail(Long orderId)\n        +deleteOrder(Long orderId)\n        +paySuccessByOrderSn(String orderSn, Integer payType)\n        -UmsMemberService memberService\n        -OmsCartItemService cartItemService\n        -UmsMemberReceiveAddressService memberReceiveAddressService\n        -UmsMemberCouponService memberCouponService\n        -UmsIntegrationConsumeSettingMapper integrationConsumeSettingMapper\n        -PmsSkuStockMapper skuStockMapper\n        -SmsCouponHistoryDao couponHistoryDao\n        -OmsOrderMapper orderMapper\n        -PortalOrderItemDao orderItemDao\n        -SmsCouponHistoryMapper couponHistoryMapper\n        -RedisService redisService\n        -String REDIS_KEY_ORDER_ID\n        -String REDIS_DATABASE\n        -PortalOrderDao portalOrderDao\n        -OmsOrderSettingMapper orderSettingMapper\n        -OmsOrderItemMapper orderItemMapper\n        -CancelOrderSender cancelOrderSender\n    }\n    class Asserts {\n        +fail(String message)\n        +fail(IErrorCode errorCode)\n    }\n    class RedisService {\n        <<interface>>\n        +set(String key, Object value, long time)\n        +set(String key, Object value)\n        +get(String key)\n        +del(String key)\n        +del(List~String~ keys)\n        +expire(String key, long time)\n        +getExpire(String key)\n        +hasKey(String key)\n        +incr(String key, long delta)\n        +decr(String key, long delta)\n        +hGet(String key, String hashKey)\n        +hSet(String key, String hashKey, Object value, long time)\n        +hSet(String key, String hashKey, Object value)\n        +hGetAll(String key)\n        +hSetAll(String key, Map~String,Object~ map, long time)\n        +hSetAll(String key, Map~String,?~ map)\n        +hDel(String key, Object... hashKey)\n        +hHasKey(String key, String hashKey)\n        +hIncr(String key, String hashKey, Long delta)\n        +hDecr(String key, String hashKey, Long delta)\n        +sMembers(String key)\n        +sAdd(String key, Object... values)\n        +sAdd(String key, long time, Object... values)\n        +sIsMember(String key, Object value)\n        +sSize(String key)\n        +sRemove(String key, Object... values)\n        +lRange(String key, long start, long end)\n        +lSize(String key)\n        +lIndex(String key, long index)\n        +lPush(String key, Object value)\n        +lPush(String key, Object value, long time)\n        +lPushAll(String key, Object... values)\n        +lPushAll(String key, Long time, Object... values)\n        +lRemove(String key, long count, Object value)\n    }\n    class SmsCouponHistoryMapper {\n        <<interface>>\n        +countByExample(SmsCouponHistoryExample example)\n        +deleteByExample(SmsCouponHistoryExample example)\n        +deleteByPrimaryKey(Long id)\n        +insert(SmsCouponHistory record)\n        +insertSelective(SmsCouponHistory record)\n        +selectByExample(SmsCouponHistoryExample example)\n        +selectByPrimaryKey(Long id)\n        +updateByExampleSelective(SmsCouponHistory record, SmsCouponHistoryExample example)\n        +updateByExample(SmsCouponHistory record, SmsCouponHistoryExample example)\n        +updateByPrimaryKeySelective(SmsCouponHistory record)\n        +updateByPrimaryKey(SmsCouponHistory record)\n    }\n    class OmsOrderItemMapper {\n        <<interface>>\n        +countByExample(OmsOrderItemExample example)\n        +deleteByExample(OmsOrderItemExample example)\n        +deleteByPrimaryKey(Long id)\n        +insert(OmsOrderItem record)\n        +insertSelective(OmsOrderItem record)\n        +selectByExample(OmsOrderItemExample example)\n        +selectByPrimaryKey(Long id)\n        +updateByExampleSelective(OmsOrderItem record, OmsOrderItemExample example)\n        +updateByExample(OmsOrderItem record, OmsOrderItemExample example)\n        +updateByPrimaryKeySelective(OmsOrderItem record)\n        +updateByPrimaryKey(OmsOrderItem record)\n    }\n    class UmsIntegrationConsumeSettingMapper {\n        <<interface>>\n        +countByExample(UmsIntegrationConsumeSettingExample example)\n        +deleteByExample(UmsIntegrationConsumeSettingExample example)\n        +deleteByPrimaryKey(Long id)\n        +insert(UmsIntegrationConsumeSetting record)\n        +insertSelective(UmsIntegrationConsumeSetting record)\n        +selectByExample(UmsIntegrationConsumeSettingExample example)\n        +selectByPrimaryKey(Long id)\n        +updateByExampleSelective(UmsIntegrationConsumeSetting record, UmsIntegrationConsumeSettingExample example)\n        +updateByExample(UmsIntegrationConsumeSetting record, UmsIntegrationConsumeSettingExample example)\n        +updateByPrimaryKeySelective(UmsIntegrationConsumeSetting record)\n        +updateByPrimaryKey(UmsIntegrationConsumeSetting record)\n    }\n    class OmsOrderMapper {\n        <<interface>>\n        +countByExample(OmsOrderExample example)\n        +deleteByExample(OmsOrderExample example)\n        +deleteByPrimaryKey(Long id)\n        +insert(OmsOrder record)\n        +insertSelective(OmsOrder record)\n        +selectByExample(OmsOrderExample example)\n        +selectByPrimaryKey(Long id)\n        +updateByExampleSelective(OmsOrder record, OmsOrderExample example)\n        +updateByExample(OmsOrder record, OmsOrderExample example)\n        +updateByPrimaryKeySelective(OmsOrder record)\n        +updateByPrimaryKey(OmsOrder record)\n    }\n    class OmsOrderSettingMapper {\n        <<interface>>\n        +countByExample(OmsOrderSettingExample example)\n        +deleteByExample(OmsOrderSettingExample example)\n        +deleteByPrimaryKey(Long id)\n        +insert(OmsOrderSetting record)\n        +insertSelective(OmsOrderSetting record)\n        +selectByExample(OmsOrderSettingExample example)\n        +selectByPrimaryKey(Long id)\n        +updateByExampleSelective(OmsOrderSetting record, OmsOrderSettingExample example)\n        +updateByExample(OmsOrderSetting record, OmsOrderSettingExample example)\n        +updateByPrimaryKeySelective(OmsOrderSetting record)\n        +updateByPrimaryKey(OmsOrderSetting record)\n    }\n    class PmsSkuStockMapper {\n        <<interface>>\n        +countByExample(PmsSkuStockExample example)\n        +deleteByExample(PmsSkuStockExample example)\n        +deleteByPrimaryKey(Long id)\n        +insert(PmsSkuStock record)\n        +insertSelective(PmsSkuStock record)\n        +selectByExample(PmsSkuStockExample example)\n        +selectByPrimaryKey(Long id)\n        +updateByExampleSelective(PmsSkuStock record, PmsSkuStockExample example)\n        +updateByExample(PmsSkuStock record, PmsSkuStockExample example)\n        +updateByPrimaryKeySelective(PmsSkuStock record)\n        +updateByPrimaryKey(PmsSkuStock record)\n    }\n    class OmsOrderExample {\n    }\n    class SmsCouponProductCategoryRelation {\n        -Long id\n        -Long couponId\n        -Long productCategoryId\n        -String productCategoryName\n        -String parentCategoryName\n        +getProductCategoryId()\n    }\n    class SmsCouponHistoryExample {\n    }\n    class OmsOrder {\n        -Long id\n        -Long memberId\n        -Long couponId\n        -String orderSn\n        -Date createTime\n        -String memberUsername\n        -BigDecimal totalAmount\n        -BigDecimal payAmount\n        -BigDecimal freightAmount\n        -BigDecimal promotionAmount\n        -BigDecimal integrationAmount\n        -BigDecimal couponAmount\n        -BigDecimal discountAmount\n        -Integer payType\n        -Integer sourceType\n        -Integer status\n        -Integer orderType\n        -String deliveryCompany\n        -String deliverySn\n        -Integer autoConfirmDay\n        -Integer integration\n        -Integer growth\n        -String promotionInfo\n        -Integer billType\n        -String billHeader\n        -String billContent\n        -String billReceiverPhone\n        -String billReceiverEmail\n        -String receiverName\n        -String receiverPhone\n        -String receiverPostCode\n        -String receiverProvince\n        -String receiverCity\n        -String receiverRegion\n        -String receiverDetailAddress\n        -String note\n        -Integer confirmStatus\n        -Integer deleteStatus\n        -Integer useIntegration\n        -Date paymentTime\n        -Date deliveryTime\n        -Date receiveTime\n        -Date commentTime\n        -Date modifyTime\n        +getId()\n        +setId(Long id)\n        +getMemberId()\n        +setMemberId(Long memberId)\n        +getCouponId()\n        +setCouponId(Long couponId)\n        +getOrderSn()\n        +setOrderSn(String orderSn)\n        +getCreateTime()\n        +setCreateTime(Date createTime)\n        +getMemberUsername()\n        +setMemberUsername(String memberUsername)\n        +getTotalAmount()\n        +setTotalAmount(BigDecimal totalAmount)\n        +getPayAmount()\n        +setPayAmount(BigDecimal payAmount)\n        +getFreightAmount()\n        +setFreightAmount(BigDecimal freightAmount)\n        +getPromotionAmount()\n        +setPromotionAmount(BigDecimal promotionAmount)\n        +getIntegrationAmount()\n        +setIntegrationAmount(BigDecimal integrationAmount)\n        +getCouponAmount()\n        +setCouponAmount(BigDecimal couponAmount)\n        +getDiscountAmount()\n        +setDiscountAmount(BigDecimal discountAmount)\n        +getPayType()\n        +setPayType(Integer payType)\n        +getSourceType()\n        +setSourceType(Integer sourceType)\n        +getStatus()\n        +setStatus(Integer status)\n        +getOrderType()\n        +setOrderType(Integer orderType)\n        +getDeliveryCompany()\n        +setDeliveryCompany(String deliveryCompany)\n        +getDeliverySn()\n        +setDeliverySn(String deliverySn)\n        +getAutoConfirmDay()\n        +setAutoConfirmDay(Integer autoConfirmDay)\n        +getIntegration()\n        +setIntegration(Integer integration)\n        +getGrowth()\n        +setGrowth(Integer growth)\n        +getPromotionInfo()\n        +setPromotionInfo(String promotionInfo)\n        +getBillType()\n        +setBillType(Integer billType)\n        +getBillHeader()\n        +setBillHeader(String billHeader)\n        +getBillContent()\n        +setBillContent(String billContent)\n        +getBillReceiverPhone()\n        +setBillReceiverPhone(String billReceiverPhone)\n        +getBillReceiverEmail()\n        +setBillReceiverEmail(String billReceiverEmail)\n        +getReceiverName()\n        +setReceiverName(String receiverName)\n        +getReceiverPhone()\n        +setReceiverPhone(String receiverPhone)\n        +getReceiverPostCode()\n        +setReceiverPostCode(String receiverPostCode)\n        +getReceiverProvince()\n        +setReceiverProvince(String receiverProvince)\n        +getReceiverCity()\n        +setReceiverCity(String receiverCity)\n        +getReceiverRegion()\n        +setReceiverRegion(String receiverRegion)\n        +getReceiverDetailAddress()\n        +setReceiverDetailAddress(String receiverDetailAddress)\n        +getNote()\n        +setNote(String note)\n        +getConfirmStatus()\n        +setConfirmStatus(Integer confirmStatus)\n        +getDeleteStatus()\n        +setDeleteStatus(Integer deleteStatus)\n        +getUseIntegration()\n        +setUseIntegration(Integer useIntegration)\n        +getPaymentTime()\n        +setPaymentTime(Date paymentTime)\n        +getDeliveryTime()\n        +setDeliveryTime(Date deliveryTime)\n        +getReceiveTime()\n        +setReceiveTime(Date receiveTime)\n        +getCommentTime()\n        +setCommentTime(Date commentTime)\n        +getModifyTime()\n        +setModifyTime(Date modifyTime)\n    }\n    class SmsCouponHistory {\n        -Long id\n        -Long couponId\n        -Long memberId\n        -String couponCode\n        -String memberNickname\n        -Integer getType\n        -Date createTime\n        -Integer useStatus\n        -Date useTime\n        -Long orderId\n        -String orderSn\n        +setUseStatus(Integer useStatus)\n        +setUseTime(Date useTime)\n    }\n    class OmsCartItem {\n        -Long id\n        -Long productId\n        -Long productSkuId\n        -Long memberId\n        -Integer quantity\n        -BigDecimal price\n        -String productPic\n        -String productName\n        -String productSubTitle\n        -String productSkuCode\n        -String memberNickname\n        -Date createDate\n        -Date modifyDate\n        -Integer deleteStatus\n        -Long productCategoryId\n        -String productBrand\n        -String productSn\n        -String productAttr\n        +getId()\n        +getProductSkuId()\n        +getProductName()\n        +getQuantity()\n        +getProductSn()\n        +getProductBrand()\n        +getProductPic()\n        +getProductAttr()\n        +getPrice()\n        +getProductSkuCode()\n        +getProductId()\n        +getProductCategoryId()\n    }\n    class SmsCouponProductRelation {\n        -Long id\n        -Long couponId\n        -Long productId\n        -String productName\n        -String productSn\n        +getProductId()\n    }\n    class UmsMember {\n        -Long id\n        -Long memberLevelId\n        -String username\n        -String password\n        -String nickname\n        -String phone\n        -Integer status\n        -Date createTime\n        -String icon\n        -Integer gender\n        -Date birthday\n        -String city\n        -String job\n        -String personalizedSignature\n        -Integer sourceType\n        -Integer integration\n        -Integer growth\n        -Integer luckeyCount\n        -Integer historyIntegration\n        +getId()\n        +getUsername()\n        +getIntegration()\n        +setIntegration(Integer integration)\n    }\n    class UmsMemberReceiveAddress {\n        -Long id\n        -Long memberId\n        -String name\n        -String phoneNumber\n        -Integer defaultStatus\n        -String postCode\n        -String province\n        -String city\n        -String region\n        -String detailAddress\n        +getName()\n        +getPhoneNumber()\n        +getPostCode()\n        +getProvince()\n        +getCity()\n        +getRegion()\n        +getDetailAddress()\n    }\n    class OmsOrderItem {\n        -Long id\n        -Long orderId\n        -String orderSn\n        -Long productId\n        -String productPic\n        -String productName\n        -String productBrand\n        -String productSn\n        -BigDecimal productPrice\n        -Integer productQuantity\n        -Long productSkuId\n        -String productSkuCode\n        -Long productCategoryId\n        -String promotionName\n        -BigDecimal promotionAmount\n        -BigDecimal couponAmount\n        -BigDecimal integrationAmount\n        -BigDecimal realAmount\n        -Integer giftIntegration\n        -Integer giftGrowth\n        -String productAttr\n        +setPromotionAmount(BigDecimal promotionAmount)\n        +getPromotionName()\n        +setProductCategoryId(Long productCategoryId)\n        +setPromotionName(String promotionName)\n        +setProductAttr(String productAttr)\n        +setGiftIntegration(Integer giftIntegration)\n        +getGiftGrowth()\n        +setProductSn(String productSn)\n        +getProductPrice()\n        +getOrderId()\n        +setProductPrice(BigDecimal productPrice)\n        +getCouponAmount()\n        +setOrderId(Long orderId)\n        +setIntegrationAmount(BigDecimal integrationAmount)\n        +setProductId(Long productId)\n        +setProductPic(String productPic)\n        +setProductQuantity(Integer productQuantity)\n        +setGiftGrowth(Integer giftGrowth)\n        +setProductSkuId(Long productSkuId)\n        +setRealAmount(BigDecimal realAmount)\n        +getGiftIntegration()\n        +setProductSkuCode(String productSkuCode)\n        +setProductBrand(String productBrand)\n        +setOrderSn(String orderSn)\n        +getProductId()\n        +getIntegrationAmount()\n        +getProductQuantity()\n        +setProductName(String productName)\n        +setCouponAmount(BigDecimal couponAmount)\n    }\n    class OmsOrderSetting {\n        -Long id\n        -Integer flashOrderOvertime\n        -Integer normalOrderOvertime\n        -Integer confirmOvertime\n        -Integer finishOvertime\n        -Integer commentOvertime\n        +getConfirmOvertime()\n        +getNormalOrderOvertime()\n    }\n    class UmsIntegrationConsumeSetting {\n        -Long id\n        -Integer deductionPerAmount\n        -Integer maxPercentPerOrder\n        -Integer useUnit\n        -Integer couponStatus\n        +getCouponStatus()\n        +getMaxPercentPerOrder()\n        +getUseUnit()\n    }\n    class SmsCoupon {\n        -Long id\n        -Integer type\n        -String name\n        -Integer platform\n        -Integer count\n        -BigDecimal amount\n        -Integer perLimit\n        -BigDecimal minPoint\n        -Date startTime\n        -Date endTime\n        -Integer useType\n        -String note\n        -Integer publishCount\n        -Integer useCount\n        -Integer receiveCount\n        -Date enableTime\n        -String code\n        -Integer memberLevel\n        +getUseType()\n        +getId()\n        +getAmount()\n    }\n    class PmsSkuStock {\n        -Long id\n        -Long productId\n        -String skuCode\n        -BigDecimal price\n        -Integer stock\n        -Integer lowStock\n        -String pic\n        -Integer sale\n        -BigDecimal promotionPrice\n        -Integer lockStock\n        -String spData\n        +setLockStock(Integer lockStock)\n        +getLockStock()\n    }\n    class OmsOrderItemExample {\n    }\n    class OmsOrderSettingExample {\n    }\n    class CancelOrderSender {\n        +sendMessage(Long orderId, long delayTimes)\n    }\n    class UmsMemberCouponService {\n        <<interface>>\n        +add(Long couponId)\n        +listHistory(Integer useStatus)\n        +listCart(List~CartPromotionItem~, Integer type)\n        +listByProduct(Long productId)\n        +list(Integer useStatus)\n    }\n    class OmsCartItemService {\n        <<interface>>\n        +add(OmsCartItem cartItem)\n        +list(Long memberId)\n        +listPromotion(Long memberId, List~Long~ cartIds)\n        +updateQuantity(Long id, Long memberId, Integer quantity)\n        +delete(Long memberId, List~Long~ ids)\n        +getCartProduct(Long productId)\n        +updateAttr(OmsCartItem cartItem)\n        +clear(Long memberId)\n    }\n    class UmsMemberService {\n        <<interface>>\n        +getByUsername(String username)\n        +getById(Long id)\n        +register(String username, String password, String telephone, String authCode)\n        +generateAuthCode(String telephone)\n        +updatePassword(String telephone, String password, String authCode)\n        +getCurrentMember()\n        +updateIntegration(Long id,Integer integration)\n        +loadUserByUsername(String username)\n        +login(String username, String password)\n        +refreshToken(String token)\n    }\n    class UmsMemberReceiveAddressService {\n        <<interface>>\n        +add(UmsMemberReceiveAddress address)\n        +delete(Long id)\n        +update(Long id, UmsMemberReceiveAddress address)\n        +list()\n        +getItem(Long id)\n    }\n    class PortalOrderDao {\n        <<interface>>\n        +getDetail(Long orderId)\n        +updateSkuStock(List~OmsOrderItem~ orderItemList)\n        +getTimeOutOrders(Integer minute)\n        +updateOrderStatus(List~Long~ ids,Integer status)\n        +releaseSkuStockLock(List~OmsOrderItem~ orderItemList)\n        +lockStockBySkuId(Long productSkuId,Integer quantity)\n        +reduceSkuStock(Long productSkuId,Integer quantity)\n        +releaseStockBySkuId(Long productSkuId,Integer quantity)\n    }\n    class PortalOrderItemDao {\n        <<interface>>\n        +insertList(List~OmsOrderItem~ list)\n    }\n    class SmsCouponHistoryDetail {\n    }\n    AlipayController ..> AlipayService : uses\n    AlipayController ..> CommonResult~String~ : returns\n    AlipayServiceImpl <|.. AlipayService\n    AlipayServiceImpl ..> OmsPortalOrderService : uses\n    OmsPortalOrderServiceImpl <|.. OmsPortalOrderService\n    OmsPortalOrderServiceImpl ..> CommonPage~OmsOrderDetail~ : uses\n    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderDetail : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderExample : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponHistoryExample : uses\n    OmsPortalOrderServiceImpl ..> OmsOrder : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderItem : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderItemExample : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderSettingExample : uses\n    OmsPortalOrderServiceImpl ..> UmsMember : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberReceiveAddress : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponHistory : uses\n    OmsPortalOrderServiceImpl ..> OmsCartItem : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponProductRelation : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponProductCategoryRelation : uses\n    OmsPortalOrderServiceImpl ..> SmsCoupon : uses\n    OmsPortalOrderServiceImpl ..> UmsIntegrationConsumeSetting : uses\n    OmsPortalOrderServiceImpl ..> PmsSkuStock : uses\n    OmsPortalOrderServiceImpl ..> Asserts : uses\n    OmsPortalOrderServiceImpl ..> RedisService : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponHistoryMapper : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderItemMapper : uses\n    OmsPortalOrderServiceImpl ..> UmsIntegrationConsumeSettingMapper : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderMapper : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderSettingMapper : uses\n    OmsPortalOrderServiceImpl ..> PmsSkuStockMapper : uses\n    OmsPortalOrderServiceImpl ..> CancelOrderSender : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberCouponService : uses\n    OmsPortalOrderServiceImpl ..> OmsCartItemService : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberService : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberReceiveAddressService : uses\n    OmsPortalOrderServiceImpl ..> PortalOrderDao : uses\n    OmsPortalOrderServiceImpl ..> PortalOrderItemDao : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponHistoryDetail : returns\n    OmsPortalOrderServiceImpl ..> CommonPage~OmsOrderDetail~ : returns\n    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : returns\n    OmsPortalOrderServiceImpl ..> OmsOrderDetail : returns\n    OmsPortalOrderServiceImpl ..> OmsPortalOrderService : implements\n    OmsPortalOrderServiceImpl ..> OmsOrderExample : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponHistoryExample : uses\n    OmsPortalOrderServiceImpl ..> OmsOrder : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderItem : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderItemExample : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderSettingExample : uses\n    OmsPortalOrderServiceImpl ..> OmsOrderDetail : uses\n    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : uses\n    OmsPortalOrderServiceImpl ..> SmsCoupon : uses\n    OmsPortalOrderServiceImpl ..> PmsSkuStock : uses\n    OmsPortalOrderServiceImpl ..> CancelOrderSender : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberCouponService : uses\n    OmsPortalOrderServiceImpl ..> OmsCartItemService : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberService : uses\n    OmsPortalOrderServiceImpl ..> UmsMemberReceiveAddressService : uses\n    OmsPortalOrderServiceImpl ..> PortalOrderDao : uses\n    OmsPortalOrderServiceImpl ..> PortalOrderItemDao : uses\n    OmsPortalOrderServiceImpl ..> SmsCouponHistoryDetail : returns\n    OmsPortalOrderServiceImpl ..> OmsOrderDetail : returns\n    OmsPortalOrderServiceImpl ..> ConfirmOrderResult : returns\n    OmsPortalOrderServiceImpl ..> CommonPage~OmsOrderDetail~ : returns\n    OmsPortalOrderServiceImpl ..> OmsPortalOrderService : implements\n    OmsPortalOrderServiceImpl ..|> OmsPortalOrderService\n    AlipayServiceImpl ..|> AlipayService\n",
    "mapping": {
        "AlipayController": "1810",
        "CommonResult~T~": "5968",
        "AlipayService": "1396",
        "AlipayServiceImpl": "2678",
        "OmsPortalOrderService": "1907",
        "CommonPage~T~": "2843",
        "ConfirmOrderResult": "1715",
        "OmsOrderDetail": "2321",
        "OmsPortalOrderServiceImpl": "4506",
        "Asserts": "1976",
        "RedisService": "2580",
        "SmsCouponHistoryMapper": "1843",
        "OmsOrderItemMapper": "3401",
        "UmsIntegrationConsumeSettingMapper": "1821",
        "OmsOrderMapper": "6852",
        "OmsOrderSettingMapper": "5231",
        "PmsSkuStockMapper": "1346",
        "OmsOrderExample": "9180",
        "SmsCouponProductCategoryRelation": "3400",
        "SmsCouponHistoryExample": "8394",
        "OmsOrder": "9215",
        "SmsCouponHistory": "3611",
        "OmsCartItem": "1204",
        "SmsCouponProductRelation": "2869",
        "UmsMember": "7450",
        "UmsMemberReceiveAddress": "1937",
        "OmsOrderItem": "1841",
        "OmsOrderSetting": "2524",
        "UmsIntegrationConsumeSetting": "1515",
        "SmsCoupon": "2975",
        "PmsSkuStock": "3036",
        "OmsOrderItemExample": "2251",
        "OmsOrderSettingExample": "2786",
        "CancelOrderSender": "2773",
        "UmsMemberCouponService": "1625",
        "OmsCartItemService": "2399",
        "UmsMemberService": "7755",
        "UmsMemberReceiveAddressService": "2834",
        "PortalOrderDao": "2311",
        "PortalOrderItemDao": "2970",
        "SmsCouponHistoryDetail": "2329"
    },
    "id_list": [
        {
            "source_id": "1810",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "32-74"
            ]
        },
        {
            "source_id": "5968",
            "name": "mall-common/src/main/java/com/macro/mall/common/api/CommonResult.java",
            "lines": [
                "21-22"
            ]
        },
        {
            "source_id": "1396",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "14-37"
            ]
        },
        {
            "source_id": "2678",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "29-162"
            ]
        },
        {
            "source_id": "1907",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "16-76"
            ]
        },
        {
            "source_id": "2843",
            "name": "mall-common/src/main/java/com/macro/mall/common/api/CommonPage.java",
            "lines": [
                "12-100"
            ]
        },
        {
            "source_id": "1715",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/domain/ConfirmOrderResult.java",
            "lines": [
                "18-44"
            ]
        },
        {
            "source_id": "2321",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/domain/OmsOrderDetail.java",
            "lines": [
                "15-20"
            ]
        },
        {
            "source_id": "4506",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "33-794"
            ]
        },
        {
            "source_id": "1976",
            "name": "mall-common/src/main/java/com/macro/mall/common/exception/Asserts.java",
            "lines": [
                "9-17"
            ]
        },
        {
            "source_id": "2580",
            "name": "mall-common/src/main/java/com/macro/mall/common/service/RedisService.java",
            "lines": [
                "11-182"
            ]
        },
        {
            "source_id": "1843",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/SmsCouponHistoryMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "3401",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/OmsOrderItemMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "1821",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/UmsIntegrationConsumeSettingMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "6852",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/OmsOrderMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "5231",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/OmsOrderSettingMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "1346",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/PmsSkuStockMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "9180",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderExample.java",
            "lines": [
                "8-3011"
            ]
        },
        {
            "source_id": "3400",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponProductCategoryRelation.java",
            "lines": [
                "6-76"
            ]
        },
        {
            "source_id": "8394",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponHistoryExample.java",
            "lines": [
                "7-890"
            ]
        },
        {
            "source_id": "9215",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrder.java",
            "lines": [
                "8-547"
            ]
        },
        {
            "source_id": "3611",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponHistory.java",
            "lines": [
                "7-147"
            ]
        },
        {
            "source_id": "1204",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsCartItem.java",
            "lines": [
                "8-231"
            ]
        },
        {
            "source_id": "2869",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponProductRelation.java",
            "lines": [
                "6-76"
            ]
        },
        {
            "source_id": "7450",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/UmsMember.java",
            "lines": [
                "7-246"
            ]
        },
        {
            "source_id": "1937",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/UmsMemberReceiveAddress.java",
            "lines": [
                "6-136"
            ]
        },
        {
            "source_id": "1841",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderItem.java",
            "lines": [
                "7-264"
            ]
        },
        {
            "source_id": "2524",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderSetting.java",
            "lines": [
                "6-90"
            ]
        },
        {
            "source_id": "1515",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/UmsIntegrationConsumeSetting.java",
            "lines": [
                "6-78"
            ]
        },
        {
            "source_id": "2975",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCoupon.java",
            "lines": [
                "8-233"
            ]
        },
        {
            "source_id": "3036",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/PmsSkuStock.java",
            "lines": [
                "7-149"
            ]
        },
        {
            "source_id": "2251",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderItemExample.java",
            "lines": [
                "7-1540"
            ]
        },
        {
            "source_id": "2786",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderSettingExample.java",
            "lines": [
                "6-559"
            ]
        },
        {
            "source_id": "2773",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/component/CancelOrderSender.java",
            "lines": [
                "18-35"
            ]
        },
        {
            "source_id": "1625",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/UmsMemberCouponService.java",
            "lines": [
                "15-41"
            ]
        },
        {
            "source_id": "2399",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsCartItemService.java",
            "lines": [
                "14-56"
            ]
        },
        {
            "source_id": "7755",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/UmsMemberService.java",
            "lines": [
                "11-64"
            ]
        },
        {
            "source_id": "2834",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/UmsMemberReceiveAddressService.java",
            "lines": [
                "12-42"
            ]
        },
        {
            "source_id": "2311",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/dao/PortalOrderDao.java",
            "lines": [
                "13-54"
            ]
        },
        {
            "source_id": "2970",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/dao/PortalOrderItemDao.java",
            "lines": [
                "12-17"
            ]
        },
        {
            "source_id": "2329",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/domain/SmsCouponHistoryDetail.java",
            "lines": [
                "17-26"
            ]
        }
    ]
}