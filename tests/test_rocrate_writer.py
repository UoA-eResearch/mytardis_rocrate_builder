# Test writing the crate to disk and reading it back (can probably steal some stuff from the RO-Crate lib)
# type: ignore
# pylint: disable
import mock
from gnupg import GPG, GenKey, ImportResult
from pytest import fixture, raises, warns
from rocrate.rocrate import ROCrate

from mytardis_rocrate_builder.rocrate_dataclasses.crate_manifest import CrateManifest
from mytardis_rocrate_builder.rocrate_dataclasses.rocrate_dataclasses import MTMetadata
from mytardis_rocrate_builder.rocrate_writer import receive_keys_for_crate


@fixture
def test_gpg_import_missing(test_gpg_binary_location: str) -> ImportResult:
    result = ImportResult(test_gpg_binary_location)
    result.returncode = 2
    result.results.append(
        {"fingerprint": None, "problem": "0", "text": "No valid data found"}
    )
    return result


@fixture
def test_gpg_import_nothing(test_gpg_binary_location: str) -> ImportResult:
    result = ImportResult(gpg=test_gpg_binary_location)
    result.returncode = 0
    return result


@fixture
def test_gpg_import_sucess(
    test_gpg_binary_location: str, test_gpg_key: GenKey
) -> ImportResult:
    result = ImportResult(gpg=test_gpg_binary_location)
    result.fingerprints = [test_gpg_key.fingerprint]
    result.returncode = 0
    result.results.append(
        {"fingerprint": test_gpg_key.fingerprint, "ok": "1", "text": "Entirely new key"}
    )
    return result


@fixture
def test_gpg_import_fail(
    test_gpg_binary_location: str, test_gpg_key: GenKey
) -> ImportResult:
    result = ImportResult(gpg=test_gpg_binary_location)
    result.fingerprints = [test_gpg_key.fingerprint]
    result.returncode = 2
    result.results.append(
        {
            "fingerprint": test_gpg_key.fingerprint,
            "problem": "0",
            "text": "Other failure",
        }
    )
    return result


@mock.patch.object(GPG, "recv_keys")
def test_receive_keys(
    test_recv_keys,
    test_gpg_binary_location: str,
    test_gpg_key: str,
    test_sensitive_metadata: MTMetadata,
    test_gpg_import_nothing: ImportResult,
    test_gpg_import_missing: ImportResult,
    test_gpg_import_sucess: ImportResult,
    test_gpg_import_fail: ImportResult,
):
    manifest = CrateManifest()
    manifest.add_metadata([test_sensitive_metadata])
    test_recv_keys.return_value = test_gpg_import_nothing
    result = receive_keys_for_crate(test_gpg_binary_location, manifest)
    assert result.results == []

    test_recv_keys.return_value = test_gpg_import_fail
    result = receive_keys_for_crate(test_gpg_binary_location, CrateManifest())
    assert result.fingerprints == [test_gpg_key.fingerprint]

    test_recv_keys.return_value = test_gpg_import_sucess
    result = receive_keys_for_crate(test_gpg_binary_location, CrateManifest())
    assert result.fingerprints == [test_gpg_key.fingerprint]
    assert result.results[0].get("ok") == "1"

    with raises(Exception):
        test_recv_keys.return_value = test_gpg_import_missing
        result = receive_keys_for_crate(test_gpg_binary_location, CrateManifest())
        assert result.results == []
