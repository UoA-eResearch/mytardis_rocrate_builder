# Test writing the crate to disk and reading it back (can probably steal some stuff from the RO-Crate lib)
# type: ignore
# pylint: disable
import copy
import os
import tarfile
import zipfile
from pathlib import Path

import bagit
import mock
from gnupg import GPG, GenKey, ImportResult
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pytest import fixture, mark, raises, warns
from rocrate.rocrate import ROCrate

from mytardis_rocrate_builder.rocrate_dataclasses.crate_manifest import (
    CrateManifest,
    reduce_to_dataset,
)
from mytardis_rocrate_builder.rocrate_dataclasses.rocrate_dataclasses import (
    Datafile,
    Dataset,
    MTMetadata,
)
from mytardis_rocrate_builder.rocrate_writer import (
    archive_crate,
    bagit_crate,
    bulk_decrypt_file,
    bulk_encrypt_file,
    receive_keys_for_crate,
    write_crate,
)

METADATA_FILE_NAME = "ro-crate-metadata.json"


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


def test_reduce_to_dataset(
    test_manifest: CrateManifest, test_datafile, test_dataset, tmpdir, data_dir, builder
):
    manifest_with_extras = CrateManifest(
        projects=test_manifest.projects,
        experiments=test_manifest.experiments,
        datasets=test_manifest.datasets,
        datafiles=test_manifest.datafiles,
        metadata=test_manifest.metadata,
        acls=test_manifest.acls,
    )

    Project = mock.MagicMock()
    Experiment = mock.MagicMock()
    Instrument = mock.MagicMock()
    unlinked_dataset = Dataset(
        name="unlinked dataset",
        experiments=Experiment(),
        directory=Path("/unlinked_dataset/"),
        instrument=Instrument(),
        description="a second dataset not linked to the first",
    )
    unlinked_datafile = Datafile(
        name="unlinked datafile",
        filepath=Path("/unlinked_dataset/unlinked_datafile"),
        description="a datafile not linked to the main dastaset",
        dataset=unlinked_dataset,
    )
    ACL = mock.MagicMock()
    Metadata = mock.MagicMock()

    manifest_with_extras.add_projects({"test_extra_project": Project()})
    manifest_with_extras.add_experiments({"test_extra_dc": Experiment()})
    manifest_with_extras.add_datafiles([unlinked_datafile])
    manifest_with_extras.add_datasets({"test_extra_ds": unlinked_dataset})
    manifest_with_extras.add_metadata([Metadata()])
    manifest_with_extras.add_acls([ACL()])
    out_manifest = reduce_to_dataset(manifest_with_extras, test_dataset)
    assert out_manifest.projects == test_manifest.projects
    assert out_manifest.projects != manifest_with_extras.projects

    assert out_manifest.experiments == test_manifest.experiments
    assert out_manifest.experiments != manifest_with_extras.experiments

    assert out_manifest.datasets == test_manifest.datasets
    assert out_manifest.datasets != manifest_with_extras.datasets

    assert unlinked_dataset not in out_manifest.datasets.values()
    assert unlinked_datafile not in out_manifest.datafiles

    assert [metadata.id for metadata in out_manifest.metadata] == [
        metadata.id for metadata in test_manifest.metadata
    ]
    assert [acl.id for acl in out_manifest.acls] == [
        acl.id for acl in test_manifest.acls
    ]
    # make sure the crate has complete data to be written
    write_crate(
        builder=builder,
        crate_source=data_dir,
        crate_destination=tmpdir,
        crate_contents=out_manifest,
        meta_only=True,
    )


@mark.parametrize("meta_only", [(False), (True)])
def test_write_crate(
    tmpdir,
    data_dir,
    builder,
    test_manifest,
    test_datafile,
    test_dataset,
    ro_crate_helpers,
    manifest_ro_contents,
    meta_only,
):
    crate_destination = tmpdir / "output_crate"
    os.chdir(data_dir)
    write_crate(
        builder=builder,
        crate_source=data_dir,
        crate_contents=test_manifest,
        crate_destination=crate_destination,
        meta_only=meta_only,
    )
    # Check files have been moved (or not if meta only is false)
    assert Path(crate_destination / METADATA_FILE_NAME).is_file()
    assert Path(crate_destination / test_dataset.directory).is_dir() != meta_only
    assert (
        Path(
            crate_destination / test_dataset.directory / test_datafile.filepath
        ).is_file()
        != meta_only
    )
    assert not Path(
        crate_destination / test_dataset.directory / "file_that_should_not_move.bam"
    ).is_file()
    # validate crate entites are created correctly
    entites = ro_crate_helpers.read_json_entities(crate_destination)
    ro_crate_helpers.check_crate(entites)
    ro_crate_helpers.check_crate_contains(entites, manifest_ro_contents)


