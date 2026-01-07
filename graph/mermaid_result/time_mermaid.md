```mermaid
sequenceDiagram
    autonumber
    participant AlipayController as AlipayController
    participant AlipayService as AlipayService
    participant AlipayServiceImpl as AlipayServiceImpl
    participant OmsPortalOrderService as OmsPortalOrderService
    participant OmsPortalOrderServiceImpl as OmsPortalOrderServiceImpl

    AlipayController->>AlipayService: pay %% AlipayController.pay
    AlipayController->>AlipayService: webPay %% AlipayController.webPay
    AlipayController->>AlipayService: notify %% AlipayController.notify
    AlipayController->>AlipayService: query %% AlipayController.query
    AlipayService-->>AlipayServiceImpl: implemented_by %% AlipayServiceImpl implements AlipayService
    AlipayServiceImpl->>OmsPortalOrderService: query %% AlipayServiceImpl.query
    AlipayServiceImpl->>OmsPortalOrderService: notify %% AlipayServiceImpl.notify
    OmsPortalOrderService-->>OmsPortalOrderServiceImpl: implemented_by %% OmsPortalOrderServiceImpl implements OmsPortalOrderService
    OmsPortalOrderServiceImpl->>OmsPortalOrderServiceImpl: paySuccessByOrderSn %% OmsPortalOrderServiceImpl.paySuccessByOrderSn

```