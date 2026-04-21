```mermaid
classDiagram
    class RuoYiConfig {
        -String name
        -String version
        -String copyrightYear
        -boolean demoEnabled
        -static String profile
        -static boolean addressEnabled
        -static String captchaType
        +String getName()
        +void setName(String)
        +String getVersion()
        +void setVersion(String)
        +String getCopyrightYear()
        +void setCopyrightYear(String)
        +boolean isDemoEnabled()
        +void setDemoEnabled(boolean)
        +static String getProfile()
        +void setProfile(String)
        +static boolean isAddressEnabled()
        +void setAddressEnabled(boolean)
        +static String getCaptchaType()
        +void setCaptchaType(String)
        +static String getImportPath()
        +static String getAvatarPath()
        +static String getDownloadPath()
        +static String getUploadPath()
    }

    namespace 通用工具与契约 {
        class CharsetKit {
            +static String ISO_8859_1
            +static String UTF_8
            +static String GBK
            +static Charset forName(ISO_8859_1)
            +static Charset forName(UTF_8)
            +static Charset forName(GBK)
            +static Charset charset(String)
            +static String convert(String,String,String)
            +static String convert(String,Charset,Charset)
            +static String systemCharset()
        }

        class StringUtils {
            -static String NULLSTR
            -static char SEPARATOR
            +static T nvl(T,T)
            +static boolean isEmpty(Collection<?>)
            +static boolean isNotEmpty(Collection<?>)
            +static boolean isEmpty(Object[])
            +static boolean isNotEmpty(Object[])
            +static boolean isEmpty(Map<?,?>)
            +static boolean isNotEmpty(Map<?,?>)
            +static boolean isEmpty(String)
            +static boolean isNotEmpty(String)
            +static boolean isNull(Object)
            +static boolean isNotNull(Object)
            +static boolean isArray(Object)
            +static String trim(String)
            +static String substring(final,int)
            +static String substring(final,int,int)
        }

        class StrFormatter {
            +static String EMPTY_JSON
            +static char C_BACKSLASH
            +static char C_DELIM_START
        }

        class Convert {
            +static String toStr(Object,String)
            +static String toStr(Object)
            +static Character toChar(Object,Character)
            +static Character toChar(Object)
            +static Byte toByte(Object,Byte)
            +static Byte toByte(Object)
            +static Short toShort(Object,Short)
            +static Short toShort(Object)
            +static Number toNumber(Object,Number)
            +static Number toNumber(Object)
            +static Integer toInt(Object,Integer)
            +static Integer toInt(Object)
            +static Integer[] toIntArray(String)
            +static Long[] toLongArray(String)
            +static Integer[] toIntArray(String,String)
            +static Long[] toLongArray(String,String)
            +static String[] toStrArray(String)
            +static String[] toStrArray(String,String)
            +static Long toLong(Object,Long)
            +static Long toLong(Object)
            +static Double toDouble(Object,Double)
            +static Double toDouble(Object)
            +static Float toFloat(Object,Float)
            +static Float toFloat(Object)
            +static Boolean toBool(Object,Boolean)
            +static Boolean toBool(Object)
            +static E toEnum(Class~E~,Object,E)
            +static E toEnum(Class~E~,Object)
            +static BigInteger toBigInteger(Object,BigInteger)
            +static BigInteger toBigInteger(Object)
            +static BigDecimal toBigDecimal(Object,BigDecimal)
            +static BigDecimal toBigDecimal(Object)
            +static String utf8Str(Object)
            +static String str(Object,String)
            +static String str(Object,Charset)
            +static String str(byte[],String)
            +static String str(byte[],Charset)
            +static String str(ByteBuffer,String)
            +static String str(ByteBuffer,Charset)
            +static String toSBC(String)
            +static String toSBC(String,Set~Character~)
            +static String toDBC(String)
            +static String toDBC(String,Set~Character~)
            +static String digitUppercase(double)
        }

        class TableSupport {
            +static String PAGE_NUM
            +static String PAGE_SIZE
            +static String ORDER_BY_COLUMN
            +static String IS_ASC
            +static String REASONABLE
            +static PageDomain getPageDomain()
            +static PageDomain buildPageRequest()
        }

        class PageDomain {
            -Integer pageNum
            -Integer pageSize
            -String orderByColumn
            -String isAsc
            -Boolean reasonable
            +String getOrderBy()
            +Integer getPageNum()
            +void setPageNum(Integer)
            +Integer getPageSize()
            +void setPageSize(Integer)
            +String getOrderByColumn()
            +void setOrderByColumn(String)
            +String getIsAsc()
            +void setIsAsc(String)
            +Boolean getReasonable()
            +void setReasonable(Boolean)
        }

        class ServletUtils {
            +static String getParameter(String)
            +static String getParameter(String,String)
            +static Integer getParameterToInt(String)
            +static Integer getParameterToInt(String,Integer)
            +static Boolean getParameterToBool(String)
            +static Boolean getParameterToBool(String,Boolean)
            +static HttpServletRequest getRequest()
            +static HttpServletResponse getResponse()
            +static HttpSession getSession()
            +static ServletRequestAttributes getRequestAttributes()
            +static void renderString(HttpServletResponse,String)
            +static boolean isAjaxRequest(HttpServletRequest)
            +static String urlEncode(String)
            +static String urlDecode(String)
        }

        class TableDataInfo {
            -static long serialVersionUID
            -long total
            -List<?> rows
            -int code
            -String msg
            +TableDataInfo()
            +TableDataInfo(List<?>,int)
            +long getTotal()
            +void setTotal(long)
            +List<?> getRows()
            +void setRows(List<?>)
            +int getCode()
            +void setCode(int)
            +String getMsg()
            +void setMsg(String)
        }

        class LoginBody {
            -String username
            -String password
            -String code
            -String uuid
            +String getUsername()
            +void setUsername(String)
            +String getPassword()
            +void setPassword(String)
            +String getCode()
            +void setCode(String)
            +String getUuid()
            +void setUuid(String)
        }

        class RegisterBody {
        }

        class LoginUser {
            -static long serialVersionUID
            -Long userId
            -Long deptId
            -String token
            -Long loginTime
            -Long expireTime
            -String ipaddr
            -String loginLocation
            -String browser
            -String os
            -Set~String~ permissions
            -SysUser user
            +Long getUserId()
            +void setUserId(Long)
            +Long getDeptId()
            +void setDeptId(Long)
            +String getToken()
            +void setToken(String)
            +LoginUser()
            +LoginUser(SysUser,Set~String~)
            +LoginUser(Long,Long,SysUser,Set~String~)
            +String getPassword()
            +String getUsername()
            +boolean isAccountNonExpired()
            +boolean isAccountNonLocked()
            +boolean isCredentialsNonExpired()
            +boolean isEnabled()
            +Long getLoginTime()
            +void setLoginTime(Long)
            +String getIpaddr()
            +void setIpaddr(String)
            +String getLoginLocation()
            +void setLoginLocation(String)
            +String getBrowser()
            +void setBrowser(String)
            +String getOs()
            +void setOs(String)
            +Long getExpireTime()
            +void setExpireTime(Long)
            +Set~String~ getPermissions()
            +void setPermissions(Set~String~)
            +SysUser getUser()
            +void setUser(SysUser)
            +GrantedAuthority> getAuthorities()
        }

        class SysUser {
            -static long serialVersionUID
            -Long userId
            -Long deptId
            -String userName
            -String nickName
            -String email
            -String phonenumber
            -String sex
            -String avatar
            -String password
            -String status
            -String delFlag
            -String loginIp
            -Date loginDate
            -SysDept dept
            -List~SysRole~ roles
            -Long[] roleIds
            -Long[] postIds
            -Long roleId
            +SysUser()
            +SysUser(Long)
            +Long getUserId()
            +void setUserId(Long)
            +boolean isAdmin()
            +static boolean isAdmin(Long)
            +Long getDeptId()
            +void setDeptId(Long)
            +String getNickName()
            +void setNickName(String)
            +String getUserName()
            +void setUserName(String)
            +String getEmail()
            +void setEmail(String)
            +String getPhonenumber()
            +void setPhonenumber(String)
            +String getSex()
            +void setSex(String)
            +String getAvatar()
            +void setAvatar(String)
            +String getPassword()
            +void setPassword(String)
            +String getStatus()
            +void setStatus(String)
            +String getDelFlag()
            +void setDelFlag(String)
            +String getLoginIp()
            +void setLoginIp(String)
            +Date getLoginDate()
            +void setLoginDate(Date)
            +SysDept getDept()
            +void setDept(SysDept)
            +List~SysRole~ getRoles()
            +void setRoles(List~SysRole~)
            +Long[] getRoleIds()
            +void setRoleIds(Long[])
            +Long[] getPostIds()
            +void setPostIds(Long[])
            +Long getRoleId()
            +void setRoleId(Long)
            +String toString()
        }

        class SysDept {
            -static long serialVersionUID
            -Long deptId
            -Long parentId
            -String ancestors
            -String deptName
            -Integer orderNum
            -String leader
            -String phone
            -String email
            -String status
            -String delFlag
            -String parentName
            +ArrayList~SysDept~()
            +Long getDeptId()
            +void setDeptId(Long)
            +Long getParentId()
            +void setParentId(Long)
            +String getAncestors()
            +void setAncestors(String)
            +String getDeptName()
            +void setDeptName(String)
            +Integer getOrderNum()
            +void setOrderNum(Integer)
            +String getLeader()
            +void setLeader(String)
            +String getPhone()
            +void setPhone(String)
            +String getEmail()
            +void setEmail(String)
            +String getStatus()
            +void setStatus(String)
            +String getDelFlag()
            +void setDelFlag(String)
            +String getParentName()
            +void setParentName(String)
            +List~SysDept~ getChildren()
            +void setChildren(List~SysDept~)
            +String toString()
        }

        class BaseEntity {
            -static long serialVersionUID
            -String searchValue
            -String createBy
            -Date createTime
            -String updateBy
            -Date updateTime
            -String remark
            -Map~String, Object~
            +String getSearchValue()
            +void setSearchValue(String)
            +String getCreateBy()
            +void setCreateBy(String)
            +Date getCreateTime()
            +void setCreateTime(Date)
            +String getUpdateBy()
            +void setUpdateBy(String)
            +Date getUpdateTime()
            +void setUpdateTime(Date)
            +String getRemark()
            +void setRemark(String)
            +Object> getParams()
            +void setParams(Map~String,Object~)
        }

        class SysDictData {
            -static long serialVersionUID
            -Long dictCode
            -Long dictSort
            -String dictLabel
            -String dictValue
            -String dictType
            -String cssClass
            -String listClass
            -String isDefault
            -String status
            +Long getDictCode()
            +void setDictCode(Long)
            +Long getDictSort()
            +void setDictSort(Long)
            +String getDictLabel()
            +void setDictLabel(String)
            +String getDictValue()
            +void setDictValue(String)
            +String getDictType()
            +void setDictType(String)
            +String getCssClass()
            +void setCssClass(String)
            +String getListClass()
            +void setListClass(String)
            +boolean getDefault()
            +String getIsDefault()
            +void setIsDefault(String)
            +String getStatus()
            +void setStatus(String)
            +String toString()
        }

        class SysMenu {
            -static long serialVersionUID
            -Long menuId
            -String menuName
            -String parentName
            -Long parentId
            -Integer orderNum
            -String path
            -String component
            -String query
            -String isFrame
            -String isCache
            -String menuType
            -String visible
            -String status
            -String perms
            -String icon
            +ArrayList~SysMenu~()
            +Long getMenuId()
            +void setMenuId(Long)
            +String getMenuName()
            +void setMenuName(String)
            +String getParentName()
            +void setParentName(String)
            +Long getParentId()
            +void setParentId(Long)
            +Integer getOrderNum()
            +void setOrderNum(Integer)
            +String getPath()
            +void setPath(String)
            +String getComponent()
            +void setComponent(String)
            +String getQuery()
            +void setQuery(String)
            +String getIsFrame()
            +void setIsFrame(String)
            +String getIsCache()
            +void setIsCache(String)
            +String getMenuType()
            +void setMenuType(String)
            +String getVisible()
            +void setVisible(String)
            +String getStatus()
            +void setStatus(String)
            +String getPerms()
            +void setPerms(String)
            +String getIcon()
            +void setIcon(String)
            +List~SysMenu~ getChildren()
            +void setChildren(List~SysMenu~)
            +String toString()
        }

        class SysRole {
            -static long serialVersionUID
            -Long roleId
            -String roleName
            -String roleKey
            -String roleSort
            -String dataScope
            -boolean menuCheckStrictly
            -boolean deptCheckStrictly
            -String status
            -String delFlag
            -boolean flag
            -Long[] menuIds
            -Long[] deptIds
            -Set~String~ permissions
            +SysRole()
            +SysRole(Long)
            +Long getRoleId()
            +void setRoleId(Long)
            +boolean isAdmin()
            +static boolean isAdmin(Long)
            +String getRoleName()
            +void setRoleName(String)
            +String getRoleKey()
            +void setRoleKey(String)
            +String getRoleSort()
            +void setRoleSort(String)
            +String getDataScope()
            +void setDataScope(String)
            +boolean isMenuCheckStrictly()
            +void setMenuCheckStrictly(boolean)
            +boolean isDeptCheckStrictly()
            +void setDeptCheckStrictly(boolean)
            +String getStatus()
            +void setStatus(String)
            +String getDelFlag()
            +void setDelFlag(String)
            +boolean isFlag()
            +void setFlag(boolean)
            +Long[] getMenuIds()
            +void setMenuIds(Long[])
            +Long[] getDeptIds()
            +void setDeptIds(Long[])
            +Set~String~ getPermissions()
            +void setPermissions(Set~String~)
            +String toString()
        }

        class SysDictType {
            -static long serialVersionUID
            -Long dictId
            -String dictName
            -String dictType
            -String status
            +Long getDictId()
            +void setDictId(Long)
            +String getDictName()
            +void setDictName(String)
            +String getDictType()
            +void setDictType(String)
            +String getStatus()
            +void setStatus(String)
            +String toString()
        }

        class TreeEntity {
            -static long serialVersionUID
            -String parentName
            -Long parentId
            -Integer orderNum
            -String ancestors
            +ArrayList~ ~()
            +String getParentName()
            +void setParentName(String)
            +Long getParentId()
            +void setParentId(Long)
            +Integer getOrderNum()
            +void setOrderNum(Integer)
            +String getAncestors()
            +void setAncestors(String)
            +List<?> getChildren()
            +void setChildren(List<?>)
        }

        class TreeSelect {
            -static long serialVersionUID
            -Long id
            -String label
            -String value
            -List~TreeSelect~ children
            +TreeSelect()
            +TreeSelect(SysDept)
            +TreeSelect(SysMenu)
            +Long getId()
            +void setId(Long)
            +String getLabel()
            +void setLabel(String)
            +String getValue()
            +void setValue(String)
            +List~TreeSelect~ getChildren()
            +void setChildren(List~TreeSelect~)
        }

        class AjaxResult {
            -static long serialVersionUID
            +static String CODE_TAG
            +static String MSG_TAG
            +static String DATA_TAG
            +AjaxResult()
            +AjaxResult(int,String)
            +AjaxResult(int,String,Object)
            +static AjaxResult success()
            +static AjaxResult success(Object)
            +static AjaxResult success(String)
            +static AjaxResult success(String,Object)
            +static AjaxResult error()
            +static AjaxResult error(String)
            +static AjaxResult error(String,Object)
            +static AjaxResult error(int,String)
            +AjaxResult put(String,Object)
        }

        class R~T~ {
            -static long serialVersionUID
            +static int SUCCESS
            +static int FAIL
            -int code
            -String msg
            -T data
            +static R~T~ ok()
            +static R~T~ ok(T)
            +static R~T~ ok(T,String)
            +static R~T~ fail()
            +static R~T~ fail(String)
            +static R~T~ fail(T)
            +static R~T~ fail(T,String)
            +static R~T~ fail(int,String)
            -static R~T~ restResult(T,int,String)
            +int getCode()
            +void setCode(int)
            +String getMsg()
            +void setMsg(String)
            +T getData()
            +void setData(T)
        }

        class BaseController {
            +LoggerFactory.getLogger(this.getClass())
            +void initBinder(WebDataBinder)
            +void startPage()
            +void startOrderBy()
            +void clearPage()
            +TableDataInfo getDataTable(List<?>)
            +TableDataInfo getDataTableTwoList(List<?>,List<?>)
            +TableDataInfo getDataTable(List<?>,Long)
            +AjaxResult success()
            +AjaxResult error()
            +AjaxResult success(String)
            +AjaxResult error(String)
            +AjaxResult toAjax(int)
            +AjaxResult toAjax(boolean)
            +String redirect(String)
            +LoginUser getLoginUser()
            +Long getUserId()
            +Long getDeptId()
            +String getUsername()
        }

        class DateUtils {
            +static String YYYY
            +static String YYYY_MM
            +static String YYYY_MM_DD
            +static String YYYYMMDDHHMMSS
            +static String YYYY_MM_DD_HH_MM_SS
            -static String[] parsePatterns
            +static Date getNowDate()
            +static String getDate()
            +static String getTime()
            +static String dateTimeNow()
            +static String dateTimeNow(final)
            +static String dateTime(final)
            +static String parseDateToStr(final,final)
            +static Date dateTime(final,final)
            +static String datePath()
            +static String dateTime()
            +static Date parseDate(Object)
            +static Date getServerStartDate()
            +static int differentDaysByMillisecond(Date,Date)
            +static String getDatePoor(Date,Date)
            +static Date toDate(LocalDateTime)
            +static Date toDate(LocalDate)
        }

        class PageUtils {
            +static void startPage()
            +static void clearPage()
            +static TableDataInfo getDataTable(List<?>)
        }

        class SecurityUtils {
            +static Long getUserId()
            +static Long getDeptId()
            +static String getUsername()
            +static LoginUser getLoginUser()
            +static Authentication getAuthentication()
            +static String encryptPassword(String)
            +static boolean matchesPassword(String,String)
            +static boolean isAdmin(Long)
        }

        class SqlUtil {
            +static String SQL_REGEX
            +static String SQL_PATTERN
            +static String escapeOrderBySql(String)
            +static boolean isValidOrderBySql(String)
            +static void filterKeyword(String)
        }

        class RedisCache {
            +RedisTemplate redisTemplate
            +void setCacheObject(final,final)
            +void setCacheObject(final,final,final,final)
            +boolean expire(final,final)
            +boolean expire(final,final,final)
            +long getExpire(final)
            +Boolean hasKey(String)
            +T getCacheObject(final)
            +boolean deleteObject(final)
            +boolean deleteObject(final)
            +long setCacheList(final,final)
            +List~T~ getCacheList(final)
            +T> setCacheSet(final,final)
            +Set~T~ getCacheSet(final)
            +void setCacheMap(final,final,T>)
            +T> getCacheMap(final)
            +void setCacheMapValue(final,final,final)
            +T getCacheMapValue(final,final)
            +List~T~ getMultiCacheMapValue(final,final)
            +boolean deleteCacheMapValue(final,final)
            +Collection~String~ keys(final)
        }

        class Arith {
            -static int DEF_DIV_SCALE
            -Arith()
            +static double add(double,double)
            +static double sub(double,double)
            +static double mul(double,double)
            +static double div(double,double)
            +static double div(double,double,int)
            +static double round(double,int)
        }

        class LotteryUtils {
            +static int lottery(List~Double~)
        }

        class Threads {
            +LoggerFactory.getLogger(Threads.class)
            +static void sleep(long)
            +static void shutdownAndAwaitTermination(ExecutorService)
            +static void printException(Runnable,Throwable)
        }

        class DictUtils {
            +static String SEPARATOR
            +static void setDictCache(String,List~SysDictData~)
            +static List~SysDictData~ getDictCache(String)
            +static String getDictLabel(String,String)
            +static String getDictValue(String,String)
            +static String getDictLabel(String,String,String)
            +static String getDictValue(String,String,String)
            +static void removeDictCache(String)
            +static void clearDictCache()
            +static String getCacheKey(String)
        }

        class SpringUtils {
            -static ConfigurableListableBeanFactory beanFactory
            -static ApplicationContext applicationContext
            +void postProcessBeanFactory(ConfigurableListableBeanFactory)
            +void setApplicationContext(ApplicationContext)
            +static T getBean(String)
            +static T getBean(Class~T~)
            +static boolean containsBean(String)
            +static boolean isSingleton(String)
            +static Class<?> getType(String)
            +static String[] getAliases(String)
            +static T getAopProxy(T)
            +static String[] getActiveProfiles()
            +static String getActiveProfile()
            +static String getRequiredProperty(String)
        }

        class IdUtils {
            +static String randomUUID()
            +static String simpleUUID()
            +static String fastUUID()
            +static String fastSimpleUUID()
        }

        class UUID {
            -static long serialVersionUID
            -static class Holder
            -long mostSigBits
            -long leastSigBits
            -UUID(byte[])
            +UUID(long,long)
            +static UUID fastUUID()
            +static UUID randomUUID()
            +static UUID randomUUID(boolean)
            +static UUID nameUUIDFromBytes(byte[])
            +static UUID fromString(String)
            +long getLeastSignificantBits()
            +long getMostSignificantBits()
            +int version()
            +int variant()
            +long timestamp()
            +int clockSequence()
            +long node()
            +String toString()
            +String toString(boolean)
            +int hashCode()
            +boolean equals(Object)
            +int compareTo(UUID)
            +String digits(long,int)
            +void checkTimeBase()
            +static SecureRandom getSecureRandom()
            +static ThreadLocalRandom getRandom()
        }

        class UtilException {
            -static long serialVersionUID
            +UtilException(Throwable)
            +UtilException(String)
            +UtilException(String,Throwable)
        }

        class Seq {
            +static String commSeqType
            +static String uploadSeqType
            -static String machineCode
            +static AtomicInteger(1)
            +static AtomicInteger(1)
            +static String getId()
            +static String getId(String)
            +static String getId(AtomicInteger,int)
            -static String getSeq(AtomicInteger,int)
        }

        class Md5Utils {
            +LoggerFactory.getLogger(Md5Utils.class)
            -byte[] md5(String)
            -String toHex(byte)
            +static String hash(String)
        }

        class Base64 {
            -static int BASELENGTH
            -static int LOOKUPLENGTH
            -static int TWENTYFOURBITGROUP
            -static int EIGHTBIT
            -static int SIXTEENBIT
            -static int FOURBYTE
            -static int SIGN
            -static char PAD
            -static byte[] base64Alphabet
            -static char[] lookUpBase64Alphabet
            -static boolean isWhiteSpace(char)
            -static boolean isPad(char)
            -static boolean isData(char)
            +static String encode(byte[])
            +static byte[] decode(String)
            -static int removeWhiteSpace(char[])
        }

        class BeanValidators {
            +ConstraintViolationException
            +static void validateWithException(Validator,Object,Class<?>...)
        }

        class BeanUtils {
            -static int BEAN_METHOD_PROP_INDEX
            +static void copyBeanProp(Object,Object)
            +static List~Method~ getSetterMethods(Object)
            +static List~Method~ getGetterMethods(Object)
            +static boolean isMethodPropEquals(String,String)
        }

        class ReflectUtils {
            -static String SETTER_PREFIX
            -static String GETTER_PREFIX
            -static String CGLIB_CLASS_SEPARATOR
            +LoggerFactory.getLogger(ReflectUtils.class)
            +E invokeGetter(Object,String)
            +void invokeSetter(Object,String,E)
            +E getFieldValue(final,final)
            +void setFieldValue(final,final,final)
            +E invokeMethodByName(final,final,final)
            +Field getAccessibleField(final,final)
            +Method getAccessibleMethodByName(final,final,int)
            +void makeAccessible(Method)
            +void makeAccessible(Field)
            +Class~T~ getClassGenricType(final)
            +Class getClassGenricType(final,final)
            +Class<?> getUserClass(Object)
            +RuntimeException convertReflectionExceptionToUnchecked(String,Exception)
        }

        class MessageUtils {
            +static String message(String,Object[])
        }

        class ServiceException {
            -static long serialVersionUID
            -Integer code
            -String message
            -String detailMessage
            +ServiceException()
            +ServiceException(String)
            +ServiceException(String,Integer)
            +String getDetailMessage()
            +String getMessage()
            +Integer getCode()
            +ServiceException setMessage(String)
            +ServiceException setDetailMessage(String)
        }

        class HTMLFilter {
            -static int REGEX_FLAGS_SI
            -Map~String, List~String~~
            -String[] vSelfClosingTags
            -String[] vNeedClosingTags
            -String[] vDisallowed
            -String[] vProtocolAtts
            -String[] vAllowedProtocols
            -String[] vRemoveBlanks
            -String[] vAllowedEntities
            -boolean stripComment
            -boolean encodeQuotes
            -boolean alwaysMakeTags
            +Pattern.compile("<!--(.*?)-->",Pattern.DOTALL)
            +Pattern.compile("^!--(.*)--$",REGEX_FLAGS_SI)
            +Pattern.compile("<(.*?)>",Pattern.DOTALL)
            +Pattern.compile("^/([a-z0-9]+)",REGEX_FLAGS_SI)
            +Pattern.compile("^([a-z0-9]+)(.*?)(/?)$",REGEX_FLAGS_SI)
            +Pattern.compile("([a-z0-9]+)=([\"'])(.*?)\\2",REGEX_FLAGS_SI)
            +Pattern.compile("([a-z0-9]+)(=)([^\"\\s']+)",REGEX_FLAGS_SI)
            +Pattern.compile("^([^:]+):",REGEX_FLAGS_SI)
            +Pattern.compile("&#(\\d+);?")
            +Pattern.compile("&#x([0-9a-f]+);?")
            +Pattern.compile("&([^&;]*)(?=(;|&|$))")
            +Pattern.compile("(>|^)([^<]+?)(<|$)",Pattern.DOTALL)
            +Pattern.compile("^>")
            +Pattern.compile("<([^>]*?)(?=<|$)")
            +Pattern.compile("(^|>)([^<]*?)(?=>)")
            +Pattern.compile("<([^>]*?)(?=<|$)")
            +Pattern.compile("(^|>)([^<]*?)(?=>)")
            +Pattern.compile("&")
            +Pattern.compile("\"")
            +Pattern.compile("<")
            +Pattern.compile(">")
            +Pattern.compile("<>")
            +ConcurrentHashMap<>()
            +ConcurrentHashMap<>()
            +HashMap<>()
            +HTMLFilter()
            +HTMLFilter(final,Object>)
            -void reset()
            +static String chr(final)
            +static String htmlSpecialChars(final)
            +String filter(final)
            +boolean isAlwaysMakeTags()
            +boolean isStripComments()
            -String escapeComments(final)
            -String balanceHTML(String)
            -String checkTags(String)
            -String processRemoveBlanks(final)
            -static String regexReplace(final,final,final)
            -String processTag(final)
            -String processParamProtocol(String)
            -String decodeEntities(String)
            -String validateEntities(final)
            -String encodeQuotes(final)
            -String checkEntity(final,final)
            -boolean isValidEntity(final)
            -static boolean inArray(final,final)
            -boolean allowed(final)
            -boolean allowedAttribute(final,final)
        }

        class EscapeUtil {
            -static char[][] TEXT
            +"(<[^<]*?>)|(<[\\s]*?/[^<]*?>)|(<[^<]*?/[\\s]*?>):=
            +static String escape(String)
            +static String unescape(String)
            +static String clean(String)
            -static String encode(String)
            +static String decode(String)
            +static void main(String[])
        }

        class LogUtils {
            +static String getBlock(Object)
        }

        class ExceptionUtil {
            +static String getExceptionMessage(Throwable)
            +static String getRootErrorMessage(Exception)
        }

        class HttpUtils {
            +static LoggerFactory.getLogger(HttpUtils.class)
            +static String sendGet(String)
            +static String sendGet(String,String)
            +static String sendGet(String,String,String)
            +static String sendPost(String,String)
            +static String sendSSLPost(String,String)
        }

        class HttpHelper {
            +static LoggerFactory.getLogger(HttpHelper.class)
            +static String getBodyString(ServletRequest)
        }

        class AddressUtils {
            +static String IP_URL
            +static String UNKNOWN
            +static LoggerFactory.getLogger(AddressUtils.class)
            +static String getRealAddressByIP(String)
        }

        class IpUtils {
            +static String getIpAddr(HttpServletRequest)
            +static boolean internalIp(String)
            +static boolean internalIp(byte[])
            +static byte[] textToNumericFormatV4(String)
            +static String getHostIp()
            +static String getHostName()
            +static String getMultistageReverseProxyIp(String)
            +static boolean isUnknown(String)
        }

        class FileUploadUtils {
            +static long DEFAULT_MAX_SIZE
            +static int DEFAULT_FILE_NAME_LENGTH
            +RuoYiConfig.getProfile()
            +static void setDefaultBaseDir(String)
            +static String getDefaultBaseDir()
            +static String upload(MultipartFile)
            +static String upload(String,MultipartFile)
            +static String upload(String,MultipartFile,String[])
            +static String extractFilename(MultipartFile)
            +static File getAbsoluteFile(String,String)
            +static String getPathFileName(String,String)
            +static void assertAllowed(MultipartFile,String[])
            +static boolean isAllowedExtension(String,String[])
            +static String getExtension(MultipartFile)
        }

        class FileNameLengthLimitExceededException {
            -static long serialVersionUID
            +FileNameLengthLimitExceededException(int)
        }

        class FileSizeLimitExceededException {
            -static long serialVersionUID
            +FileSizeLimitExceededException(long)
        }

        class InvalidExtensionException {
            -static long serialVersionUID
            -String[] allowedExtension
            -String extension
            -String filename
            +InvalidExtensionException(String[],String,String)
            +String[] getAllowedExtension()
            +String getExtension()
            +String getFilename()
        }

        class MimeTypeUtils {
            +static String IMAGE_PNG
            +static String IMAGE_JPG
            +static String IMAGE_JPEG
            +static String IMAGE_BMP
            +static String IMAGE_GIF
            +static String[] IMAGE_EXTENSION
            +static String[] FLASH_EXTENSION
            +static String[] MEDIA_EXTENSION
            +static String[] VIDEO_EXTENSION
            +static String[] DEFAULT_ALLOWED_EXTENSION
            +static String getExtension(String)
        }

        class FileUtils {
            +static String FILENAME_PATTERN
            +static void writeBytes(String,OutputStream)
            +static String writeImportBytes(byte[])
            +static String writeBytes(byte[],String)
            +static boolean deleteFile(String)
            +static boolean isValidFilename(String)
            +static boolean checkAllowDownload(String)
            +static String setFileDownloadHeader(HttpServletRequest,String)
            +static void setAttachmentResponseHeader(HttpServletResponse,String)
            +static String percentEncode(String)
            +static String getFileExtendName(byte[])
            +static String getName(String)
            +static String getNameNotSuffix(String)
        }

        class FileTypeUtils {
            +static String getFileType(File)
            +static String getFileType(String)
            +static String getFileExtendName(byte[])
        }

        class ImageUtils {
            +static LoggerFactory.getLogger(ImageUtils.class)
            +static byte[] getImage(String)
            +static InputStream getFile(String)
            +static byte[] readFile(String)
        }

        class ExcelHandlerAdapter {
            <<interface>>
            +Object format(Object,String[])
        }

        class ExcelUtil~T~ {
            +static String FORMULA_REGEX_STR
            +static String[] FORMULA_STR
            +static int sheetSize
            -String sheetName
            -Type type
            -Workbook wb
            -Sheet sheet
            -Map~String, CellStyle~
            -List~T~ list
            -List~Object[]~ fields
            -int rownum
            -String title
            -short maxHeight
            -int subMergedLastRowNum
            -int subMergedFirstRowNum
            -Method subMethod
            -List~Field~ subFields
            +Class~T~ clazz
            +String[] excludeFields
            +LoggerFactory.getLogger(ExcelUtil.class)
            +Double> HashMap~Integer,
            +DecimalFormat("######0.00")
            +ExcelUtil(Class~T~)
            +void hideColumn(String[])
            +void init(List~T~,String,String,Type)
            +void createTitle()
            +void createSubHead()
            +List~T~ importExcel(InputStream)
            +List~T~ importExcel(InputStream,int)
            +List~T~ importExcel(String,InputStream,int)
            +AjaxResult exportExcel(List~T~,String)
            +AjaxResult exportExcel(List~T~,String,String)
            +void exportExcel(HttpServletResponse,List~T~,String)
            +void exportExcel(HttpServletResponse,List~T~,String,String)
            +AjaxResult importTemplateExcel(String)
            +AjaxResult importTemplateExcel(String,String)
            +void importTemplateExcel(HttpServletResponse,String)
            +void importTemplateExcel(HttpServletResponse,String,String)
            +void exportExcel(HttpServletResponse)
            +AjaxResult exportExcel()
            +void writeSheet()
            +void fillExcelData(int,Row)
            +CellStyle> createStyles(Workbook)
            +CellStyle> annotationHeaderStyles(Workbook,Map~String,CellStyle~)
            +CellStyle> annotationDataStyles(Workbook)
            +Cell createHeadCell(Excel,Row,int)
            +void setCellVo(Object,Excel,Cell)
            +static Drawing<?> getDrawingPatriarch(Sheet)
            +int getImageType(byte[])
            +void setDataValidation(Excel,Row,int)
            +Cell addCell(Excel,Row,T,Field,int)
            +static String convertByExp(String,String,String)
            +static String reverseByExp(String,String,String)
            +static String convertDictByExp(String,String,String)
            +static String reverseDictByExp(String,String,String)
            +String dataFormatHandlerAdapter(Object,Excel)
            +void addStatisticsData(Integer,String,Excel)
            +void addStatisticsRow()
            +String encodingFilename(String)
            +String getAbsoluteFile(String)
            +Object getTargetValue(T,Field,Excel)
            +Object getValue(Object,String)
            +void createExcelField()
            +List~Object[]~ getFields()
            +short getRowHeight()
            +void createWorkbook()
            +void createSheet(int,int)
            +Object getCellValue(Row,int)
            +boolean isRowEmpty(Row)
            +PictureData> getSheetPictures03(HSSFSheet,HSSFWorkbook)
            +PictureData> getSheetPictures07(XSSFSheet,XSSFWorkbook)
            +String parseDateToStr(String,Object)
            +boolean isSubList()
            +boolean isSubListValue(T)
            +Collection<?> getListCellValue(Object)
            +Method getSubMethod(String,Class<?>):Method
        }

        class CaptchaExpireException {
            -static long serialVersionUID
            +CaptchaExpireException()
        }

        class UserException {
            -static long serialVersionUID
            +UserException(String,Object[])
        }

        class UserPasswordRetryLimitExceedException {
            -static long serialVersionUID
            +UserPasswordRetryLimitExceedException(int,int)
        }

        class UserPasswordNotMatchException {
            -static long serialVersionUID
            +UserPasswordNotMatchException()
        }

        class CaptchaException {
            -static long serialVersionUID
            +CaptchaException()
        }

        class BaseException {
            -static long serialVersionUID
            -String module
            -String code
            -Object[] args
            -String defaultMessage
            +BaseException(String,String,Object[],String)
            +BaseException(String,String,Object[])
            +BaseException(String,String)
            +BaseException(String,Object[])
            +BaseException(String)
            +String getMessage()
            +String getModule()
            +String getCode()
            +Object[] getArgs()
            +String getDefaultMessage()
        }

        class FileException {
            -static long serialVersionUID
            +FileException(String,Object[])
        }

        class DemoModeException {
            -static long serialVersionUID
            +DemoModeException()
        }

        class GlobalException {
            -static long serialVersionUID
            -String message
            -String detailMessage
            +GlobalException()
            +GlobalException(String)
            +String getDetailMessage()
            +GlobalException setDetailMessage(String)
            +String getMessage()
            +GlobalException setMessage(String)
        }

        class TaskException {
            -static long serialVersionUID
            -Code code
            +TaskException(String,Code)
            +TaskException(String,Code,Exception)
            +Code getCode()
        }

        class Constants {
            +static String UTF8
            +static String GBK
            +static String WWW
            +static String HTTP
            +static String HTTPS
            +static String SUCCESS
            +static String FAIL
            +static String LOGIN_SUCCESS
            +static String LOGOUT
            +static String REGISTER
            +static String LOGIN_FAIL
            +static Integer CAPTCHA_EXPIRATION
            +static String TOKEN
            +static String TOKEN_PREFIX
            +static String LOGIN_USER_KEY
            +static String JWT_USERID
            +static String JWT_USERNAME
            +static String JWT_AVATAR
            +static String JWT_CREATED
            +static String JWT_AUTHORITIES
            +static String RESOURCE_PREFIX
            +static String LOOKUP_RMI
            +static String LOOKUP_LDAP
            +static String LOOKUP_LDAPS
            +static String[] JOB_WHITELIST_STR
            +static String[] JOB_ERROR_STR
            +static String ACCESS_TOKEN_URL
            +static String GET_USER_INFO_URL
            +static String X_BG_HMAC_ACCESS_KEY
            +static String X_BG_HMAC_SIGNATURE
            +static String X_BG_HMAC_ALGORITHM
            +static String X_BG_DATE_TIME
            +static String DEFAULT_HMAC_SIGNATURE
            +static String WEIXIN_ENDPOINT_TYPE
            +static String APP_ID
            +static String IRS_AK
            +static String IRS_SK
        }

        class CacheConstants {
            +static String LOGIN_TOKEN_KEY
            +static String CAPTCHA_CODE_KEY
            +static String SYS_CONFIG_KEY
            +static String SYS_DICT_KEY
            +static String REPEAT_SUBMIT_KEY
            +static String RATE_LIMIT_KEY
            +static String PWD_ERR_CNT_KEY
        }

        class HttpStatus {
            +static int SUCCESS
            +static int CREATED
            +static int ACCEPTED
            +static int NO_CONTENT
            +static int MOVED_PERM
            +static int SEE_OTHER
            +static int NOT_MODIFIED
            +static int BAD_REQUEST
            +static int UNAUTHORIZED
            +static int FORBIDDEN
            +static int NOT_FOUND
            +static int BAD_METHOD
            +static int CONFLICT
            +static int UNSUPPORTED_TYPE
            +static int ERROR
            +static int NOT_IMPLEMENTED
        }

        class ScheduleConstants {
            +static String TASK_CLASS_NAME
            +static String TASK_PROPERTIES
            +static String MISFIRE_DEFAULT
            +static String MISFIRE_IGNORE_MISFIRES
            +static String MISFIRE_FIRE_AND_PROCEED
            +static String MISFIRE_DO_NOTHING
        }

        class UserConstants {
            +static String SYS_USER
            +static String NORMAL
            +static String EXCEPTION
            +static String USER_DISABLE
            +static String ROLE_DISABLE
            +static String DEPT_NORMAL
            +static String DEPT_DISABLE
            +static String DICT_NORMAL
            +static String YES
            +static String YES_FRAME
            +static String NO_FRAME
            +static String TYPE_DIR
            +static String TYPE_MENU
            +static String TYPE_BUTTON
            +static String LAYOUT
            +static String PARENT_VIEW
            +static String INNER_LINK
            +static String UNIQUE
            +static String NOT_UNIQUE
            +static int USERNAME_MIN_LENGTH
            +static int USERNAME_MAX_LENGTH
            +static int PASSWORD_MIN_LENGTH
            +static int PASSWORD_MAX_LENGTH
        }

        class GenConstants {
            +static String TPL_CRUD
            +static String TPL_TREE
            +static String TPL_SUB
            +static String TREE_CODE
            +static String TREE_PARENT_CODE
            +static String TREE_NAME
            +static String PARENT_MENU_ID
            +static String PARENT_MENU_NAME
            +static String[] COLUMNTYPE_STR
            +static String[] COLUMNTYPE_TEXT
            +static String[] COLUMNTYPE_TIME
            +static String[] COLUMNTYPE_NUMBER
            +static String[] COLUMNNAME_NOT_EDIT
            +static String[] COLUMNNAME_NOT_LIST
            +static String[] COLUMNNAME_NOT_QUERY
            +static String[] BASE_ENTITY
            +static String[] TREE_ENTITY
            +static String HTML_INPUT
            +static String HTML_TEXTAREA
            +static String HTML_SELECT
            +static String HTML_RADIO
            +static String HTML_CHECKBOX
            +static String HTML_DATETIME
            +static String HTML_IMAGE_UPLOAD
            +static String HTML_FILE_UPLOAD
            +static String HTML_EDITOR
            +static String TYPE_STRING
            +static String TYPE_INTEGER
            +static String TYPE_LONG
            +static String TYPE_DOUBLE
            +static String TYPE_BIGDECIMAL
            +static String TYPE_DATE
            +static String QUERY_LIKE
            +static String QUERY_EQ
            +static String REQUIRE
        }
    }

    CharsetKit --> StringUtils
    StringUtils <|-- StringUtils
    StringUtils --> StrFormatter
    StringUtils --> StringUtils
    StrFormatter --> Convert
    StrFormatter --> StringUtils
    Convert --> StringUtils
    TableSupport --> PageDomain
    TableSupport --> Convert
    TableSupport --> ServletUtils
    TableSupport --> PageDomain
    TableSupport --> PageDomain
    PageDomain --> StringUtils
    ServletUtils --> Convert
    ServletUtils --> StringUtils
    RegisterBody <|-- LoginBody
    LoginUser --> SysUser
    LoginUser --> SysUser
    SysUser <|-- BaseEntity
    SysUser --> BaseEntity
    SysUser --> SysDept
    SysDept <|-- BaseEntity
    SysDept --> BaseEntity
    SysDictData <|-- BaseEntity
    SysDictData --> BaseEntity
    SysMenu <|-- BaseEntity
    SysMenu --> BaseEntity
    SysRole <|-- BaseEntity
    SysRole --> BaseEntity
    SysDictType <|-- BaseEntity
    SysDictType --> BaseEntity
    TreeEntity <|-- BaseEntity
    TreeSelect --> SysDept
    TreeSelect --> SysMenu
    AjaxResult --> StringUtils
    BaseController --> AjaxResult
    BaseController --> LoginUser
    BaseController --> PageDomain
    BaseController --> TableDataInfo
    BaseController --> TableSupport
    BaseController --> DateUtils
    BaseController --> PageUtils
    BaseController --> SecurityUtils
    BaseController --> StringUtils
    BaseController --> SqlUtil
    DateUtils <|-- DateUtils
    DateUtils --> DateUtils
    PageUtils --> PageDomain
    PageUtils --> TableDataInfo
    PageUtils --> TableSupport
    PageUtils --> SqlUtil
    SecurityUtils --> LoginUser
    SecurityUtils --> ServiceException
    SqlUtil --> UtilException
    SqlUtil --> StringUtils
    RedisCache --> RedisTemplate
    DictUtils --> SysDictData
    DictUtils --> RedisCache
    DictUtils --> StringUtils
    DictUtils --> SpringUtils
    SpringUtils --> StringUtils
    IdUtils --> UUID
    UUID --> UtilException
    Seq --> DateUtils
    Seq --> StringUtils
    ReflectUtils --> Convert
    ReflectUtils --> DateUtils
    ReflectUtils --> StringUtils
    MessageUtils --> SpringUtils
    EscapeUtil --> StringUtils
    EscapeUtil --> HTMLFilter
    HttpUtils --> StringUtils
    AddressUtils --> RuoYiConfig
    AddressUtils --> StringUtils
    AddressUtils --> HttpUtils
    AddressUtils --> IpUtils
    IpUtils --> StringUtils
    FileUploadUtils --> RuoYiConfig
    FileUploadUtils --> FileNameLengthLimitExceededException
    FileUploadUtils --> FileSizeLimitExceededException
    FileUploadUtils --> InvalidExtensionException
    FileUploadUtils --> DateUtils
    FileUploadUtils --> StringUtils
    FileUploadUtils --> MimeTypeUtils
    FileUploadUtils --> Seq
    FileNameLengthLimitExceededException <|-- FileException
    FileNameLengthLimitExceededException --> FileException
    FileSizeLimitExceededException <|-- FileException
    FileSizeLimitExceededException --> FileException
    InvalidExtensionException <|-- FileUploadException
    FileUtils --> RuoYiConfig
    FileUtils --> DateUtils
    FileUtils --> FileTypeUtils
    FileUtils --> FileUploadUtils
    FileUtils --> IdUtils
    FileUtils --> StringUtils
    ImageUtils --> RuoYiConfig
    ImageUtils --> StringUtils
    ExcelUtil~T~ --> RuoYiConfig
    ExcelUtil~T~ --> AjaxResult
    ExcelUtil~T~ --> Convert
    ExcelUtil~T~ --> UtilException
    ExcelUtil~T~ --> DateUtils
    ExcelUtil~T~ --> DictUtils
    ExcelUtil~T~ --> StringUtils
    ExcelUtil~T~ --> FileTypeUtils
    ExcelUtil~T~ --> FileUtils
    ExcelUtil~T~ --> ImageUtils
    ExcelUtil~T~ --> ReflectUtils
    ExcelUtil~T~ --> UUID
    CaptchaExpireException <|-- UserException
    CaptchaExpireException --> UserException
    UserException <|-- BaseException
    UserException --> BaseException
    UserPasswordRetryLimitExceedException <|-- UserException
    UserPasswordRetryLimitExceedException --> UserException
    UserPasswordNotMatchException <|-- UserException
    UserPasswordNotMatchException --> UserException
    CaptchaException <|-- UserException
    CaptchaException --> UserException
    BaseException --> MessageUtils
    BaseException --> StringUtils
    FileException <|-- BaseException
    FileException --> BaseException

```
## 一、整体概述

