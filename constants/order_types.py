from os import getenv
from enum import Enum


class OrderType(Enum):
    ELECTRICAL = "ELECTRICAL"
    PLUMBING = "PLUMBING"
    GAS = "GAS"
    ELEVATOR = "ELEVATOR"
    CARPENTRY = "CARPENTRY"
    OTHER = "OTHER"


ORDER_TYPE_NAMES: dict[OrderType, str] = {
    OrderType.ELECTRICAL: "Електрика",
    OrderType.PLUMBING: "Сантехніка",
    OrderType.GAS: "Газ",
    OrderType.ELEVATOR: "Ліфт",
    OrderType.CARPENTRY: "Столярство",
    OrderType.OTHER: "Інше",
}


ORDER_TYPE_CHAT_THREADS: dict[OrderType, int] = {
    order_type: int(getenv(f"CHAT_THREAD_{order_type.name}", "0"))
    for order_type in OrderType
}
