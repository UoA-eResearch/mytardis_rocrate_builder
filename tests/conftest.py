# pylint: disable
#  type: ignore
# pylint: disable
# test building a functional crate out of components
import copy
import json
import shutil
from datetime import datetime
from pathlib import Path
from sys import platform
from typing import Any, Dict, List

from gnupg import GPG, GenKey
from pytest import fixture
from rocrate.model import Entity as RO_Entity
from rocrate.model.contextentity import ContextEntity as ROContextEntity
from rocrate.model.dataset import Dataset as RODataset
from rocrate.model.file import File as RODataFile
from rocrate.model.person import Person as ROPerson
from rocrate.rocrate import ROCrate
from rocrate.utils import get_norm_value

from mytardis_rocrate_builder.rocrate_builder import (
    MT_METADATA_SCHEMATYPE,
    ROBuilder,
    serialize_optional_date,
)
from mytardis_rocrate_builder.rocrate_dataclasses.crate_manifest import CrateManifest
from mytardis_rocrate_builder.rocrate_dataclasses.rocrate_dataclasses import (
    ACL,
    MT_METADATA_TYPE,
    BaseObject,
    ContextObject,
    Datafile,
    Dataset,
    Experiment,
    Facility,
    Group,
    Instrument,
    License,
    MTMetadata,
    MyTardisContextObject,
    Organisation,
    Person,
    Project,
    User,
)

TEST_DATA_NAME = "test-data"
THIS_DIR = Path(__file__).absolute().parent


@fixture
def test_ogranization_name() -> str:
    return "Unseen Univeristy"


@fixture
def test_url() -> str:
    return "https://duckduckgo.com/"


@fixture
def test_person_name() -> str:
    return "Tom Baker"


@fixture
def test_email() -> str:
    return "mailmaster@brigadoon.alba.uk"


@fixture
def test_name() -> str:
    return "Name"


@fixture
def test_instrument_name() -> str:
    return "P.Express. Smelloscope"


@fixture
def test_metadata_id() -> str:
    return "metadata_name"


@fixture
def test_metadata_value() -> str:
    return "NHI0000"


@fixture
def test_metadata_type() -> str:
    return MT_METADATA_TYPE[2]


@fixture
def test_description() -> str:
    "descsription for an object"


@fixture
def test_datatime() -> datetime:
    return datetime(1, 1, 1, 0, 0)


@fixture
def test_extra_properties() -> Dict:
    return {
        "quantity": 16,
        "units": "tons",
        "days": datetime(1, 1, 1, 0, 0).isoformat(),
        "soul": "IOU",
        "left-right": ["iron", "steel"],
    }


@fixture
def test_extra_properties_output() -> Dict:
    return {
        "additionalProperties": [
            {"@type": "PropertyValue", "name": "quantity", "value": 16},
            {"@type": "PropertyValue", "name": "units", "value": "tons"},
            {"@type": "PropertyValue", "name": "days", "value": "0001-01-01T00:00:00"},
            {"@type": "PropertyValue", "name": "soul", "value": "IOU"},
            {
                "@type": "PropertyValue",
                "name": "left-right",
                "value": ["iron", "steel"],
            },
        ]
    }


@fixture
def test_schema_type() -> str:
    return "Thing"


@fixture
def test_upi() -> str:
    return "jbon007"


@fixture
def test_ogranization_type() -> str:
    return "Organization"


@fixture
def test_person_type() -> str:
    return "Person"


@fixture
def test_ethics_policy() -> str:
    return "https://dnafriend.com/values"


@fixture
def test_directory() -> Path:
    return Path("test_dataset/")


@fixture
def test_filepath() -> Path:
    return Path("test_datafile.bam")


@fixture
def test_not_used_filepath() -> Path:
    # a test filepath for a file that exists but is not included in the RO-Crate
    return Path("file_that_should_not_move.bam")


