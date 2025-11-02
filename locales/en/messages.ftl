# locales/en/messages.ftl (WITH UNDERSCORES!)

# --- General ---
welcome = 👋 Hi, { $user_name }!
    I'm a bot for tracking coffee shop work hours.
help_text = <b>Bot Commands:</b>

    <b>For everyone:</b>
    /start - Restart the bot and show the menu
    <b>{ $btn_record }</b> - Record the start or end of your shift.
    <b>{ $btn_stats }</b> - Show your statistics for the week/month.
    <b>{ $btn_help }</b> - Show this message.

    <b>For administrators:</b>
    <b>{ $btn_admin }</b> - Open the management menu:
      - <b>Reports</b> - Get a summary report for all employees.
      - <b>Adjustment</b> - Add/subtract hours for an employee.
      - <b>Delete Employee</b> - Permanently delete a user and their data.

generic_db_error = An error occurred while working with the database: { $error }
menu_updated = Menu updated. # Can keep or remove if not used

# --- Main Menu Buttons ---
button_record_shift = 📝 Record Shift
button_my_stats = My Statistics
button_help = Help
button_admin_panel = 👑 Admin Panel
input_placeholder = Choose an action

# --- Role Setup (UserSetup) ---
setup_welcome = <b>Welcome!</b>
    Please select your job role(s) to start tracking time. Press "Done" when finished.
button_done = Done
setup_error_no_roles = 🚫 Please select at least one role.
setup_success = ✅ Great! Your roles have been saved. You can now record shifts.

# --- Shift Recording (RecordShift) ---
error_no_roles_assigned = 🚫 You have no roles assigned. Please type /start to set them up.
shift_select_role = Select the role for this shift:
# ❗️❗️❗️ THESE KEYS WERE MISSING/WRONG ❗️❗️❗️
shift_request_start_time_role = Role: <b>{ $role_name }</b>.
    Select the <b>start</b> time of your shift:
shift_request_end_time = Shift started at <b>{ $start_hour }:00</b>.
    Select the <b>end</b> time of your shift:
error_role_or_time_not_found = 🚫 Error: Role or start time data not found. Please try again.
shift_error_end_lt_start = 🚫 <b>Error!</b> The end time ({ $end_hour }:00) cannot be earlier than or equal to the start time ({ $start_hour }:00).
shift_error_start_overlap = 🚫 <b>Error!</b> The selected start time (<b>{ $start_hour }:00</b>) falls within or starts before the end of an already recorded shift ({ $old_start }:00 - { $old_end }:00). Please choose a later time.
shift_start_recorded = ✅ Shift start at <b>{ $start_hour }:00</b> recorded. Don't forget to press "Record Shift" again later to set the end time.
shift_start_forgotten = ⚠️ It seems you forgot to record the end of your shift from { $start_date }. That record has been deleted. Please start a new shift for today.
shift_success_recorded = ✅ <b>Shift successfully recorded!</b>
    <b>Date:</b> { $date }
    <b>Role:</b> { $role_name }
    <b>Time:</b> { $start_time }:00 - { $end_time }:00
    <b>Total hours:</b> { $hours }
# ❗️❗️❗️ END OF MISSING KEYS ❗️❗️❗️
shift_error_overlap = 🚫 <b>Error!</b>
    Your new shift (<b>{ $new_start }:00 - { $new_end }:00</b>)
    overlaps with an existing one (<b>{ $old_start }:00 - { $old_end }:00</b>).
    Please choose a different time.
shift_error_alert = Error!


# --- Statistics (User) ---
stats_select_period = For which period do you want to see your statistics?
stats_button_week = This Week
stats_button_month = This Month
stats_report_header = <b>Report from { $start_date } to { $end_date }</b>
stats_report_no_data = No shift records for this period.
stats_role_header = <b>{ $role_name }</b> ({ $hours } h. x { $rate } RSD/h = { $earnings } RSD)
stats_report_footer_total = <b>TOTAL: { $total_hours } h. ({ $total_earnings } RSD)</b>
shift_entry_auto = • { $date }: { $start }:00 - { $end }:00 ({ $hours } h.)
shift_entry_manual = • { $date }: [Manual] ({ $hours } h.)
shift_entry_adjustment = • { $date }: [Adj.] ({ $hours } h.)

# --- Admin Panel ---
admin_panel_welcome = Welcome to the Admin Panel.
admin_button_report_day = Report for Today
admin_button_report_week = Weekly Report
admin_button_report_month = Monthly Report
admin_button_report_prev_month = Report for PREVIOUS month
admin_button_manual_add = Adjust Hours
admin_button_delete_user = ☠️ Delete Employee
admin_no_users_in_db = There are no users in the database yet.
menu_updated_admin = Menu updated. # Can keep or remove

