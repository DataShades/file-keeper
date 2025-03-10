import pytest
from datetime import datetime
import pytz
from freezegun import freeze_time


@pytest.fixture()
def files_stopped_time():
    now = datetime.now(pytz.utc)
    with freeze_time(now):
        yield now
