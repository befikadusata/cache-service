from uuid import UUID

import pytest
from pydantic import ValidationError

from cache_service.config import Settings
from cache_service.schemas import PayloadCreate, PayloadCreated, PayloadOutput


def test_preserves_exact_input_and_accepts_empty_lists():
    request = PayloadCreate(list1=[" a ", ""], list2=["a", "é"])
    assert request.model_dump() == {"list1": [" a ", ""], "list2": ["a", "é"]}
    assert PayloadCreate(list1=[], list2=[]).list1 == []


@pytest.mark.parametrize("data", [
    {}, {"list1": [], "list2": ["a"]},
    {"list1": [1], "list2": ["a"]}, {"list1": [None], "list2": ["a"]},
    {"list1": [True], "list2": ["a"]}, {"list1": "a", "list2": ["a"]},
    {"list1": ("a",), "list2": ["a"]},
    {"list1": [], "list2": [], "unexpected": True},
])
def test_rejects_invalid_input(data):
    with pytest.raises(ValidationError):
        PayloadCreate.model_validate(data)


def test_configured_limits_include_both_lists_and_accept_boundary():
    settings = Settings(_env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        max_list_items=1, max_string_characters=2, max_total_characters=3)
    context = {"settings": settings}
    PayloadCreate.model_validate({"list1": ["éé"], "list2": ["a"]}, context=context)
    for data in [
        {"list1": ["a", "b"], "list2": ["c", "d"]},
        {"list1": ["abc"], "list2": [""]},
        {"list1": ["ab"], "list2": ["cd"]},
    ]:
        with pytest.raises(ValidationError):
            PayloadCreate.model_validate(data, context=context)


@pytest.mark.parametrize("field,value", [
    ("max_list_items", 0), ("max_string_characters", 0), ("max_total_characters", 0),
    ("generation_timeout_seconds", 0), ("generation_timeout_seconds", float("inf")),
    ("read_timeout_seconds", -1), ("read_timeout_seconds", float("nan")),
])
def test_rejects_invalid_budgets(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql+asyncpg://test:test@localhost/test",
                 **{field: value})


def test_response_serialization():
    identifier = UUID("00000000-0000-4000-8000-000000000001")
    assert PayloadCreated(id=identifier).model_dump(mode="json") == {"id": str(identifier)}
    assert PayloadOutput(output="").model_dump() == {"output": ""}
