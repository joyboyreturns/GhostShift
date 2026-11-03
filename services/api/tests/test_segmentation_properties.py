from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st

from app.services.segmentation import segment_document


@given(st.text(min_size=1, max_size=1000))
def test_segmentation_is_deterministic_and_offsets_roundtrip(content: str) -> None:
    first = segment_document("same-document", content)
    second = segment_document("same-document", content)
    assert [(s.id, s.text) for s in first] == [(s.id, s.text) for s in second]
    assert len({s.id for s in first}) == len(first)
    for segment in first:
        assert content[segment.start_offset : segment.end_offset] == segment.text
        assert segment.text.strip()
    for left, right in pairwise(first):
        assert left.end_offset <= right.start_offset
