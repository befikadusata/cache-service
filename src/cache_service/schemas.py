"""Payload wire models; endpoints are implemented in B07."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr, ValidationInfo, model_validator

from cache_service.config import Settings


class PayloadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    list1: list[StrictStr]
    list2: list[StrictStr]

    @model_validator(mode="after")
    def validate_lists(self, info: ValidationInfo) -> "PayloadCreate":
        if len(self.list1) != len(self.list2):
            raise ValueError("Lists must have equal lengths")
        settings = info.context.get("settings") if info.context else None
        if settings is None:
            settings = Settings.model_construct()
        if len(self.list1) > settings.max_list_items:
            raise ValueError("List item limit exceeded")
        total = 0
        for values in (self.list1, self.list2):
            for value in values:
                if len(value) > settings.max_string_characters:
                    raise ValueError("String character limit exceeded")
                total += len(value)
        if total > settings.max_total_characters:
            raise ValueError("Total character limit exceeded")
        return self


class PayloadCreated(BaseModel):
    id: UUID


class PayloadOutput(BaseModel):
    output: str
