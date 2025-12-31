{
    "mermaid": "flowchart TD\n    direction TB\n    subgraph 请求参数处理\n        A1[\"收集支付宝回调参数\n(将参数整理为Map)\"]\n        style A1 fill:#0af,stroke:#036,stroke-width:4px\n    end\n    subgraph 业务回调通知\n        B1[\"调用alipayService.notify\n(验证合法性并处理业务)\"]\n        style B1 fill:#0af,stroke:#036,stroke-width:4px\n        B2[\"业务处理成功?\"]\n        style B2 fill:#fff,stroke:#333,stroke-width:2px,shape:diamond\n        B3[\"返回 'success'\n(支付宝认为通知完成)\"]\n        style B3 fill:#0af,stroke:#036,stroke-width:4px\n        B4[\"返回 'failure'\n(支付宝可能重试)\"]\n        style B4 fill:#fbb,stroke:#f96,stroke-width:3px,stroke-dasharray:5 5\n    end\n    A1 --> B1\n    B1 --> B2\n    B2 -- 处理成功 --> B3\n    B2 -- 处理失败 --> B4\n    style B4 fill:#fbb,stroke:#f96,stroke-width:3px,stroke-dasharray:5 5\n    style B3 fill:#0af,stroke:#036,stroke-width:4px\n    style B1 fill:#0af,stroke:#036,stroke-width:4px",
    "mapping": {
        "A1": "1867",
        "B1": "2560",
        "B2": "2560",
        "B3": "2560",
        "B4": "2560"
    },
    "id_list": [
        {
            "source_id": "1867",
            "lines": [
                "3-5"
            ],
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java"
        },
        {
            "source_id": "2560",
            "lines": [
                "6"
            ],
            "name": "mall-portal/src/main/java/com/macro/mall/portal/controller/AlipayController.java"
        }
    ]
}