@fixture(name="crate")
def fixture_crate() -> ROCrate:
    return ROCrate()


@fixture(name="builder")
def fixture_builder(crate: ROCrate) -> ROBuilder:
    return ROBuilder(crate)


@fixture
def test_passphrase():
    return "JosiahCarberry1929/13/09"


@fixture
def test_gpg_binary_location() -> str:
    if gpg_which := shutil.which("gpg"):
        return gpg_which
    if platform in ["linux", "linux2"]:
        # linux
        return "/usr/bin/gpg"
    elif platform == "darwin":
        # OS X
        return "/opt/homebrew/bin/gpg"
    elif platform == "win32":
        # Windows
        return "C:\\Program Files (x86)\\GnuPG\\bin\\gpg.exe"
    raise NotImplementedError(
        "Unknown OS, please define where the gpg executable binary can be located"
    )
    return ""


@fixture()
def test_gpg_object(test_gpg_binary_location):
    gpg = GPG(test_gpg_binary_location)
    return gpg


@fixture
def test_organization(
    test_ogranization_name: str,
    test_location: str,
    test_url: str,
) -> Organisation:
    return Organisation(
        mt_identifiers=[test_ogranization_name],
        name=test_ogranization_name,
        location=test_location,
        url=test_url,
        research_org=True,
    )


@fixture
def test_group() -> Group:
    return Group(name="test_group")


@fixture
def test_metadata_schema() -> str:
    return "http://rocrate.testing/project/1/schema"


@fixture
def test_person(
    test_person_name: str,
    test_email: str,
    test_organization: Organisation,
    test_upi: str,
):
    return Person(
        name=test_person_name,
        email=test_email,
        affiliation=test_organization,
        mt_identifiers=[test_upi],
    )


@fixture
def test_gpg_key(test_gpg_object: GPG, test_passphrase: str) -> GenKey:
    key_input = test_gpg_object.gen_key_input(
        key_type="RSA",
        key_length=1024,
        Passphrase=test_passphrase,
        key_usage="sign encrypt",
    )
    key = test_gpg_object.gen_key(key_input)
    yield key
    test_gpg_object.delete_keys(key.fingerprint, True, passphrase=test_passphrase)
    test_gpg_object.delete_keys(key.fingerprint, passphrase=test_passphrase)


@fixture
def test_second_gpg_key(test_gpg_object: GPG, test_passphrase: str) -> GenKey:
    key_input = test_gpg_object.gen_key_input(
        key_type="RSA",
        key_length=1024,
        Passphrase=test_passphrase,
        key_usage="sign encrypt",
    )
    key = test_gpg_object.gen_key(key_input)
    yield key
    test_gpg_object.delete_keys(key.fingerprint, True, passphrase=test_passphrase)
    test_gpg_object.delete_keys(key.fingerprint, passphrase=test_passphrase)


@fixture
def test_user(
    test_person_name: str,
    test_email: str,
    test_organization: Organisation,
    test_gpg_key: GenKey,
    test_group: Group,
    test_datatime: test_datatime,
):
    return User(
        name=test_person_name,
        email=test_email,
        affiliation=test_organization,
        mt_identifiers=[test_person_name],
        pubkey_fingerprints=[test_gpg_key.fingerprint],
        last_login=test_datatime,
        date_joined=test_datatime,
        groups=[test_group],
    )


@fixture
def test_second_user(
    test_person_name: str,
    test_email: str,
    test_organization: Organisation,
    test_second_gpg_key: GenKey,
    test_group: Group,
    test_datatime: test_datatime,
):
    return User(
        name=test_person_name + "secondary",
        email=test_email,
        affiliation=test_organization,
        mt_identifiers=[test_person_name],
        pubkey_fingerprints=[test_second_gpg_key.fingerprint],
        last_login=test_datatime,
        date_joined=test_datatime,
        groups=[test_group],
    )


@fixture
def test_base_object() -> BaseObject:
    return BaseObject()


