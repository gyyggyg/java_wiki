from ast import pattern
import re
from typing import List, Tuple

def match_characteristic_info(class_code: str) -> str:
    match = re.search(r'public|private|protected', class_code)
    first_brace = match.start() if match else -1

    # 提取大括号之后的内容
    after_brace = class_code[first_brace:]

    # 找到第一个函数的位置（public 或 private 开头，后面跟着返回类型和括号）
    # 匹配模式：访问修饰符 + 返回类型 + 方法名 + ()
    method_pattern = r'\s+(public|private|protected)\s+\w+(\s+[\w<>,\s]+)?\s+\w+\s*\('
    match = re.search(method_pattern, after_brace)

    if match:
        # 提取从开始到第一个函数之前的所有内容
        attributes_section = after_brace[:match.start()]
    else:
        attributes_section = after_brace
    return attributes_section.strip()

# 测试代码
interface_code = '''
package com.macro.mall.model;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class OmsOrderExample imp abc{
    protected String orderByClause;

    protected boolean distinct;

    protected List<Criteria> oredCriteria;

    public OmsOrderExample() {
        oredCriteria = new ArrayList<>();
    }

    public void setOrderByClause(String orderByClause) {
        this.orderByClause = orderByClause;
    }

    public String getOrderByClause() {
        return orderByClause;
    }

    public void setDistinct(boolean distinct) {
        this.distinct = distinct;
    }

    public boolean isDistinct() {
        return distinct;
    }

    public List<Criteria> getOredCriteria() {
        return oredCriteria;
    }

    public void or(Criteria criteria) {
        oredCriteria.add(criteria);
    }

'''

a = match_characteristic_info(interface_code)
print(a)