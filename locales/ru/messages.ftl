# locales/ru/messages.ftl (С ПОДЧЕРКИВАНИЯМИ!)

# --- Общие ---
welcome = 👋 Привет, { $user_name }!
    Я бот для учета рабочего времени кофейни.
help_text = <b>Справка по командам:</b>

    <b>Для всех:</b>
    /start - Перезапуск бота и показ меню
    <b>{ $btn_record }</b> - Записать начало или конец смены.
    <b>{ $btn_stats }</b> - Показать вашу статистику за неделю/месяц.
    <b>{ $btn_help }</b> - Показать это сообщение.

    <b>Для администраторов:</b>
    <b>{ $btn_admin }</b> - Открыть меню управления:
      - <b>Отчеты</b> - Получить общий отчет по всем сотрудникам.
      - <b>Корректировка</b> - Внести/вычесть часы сотруднику.
      - <b>Удалить сотрудника</b> - Полностью удалить пользователя и его данные.

generic_db_error = Произошла ошибка при работе с базой данных: { $error }
menu_updated = Меню обновлено. # Можно оставить или удалить, если не используется

# --- Кнопки главного меню ---
button_record_shift = 📝 Записать смену
button_my_stats = Моя статистика
button_help = Справка
button_admin_panel = 👑 Админ-панель
input_placeholder = Выберите действие

# --- Настройка ролей (UserSetup) ---
setup_welcome = <b>Добро пожаловать!</b>
    Пожалуйста, выберите вашу должность (или несколько), чтобы начать учет рабочего времени. Нажмите "Готово", когда закончите.
button_done = Готово
setup_error_no_roles = 🚫 Пожалуйста, выберите хотя бы одну должность.
setup_success = ✅ Отлично! Ваши должности сохранены. Теперь вы можете записывать смены.

# --- Запись смены (RecordShift) ---
error_no_roles_assigned = 🚫 У вас не выбраны должности. Пожалуйста, введите /start, чтобы их настроить.
shift_select_role = Выберите должность для этой смены:
# ❗️❗️❗️ ВОТ ЭТИ КЛЮЧИ БЫЛИ ПРОПУЩЕНЫ/НЕПРАВИЛЬНЫЕ ❗️❗️❗️
shift_request_start_time_role = Должность: <b>{ $role_name }</b>.
    Выберите время <b>начала</b> смены:
shift_request_end_time = Начало смены было в <b>{ $start_hour }:00</b>.
    Выберите время <b>окончания</b> смены:
error_role_or_time_not_found = 🚫 Ошибка: Не найдены данные о роли или времени начала. Попробуйте снова.
shift_error_end_lt_start = 🚫 <b>Ошибка!</b> Время окончания ({ $end_hour }:00) не может быть раньше или равно времени начала ({ $start_hour }:00).
shift_error_start_overlap = 🚫 <b>Ошибка!</b> Выбранное время начала (<b>{ $start_hour }:00</b>) попадает внутрь или начинается до окончания уже записанной смены ({ $old_start }:00 - { $old_end }:00). Пожалуйста, выберите время позже.
shift_start_recorded = ✅ Начало смены в <b>{ $start_hour }:00</b> записано. Не забудьте потом нажать "Записать смену" еще раз, чтобы указать время окончания.
shift_start_forgotten = ⚠️ Похоже, вы забыли записать окончание смены за прошлый день ({ $start_date }). Та запись удалена. Пожалуйста, начните новую смену за сегодня.
shift_success_recorded = ✅ <b>Смена успешно записана!</b>
    <b>Дата:</b> { $date }
    <b>Должность:</b> { $role_name }
    <b>Время:</b> { $start_time }:00 - { $end_time }:00
    <b>Всего часов:</b> { $hours }
# ❗️❗️❗️ КОНЕЦ ПРОПУЩЕННЫХ КЛЮЧЕЙ ❗️❗️❗️
shift_error_overlap = 🚫 <b>Ошибка!</b>
    Ваша новая смена (<b>{ $new_start }:00 - { $new_end }:00</b>)
    пересекается с существующей (<b>{ $old_start }:00 - { $old_end }:00</b>).
    Пожалуйста, выберите другое время.
shift_error_alert = Ошибка!


# --- Статистика (User) ---
stats_select_period = За какой период вы хотите посмотреть свою статистику?
stats_button_week = Эта неделя
stats_button_month = Этот месяц
stats_report_header = <b>Отчет с { $start_date } по { $end_date }</b>
stats_report_no_data = За этот период нет записей о сменах.
stats_role_header = <b>{ $role_name }</b> ({ $hours } ч. x { $rate } RSD/ч = { $earnings } RSD)
stats_report_footer_total = <b>ИТОГО: { $total_hours } ч. ({ $total_earnings } RSD)</b>
shift_entry_auto = • { $date }: { $start }:00 - { $end }:00 ({ $hours } ч.)
shift_entry_manual = • { $date }: [Вручную] ({ $hours } ч.)
shift_entry_adjustment = • { $date }: [Корр.] ({ $hours } ч.)