def test_bag_crage(tmpdir, data_dir, builder, test_person_name):
    crate_destination = tmpdir / "output_crate"
    manifest = CrateManifest()
    write_crate(
        builder=builder,
        crate_source=data_dir,
        crate_destination=crate_destination,
        crate_contents=manifest,
        meta_only=True,
    )

    bagit_crate(crate_destination, test_person_name)
    assert Path(crate_destination / "data").is_dir()
    assert Path(crate_destination / "data" / METADATA_FILE_NAME).is_file()
    bag = bagit.Bag(crate_destination.as_posix())
    assert bag.is_valid()
    archive_crate("zip", crate_destination, crate_destination, True)


def test_zip_crate(tmpdir, data_dir, builder, test_person_name, ro_crate_helpers):
    crate_destination = tmpdir / "output_crate"
    manifest = CrateManifest()
    write_crate(
        builder=builder,
        crate_source=data_dir,
        crate_destination=crate_destination,
        crate_contents=manifest,
        meta_only=True,
    )
    archive_destination = tmpdir / "zipped_crate/"
    archive_output = tmpdir / "files_landing/"
    archive_crate("zip", archive_destination, crate_destination, False)
    zip_path = archive_destination.as_posix() + ".zip"
    assert Path(zip_path).is_file()
    with zipfile.ZipFile(zip_path) as validate_zip:
        assert validate_zip.namelist()
        metadata_path = validate_zip.extract(
            f"output_crate/{METADATA_FILE_NAME}", path=archive_output
        )
        entites = ro_crate_helpers.read_json_entities(Path(metadata_path).parent)
        ro_crate_helpers.check_crate(entites)
        validate_zip.close()


@mark.parametrize("tar_type,read_mode", [("tar.gz", "r:gz"), ("tar", "r")])
def test_tar_crate(
    tmpdir, data_dir, builder, test_person_name, ro_crate_helpers, tar_type, read_mode
):
    crate_destination = tmpdir / "output_crate"
    manifest = CrateManifest()
    write_crate(
        builder=builder,
        crate_source=data_dir,
        crate_destination=crate_destination,
        crate_contents=manifest,
        meta_only=True,
    )
    archive_destination = tmpdir / "tarred_crate/"
    archive_output = tmpdir / "files_landing/"
    archive_crate(tar_type, archive_destination, crate_destination, False)
    tar_path = archive_destination.as_posix() + "." + tar_type
    assert Path(tar_path).is_file()
    with tarfile.open(tar_path, read_mode) as validate_tar:
        assert validate_tar.getnames()
        validate_tar.extract(f"output_crate/{METADATA_FILE_NAME}", path=archive_output)
        metadata_path = archive_output / "output_crate"
        entites = ro_crate_helpers.read_json_entities(Path(metadata_path))
        ro_crate_helpers.check_crate(entites)
        validate_tar.close()


# check files with random input come in and out the same (probably due to us having messed about with them before GPG does the work)
@given(st.binary())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
    max_examples=25,
)
def test_bulk_encrypt_and_decrypt(
    tmpdir,
    data_dir,
    test_gpg_binary_location,
    test_gpg_key,
    test_passphrase,
    bytes_data,
):
    target_test_file = data_dir / "file_to_encrypt"
    with open(target_test_file, "wb") as of:
        of.write(bytes_data)
    of.close()
    target_encrypted_file = target_test_file.as_posix() + ".gpg"
    target_decrypted_file = target_test_file.as_posix() + ".decrypted"
    bulk_encrypt_file(
        gpg_binary=test_gpg_binary_location,
        pubkey_fingerprints=[test_gpg_key.fingerprint],
        data_to_encrypt=target_test_file,
        output_path=target_test_file,
    )
    assert Path(target_encrypted_file).is_file()
    bulk_decrypt_file(
        gpg_binary=test_gpg_binary_location,
        data_to_decrypt=Path(target_encrypted_file),
        output_path=Path(target_decrypted_file),
        passphrase=test_passphrase,
    )
    with open(target_test_file, "rb") as f1:
        with open(target_decrypted_file, "rb") as f2:
            assert f1.read() == f2.read()
