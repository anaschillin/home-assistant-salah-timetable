"""Remote source persistence is isolated from approved prayer data."""

import base64
from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers.storage import Store
from homeassistant.util.file import WriteError
from homeassistant.util.json import load_json

from custom_components.salah_timetable.const import DOMAIN, STORAGE_VERSION
from custom_components.salah_timetable.parsers.csv_parser import CsvParser
from custom_components.salah_timetable.parsers.import_model import (
    ImportCandidate,
    ImportValidationError,
)
from custom_components.salah_timetable.persistence.storage import (
    PendingImportError,
    TimetableStorage,
)
from custom_components.salah_timetable.sources.source_model import (
    RemoteSource,
    validate_check,
)


def csv_candidate(value="05:45", year=2026):
    return CsvParser().parse(
        f"Date,Fajr\n{year}-10-21,{value}\n".encode(),
        timetable_id=f"annual-{year}",
        kind="annual",
        year=year,
        date_column="Date",
        columns={"Fajr": "fajr_begin"},
    )


def source(year=2026, url="https://example.com/timetable.csv"):
    return RemoteSource(
        f"annual-{year}",
        url,
        "csv",
        "annual",
        year,
        "Date",
        {"Fajr": "fajr_begin"},
        parser_id="csv_v1",
    )


async def storage(hass, entry):
    result = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await result.async_load()
    return result


async def test_url_stage_baseline_and_approval_survive_restart(hass, entry):
    current = await storage(hass, entry)
    profile = source()
    candidate = replace(
        csv_candidate(),
        source_url=profile.url,
        etag='"v1"',
        last_modified="Wed, 21 Oct 2026 10:00:00 GMT",
    )
    stage = await current.async_stage(candidate, remote_source=profile)
    assert current.for_date(date(2026, 10, 21)) is None
    assert current.remote_sources == {profile.source_id: profile}
    check = current.remote_checks[profile.source_id]
    assert check["last_seen_sha256"] == candidate.sha256
    assert check["etag"] == '"v1"'
    assert check["status"] == "pending"
    assert check["last_success"] == check["last_checked"]
    restored = await storage(hass, entry)
    assert restored.staged.stage_id == stage
    assert restored.staged.candidate == candidate
    await restored.async_approve(stage)
    restored = await storage(hass, entry)
    assert restored.approved_sources[profile.source_id] == candidate
    assert restored.remote_checks[profile.source_id]["status"] == "approved"
    assert restored.remote_sources[profile.source_id] == profile


async def test_rejection_keeps_seen_digest_and_last_good(hass, entry):
    current = await storage(hass, entry)
    original = csv_candidate()
    await current.async_approve(await current.async_stage(original))
    profile = source()
    candidate = replace(csv_candidate("06:00"), source_url=profile.url, etag='"v2"')
    stage = await current.async_stage(candidate, remote_source=profile)
    await current.async_reject(stage)
    restored = await storage(hass, entry)
    assert restored.remote_checks[profile.source_id]["status"] == "rejected"
    assert (
        restored.remote_checks[profile.source_id]["rejected_sha256"] == candidate.sha256
    )
    assert (
        restored.remote_checks[profile.source_id]["last_seen_sha256"]
        == candidate.sha256
    )
    assert restored.timetables == (original.timetable,)


async def test_profile_changes_reset_checks_and_stale_network_results_fail_cas(
    hass, entry
):
    first = await storage(hass, entry)
    second = await storage(hass, entry)
    original = source()
    changed = source(url="https://example.com/new.csv")
    await first.async_set_remote_source(original)
    await first.async_record_check(
        original.source_id,
        {"status": "unchanged", "last_seen_sha256": "a" * 64, "etag": '"old"'},
        expected_source=original,
    )
    await second.async_set_remote_source(changed, expected_source=original)
    assert second.remote_checks[original.source_id] == {"status": "configured"}
    candidate = replace(csv_candidate(), source_url=original.url)
    with pytest.raises(ValueError, match="changed"):
        await first.async_stage(candidate, expected_source=original)
    with pytest.raises(ValueError, match="changed"):
        await first.async_record_check(
            original.source_id,
            {"status": "error", "error_code": "request_failed"},
            expected_source=original,
        )
    with pytest.raises(ValueError, match="changed"):
        await first.async_remove_remote_source(
            original.source_id, expected_source=original
        )
    assert (await storage(hass, entry)).remote_sources[changed.source_id] == changed


async def test_removing_profile_preserves_approved_and_pending_data(hass, entry):
    current = await storage(hass, entry)
    original = csv_candidate()
    await current.async_approve(await current.async_stage(original))
    profile = source()
    candidate = replace(csv_candidate("06:00"), source_url=profile.url)
    stage = await current.async_stage(candidate, remote_source=profile)
    await current.async_remove_remote_source(profile.source_id, expected_source=profile)
    assert current.remote_sources == {}
    assert current.remote_checks == {}
    assert current.staged.stage_id == stage
    assert current.timetables == (original.timetable,)
    await current.async_approve(stage)
    assert current.approved_sources[profile.source_id] == candidate


async def test_configure_profile_cannot_change_pending_proposal(hass, entry):
    current = await storage(hass, entry)
    profile = source()
    candidate = replace(csv_candidate(), source_url=profile.url)
    await current.async_stage(candidate, remote_source=profile)
    with pytest.raises(PendingImportError):
        await current.async_set_remote_source(
            source(url="https://example.com/other.csv")
        )
    assert current.remote_sources[profile.source_id] == profile


