from app.schemas.response import error, success


def test_success_envelope_carries_data_and_no_error() -> None:
    assert success({"total": 3}).model_dump() == {"data": {"total": 3}, "error": None}


def test_error_envelope_carries_error_and_no_data() -> None:
    body = error("not_found", "Missing").model_dump()

    assert body == {
        "data": None,
        "error": {"code": "not_found", "message": "Missing", "details": None},
    }
