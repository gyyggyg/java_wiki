{
    "mermaid": "graph TD\nsubgraph block1[\"Block:PortalOrderAndPromotionServiceImpl\"]\n  subgraph pkg1[\"Package:com.macro.mall.portal.service.impl\"]\n    fileOmsPortalOrderServiceImpl[OmsPortalOrderServiceImpl.java]\n    classOmsPortalOrderServiceImpl{OmsPortalOrderServiceImpl}\n    methodPaySuccessByOrderSnOmsImpl((paySuccessByOrderSn))\n    methodPaySuccessOmsImpl((paySuccess))\n    fileOmsPortalOrderServiceImpl --> classOmsPortalOrderServiceImpl\n    classOmsPortalOrderServiceImpl --> methodPaySuccessByOrderSnOmsImpl\n    classOmsPortalOrderServiceImpl --> methodPaySuccessOmsImpl\n  end\nend\nsubgraph block2[\"Block:mall-portal/src/main/java/com/macro/mall/portal/service/impl/\"]\n  subgraph pkg2[\"Package:com.macro.mall.portal.service.impl\"]\n    fileAlipayServiceImpl[AlipayServiceImpl.java]\n    classAlipayServiceImpl{AlipayServiceImpl}\n    methodQueryAlipayImpl((query))\n    methodNotifyAlipayImpl((notify))\n    fileAlipayServiceImpl --> classAlipayServiceImpl\n    classAlipayServiceImpl --> methodQueryAlipayImpl\n    classAlipayServiceImpl --> methodNotifyAlipayImpl\n  end\nend\nsubgraph block3[\"Block:mall-portal/src/main/java/com/macro/mall/portal/controller/\"]\n  subgraph pkg3[\"Package:com.macro.mall.portal.controller\"]\n    fileAlipayController[AlipayController.java]\n    classAlipayController{AlipayController}\n    methodPayAlipayCtrl((pay))\n    methodWebPayAlipayCtrl((webPay))\n    methodNotifyAlipayCtrl((notify))\n    methodQueryAlipayCtrl((query))\n    fileAlipayController --> classAlipayController\n    classAlipayController --> methodPayAlipayCtrl\n    classAlipayController --> methodWebPayAlipayCtrl\n    classAlipayController --> methodNotifyAlipayCtrl\n    classAlipayController --> methodQueryAlipayCtrl\n  end\nend\nsubgraph block4[\"Block:PortalOrderAndReturnService\"]\n  subgraph pkg4[\"Package:com.macro.mall.portal.service\"]\n    fileOmsPortalOrderService[OmsPortalOrderService.java]\n    classOmsPortalOrderService{OmsPortalOrderService}\n    methodPaySuccessByOrderSnOms((paySuccessByOrderSn))\n    fileOmsPortalOrderService --> classOmsPortalOrderService\n    classOmsPortalOrderService --> methodPaySuccessByOrderSnOms\n  end\nend\nsubgraph block5[\"Block:mall-portal/src/main/java/com/macro/mall/portal/service/\"]\n  subgraph pkg5[\"Package:com.macro.mall.portal.service\"]\n    fileAlipayService[AlipayService.java]\n    classAlipayService{AlipayService}\n    methodPayAlipay((pay))\n    methodWebPayAlipay((webPay))\n    methodNotifyAlipay((notify))\n    methodQueryAlipay((query))\n    fileAlipayService --> classAlipayService\n    classAlipayService --> methodPayAlipay\n    classAlipayService --> methodWebPayAlipay\n    classAlipayService --> methodNotifyAlipay\n    classAlipayService --> methodQueryAlipay\n  end\nend\n%% 方法间调用/实现关系\nmethodQueryAlipayImpl ==> methodPaySuccessByOrderSnOms\nmethodNotifyAlipayImpl ==> methodPaySuccessByOrderSnOms\nmethodPayAlipayCtrl ==> methodPayAlipay\nmethodWebPayAlipayCtrl ==> methodWebPayAlipay\nmethodNotifyAlipayCtrl ==> methodNotifyAlipay\nmethodQueryAlipayCtrl ==> methodQueryAlipay\nclassAlipayService ==> classAlipayServiceImpl\nclassOmsPortalOrderService ==> classOmsPortalOrderServiceImpl\nmethodPaySuccessByOrderSnOmsImpl ==> methodPaySuccessOmsImpl\n%% 高亮关键调用链\nlinkStyle 12 stroke:#ff0000,stroke-width:4px\nlinkStyle 16 stroke:#ff0000,stroke-width:4px\nlinkStyle 18 stroke:#ff0000,stroke-width:4px\nlinkStyle 19 stroke:#ff0000,stroke-width:4px\nlinkStyle 21 stroke:#ff0000,stroke-width:4px",
    "mapping": {
        "3159": "AlipayServiceImpl",
        "3233": "AlipayServiceImpl.query",
        "2737": "AlipayServiceImpl.notify",
        "1574": "OmsPortalOrderService",
        "1396": "OmsPortalOrderService.paySuccessByOrderSn",
        "8997": "AlipayController",
        "1734": "AlipayController.pay",
        "8918": "AlipayController.webPay",
        "1224": "AlipayController.notify",
        "3114": "AlipayController.query",
        "1623": "AlipayService",
        "1652": "AlipayService.pay",
        "1801": "AlipayService.webPay",
        "2246": "AlipayService.notify",
        "6005": "AlipayService.query",
        "5466": "OmsPortalOrderServiceImpl",
        "1362": "OmsPortalOrderServiceImpl.paySuccessByOrderSn",
        "3763": "OmsPortalOrderServiceImpl.paySuccess"
    },
    "id_list": [
        {
            "source_id": "3159",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "29-162"
            ]
        },
        {
            "source_id": "3233",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "99-130"
            ]
        },
        {
            "source_id": "2737",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "72-96"
            ]
        },
        {
            "source_id": "1574",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "16-76"
            ]
        },
        {
            "source_id": "1396",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "74-75"
            ]
        },
        {
            "source_id": "8997",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "32-74"
            ]
        },
        {
            "source_id": "1734",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "39-46"
            ]
        },
        {
            "source_id": "8918",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "48-55"
            ]
        },
        {
            "source_id": "1224",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "59-66"
            ]
        },
        {
            "source_id": "3114",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "68-73"
            ]
        },
        {
            "source_id": "1623",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "14-37"
            ]
        },
        {
            "source_id": "1652",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "18-18"
            ]
        },
        {
            "source_id": "1801",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "36-36"
            ]
        },
        {
            "source_id": "2246",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "23-23"
            ]
        },
        {
            "source_id": "6005",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "31-31"
            ]
        },
        {
            "source_id": "5466",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "33-794"
            ]
        },
        {
            "source_id": "1362",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "446-457"
            ]
        },
        {
            "source_id": "3763",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "255-283"
            ]
        }
    ]
}