本模块自身只直接实现了一个核心配置类 **`RuoYiConfig`**，用于集中管理系统名称、版本、版权年份、演示模式、文件根目录（profile）、是否开启地址解析以及验证码类型等运行时配置。  
`RuoYiConfig` 被“通用工具与契约”子模块中的文件上传、文件访问、图片访问、Excel 导入导出、IP 地址解析等大量工具类依赖，用于获取存储路径、开关配置等。  
整体上，该模块呈现出“**配置中心 + 通用工具层**”的协作模式：`RuoYiConfig` 提供核心配置，通用工具层封装字符串、日期、分页、安全、缓存、文件、Excel、异常与常量等横切能力，供上层业务统一调用。

---

## 二、关联子模块中的类说明（按“通用工具与契约”子模块分组）

### 1. 字符与类型转换相关

- **CharsetKit**：封装常用字符集常量（UTF-8、GBK 等），提供字符串在不同 `Charset` 间转换的工具方法，方便在 IO、网络等场景下统一编码处理。
- **StringUtils**：在 Apache `StringUtils` 基础上扩展了集合、数组、Map、对象等“空判断”和截取方法，同时提供自定义 `substring`、空值替换等；很多工具类依赖它做健壮的空值处理和字符串格式化。
- **StrFormatter**：实现占位符格式化逻辑（如 `"{}"` 风格），配合 `Convert.utf8Str` 和 `StringUtils` 对参数做空值判断，统一日志和提示语的格式化输出。
- **Convert**：提供对象到字符串、数字、布尔值、枚举、大数等多种类型的转换，支持数组/集合转换和半角/全角转换，是参数解析、反射填充等场景的底层能力。

