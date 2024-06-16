from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import List, Dict, Annotated, Any, Optional


class Player(Document):
    player_name: Indexed(str, unique=True)
    tokens: float = 0.0
    items: Dict[str, int] = Field(default_factory=dict)
    can_claim: List[int] = Field(default_factory=list)
    claimed: List[int] = Field(default_factory=list)
    task_progress: Dict[int, int] = Field(default_factory=dict)
    checkin: Dict[str, int] = Field(default_factory=lambda: {"max_consecutive_days": 0, "current_consecutive_days": 0})

    class Config:
        schema_extra = {
            "example": {
                "player_name": "JohnDoe",
                "tokens": 100.5,
                "items": {"sword": 1, "shield": 2},
                "can_claim": [101, 102],
                "claimed": [100],
                "task_progress": {201: 2, 202: 5},
                "checkin": {"max_consecutive_days": 5, "current_consecutive_days": 3}
            }
        }

    def update_tokens(self, amount: float) -> None:
        """Update the number of tokens."""
        self.tokens += amount
        self.save()

    def add_item(self, item_name: str, quantity: int) -> None:
        """Add or update items in the inventory."""
        if item_name in self.items:
            self.items[item_name] += quantity
        else:
            self.items[item_name] = quantity
        self.save()

    def record_task_progress(self, task_id: int, progress: int) -> None:
        """Record the progress of a specific task."""
        self.task_progress[task_id] = progress
        self.save()

    def update_checkin(self, consecutive_days: int) -> None:
        """Update check-in information."""
        self.checkin["current_consecutive_days"] = consecutive_days
        if consecutive_days > self.checkin["max_consecutive_days"]:
            self.checkin["max_consecutive_days"] = consecutive_days
        self.save()

    @classmethod
    async def by_id(cls, player_id: str) -> Optional["Player"]:
        """Get a user by email."""
        return await cls.find_one(cls.player_name == player_id)