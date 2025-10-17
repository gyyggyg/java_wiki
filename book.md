# 2. 对外提供接口说明文档

## 1. 功能分析

### 1.1 本项目对外提供的服务

本Java项目围绕图书馆管理系统，主要对外提供如下服务：

#### 1.1.1 书籍的搜索与借阅服务
- **搜索服务**：支持通过关键字对书籍进行搜索，包括区分大小写和不区分大小写的搜索。
- **借阅服务**：允许对书籍进行借出和归还操作，支持自动资源管理。

#### 1.1.2 会员借书与通知服务
- **会员借书**：会员可借阅书籍并自动记录借阅历史。
- **通知服务**：当有新书加入时，系统可通知所有活跃会员。

#### 1.1.3 图书馆书籍管理与导出服务
- **添加书籍**：可新增书籍到图书馆，并自动校验书籍内容有效性。
- **按作者查找书籍**：支持根据作者名筛选并排序书籍列表。
- **导出书籍列表**：可将书籍列表导出到指定文件。
- **按出版商分类描述**：可根据出版商获取对应的类别描述。

#### 1.1.4 统一的接口抽象服务
- **Searchable接口**：为支持搜索功能的实体（如Book）提供统一接口。
- **Borrowable接口**：为支持借用与归还资源的实体（如Book）提供统一接口，便于资源自动管理。

### 1.2 服务之间的关系

- `Library` 是系统的核心管理类，负责维护书籍集合和会员集合，对外聚合提供书籍相关管理、查找、导出、通知等服务。
- `Book` 实现了 `Searchable` 和 `Borrowable` 两大接口，作为系统中支持被搜索和借用的主要实体，服务于会员的借书和书籍检索功能。
- `Member` 代表图书馆会员，能执行借书操作和接收新书通知，与 `Book` 及 `Library` 紧密协作。
- `Searchable` 和 `Borrowable` 为系统提供统一的搜索和借用能力抽象，便于扩展和多态调用。

## 2. 调用类说明

### 2.1 服务类及其功能说明

#### 2.1.1 Library

- **功能**：  
  - 管理整个图书馆的书籍（添加、查找、导出）、会员集合和借阅队列。
  - 提供单例访问方式（Singleton）。
  - 负责通知活跃会员新书信息、验证书籍内容、按作者查找书籍、导出书籍列表、根据出版商获取类别描述等高级功能。
- **所属文件**：  
  - `src/com/library/core/Library.java`
- **Package**：  
  - `com.library.core`

#### 2.1.2 Book

- **功能**：  
  - 表示具体的书籍实体，具备丰富的字段和多种操作。
  - 实现了 `Searchable` 和 `Borrowable`，支持关键字搜索、忽略大小写搜索、书籍借阅与归还。
  - 提供书籍元数据管理、标签管理、链式调用、静态统计、同步更新等多样化方法。
- **所属文件**：  
  - `src/com/library/core/Book.java`
- **Package**：  
  - `com.library.core`

#### 2.1.3 Member

- **功能**：  
  - 表示图书馆会员，包含会员信息、借书、通知、历史记录管理等能力。
  - 支持借阅书籍（调用Book的borrow相关方法），接收新书通知。
- **所属文件**：  
  - `src/com/library/core/Member.java`
- **Package**：  
  - `com.library.core`

#### 2.1.4 Searchable (接口)

- **功能**：  
  - 提供支持搜索功能的统一接口。
  - 定义抽象方法 `boolean search(String keyword)`，默认方法 `boolean searchIgnoreCase(String keyword)`，静态方法 `normalizeKeyword(String keyword)`。
- **所属文件**：  
  - `src/com/library/interfaces/Searchable.java`
- **Package**：  
  - `com.library.interfaces`

#### 2.1.5 Borrowable (接口)

- **功能**：  
  - 提供支持借用和归还功能的统一接口。
  - 定义抽象方法 `void borrow()` 和 `void returnItem()`，默认实现 `close()` 方法以便资源自动管理。
- **所属文件**：  
  - `src/com/library/interfaces/Borrowable.java`
- **Package**：  
  - `com.library.interfaces`## 3. 数据结构说明

### 3.1 类与接口结构总览

涉及的主要类与接口如下：

- `com.library.core.Library`
- `com.library.core.Book`
- `com.library.core.Member`
- `com.library.interfaces.Searchable`
- `com.library.interfaces.Borrowable`

---

### 3.2 详细类与方法说明

#### 3.2.1 com.library.core.Library

**单例模式，需通过 `getInstance()` 获取对象。**

##### 3.2.1.1 主要方法及签名

```java
public static synchronized Library getInstance()
public void addBook(Book book)
public List<Book> findBooksByAuthor(String author)
public void exportBooks(String filename)
public String getCategoryDescription(Book.Publisher publisher)
```

##### 3.2.1.2 方法说明与参数

- **getInstance()**
  - **用途**：获取唯一 `Library` 实例。
  - **用法**：
    ```java
    import com.library.core.Library;
    Library lib = Library.getInstance();
    ```

- **addBook(Book book)**
  - **用途**：向图书馆添加新书。
  - **参数**：`book` - `com.library.core.Book` 实例
  - **示例**：
    ```java
    Book b = new Book("123456", "Java编程", "张三");
    lib.addBook(b);
    ```

- **findBooksByAuthor(String author)**
  - **用途**：查找指定作者的所有书籍，返回按类别排序的列表。
  - **参数**：`author` - 作者名
  - **返回**：`List<Book>`
  - **示例**：
    ```java
    List<Book> books = lib.findBooksByAuthor("张三");
    ```