### 2. 分页与 Web 请求相关

- **TableSupport**：从当前 HTTP 请求中读取分页参数（页码、每页大小、排序列、排序方向、合理化标记），通过 `ServletUtils`、`Convert` 组装为 `PageDomain`，是分页查询入口工具。
- **PageDomain**：封装当前请求的分页和排序信息，并在 `getOrderBy` 时利用 `StringUtils` 做空值判断及驼峰转下划线，生成安全可用的 `order by` 片段。
- **ServletUtils**：围绕 Spring Web 上下文封装获取 `HttpServletRequest/Response/Session` 的方法，并提供参数获取与类型转换（使用 `Convert`）、Ajax 请求判断及 URL 编解码功能。
- **TableDataInfo**：统一分页结果载体，包含总记录数、数据列表、返回码和提示信息，供 `BaseController`、`PageUtils` 等封装统一分页接口返回。

### 3. 登录与用户/组织/权限实体

- **LoginBody**：封装登录请求体（用户名、密码、验证码、uuid），作为认证接口的入参对象。
- **RegisterBody**：继承 `LoginBody`，用于注册场景复用用户名、密码等字段，简化表单模型。
- **LoginUser**：实现 Spring Security `UserDetails`，聚合 `SysUser` 和权限集合、token、登录时间/IP/设备信息等，是安全框架在会话中使用的登录用户载体。
- **SysUser**：继承 `BaseEntity`，表示系统用户，包含账号、邮箱、手机号、性别、头像、密码、状态、部门与角色集合等，并提供 `isAdmin` 等判定方法作为权限控制基础。
- **SysDept**：继承 `BaseEntity`，表示部门节点，支持父子结构、排序和领导信息，用于组织树构建和数据权限过滤。
- **SysRole**：继承 `BaseEntity`，表示角色实体，包含角色标识、数据范围、菜单/部门关联及权限集合，`isAdmin` 方法用于快速判定超级管理员。
- **SysMenu**：继承 `BaseEntity`，表示菜单/按钮，包含路由路径、组件、是否外链、显示状态、权限标识等，用于前端路由与权限控制。
- **SysDictType**：继承 `BaseEntity`，表示字典类型（如“性别”、“状态”），配合 `SysDictData` 使用，用于动态下拉选项配置。
- **SysDictData**：继承 `BaseEntity`，表示具体字典项（标签、值、样式、默认标记等），被 `DictUtils` 缓存和转换，用于前端展示与导出。
- **BaseEntity**：所有业务实体的基础类，统一提供创建人/创建时间、修改人/修改时间、备注和扩展参数 Map 等公共元数据。
- **TreeEntity**：在 `BaseEntity` 基础上增加树形结构字段（父 ID、父名称、排序、祖级列表与 children），作为组织/菜单等树形实体的通用父类。
- **TreeSelect**：树形下拉组件专用 DTO，提供 id/label/value/children，并通过构造器从 `SysDept`、`SysMenu` 构建树节点，便于前端直接消费。

