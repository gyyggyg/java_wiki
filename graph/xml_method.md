- 功能说明  
批量插入或替换商品SKU库存信息，当主键冲突时会用新数据替换原有记录。

- 字段表格  
| 字段名        | 含义           | 备注             |
|---------------|----------------|------------------|
| id            | SKU主键ID      | BIGINT           |
| product_id    | 商品ID         | BIGINT           |
| sku_code      | SKU编码        | VARCHAR          |
| price         | 销售价         | DECIMAL          |
| stock         | 库存           | INTEGER          |
| low_stock     | 预警库存       | INTEGER          |
| pic           | 展示图片URL    | VARCHAR          |
| sale          | 销量           | INTEGER          |
| sp_data       | 商品销售属性   | VARCHAR（JSON）  |

- 效果示例  
假设传入的skuStockList包含两条数据：

```
{
  "id": 101,
  "productId": 2001,
  "skuCode": "A1001",
  "price": 59.99,
  "stock": 100,
  "lowStock": 10,
  "pic": "http://img.com/sku101.jpg",
  "sale": 5,
  "spData": "{\"color\":\"red\",\"size\":\"M\"}"
},
{
  "id": 102,
  "productId": 2001,
  "skuCode": "A1002",
  "price": 69.99,
  "stock": 50,
  "lowStock": 5,
  "pic": "http://img.com/sku102.jpg",
  "sale": 3,
  "spData": "{\"color\":\"blue\",\"size\":\"L\"}"
}
```
执行后实际SQL片段为：

```
REPLACE INTO pms_sku_stock (id, product_id, sku_code, price, stock, low_stock, pic, sale, sp_data)
VALUES
(101, 2001, 'A1001', 59.99, 100, 10, 'http://img.com/sku101.jpg', 5, '{"color":"red","size":"M"}'),
(102, 2001, 'A1002', 69.99, 50, 5, 'http://img.com/sku102.jpg', 3, '{"color":"blue","size":"L"}')
```

- 注意事项  
- 此方法使用`REPLACE INTO`，会先删除主键冲突的原有记录再插入新记录，导致自增主键可能重新编号，且原有记录相关的外键或依赖数据会受影响，使用时需注意数据完整性和关联更新。

下面介绍该方法所属的文件、接口、方法的基本信息

| 文件 | 接口 | 方法 |
| --- | --- | --- |
| mall-admin/src/main/java/com/macro/mall/dao/PmsSkuStockDao.java | PmsSkuStockDao | replaceList |
| 该文件定义了一个名为PmsSkuStockDao的接口，属于com.macro.mall.dao包，专门用于商品SKU库存的批量数据库操作。它提供了两种批量操作方法：insertList用于批量插入多个SKU库存记录，replaceList用于批量插入或替换多个SKU库存记录，旨在提高SKU库存数据的持久化效率。 | PmsSkuStockDao接口定义了针对商品SKU库存表的批量数据操作方法，包含批量插入和批量插入或替换两种操作，专注于高效地将多个PmsSkuStock对象持久化到数据库中，实现商品SKU库存数据的快速批量更新。 | replaceList方法用于批量插入或替换商品SKU库存信息。该方法接收一个PmsSkuStock对象列表作为参数，执行批量数据库操作，将列表中的每个SKU库存对象对应的数据插入到数据库中，如果记录已存在则进行替换更新，从而实现SKU库存数据的批量同步和维护。 |