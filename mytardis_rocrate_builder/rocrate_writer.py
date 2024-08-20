"""Functions for witing and archiving RO-Crates on disk
"""

import logging
import os
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import bagit
from gnupg import GPG, ImportResult
from rocrate.rocrate import ROCrate

from . import PROCESSES
from .rocrate_builder import ROBuilder
from .rocrate_dataclasses.crate_manifest import CrateManifest

logger = logging.getLogger(__name__)
DEFAULT_KEYSERVER = "https://keyserver.ubuntu.com"


def receive_keys_for_crate(
    gpg_binary: Path, crate_contents: CrateManifest, keyserver: str = DEFAULT_KEYSERVER
) -> ImportResult:
    """For all sensitive metadata recipients Receive gpg puiblic keys,
    using a given keyserver based on the fingerprints provided.

    Args:
        gpg_binary (Path): gpg binary on the local machine
        crate_contents (CrateManifest): the contents of this RO-Crate
        keyserver (str): the target keyserver to receive keys

    Returns:
        Dict: the result of the retreival operation
    """
    gpg = GPG(gpgbinary=gpg_binary)
    fingerprints = set()
    for metadata in crate_contents.metadata:
        if recipients := metadata.recipients:
            for recipient in recipients:
                if recipient.pubkey_fingerprints:
                    recipient_fingerprints = set(recipient.pubkey_fingerprints)
                    fingerprints.update(recipient_fingerprints)
    result: Dict[str, Any] = gpg.recv_keys(keyserver, fingerprints)
    return result


def write_crate(
    builder: ROBuilder,
    crate_source: Path,
    crate_destination: Path,
    crate_contents: CrateManifest,
    meta_only: bool = True,
) -> ROCrate:
    """Build an RO-Crate given a manifest of files

    Args:
        crate_source (Path): The soruce location, may contain an existing crate
        crate_destination (Path): where the RO-Crate is to be written
            -either location on disk if directly writing crate
            -or tmpfile location if crate is to be output as an archive
        crate_contents (CrateManifest): manifest of the RO-Crate

    Returns:
        ROCrate: _The RO-Crate object that has been written
    """
    logger.info("adding projects")
    _ = [builder.add_project(project) for project in crate_contents.projcets.values()]
    logger.info("adding experiments")
    _ = [
        builder.add_experiment(experiment)
        for experiment in crate_contents.experiments.values()
    ]
    logger.info("adding datasets")
    _ = [builder.add_dataset(dataset) for dataset in crate_contents.datasets.values()]
    logger.info("adding datafiles")
    _ = [builder.add_datafile(datafile) for datafile in crate_contents.datafiles]
    # crate.source = None

    logger.info("adding mytardis metadata")
    _ = [builder.add_metadata(metadata) for metadata in crate_contents.metadata]

    logger.info("adding access level controls")
    _ = [builder.add_acl(acl) for acl in crate_contents.acls]
    logger.info(
        "writing crate metadata and moving files from %s to %s",
        crate_source,
        crate_destination,
    )
    if not crate_destination.exists():
        crate_destination.mkdir(parents=True)
    if meta_only:
        builder.crate.metadata.write(crate_destination)
        return ROCrate
    builder.crate.write(crate_destination)
    return ROCrate


def bagit_crate(crate_path: Path, contact_name: str) -> None:
    """Put an RO-Crate into a bagit archive, moving all contents down one directory

    Args:
        crate_path (Path): location of the RO-Crate
        contact_name (str): contact name listed on the RO-Crate
    """
    bagit.make_bag(
        crate_path,
        {"Contact-Name": contact_name},
        processes=PROCESSES,
        checksum=["md5", "sha256", "sha512"],
    )


def archive_crate(
    archive_type: str | None,
    output_location: Path,
    crate_location: Path,
    validate: Optional[bool],
) -> None:
    """Archive the RO-Crate as a TAR, GZIPPED TAR or ZIP archive

    Args:
        archive_type (str | None): the archive format [tar.gz, tar, or zip]
        output_location (Path): the path where the archive should be written to
        crate_location (Path): the path of the RO-Crate to be archived
    """
    if validate:
        bag = bagit.Bag(crate_location.as_posix())
        if not bag.is_valid():
            logger.warning("Bagit for crate is not valid!")
    if not archive_type:
        return
    file_location = output_location.parent / (f"{output_location.name}.{archive_type}")
    match archive_type:
        case "tar.gz":
            logger.info("Tar GZIP archiving %s", crate_location.name)
            with tarfile.open(
                file_location,
                mode="w:gz",
            ) as out_tar:
                out_tar.add(
                    crate_location,
                    arcname=crate_location.name,
                    recursive=True,
                )
            out_tar.close()
        case "tar":
            logger.info("Tar archiving %s", crate_location.name)
            with tarfile.open(file_location, mode="w") as out_tar:
                out_tar.add(
                    crate_location,
                    arcname=crate_location.name,
                    recursive=True,
                )
            out_tar.close()
        case "zip":
            logger.info("zip archiving %s", crate_location.name)
            with zipfile.ZipFile(file_location, "w") as out_zip:
                for root, _, files in os.walk(crate_location):
                    for filename in files:
                        arcname = (
                            crate_location.name
                            / Path(root).relative_to(crate_location)
                            / filename
                        )
                        logger.info("wirting to archived path %s", arcname)
                        out_zip.write(os.path.join(root, filename), arcname=arcname)


def bulk_encrypt_file(
    gpg_binary: Path,
    pubkey_fingerprints: List[str],
    data_to_encrypt: Path,
    output_path: Path,
) -> None:
    """Encrypt a file using gnupg to a specific set of recipents

    Args:
        gpg_binary (Path): the gpg binary to run this encryption
        pubkey_fingerprints (List[str]): a list of public key fingerprints to encrypt to
        data_to_encrypt (Path): the location of the file to encrypt
        output_path (Path): the desitnation of the output encrypted file
    """
    gpg = GPG(gpgbinary=gpg_binary)
    if data_to_encrypt.is_file():
        with open(data_to_encrypt, "rb") as f:
            status = gpg.encrypt(
                f.read(),
                recipients=pubkey_fingerprints,
                armor=False,
                output=output_path.with_suffix(data_to_encrypt.suffix + ".gpg"),
            )

    else:
        with open(f"{data_to_encrypt}.tar", "rb") as f:
            status = gpg.encrypt(
                f.read(),
                recipients=pubkey_fingerprints,
                armor=False,
                output=output_path.with_suffix(data_to_encrypt.suffix + ".tar.gpg"),
            )
        logger.info("encrypt ok: %s", status.ok)
        logger.info("encrypt status: %s", status.status)


def bulk_decrypt_file(
    gpg_binary: Path,
    data_to_decrypt: Path,
    output_path: Path,
    passphrase: str | None = None,
) -> None:
    """Add

    Args:
        gpg_binary (Path): _description_
        data_to_decrypt (Path): _description_
        output_path (Path): _description_
    """

    gpg = GPG(gpgbinary=gpg_binary)
    if data_to_decrypt.is_file():
        with open(data_to_decrypt, "rb") as f:
            result = gpg.decrypt(f.read(), passphrase=passphrase)
            logger.info("encrypt ok: %s", result.ok)
            logger.info("encrypt status: %s", result.status)
            if result.ok:
                with open(output_path, "wb") as of:
                    of.write(result.data)
                of.close()
        f.close()
