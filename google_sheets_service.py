from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Any

from config import GOOGLE_SERVICE_ACCOUNT_FILENAME, SPREADSHEET_ID
from constants.order_statuses import ORDER_STATUS_SPREADSHEET_NAMES, OrderStatus
from constants.order_types import ORDER_TYPE_NAMES, OrderType

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

REQUEST_ID_COLUMN = 1
STATUS_COLUMN = 6
EDIT_TIMESTAMP_COLUMN = 9

WORKSHEET_TITLE_ROW = [
    "ID",
    "ПІБ",
    "Телефон",
    "Гуртожиток",
    "Опис проблеми",
    "Статус",
    "Повідомлення в телеграм",
    "Час створення заяви",
    "Час оновлення статусу",
    "Примітки",
]


creds = Credentials.from_service_account_file(
    GOOGLE_SERVICE_ACCOUNT_FILENAME, scopes=SCOPES
)

gc = gspread.authorize(creds)
sh = gc.open_by_key(SPREADSHEET_ID)


def add_order_to_sheet(order_id: str, telegram_url: str, order: Dict[str, Any]) -> None:
    """
    Adds a new order to the appropriate Google Sheet tab based on problem type. Returns the row number.
    """
    problem_type = OrderType(order["problem_type"])
    order_status = OrderStatus(order["status"])

    sheet_name = ORDER_TYPE_NAMES.get(problem_type)
    order_status_str = ORDER_STATUS_SPREADSHEET_NAMES[order_status]

    is_sheet_created = False

    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=1, cols=10)
        worksheet.append_row(WORKSHEET_TITLE_ROW)
        is_sheet_created = True

    row = [
        order_id,
        order["name"],
        order["phone"],
        order["dorm"],
        order.get("details", ""),
        order_status_str,
        telegram_url,
        order["timestamp"].strftime("%d.%m.%Y %H:%M"),
        order["edit_timestamp"].strftime("%d.%m.%Y %H:%M"),
    ]

    worksheet.append_row(row)

    if is_sheet_created:
        worksheet.freeze(1)


def update_order_status_in_sheet(
    request_id: str,
    new_status: OrderStatus,
    problem_type: OrderType,
    edit_timestamp: datetime,
):
    """
    Updates the status of an order in the appropriate Google Sheet tab by request_id.
    """
    status_name = ORDER_STATUS_SPREADSHEET_NAMES[new_status]
    sheet_name = ORDER_TYPE_NAMES[problem_type]

    worksheet = sh.worksheet(sheet_name)

    cell = worksheet.find(request_id, in_column=REQUEST_ID_COLUMN)
    if cell:
        worksheet.update_cells(
            [
                gspread.Cell(cell.row, STATUS_COLUMN, status_name),
                gspread.Cell(
                    cell.row,
                    EDIT_TIMESTAMP_COLUMN,
                    edit_timestamp.strftime("%d.%m.%Y %H:%M"),
                ),
            ]
        )
    else:
        raise Exception("Column with request id not found in sheet: " + sheet_name)
