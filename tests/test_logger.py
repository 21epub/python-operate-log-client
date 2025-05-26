"""
OperateLogger 单元测试模块。

覆盖初始化、单条日志、批量日志和异常处理。
"""

import unittest
from unittest.mock import MagicMock, patch

from operate_log_client.logger import OperateLogger


class TestOperateLogger(unittest.TestCase):
    """OperateLogger 测试类。"""

    def setUp(self):
        """测试前准备。"""
        self.kafka_servers = ["localhost:9092"]
        self.topic = "test_topic"
        self.application = "test_app"
        self.environment = "test_env"
        self.kafka_config = {}

    @patch("operate_log_client.logger.KafkaProducer")
    def test_init(self, mock_producer):
        """测试初始化。"""
        logger = OperateLogger(
            kafka_servers=self.kafka_servers,
            topic=self.topic,
            application=self.application,
            environment=self.environment,
            kafka_config=self.kafka_config,
        )
        self.assertIsNotNone(logger.producer)
        self.assertEqual(logger.topic, self.topic)

    @patch("operate_log_client.logger.KafkaProducer")
    def test_log_operation(self, mock_producer):
        """测试单条日志记录。"""
        mock_instance = MagicMock()
        mock_producer.return_value = mock_instance
        mock_instance.send.return_value.get.return_value = True
        logger = OperateLogger(kafka_servers=self.kafka_servers, topic=self.topic)
        op_id = logger.log_operation(
            operation_type="TEST_OP",
            operator="tester",
            target="target1",
            details={"foo": "bar"},
            status="SUCCESS",
            request_id="req-1",
            user_id="tenant-1",
            subuser_id="user-1",
        )
        self.assertIsInstance(op_id, str)
        mock_instance.send.assert_called_once()

    @patch("operate_log_client.logger.KafkaProducer")
    def test_log_batch(self, mock_producer):
        """测试批量日志记录。"""
        mock_instance = MagicMock()
        mock_producer.return_value = mock_instance
        mock_instance.send.return_value.get.return_value = True
        logger = OperateLogger(kafka_servers=self.kafka_servers, topic=self.topic)
        operations = [
            {
                "operation_type": "BATCH_OP",
                "operator": "tester",
                "target": f"target{i}",
                "details": {"idx": i},
                "status": "SUCCESS",
            }
            for i in range(3)
        ]
        op_ids = logger.log_batch(operations)
        self.assertEqual(len(op_ids), 3)
        self.assertTrue(all(isinstance(i, str) for i in op_ids))

    @patch("operate_log_client.logger.KafkaProducer")
    def test_log_operation_kafka_error(self, mock_producer):
        """测试Kafka错误处理。"""
        from kafka.errors import KafkaError

        mock_instance = MagicMock()
        mock_producer.return_value = mock_instance
        mock_instance.send.return_value.get.side_effect = KafkaError("fail")
        logger = OperateLogger(kafka_servers=self.kafka_servers, topic=self.topic)
        with self.assertRaises(KafkaError):
            logger.log_operation(operation_type="ERR_OP", operator="tester", target="target1")


if __name__ == "__main__":
    unittest.main()
