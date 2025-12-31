@Controller
@RequestMapping("/disbExam")
public class DisbExamController{
    @Autowired
    private IReceiptAccountService receiptAccountService;

    @RequestMapping(value = "/receiptAccountQry", method = RequestMethod.GET)
    @ResponseBody
    public Object receiptAccountory(Master master, HttpservIetRequest request,@RequestParam String appLSeq) {//请求参数工具类
        RequestUtil requestUtil = RequestUtil.createRequestUtil(request, master);
        requestUtil.putValueToData("master", master);
        requestUtil.putValueToData("applSeq", applSeq);
        return receiptAccountService.receiptAccountory(requestUtil);
    }
}

public interface IReceiptAccountService {
    receiptAccountQry(RequestUtil requestUtil);
    ResponseUtil changeReceiptAccount(RequestUtil requestUtil);
}

@Component
public class ReceiptAccountServiceImpl implements IReceiptAccountService {
    @Autowired
    private ReceiptAccountAl receiptAccountAl;
    @override
    public ResponseUtil receiptAccountQry(RequestUtil requestutil) {
        DataSourceSwitch.setDataSourceType(DataSourceInstances.ORAcLE);
        return receiptAccountAl.receiptAccountQry(requestUtil);
    }
    @override
    public ResponseUtil changeReceiptAccount(RequestUtil requestutil) {
        DataSourceSwitch.setDataSourceType(DataSourceInstances.ORAcLE);
        return receiptAccountAl.changeReceiptAccount(requestUtil);
    }
}

@component
public class ReceiptAccountAl{
    private static final Logger logger = LoggerFactory.getLogger(ReceiptAccountAl.class); 
    public ResponseUtil receiptAccountQry(RequestUtil requestutil) {
        String applSeq = (String) requestUtil.getvalueFormData("applSeq");
        if (StringUtils.isBlank(applSeq)) {
            throw new BusinessException("请输入业务号");
        }
        Appl appl = applDao.selectByPrimarykey(new BigDecimal(applSeq));
        if (appl == null) {
            throw new BusinessException("未发现业务信息");
        }
        //放款卡信息 01
        ApplAccInfo applAccInfo01 = applAccInfoDao.selectBankInfoByApplSeq(appl.getApplSeq());
        if (applAccInfo01 == null) {
            throw new BusinessException("未发现收款卡信息");
        }
    }
}