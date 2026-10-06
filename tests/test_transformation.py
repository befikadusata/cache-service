import pytest

from cache_service.transformation import Transformer, compose_output, uppercase_transform


@pytest.mark.parametrize("source,expected", [
    ("hello", "HELLO"),
    ("MiXeD", "MIXED"),
    ("ALREADY", "ALREADY"),
    ("", ""),
    ("  hello\n\t", "  HELLO\n\t"),
    ("123, !", "123, !"),
    ("straße", "STRASSE"),
    ("é", "É"),
    ("e\u0301", "E\u0301"),
    ("😀", "😀"),
])
async def test_uppercase_conversion_preserves_content_except_case(source, expected):
    assert await uppercase_transform(source) == expected


async def test_sample_transformation_and_alternating_composition():
    transformer: Transformer = uppercase_transform
    list1 = [await transformer(value) for value in ["a", "b", "c"]]
    list2 = [await transformer(value) for value in ["d", "e", "f"]]
    assert compose_output(list1, list2) == "A, D, B, E, C, F"


async def test_transformer_can_be_replaced_without_changing_composition():
    async def reverse(source: str) -> str:
        return source[::-1]

    transformer: Transformer = reverse
    assert compose_output([await transformer("abc")], [await transformer("def")]) == (
        "cba, fed"
    )


async def test_transformer_failure_propagates_to_caller():
    async def failing(source: str) -> str:
        raise RuntimeError("Transformer unavailable")

    transformer: Transformer = failing
    with pytest.raises(RuntimeError, match="Transformer unavailable"):
        await transformer("a")


@pytest.mark.parametrize("list1,list2,expected", [
    ([], [], ""),
    ([""], [""], ", "),
    (["", "B"], ["D", ""], ", D, B, "),
    (["A", "A"], ["B", "B"], "A, B, A, B"),
    ([" a, b "], ["c\n"], " a, b , c\n"),
    (("one", "two"), ("three", "four"), "one, three, two, four"),
])
def test_composition_preserves_completed_values_and_order(list1, list2, expected):
    original1, original2 = list(list1), list(list2)
    assert compose_output(list1, list2) == expected
    assert list(list1) == original1
    assert list(list2) == original2


@pytest.mark.parametrize("list1,list2", [(["A"], []), ([], ["B"])])
def test_composition_rejects_unequal_lengths(list1, list2):
    with pytest.raises(ValueError):
        compose_output(list1, list2)
