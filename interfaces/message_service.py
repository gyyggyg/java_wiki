import asyncio
import time
import os
import json
import datetime
from typing import Dict, List, Any, Optional, Union
from interfaces.kafka_interface import KafkaInterface

class MessageService:
    """消息服务主类 处理消息队列"""
    def __init__(self,
                 kafka_config: Dict[str, Any] = None):
        """初始化kafka"""
        # 配置openai client
        self.kafka = KafkaInterface(**kafka_config)
    
    def send_message(self, topic, message_body, tags=None, keys=None):
        return self.kafka.send_message(topic, message_body, tags, keys)
    
    def close(self):
        self.kafka.shutdown()