- **exportBooks(String filename)**
  - **用途**：将当前所有书籍名称导出到指定文件。
  - **参数**：`filename` - 文件路径
  - **示例**：
    ```java
    lib.exportBooks("books.txt");
    ```

- **getCategoryDescription(Book.Publisher publisher)**
  - **用途**：根据出版商对象，获取类别描述。
  - **参数**：`publisher` - `Book.Publisher` 实例
  - **返回**：`String` （如 "Educational", "Entertainment", "General"）
  - **示例**：
    ```java
    Book.Publisher p = new Book.Publisher("Academic Press");
    String desc = lib.getCategoryDescription(p);
    ```

---

#### 3.2.2 com.library.core.Book

**实现了 Searchable、Borrowable 两大接口。**

##### 3.2.2.1 主要方法及签名

```java
// 构造函数
public Book()
public Book(String isbn, String title, String author)
public Book(String... args)

// Searchable 接口实现
public boolean search(String keyword)
public boolean searchIgnoreCase(String keyword)

// Borrowable 接口实现
public void borrow()
public void returnItem()
public void close()

// 其他对外方法
public void setAuthor(String a)
public String getAuthor()
public void addTags(String... newTags)
public BookGenre getGenre()
public Book withTitle(String title)
public static int getTotalBooks()
public synchronized void updateMetadata(String key, Object value)
public void validateContent() throws LibraryException
public <T> List<T> getMetadataValues(Class<T> type)
public Comparator<Book> getComparator()
```

##### 3.2.2.2 方法说明与用法

- **构造函数**
  - 用于创建新书对象。
  - 示例：
    ```java
    Book b = new Book("123456", "Java编程", "张三");
    ```

- **search(String keyword) / searchIgnoreCase(String keyword)**
  - 用于关键字搜索（区分/不区分大小写）。
  - 返回 `boolean`
  - 示例：
    ```java
    boolean found = b.search("Java");
    boolean found2 = b.searchIgnoreCase("java");
    ```

- **borrow() / returnItem() / close()**
  - 用于借出、归还、自动资源管理。
  - 示例（try-with-resources）：
    ```java
    try (Book b = new Book(...)) {
        b.borrow();
        // ...
    } // 自动调用 returnItem()
    ```

- **addTags(String... newTags)**
  - 添加标签。
  - 示例：
    ```java
    b.addTags("技术", "编程");
    ```

- **getGenre()**
  - 获取书籍类别。
  - 返回：`BookGenre` 枚举

- **withTitle(String title)**
  - 链式设置标题。
  - 示例：
    ```java
    b.withTitle("新标题").setAuthor("新作者");
    ```

- **getTotalBooks()**
  - 静态方法，获取已创建书籍总数。

- **updateMetadata(String key, Object value)**
  - 同步方法，更新元数据。

- **validateContent()**
  - 校验书籍内容，异常时抛出 `LibraryException`。

- **getMetadataValues(Class<T> type)**
  - 泛型方法，获取指定类型的元数据值。

- **getComparator()**
  - 获取书籍比较器（按标题排序）。

##### 3.2.2.3 内部类用法

- **Book.Publisher**
  - 创建：`Book.Publisher p = new Book.Publisher("出版社名");`
- **Book.Review**
  - 创建：`Book.Review r = b.new Review("评论人", 5);`

---

#### 3.2.3 com.library.core.Member

##### 3.2.3.1 主要方法及签名

```java
public Member(String id, String name)
public boolean isActive()
public void notify(Book book)
public void borrowBook(Book book)
public Optional<BorrowRecord> getLastBorrow()
```

##### 3.2.3.2 方法说明与用法

- **Member(String id, String name)**
  - 构造新会员。
  - 示例：
    ```java
    Member m = new Member("U001", "李雷");
    ```

- **isActive()**
  - 判断会员是否活跃。

- **notify(Book book)**
  - 接收新书通知。

- **borrowBook(Book book)**
  - 借阅书籍，自动记录历史。
  - 示例：
    ```java
    m.borrowBook(b);
    ```

- **getLastBorrow()**
  - 获取最近一次借阅记录（`Optional<BorrowRecord>`）。

---

#### 3.2.4 com.library.interfaces.Searchable

##### 3.2.4.1 接口方法

```java
boolean search(String keyword)
default boolean searchIgnoreCase(String keyword)
static String normalizeKeyword(String keyword)
```

##### 3.2.4.2 用法

- 任何实现了 `Searchable` 的类（如 `Book`）都可作为搜索对象。
- **normalizeKeyword** 为静态方法，可直接调用：
    ```java
    String norm = Searchable.normalizeKeyword("  Java  ");
    ```

---

#### 3.2.5 com.library.interfaces.Borrowable

##### 3.2.5.1 接口方法

```java
void borrow()
void returnItem()
default void close()
```

##### 3.2.5.2 用法

- 任何实现 `Borrowable` 的类（如 `Book`）都可用作可借用资源。
- 支持自动资源管理（try-with-resources）：
    ```java
    try (Book b = new Book(...)) {
        b.borrow();
    }
    // 自动归还
    ```

---

### 3.3 导入与使用说明

#### 3.3.1 示例 import 语句

```java
import com.library.core.Library;
import com.library.core.Book;
import com.library.core.Member;
import com.library.interfaces.Searchable;
import com.library.interfaces.Borrowable;
```

#### 3.3.2 外部调用典型流程

```java
Library lib = Library.getInstance();
Book book = new Book("123456", "Java入门", "张三");
lib.addBook(book);

Member user = new Member("M001", "王五");
user.borrowBook(book);

List<Book> found = lib.findBooksByAuthor("张三");
lib.exportBooks("out.txt");
```

---