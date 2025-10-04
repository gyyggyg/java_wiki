#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KafkaInterface:
    def __init__(self, bootstrap_servers, client_id):
        """
        初始化Kafka生产者
        
        Args:
            bootstrap_servers: Kafka服务器地址，例如 'kafka:9092'
            client_id: 客户端ID
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        
        """启动生产者"""
        try:
            # 创建Kafka生产者实例
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id
            )
            logger.info(f"Kafka生产者启动成功，连接到: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"启动Kafka生产者失败: {e}")
    
    def send_message(self, topic, message_body, tags=None, keys=None):
        """
        发送消息到指定Topic
        
        Args:
            topic: 主题名称
            message_body: 消息内容，可以是字符串或字典
            tags: 消息标签（可选，将作为消息头）
            keys: 消息键（可选）
            
        Returns:
            bool: 发送是否成功
        """
        if not self.producer:
            logger.error("生产者未启动，请先调用start_producer()")
            return False
        
        try:
            # 序列化消息
            if isinstance(message_body, dict):
                message_value = json.dumps(message_body, ensure_ascii=False).encode('utf-8')
            else:
                message_value = str(message_body).encode('utf-8')
            
            # 序列化键
            message_key = keys.encode('utf-8') if keys else None
            
            # 发送消息
            future = self.producer.send(
                topic=topic,
                value=message_value,
                key=message_key
            )
            
            # 等待发送结果
            record_metadata = future.get(timeout=10)
            logger.info(f"消息发送成功: Topic={topic}, Partition={record_metadata.partition}, Offset={record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka消息发送失败: {e}")
            return False
        except Exception as e:
            logger.error(f"发送消息时发生未知错误: {e}")
            return False
    
    def shutdown(self):
        """关闭生产者"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka生产者已关闭")

def main():
    # Kafka配置
    BOOTSTRAP_SERVERS = '43.199.163.233:9092'  # 假设Kafka运行在9092端口
    TOPIC = 'TEST_MESSAGE'
    CLIENT_ID = 'py_kafka_producer'
    
    # 创建生产者实例
    mq_producer = KafkaInterface(BOOTSTRAP_SERVERS, CLIENT_ID)
    
    # 启动生产者
    if not mq_producer.start_producer():
        logger.error("无法启动Kafka生产者，程序退出")
        return
    
    try:
        
        # 示例1: 发送JSON格式的消息
        node_analyze_progress_message = {
            "spaceId": "123",
            "event": "node.analyze.progress",
            "data": {
                "progress": 35,
                "time": int(time.time()),
                "status": "analyzing",
                "remark": "解析进度35%"
            }
        }
  
        mq_producer.send_message(
            TOPIC, 
            node_analyze_progress_message, 
            tags='node.analyze'
        )

        time.sleep(2)

        # 示例2: 完成解析
        node_analyze_complete_message = {
            "spaceId": "123",
            "event": "node.analyze.complete",
            "data": {
                "progress": 100,
                "time": int(time.time()),
                "status": "complete",
                "remark":"完成解析",
                "cost":{
                    "points": 30,
                    "tokens": 14523
                }
            }
        }

        mq_producer.send_message(
            TOPIC, 
            node_analyze_complete_message, 
            tags='node.analyze'
        )
            
        time.sleep(2)

        # 示例3: 我已完成所有的工作，可以回收我了
        pod_recycle_message = {
            "spaceId": "123",
            "event": "pod.recycle",
            "data": {
                "podId":"pod-2",
                "time": int(time.time()),
                "status": "complete",
                "remark":"我已完成对/alibaba/fastjson的分析工作，可以回收我了"
            }
        }

        mq_producer.send_message(
            TOPIC, 
            pod_recycle_message, 
            tags='node.analyze'
        )

    except KeyboardInterrupt:
        logger.info("用户中断程序")
    finally:
        # 关闭生产者
        mq_producer.shutdown()

if __name__ == '__main__':
    main()