# --- Summary Report (Admin) ---
admin_summary_report_header = <b>Summary Report from { $start_date } to { $end_date }</b>
admin_summary_report_header_day = <b>Summary Report for { $date }</b>
admin_summary_report_no_data = No shift data for this period.
admin_summary_user_line = { $num }. <b>{ $user_name }</b>: { $total_hours } h. (Total: { $total_earnings } RSD)
admin_summary_role_line = • <i>{ $role_name }</i>: { $hours } h. ({ $earnings } RSD)
admin_summary_report_footer_grand_total = <b>GRAND TOTAL (ALL STAFF): { $grand_total_hours } h. ({ $grand_total_earnings } RSD)</b>
admin_summary_report_header_prev_month = <b>Summary Report for { $month_name }</b>
admin_summary_prev_month_line = { $num }. <b>{ $user_name }</b> ({ $roles_str }): <b>{ $total_hours } h.</b> ({ $total_earnings } RSD)
admin_summary_prev_month_footer = <b>Grand Total Salary: { $total_salary } RSD</b>

# --- Adjustment (Admin) ---
admin_select_user_adjust = Select an employee to *adjust* hours for:
error_user_has_no_roles_admin = 🚫 This user has no roles configured. Adjustment is not possible.
adjust_select_role = Selected: <b>{ $user_name }</b>.
    Select the role for the hours adjustment:
adjust_user_selected_single_role = Selected: <b>{ $user_name }</b> (Role: <b>{ $role_name }</b>).
    Enter the number of hours to add/subtract (e.g., 8.5 or -10):
adjust_user_selected_multi_role = Selected: <b>{ $user_name }</b> (Role: <b>{ $role_name }</b>).
    Enter the number of hours to add/subtract (e.g., 8.5 or -10):
error_role_not_found_in_state_admin = 🚫 Error: Could not determine the role for the adjustment. Please try again.
adjust_error_format = 🚫 Invalid format. Enter a non-zero number (e.g., <b>8.5</b> or <b>-10</b>).
adjust_error_negative_limit = 🚫 <b>Error!</b>
    Subtracting <b>{ $hours_to_add } h.</b> is not possible.

    Current total: { $current_hours } h.
    <b>The new total would be: { $new_total } h.</b> (cannot be < 0)
adjust_error_positive_limit = 🚫 <b>Validation Error (Month Limit)!</b>
    Adding <b>{ $hours_to_add } h.</b> will exceed the limit.

    Current total for { $month }: { $current_hours } h.
    <b>New total: { $new_total } h.</b>
    <b>Maximum (up to { $today }): { $max_hours } h.</b>
adjust_success_with_role = ✅ <b>Adjustment successfully added!</b>

    <b>Employee:</b> { $user_name }
    <b>Role:</b> { $role_name }
    <b>Record Date:</b> { $date }
    <b>Change:</b> { $hours_str } h.

# --- Deletion (Admin) ---
admin_select_user_delete = Select an employee to <b>permanently</b> delete from the database:
admin_delete_confirm = ⚠️ <b>ATTENTION!</b> ⚠️
    Are you sure you want to delete <b>{ $user_name }</b>?

    This action is <b>IRREVERSIBLE</b> and will delete <b>ALL</b> shifts for this employee.
admin_delete_confirm_yes = Yes, delete
admin_delete_confirm_no = No, cancel
admin_delete_success = ✅ Employee <b>{ $user_name }</b> has been deleted.
admin_delete_cancelled = Deletion cancelled.
admin_delete_self = 🚫 You cannot delete yourself.

# --- Group Chats ---
group_welcome = 👋 Hi, { $user_name }!
    For confidential time tracking,
    please start a private chat with me.
button_start_private = Start private tracking
group_please_go_to_private = Please use commands
    only in a private chat with me (click my name and "Send Message").

# --- Reminder ---
reminder_end_shift = ⏰ Reminder! It looks like you haven't recorded the end of your shift (started today). Please press "📝 Record Shift" and select the end time if you have finished working.
# ... (after adjust_error_positive_limit)
adjust_error_negative_role_limit = 🚫 <b>Error!</b>
    Cannot subtract <b>{ $hours_to_add } h.</b> for the role "<b>{ $role_name }</b>".
    Current total for this role: { $current_hours } h.
    <b>The new total would be: { $new_total } h.</b> (cannot be < 0)