@fixture
def test_mytardis_metadata(
    test_name: str,
    test_metadata_value: str,
    test_metadata_type: str,
    test_metadata_id: str,
    test_metadata_schema: str,
    test_datafile: Datafile,
) -> MTMetadata:
    return MTMetadata(
        name=test_name,
        value=test_metadata_value,
        mt_type=test_metadata_type,
        sensitive=False,
        parent=test_datafile,
        mt_schema=test_metadata_schema,
        recipients=None,
    )


@fixture
def test_sensitive_metadata(
    test_name: str,
    test_metadata_value: str,
    test_metadata_type: str,
    test_metadata_id: str,
    test_metadata_schema: str,
    test_datafile: Datafile,
    test_user: User,
    test_second_user: User,
) -> MTMetadata:
    return MTMetadata(
        name=test_name + "sensitive",
        value=test_metadata_value,
        mt_type=test_metadata_type,
        sensitive=True,
        parent=test_datafile,
        mt_schema=test_metadata_schema,
        recipients=[test_user, test_second_user],
    )


@fixture
def test_context_object(
    test_name: str,
    test_description: str,
    test_datatime,
    test_extra_properties,
    test_schema_type,
) -> ContextObject:
    return ContextObject(
        name=test_name,
        description=test_description,
        mt_identifiers=["test_context_object"],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
    )


@fixture
def test_location(test_datatime, test_group) -> Facility:
    return Facility(
        name="test lab",
        description="the lab for testing things",
        mt_identifiers=None,
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=None,
        manager_group=test_group,
    )


@fixture
def test_instrument(
    test_instrument_name,
    test_location,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
) -> Instrument:
    return Instrument(
        name=test_instrument_name,
        description=test_description,
        mt_identifiers=[test_instrument_name],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
        location=test_location,
    )


@fixture
def test_org_ACL(
    test_organization,
    test_ogranization_type,
    test_description,
    test_extra_properties,
    test_group,
    test_datafile,
) -> ACL:
    return ACL(
        name="test_audiance_acl",
        grantee=test_group,
        grantee_type="Audiance",
        mytardis_owner=True,
        mytardis_can_download=True,
        mytardis_see_sensitive=False,
        parent=test_datafile,
    )


@fixture
def test_person_ACL(
    test_user,
    test_person_type,
    test_description,
    test_extra_properties,
    test_datafile,
) -> ACL:
    return ACL(
        name="test_person_acl",
        grantee=test_user,
        grantee_type="Person",
        mytardis_owner=False,
        mytardis_can_download=False,
        mytardis_see_sensitive=False,
        parent=test_datafile,
    )


@fixture
def test_mytardis_context_object(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
) -> MyTardisContextObject:
    return MyTardisContextObject(
        name=test_name,
        description=test_description,
        mt_identifiers=["test_mytardis_context_object"],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
    )


@fixture
def test_properties_with_Context_obj(test_context_object) -> datetime:
    return {
        "quantity": 16,
        "units": "tons",
        "days": datetime(1, 1, 1, 0, 0).isoformat(),
        "soul": "IOU",
        "Context_obj": test_context_object,
        "left-right": ["iron", "steel"],
    }


@fixture
def test_license(test_url, test_name, test_description) -> License:
    return License(
        identifier=test_url, url=test_url, name=test_name, description=test_description
    )


@fixture
def test_project(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    test_person,
    test_organization,
    test_user,
) -> Project:
    return Project(
        name="Project_name",
        description=test_description,
        mt_identifiers=["Project", "Project_name"],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
        principal_investigator=test_person,
        contributors=[test_person],
        institution=test_organization,
        created_by=test_user,
    )


@fixture
def test_experiment(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    test_project,
    test_person,
    test_user,
    test_license,
) -> Experiment:
    return Experiment(
        name="experiment_name",
        description=test_description,
        mt_identifiers=["experiment"],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
        contributors=[test_person],
        mytardis_classification=None,
        projects=[test_project],
        created_by=test_user,
        sd_license=test_license,
    )


