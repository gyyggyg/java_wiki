```mermaid
classDiagram
    class PmsDaoTests {
        -PmsMemberPriceDao memberPriceDao
        -PmsProductDao productDao
        -static LoggerFactory.getLogger(PmsDaoTests.class)
        +testInsertBatch() void
        +testGetProductUpdateInfo() void
    }
    namespace 商城后台管理系统主程序 {
        class PmsProductDao {
            <<interface>>
            +getUpdateInfo(@Param("id")) PmsProductResult
        }
        class PmsMemberPriceDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class CmsPrefrenceAreaController {
            -CmsPrefrenceAreaService prefrenceAreaService
            +listAll() CommonResult~List~CmsPrefrenceArea~~~
        }
        class CmsPrefrenceAreaService {
            <<interface>>
            +listAll() List~CmsPrefrenceArea~
        }
        class CmsSubjectController {
            -CmsSubjectService subjectService
            +listAll() CommonResult~List~CmsSubject~~~
            +getList(@RequestParam(value,required)) CommonResult~CommonPage~CmsSubject~~~
        }
        class CmsSubjectService {
            <<interface>>
            +listAll() List~CmsSubject~
            +list(String,Integer,Integer) List~CmsSubject~
        }
        class SmsCouponController {
            -SmsCouponService couponService
            +add(@RequestBody) CommonResult
            +delete(@PathVariable) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +getItem(@PathVariable) CommonResult~SmsCouponParam~
        }
        class SmsCouponService {
            <<interface>>
            +create(SmsCouponParam) int
            +delete(Long) int
            +update(Long,SmsCouponParam) int
            +list(String,Integer,Integer,Integer) List~SmsCoupon~
            +getItem(Long) SmsCouponParam
        }
        class SmsCouponHistoryController {
            -SmsCouponHistoryService historyService
            +list(@RequestParam(value,required)) CommonResult~CommonPage~SmsCouponHistory~~~
        }
        class SmsCouponHistoryService {
            <<interface>>
            +list(Long,Integer,String,Integer,Integer) List~SmsCouponHistory~
        }
        class SmsHomeRecommendSubjectController {
            -SmsHomeRecommendSubjectService recommendSubjectService
            +create(@RequestBody) CommonResult
            +updateSort(@PathVariable,Integer) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +updateRecommendStatus(@RequestParam("ids"),@RequestParam) CommonResult
            +list(@RequestParam(value,required)) CommonResult~CommonPage~SmsHomeRecommendSubject~~~
        }
        class SmsHomeRecommendSubjectService {
            <<interface>>
            +create(List~SmsHomeRecommendSubject~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeRecommendSubject~
        }
        class SmsHomeAdvertiseController {
            -SmsHomeAdvertiseService advertiseService
            +create(@RequestBody) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +updateStatus(@PathVariable,Integer) CommonResult
            +getItem(@PathVariable) CommonResult~SmsHomeAdvertise~
            +update(@PathVariable,@RequestBody) CommonResult
            +list(@RequestParam(value,required)) CommonResult~CommonPage~SmsHomeAdvertise~~~
        }
        class SmsHomeAdvertiseService {
            <<interface>>
            +create(SmsHomeAdvertise) int
            +delete(List~Long~) int
            +updateStatus(Long,Integer) int
            +getItem(Long) SmsHomeAdvertise
            +update(Long, SmsHomeAdvertise) int
            +list(String,Integer,String,Integer,Integer) List~SmsHomeAdvertise~
        }
        class SmsHomeNewProductController {
            -SmsHomeNewProductService homeNewProductService
            +create(@RequestBody) CommonResult
            +updateSort(@PathVariable,Integer) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +updateRecommendStatus(@RequestParam("ids"),@RequestParam) CommonResult
            +list(@RequestParam(value,required)) CommonResult~CommonPage~SmsHomeNewProduct~~~
        }
        class SmsHomeNewProductService {
            <<interface>>
            +create(List~SmsHomeNewProduct~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeNewProduct~
        }
        class SmsHomeBrandController {
            -SmsHomeBrandService homeBrandService
            +create(@RequestBody) CommonResult
            +updateSort(@PathVariable,Integer) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +updateRecommendStatus(@RequestParam("ids"),@RequestParam) CommonResult
            +list(@RequestParam(value,required)) CommonResult~CommonPage~SmsHomeBrand~~~
        }
        class SmsHomeBrandService {
            <<interface>>
            +create(List~SmsHomeBrand~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeBrand~
        }
        class SmsHomeRecommendProductController {
            -SmsHomeRecommendProductService recommendProductService
            +create(@RequestBody) CommonResult
            +updateSort(@PathVariable,Integer) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +updateRecommendStatus(@RequestParam("ids"),@RequestParam) CommonResult
            +list(@RequestParam(value,required)) CommonResult~CommonPage~SmsHomeRecommendProduct~~~
        }
        class SmsHomeRecommendProductService {
            <<interface>>
            +create(List~SmsHomeRecommendProduct~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeRecommendProduct~
        }
        class UmsAdminController {
            -String tokenHeader
            -String tokenHead
            -UmsAdminService adminService
            -UmsRoleService roleService
            +register(@Validated) CommonResult~UmsAdmin~
            +login(@Validated) CommonResult
            +refreshToken(HttpServletRequest) CommonResult
            +getAdminInfo(Principal) CommonResult
            +logout(Principal) CommonResult
            +list(@RequestParam(value,required)) CommonResult~CommonPage~UmsAdmin~~~
            +getItem(@PathVariable) CommonResult~UmsAdmin~
            +update(@PathVariable,@RequestBody) CommonResult
            +updatePassword(@Validated) CommonResult
            +delete(@PathVariable) CommonResult
            +updateStatus(@PathVariable,@RequestParam(value)) CommonResult
            +updateRole(@RequestParam("adminId")) CommonResult
            +getRoleList(@PathVariable) CommonResult~List~UmsRole~~~
        }
        class UmsRoleService {
            <<interface>>
            +create(UmsRole) int
            +update(Long,UmsRole) int
            +delete(List~Long~) int
            +list() List~UmsRole~
            +list(String,Integer,Integer) List~UmsRole~
            +getMenuList(Long) List~UmsMenu~
            +listMenu(Long) List~UmsMenu~
            +listResource(Long) List~UmsResource~
            +allocMenu(Long,List~Long~) int
            +allocResource(Long,List~Long~) int
        }
        class UmsAdminService {
            <<interface>>
            +getAdminByUsername(String) UmsAdmin
            +register(UmsAdminParam) UmsAdmin
            +login(String,String) String
            +refreshToken(String) String
            +getItem(Long) UmsAdmin
            +list(String,Integer,Integer) List~UmsAdmin~
            +update(Long,UmsAdmin) int
            +delete(Long) int
            +updateRole(Long,List~Long~) int
            +getRoleList(Long) List~UmsRole~
            +getResourceList(Long) List~UmsResource~
            +updatePassword(UpdateAdminPasswordParam) int
            +loadUserByUsername(String) UserDetails
            +getCacheService() UmsAdminCacheService
            +logout(String) void
        }
        class UmsRoleController {
            -UmsRoleService roleService
            +create(@RequestBody) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +listAll() CommonResult~List~UmsRole~~~
            +list(@RequestParam(value,required)) CommonResult~CommonPage~UmsRole~~~
            +updateStatus(@PathVariable,@RequestParam(value)) CommonResult
            +listMenu(@PathVariable) CommonResult~List~UmsMenu~~~
            +listResource(@PathVariable) CommonResult~List~UmsResource~~~
            +allocMenu(@RequestParam,@RequestParam) CommonResult
            +allocResource(@RequestParam,@RequestParam) CommonResult
        }
        class UmsMenuController {
            -UmsMenuService menuService
            +create(@RequestBody) CommonResult
            +getItem(@PathVariable) CommonResult~UmsMenu~
            +delete(@PathVariable) CommonResult
            +treeList() CommonResult~List~UmsMenuNode~~~
            +updateHidden(@PathVariable,@RequestParam("hidden")) CommonResult
        }
        class UmsMenuService {
            <<interface>>
            +create(UmsMenu) int
            +update(Long,UmsMenu) int
            +getItem(Long) UmsMenu
            +delete(Long) int
            +list(Long,Integer,Integer) List~UmsMenu~
            +treeList() List~UmsMenuNode~
            +updateHidden(Long,Integer) int
        }
        class UmsResourceCategoryController {
            -UmsResourceCategoryService resourceCategoryService
            +listAll() CommonResult~List~UmsResourceCategory~~~
            +create(@RequestBody) CommonResult
            +delete(@PathVariable) CommonResult
        }
        class UmsResourceCategoryService {
            <<interface>>
            +listAll() List~UmsResourceCategory~
            +create(UmsResourceCategory) int
            +update(Long,UmsResourceCategory) int
            +delete(Long) int
        }
        class UmsResourceController {
            -UmsResourceService resourceService
            -DynamicSecurityMetadataSource dynamicSecurityMetadataSource
            +create(@RequestBody) CommonResult
            +getItem(@PathVariable) CommonResult~UmsResource~
            +delete(@PathVariable) CommonResult
            +list(@RequestParam(required)) CommonResult~CommonPage~UmsResource~~~
            +listAll() CommonResult~List~UmsResource~~~
        }
        class UmsResourceService {
            <<interface>>
            +create(UmsResource) int
            +update(Long,UmsResource) int
            +getItem(Long) UmsResource
            +delete(Long) int
            +list(Long,String,String,Integer,Integer) List~UmsResource~
            +listAll() List~UmsResource~
        }
        class UmsMemberLevelController {
            -UmsMemberLevelService memberLevelService
            +list(@RequestParam("defaultStatus")) CommonResult~List~UmsMemberLevel~~~
        }
        class UmsMemberLevelService {
            <<interface>>
            +list(Integer) List~UmsMemberLevel~
        }
        class PmsBrandController {
            -PmsBrandService brandService
            +getList() CommonResult~List~PmsBrand~~~
            +create(@Validated) CommonResult
            +update(@PathVariable("id")) CommonResult
            +delete(@PathVariable("id")) CommonResult
            +getList(@RequestParam(value,required)) CommonResult~CommonPage~PmsBrand~~~
            +getItem(@PathVariable("id")) CommonResult~PmsBrand~
            +deleteBatch(@RequestParam("ids")) CommonResult
            +updateShowStatus(@RequestParam("ids")) CommonResult
            +updateFactoryStatus(@RequestParam("ids")) CommonResult
        }
        class PmsBrandService {
            <<interface>>
            +listAllBrand() List~PmsBrand~
            +createBrand(PmsBrandParam) int
            +updateBrand(Long,PmsBrandParam) int
            +deleteBrand(Long) int
            +deleteBrand(List~Long~) int
            +listBrand(String,Integer,int,int) List~PmsBrand~
            +getBrand(Long) PmsBrand
            +updateShowStatus(List~Long~,Integer) int
            +updateFactoryStatus(List~Long~,Integer) int
        }
        class PmsProductAttributeController {
            -PmsProductAttributeService productAttributeService
            +create(@RequestBody) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +getItem(@PathVariable) CommonResult~PmsProductAttribute~
            +delete(@RequestParam("ids")) CommonResult
            +getAttrInfo(@PathVariable) CommonResult~List~ProductAttrInfo~~~
        }
        class PmsProductAttributeService {
            <<interface>>
            +getList(Long,Integer,Integer,Integer) List~PmsProductAttribute~
            +create(PmsProductAttributeParam) int
            +update(Long,PmsProductAttributeParam) int
            +getItem(Long) PmsProductAttribute
            +delete(List~Long~) int
            +getProductAttrInfo(Long) List~ProductAttrInfo~
        }
        class PmsProductCategoryController {
            -PmsProductCategoryService productCategoryService
            +create(@Validated) CommonResult
            +getItem(@PathVariable) CommonResult~PmsProductCategory~
            +delete(@PathVariable) CommonResult
            +updateNavStatus(@RequestParam("ids"),@RequestParam("navStatus")) CommonResult
            +updateShowStatus(@RequestParam("ids"),@RequestParam("showStatus")) CommonResult
            +listWithChildren() CommonResult~List~PmsProductCategoryWithChildrenItem~~~
        }
        class PmsProductCategoryService {
            <<interface>>
            +create(PmsProductCategoryParam) int
            +update(Long,PmsProductCategoryParam) int
            +getList(Long,Integer,Integer) List~PmsProductCategory~
            +delete(Long) int
            +getItem(Long) PmsProductCategory
            +updateNavStatus(List~Long~,Integer) int
            +updateShowStatus(List~Long~,Integer) int
            +listWithChildren() List~PmsProductCategoryWithChildrenItem~
        }
        class PmsProductAttributeCategoryController {
            -PmsProductAttributeCategoryService productAttributeCategoryService
            +create(@RequestParam) CommonResult
            +update(@PathVariable,@RequestParam) CommonResult
            +delete(@PathVariable) CommonResult
            +getItem(@PathVariable) CommonResult~PmsProductAttributeCategory~
            +getList(@RequestParam(defaultValue,@RequestParam(defaultValue)) CommonResult~CommonPage~PmsProductAttributeCategory~~~
            +getListWithAttr() CommonResult~List~PmsProductAttributeCategoryItem~~~
        }
        class PmsProductAttributeCategoryService {
            <<interface>>
            +create(String) int
            +update(Long,String) int
            +delete(Long) int
            +getItem(Long) PmsProductAttributeCategory
            +getList(Integer,Integer) List~PmsProductAttributeCategory~
            +getListWithAttr() List~PmsProductAttributeCategoryItem~
        }
        class PmsSkuStockController {
            -PmsSkuStockService skuStockService
            +getList(@PathVariable,@RequestParam(value,required)) CommonResult~List~PmsSkuStock~~~
            +update(@PathVariable,@RequestBody) CommonResult
        }
        class PmsSkuStockService {
            <<interface>>
            +getList(Long,String) List~PmsSkuStock~
            +update(Long,List~PmsSkuStock~) int
        }
        class PmsProductController {
            -PmsProductService productService
            +create(@RequestBody) CommonResult
            +getUpdateInfo(@PathVariable) CommonResult~PmsProductResult~
            +update(@PathVariable,@RequestBody) CommonResult
            +getList(String) CommonResult~List~PmsProduct~~~
            +updateVerifyStatus(@RequestParam("ids")) CommonResult
            +updatePublishStatus(@RequestParam("ids")) CommonResult
            +updateRecommendStatus(@RequestParam("ids")) CommonResult
            +updateNewStatus(@RequestParam("ids")) CommonResult
            +updateDeleteStatus(@RequestParam("ids")) CommonResult
        }
        class PmsProductService {
            <<interface>>
            +create(PmsProductParam) int
            +getUpdateInfo(Long) PmsProductResult
            +update(Long,PmsProductParam) int
            +list(PmsProductQueryParam,Integer,Integer) List~PmsProduct~
            +updateVerifyStatus(List~Long~,Integer,String) int
            +updatePublishStatus(List~Long~,Integer) int
            +updateRecommendStatus(List~Long~,Integer) int
            +updateNewStatus(List~Long~,Integer) int
            +updateDeleteStatus(List~Long~,Integer) int
            +list(String) List~PmsProduct~
        }
        class OmsOrderSettingController {
            -OmsOrderSettingService orderSettingService
            +getItem(@PathVariable) CommonResult~OmsOrderSetting~
            +update(@PathVariable,@RequestBody) CommonResult
        }
        class OmsOrderSettingService {
            <<interface>>
            +getItem(Long) OmsOrderSetting
            +update(Long,OmsOrderSetting) int
        }
        class OmsOrderReturnApplyController {
            -OmsOrderReturnApplyService returnApplyService
            +delete(@RequestParam("ids")) CommonResult
            +getItem(@PathVariable) CommonResult
            +updateStatus(@PathVariable,@RequestBody) CommonResult
        }
        class OmsOrderReturnApplyService {
            <<interface>>
            +list(OmsReturnApplyQueryParam,Integer,Integer) List~OmsOrderReturnApply~
            +delete(List~Long~) int
            +updateStatus(Long,OmsUpdateStatusParam) int
            +getItem(Long) OmsOrderReturnApplyResult
        }
        class OmsCompanyAddressController {
            -OmsCompanyAddressService companyAddressService
            +list() CommonResult~List~OmsCompanyAddress~~~
        }
        class OmsCompanyAddressService {
            <<interface>>
            +list() List~OmsCompanyAddress~
        }
        class OmsOrderReturnReasonController {
            -OmsOrderReturnReasonService orderReturnReasonService
            +create(@RequestBody) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +list(@RequestParam(value,defaultValue)) CommonResult~CommonPage~OmsOrderReturnReason~~~
            +getItem(@PathVariable) CommonResult~OmsOrderReturnReason~
            +updateStatus(@RequestParam(value)) CommonResult
        }
        class OmsOrderReturnReasonService {
            <<interface>>
            +create(OmsOrderReturnReason) int
            +update(Long,OmsOrderReturnReason) int
            +delete(List~Long~) int
            +list(Integer,Integer) List~OmsOrderReturnReason~
            +updateStatus(List~Long~,Integer) int
            +getItem(Long) OmsOrderReturnReason
        }
        class OmsOrderController {
            -OmsOrderService orderService
            +delivery(@RequestBody) CommonResult
            +close(@RequestParam("ids"),@RequestParam) CommonResult
            +delete(@RequestParam("ids")) CommonResult
            +detail(@PathVariable) CommonResult~OmsOrderDetail~
            +updateReceiverInfo(@RequestBody) CommonResult
            +updateReceiverInfo(@RequestBody) CommonResult
            +updateNote(@RequestParam("id")) CommonResult
        }
        class OmsOrderService {
            <<interface>>
            +list(OmsOrderQueryParam,Integer,Integer) List~OmsOrder~
            +delivery(List~OmsOrderDeliveryParam~) int
            +close(List~Long~,String) int
            +delete(List~Long~) int
            +detail(Long) OmsOrderDetail
            +updateReceiverInfo(OmsReceiverInfoParam) int
            +updateMoneyInfo(OmsMoneyInfoParam) int
            +updateNote(Long,String,Integer) int
        }
        class SmsFlashPromotionSessionController {
            -SmsFlashPromotionSessionService flashPromotionSessionService
            +create(@RequestBody) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +updateStatus(@PathVariable,Integer) CommonResult
            +delete(@PathVariable) CommonResult
            +getItem(@PathVariable) CommonResult~SmsFlashPromotionSession~
            +list() CommonResult~List~SmsFlashPromotionSession~~~
            +selectList(Long) CommonResult~List~SmsFlashPromotionSessionDetail~~~
        }
        class SmsFlashPromotionSessionService {
            <<interface>>
            +create(SmsFlashPromotionSession) int
            +update(Long,SmsFlashPromotionSession) int
            +updateStatus(Long,Integer) int
            +delete(Long) int
            +getItem(Long) SmsFlashPromotionSession
            +list() List~SmsFlashPromotionSession~
            +selectList(Long) List~SmsFlashPromotionSessionDetail~
        }
        class SmsFlashPromotionProductRelationController {
            -SmsFlashPromotionProductRelationService relationService
            +create(@RequestBody) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +delete(@PathVariable) CommonResult
            +getItem(@PathVariable) CommonResult~SmsFlashPromotionProductRelation~
            +list(@RequestParam(value)) CommonResult~CommonPage~SmsFlashPromotionProduct~~~
        }
        class SmsFlashPromotionProductRelationService {
            <<interface>>
            +create(List~SmsFlashPromotionProductRelation~) int
            +update(Long,SmsFlashPromotionProductRelation) int
            +delete(Long) int
            +getItem(Long) SmsFlashPromotionProductRelation
            +list(Long,Long,Integer,Integer) List~SmsFlashPromotionProduct~
            +getCount(Long,Long) long
        }
        class SmsFlashPromotionController {
            -SmsFlashPromotionService flashPromotionService
            +create(@RequestBody) CommonResult
            +update(@PathVariable,@RequestBody) CommonResult
            +delete(@PathVariable) CommonResult
            +update(@PathVariable,Integer) CommonResult
            +getItem(@PathVariable) CommonResult~SmsFlashPromotion~
            +getItem(@RequestParam(value,required)) CommonResult~CommonPage~SmsFlashPromotion~~~
        }
        class SmsFlashPromotionService {
            <<interface>>
            +create(SmsFlashPromotion) int
            +update(Long,SmsFlashPromotion) int
            +delete(Long) int
            +updateStatus(Long,Integer) int
            +getItem(Long) SmsFlashPromotion
            +list(String,Integer,Integer) List~SmsFlashPromotion~
        }
        class MinioController {
            -String ENDPOINT
            -String BUCKET_NAME
            -String ACCESS_KEY
            -String SECRET_KEY
            -static LoggerFactory.getLogger(MinioController.class)
            +upload(@RequestPart("file")) CommonResult
            -createBucketPolicyConfigDto(String) BucketPolicyConfigDto
            +delete(@RequestParam("objectName")) CommonResult
        }
        class MinioUploadDto {
            -String url
            -String name
        }
        class BucketPolicyConfigDto {
            -String Version
            -List~Statement~ Statement
            +static class Statement
        }
        class OssController {
            -OssService ossService
            +policy() CommonResult~OssPolicyResult~
            +callback(HttpServletRequest) CommonResult~OssCallbackResult~
        }
        class OssService {
            <<interface>>
            +policy() OssPolicyResult
            +callback(HttpServletRequest) OssCallbackResult
        }
        class PmsProductCategoryWithChildrenItem {
            -List~PmsProductCategory~ children
        }
        class PmsProductCategoryParam {
            -Long parentId
            -String name
            -String productUnit
            -Integer navStatus
            -Integer showStatus
            -Integer sort
            -String icon
            -String keywords
            -String description
            -List~Long~ productAttributeIdList
        }
        class ProductAttrInfo {
            -Long attributeId
            -Long attributeCategoryId
        }
        class PmsProductAttributeCategoryItem {
            -List~PmsProductAttribute~ productAttributeList
        }
        class PmsProductAttributeParam {
            -Long productAttributeCategoryId
            -String name
            -Integer selectType
            -Integer inputType
            -String inputList
            -Integer sort
            -Integer filterType
            -Integer searchType
            -Integer relatedStatus
            -Integer handAddStatus
            -Integer type
        }
        class UpdateAdminPasswordParam {
            -String username
            -String oldPassword
            -String newPassword
        }
        class UmsAdminLoginParam {
            -String username
            -String password
        }
        class OmsOrderReturnApplyResult {
            -OmsCompanyAddress companyAddress
        }
        class OmsUpdateStatusParam {
            -Long id
            -Long companyAddressId
            -BigDecimal returnAmount
            -String handleNote
            -String handleMan
            -String receiveNote
            -String receiveMan
            -Integer status
        }
        class OmsMoneyInfoParam {
            -Long orderId
            -BigDecimal freightAmount
            -BigDecimal discountAmount
            -Integer status
        }
        class OmsOrderDeliveryParam {
            -Long orderId
            -String deliveryCompany
            -String deliverySn
        }
        class OmsOrderQueryParam {
            -String orderSn
            -String receiverKeyword
            -Integer status
            -Integer orderType
            -Integer sourceType
            -String createTime
        }
        class OmsReceiverInfoParam {
            -Long orderId
            -String receiverName
            -String receiverPhone
            -String receiverPostCode
            -String receiverDetailAddress
            -String receiverProvince
            -String receiverCity
            -String receiverRegion
            -Integer status
        }
        class OmsReturnApplyQueryParam {
            -Long id
            -String receiverKeyword
            -Integer status
            -String createTime
            -String handleMan
            -String handleTime
        }
        class OmsOrderDetail {
            -List~OmsOrderItem~ orderItemList
            -List~OmsOrderOperateHistory~ historyList
        }
        class SmsFlashPromotionProduct {
            -PmsProduct product
        }
        class SmsFlashPromotionSessionDetail {
            -Long productCount
        }
        class UmsAdminParam {
            -String username
            -String password
            -String icon
            -String email
            -String nickName
            -String note
        }
        class PmsBrandParam {
            -String name
            -String firstLetter
            -Integer sort
            -Integer factoryStatus
            -Integer showStatus
            -String logo
            -String bigPic
            -String brandStory
        }
        class SmsCouponParam {
            -List~SmsCouponProductRelation~ productRelationList
            -List~SmsCouponProductCategoryRelation~ productCategoryRelationList
        }
        class UmsMenuNode {
            -List~UmsMenuNode~ children
        }
        class PmsProductQueryParam {
            -Integer publishStatus
            -Integer verifyStatus
            -String keyword
            -String productSn
            -Long productCategoryId
            -Long brandId
        }
        class PmsProductParam {
            -List~PmsProductLadder~ productLadderList
            -List~PmsProductFullReduction~ productFullReductionList
            -List~PmsMemberPrice~ memberPriceList
            -List~PmsSkuStock~ skuStockList
            -List~PmsProductAttributeValue~ productAttributeValueList
            -List~CmsSubjectProductRelation~ subjectProductRelationList
            -List~CmsPrefrenceAreaProductRelation~ prefrenceAreaProductRelationList
        }
        class PmsProductResult {
            -Long cateParentId
        }
        class OssPolicyResult {
            -String accessKeyId
            -String policy
            -String signature
            -String dir
            -String host
            -String callback
        }
        class OssCallbackParam {
            -String callbackUrl
            -String callbackBody
            -String callbackBodyType
        }
        class OssCallbackResult {
            -String filename
            -String size
            -String mimeType
            -String width
            -String height
        }
        class UmsMemberLevelServiceImpl {
            -UmsMemberLevelMapper memberLevelMapper
            +list(Integer) List~UmsMemberLevel~
        }
        class UmsAdminServiceImpl {
            -JwtTokenUtil jwtTokenUtil
            -PasswordEncoder passwordEncoder
            -UmsAdminMapper adminMapper
            -UmsAdminRoleRelationMapper adminRoleRelationMapper
            -UmsAdminRoleRelationDao adminRoleRelationDao
            -UmsAdminLoginLogMapper loginLogMapper
            -static LoggerFactory.getLogger(UmsAdminServiceImpl.class)
            +getAdminByUsername(String) UmsAdmin
            +register(UmsAdminParam) UmsAdmin
            +login(String,String) String
            -insertLoginLog(String) void
            -updateLoginTimeByUsername(String) void
            +refreshToken(String) String
            +getItem(Long) UmsAdmin
            +list(String,Integer,Integer) List~UmsAdmin~
            +update(Long,UmsAdmin) int
            +delete(Long) int
            +updateRole(Long,List~Long~) int
            +getRoleList(Long) List~UmsRole~
            +getResourceList(Long) List~UmsResource~
            +updatePassword(UpdateAdminPasswordParam) int
            +loadUserByUsername(String) UserDetails
            +getCacheService() UmsAdminCacheService
            +logout(String) void
        }
        class AdminUserDetails {
            -UmsAdmin umsAdmin
            -List~UmsResource~ resourceList
            +AdminUserDetails(UmsAdmin,List~UmsResource~)
            +getAuthorities() GrantedAuthority~
            +getPassword() String
            +getUsername() String
            +isAccountNonExpired() boolean
            +isAccountNonLocked() boolean
            +isCredentialsNonExpired() boolean
            +isEnabled() boolean
        }
        class UmsAdminCacheService {
            <<interface>>
            +delAdmin(Long) void
            +delResourceList(Long) void
            +delResourceListByRole(Long) void
            +delResourceListByRoleIds(List~Long~) void
            +delResourceListByResource(Long) void
            +getAdmin(String) UmsAdmin
            +setAdmin(UmsAdmin) void
            +getResourceList(Long) List~UmsResource~
            +setResourceList(Long,List~UmsResource~) void
        }
        class UmsAdminRoleRelationDao {
            <<interface>>
            +insertList(@Param("list")) int
            +getRoleList(@Param("adminId")) List~UmsRole~
            +getResourceList(@Param("adminId")) List~UmsResource~
            +getAdminIdList(@Param("resourceId")) List~Long~
        }
        class SmsHomeRecommendSubjectServiceImpl {
            -SmsHomeRecommendSubjectMapper smsHomeRecommendSubjectMapper
            +create(List~SmsHomeRecommendSubject~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeRecommendSubject~
        }
        class CmsSubjectServiceImpl {
            -CmsSubjectMapper subjectMapper
            +listAll() List~CmsSubject~
            +list(String,Integer,Integer) List~CmsSubject~
        }
        class SmsHomeNewProductServiceImpl {
            -SmsHomeNewProductMapper homeNewProductMapper
            +create(List~SmsHomeNewProduct~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeNewProduct~
        }
        class SmsHomeAdvertiseServiceImpl {
            -SmsHomeAdvertiseMapper advertiseMapper
            +create(SmsHomeAdvertise) int
            +delete(List~Long~) int
            +updateStatus(Long,Integer) int
            +getItem(Long) SmsHomeAdvertise
            +update(Long,SmsHomeAdvertise) int
            +list(String,Integer,String,Integer,Integer) List~SmsHomeAdvertise~
        }
        class SmsHomeBrandServiceImpl {
            -SmsHomeBrandMapper homeBrandMapper
            +create(List~SmsHomeBrand~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeBrand~
        }
        class SmsHomeRecommendProductServiceImpl {
            -SmsHomeRecommendProductMapper recommendProductMapper
            +create(List~SmsHomeRecommendProduct~) int
            +updateSort(Long,Integer) int
            +delete(List~Long~) int
            +updateRecommendStatus(List~Long~,Integer) int
            +list(String,Integer,Integer,Integer) List~SmsHomeRecommendProduct~
        }
        class SmsCouponServiceImpl {
            -SmsCouponMapper couponMapper
            -SmsCouponProductRelationMapper productRelationMapper
            -SmsCouponProductCategoryRelationMapper productCategoryRelationMapper
            -SmsCouponProductRelationDao productRelationDao
            -SmsCouponProductCategoryRelationDao productCategoryRelationDao
            -SmsCouponDao couponDao
            +create(SmsCouponParam) int
            +delete(Long) int
            -deleteProductCategoryRelation(Long) void
            -deleteProductRelation(Long) void
            +update(Long,SmsCouponParam) int
            +list(String,Integer,Integer,Integer) List~SmsCoupon~
            +getItem(Long) SmsCouponParam
        }
        class SmsCouponDao {
            <<interface>>
            +getItem(@Param("id")) SmsCouponParam
        }
        class SmsCouponProductRelationDao {
            <<interface>>
            +insertList(@Param("list")List~SmsCouponProductRelation~) int
        }
        class SmsCouponProductCategoryRelationDao {
            <<interface>>
            +insertList(@Param("list")List~SmsCouponProductCategoryRelation~) int
        }
        class SmsCouponHistoryServiceImpl {
            -SmsCouponHistoryMapper historyMapper
            +list(Long,Integer,String,Integer,Integer) List~SmsCouponHistory~
        }
        class PmsProductCategoryServiceImpl {
            -PmsProductCategoryMapper productCategoryMapper
            -PmsProductMapper productMapper
            -PmsProductCategoryAttributeRelationDao productCategoryAttributeRelationDao
            -PmsProductCategoryAttributeRelationMapper productCategoryAttributeRelationMapper
            -PmsProductCategoryDao productCategoryDao
            +create(PmsProductCategoryParam) int
            -insertRelationList(Long,List~Long~) void
            +update(Long,PmsProductCategoryParam) int
            +getList(Long,Integer,Integer) List~PmsProductCategory~
            +delete(Long) int
            +getItem(Long) PmsProductCategory
            +updateNavStatus(List~Long~,Integer) int
            +updateShowStatus(List~Long~,Integer) int
            +listWithChildren() List~PmsProductCategoryWithChildrenItem~
            -setCategoryLevel(PmsProductCategory) void
        }
        class PmsProductCategoryDao {
            <<interface>>
            +listWithChildren() List~PmsProductCategoryWithChildrenItem~
        }
        class PmsProductCategoryAttributeRelationDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class PmsBrandServiceImpl {
            -PmsBrandMapper brandMapper
            -PmsProductMapper productMapper
            +listAllBrand() List~PmsBrand~
            +createBrand(PmsBrandParam) int
            +updateBrand(Long,PmsBrandParam) int
            +deleteBrand(Long) int
            +deleteBrand(List~Long~) int
            +listBrand(String,Integer,int,int) List~PmsBrand~
            +getBrand(Long) PmsBrand
            +updateShowStatus(List~Long~,Integer) int
            +updateFactoryStatus(List~Long~,Integer) int
        }
        class PmsProductAttributeServiceImpl {
            -PmsProductAttributeMapper productAttributeMapper
            -PmsProductAttributeCategoryMapper productAttributeCategoryMapper
            -PmsProductAttributeDao productAttributeDao
            +getList(Long,Integer,Integer,Integer) List~PmsProductAttribute~
            +create(PmsProductAttributeParam) int
            +update(Long,PmsProductAttributeParam) int
            +getItem(Long) PmsProductAttribute
            +delete(List~Long~) int
            +getProductAttrInfo(Long) List~ProductAttrInfo~
        }
        class PmsProductAttributeDao {
            <<interface>>
            +getProductAttrInfo(@Param("id")) List~ProductAttrInfo~
        }
        class PmsProductAttributeCategoryServiceImpl {
            -PmsProductAttributeCategoryMapper productAttributeCategoryMapper
            -PmsProductAttributeCategoryDao productAttributeCategoryDao
            +create(String) int
            +update(Long,String) int
            +delete(Long) int
            +getItem(Long) PmsProductAttributeCategory
            +getList(Integer,Integer) List~PmsProductAttributeCategory~
            +getListWithAttr() List~PmsProductAttributeCategoryItem~
        }
        class PmsProductAttributeCategoryDao {
            <<interface>>
            +getListWithAttr() List~PmsProductAttributeCategoryItem~
        }
        class UmsMenuServiceImpl {
            -UmsMenuMapper menuMapper
            +create(UmsMenu) int
            -updateLevel(UmsMenu) void
            +update(Long,UmsMenu) int
            +getItem(Long) UmsMenu
            +delete(Long) int
            +list(Long,Integer,Integer) List~UmsMenu~
            +treeList() List~UmsMenuNode~
            +updateHidden(Long,Integer) int
            -covertMenuNode(UmsMenu,List~UmsMenu~) UmsMenuNode
        }
        class UmsRoleServiceImpl {
            -UmsRoleMapper roleMapper
            -UmsRoleMenuRelationMapper roleMenuRelationMapper
            -UmsRoleResourceRelationMapper roleResourceRelationMapper
            -UmsRoleDao roleDao
            -UmsAdminCacheService adminCacheService
            +create(UmsRole) int
            +update(Long,UmsRole) int
            +delete(List~Long~) int
            +list() List~UmsRole~
            +list(String,Integer,Integer) List~UmsRole~
            +getMenuList(Long) List~UmsMenu~
            +listMenu(Long) List~UmsMenu~
            +listResource(Long) List~UmsResource~
            +allocMenu(Long,List~Long~) int
            +allocResource(Long,List~Long~) int
        }
        class UmsRoleDao {
            <<interface>>
            +getMenuList(@Param("adminId")) List~UmsMenu~
            +getMenuListByRoleId(@Param("roleId")) List~UmsMenu~
            +getResourceListByRoleId(@Param("roleId")) List~UmsResource~
        }
        class UmsAdminCacheServiceImpl {
            -UmsAdminService adminService
            -RedisService redisService
            -UmsAdminRoleRelationMapper adminRoleRelationMapper
            -UmsAdminRoleRelationDao adminRoleRelationDao
            -String REDIS_DATABASE
            -Long REDIS_EXPIRE
            -String REDIS_KEY_ADMIN
            -String REDIS_KEY_RESOURCE_LIST
            +delAdmin(Long) void
            +delResourceList(Long) void
            +delResourceListByRole(Long) void
            +delResourceListByRoleIds(List~Long~) void
            +delResourceListByResource(Long) void
            +getAdmin(String) UmsAdmin
            +setAdmin(UmsAdmin) void
            +getResourceList(Long) List~UmsResource~
            +setResourceList(Long,List~UmsResource~) void
        }
        class UmsResourceServiceImpl {
            -UmsResourceMapper resourceMapper
            -UmsAdminCacheService adminCacheService
            +create(UmsResource) int
            +update(Long,UmsResource) int
            +getItem(Long) UmsResource
            +delete(Long) int
            +list(Long,String,String,Integer,Integer) List~UmsResource~
            +listAll() List~UmsResource~
        }
        class UmsResourceCategoryServiceImpl {
            -UmsResourceCategoryMapper resourceCategoryMapper
            +listAll() List~UmsResourceCategory~
            +create(UmsResourceCategory) int
            +update(Long,UmsResourceCategory) int
            +delete(Long) int
        }
        class OmsOrderSettingServiceImpl {
            -OmsOrderSettingMapper orderSettingMapper
            +getItem(Long) OmsOrderSetting
            +update(Long,OmsOrderSetting) int
        }
        class OssServiceImpl {
            -int ALIYUN_OSS_EXPIRE
            -int ALIYUN_OSS_MAX_SIZE
            -String ALIYUN_OSS_CALLBACK
            -String ALIYUN_OSS_BUCKET_NAME
            -String ALIYUN_OSS_ENDPOINT
            -String ALIYUN_OSS_DIR_PREFIX
            -OSSClient ossClient
            -static LoggerFactory.getLogger(OssServiceImpl.class)
            +policy() OssPolicyResult
            +callback(HttpServletRequest) OssCallbackResult
        }
        class PmsProductServiceImpl {
            -PmsProductMapper productMapper
            -PmsMemberPriceDao memberPriceDao
            -PmsMemberPriceMapper memberPriceMapper
            -PmsProductLadderDao productLadderDao
            -PmsProductLadderMapper productLadderMapper
            -PmsProductFullReductionDao productFullReductionDao
            -PmsProductFullReductionMapper productFullReductionMapper
            -PmsSkuStockDao skuStockDao
            -PmsSkuStockMapper skuStockMapper
            -PmsProductAttributeValueDao productAttributeValueDao
            -PmsProductAttributeValueMapper productAttributeValueMapper
            -CmsSubjectProductRelationDao subjectProductRelationDao
            -CmsSubjectProductRelationMapper subjectProductRelationMapper
            -CmsPrefrenceAreaProductRelationDao prefrenceAreaProductRelationDao
            -CmsPrefrenceAreaProductRelationMapper prefrenceAreaProductRelationMapper
            -PmsProductDao productDao
            -PmsProductVertifyRecordDao productVertifyRecordDao
            -static LoggerFactory.getLogger(PmsProductServiceImpl.class)
            +create(PmsProductParam) int
            -handleSkuStockCode(List~PmsSkuStock~,Long) void
            +getUpdateInfo(Long) PmsProductResult
            +update(Long,PmsProductParam) int
            -handleUpdateSkuStockList(Long,PmsProductParam) void
            +list(PmsProductQueryParam,Integer,Integer) List~PmsProduct~
            +updateVerifyStatus(List~Long~,Integer,String) int
            +updatePublishStatus(List~Long~,Integer) int
            +updateRecommendStatus(List~Long~,Integer) int
            +updateNewStatus(List~Long~,Integer) int
            +updateDeleteStatus(List~Long~,Integer) int
            +list(String) List~PmsProduct~
            -relateAndInsertList(Object,List,Long) void
        }
        class PmsProductVertifyRecordDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class PmsSkuStockServiceImpl {
            -PmsSkuStockMapper skuStockMapper
            -PmsSkuStockDao skuStockDao
            +getList(Long,String) List~PmsSkuStock~
            +update(Long,List~PmsSkuStock~) int
        }
        class PmsSkuStockDao {
            <<interface>>
            +insertList(@Param("list")List~PmsSkuStock~) int
            +replaceList(@Param("list")List~PmsSkuStock~) int
        }
        class OmsCompanyAddressServiceImpl {
            -OmsCompanyAddressMapper companyAddressMapper
            +list() List~OmsCompanyAddress~
        }
        class CmsPrefrenceAreaServiceImpl {
            -CmsPrefrenceAreaMapper prefrenceAreaMapper
            +listAll() List~CmsPrefrenceArea~
        }
        class OmsOrderServiceImpl {
            -OmsOrderMapper orderMapper
            -OmsOrderDao orderDao
            -OmsOrderOperateHistoryDao orderOperateHistoryDao
            -OmsOrderOperateHistoryMapper orderOperateHistoryMapper
            +list(OmsOrderQueryParam,Integer,Integer) List~OmsOrder~
            +delivery(List~OmsOrderDeliveryParam~) int
            +close(List~Long~,String) int
            +delete(List~Long~) int
            +detail(Long) OmsOrderDetail
            +updateReceiverInfo(OmsReceiverInfoParam) int
            +updateMoneyInfo(OmsMoneyInfoParam) int
            +updateNote(Long,String,Integer) int
        }
        class OmsOrderOperateHistoryDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class OmsOrderDao {
            <<interface>>
            +getList(@Param("queryParam")) List~OmsOrder~
            +delivery(@Param("list")) int
            +getDetail(@Param("id")) OmsOrderDetail
        }
        class OmsOrderReturnReasonServiceImpl {
            -OmsOrderReturnReasonMapper returnReasonMapper
            +create(OmsOrderReturnReason) int
            +update(Long,OmsOrderReturnReason) int
            +delete(List~Long~) int
            +list(Integer,Integer) List~OmsOrderReturnReason~
            +updateStatus(List~Long~,Integer) int
            +getItem(Long) OmsOrderReturnReason
        }
        class OmsOrderReturnApplyServiceImpl {
            -OmsOrderReturnApplyDao returnApplyDao
            -OmsOrderReturnApplyMapper returnApplyMapper
            +list(OmsReturnApplyQueryParam,Integer,Integer) List~OmsOrderReturnApply~
            +delete(List~Long~) int
            +updateStatus(Long,OmsUpdateStatusParam) int
            +getItem(Long) OmsOrderReturnApplyResult
        }
        class OmsOrderReturnApplyDao {
            <<interface>>
            +getList(@Param("queryParam")) List~OmsOrderReturnApply~
            +getDetail(@Param("id")Long) OmsOrderReturnApplyResult
        }
        class SmsFlashPromotionServiceImpl {
            -SmsFlashPromotionMapper flashPromotionMapper
            +create(SmsFlashPromotion) int
            +update(Long,SmsFlashPromotion) int
            +delete(Long) int
            +updateStatus(Long,Integer) int
            +getItem(Long) SmsFlashPromotion
            +list(String,Integer,Integer) List~SmsFlashPromotion~
        }
        class SmsFlashPromotionProductRelationServiceImpl {
            -SmsFlashPromotionProductRelationMapper relationMapper
            -SmsFlashPromotionProductRelationDao relationDao
            +create(List~SmsFlashPromotionProductRelation~) int
            +update(Long,SmsFlashPromotionProductRelation) int
            +delete(Long) int
            +getItem(Long) SmsFlashPromotionProductRelation
            +list(Long,Long,Integer,Integer) List~SmsFlashPromotionProduct~
            +getCount(Long,Long) long
        }
        class SmsFlashPromotionProductRelationDao {
            <<interface>>
            +getList(@Param("flashPromotionId"),@Param("flashPromotionSessionId")) List~SmsFlashPromotionProduct~
        }
        class SmsFlashPromotionSessionServiceImpl {
            -SmsFlashPromotionSessionMapper promotionSessionMapper
            -SmsFlashPromotionProductRelationService relationService
            +create(SmsFlashPromotionSession) int
            +update(Long,SmsFlashPromotionSession) int
            +updateStatus(Long,Integer) int
            +delete(Long) int
            +getItem(Long) SmsFlashPromotionSession
            +list() List~SmsFlashPromotionSession~
            +selectList(Long) List~SmsFlashPromotionSessionDetail~
        }
        class PmsProductFullReductionDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class CmsSubjectProductRelationDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class CmsPrefrenceAreaProductRelationDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class PmsProductAttributeValueDao {
            <<interface>>
            +insertList(@Param("list")List~PmsProductAttributeValue~) int
        }
        class PmsProductLadderDao {
            <<interface>>
            +insertList(@Param("list")) int
        }
        class GlobalCorsConfig {
            +corsFilter() CorsFilter
        }
        class OssConfig {
            -String ALIYUN_OSS_ENDPOINT
            -String ALIYUN_OSS_ACCESSKEYID
            -String ALIYUN_OSS_ACCESSKEYSECRET
            +ossClient() OSSClient
        }
        class MyBatisConfig {
        }
        class SwaggerConfig {
            +swaggerProperties() SwaggerProperties
            +springfoxHandlerProviderBeanPostProcessor() BeanPostProcessor
        }
        class MallSecurityConfig {
            -UmsAdminService adminService
            -UmsResourceService resourceService
            +userDetailsService() UserDetailsService
            +dynamicSecurityService() DynamicSecurityService
        }
        class FlagValidatorClass {
            -String[] values
            +initialize(FlagValidator) void
            +isValid(Integer,ConstraintValidatorContext) boolean
        }
        class MallAdminApplication {
            +main(String[]) void
        }
    }
    PmsDaoTests --> PmsProductDao
    PmsDaoTests --> PmsMemberPriceDao
    PmsProductDao --> PmsProductResult
    CmsPrefrenceAreaController --> CmsPrefrenceAreaService
    CmsSubjectController --> CmsSubjectService
    SmsCouponController --> SmsCouponService
    SmsCouponService --> SmsCouponParam
    SmsCouponHistoryController --> SmsCouponHistoryService
    SmsHomeRecommendSubjectController --> SmsHomeRecommendSubjectService
    SmsHomeAdvertiseController --> SmsHomeAdvertiseService
    SmsHomeNewProductController --> SmsHomeNewProductService
    SmsHomeBrandController --> SmsHomeBrandService
    SmsHomeRecommendProductController --> SmsHomeRecommendProductService
    UmsAdminController --> UmsRoleService
    UmsAdminController --> UmsAdminService
    UmsRoleController --> UmsRoleService
    UmsMenuController --> UmsMenuService
    UmsResourceCategoryController --> UmsResourceCategoryService
    UmsResourceController --> UmsResourceService
    UmsMemberLevelController --> UmsMemberLevelService
    PmsBrandController --> PmsBrandService
    PmsProductAttributeController --> PmsProductAttributeService
    PmsProductCategoryController --> PmsProductCategoryService
    PmsProductAttributeCategoryController --> PmsProductAttributeCategoryService
    PmsSkuStockController --> PmsSkuStockService
    PmsProductController --> PmsProductService
    OmsOrderSettingController --> OmsOrderSettingService
    OmsOrderReturnApplyController --> OmsOrderReturnApplyService
    OmsCompanyAddressController --> OmsCompanyAddressService
    OmsOrderReturnReasonController --> OmsOrderReturnReasonService
    OmsOrderController --> OmsOrderService
    SmsFlashPromotionSessionController --> SmsFlashPromotionSessionService
    SmsFlashPromotionProductRelationController --> SmsFlashPromotionProductRelationService
    SmsFlashPromotionController --> SmsFlashPromotionService
    MinioController --> MinioUploadDto
    MinioController --> BucketPolicyConfigDto
    OssController --> OssService
    OssService --> OssCallbackResult
    OssService --> OssPolicyResult
    PmsProductResult <|-- PmsProductParam
    UmsMemberLevelServiceImpl <|.. UmsMemberLevelService
    UmsAdminServiceImpl <|.. UmsAdminService
    UmsAdminServiceImpl --> AdminUserDetails
    UmsAdminServiceImpl --> UmsAdminCacheService
    UmsAdminServiceImpl --> UmsAdminRoleRelationDao
    UmsAdminCacheServiceImpl <|.. UmsAdminCacheService
    UmsAdminCacheServiceImpl --> UmsAdminService
    UmsAdminCacheServiceImpl --> UmsAdminRoleRelationDao
    UmsRoleServiceImpl <|.. UmsRoleService
    UmsRoleServiceImpl --> UmsAdminCacheService
    UmsRoleServiceImpl --> UmsRoleDao
    UmsMenuServiceImpl <|.. UmsMenuService
    UmsResourceServiceImpl <|.. UmsResourceService
    UmsResourceServiceImpl --> UmsAdminCacheService
    UmsResourceCategoryServiceImpl <|.. UmsResourceCategoryService
    PmsProductCategoryServiceImpl <|.. PmsProductCategoryService
    PmsProductCategoryServiceImpl --> PmsProductCategoryDao
    PmsProductCategoryServiceImpl --> PmsProductCategoryAttributeRelationDao
    PmsBrandServiceImpl <|.. PmsBrandService
    PmsProductAttributeServiceImpl <|.. PmsProductAttributeService
    PmsProductAttributeServiceImpl --> PmsProductAttributeDao
    PmsProductAttributeCategoryServiceImpl <|.. PmsProductAttributeCategoryService
    PmsProductAttributeCategoryServiceImpl --> PmsProductAttributeCategoryDao
    SmsCouponServiceImpl <|.. SmsCouponService
    SmsCouponServiceImpl --> SmsCouponDao
    SmsCouponServiceImpl --> SmsCouponProductRelationDao
    SmsCouponServiceImpl --> SmsCouponProductCategoryRelationDao
    SmsCouponServiceImpl --> SmsCouponParam
    SmsCouponHistoryServiceImpl <|.. SmsCouponHistoryService
    SmsHomeRecommendSubjectServiceImpl <|.. SmsHomeRecommendSubjectService
    CmsSubjectServiceImpl <|.. CmsSubjectService
    SmsHomeNewProductServiceImpl <|.. SmsHomeNewProductService
    SmsHomeAdvertiseServiceImpl <|.. SmsHomeAdvertiseService
    SmsHomeBrandServiceImpl <|.. SmsHomeBrandService
    SmsHomeRecommendProductServiceImpl <|.. SmsHomeRecommendProductService
    PmsProductServiceImpl <|.. PmsProductService
    PmsProductServiceImpl --> PmsProductDao
    PmsProductServiceImpl --> PmsProductVertifyRecordDao
    PmsProductServiceImpl --> PmsProductResult
    PmsSkuStockServiceImpl <|.. PmsSkuStockService
    PmsSkuStockServiceImpl --> PmsSkuStockDao
    OmsOrderServiceImpl <|.. OmsOrderService
    OmsOrderServiceImpl --> OmsOrderOperateHistoryDao
    OmsOrderServiceImpl --> OmsOrderDao
    OmsOrderServiceImpl --> OmsOrderDetail
    OmsCompanyAddressServiceImpl <|.. OmsCompanyAddressService
    CmsPrefrenceAreaServiceImpl <|.. CmsPrefrenceAreaService
    OmsOrderReturnReasonServiceImpl <|.. OmsOrderReturnReasonService
    OmsOrderReturnApplyServiceImpl <|.. OmsOrderReturnApplyService
    OmsOrderReturnApplyServiceImpl --> OmsOrderReturnApplyDao
    OmsOrderReturnApplyServiceImpl --> OmsOrderReturnApplyResult
    OmsOrderReturnApplyDao --> OmsOrderReturnApplyResult
    SmsFlashPromotionServiceImpl <|.. SmsFlashPromotionService
    SmsFlashPromotionProductRelationServiceImpl <|.. SmsFlashPromotionProductRelationService
    SmsFlashPromotionProductRelationServiceImpl --> SmsFlashPromotionProductRelationDao
    SmsFlashPromotionSessionServiceImpl <|.. SmsFlashPromotionSessionService
    SmsFlashPromotionSessionServiceImpl --> SmsFlashPromotionProductRelationService
    SmsFlashPromotionSessionServiceImpl --> SmsFlashPromotionSessionDetail
    OssServiceImpl <|.. OssService
    OssServiceImpl --> OssCallbackResult
    OssServiceImpl --> OssPolicyResult
    OssServiceImpl --> OssCallbackParam
    PmsProductResult <|-- PmsProductParam
    OmsOrderReturnApplyResult <|-- OmsOrderReturnApply
    OmsOrderDao --> OmsOrderDetail
    OmsOrderService --> OmsOrderDetail
    OmsOrderReturnApplyService --> OmsOrderReturnApplyResult
    SmsCouponService --> SmsCouponParam
    PmsProductService --> PmsProductResult

```
## 第一部分：整体概述

