"""
Vector Queue Processor Tests (TDD)
"""
import pytest
import sys
sys.path.insert(0, 'D:\\tools\\消费看板5（前端）\\backend')

from vector.vector_queue import VectorQueueProcessor


def test_vector_queue_processor_init():
    """Test VectorQueueProcessor initialization with default parameters"""
    processor = VectorQueueProcessor()
    assert processor.batch_size == 10
    assert processor.max_retries == 3


def test_vector_queue_processor_custom_params():
    """Test VectorQueueProcessor with custom batch size"""
    processor = VectorQueueProcessor()
    processor.batch_size = 20
    assert processor.batch_size == 20


def test_vector_queue_processor_max_retries():
    """Test VectorQueueProcessor max retries value"""
    processor = VectorQueueProcessor()
    assert processor.max_retries == 3