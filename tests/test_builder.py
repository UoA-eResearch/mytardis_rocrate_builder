# type: ignore
# pylint: disable
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from gnupg import GenKey
from hypothesis import assume, given
from hypothesis import strategies as st
from pytest import fixture, raises
from rocrate.encryption_utils import NoValidKeysError
from rocrate.model.contextentity import ContextEntity as ROContextEntity
from rocrate.model.dataset import Dataset as RODataset
from rocrate.model.file import File as RODataFile
from rocrate.model.person import Person as ROPerson
from rocrate.rocrate import ROCrate

from mytardis_rocrate_builder.rocrate_builder import (
    MT_METADATA_SCHEMATYPE,
    ROBuilder,
    serialize_optional_date,
)
from mytardis_rocrate_builder.rocrate_dataclasses.rocrate_dataclasses import (
    ACL,
    Datafile,
    Dataset,
    MTMetadata,
    Person,
    Project,
    User,
    gen_uuid_id,
    generate_pedd_name,
)


def test_optional_add(
    builder: ROBuilder,
    test_project: Project,
    test_rocrate_context_entity: ROContextEntity,
):
    builder._add_optional_attr(
        test_rocrate_context_entity, "additional project", test_project
    )
    assert [
        {"@id": "#" + test_project.id}
    ] == test_rocrate_context_entity.properties().get("additional project")
    builder._add_optional_attr(test_rocrate_context_entity, "empty value", None)
    assert test_rocrate_context_entity.get("empty value") is None


def test_add_metadata(builder, test_mytardis_metadata, test_rocrate_metadata) -> None:
    crate_metadata = builder.add_metadata(test_mytardis_metadata)
    assert crate_metadata.properties() == test_rocrate_metadata.properties()


def test_add_sensitive_metadata(
    builder, test_sensitive_metadata, test_rocrate_sensitive_metadata
) -> None:
    crate_metadata = builder.add_metadata(test_sensitive_metadata)
    assert crate_metadata.get("recipients") is not None
    test_rocrate_sensitive_metadata.append_to(
        "recipients", crate_metadata.get("recipients")
    )
    assert crate_metadata.properties() == test_rocrate_sensitive_metadata.properties()


def test_no_recipents_failure(
    builder,
    test_sensitive_metadata: MTMetadata,
    test_rocrate_sensitive_metadata,
    test_user: User,
    test_second_user: User,
) -> None:
    with raises(NoValidKeysError):  # test recipients without keys
        test_user.pubkey_fingerprints = None
        test_second_user.pubkey_fingerprints = None
        builder.add_metadata(test_sensitive_metadata)
    with raises(NoValidKeysError):  # test recipients missing
        test_sensitive_metadata.recipients = None
        builder.add_metadata(test_sensitive_metadata)
    with raises(NoValidKeysError):  # test recipients empty
        test_sensitive_metadata.recipients = []
        builder.add_metadata(test_sensitive_metadata)


def test_add_principal_investigator(
    builder: ROBuilder,
    test_person: Person,
    test_rocrate_person: ROPerson,
) -> None:
    assert (
        builder.add_principal_investigator(test_person).properties()
        == test_rocrate_person.properties()
    )


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
    builder: ROBuilder,
    test_org_ACL: ACL,
    test_crate_ACL: ROContextEntity,
    test_person_ACL: ACL,
    test_user: User,
    test_crate_user_ACL: ROContextEntity,
) -> None:
    assert test_crate_ACL.properties() == builder.add_acl(test_org_ACL).properties()
    test_crate_ACL.properties()["grantee"] = [{"@id": "#" + test_user.id}]
    assert (
        test_crate_user_ACL.properties()
        == builder.add_acl(test_person_ACL).properties()
    )


def test_add_additional_properites(
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
    assert added_datafile.properties() == test_rocrate_datafile.properties()