# --- Админ-панель ---
admin_panel_welcome = Добро пожаловать в Админ-панель.
admin_button_report_day = Отчет за сегодня
admin_button_report_week = Отчет за неделю
admin_button_report_month = Отчет за месяц
admin_button_manual_add = Корректировка часов
admin_button_delete_user = ☠️ Удалить сотрудника
admin_no_users_in_db = В базе данных пока нет пользователей.
menu_updated_admin = Меню обновлено. # Можно оставить или удалить

# --- Сводный отчет (Admin) ---
admin_summary_report_header = <b>Общий отчет с { $start_date } по { $end_date }</b>
admin_summary_report_header_day = <b>Общий отчет за { $date }</b>
admin_summary_report_no_data = Нет данных о сменах за этот период.
admin_summary_user_line = { $num }. <b>{ $user_name }</b>: { $total_hours } ч. (Итого: { $total_earnings } RSD)
admin_summary_role_line = • <i>{ $role_name }</i>: { $hours } ч. ({ $earnings } RSD)
admin_summary_report_footer_grand_total = <b>ИТОГО ПО КОФЕЙНЕ: { $grand_total_hours } ч. ({ $grand_total_earnings } RSD)</b>

# --- Корректировка (Admin) ---
admin_select_user_adjust = Выберите сотрудника, которому нужно внести *корректировку* часов:
error_user_has_no_roles_admin = 🚫 У этого пользователя не настроены должности. Корректировка невозможна.
adjust_select_role = Выбран: <b>{ $user_name }</b>.
    Выберите должность для корректировки часов:
adjust_user_selected_single_role = Выбран: <b>{ $user_name }</b> (Должность: <b>{ $role_name }</b>).
    Введите кол-во часов для добавления/вычитания (напр. 8.5 или -10):
adjust_user_selected_multi_role = Выбран: <b>{ $user_name }</b> (Должность: <b>{ $role_name }</b>).
    Введите кол-во часов для добавления/вычитания (напр. 8.5 или -10):
error_role_not_found_in_state_admin = 🚫 Ошибка: Не удалось определить роль для корректировки. Попробуйте заново.
adjust_error_format = 🚫 Неверный формат. Введите число, не равное нулю (например, <b>8.5</b> или <b>-10</b>).
adjust_error_negative_limit = 🚫 <b>Ошибка!</b>
    Вычитание <b>{ $hours_to_add } ч.</b> невозможно.

    Текущий итог: { $current_hours } ч.
    <b>Новый итог был бы: { $new_total } ч.</b> (не может быть < 0)
adjust_error_positive_limit = 🚫 <b>Ошибка валидации (лимит месяца)!</b>
    Добавление <b>{ $hours_to_add } ч.</b> приведет к превышению лимита.

    Текущий итог за { $month }: { $current_hours } ч.
    <b>Новый итог: { $new_total } ч.</b>
    <b>Максимум (до { $today }): { $max_hours } ч.</b>
adjust_success_with_role = ✅ <b>Корректировка успешно добавлена!</b>

    <b>Сотрудник:</b> { $user_name }
    <b>Должность:</b> { $role_name }
    <b>Дата записи:</b> { $date }
    <b>Изменение:</b> { $hours_str } ч.

# --- Удаление (Admin) ---
admin_select_user_delete = Выберите сотрудника для <b>полного</b> удаления из базы:
admin_delete_confirm = ⚠️ <b>ВНИМАНИЕ!</b> ⚠️
    Вы уверены, что хотите удалить <b>{ $user_name }</b>?

    Это действие <b>НЕОБРАТИМО</b> и удалит <b>ВСЕ</b> смены этого сотрудника.
admin_delete_confirm_yes = Да, удалить
admin_delete_confirm_no = Нет, отмена
admin_delete_success = ✅ Сотрудник <b>{ $user_name }</b> был удален.
admin_delete_cancelled = Удаление отменено.
admin_delete_self = 🚫 Вы не можете удалить сами себя.

# --- Групповые чаты ---
group_welcome = 👋 Привет, { $user_name }!
    Для конфиденциального учета часов, пожалуйста,
    начните диалог со мной в личном чате.
button_start_private = Начать конфиденциальный учет
group_please_go_to_private = Пожалуйста, используйте команды
    только в личном чате со мной (нажмите на мое имя и "Отправить сообщение").

# --- Напоминание ---
reminder_end_shift = ⏰ Напоминание! Похоже, вы еще не завершили свою смену (начатую сегодня). Нажмите "📝 Записать смену" и выберите время окончания, если вы уже закончили работать.
adjust_error_negative_role_limit = 🚫 <b>Ошибка!</b>
    Нельзя вычесть <b>{ $hours_to_add } ч.</b> для должности "<b>{ $role_name }</b>".
    Текущий итог по этой должности: { $current_hours } ч.
    <b>Новый итог был бы: { $new_total } ч.</b> (не может быть < 0)