### 4. 控制层与分页封装

- **AjaxResult**：继承 `HashMap<String, Object>`，提供 `success`/`error` 系列静态工厂方法，统一接口的 JSON 返回结构（code/msg/data），`BaseController` 大量依赖它快速构建返回值。
- **R<T>**：通用结果包装类，使用 `code/msg/data` 标准格式，提供一组 `ok`/`fail` 工厂方法，适合对外开放接口或 Feign 调用场景。
- **BaseController**：封装所有 Controller 通用逻辑：初始化数据绑定、开启/清理分页（依赖 `PageUtils`/`TableSupport`）、构造 `TableDataInfo`、`AjaxResult`，并通过 `SecurityUtils` 获取当前登录用户信息。
- **PageUtils**：基于 PageHelper 的分页工具，配合 `TableSupport` 构建分页参数，封装 `getDataTable` 以 `TableDataInfo` 返回统一分页结果。
- **SecurityUtils**：安全相关静态工具：从 Spring Security 上下文中提取 `LoginUser`、获取用户/部门 ID、用户名，以及密码加密/比对逻辑；通过抛出 `ServiceException` 统一错误处理。
- **SqlUtil**：对前端传入的排序字段做 SQL 关键字过滤与正则校验，必要时抛出 `UtilException`，防止 SQL 注入风险。
- **DateUtils**：在 commons-dateutils 基础上扩展日期格式常量、日期格式化/解析、日期差值、服务器启动时间获取等，供日志、文件命名、Excel 导出等场景复用。

