{
    "mermaid": "classDiagram\nclass AlipayController {\n    +pay(AliPayParam, HttpServletResponse) void\n    +webPay(AliPayParam, HttpServletResponse) void\n    +notify(HttpServletRequest) String\n    +query(String, String) CommonResult~String~\n    -AlipayConfig alipayConfig\n    -AlipayService alipayService\n}\nclass AlipayService {\n    <<interface>>\n    +pay(AliPayParam) String\n    +notify(Map~String, String~) String\n    +query(String, String) String\n    +webPay(AliPayParam) String\n}\nclass AlipayServiceImpl {\n    +pay(AliPayParam) String\n    +notify(Map~String, String~) String\n    +query(String, String) String\n    +webPay(AliPayParam) String\n    -AlipayConfig alipayConfig\n    -AlipayClient alipayClient\n    -OmsOrderMapper orderMapper\n    -OmsPortalOrderService portalOrderService\n}\nclass CommonResult~T~ {\n    -long code\n    -String message\n    -T data\n    +getCode() long\n    +setCode(long)\n    +getMessage() String\n    +setMessage(String)\n    +getData() T\n    +setData(T)\n    +success(T) CommonResult~T~\n    +success(T, String) CommonResult~T~\n    +failed(IErrorCode) CommonResult~T~\n    +failed(IErrorCode, String) CommonResult~T~\n    +failed(String) CommonResult~T~\n    +failed() CommonResult~T~\n    +validateFailed() CommonResult~T~\n    +validateFailed(String) CommonResult~T~\n    +unauthorized(T) CommonResult~T~\n    +forbidden(T) CommonResult~T~\n}\nclass OmsPortalOrderService {\n    <<interface>>\n    +generateConfirmOrder(List~Long~) ConfirmOrderResult\n    +generateOrder(OrderParam) Map~String, Object~\n    +paySuccess(Long, Integer) Integer\n    +cancelTimeOutOrder() Integer\n    +cancelOrder(Long)\n    +sendDelayMessageCancelOrder(Long)\n    +confirmReceiveOrder(Long)\n    +list(Integer, Integer, Integer) CommonPage~OmsOrderDetail~\n    +detail(Long) OmsOrderDetail\n    +deleteOrder(Long)\n    +paySuccessByOrderSn(String, Integer)\n}\nclass OmsPortalOrderServiceImpl {\n    +generateConfirmOrder(List~Long~) ConfirmOrderResult\n    +generateOrder(OrderParam) Map~String, Object~\n    +paySuccess(Long, Integer) Integer\n    +cancelTimeOutOrder() Integer\n    +cancelOrder(Long)\n    +sendDelayMessageCancelOrder(Long)\n    +confirmReceiveOrder(Long)\n    +list(Integer, Integer, Integer) CommonPage~OmsOrderDetail~\n    +detail(Long) OmsOrderDetail\n    +deleteOrder(Long)\n    +paySuccessByOrderSn(String, Integer)\n    -UmsMemberService memberService\n    -OmsCartItemService cartItemService\n    -UmsMemberReceiveAddressService memberReceiveAddressService\n    -UmsMemberCouponService memberCouponService\n    -UmsIntegrationConsumeSettingMapper integrationConsumeSettingMapper\n    -PmsSkuStockMapper skuStockMapper\n    -SmsCouponHistoryMapper couponHistoryMapper\n    -OmsOrderMapper orderMapper\n    -PortalOrderItemDao orderItemDao\n    -RedisService redisService\n    -PortalOrderDao portalOrderDao\n    -OmsOrderSettingMapper orderSettingMapper\n    -OmsOrderItemMapper orderItemMapper\n    -CancelOrderSender cancelOrderSender\n    -String REDIS_KEY_ORDER_ID\n    -String REDIS_DATABASE\n}\nAlipayController --> AlipayService : uses\nAlipayController --> CommonResult~String~ : uses success()\nAlipayServiceImpl ..|> AlipayService : implements\nAlipayServiceImpl --> OmsPortalOrderService : uses paySuccessByOrderSn()\nOmsPortalOrderServiceImpl ..|> OmsPortalOrderService : implements\nOmsPortalOrderServiceImpl --> CommonPage~OmsOrderDetail~ : uses list()\nOmsPortalOrderServiceImpl --> ConfirmOrderResult : uses generateConfirmOrder()\nOmsPortalOrderServiceImpl --> OmsOrderDetail : uses detail(), list()\nOmsPortalOrderServiceImpl --> Asserts : uses fail()\nOmsPortalOrderServiceImpl --> RedisService : uses incr()\nOmsPortalOrderServiceImpl --> SmsCouponHistoryMapper : uses selectByExample(), updateByPrimaryKeySelective()\nOmsPortalOrderServiceImpl --> OmsOrderItemMapper : uses selectByExample()\nOmsPortalOrderServiceImpl --> UmsIntegrationConsumeSettingMapper : uses selectByPrimaryKey()\nOmsPortalOrderServiceImpl --> OmsOrderMapper : uses insert(), selectByExample(), updateByPrimaryKeySelective()\nOmsPortalOrderServiceImpl --> OmsOrderSettingMapper : uses selectByPrimaryKey(), selectByExample()\nOmsPortalOrderServiceImpl --> PmsSkuStockMapper : uses selectByPrimaryKey()\nOmsPortalOrderServiceImpl --> OmsOrderExample : uses list(), paySuccess(), paySuccessByOrderSn(), cancelOrder()\nOmsPortalOrderServiceImpl --> SmsCouponProductCategoryRelation : uses getProductCategoryId()\nOmsPortalOrderServiceImpl --> SmsCouponHistoryExample : uses updateCouponStatus()\nOmsPortalOrderServiceImpl --> OmsOrder : uses generateOrder(), paySuccess()\nOmsPortalOrderServiceImpl --> SmsCouponHistory : uses setUseStatus(), setUseTime()\nOmsPortalOrderServiceImpl --> OmsCartItem : uses getId(), getProductSkuId(), getProductName()\nOmsPortalOrderServiceImpl --> SmsCouponProductRelation : uses getProductId()\nOmsPortalOrderServiceImpl --> UmsMember : uses getIntegration(), getId(), getUsername()\nOmsPortalOrderServiceImpl --> UmsMemberReceiveAddress : uses getName(), getPhoneNumber(), getPostCode(), getProvince(), getCity(), getRegion(), getDetailAddress()\nOmsPortalOrderServiceImpl --> OmsOrderItem : uses generateOrder()\nOmsPortalOrderServiceImpl --> OmsOrderItemExample : uses cancelOrder(), list(), detail()\nOmsPortalOrderServiceImpl --> OmsOrderSetting : uses getConfirmOvertime(), getNormalOrderOvertime()\nOmsPortalOrderServiceImpl --> UmsIntegrationConsumeSetting : uses getCouponStatus(), getMaxPercentPerOrder(), getUseUnit()\nOmsPortalOrderServiceImpl --> SmsCoupon : uses getUseType(), getId(), getAmount()\nOmsPortalOrderServiceImpl --> PmsSkuStock : uses setLockStock(), getLockStock()\nOmsPortalOrderServiceImpl --> CancelOrderSender : uses sendMessage()\nOmsPortalOrderServiceImpl --> UmsMemberCouponService : uses listCart()\nOmsPortalOrderServiceImpl --> OmsCartItemService : uses delete(), listPromotion()\nOmsPortalOrderServiceImpl --> UmsMemberService : uses getCurrentMember(), getById(), updateIntegration()\nOmsPortalOrderServiceImpl --> UmsMemberReceiveAddressService : uses list(), getItem()\nOmsPortalOrderServiceImpl --> PortalOrderDao : uses releaseSkuStockLock(), lockStockBySkuId(), reduceSkuStock(), getTimeOutOrders(), getDetail(), releaseStockBySkuId(), updateOrderStatus()\nOmsPortalOrderServiceImpl --> PortalOrderItemDao : uses insertList()\n%% 高亮目标节点\nstyle AlipayController fill:#ffe4e1,stroke:#d60000,stroke-width:2px\nstyle AlipayService fill:#ffe4e1,stroke:#d60000,stroke-width:2px\nstyle AlipayServiceImpl fill:#ffe4e1,stroke:#d60000,stroke-width:2px\nstyle OmsPortalOrderService fill:#ffe4e1,stroke:#d60000,stroke-width:2px\nstyle OmsPortalOrderServiceImpl fill:#ffe4e1,stroke:#d60000,stroke-width:2px\nlinkStyle 0 stroke:#d60000,\nstroke-width:2px\nlinkStyle 1 stroke:#d60000,\nstroke-width:2px\nlinkStyle 2 stroke:#d60000,\nstroke-width:2px\nlinkStyle 3 stroke:#d60000,\nstroke-width:2px\nlinkStyle 4 stroke:#d60000,\nstroke-width:2px\n",
    "mapping": {
        "AlipayController": "2226",
        "CommonResult~T~": "6900",
        "AlipayService": "4369",
        "AlipayServiceImpl": "1346",
        "OmsPortalOrderService": "2524",
        "CommonPage~OmsOrderDetail~": "3239",
        "ConfirmOrderResult": "1425",
        "OmsOrderDetail": "5315",
        "OmsPortalOrderServiceImpl": "4708",
        "Asserts": "8707",
        "RedisService": "2465",
        "SmsCouponHistoryMapper": "2949",
        "OmsOrderItemMapper": "8642",
        "UmsIntegrationConsumeSettingMapper": "2637",
        "OmsOrderMapper": "8577",
        "OmsOrderSettingMapper": "4617",
        "PmsSkuStockMapper": "1025",
        "OmsOrderExample": "1852",
        "SmsCouponProductCategoryRelation": "1512",
        "SmsCouponHistoryExample": "1672",
        "OmsOrder": "7746",
        "SmsCouponHistory": "3162",
        "OmsCartItem": "2500",
        "SmsCouponProductRelation": "5902",
        "UmsMember": "1239",
        "UmsMemberReceiveAddress": "5985",
        "OmsOrderItem": "2817",
        "OmsOrderItemExample": "8645",
        "OmsOrderSetting": "1250",
        "UmsIntegrationConsumeSetting": "9273",
        "SmsCoupon": "2521",
        "PmsSkuStock": "1508",
        "CancelOrderSender": "1656",
        "UmsMemberCouponService": "3244",
        "OmsCartItemService": "1964",
        "UmsMemberService": "1338",
        "UmsMemberReceiveAddressService": "3024",
        "PortalOrderDao": "1675",
        "PortalOrderItemDao": "2929"
    },
    "id_list": [
        {
            "source_id": "2226",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "32-74"
            ]
        },
        {
            "source_id": "6900",
            "name": "mall-common/src/main/java/com/macro/mall/common/api/CommonResult.java",
            "lines": [
                "21-22"
            ]
        },
        {
            "source_id": "4369",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "14-37"
            ]
        },
        {
            "source_id": "1346",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "29-162"
            ]
        },
        {
            "source_id": "2524",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "16-76"
            ]
        },
        {
            "source_id": "3239",
            "name": "mall-common/src/main/java/com/macro/mall/common/api/CommonPage.java",
            "lines": [
                "12-100"
            ]
        },
        {
            "source_id": "1425",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/domain/ConfirmOrderResult.java",
            "lines": [
                "18-44"
            ]
        },
        {
            "source_id": "5315",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/domain/OmsOrderDetail.java",
            "lines": [
                "15-20"
            ]
        },
        {
            "source_id": "4708",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "33-794"
            ]
        },
        {
            "source_id": "8707",
            "name": "mall-common/src/main/java/com/macro/mall/common/exception/Asserts.java",
            "lines": [
                "9-17"
            ]
        },
        {
            "source_id": "2465",
            "name": "mall-common/src/main/java/com/macro/mall/common/service/RedisService.java",
            "lines": [
                "11-182"
            ]
        },
        {
            "source_id": "2949",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/SmsCouponHistoryMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "8642",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/OmsOrderItemMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "2637",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/UmsIntegrationConsumeSettingMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "8577",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/OmsOrderMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "4617",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/OmsOrderSettingMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "1025",
            "name": "mall-mbg/src/main/java/com/macro/mall/mapper/PmsSkuStockMapper.java",
            "lines": [
                "8-30"
            ]
        },
        {
            "source_id": "1852",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderExample.java",
            "lines": [
                "8-3011"
            ]
        },
        {
            "source_id": "1512",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponProductCategoryRelation.java",
            "lines": [
                "6-76"
            ]
        },
        {
            "source_id": "1672",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponHistoryExample.java",
            "lines": [
                "7-890"
            ]
        },
        {
            "source_id": "7746",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrder.java",
            "lines": [
                "8-547"
            ]
        },
        {
            "source_id": "3162",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponHistory.java",
            "lines": [
                "7-147"
            ]
        },
        {
            "source_id": "2500",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsCartItem.java",
            "lines": [
                "8-231"
            ]
        },
        {
            "source_id": "5902",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCouponProductRelation.java",
            "lines": [
                "6-76"
            ]
        },
        {
            "source_id": "1239",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/UmsMember.java",
            "lines": [
                "7-246"
            ]
        },
        {
            "source_id": "5985",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/UmsMemberReceiveAddress.java",
            "lines": [
                "6-136"
            ]
        },
        {
            "source_id": "2817",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderItem.java",
            "lines": [
                "7-264"
            ]
        },
        {
            "source_id": "1250",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderSetting.java",
            "lines": [
                "6-90"
            ]
        },
        {
            "source_id": "9273",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/UmsIntegrationConsumeSetting.java",
            "lines": [
                "6-78"
            ]
        },
        {
            "source_id": "2521",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/SmsCoupon.java",
            "lines": [
                "8-233"
            ]
        },
        {
            "source_id": "1508",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/PmsSkuStock.java",
            "lines": [
                "7-149"
            ]
        },
        {
            "source_id": "8645",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderItemExample.java",
            "lines": [
                "7-1540"
            ]
        },
        {
            "source_id": "1784",
            "name": "mall-mbg/src/main/java/com/macro/mall/model/OmsOrderSettingExample.java",
            "lines": [
                "6-559"
            ]
        },
        {
            "source_id": "1656",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/component/CancelOrderSender.java",
            "lines": [
                "18-35"
            ]
        },
        {
            "source_id": "3244",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/UmsMemberCouponService.java",
            "lines": [
                "15-41"
            ]
        },
        {
            "source_id": "1964",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsCartItemService.java",
            "lines": [
                "14-56"
            ]
        },
        {
            "source_id": "1338",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/UmsMemberService.java",
            "lines": [
                "11-64"
            ]
        },
        {
            "source_id": "3024",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/UmsMemberReceiveAddressService.java",
            "lines": [
                "12-42"
            ]
        },
        {
            "source_id": "1675",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/dao/PortalOrderDao.java",
            "lines": [
                "13-54"
            ]
        },
        {
            "source_id": "2929",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/dao/PortalOrderItemDao.java",
            "lines": [
                "12-17"
            ]
        },
        {
            "source_id": "3541",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/domain/SmsCouponHistoryDetail.java",
            "lines": [
                "17-26"
            ]
        }
    ]
}