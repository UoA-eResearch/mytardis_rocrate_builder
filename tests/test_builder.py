from datetime import datetime
from pathlib import Path
from typing import List

from pytest import fixture
from rocrate.model.contextentity import ContextEntity as ROContextEntity
from rocrate.model.dataset import Dataset as RODataset
from rocrate.model.person import Person as ROPerson
from rocrate.rocrate import ROCrate

from mytardis_rocrate_builder.rocrate_builder import (MT_METADATA_SCHEMATYPE,
                                                      ROBuilder)
from mytardis_rocrate_builder.rocrate_dataclasses.rocrate_dataclasses import (
    ACL, MT_METADATA_TYPE, BaseObject, ContextObject, DataClassification,
    Datafile, Dataset, Experiment, Instrument, MTMetadata,
    MyTardisContextObject, Organisation, Person, Project)


@fixture
def test_rocrate_person(
    test_person_name, test_email, test_organization, crate: ROCrate
) -> ROPerson:
    return ROPerson(
        crate=ROCrate,
        identifier=test_person_name,
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
    test_metadata_id: str,
    crate: ROCrate,
):
    return ROContextEntity(
        crate,
        test_name,
        properties={
            "@type": MT_METADATA_SCHEMATYPE,
            "name": test_name,
            "value": test_metadata_value,
            "myTardis-type": test_metadata_type,
            "sensitive": False,
            "parents": ["./"],
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
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        "#test_context_object",
        properties={
            "@type": test_schema_type,
            "identifiers": ["test_context_object"],
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "additional_properties": test_extra_properties,
            "name": test_name,
        },
    )


@fixture
def test_crate_ACL(
    test_organization,
    test_ogranization_type,
    test_description,
    test_datatime,
    test_extra_properties,
    crate: ROCrate,
    ro_date,
) -> ROContextEntity:
    return ROContextEntity(
        crate,
        "test_ACL",
        properties={
            "@type": "DigitalDocumentPermission",
            "grantee": test_organization.id,
            "grantee_type": test_ogranization_type,
            "identifiers": ["test_ACL"],
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "additional_properties": test_extra_properties,
            "name": "test_ACL",
            "permission_type": "ReadPermission",
            "mytardis_owner": True,
            "mytardis_can_download": True,
            "mytardis_see_sensitive": False,
        },
    )


def test_add_metadata(builder, test_mytardis_metadata, test_rocrate_metadata):
    crate_metadata = builder._add_metadata_to_crate(
        test_mytardis_metadata, metadata_id=test_mytardis_metadata.name, parent_id="./"
    )
    assert crate_metadata == test_rocrate_metadata


def test_add_principal_investigator(
    builder: ROBuilder,
    test_person: Person,
    test_rocrate_person: ROPerson,
) -> None:
    assert builder.add_principal_investigator(test_person) == test_rocrate_person


def test_add_context_entity(
    builder: ROBuilder, test_context_object, test_rocrate_context_entity
):
    assert (
        builder.add_context_object(test_context_object).properties()
        == test_rocrate_context_entity.properties()
    )


def test_add_dates(builder: ROBuilder, test_datatime, ro_date):
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
):
    assert test_crate_ACL == builder.add_acl(test_org_ACL)


def test_adda_additional_properites(
    builder: ROBuilder,
    test_extra_properties,
    test_context_object,
    test_properties_with_Context_obj,
    test_rocrate_context_entity,
):
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
    test_acl_list,
    test_metadata_list,
    test_person,
    ro_date,
    crate,
):
    return ROContextEntity(
        crate,
        "Project",
        properties={
            "@type": "Project",
            "name": "Project_name",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "hasDigitalDocumentPermission": ["#" + acl.id for acl in test_acl_list],
            "metadata": [
                "_".join(["Project_" + metadata.name])
                for metadata in test_metadata_list.values()
            ],
            "principal_investigator": "#" + test_person.id,
            "contributors": ["#" + test_person.id],
        }
        | test_extra_properties,
    )


@fixture
def test_ro_crate_experiment(
    test_name,
    test_description,
    test_datatime,
    test_extra_properties,
    test_schema_type,
    test_acl_list,
    test_metadata_list,
    test_person,
    test_ethics_policy,
    ro_date,
    crate,
    test_ro_crate_project,
):
    return ROContextEntity(
        crate,
        "experiment",
        properties={
            "project": [test_ro_crate_project.id],
            "@type": "DataCatalog",
            "name": "experiment_name",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "hasDigitalDocumentPermission": ["#" + acl.id for acl in test_acl_list],
            "metadata": [
                "_".join(["experiment_" + metadata.name])
                for metadata in test_metadata_list.values()
            ],
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
    test_schema_type,
    test_acl_list,
    test_metadata_list,
    test_person,
    test_ethics_policy,
    ro_date,
    crate,
    test_instrument,
    test_ro_crate_experiment,
):
    return RODataset(
        crate,
        source=Path(test_directory),
        dest_path=Path(test_directory),
        fetch_remote=False,
        validate_url=False,
        properties={
            "includedInDataCatalog": [test_ro_crate_experiment.id],
            "@type": "DataCatalog",
            "name": "experiment_name",
            "description": test_description,
            "dateCreated": ro_date,
            "dateModified": [ro_date],
            "datePublished": ro_date,
            "identifiers": [test_directory],
            "instrument": test_instrument.name,
            "hasDigitalDocumentPermission": ["#" + acl.id for acl in test_acl_list],
            "metadata": [
                "_".join([test_directory.as_posix() + metadata.name])
                for metadata in test_metadata_list.values()
            ],
        }
        | test_extra_properties,
    )


def test_add_project(builder, test_project, test_ro_crate_project):
    assert builder.add_project(test_project) == test_ro_crate_project


def test_add_experiment(builder, test_experiment, test_ro_crate_experiment):
    assert builder.add_experiment(test_experiment) == test_ro_crate_experiment


# def test_add_dataset(builder, test_dataset, test_ro_crate_dataset):
#     assert (
#         builder.add_dataset(test_dataset).properties()
#         == test_ro_crate_dataset.properties()
#     )


def test_add_datafile():
    assert True


# def test_add_project(
#     builder: ROBuilder,
#     test_rocrate_person: ROPerson,
#     test_project: Project,
# ) -> None:
#     assert builder.add_project(test_project) == ContextEntity(
#         builder.crate,
#         "test-project",
#         properties={
#             "@type": "Project",
#             "name": "Test Project",
#             "description": "A sample project for test purposes",
#             "principal_investigator": test_rocrate_person.id,
#             "contributors": [test_rocrate_person.id, test_rocrate_person.id],
#             "identifiers": ["test-raid", "another-id"],
#         },
#     )


# def test_add_experiment(
#     builder: ROBuilder,
#     test_experiment: Experiment,
#     test_rocrate_experiment: ContextEntity,
# ) -> None:
#     assert builder.add_experiment(test_experiment) == test_rocrate_experiment