### 5. 缓存与字典

- **RedisCache**：对 Spring `RedisTemplate` 做二次封装，提供对象、List、Set、Map 的通用缓存读写与过期控制，是系统 Redis 访问的统一入口。
- **DictUtils**：封装字典缓存处理：通过 `SpringUtils` 获取 `RedisCache` Bean，将 `SysDictData` 列表按 key 存入 Redis，并提供 `getDictLabel`/`getDictValue` 等转换方法，广泛用于显示值与字典值之间的转换。
- **SpringUtils**：实现 `BeanFactoryPostProcessor` 和 `ApplicationContextAware`，在静态上下文中保存 BeanFactory/ApplicationContext，提供静态 `getBean`、获取 profile、AOP 代理等能力，供工具类在无注入场景下获取 Spring Bean 和环境配置。
- **IdUtils**：主键/随机串生成工具类，对自定义 `UUID` 进行封装，提供随机 UUID、简化 UUID 和高性能 UUID 生成方法。
- **UUID**：自定义 UUID 实现，支持快速 UUID 生成、基于名字/字符串的 UUID、版本/变体等属性解析，部分错误场景抛出 `UtilException`，保证输入合法。
- **UtilException**：运行时异常包装类，在工具类中统一抛出，用于把检查型异常转换为非检查型异常。

