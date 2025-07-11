from datetime import datetime
from pymongo.collection import Collection

from constants.order_statuses import OrderStatus
from constants.order_types import OrderType


async def get_queue_position(
    collection: Collection, problem_type: OrderType, timestamp: datetime
) -> int:
    return (
        await collection.count_documents(
            {
                "problem_type": problem_type.value,
                "status": {
                    "$in": [OrderStatus.WAITING.value, OrderStatus.IN_PROGRESS.value]
                },
                "timestamp": {"$lt": timestamp},
            }
        )
        + 1
    )
