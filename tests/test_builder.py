# type: ignore
# pylint: disable
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pytest import fixture
from rocrate.model.contextentity import ContextEntity as ROContextEntity
from rocrate.model.dataset import Dataset as RODataset
from rocrate.model.file import File as RODataFile
from rocrate.model.person import Person as ROPerson
from rocrate.rocrate import ROCrate

from mytardis_rocrate_builder.rocrate_builder import MT_METADATA_SCHEMATYPE, ROBuilder
from mytardis_rocrate_builder.rocrate_dataclasses.rocrate_dataclasses import (
    ACL,
    Datafile,
    Dataset,
    MTMetadata,
    Person,
    gen_uuid_id,
    generate_pedd_name,
)


@fixture
def test_rocrate_person(
    test_person_name, test_email, test_organization, crate: ROCrate, test_person: Person
) -> ROPerson:
    return ROPerson(
        crate=ROCrate,
        identifier=test_person.id,
        properties={
            "affiliation": test_organization.id,
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
            "parents": [test_datafile.id],
        },
    )


@fixture
def ro_date(test_datatime):
    return test_datatime.isoformat()


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
    test_extra_properties,
    crate: ROCrate,
    ro_date,
    test_org_ACL,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        test_org_ACL.id,
        properties={
            "@type": "DigitalDocumentPermission",
            "grantee": test_group.id,
            "grantee_type": "Audiance",
            "permission_type": "ReadPermission",
            "mytardis_owner": True,
            "my_tardis_can_download": True,
            "mytardis_see_sensitive": False,
            "subjectOf": ["data/testfile.txt"],
        },
    )


def test_add_metadata(builder, test_mytardis_metadata, test_rocrate_metadata) -> None:
    crate_metadata = builder._add_metadata_to_crate(test_mytardis_metadata)
    assert crate_metadata.properties() == test_rocrate_metadata.properties()


def test_add_principal_investigator(
    builder: ROBuilder,
    test_person: Person,
    test_rocrate_person: ROPerson,
) -> None:
    assert builder.add_principal_investigator(test_person) == test_rocrate_person


def test_add_context_entity(
    builder: ROBuilder, test_context_object, test_rocrate_context_entity
) -> None:
    assert (
        builder.add_context_object(test_context_object).properties()
        == test_rocrate_context_entity.properties()
    )


def test_add_dates(builder: ROBuilder, test_datatime, ro_date) -> None:
    properties = {}
    assert builder._add_dates(properties, test_datatime, [test_datatime]) == {
        "dateCreated": ro_date,
        "dateModified": [ro_date],
        "datePublished": ro_date,
    }


def test_add_contributors(
    builder: ROBuilder,
    test_person: Person,
    test_rocrate_person: ROPerson,
) -> None:
    assert builder.add_contributors([test_person, test_person]) == [
        test_rocrate_person,
        test_rocrate_person,
    ]


def test_add_acl(
    builder: ROBuilder, test_org_ACL: ACL, test_crate_ACL: ROContextEntity
) -> None:
    assert test_crate_ACL.properties() == builder.add_acl(test_org_ACL).properties()


def test_adda_additional_properites(
    builder: ROBuilder,
    test_extra_properties,
    test_context_object,
    test_properties_with_Context_obj,
    test_rocrate_context_entity,
) -> None:
    properties = {}
    assert (
        builder._add_additional_properties(properties, test_extra_properties)
        == test_extra_properties
    )
    properties = {}
    test_extra_properties["Context_obj"] = "#" + test_context_object.id
    assert (
        builder._add_additional_properties(properties, test_properties_with_Context_obj)
        == test_extra_properties
    )
    assert (
        builder.crate.dereference("#" + test_context_object.id)
        == test_rocrate_context_entity
    )


@fixture
def test_ro_crate_project(
    test_description,
    test_extra_properties,
    test_person,
    ro_date,
    crate,
    test_project,
    test_organization,
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
            "mt_identifiers": ["Project"],
            "principal_investigator": "#" + test_person.id,
            "contributors": ["#" + test_person.id],
            "mytardis_classification": "DataClassification.SENSITIVE",
        }
        | test_extra_properties,
    )


@fixture
def test_ro_crate_experiment(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_person,
    test_ethics_policy,
    ro_date,
    crate,
    test_ro_crate_project,
    test_experiment,
) -> None:
    return ROContextEntity(
        crate,
        test_experiment.id,
        properties={
            "project": [test_ro_crate_project.id],
            "@type": "DataCatalog",
            "name": "experiment_name",
            "mt_identifiers": ["experiment"],
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "approved": False,
        }
        | test_extra_properties,
    )


@fixture
def test_ro_crate_dataset(
    test_name,
    test_directory,
    test_description,
    test_datatime,
    test_extra_properties,
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
            "includedInDataCatalog": [test_ro_crate_experiment.id],
            "@type": "Dataset",
            "name": "test_dataset",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "mt_identifiers": [test_directory.as_posix()],
            "instrument": "#" + test_instrument.id,
            "mytardis_classification": "DataClassification.SENSITIVE",
        }
        | test_extra_properties,
    )


@fixture
def test_rocrate_datafile(
    crate: ROCrate,
    test_filepath: Path,
    test_description: str,
    test_directory: str,
    ro_date: datetime,
    test_dataset: Dataset,
    test_extra_properties: Dict[str, Any],
) -> RODataFile:
    return RODataFile(
        crate=crate,
        source=Path(test_filepath),
        dest_path=Path(test_filepath),
        fetch_remote=False,
        validate_url=False,
        properties={
            "@type": "File",
            "name": "test_datafile",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "mt_identifiers": [test_filepath],
            "dataset": crate.root_dataset.id,
            "version": 1.0,
            "mytardis_classification": "DataClassification.SENSITIVE",
        }
        | test_extra_properties,
    )


def test_add_project(builder: ROBuilder, test_project, test_ro_crate_project):
    added_project = builder.add_project(test_project)
    assert added_project.properties() == test_ro_crate_project.properties()


def test_add_experiment(
    builder: ROBuilder, test_experiment, test_ro_crate_experiment
) -> None:
    added_experiment = builder.add_experiment(test_experiment)
    assert added_experiment.properties() == test_ro_crate_experiment.properties()


def test_add_dataset(builder: ROBuilder, test_dataset, test_ro_crate_dataset) -> None:
    added_dataset = builder.add_dataset(test_dataset)
    assert added_dataset.properties() == test_ro_crate_dataset.properties()


def test_add_datafile(
    builder: ROBuilder, test_datafile: Datafile, test_rocrate_datafile: RODataFile
) -> None:
    added_datafile = builder.add_datafile(test_datafile)
    assert added_datafile == test_rocrate_datafile
