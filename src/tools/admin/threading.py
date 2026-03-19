import threading

from src.tools.admin.app import AdminEditorApp


def start_admin_gui_thread(
    spell_service,
    item_service,
    character_service,
    achievement_service,
    player_service,
    race_service,
    unit_service,
    allegiance_service,
    mission_service,
    campaign_service,
    environment_service,
    memory_service,
    power_rating_service,
    combat_simulator_service,
):
    def _run_gui():
        try:
            app = AdminEditorApp(
                spell_service,
                item_service,
                character_service,
                achievement_service,
                player_service,
                race_service,
                unit_service,
                allegiance_service,
                mission_service,
                campaign_service,
                environment_service,
                memory_service,
                power_rating_service,
                combat_simulator_service,
            )
            app.run()
        except Exception as exc:
            print(f"Admin GUI failed to start: {exc}")

    thread = threading.Thread(target=_run_gui, name="AdminEditorGUI", daemon=True)
    thread.start()
    return thread