@fixture
def test_dataset(
    test_experiment,
    test_directory,
    test_instrument,
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    test_person,
) -> Dataset:
    return Dataset(
        name="test_dataset",
        description=test_description,
        mt_identifiers=None,
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
        contributors=[test_person],
        experiments=[test_experiment],
        directory=test_directory,
        instrument=test_instrument,
    )


@fixture
def test_datafile(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    test_person,
    test_filepath,
    test_dataset,
) -> Datafile:
    return Datafile(
        name="test_datafile",
        description=test_description,
        mt_identifiers=[test_filepath],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
        filepath=test_filepath,
        dataset=test_dataset,
    )


@fixture
def test_manifest(
    test_project,
    test_experiment,
    test_dataset,
    test_datafile,
    test_sensitive_metadata,
    test_mytardis_metadata,
    test_person_ACL,
    test_org_ACL,
):
    return CrateManifest(
        projects={test_project.id: test_project},
        experiments={test_experiment.id: test_experiment},
        datafiles=[test_datafile],
        datasets={test_dataset.id: test_dataset},
        metadata=[test_mytardis_metadata, test_sensitive_metadata],
        acls=[test_person_ACL, test_org_ACL],
    )


@fixture
def test_rocrate_person(
    test_person_name,
    test_email,
    test_organization,
    crate: ROCrate,
    test_person: Person,
    test_upi: str,
) -> ROPerson:
    return ROPerson(
        crate=ROCrate,
        identifier=test_upi,
        properties={
            "affiliation": [{"@id": "#" + test_organization.id}],
            "name": test_person_name,
            "email": test_email,
        },
    )


@fixture
def test_rocrate_metadata(
    test_name: str,
    test_metadata_value: str,
    test_metadata_type: str,
    crate: ROCrate,
    test_datafile: Datafile,
    test_mytardis_metadata: MTMetadata,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        test_mytardis_metadata.id,
        properties={
            "@type": MT_METADATA_SCHEMATYPE,
            "name": test_name,
            "value": test_metadata_value,
            "myTardis-type": test_metadata_type,
            "sensitive": False,
            "mytardis-schema": "http://rocrate.testing/project/1/schema",
            "parents": [{"@id": test_datafile.roc_id}],
        },
    )


@fixture
def test_rocrate_sensitive_metadata(
    test_name: str,
    test_metadata_value: str,
    test_metadata_type: str,
    crate: ROCrate,
    test_datafile: Datafile,
    test_sensitive_metadata: MTMetadata,
    test_gpg_key: GenKey,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        test_sensitive_metadata.id,
        properties={
            "@type": MT_METADATA_SCHEMATYPE,
            "name": test_name + "sensitive",
            "value": test_metadata_value,
            "ToBeEncrypted": True,
            "myTardis-type": test_metadata_type,
            "sensitive": True,
            "mytardis-schema": "http://rocrate.testing/project/1/schema",
            "parents": [{"@id": test_datafile.roc_id}],
        },
    )


@fixture
def ro_date(test_datatime):
    return serialize_optional_date(test_datatime)


@fixture
def test_rocrate_context_entity(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    crate: ROCrate,
    ro_date,
    test_context_object,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        test_context_object.id,
        properties={
            "@type": test_schema_type,
            "mt_identifiers": ["test_context_object"],
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "additional_properties": test_extra_properties,
            "name": test_name,
        },
    )


@fixture
def test_crate_ACL(
    test_group,
    test_ogranization_type,
    test_description,
    test_datatime,
    test_extra_properties_output,
    crate: ROCrate,
    ro_date,
    test_org_ACL,
    test_datafile,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        test_org_ACL.id,
        properties={
            "@type": "DigitalDocumentPermission",
            "grantee": [{"@id": "#" + test_group.id}],
            "grantee_type": "Audiance",
            "permission_type": "ReadPermission",
            "mytardis_owner": True,
            "my_tardis_can_download": True,
            "mytardis_see_sensitive": False,
            "subjectOf": [{"@id": test_datafile.roc_id}],
        },
    )


