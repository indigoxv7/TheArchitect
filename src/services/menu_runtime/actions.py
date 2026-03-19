from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.combat import EncounterType
from src.services.menu_runtime.fields import (
    COMPONENT_FIELD_EDIT_CONFIG,
    ITEM_ENUM_ACTIONS,
    ITEM_FIELD_EDIT_CONFIG,
    SPELL_FIELD_EDIT_CONFIG,
)
from src.ui.menu import Menu

if TYPE_CHECKING:
    from src.services.menu_runtime import MenuInterface, MenuRuntimeService, OriginalMessage


SpecialActionResult = tuple[Menu, bool, bool]


class MenuSpecialActionRouter:
    def __init__(self, runtime: "MenuRuntimeService"):
        self.runtime = runtime
        self._handlers = {
            "scavengingMissionAction": self._start_scavenging_battle,
            "portalMissionAction": self._start_portal_battle,
            "spellCreateAction": self._start_spell_create,
            "spellCreateSaveAction": self._save_spell_create,
            "spellCreateCancelAction": self._cancel_spell_create,
            "spellEditAction": self._open_spell_edit_modal,
            "itemCreateAction": self._start_item_create,
            "itemCreateSaveAction": self._save_item_create,
            "itemCreateCancelAction": self._cancel_item_create,
            "itemEditAction": self._open_item_edit_modal,
            "attributesEditorMenu": self._open_attributes_editor,
            "gearEditorMenu": self._open_gear_editor,
            "bonusEditorMenu": self._open_bonus_editor,
            "achievementEditorMenu": self._open_achievement_editor,
            "attributesTempSaveAction": self._save_attributes_editor,
            "attributesTempCancelAction": self._cancel_attributes_editor,
            "gearTempSaveAction": self._save_gear_editor,
            "gearTempCancelAction": self._cancel_gear_editor,
            "bonusTempSaveAction": self._save_bonus_editor,
            "bonusTempCancelAction": self._cancel_bonus_editor,
            "achievementTempSaveAction": self._save_achievement_editor,
            "achievementTempCancelAction": self._cancel_achievement_editor,
        }

    async def handle(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult | None:
        handler = self._handlers.get(menu.uniqueName)
        if handler is not None:
            return await handler(interface, menu, original_message)

        if menu.uniqueName in ITEM_ENUM_ACTIONS:
            return await self._handle_item_enum_action(interface, menu, original_message)

        if (
            menu.uniqueName in SPELL_FIELD_EDIT_CONFIG
            or menu.uniqueName in ITEM_FIELD_EDIT_CONFIG
            or menu.uniqueName in COMPONENT_FIELD_EDIT_CONFIG
        ):
            return await self._handle_field_edit_action(interface, menu, original_message)

        return None

    @staticmethod
    def _parent_or_self(menu: Menu) -> Menu:
        return menu.parent if menu.parent is not None else menu

    def _menu_by_name(self, name: str, fallback: Menu) -> Menu:
        return self.runtime.context.menus_by_name.get(name, fallback)

    async def _start_battle(
        self,
        interface: "MenuInterface",
        menu: Menu,
        encounter_type: EncounterType,
    ) -> SpecialActionResult:
        interaction = interface.discord_interaction
        if self.runtime.battle_runtime_service is None or interaction is None:
            await interface.send_ephemeral("Combat runtime is only available in Discord right now.")
            return self._parent_or_self(menu), False, True

        await self.runtime.battle_runtime_service.start_or_resume_battle(
            interaction=interaction,
            player_id=interface.user_id,
            encounter_type=encounter_type,
        )
        return self._parent_or_self(menu), False, True

    async def _start_scavenging_battle(
        self, interface: "MenuInterface", menu: Menu, _original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        return await self._start_battle(interface, menu, EncounterType.SCAVENGING)

    async def _start_portal_battle(
        self, interface: "MenuInterface", menu: Menu, _original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        return await self._start_battle(interface, menu, EncounterType.PORTAL)

    async def _start_spell_create(
        self, _interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._start_spell_draft(original_message.menuContext)
        return self._menu_by_name("spellCreateNameMenu", menu), True, False

    async def _save_spell_create(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.is_developer_admin:
            await interface.send_ephemeral("You are not authorized to save spells.")
            return self._parent_or_self(menu), False, True

        payload = self.runtime._build_spell_payload_from_draft(original_message.menuContext.spellDraft)
        source_spell_name = original_message.menuContext.spellDraftSourceName
        try:
            if source_spell_name:
                self.runtime.spell_service.edit_spell_from_patch(source_spell_name, payload)
                await interface.send_ephemeral("Spell updated.")
            else:
                self.runtime.spell_service.create_spell_from_dict(payload)
                await interface.send_ephemeral("Spell saved.")
        except Exception as exc:
            await interface.send_ephemeral(f"Failed to save spell: {exc}")
        self.runtime._clear_spell_draft(original_message.menuContext)
        self.runtime._refresh_spellbook_overview()
        return self._menu_by_name("spellbookMenu", menu), True, True

    async def _cancel_spell_create(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_spell_draft(original_message.menuContext)
        self.runtime._refresh_spellbook_overview()
        await interface.send_ephemeral("Spell creation cancelled.")
        return self._menu_by_name("spellbookMenu", menu), True, True

    async def _open_spell_edit_modal(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.is_developer_admin:
            await interface.send_ephemeral("You are not authorized to edit drafts.")
            return self._parent_or_self(menu), False, True
        if interface.supports_modals:
            await interface.send_modal(self.runtime.build_spell_select_modal(original_message))
        else:
            await interface.send_ephemeral("Spell edit modal is available in Discord UI only.")
        self.runtime._refresh_spellbook_overview()
        return self._parent_or_self(menu), False, True

    async def _start_item_create(
        self, _interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._start_item_draft(original_message.menuContext)
        return self._menu_by_name("itemCreateNameMenu", menu), True, False

    async def _save_item_create(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.is_developer_admin:
            await interface.send_ephemeral("You are not authorized to save items.")
            return self._parent_or_self(menu), False, True

        try:
            payload = self.runtime._build_item_payload_from_draft(original_message.menuContext.itemDraft)
            source_item_id = (
                original_message.menuContext.itemDraftSourceId
                if hasattr(original_message.menuContext, "itemDraftSourceId")
                else original_message.menuContext.itemDraftSourceName
            )
            if source_item_id:
                self.runtime.item_service.edit_item_from_patch(source_item_id, payload)
                await interface.send_ephemeral("Item updated.")
            else:
                self.runtime.item_service.create_item_from_dict(payload)
                await interface.send_ephemeral("Item saved.")
        except Exception as exc:
            await interface.send_ephemeral(f"Failed to save item: {exc}")
        self.runtime._clear_item_draft(original_message.menuContext)
        self.runtime._refresh_itembook_overview()
        return self._menu_by_name("itembookMenu", menu), True, True

    async def _cancel_item_create(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_item_draft(original_message.menuContext)
        self.runtime._refresh_itembook_overview()
        await interface.send_ephemeral("Item creation cancelled.")
        return self._menu_by_name("itembookMenu", menu), True, True

    async def _open_item_edit_modal(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.is_developer_admin:
            await interface.send_ephemeral("You are not authorized to edit items.")
            return self._parent_or_self(menu), False, True
        if interface.supports_modals:
            await interface.send_modal(self.runtime.build_item_select_modal(original_message))
        else:
            await interface.send_ephemeral("Item edit modal is available in Discord UI only.")
        self.runtime._refresh_itembook_overview()
        return self._parent_or_self(menu), False, True

    async def _open_attributes_editor(
        self, _interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.menuContext.attributesDraftActive:
            self.runtime._start_attributes_draft(original_message.menuContext)
        return menu, True, False

    async def _open_gear_editor(
        self, _interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.menuContext.gearDraftActive:
            self.runtime._start_gear_draft(original_message.menuContext)
        return menu, True, False

    async def _open_bonus_editor(
        self, _interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.menuContext.bonusDraftActive:
            self.runtime._start_bonus_draft(original_message.menuContext)
        return menu, True, False

    async def _open_achievement_editor(
        self, _interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.menuContext.achievementDraftActive:
            self.runtime._start_achievement_draft(original_message.menuContext)
        return menu, True, False

    async def _save_attributes_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_attributes_draft(original_message.menuContext)
        await interface.send_ephemeral("Attributes saved for this session only (not persisted).")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _cancel_attributes_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_attributes_draft(original_message.menuContext)
        await interface.send_ephemeral("Attributes editor cancelled.")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _save_gear_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_gear_draft(original_message.menuContext)
        await interface.send_ephemeral("Gear saved for this session only (not persisted).")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _cancel_gear_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_gear_draft(original_message.menuContext)
        await interface.send_ephemeral("Gear editor cancelled.")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _save_bonus_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_bonus_draft(original_message.menuContext)
        await interface.send_ephemeral("Bonus saved for this session only (not persisted).")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _cancel_bonus_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_bonus_draft(original_message.menuContext)
        await interface.send_ephemeral("Bonus editor cancelled.")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _save_achievement_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_achievement_draft(original_message.menuContext)
        await interface.send_ephemeral("Achievement saved for this session only (not persisted).")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _cancel_achievement_editor(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        self.runtime._clear_achievement_draft(original_message.menuContext)
        await interface.send_ephemeral("Achievement editor cancelled.")
        return self._menu_by_name("mainMenu", menu), True, True

    async def _handle_item_enum_action(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.is_developer_admin:
            await interface.send_ephemeral("You are not authorized to edit items.")
            return self._parent_or_self(menu), False, True

        field_key, value = ITEM_ENUM_ACTIONS[menu.uniqueName]
        original_message.menuContext.itemDraft[field_key] = value
        return self._parent_or_self(menu), True, False

    async def _handle_field_edit_action(
        self, interface: "MenuInterface", menu: Menu, original_message: "OriginalMessage"
    ) -> SpecialActionResult:
        if not original_message.is_developer_admin:
            await interface.send_ephemeral("You are not authorized to edit drafts.")
            return self._parent_or_self(menu), False, True

        if interface.supports_modals:
            await interface.send_modal(self.runtime.build_field_edit_modal(menu, original_message))
        else:
            await interface.send_ephemeral("Field edit modal is available in Discord UI only.")
        return self._parent_or_self(menu), False, True
