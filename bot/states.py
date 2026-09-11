from aiogram.fsm.state import State, StatesGroup


class PromptStates(StatesGroup):
    waiting_for_target = State()
    waiting_for_request = State()
    waiting_for_mode = State()
    clarifying = State()
    waiting_for_reference = State()
    completed = State()