### 6. 序列号与加解密

- **Seq**：序列号工具，基于日期（`DateUtils.dateTimeNow`）和自增 `AtomicInteger` 生成全局唯一 ID，支持类型前缀和补零（通过 `StringUtils.padl`），广泛用于上传文件名等场景。
- **Md5Utils**：提供字符串 MD5 摘要算法实现（内部字节数组转十六进制），常用于签名校验或简单一致性校验。
- **Base64**：自实现 Base64 编解码工具（不依赖 JDK 内置），通过字符表和位运算实现 encode/decode，供部分安全或文件处理场景使用。

### 7. Bean 校验与反射工具

- **BeanValidators**：封装基于 `Validator` 的 Bean 校验逻辑，统一在校验失败时抛出 `ConstraintViolationException`，方便上层全局异常处理。
- **BeanUtils**：扩展 Spring `BeanUtils`，提供 `copyBeanProp`、setter/getter 列表获取及方法名与属性名匹配判断，用于 DTO 与实体之间的字段复制。
- **ReflectUtils**：提供基于反射的 getter/setter 调用、字段读写、方法访问权限修改、泛型类型解析和异常包装等能力，并结合 `Convert`、`DateUtils`、`StringUtils` 完成字符串/日期到属性类型的转换，这在 Excel 导入、动态映射时非常关键。

### 8. 消息、多语言与业务异常

- **MessageUtils**：通过 `SpringUtils.getBean` 获取消息源，根据 code 和参数返回多语言消息文本，`BaseException` 使用它实现国际化错误信息。
- **ServiceException**：对业务服务层错误的统一运行时异常封装，带有 code、message、detailMessage 字段，`SecurityUtils` 在用户信息获取失败时会抛出该异常。
- **BaseException**：通用基础异常类，支持模块名、消息 code、参数和默认消息；内部通过 `MessageUtils` 和 `StringUtils` 组合出最终消息字符串。
- **UserException**：继承自 `BaseException` 的用户相关异常基类，用于登录、验证等用户业务错误的统一封装。
- **FileException**：继承 `BaseException`，专门用于文件相关异常（超长、超大、非法扩展名等）的顶层封装，让文件处理错误有统一异常层级。
- **DemoModeException**：在演示模式下禁止某些操作时抛出的运行时异常，结合 `RuoYiConfig.demoEnabled` 实现只读演示环境。
- **GlobalException**：包含 message 和 detailMessage 的通用异常，用于一些需要更细致错误描述的全局业务错误。
- **TaskException**：计划任务相关异常，带有内部枚举 `Code` 表示错误类型，用于调度任务执行中的错误区分。

### 9. 文本与 HTML 处理

- **HTMLFilter**：对 HTML 字符串进行过滤和清洗，删除危险标签与属性，保留白名单，对注释与实体进行解析，是防止 XSS 的核心组件之一。
- **EscapeUtil**：封装转义/反转义/清理文本的逻辑，通过 `HTMLFilter` 过滤潜在危险 HTML，并借助 `StringUtils.isEmpty` 做空值安全判断。
- **LogUtils**：对日志中的对象做统一包装（如加方括号等），便于日志格式统一与审计。
- **ExceptionUtil**：将异常栈转为字符串，并获取根因错误信息，同时利用 `StringUtils.defaultString` 保证空安全。

### 10. HTTP 与 IP 工具

- **HttpUtils**：封装基于 JDK 的 HTTP/HTTPS GET/POST/SSL 请求逻辑，配合 `StringUtils.isNotBlank` 处理可选参数，用于调用外部服务（如 IP 地址解析等）。
- **HttpHelper**：从 `ServletRequest` 中读取请求体并转为字符串，主要用于日志记录或签名校验场景。
- **AddressUtils**：通过 IP 地址调用第三方接口（使用 `HttpUtils`）获取地理位置，同时根据 `RuoYiConfig.isAddressEnabled` 控制是否启用该功能，并用 `IpUtils.internalIp` 处理内网 IP。
- **IpUtils**：提供获取请求 IP、判断是否内网 IP、IP 文本转字节、获取本机 IP/主机名、多级代理头解析等功能，配合 `StringUtils` 处理请求头和空值。

### 11. 文件上传/下载与类型识别

- **FileUploadUtils**：统一封装文件上传逻辑：使用 `RuoYiConfig.getProfile` 确定根目录，结合 `DateUtils.datePath` 和 `Seq.getId` 生成文件路径；校验文件名长度和大小（抛出对应异常）、判断扩展名是否合法，是所有上传接口的核心工具。
- **FileNameLengthLimitExceededException**：当上传文件名超过限制时抛出，继承 `FileException`，由 `FileUploadUtils` 触发。
- **FileSizeLimitExceededException**：当上传文件大小超出上限时抛出，继承 `FileException`，由 `FileUploadUtils` 触发。
- **InvalidExtensionException**：当文件扩展名不在允许列表中时抛出，内部还细分图片、Flash、媒体、视频四类子异常；由 `FileUploadUtils.assertAllowed` 根据 `MimeTypeUtils` 判断后抛出。
- **MimeTypeUtils**：维护各类文件对应的后缀数组，并根据 MIME 类型返回文件扩展名，为上传时扩展名判定提供依据。
- **FileUtils**：封装文件字节写入、临时导入文件写入、校验文件名合法性、设置下载响应头、根据魔数识别文件类型、提取文件名和不带后缀名等逻辑，并依赖 `RuoYiConfig.getImportPath`、`FileUploadUtils` 等协调存储路径。
- **FileTypeUtils**：根据文件/路径或字节内容判断文件类型和扩展名，主要用于安全检查和文件显示。
- **ImageUtils**：基于 `RuoYiConfig.getProfile` 读取图片或任意文件内容，支持返回字节数组或 `InputStream`，用 `StringUtils.substringAfter` 处理路径拆分，常用于图片预览与导出。

### 12. Excel 导入导出

- **ExcelHandlerAdapter**：导出时的自定义格式化接口，允许调用方指定如何将字段值转换为显示文本（如字典翻译、自定义格式）。
- **ExcelUtil<T>**：Excel 通用工具类，支持导入/导出/下载模板，依赖 `DictUtils` 做字典转换、`ReflectUtils` 反射赋值、`Convert` 类型转换、`DateUtils` 日期处理、`ImageUtils`/`FileUtils` 写入图片和文件，并通过 `RuoYiConfig.getDownloadPath` 将生成文件路径包装为 `AjaxResult` 返回给前端。

