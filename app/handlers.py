from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards import my_comands_text, my_comands, post_categories, cancel
from aiogram.fsm.context import FSMContext 
from states import WritePost

from sqlalchemy.future import select
from database.db import async_session_maker
from database.models import Post, User

from datetime import datetime, timedelta

router = Router()

@router.message(F.text == '/start')
async def hello(message: Message, state: FSMContext):
    async with async_session_maker() as session:
        existing_user = await session.execute(select(User).filter_by(tg_id=message.from_user.id))
        existing_user = existing_user.scalar_one_or_none()

        if not existing_user:
            new_user = User(
                tg_id=message.from_user.id,
                username=message.from_user.first_name,
                nickname=message.from_user.username
            )
            session.add(new_user)
            await session.commit()
    
    current_state = await state.get_state()
    if current_state == WritePost.waiting_for_text.state:
        data = await state.get_data()
        post_type = data.get("post_type", "public")
        post_type_text = "публичный" if post_type == "public" else "приватный"
        await message.answer(
            f"Вы начали писать {post_type_text} пост. Напишите его, чтобы я мог сохранить или нажмите отмена", 
            reply_markup=cancel
        )
    else:
        await message.answer('Привет, я бот для заметок', reply_markup=my_comands_text)
    
@router.callback_query(F.data == 'my_comands_text')
async def show_comands(callback: CallbackQuery):
    await callback.message.edit_text("Вот мои команды:", reply_markup=my_comands)

@router.callback_query(F.data == 'add_post')
async def show_add_post(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию поста", reply_markup=post_categories)

# Обработчик для публичного поста
@router.callback_query(F.data == 'public_post')
async def show_add_post(callback: CallbackQuery, state: FSMContext):
    await state.update_data(post_type="public")  # Запоминаем тип поста
    await callback.message.edit_text("Напишите публичный пост", reply_markup=cancel)
    await state.set_state(WritePost.waiting_for_text)

# Обработчик для приватного поста
@router.callback_query(F.data == 'private_post')
async def show_add_private_post(callback: CallbackQuery, state: FSMContext):
    await state.update_data(post_type="private")  # Запоминаем тип поста
    await callback.message.edit_text("Напишите приватный пост:", reply_markup=cancel)
    await state.set_state(WritePost.waiting_for_text)

# Универсальный обработчик для сохранения постов
@router.message(WritePost.waiting_for_text)
async def receive_post_text(message: Message, state: FSMContext):
    data = await state.get_data()
    post_type = data.get("post_type", "public")  # Получаем тип поста
    post_text = message.text  
    user_id = message.from_user.id  

    async with async_session_maker() as session:
        async with session.begin():
            session.add(Post(
                user_id=user_id, 
                post_type=post_type, 
                text=post_text, 
                created_at=datetime.utcnow() + timedelta(hours=3) # Московское время
            ))

    await message.answer(f"Ваш {post_type} пост сохранён!")  
    await state.clear()  

# Обработчик для кнопки "Назад"
@router.callback_query(F.data == 'back_to_menu')
async def back_to_menu(callback: CallbackQuery):
    await show_comands(callback)
    
@router.callback_query(F.data == 'cancel')
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()  # Очистка всех состояний
    await callback.message.edit_text("Вы вернулись в главное меню.", reply_markup=my_comands_text)    