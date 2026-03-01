from src.persistence.whitelist_store import WhitelistStore
from src.services.game_context import GameContext


class AdminWhitelistService:
    def __init__(
        self,
        whitelist_path: str,
        context: GameContext,
        default_admin_id: int = 191980469670248448,
    ):
        self.context = context
        self.store = WhitelistStore(whitelist_path, default_admin_id=default_admin_id)

    @property
    def whitelist_path(self) -> str:
        return self.store.whitelist_path

    @property
    def admin_ids(self) -> set[int]:
        return set(self.context.development_admin_whitelist)

    def ensure_exists(self):
        self.store.ensure_exists()

    def load(self):
        loaded = self.store.load_ids()
        self.context.development_admin_whitelist.clear()
        self.context.development_admin_whitelist.update(loaded)

    def is_admin(self, discord_id: int) -> bool:
        return int(discord_id) in self.context.development_admin_whitelist