### 13. 验证码与用户登录相关异常

- **CaptchaExpireException**：验证码过期时抛出的异常，继承 `UserException`，用于与其他用户错误区分。
- **UserPasswordRetryLimitExceedException**：密码重试次数超限时抛出，继承 `UserException`，通常用于登录防暴力破解。
- **UserPasswordNotMatchException**：登录时密码不匹配时抛出，继承 `UserException`。
- **CaptchaException**：验证码错误（而非过期）时抛出，继承 `UserException`。

### 14. 通用常量

- **Constants**：系统级通用常量，包括编码、协议前缀、登录结果文案、token、JWT 字段名、资源前缀以及外部调用相关的 HMAC 与 APP ID 等常量。
- **CacheConstants**：约定 Redis 中各类缓存 key 前缀，如登录 token、验证码、系统配置、字典缓存、幂等性、限流、密码错误次数等。
- **HttpStatus**：定义业务层使用的 HTTP 状态码常量，统一成功、客户端错误、服务端错误等编码。
- **ScheduleConstants**：调度任务相关常量，如任务类名、任务属性名及 misfire 策略标识，并内置状态枚举。
- **UserConstants**：用户/部门/字典状态、菜单类型、内外链标记以及用户名/密码长度约束等业务常量。
- **GenConstants**：代码生成模块使用的模板类型标识、树型配置字段、列类型分组及前端控件类型（输入框、下拉框、上传等）、Java 类型和查询规则常量。

---

## 三、关系线逐条解读

> 说明：以下按 UML 中出现的连线顺序逐条解释。

### 1. 基础字符串与转换工具

- `CharsetKit --> StringUtils`：`CharsetKit` 在进行编码转换时，会用 `StringUtils` 判断字符串是否为空，从而避免空指针和无效转换。
- `StringUtils <|-- StringUtils`：自定义 `StringUtils` 继承了 Apache 的 `StringUtils`，在保留原有功能的基础上扩展了项目特有的字符串工具方法。
- `StringUtils --> StrFormatter`：`StringUtils` 在某些格式化场景中会委托 `StrFormatter` 实现占位符替换，从而实现统一的格式化逻辑。
- `StringUtils --> StringUtils`：表示内部方法之间的自调用，如高阶方法复用基础空判断/截取方法，减少重复实现。
- `StrFormatter --> Convert`：`StrFormatter` 在处理可变参数时，通过 `Convert.utf8Str` 将各种对象安全地转为字符串进行拼接。
- `StrFormatter --> StringUtils`：格式化前使用 `StringUtils.isEmpty` 等判断模板或参数是否为空，保证格式化逻辑健壮。
- `Convert --> StringUtils`：`Convert` 在做类型转换时通过 `StringUtils.isEmpty` 等过滤空串或非法输入，避免抛出异常或产生无意义结果。

### 2. 分页与请求解析

- `TableSupport --> PageDomain`：`TableSupport` 负责创建并填充分页参数对象 `PageDomain`，为后续分页插件/查询提供统一入口。
- `TableSupport --> Convert`：从请求参数中读取的页码/大小字符串会通过 `Convert.toInt` 转成整数，确保类型正确。
- `TableSupport --> ServletUtils`：通过 `ServletUtils.getParameter` 等方法从当前请求中获取分页相关参数。
- `TableSupport --> PageDomain`（多条）：强调 `TableSupport` 对 `PageDomain` 的多次使用与返回，体现它是分页参数的核心载体。
- `PageDomain --> StringUtils`：`PageDomain.getOrderBy` 在生成排序字符串前会用 `StringUtils` 判断是否为空，并做驼峰转下划线处理，防止 SQL 注入和格式错误。
- `ServletUtils --> Convert`：`ServletUtils` 将请求参数转换为 `Integer`、`Boolean`、`String` 时统一委托 `Convert` 实现。
- `ServletUtils --> StringUtils`：使用 `StringUtils.inStringIgnoreCase` 判断请求头是否包含 Ajax 标识，以识别异步请求。

### 3. 登录体与登录用户

- `RegisterBody <|-- LoginBody`：`RegisterBody` 继承 `LoginBody`，在注册场景重用用户名、密码、验证码等属性，减少重复定义。
- `LoginUser --> SysUser`：`LoginUser` 内部持有 `SysUser` 实体，通过它获取用户名、密码及基础信息，是 Security 框架与业务用户信息之间的桥梁（多条箭头表示多处使用）。
- `SysUser <|-- BaseEntity`：`SysUser` 继承 `BaseEntity`，复用了审计字段（创建人/时间等），统一了实体基础信息管理。
- `SysUser --> BaseEntity`：`SysUser` 调用父类 `BaseEntity` 的 getter 方法，以在 `toString` 或业务逻辑中输出/使用这些公共字段。
- `SysUser --> SysDept`：`SysUser` 关联 `SysDept` 表示用户所属部门，为组织结构与数据权限控制提供基础。
- `SysDept <|-- BaseEntity`：`SysDept` 继承基础实体，具备统一的审计信息。
- `SysDept --> BaseEntity`：`SysDept` 在业务或序列化场景中会直接读取父类的公共字段。
- `SysDictData <|-- BaseEntity`：`SysDictData` 继承自 `BaseEntity`，字典数据也具备创建/修改等公共信息。
- `SysDictData --> BaseEntity`：`SysDictData` 直接使用父类审计字段进行展示或日志输出。
- `SysMenu <|-- BaseEntity`：`SysMenu` 继承基础实体，菜单信息也记录创建修改人等元信息。
- `SysMenu --> BaseEntity`：`SysMenu` 通过父类方法获取这些审计字段，例如在 `toString` 中输出。
- `SysRole <|-- BaseEntity`：`SysRole` 继承基础实体，使角色配置具备统一审计字段。
- `SysRole --> BaseEntity`：`SysRole` 在日志或界面展示时会借助父类方法展示创建人等信息。
- `SysDictType <|-- BaseEntity`：`SysDictType` 作为业务实体，也继承基础审计信息。
- `SysDictType --> BaseEntity`：`SysDictType` 通过父类访问这些元数据。
- `TreeEntity <|-- BaseEntity`：`TreeEntity` 拓展了 `BaseEntity`，为树形结构实体提供统一基础字段。
- `TreeSelect --> SysDept`：`TreeSelect` 构造器从 `SysDept` 中读取部门 ID、名称和子部门，用于构建部门树下拉数据。
- `TreeSelect --> SysMenu`：同理，`TreeSelect` 也可从 `SysMenu` 构造菜单树结构给前端。

### 4. Ajax 结果与控制器

- `AjaxResult --> StringUtils`：构造数据时用 `StringUtils.isNotNull` 判断 data 是否存在，从而决定是否放入结果 Map 中。
- `BaseController --> AjaxResult`：`BaseController` 封装了大量返回 `AjaxResult` 的方法，用于统一 REST 接口的成功/失败返回格式。
- `BaseController --> LoginUser`：`BaseController` 通过 `getLoginUser` 获取当前用户信息，为控制层提供快捷访问登录用户的能力。
- `BaseController --> PageDomain`：在分页查询时，控制器使用 `PageDomain.getOrderBy` 生成排序条件，用于排序构造。
- `BaseController --> TableDataInfo`：`BaseController` 构造 `TableDataInfo` 返回分页数据列表及总数，实现统一分页响应。
- `BaseController --> TableSupport`：通过 `TableSupport.buildPageRequest` 读取请求中的分页参数，并应用到查询中。
- `BaseController --> DateUtils`：在绑定或参数转换时使用 `DateUtils.parseDate` 处理日期字符串。
- `BaseController --> PageUtils`：通过 `PageUtils.startPage/clearPage` 开启与清理分页上下文，简化分页查询代码。
- `BaseController --> SecurityUtils`：通过 `SecurityUtils.getLoginUser` 等方法获取当前用户 ID、部门 ID、用户名，统一从安全上下文中取值。
- `BaseController --> StringUtils`：对提示语、分页参数等进行空判断或格式化输出。
- `BaseController --> SqlUtil`：对前端传入的排序字段调用 `SqlUtil.escapeOrderBySql` 做安全过滤，防止 SQL 注入。

### 5. 日期与分页工具

- `DateUtils <|-- DateUtils`：项目自定义的 `DateUtils` 继承了 Apache 的 `DateUtils` 基类，扩展出更符合业务的日期格式和工具方法。
- `DateUtils --> DateUtils`：内部方法可能复用父类或自身的日期解析逻辑，以统一实现。
- `PageUtils --> PageDomain`：`PageUtils` 利用 `PageDomain` 获取页码、每页大小和排序，配置分页插件执行查询。
- `PageUtils --> TableDataInfo`：查询结果转换为 `TableDataInfo`，提供统一分页响应对象。
- `PageUtils --> TableSupport`：通过 `TableSupport.buildPageRequest` 解析请求参数得到 `PageDomain`。
- `PageUtils --> SqlUtil`：将 `PageDomain` 的排序信息通过 `SqlUtil.escapeOrderBySql` 清洗后再传给底层分页插件，确保安全。

### 6. 安全与 SQL 工具

- `SecurityUtils --> LoginUser`：`SecurityUtils` 在获取登录用户信息时直接返回 `LoginUser`，供业务层使用。
- `SecurityUtils --> ServiceException`：当安全上下文中用户信息缺失或不合法时抛出 `ServiceException`，统一异常类型，便于全局处理。
- `SqlUtil --> UtilException`：当检测到非法排序字段或关键字注入时抛出 `UtilException`，中断请求处理。
- `SqlUtil --> StringUtils`：在校验排序字符串时依赖 `StringUtils` 做空判断和分割，提升健壮性。

### 7. Redis 缓存与字典工具

