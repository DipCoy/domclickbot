import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DOWN_PAYMENT_MIN_PERCENT = 15


bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class MortgageStep(StatesGroup):
    start = State()
    loan = State()
    down_payment = State()


def is_not_number(message: types.Message) -> bool:
    return not message.text.isdigit()


async def start_or_run_again(message: types.Message):
    await MortgageStep.loan.set()
    await message.reply(
        "Привет! Совсем скоро у тебя будет свой дом, без мам, пап и кредитов. Но с ипотекой... Укажи сумму, "
        "которая тебе нужна"
    )


async def get_loan_from_state(state: FSMContext) -> int:
    async with state.proxy() as data:
        return data['loan']


async def set_loan_to_state(state: FSMContext, loan: int):
    async with state.proxy() as data:
        data['loan'] = loan


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await start_or_run_again(message)


@dp.message_handler(state=MortgageStep.start)
async def again_state(message: types.Message):
    await start_or_run_again(message)


@dp.message_handler(is_not_number, state=MortgageStep.loan)
async def process_loan_invalid(message: types.Message):
    return await message.reply("Сумма кредита должна быть числом.\nПопробуй снова.")


@dp.message_handler(state=MortgageStep.loan)
async def process_loan(message: types.Message, state: FSMContext):
    await set_loan_to_state(state, int(message.text))
    await MortgageStep.down_payment.set()
    await message.reply("Укажи первоначальный взнос.")


@dp.message_handler(is_not_number, state=MortgageStep.down_payment)
async def process_down_payment_invalid(message: types.Message):
    return await message.reply("Первоначальный взнос должен быть числом.\nУкажи первоначальный взнос.")


@dp.message_handler(state=MortgageStep.down_payment)
async def process_down_payment(message: types.Message, state: FSMContext):
    down_payment = int(message.text)
    await state.update_data(down_payment=down_payment)

    loan = await get_loan_from_state(state)

    if down_payment < 0.01 * DOWN_PAYMENT_MIN_PERCENT * loan:
        await message.reply(
            "Сумма первоначального взноса должна быть не меньше 15% от суммы кредита. Попробуй ещё раз."
        )
        return

    await message.reply("Всё отлично! Заявку можно подать на сайте https://domclick.ru/ipoteka/programs/onlajn-zayavka")
    await MortgageStep.start.set()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
