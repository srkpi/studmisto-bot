from aiogram.fsm.state import State, StatesGroup


class RequestForm(StatesGroup):
    name = State()
    phone = State()
    dorm = State()
    problem_type = State()
    details = State()
