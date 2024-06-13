# pylint: disable
#  type: ignore
# pylint: disable
# test building a functional crate out of components
from datetime import datetime
from pathlib import Path

from pytest import fixture
from rocrate.rocrate import ROCrate

from mytardis_rocrate_builder.rocrate_builder import ROBuilder
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
    MTMetadata,
    MyTardisContextObject,
    Organisation,
    Person,
    Project,
)


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
def test_extra_properties() -> datetime:
    return {
        "quantity": 16,
        "units": "tons",
        "days": datetime(1, 1, 1, 0, 0),
        "soul": "IOU",
    }


@fixture
def test_schema_type() -> str:
    return "Thing"


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
    return Path("data/")


@fixture
def test_filepath() -> Path:
    return Path("data/testfile.txt")


@fixture(name="crate")
def fixture_crate() -> ROCrate:
    return ROCrate()


@fixture(name="builder")
def fixture_builder(crate: ROCrate) -> ROBuilder:
    return ROBuilder(crate)


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
    test_person_name: str, test_email: str, test_organization: Organisation
):
    return Person(
        name=test_person_name,
        email=test_email,
        affiliation=test_organization,
        mt_identifiers=[test_person_name],
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
    )


@fixture
def test_sensitive_metadata(
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
        sensitive=True,
        parent=test_datafile,
        mt_schema=test_metadata_schema,
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
    test_datatime,
    test_extra_properties,
    test_group,
    test_datafile,
) -> ACL:
    return ACL(
        name="test_acl",
        grantee=test_group,
        grantee_type="Audiance",
        mytardis_owner=True,
        mytardis_can_download=True,
        mytardis_see_sensitive=False,
        parent=test_datafile,
    )


@fixture
def test_person_ACL(
    test_person,
    test_person_type,
    test_description,
    test_datatime,
    test_extra_properties,
) -> ACL:
    return ACL(
        name="test_acl",
        grantee=test_person,
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
        "days": datetime(1, 1, 1, 0, 0),
        "soul": "IOU",
        "Context_obj": test_context_object,
    }


@fixture
def test_project(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    test_person,
) -> Project:
    return Project(
        name="Project_name",
        description=test_description,
        mt_identifiers=["Project"],
        date_created=test_datatime,
        date_modified=[test_datatime],
        additional_properties=test_extra_properties,
        principal_investigator=test_person,
        contributors=[test_person],
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
        mt_identifiers=[test_directory.as_posix()],
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