async def test_remote_stage_failure_preserves_profile_and_approved_snapshot(
    hass, entry
):
    current = await storage(hass, entry)
    original = csv_candidate()
    await current.async_approve(await current.async_stage(original))
    profile = source()
    candidate = replace(csv_candidate("06:00"), source_url=profile.url)
    with (
        patch.object(
            current._store, "_write_prepared_data", side_effect=WriteError("disk full")
        ),
        pytest.raises(OSError),
    ):
        await current.async_stage(candidate, remote_source=profile)
    assert current.remote_sources == {}
    restored = await storage(hass, entry)
    assert restored.remote_sources == {}
    assert restored.remote_checks == {}
    assert restored.timetables == (original.timetable,)
    assert restored.staged is None


async def test_profile_and_check_maps_are_immutable(hass, entry):
    current = await storage(hass, entry)
    profile = source()
    await current.async_set_remote_source(profile)
    with pytest.raises(TypeError):
        current.remote_sources[profile.source_id] = profile
    with pytest.raises(TypeError):
        profile.columns["Fajr"] = "fajr_jamaat"
    with pytest.raises(TypeError):
        current.remote_checks[profile.source_id]["status"] = "error"


async def test_check_updates_merge_and_do_not_mutate_active_data(hass, entry):
    current = await storage(hass, entry)
    profile = source()
    await current.async_set_remote_source(profile)
    await current.async_record_check(
        profile.source_id,
        {
            "status": "unchanged",
            "last_success": "2026-10-21T10:00:00+00:00",
            "etag": '"ok"',
        },
        expected_source=profile,
    )
    await current.async_record_check(
        profile.source_id,
        {"status": "error", "error_code": "request_failed"},
        expected_source=profile,
    )
    assert (
        current.remote_checks[profile.source_id]["last_success"]
        == "2026-10-21T10:00:00+00:00"
    )
    assert current.remote_checks[profile.source_id]["etag"] == '"ok"'
    assert current.timetables == ()


async def test_v2_migration_preserves_pending_approved_and_old_candidate_schema(
    hass, entry
):
    original, proposed = csv_candidate(), csv_candidate("06:00", 2027)

    def legacy(candidate):
        data = candidate.as_dict()
        for key in (
            "source_format",
            "source_base64",
            "extracted_text",
            "source_url",
            "etag",
            "last_modified",
        ):
            data.pop(key)
        return data

    legacy_store = Store(hass, 2, f"{DOMAIN}.{entry.entry_id}", atomic_writes=True)
    await legacy_store.async_save(
        {
            "timetables": [original.timetable.as_dict()],
            "approved_sources": {"annual-2026": legacy(original)},
            "staged": {"stage_id": "a" * 32, "candidate": legacy(proposed)},
        }
    )
    current = await storage(hass, entry)
    assert current.approved_sources == {"annual-2026": original}
    assert current.staged.candidate == proposed
    assert current.remote_sources == {}
    assert current.remote_checks == {}
    saved = await hass.async_add_executor_job(load_json, legacy_store.path)
    assert saved["version"] == STORAGE_VERSION == 3
    assert saved["data"]["approved_sources"]["annual-2026"]["source_format"] == "csv"
    assert (await storage(hass, entry)).staged.candidate == proposed


async def test_failed_v2_migration_preserves_legacy_source(hass, entry):
    original = csv_candidate()
    legacy_store = Store(hass, 2, f"{DOMAIN}.{entry.entry_id}", atomic_writes=True)
    await legacy_store.async_save(
        {
            "timetables": [original.timetable.as_dict()],
            "approved_sources": {"annual-2026": original.as_dict()},
            "staged": None,
        }
    )
    before = await hass.async_add_executor_job(Path(legacy_store.path).read_bytes)
    current = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    with (
        patch.object(
            current._store, "_write_prepared_data", side_effect=WriteError("disk full")
        ),
        pytest.raises(OSError),
    ):
        await current.async_load()
    assert (
        await hass.async_add_executor_job(Path(legacy_store.path).read_bytes) == before
    )
    assert current.timetables == ()


@pytest.mark.parametrize(
    "check",
    [
        {"status": "raw server text"},
        {"url": "https://secret.invalid"},
        {"error_code": "https://secret.invalid/token"},
        {"etag": "x\r\ny"},
        {"last_checked": "2026-10-21T10:00:00"},
        {"last_seen_sha256": "not-a-digest"},
        {"rejected_sha256": "not-a-digest"},
    ],
)
def test_unsafe_check_metadata_is_rejected(check):
    with pytest.raises(ImportValidationError):
        validate_check(check)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/a.pdf",
        "https://127.0.0.1/a.pdf",
        "https://user:pass@example.com/a.pdf",
        "https://example.com:8443/a.pdf",
        "https://example.com/a.pdf#fragment",
    ],
)
def test_remote_profile_reuses_download_url_policy(url):
    with pytest.raises(ValueError):
        source(url=url)


def test_pdf_provenance_round_trip_and_tampering():
    original = csv_candidate()
    content = b"%PDF-1.7\nSynthetic binary provenance only\n%%EOF\n"
    candidate = replace(
        original,
        source_format="pdf",
        source_base64=base64.b64encode(content).decode(),
        extracted_text=original.source_text,
        sha256=sha256(content).hexdigest(),
        parser_id="pdf_table_v1",
    )
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate
    for mutation in (
        {"source_base64": "not base64"},
        {"source_base64": base64.b64encode(b"not a PDF").decode()},
        {"sha256": "a" * 64},
        {"extracted_text": "changed"},
        {"source_format": "csv"},
    ):
        with pytest.raises(ImportValidationError):
            ImportCandidate.from_dict(candidate.as_dict() | mutation)