该模块自身直接实现了`PmsDaoTests`这一核心类，该类主要负责对产品相关DAO的测试。该核心类与“商城后台管理系统主程序”模块中的数据访问对象（如`PmsProductDao`和`PmsMemberPriceDao`）存在直接依赖关系。整体上，模块通过顶层测试类与底层DAO接口协作，实现对数据层的功能验证和集成测试。

## 第二部分：关联子模块中的类说明

### 商城后台管理系统主程序模块

- **PmsProductDao**：负责产品数据的访问，提供如`getUpdateInfo`等方法以供业务层或测试层查询产品的更新信息。被直接依赖用于查询产品详细数据。
- **PmsMemberPriceDao**：负责会员价格相关的数据批量插入操作，为产品定价相关的业务提供数据支撑。被直接依赖用于批量插入会员价格数据。
- **CmsPrefrenceAreaController**：管理后台优选专区的接口入口，通过调用`CmsPrefrenceAreaService`实现专区列表的查询。被依赖用于专区相关功能的测试和集成。
- **CmsPrefrenceAreaService**：定义专区相关的数据查询接口，实际由实现类完成数据获取。供控制层调用以获取专区数据。
- **CmsSubjectController**：主题管理的控制器，负责主题列表与分页查询，核心方法为`listAll`和`getList`。被依赖以测试主题相关的接口交互。
- **CmsSubjectService**：主题相关的服务接口，为控制器提供主题数据的查询能力。被依赖以支持主题的业务操作。
- **SmsCouponController**：优惠券控制器，负责创建、更新、查询、删除优惠券，主要调用`SmsCouponService`实现业务。被依赖以模拟和验证优惠券业务流程。
- **SmsCouponService**：定义优惠券业务的操作接口，如创建、更新、查询等，核心返回对象为`SmsCouponParam`。被依赖以支撑优惠券相关的业务逻辑和数据处理。
- **SmsCouponHistoryController**：优惠券历史记录控制器，负责分页查询优惠券使用历史。被依赖以测试优惠券历史相关接口。
- **SmsCouponHistoryService**：定义优惠券历史记录的查询接口，供控制器调用用于获取历史数据。
- **SmsHomeRecommendSubjectController**：首页推荐专题控制器，负责推荐专题的增删改查与排序、推荐状态设置。被依赖以支持首页推荐专题管理的业务流程。
- **SmsHomeRecommendSubjectService**：推荐专题相关的服务接口，供控制器进行推荐专题维护操作。
- **SmsHomeAdvertiseController**：首页广告控制器，负责广告的增删改查与状态变更。被依赖以支撑首页广告管理。
- **SmsHomeAdvertiseService**：首页广告的服务接口，负责广告数据的操作和查询，支撑广告相关业务。
- **SmsHomeNewProductController**：新品推荐控制器，负责新品推荐的增删改查与排序、推荐状态设置。被依赖以支撑新品推荐相关的测试与业务流程。
- **SmsHomeNewProductService**：新品推荐服务接口，供控制器调用以维护新品推荐列表。
- **SmsHomeBrandController**：品牌推荐控制器，负责品牌推荐的增删改查与推荐状态设置。被依赖以支持品牌推荐管理。
- **SmsHomeBrandService**：品牌推荐相关服务接口，供控制器进行品牌推荐维护。
- **SmsHomeRecommendProductController**：推荐产品控制器，负责推荐产品的增删改查及排序、推荐状态设置。被依赖以支撑首页推荐产品管理相关测试与业务。
- **SmsHomeRecommendProductService**：推荐产品相关服务接口，供控制器进行推荐产品操作。
- **UmsAdminController**：后台管理员的控制器，负责用户注册、登录、信息获取、权限和角色管理等功能，依赖`UmsAdminService`和`UmsRoleService`。被依赖以支撑后台用户管理业务流程。
- **UmsRoleService**：定义角色相关业务接口，如角色的增删改查、菜单和资源分配。被依赖以实现权限管理功能。
- **UmsAdminService**：后台管理员相关的服务接口，负责用户认证、注册、权限、角色、资源等一系列后台管理动作。被依赖以支撑后台账号业务。
- **UmsRoleController**：角色管理控制器，负责角色的增删改查、菜单和资源分配等接口。被依赖以支持后台权限管理相关测试。
- **UmsMenuController**：菜单管理的控制器，负责菜单的增删改查和树形结构查询等接口。被依赖以支持菜单管理相关功能。
- **UmsMenuService**：定义菜单相关的业务接口，如菜单的增删改查、树形结构获取等。被依赖以支撑菜单管理。
- **UmsResourceCategoryController**：资源分类管理的控制器，负责资源分类的增删改查。被依赖以支撑资源分类管理的测试与业务。
- **UmsResourceCategoryService**：资源分类相关服务接口，供控制器维护资源分类数据。
- **UmsResourceController**：资源管理控制器，负责资源的增删改查及列表查询。被依赖以支撑资源管理相关的业务和测试。
- **UmsResourceService**：资源相关的服务接口，供控制器进行资源数据操作。
- **UmsMemberLevelController**：会员等级控制器，负责会员等级的列表查询。被依赖以支持会员等级功能测试。
- **UmsMemberLevelService**：会员等级相关服务接口，供控制器查询会员等级数据。
- **PmsBrandController**：品牌管理控制器，负责品牌的增删改查、显示状态和工厂状态管理。被依赖以测试品牌相关业务。
- **PmsBrandService**：品牌相关服务接口，供控制器维护品牌数据和状态。
- **PmsProductAttributeController**：商品属性控制器，负责商品属性的增删改查及属性信息查询。被依赖以支撑商品属性相关接口的业务。
- **PmsProductAttributeService**：商品属性相关服务接口，供控制器维护商品属性数据。
- **PmsProductCategoryController**：商品分类控制器，负责商品分类的增删改查、显示/导航状态设置及分类树查询。被依赖以支持商品分类管理。
- **PmsProductCategoryService**：商品分类相关服务接口，供控制器进行分类维护与查询。
- **PmsProductAttributeCategoryController**：商品属性分类控制器，负责属性分类的增删改查及带属性的分类列表查询。被依赖以测试属性分类相关功能。
- **PmsProductAttributeCategoryService**：商品属性分类相关服务接口，供控制器维护属性分类与其属性。
- **PmsSkuStockController**：SKU库存控制器，负责SKU库存的查询和批量更新。被依赖以支撑SKU库存相关业务。
- **PmsSkuStockService**：SKU库存相关服务接口，供控制器进行库存数据维护。
- **PmsProductController**：商品管理控制器，负责商品的增删改查、状态变更及商品详细信息获取。被依赖以测试商品全流程业务。
- **PmsProductService**：商品相关服务接口，供控制器实现商品的业务处理和数据操作。
- **OmsOrderSettingController**：订单设置控制器，负责订单配置信息的查询与更新。被依赖以支撑订单设置功能测试。
- **OmsOrderSettingService**：订单设置相关服务接口，供控制器维护订单配置信息。
- **OmsOrderReturnApplyController**：退货申请控制器，负责退货申请的查询、删除和状态更新。被依赖以测试退货业务流程。
- **OmsOrderReturnApplyService**：退货申请相关服务接口，供控制器查询和修改退货申请信息。
- **OmsCompanyAddressController**：公司收货地址控制器，负责收货地址列表查询。被依赖以支持退货及物流相关测试。
- **OmsCompanyAddressService**：公司收货地址相关服务接口，供控制器获取地址数据。
- **OmsOrderReturnReasonController**：退货原因控制器，负责退货原因的增删改查及状态管理。被依赖以支撑退货原因管理测试。
- **OmsOrderReturnReasonService**：退货原因相关服务接口，供控制器维护退货原因数据。
- **OmsOrderController**：订单管理控制器，负责订单的各类操作（发货、关闭、删除、详情、收货人信息、备注等）。被依赖以测试订单全流程业务。
- **OmsOrderService**：订单相关服务接口，供控制器实现订单业务处理。
- **SmsFlashPromotionSessionController**：秒杀时间段控制器，负责秒杀活动时间段的管理与详情查询。被依赖以支撑秒杀活动相关测试。
- **SmsFlashPromotionSessionService**：秒杀时间段相关服务接口，供控制器维护活动时间段数据。
- **SmsFlashPromotionProductRelationController**：秒杀活动商品关联控制器，负责活动商品的增删改查及详情、列表查询。被依赖以测试秒杀活动商品逻辑。
- **SmsFlashPromotionProductRelationService**：秒杀活动商品关联服务接口，供控制器维护活动商品关联数据。
- **SmsFlashPromotionController**：秒杀活动管理控制器，负责秒杀活动的增删改查及状态管理。被依赖以支撑秒杀活动相关业务。
- **SmsFlashPromotionService**：秒杀活动相关服务接口，供控制器维护秒杀活动数据。
- **MinioController**：Minio对象存储控制器，负责文件上传、删除、桶策略配置等操作。被依赖以支持文件存储相关功能。
- **MinioUploadDto**：用于封装Minio上传返回的文件信息。被控制器用于封装响应数据。
- **BucketPolicyConfigDto**：用于描述Minio桶的策略配置，控制文件访问权限。被控制器用于生成和返回策略配置。
- **OssController**：阿里云OSS控制器，负责获取上传策略和回调处理。被依赖以实现OSS上传相关业务。
- **OssService**：OSS相关的服务接口，供控制器获取上传策略和处理回调。返回上传策略和回调结果相关的对象。
- **PmsProductCategoryWithChildrenItem**：用于表示带有子分类的商品分类结构，支撑分类树查询。被依赖以实现商品分类树形结构的数据展示。
- **PmsProductCategoryParam**：商品分类参数对象，用于商品分类的创建和更新。被相关服务或控制器用于封装请求参数。
- **ProductAttrInfo**：商品属性简要信息对象，用于属性相关的查询和展示。被依赖以支撑属性信息联动功能。
- **PmsProductAttributeCategoryItem**：带属性的属性分类对象，用于属性分类及其下属属性的联合查询。被依赖以实现属性分类和属性一体化展示。
- **PmsProductAttributeParam**：商品属性参数对象，用于商品属性的创建和更新。被相关服务或控制器作为参数对象使用。
- **UpdateAdminPasswordParam**：管理员密码修改参数对象，封装修改密码的请求参数。被依赖以支撑用户密码修改功能。
- **UmsAdminLoginParam**：管理员登录参数对象，封装登录请求的数据。被依赖以支撑登录功能。
- **OmsOrderReturnApplyResult**：退货申请扩展对象，包含公司收货地址等详细信息。被依赖以实现退货申请详情查询。
- **OmsUpdateStatusParam**、**OmsMoneyInfoParam**、**OmsOrderDeliveryParam**、**OmsOrderQueryParam**、**OmsReceiverInfoParam**、**OmsReturnApplyQueryParam**：各类订单相关参数对象，支撑订单、退货等业务的数据传递。
- **OmsOrderDetail**：订单详情对象，包含订单项及操作历史，支撑订单详细信息展示。
- **SmsFlashPromotionProduct**、**SmsFlashPromotionSessionDetail**：扩展秒杀活动相关对象，用于活动商品和时间段的详细展示。
- **UmsAdminParam**、**PmsBrandParam**、**SmsCouponParam**、**UmsMenuNode**、**PmsProductQueryParam**、**PmsProductParam**、**PmsProductResult**、**OssPolicyResult**、**OssCallbackParam**、**OssCallbackResult**：各类业务参数/结果/扩展对象，为业务流程和数据展示提供结构化支撑。
- **UmsMemberLevelServiceImpl** 等 `*Impl` 实现类：上述接口的具体实现，负责与数据库或其他服务的实际交互，通常被控制器或服务层依赖调用。
- **AdminUserDetails**：封装管理员信息及权限，用于Spring Security权限认证流程。
- **UmsAdminCacheService** 及其实现 `UmsAdminCacheServiceImpl`：负责管理员及其权限的缓存操作，提高系统性能。
- **UmsAdminRoleRelationDao**、**SmsCouponDao**、**PmsProductCategoryDao** 等 `*Dao`：负责与数据库的直接交互，供服务层或实现类调用，支撑批量操作和联合查询等需求。

