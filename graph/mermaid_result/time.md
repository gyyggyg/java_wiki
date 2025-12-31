{
    "mermaid": "sequenceDiagram\n    autonumber\n    participant AlipayController as AlipayController\n    participant AlipayService as AlipayService\n    participant AlipayServiceImpl as AlipayServiceImpl\n    participant OmsPortalOrderService as OmsPortalOrderService\n    participant OmsPortalOrderServiceImpl as OmsPortalOrderServiceImpl\n\n    AlipayController->>AlipayService: pay\n    AlipayController->>AlipayService: webPay\n    AlipayController->>AlipayService: query\n    rect rgb(240,248,255)\n        AlipayController->>AlipayService: notify\n    end\n    AlipayService->>AlipayServiceImpl: implemented_by\n    rect rgb(240,248,255)\n        AlipayService->>AlipayServiceImpl: implemented_by\n    end\n    AlipayServiceImpl->>OmsPortalOrderService: query\n    rect rgb(240,248,255)\n        AlipayServiceImpl->>OmsPortalOrderService: notify\n    end\n    OmsPortalOrderService->>OmsPortalOrderServiceImpl: implemented_by\n    rect rgb(240,248,255)\n        OmsPortalOrderService->>OmsPortalOrderServiceImpl: implemented_by\n    end\n    OmsPortalOrderServiceImpl->>OmsPortalOrderServiceImpl: paySuccessByOrderSn\n    rect rgb(240,248,255)\n        OmsPortalOrderServiceImpl->>OmsPortalOrderServiceImpl: paySuccessByOrderSn calls paySuccess\n    end\n",
    "mapping": {
        "AlipayServiceImpl": "2330",
        "AlipayServiceImpl.query": "4240",
        "AlipayServiceImpl.notify": "5436",
        "OmsPortalOrderService": "3225",
        "OmsPortalOrderService.paySuccessByOrderSn": "2030",
        "AlipayController": "3151",
        "AlipayController.pay": "2340",
        "AlipayController.webPay": "3234",
        "AlipayController.notify": "1478",
        "AlipayController.query": "2691",
        "AlipayService": "6023",
        "AlipayService.pay": "2399",
        "AlipayService.webPay": "2109",
        "AlipayService.notify": "1441",
        "AlipayService.query": "2791",
        "OmsPortalOrderServiceImpl": "2853",
        "OmsPortalOrderServiceImpl.paySuccessByOrderSn": "3201",
        "OmsPortalOrderServiceImpl.paySuccess": "3085"
    },
    "id_list": [
        {
            "source_id": "2330",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "29-162"
            ]
        },
        {
            "source_id": "4240",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "99-130"
            ]
        },
        {
            "source_id": "5436",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/AlipayServiceImpl.java",
            "lines": [
                "72-96"
            ]
        },
        {
            "source_id": "3225",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "16-76"
            ]
        },
        {
            "source_id": "2030",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/OmsPortalOrderService.java",
            "lines": [
                "74-75"
            ]
        },
        {
            "source_id": "3151",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "32-74"
            ]
        },
        {
            "source_id": "2340",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "39-46"
            ]
        },
        {
            "source_id": "3234",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "48-55"
            ]
        },
        {
            "source_id": "1478",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "59-66"
            ]
        },
        {
            "source_id": "2691",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java",
            "lines": [
                "68-73"
            ]
        },
        {
            "source_id": "6023",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "14-37"
            ]
        },
        {
            "source_id": "2399",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "18-18"
            ]
        },
        {
            "source_id": "2109",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "36-36"
            ]
        },
        {
            "source_id": "1441",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "23-23"
            ]
        },
        {
            "source_id": "2791",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/AlipayService.java",
            "lines": [
                "31-31"
            ]
        },
        {
            "source_id": "2853",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "33-794"
            ]
        },
        {
            "source_id": "3201",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "446-457"
            ]
        },
        {
            "source_id": "3085",
            "name": "mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java",
            "lines": [
                "255-283"
            ]
        }
    ]
}