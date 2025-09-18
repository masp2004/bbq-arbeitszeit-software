import datetime
import pytest


def _shift(start, end, break_time=0):
    return {
        "start": start,
        "end": end,
        "break": break_time,
    }


def test_smoke():
    assert True


def test_shift():
    s = _shift(
        datetime.datetime(2023, 1, 1, 9, 0, 0),
        datetime.datetime(2023, 1, 1, 17, 0, 0),
        break_time=30,
    )
    assert s["start"] == datetime.datetime(2023, 1, 1, 9, 0, 0)
    assert s["end"] == datetime.datetime(2023, 1, 1, 17, 0, 0)
    assert s["break"] == 30


def test_long_assert():
    result = some_function_call(
        arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8
    )
    assert result == expected_value, (
        "The result did not match the expected value when called with "
        "multiple arguments"
    )