- `RedisCache --> RedisTemplate`：`RedisCache` 内部持有 `RedisTemplate`，所有缓存操作最终委托给 Spring 的 Redis 客户端。
- `DictUtils --> SysDictData`：`DictUtils` 从 `SysDictData` 对象中读取 label/value 等属性，用于翻译字典项。
- `DictUtils --> RedisCache`：字典数据统一存入 `RedisCache`，从 Redis 中读取或清理缓存字典集合。
- `DictUtils --> StringUtils`：在匹配字典值或处理分隔符时使用 `StringUtils` 的空判断、裁剪和包含判断。
- `DictUtils --> SpringUtils`：通过 `SpringUtils.getBean` 延迟获取 `RedisCache` 或其他依赖 Bean，无需在调用方显示注入。
- `SpringUtils --> StringUtils`：`SpringUtils` 在获取当前激活 profile 或属性时，通过 `StringUtils.isNotEmpty` 做结果判空。

### 8. ID 与异常工具

- `IdUtils --> UUID`：`IdUtils` 使用自定义 `UUID` 类生成随机/快速 UUID，并转为字符串形式对外提供。
- `UUID --> UtilException`：当 UUID 输入格式异常或时间戳不合法时，`UUID` 抛出 `UtilException` 封装底层错误。
- `Seq --> DateUtils`：`Seq` 通过 `DateUtils.dateTimeNow` 获取当前时间串，再拼接自增序列生成唯一 ID。
- `Seq --> StringUtils`：`Seq` 调用 `StringUtils.padl` 对序列号进行左侧补零，保证固定长度的序列部分。
- `ReflectUtils --> Convert`：`ReflectUtils` 在用反射给字段赋值时，借助 `Convert` 将字符串转换为字段所需的目标类型。
- `ReflectUtils --> DateUtils`：对日期字段赋值时，先用 `DateUtils.parseDate` 将字符串解析为 Date。
- `ReflectUtils --> StringUtils`：在解析属性名、方法名和字段名时利用 `StringUtils` 做分割、大小写变换等。

### 9. 消息、多语言与文本转义

- `MessageUtils --> SpringUtils`：`MessageUtils` 通过 `SpringUtils.getBean` 获取消息源 Bean，从而实现国际化消息解析。
- `EscapeUtil --> StringUtils`：转义/清理文本前进行空字符串判断，避免无意义处理。
- `EscapeUtil --> HTMLFilter`：`EscapeUtil` 通过创建 `HTMLFilter` 并调用其 `filter` 方法清理 HTML 标签，实现 XSS 过滤。
- `HttpUtils --> StringUtils`：发起 HTTP 请求前用 `StringUtils.isNotBlank` 判断参数是否为空，从而决定是否附加 query 参数。
- `AddressUtils --> RuoYiConfig`：`AddressUtils` 根据 `RuoYiConfig.isAddressEnabled` 来判断是否需要进行 IP 地址解析，受配置开关控制。
- `AddressUtils --> StringUtils`：解析 IP 或接口返回内容前用 `StringUtils.isEmpty` 检查，防止无效调用。
- `AddressUtils --> HttpUtils`：通过 `HttpUtils.sendGet` 请求外部 IP 地址归属地服务。
- `AddressUtils --> IpUtils`：先用 `IpUtils.internalIp` 判断是否内网 IP，内网 IP 一般不调用外部地址解析。
- `IpUtils --> StringUtils`：处理请求头和 IP 字符串时通过 `StringUtils.isNull/isBlank` 判断，确保逻辑严谨。

### 10. 文件上传与文件工具

- `FileUploadUtils --> RuoYiConfig`：上传根目录通过 `RuoYiConfig.getProfile` 获取，实现配置化存储路径。
- `FileUploadUtils --> FileNameLengthLimitExceededException`：当文件名超过最大长度时抛出该异常，阻止存储。
- `FileUploadUtils --> FileSizeLimitExceededException`：当文件大小超出最大限制时抛出该异常。
- `FileUploadUtils --> InvalidExtensionException`：当上传文件扩展名不在允许列表时，抛出相应的非法扩展名异常。
- `FileUploadUtils --> DateUtils`：构造上传路径时使用 `DateUtils.datePath` 生成按日期分目录的路径。
- `FileUploadUtils --> StringUtils`：在解析文件名、扩展名等时利用 `StringUtils.substring/format` 处理字符串。
- `FileUploadUtils --> MimeTypeUtils`：根据文件 MIME 类型，使用 `MimeTypeUtils.getExtension` 识别扩展名并对比白名单。
- `FileUploadUtils --> Seq`：使用 `Seq.getId` 生成唯一文件名，防止重名覆盖。
- `FileNameLengthLimitExceededException <|-- FileException`：`FileNameLengthLimitExceededException` 继承文件异常基类 `FileException`，让调用方按统一文件异常链路处理。
- `FileNameLengthLimitExceededException --> FileException`：构造异常时调用 `FileException` 构造器初始化基础异常信息。
- `FileSizeLimitExceededException <|-- FileException`：同理，文件大小超过限制时的异常继承自 `FileException`。
- `FileSizeLimitExceededException --> FileException`：通过父类构造器传递模块、消息等信息。
- `InvalidExtensionException <|-- FileUploadException`：非法扩展名异常继承自 `FileUploadException`（外部类），方便与其他上传异常统一处理。
- `FileUtils --> RuoYiConfig`：`FileUtils` 通过 `RuoYiConfig.getImportPath` 获取导入文件目录前缀。
- `FileUtils --> DateUtils`：创建临时导入文件名时使用日期路径作为子目录。
- `FileUtils --> FileTypeUtils`：通过 `FileTypeUtils.getFileType` 确定文件类型，用于安全校验或后缀判断。
- `FileUtils --> FileUploadUtils`：利用 `FileUploadUtils.getAbsoluteFile/getPathFileName` 实现统一的路径拼接与物理文件生成。
- `FileUtils --> IdUtils`：使用 `IdUtils.fastUUID` 生成唯一文件名，避免重复。
- `FileUtils --> StringUtils`：校验文件名是否包含非法字符或路径穿越时用 `StringUtils.contains` 等方法。

### 11. 图片与 Excel 工具

- `ImageUtils --> RuoYiConfig`：通过 `RuoYiConfig.getProfile` 计算图片物理存储路径，从而读取图片数据。
- `ImageUtils --> StringUtils`：使用 `StringUtils.substringAfter` 截取 URL 中相对路径部分，拼装实际文件路径。
- `ExcelUtil~T~ --> RuoYiConfig`：导出 Excel 文件时使用 `RuoYiConfig.getDownloadPath` 确定文件下载目录。
- `ExcelUtil~T~ --> AjaxResult`：导出/下载模板等操作返回 `AjaxResult`，将文件地址或下载链接包装在统一响应结构中。
- `ExcelUtil~T~ --> Convert`：在导入/导出过程中将单元格内容转换为字段类型（数字、布尔、日期、字符串等）。
- `ExcelUtil~T~ --> UtilException`：当反射赋值、类型转换或文件 IO 出错时抛出 `UtilException`，统一异常风格。
- `ExcelUtil~T~ --> DateUtils`：解析和格式化 Excel 中的日期值。
- `ExcelUtil~T~ --> DictUtils`：在导出时将字典值转为标签，在导入时将标签反向转为字典值。
- `ExcelUtil~T~ --> StringUtils`：对单元格内容做空判断、格式化和字符串处理（如去除多余分隔符、判断数字等）。
- `ExcelUtil~T~ --> FileTypeUtils`：处理插入图片或附件时，用 `FileTypeUtils.getFileExtendName` 识别文件类型。
- `ExcelUtil~T~ --> FileUtils`：将导出结果写入磁盘或读取导入文件字节时使用 `FileUtils.writeImportBytes` 等方法。
- `ExcelUtil~T~ --> ImageUtils`：在 Excel 中嵌入图片时通过 `ImageUtils.getImage` 获取图片字节。
- `ExcelUtil~T~ --> ReflectUtils`：通过反射给对象字段赋值或读取字段值，实现字段与 Excel 列的动态映射。
- `ExcelUtil~T~ --> UUID`：用于生成导出文件的唯一文件名或图片名称，避免冲突。

### 12. 用户与验证码相关异常关系

- `CaptchaExpireException <|-- UserException`：`CaptchaExpireException` 继承 `UserException`，说明它是一种特定的用户业务异常（验证码过期）。
- `CaptchaExpireException --> UserException`：构造函数中通过调用 `UserException` 的构造器设置模块和消息 key。
- `UserException <|-- BaseException`：`UserException` 继承 `BaseException`，沿用模块化、国际化和参数化消息能力。
- `UserException --> BaseException`：构造时调用父类构造函数传入模块名和消息参数。
- `UserPasswordRetryLimitExceedException <|-- UserException`：密码重试次数超限被建模为一种特殊的用户异常。
- `UserPasswordRetryLimitExceedException --> UserException`：构造时调用父类构造函数设置错误消息 code 和参数（剩余次数等）。
- `UserPasswordNotMatchException <|-- UserException`：密码不匹配同样继承 `UserException`，便于统一捕获登录相关异常。
- `UserPasswordNotMatchException --> UserException`：构造器调用父类以设置默认登录失败消息。
- `CaptchaException <|-- UserException`：验证码内容错误的异常也归类为用户异常。
- `CaptchaException --> UserException`：构造时通过父类构造器传入对应消息 key。

### 13. 基础异常与文件异常层级

- `BaseException --> MessageUtils`：`BaseException.getMessage` 会调用 `MessageUtils.message` 根据 code 和参数解析消息，实现国际化。
- `BaseException --> StringUtils`：在 message 为空或 code 未配置时使用 `StringUtils.isEmpty` 判空，以决定退回默认消息。
- `FileException <|-- BaseException`：`FileException` 继承自 `BaseException`，使所有文件相关异常具备同样的国际化和模块化支持。
- `FileException --> BaseException`：构造时调用父类构造器传入文件模块标识和消息 key。

---

这些关系共同构成了以 `RuoYiConfig` 为配置核心、以“通用工具与契约”模块为支撑的基础设施层，为上层业务提供统一、安全且可复用的工具能力。