@fixture
def test_crate_user_ACL(
    test_user,
    test_ogranization_type,
    test_description,
    test_datatime,
    test_extra_properties_output,
    crate: ROCrate,
    ro_date,
    test_person_ACL,
    test_datafile,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        test_person_ACL.id,
        properties={
            "@type": "DigitalDocumentPermission",
            "grantee": [{"@id": "#" + test_user.id}],
            "grantee_type": "Person",
            "permission_type": "ReadPermission",
            "mytardis_owner": False,
            "my_tardis_can_download": False,
            "mytardis_see_sensitive": False,
            "subjectOf": [{"@id": test_datafile.roc_id}],
        },
    )


@fixture
def test_ro_crate_project(
    test_description,
    test_extra_properties_output,
    test_person,
    ro_date,
    crate,
    test_project,
    test_organization,
    test_upi,
    test_user,
) -> None:
    return ROContextEntity(
        crate,
        test_project.id,
        properties={
            "@type": "Project",
            "name": "Project_name",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "mt_identifiers": ["Project", "Project_name"],
            "principal_investigator": [{"@id": "#" + test_upi}],
            "contributors": [{"@id": "#" + test_upi}],
            "mytardis_classification": "DataClassification.SENSITIVE",
            "createdBy": [{"@id": "#" + test_user.id}],
            "parentOrganization": [{"@id": "#" + test_organization.id}],
        }
        | test_extra_properties_output,
    )


@fixture
def test_ro_crate_experiment(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties_output,
    test_person,
    test_ethics_policy,
    ro_date,
    crate,
    test_ro_crate_project,
    test_experiment,
    test_user,
    test_license,
) -> None:
    return ROContextEntity(
        crate,
        test_experiment.id,
        properties={
            "project": [{"@id": test_ro_crate_project.id}],
            "@type": "DataCatalog",
            "name": "experiment_name",
            "mt_identifiers": ["experiment"],
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "approved": False,
            "createdBy": [{"@id": "#" + test_user.id}],
            "sdLicense": [{"@id": test_license.id}],
        }
        | test_extra_properties_output,
    )


@fixture
def test_ro_crate_dataset(
    test_name,
    test_directory,
    test_description,
    test_datatime,
    test_extra_properties_output,
    test_person,
    test_ethics_policy,
    ro_date,
    crate,
    test_instrument,
    test_ro_crate_experiment,
) -> RODataset:
    return RODataset(
        crate,
        source=Path(test_directory),
        dest_path=Path(test_directory),
        fetch_remote=False,
        validate_url=False,
        properties={
            "includedInDataCatalog": [{"@id": test_ro_crate_experiment.id}],
            "@type": "Dataset",
            "name": "test_dataset",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "instrument": [{"@id": "#" + str(test_instrument.id)}],
            "mytardis_classification": "DataClassification.SENSITIVE",
        }
        | test_extra_properties_output,
    )


@fixture
def test_rocrate_datafile(
    crate: ROCrate,
    test_filepath: Path,
    test_description: str,
    test_directory: str,
    ro_date: datetime,
    test_dataset: Dataset,
    test_extra_properties_output: Dict[str, Any],
) -> RODataFile:
    source_and_dest = Path(test_directory) / Path(test_filepath)
    return RODataFile(
        crate=crate,
        source=source_and_dest.as_posix(),
        dest_path=source_and_dest.as_posix(),
        fetch_remote=False,
        validate_url=False,
        properties={
            "@type": "File",
            "name": "test_datafile",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "mt_identifiers": [test_filepath.as_posix()],
            "dataset": [{"@id": test_dataset.roc_id}],
            "datafileVersion": 1,
            "mytardis_classification": "DataClassification.SENSITIVE",
        }
        | test_extra_properties_output,
    )


