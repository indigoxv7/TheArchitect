from src.domain.Spells import Spell
from src.persistence.spellbook_store import SpellbookStore
from src.services.game_context import GameContext


class SpellService:
    def __init__(self, spellbook_path: str, context: GameContext):
        self.context = context
        self.store = SpellbookStore(spellbook_path)

    def load_spellbook(self):
        payload = self.store.load()
        raw_spells = payload.get("spells", [])

        self.context.global_spellbook.clear()
        for item in raw_spells:
            try:
                spell = Spell.from_dict(item)
            except Exception:
                continue
            self.context.global_spellbook[spell.name] = spell

        self.context.spellbook_overview = self.build_spellbook_overview()

    def save_spellbook(self):
        spells = [spell.to_dict() for spell in self.list_spells()]
        payload = {"format_version": 1, "spells": spells}
        self.store.save(payload)
        self.context.spellbook_overview = self.build_spellbook_overview()

    def list_spells(self) -> list[Spell]:
        return [self.context.global_spellbook[name] for name in sorted(self.context.global_spellbook.keys())]

    def get_spell(self, name: str) -> Spell | None:
        return self.context.global_spellbook.get(name)

    def create_spell_from_dict(self, data: dict):
        spell = Spell.from_dict(data)
        if spell.name in self.context.global_spellbook:
            raise ValueError(f"Spell '{spell.name}' already exists.")
        self.context.global_spellbook[spell.name] = spell
        self.save_spellbook()

    def edit_spell_from_patch(self, spell_name: str, patch: dict):
        existing = self.get_spell(spell_name)
        if existing is None:
            raise ValueError(f"Spell '{spell_name}' does not exist.")

        merged = existing.to_dict()
        merged.update(patch)
        if "name" not in merged or not str(merged["name"]).strip():
            merged["name"] = existing.name

        updated = Spell.from_dict(merged)

        if updated.name != existing.name:
            self.context.global_spellbook.pop(existing.name, None)
        self.context.global_spellbook[updated.name] = updated
        self.save_spellbook()

    def build_spellbook_overview(self, max_lines: int = 20) -> str:
        spells = self.list_spells()
        if not spells:
            return "No spells in spellbook yet."

        lines = []
        for spell in spells[:max_lines]:
            affinity_value = spell.affinity.value if hasattr(spell.affinity, "value") else spell.affinity
            lines.append(f"- {spell.name} (Lv {spell.level}, {affinity_value})")

        if len(spells) > max_lines:
            lines.append(f"... and {len(spells) - max_lines} more")

        return "\n".join(lines)