## 第三部分：关系线逐条解读

- `PmsDaoTests --> PmsProductDao`：`PmsDaoTests`测试类通过依赖`PmsProductDao`实现对产品数据查询方法的验证。
- `PmsDaoTests --> PmsMemberPriceDao`：`PmsDaoTests`通过依赖`PmsMemberPriceDao`测试会员价格数据的批量插入功能。
- `PmsProductDao --> PmsProductResult`：`PmsProductDao`的数据查询方法返回`PmsProductResult`对象，封装了产品详细信息。
- `CmsPrefrenceAreaController --> CmsPrefrenceAreaService`：控制器通过依赖服务接口，从业务层获取专区数据实现接口响应。
- `CmsSubjectController --> CmsSubjectService`：主题控制器调用服务层接口获取主题数据，用于主题管理功能。
- `SmsCouponController --> SmsCouponService`：优惠券控制器通过服务接口实现对优惠券的增删改查业务。
- `SmsCouponService --> SmsCouponParam`：服务层方法返回`SmsCouponParam`对象，用于传递优惠券详细数据。
- `SmsCouponHistoryController --> SmsCouponHistoryService`：历史记录控制器依赖服务层获取分页后的优惠券使用历史数据。
- `SmsHomeRecommendSubjectController --> SmsHomeRecommendSubjectService`：推荐专题控制器通过服务接口完成专题的管理和查询。
- `SmsHomeAdvertiseController --> SmsHomeAdvertiseService`：广告控制器依赖服务层，实现广告的各项业务操作。
- `SmsHomeNewProductController --> SmsHomeNewProductService`：新品推荐控制器通过服务接口完成新品推荐列表的维护和查询。
- `SmsHomeBrandController --> SmsHomeBrandService`：品牌推荐控制器调用服务层接口，实现推荐品牌的管理。
- `SmsHomeRecommendProductController --> SmsHomeRecommendProductService`：推荐产品控制器通过服务接口进行推荐商品的增删改查及状态管理。
- `UmsAdminController --> UmsRoleService`：管理员控制器依赖角色服务，实现管理员与角色相关的业务。
- `UmsAdminController --> UmsAdminService`：管理员控制器通过服务接口实现后台管理员的注册、登录、权限分配等功能。
- `UmsRoleController --> UmsRoleService`：角色控制器调用服务层接口实现角色管理及权限分配等操作。
- `UmsMenuController --> UmsMenuService`：菜单控制器通过服务接口管理后台菜单数据。
- `UmsResourceCategoryController --> UmsResourceCategoryService`：资源分类控制器依赖服务层实现资源分类的维护。
- `UmsResourceController --> UmsResourceService`：资源控制器通过服务接口实现资源的增删改查及列表查询。
- `UmsMemberLevelController --> UmsMemberLevelService`：会员等级控制器依赖服务层实现会员等级的查询功能。
- `PmsBrandController --> PmsBrandService`：品牌控制器通过服务接口实现品牌数据的维护。
- `PmsProductAttributeController --> PmsProductAttributeService`：商品属性控制器通过服务接口管理商品属性及相关信息。
- `PmsProductCategoryController --> PmsProductCategoryService`：商品分类控制器通过服务接口实现分类的维护与树形结构查询。
- `PmsProductAttributeCategoryController --> PmsProductAttributeCategoryService`：商品属性分类控制器通过服务接口管理属性分类及其属性。
- `PmsSkuStockController --> PmsSkuStockService`：SKU库存控制器通过服务接口实现库存查询与维护。
- `PmsProductController --> PmsProductService`：商品控制器通过服务接口对商品的各类业务进行操作。
- `OmsOrderSettingController --> OmsOrderSettingService`：订单设置控制器通过服务接口实现订单配置信息的维护。
- `OmsOrderReturnApplyController --> OmsOrderReturnApplyService`：退货申请控制器依赖服务层实现退货申请的数据操作与状态维护。
- `OmsCompanyAddressController --> OmsCompanyAddressService`：公司收货地址控制器通过服务层接口查询收货地址数据。
- `OmsOrderReturnReasonController --> OmsOrderReturnReasonService`：退货原因控制器通过服务接口实现退货原因的维护。
- `OmsOrderController --> OmsOrderService`：订单控制器通过服务接口进行订单的各类操作。
- `SmsFlashPromotionSessionController --> SmsFlashPromotionSessionService`：秒杀时间段控制器通过服务接口管理活动时间段和查询详情。
- `SmsFlashPromotionProductRelationController --> SmsFlashPromotionProductRelationService`：活动商品关联控制器通过服务接口管理商品与活动的关联关系。
- `SmsFlashPromotionController --> SmsFlashPromotionService`：秒杀活动控制器通过服务接口管理活动的增删改查及状态。
- `MinioController --> MinioUploadDto`：Minio控制器操作中封装文件上传结果为`MinioUploadDto`对象。
- `MinioController --> BucketPolicyConfigDto`：Minio控制器创建和返回桶策略配置对象`BucketPolicyConfigDto`，用于描述文件访问权限。
- `OssController --> OssService`：OSS控制器通过服务接口实现上传策略获取及回调处理功能。
- `OssService --> OssCallbackResult`：OSS服务的回调处理方法返回`OssCallbackResult`对象，封装回调结果信息。
- `OssService --> OssPolicyResult`：OSS服务的方法返回`OssPolicyResult`对象，描述上传策略的关键信息。
- `PmsProductResult <|-- PmsProductParam`：`PmsProductParam`继承自`PmsProductResult`，用于扩展和封装产品参数，便于数据传递和复用。
- `UmsMemberLevelServiceImpl <|.. UmsMemberLevelService`：`UmsMemberLevelServiceImpl`实现了`UmsMemberLevelService`接口，实现类与接口分离有助于解耦与扩展。
- `UmsAdminServiceImpl <|.. UmsAdminService`：`UmsAdminServiceImpl`实现接口，便于业务层与实现层解耦，支持多种实现方式。
- `UmsAdminServiceImpl --> AdminUserDetails`：服务实现类在权限认证等操作中使用`AdminUserDetails`封装管理员信息。
- `UmsAdminServiceImpl --> UmsAdminCacheService`：服务实现类依赖缓存服务，提高数据获取效率。
- `UmsAdminServiceImpl --> UmsAdminRoleRelationDao`：服务实现通过DAO接口进行角色与管理员关系的数据操作。
- `UmsAdminCacheServiceImpl <|.. UmsAdminCacheService`：实现接口，便于缓存服务的替换和扩展。
- `UmsAdminCacheServiceImpl --> UmsAdminService`：缓存服务实现类依赖管理员服务，便于获取和缓存用户数据。
- `UmsAdminCacheServiceImpl --> UmsAdminRoleRelationDao`：缓存服务实现通过DAO接口获取角色关联数据。
- `UmsRoleServiceImpl <|.. UmsRoleService`：角色服务实现接口，便于权限管理功能的扩展和替换。
- `UmsRoleServiceImpl --> UmsAdminCacheService`：角色服务实现依赖缓存服务，提高角色和资源分配的性能。
- `UmsRoleServiceImpl --> UmsRoleDao`：角色服务实现通过DAO接口进行数据库操作。
- `UmsMenuServiceImpl <|.. UmsMenuService`：菜单服务实现接口，实现层与接口解耦。
- `UmsResourceServiceImpl <|.. UmsResourceService`：资源服务实现接口，便于资源管理的扩展。
- `UmsResourceServiceImpl --> UmsAdminCacheService`：资源服务实现依赖缓存服务，提高资源数据的查询效率。
- `UmsResourceCategoryServiceImpl <|.. UmsResourceCategoryService`：资源分类服务实现接口，便于分类管理的解耦。
- `PmsProductCategoryServiceImpl <|.. PmsProductCategoryService`：商品分类服务实现接口，实现类与接口分离便于扩展。
- `PmsProductCategoryServiceImpl --> PmsProductCategoryDao`：商品分类服务实现通过DAO接口获取分类树结构。
- `PmsProductCategoryServiceImpl --> PmsProductCategoryAttributeRelationDao`：实现类通过DAO接口维护分类与属性的关联关系。
- `PmsBrandServiceImpl <|.. PmsBrandService`：品牌服务实现接口，便于品牌业务的扩展。
- `PmsProductAttributeServiceImpl <|.. PmsProductAttributeService`：商品属性服务实现接口，便于属性管理的扩展。
- `PmsProductAttributeServiceImpl --> PmsProductAttributeDao`：属性服务实现通过DAO获取属性信息。
- `PmsProductAttributeCategoryServiceImpl <|.. PmsProductAttributeCategoryService`：属性分类服务实现接口，便于属性分类的扩展。
- `PmsProductAttributeCategoryServiceImpl --> PmsProductAttributeCategoryDao`：实现类通过DAO接口获取带属性的分类信息。
- `SmsCouponServiceImpl <|.. SmsCouponService`：优惠券服务实现接口，便于优惠券业务扩展和维护。
- `SmsCouponServiceImpl --> SmsCouponDao`：优惠券服务实现通过DAO获取优惠券详情。
- `SmsCouponServiceImpl --> SmsCouponProductRelationDao`：服务实现通过DAO维护优惠券与商品的关联。
- `SmsCouponServiceImpl --> SmsCouponProductCategoryRelationDao`：服务实现通过DAO维护优惠券与商品分类的关联。
- `SmsCouponServiceImpl --> SmsCouponParam`：服务实现通过`SmsCouponParam`对象传递优惠券详细数据。
- `SmsCouponHistoryServiceImpl <|.. SmsCouponHistoryService`：优惠券历史服务实现接口，便于历史记录功能扩展。
- `SmsHomeRecommendSubjectServiceImpl <|.. SmsHomeRecommendSubjectService`：推荐专题服务实现接口，便于推荐业务的扩展。
- `CmsSubjectServiceImpl <|.. CmsSubjectService`：主题服务实现接口，便于主题管理的扩展。
- `SmsHomeNewProductServiceImpl <|.. SmsHomeNewProductService`：新品推荐服务实现接口，便于新品推荐业务扩展。
- `SmsHomeAdvertiseServiceImpl <|.. SmsHomeAdvertiseService`：广告服务实现接口，便于广告管理扩展。
- `SmsHomeBrandServiceImpl <|.. SmsHomeBrandService`：品牌推荐服务实现接口，便于品牌推荐管理扩展。
- `SmsHomeRecommendProductServiceImpl <|.. SmsHomeRecommendProductService`：推荐产品服务实现接口，便于推荐产品业务扩展。
- `PmsProductServiceImpl <|.. PmsProductService`：商品服务实现接口，便于商品业务的解耦和扩展。
- `PmsProductServiceImpl --> PmsProductDao`：商品服务实现通过DAO接口获取产品数据。
- `PmsProductServiceImpl --> PmsProductVertifyRecordDao`：商品服务实现通过DAO维护商品审核记录。
- `PmsProductServiceImpl --> PmsProductResult`：商品服务实现返回产品详细数据对象。
- `PmsSkuStockServiceImpl <|.. PmsSkuStockService`：SKU库存服务实现接口，便于库存管理扩展。
- `PmsSkuStockServiceImpl --> PmsSkuStockDao`：服务实现通过DAO接口批量更新SKU库存。
- `OmsOrderServiceImpl <|.. OmsOrderService`：订单服务实现接口，便于订单业务的扩展。
- `OmsOrderServiceImpl --> OmsOrderOperateHistoryDao`：订单服务实现通过DAO维护订单操作历史。
- `OmsOrderServiceImpl --> OmsOrderDao`：服务实现通过DAO进行订单数据的查询与处理。
- `OmsOrderServiceImpl --> OmsOrderDetail`：服务实现返回订单详情对象，包含订单项和历史。
- `OmsCompanyAddressServiceImpl <|.. OmsCompanyAddressService`：公司收货地址服务实现接口，便于地址管理扩展。
- `CmsPrefrenceAreaServiceImpl <|.. CmsPrefrenceAreaService`：优选专区服务实现接口，便于专区管理扩展。
- `OmsOrderReturnReasonServiceImpl <|.. OmsOrderReturnReasonService`：退货原因服务实现接口，便于退货原因管理扩展。
- `OmsOrderReturnApplyServiceImpl <|.. OmsOrderReturnApplyService`：退货申请服务实现接口，便于退货业务扩展。
- `OmsOrderReturnApplyServiceImpl --> OmsOrderReturnApplyDao`：服务实现通过DAO接口获取和操作退货申请数据。
- `OmsOrderReturnApplyServiceImpl --> OmsOrderReturnApplyResult`：服务实现返回退货申请详情对象。
- `OmsOrderReturnApplyDao --> OmsOrderReturnApplyResult`：DAO层方法返回退货申请详情对象，包含更丰富的数据。
- `SmsFlashPromotionServiceImpl <|.. SmsFlashPromotionService`：秒杀活动服务实现接口，便于活动业务扩展。
- `SmsFlashPromotionProductRelationServiceImpl <|.. SmsFlashPromotionProductRelationService`：秒杀活动商品关联服务实现接口，便于活动商品业务扩展。
- `SmsFlashPromotionProductRelationServiceImpl --> SmsFlashPromotionProductRelationDao`：服务实现通过DAO接口获取活动商品关联数据。
- `SmsFlashPromotionSessionServiceImpl <|.. SmsFlashPromotionSessionService`：秒杀时间段服务实现接口，便于时间段管理扩展。
- `SmsFlashPromotionSessionServiceImpl --> SmsFlashPromotionProductRelationService`：服务实现依赖商品关联服务，进行活动商品统计等操作。
- `SmsFlashPromotionSessionServiceImpl --> SmsFlashPromotionSessionDetail`：服务实现返回带统计信息的时间段详情对象。
- `OssServiceImpl <|.. OssService`：OSS服务实现接口，便于OSS功能扩展。
- `OssServiceImpl --> OssCallbackResult`：实现类返回OSS回调结果对象，封装上传后的信息。
- `OssServiceImpl --> OssPolicyResult`：实现类返回OSS上传策略对象，提供上传配置信息。
- `OssServiceImpl --> OssCallbackParam`：实现类处理回调请求参数对象，便于数据转换。
- `PmsProductResult <|-- PmsProductParam`：`PmsProductParam`继承`PmsProductResult`，便于参数与结果对象的复用和扩展。
- `OmsOrderReturnApplyResult <|-- OmsOrderReturnApply`：`OmsOrderReturnApplyResult`扩展了`OmsOrderReturnApply`，增加了详情信息如公司地址。
- `OmsOrderDao --> OmsOrderDetail`：订单DAO方法返回订单详情对象，包含订单项和操作历史。
- `OmsOrderService --> OmsOrderDetail`：订单服务方法返回订单详情对象，用于前端展示。
- `OmsOrderReturnApplyService --> OmsOrderReturnApplyResult`：退货申请服务方法返回包含详细信息的申请结果对象。
- `SmsCouponService --> SmsCouponParam`：优惠券服务方法返回带有详细结构的优惠券参数对象。
- `PmsProductService --> PmsProductResult`：商品服务方法返回产品详细信息对象，用于业务处理和前端展示。

