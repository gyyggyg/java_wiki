{
    "mermaid": "graph TD\nsubgraph block1[\"Block:PortalOrderAndPromotionServiceImpl\"]\n    subgraph pkg1[\"Package:com.macro.mall.portal.service.impl\"]\n        fileOmsPortalOrderServiceImpl[\"OmsPortalOrderServiceImpl.java\"]\n        classOmsPortalOrderServiceImpl{\"OmsPortalOrderServiceImpl\"}\n        methodPaySuccessByOrderSnOmsPortalOrderServiceImpl((\"paySuccessByOrderSn\"))\n        methodPaySuccessOmsPortalOrderServiceImpl((\"paySuccess\"))\n        fileAlipayServiceImpl[\"AlipayServiceImpl.java\"]\n        classAlipayServiceImpl{\"AlipayServiceImpl\"}\n        methodQueryAlipayServiceImpl((\"query\"))\n        methodNotifyAlipayServiceImpl((\"notify\"))\n        \n        fileOmsPortalOrderServiceImpl --> classOmsPortalOrderServiceImpl\n        classOmsPortalOrderServiceImpl --> methodPaySuccessByOrderSnOmsPortalOrderServiceImpl\n        classOmsPortalOrderServiceImpl --> methodPaySuccessOmsPortalOrderServiceImpl\n        fileAlipayServiceImpl --> classAlipayServiceImpl\n        classAlipayServiceImpl --> methodQueryAlipayServiceImpl\n        classAlipayServiceImpl --> methodNotifyAlipayServiceImpl\n    end\nend\n\nsubgraph block2[\"Block:PortalOrderAndReturnService\"]\n    subgraph pkg2[\"Package:com.macro.mall.portal.service\"]\n        fileOmsPortalOrderService[\"OmsPortalOrderService.java\"]\n        classOmsPortalOrderService{\"OmsPortalOrderService\"}\n        methodPaySuccessByOrderSnOmsPortalOrderService((\"paySuccessByOrderSn\"))\n        \n        fileOmsPortalOrderService --> classOmsPortalOrderService\n        classOmsPortalOrderService --> methodPaySuccessByOrderSnOmsPortalOrderService\n    end\nend\n\nsubgraph block3[\"Block:mall-portal/src/main/java/com/macro/mall/portal/controller/\"]\n    subgraph pkg3[\"Package:com.macro.mall.portal.controller\"]\n        fileAlipayController[\"AlipayController.java\"]\n        classAlipayController{\"AlipayController\"}\n        methodPayAlipayController((\"pay\"))\n        methodWebPayAlipayController((\"webPay\"))\n        methodNotifyAlipayController((\"notify\"))\n        methodQueryAlipayController((\"query\"))\n\n        fileAlipayController --> classAlipayController\n        classAlipayController --> methodPayAlipayController\n        classAlipayController --> methodWebPayAlipayController\n        classAlipayController --> methodNotifyAlipayController\n        classAlipayController --> methodQueryAlipayController\n    end\nend\n\nsubgraph block4[\"Block:mall-portal/src/main/java/com/macro/mall/portal/service/\"]\n    subgraph pkg4[\"Package:com.macro.mall.portal.service\"]\n        fileAlipayService[\"AlipayService.java\"]\n        classAlipayService{\"AlipayService\"}\n        methodPayAlipayService((\"pay\"))\n        methodWebPayAlipayService((\"webPay\"))\n        methodNotifyAlipayService((\"notify\"))\n        methodQueryAlipayService((\"query\"))\n\n        fileAlipayService --> classAlipayService\n        classAlipayService --> methodPayAlipayService\n        classAlipayService --> methodWebPayAlipayService\n        classAlipayService --> methodNotifyAlipayService\n        classAlipayService --> methodQueryAlipayService\n    end\nend\n\n\nmethodQueryAlipayServiceImpl ==> methodPaySuccessByOrderSnOmsPortalOrderService\nmethodNotifyAlipayServiceImpl ==> methodPaySuccessByOrderSnOmsPortalOrderService\nmethodPayAlipayController ==> methodPayAlipayService\nmethodWebPayAlipayController ==> methodWebPayAlipayService\nmethodNotifyAlipayController ==> methodNotifyAlipayService\nmethodQueryAlipayController ==> methodQueryAlipayService\n\nclassAlipayService -- implemented_by --> classAlipayServiceImpl\nclassOmsPortalOrderService -- implemented_by --> classOmsPortalOrderServiceImpl\nmethodPaySuccessByOrderSnOmsPortalOrderServiceImpl ==> methodPaySuccessOmsPortalOrderServiceImpl",
    "mapping": {
        "fileAlipayServiceImpl": "1506",
        "methodQueryAlipayServiceImpl": "2791",
        "methodNotifyAlipayServiceImpl": "1067",
        "classOmsPortalOrderService": "1590",
        "methodPaySuccessByOrderSnOmsPortalOrderService": "9356",
        "classAlipayController": "1745",
        "methodPayAlipayController": "5535",
        "methodWebPayAlipayController": "2925",
        "methodNotifyAlipayController": "1235",
        "methodQueryAlipayController": "2246",
        "classAlipayService": "1913",
        "methodPayAlipayService": "2539",
        "methodWebPayAlipayService": "4913",
        "methodNotifyAlipayService": "2904",
        "methodQueryAlipayService": "1043",
        "classOmsPortalOrderServiceImpl": "1375",
        "methodPaySuccessByOrderSnOmsPortalOrderServiceImpl": "1516",
        "methodPaySuccessOmsPortalOrderServiceImpl": "2743"
    },
    "id_list": [
        {
            "source_id": "1506",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "29-162"
            ]
        },
        {
            "source_id": "2791",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "99-130"
            ]
        },
        {
            "source_id": "1067",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "72-96"
            ]
        },
        {
            "source_id": "1590",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "16-76"
            ]
        },
        {
            "source_id": "9356",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "74-75"
            ]
        },
        {
            "source_id": "1745",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "32-74"
            ]
        },
        {
            "source_id": "5535",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "39-46"
            ]
        },
        {
            "source_id": "2925",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "48-55"
            ]
        },
        {
            "source_id": "1235",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "59-66"
            ]
        },
        {
            "source_id": "2246",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "68-73"
            ]
        },
        {
            "source_id": "1913",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "14-37"
            ]
        },
        {
            "source_id": "2539",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "18-18"
            ]
        },
        {
            "source_id": "4913",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "36-36"
            ]
        },
        {
            "source_id": "2904",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "23-23"
            ]
        },
        {
            "source_id": "1043",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "31-31"
            ]
        },
        {
            "source_id": "1375",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "33-794"
            ]
        },
        {
            "source_id": "1516",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "446-457"
            ]
        },
        {
            "source_id": "2743",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "255-283"
            ]
        }
    ]
}