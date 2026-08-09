import json

import pytest

from examples.enum_product_status import CONFIG as ENUM_CONFIG, expected_configuration_hash as enum_hash, read_product_status
from examples.typed_release_date import CONFIG as DATE_CONFIG, expected_configuration_hash as date_hash, read_confirmed_date
from tools.canonical import configuration_hash


class Oracle:
    def __init__(self, config, status="CONFIRMED", value="2026-03-11"):
        self.config, self._status, self._value = config, status, value
        self.record = json.dumps({"configuration_hash": self.configuration_hash(), "status": status,
                                  "normalized_value": value})

    def configuration_hash(self):
        return configuration_hash(self.config)

    def get_config(self):
        return {"configuration_hash": self.configuration_hash()}

    def get_sources(self):
        return [{"url": url} for url in self.config["source_urls"]]

    def status(self):
        return self._status

    def value(self):
        return self._value

    def get_record(self):
        return self.record


def test_date_example_uses_independent_hash_and_views():
    assert date_hash() == configuration_hash(DATE_CONFIG)
    assert read_confirmed_date(Oracle(DATE_CONFIG)) == "2026-03-11"


def test_enum_example_refuses_non_actionable_statuses():
    assert enum_hash() == configuration_hash(ENUM_CONFIG)
    for status in ("CONFLICTED", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE"):
        with pytest.raises(RuntimeError, match="NOT_ACTIONABLE"):
            read_product_status(Oracle(ENUM_CONFIG, status, ""))
