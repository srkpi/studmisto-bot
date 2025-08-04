from enum import Enum


class OrderStatus(Enum):
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    CLARIFICATION = "CLARIFICATION"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


ORDER_STATUS_NAMES: dict[OrderStatus, str] = {
    OrderStatus.WAITING: "⏳ Очікує",
    OrderStatus.IN_PROGRESS: "🧑‍💻 У роботі",
    OrderStatus.CLARIFICATION: "📝 Уточнення",
    OrderStatus.REJECTED: "❌ Відмовлено",
    OrderStatus.COMPLETED: "✅ Виконано",
    OrderStatus.CANCELLED: "🚫 Скасовано",
}

ORDER_STATUS_SPREADSHEET_NAMES: dict[OrderStatus, str] = {
    OrderStatus.WAITING: "Очікує",
    OrderStatus.IN_PROGRESS: "У роботі",
    OrderStatus.CLARIFICATION: "Уточнення",
    OrderStatus.REJECTED: "Відмовлено",
    OrderStatus.COMPLETED: "Виконано",
    OrderStatus.CANCELLED: "Скасовано",
}