@fixture
def test_rocrate_written_datafile(
    test_rocrate_datafile: RODataFile,
    test_sensitive_metadata: MTMetadata,
    test_mytardis_metadata: MTMetadata,
    test_org_ACL: ACL,
    test_person_ACL: ACL,
) -> RODataFile:
    written_datafile = copy.deepcopy(test_rocrate_datafile)
    written_datafile.append_to(
        "metadata",
        [
            {"@id": test_mytardis_metadata.roc_id},
            {"@id": test_sensitive_metadata.roc_id},
        ],
    )
    written_datafile.append_to(
        "hasDigitalDocumentPermission",
        [{"@id": test_person_ACL.roc_id}, {"@id": test_org_ACL.roc_id}],
    )
    return written_datafile


@fixture
def test_rocrate_written_dataset(
    test_ro_crate_dataset, test_rocrate_written_datafile
) -> RODataset:
    written_dataset = copy.deepcopy(test_ro_crate_dataset)
    written_dataset.append_to("hasPart", test_rocrate_written_datafile)
    return written_dataset


@fixture
def manifest_ro_contents(
    test_rocrate_written_datafile,
    test_rocrate_written_dataset,
    test_ro_crate_experiment,
    test_ro_crate_project,
    test_rocrate_metadata,
    test_rocrate_person,
):
    return [
        test_rocrate_written_datafile,
        test_rocrate_written_dataset,
        test_ro_crate_experiment,
        test_ro_crate_project,
        test_rocrate_metadata,
        test_rocrate_person,
    ]


@fixture
def tmpdir(tmpdir):
    return Path(tmpdir)


@fixture
def data_dir(tmpdir):
    d = tmpdir / (TEST_DATA_NAME + "input")
    shutil.copytree(THIS_DIR / TEST_DATA_NAME, d)
    return d


class RO_CRATE_Helpers:  # taken from ro-crate.py's conftest helpers

    BASE_URL = "https://w3id.org/ro/crate"
    VERSION = "1.1"
    LEGACY_VERSION = "1.0"

    PROFILE = f"{BASE_URL}/{VERSION}"
    LEGACY_PROFILE = f"{BASE_URL}/{LEGACY_VERSION}"
    METADATA_FILE_NAME = "ro-crate-metadata.json"
    LEGACY_METADATA_FILE_NAME = "ro-crate-metadata.jsonld"

    @classmethod
    def read_json_entities(cls, crate_base_path):
        metadata_path = Path(crate_base_path) / cls.METADATA_FILE_NAME
        with open(metadata_path, "rt") as f:
            json_data = json.load(f)
        return {_["@id"]: _ for _ in json_data["@graph"]}

    @classmethod
    def check_crate(cls, json_entities, root_id="./", data_entity_ids=None):
        assert root_id in json_entities
        root = json_entities[root_id]
        assert root["@type"] == "Dataset"
        assert cls.METADATA_FILE_NAME in json_entities
        metadata = json_entities[cls.METADATA_FILE_NAME]
        assert metadata["@type"] == "CreativeWork"
        assert cls.PROFILE in get_norm_value(metadata, "conformsTo")
        assert metadata["about"] == {"@id": root_id}
        if data_entity_ids:
            data_entity_ids = set(data_entity_ids)
            assert data_entity_ids.issubset(json_entities)
            assert "hasPart" in root
            assert data_entity_ids.issubset([_["@id"] for _ in root["hasPart"]])

    @classmethod
    def check_crate_contains(cls, json_entities, ro_crate_entites: List[RO_Entity]):
        for entity in ro_crate_entites:
            assert json_entities[entity.id] is not None
            assert json_entities[entity.id] == entity.as_jsonld()


@fixture
def ro_crate_helpers():
    return RO_CRATE_Helpers
