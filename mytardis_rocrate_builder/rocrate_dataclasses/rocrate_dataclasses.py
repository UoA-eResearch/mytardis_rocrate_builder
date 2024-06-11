"""Definition of RO-Crate dataclasses"""

import uuid
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import AfterValidator, Field, PlainSerializer, WithJsonSchema
from slugify import slugify
from validators import url

from .. import MYTARDIS_NAMESPACE_UUID

MT_METADATA_TYPE = {
    1: "NUMERIC",
    2: "STRING",
    3: "URL",
    4: "LINK",
    5: "FILENAME",
    6: "DATETIME",
    7: "LONGSTRING",
    8: "JSON",
    "default": "STRING",
}


class DataClassification(Enum):
    """An enumerator for data classification.

    Gaps have been left deliberately in the enumeration to allow for intermediate
    classifications of data that may arise. The larger the integer that the classification
    resolves to, the less sensitive the data is.
    """

    RESTRICTED = 1
    SENSITIVE = 25
    INTERNAL = 50
    PUBLIC = 100


def validate_url(value: Any) -> str:
    """Custom validator for Urls since the default pydantic ones are not compatible
    with urllib"""
    if not isinstance(value, str):
        raise TypeError(f'Unexpected type for URL: "{type(value)}"')
    if url(value):
        return value
    raise ValueError(f'Passed string value"{value}" is not a valid URL')


Url = Annotated[
    str,
    AfterValidator(validate_url),
    PlainSerializer(str, return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


@dataclass(kw_only=True)
class Organisation:
    """Dataclass to hold the details of an organisation for RO-Crate

    Attr:
        mt_identifiers (List[str]): A list of mt_identifiers that can be used to uniquely
            identify the organisation - typically RoR
        name (str): The name of the organisation
        url (str): An optional URL for the organisation - default None
        research_org (bool): is this orgranization a research organization
    """

    mt_identifiers: List[str]
    name: str
    location: Optional[str] = None
    url: Optional[Url] = None
    research_org: bool = True

    def __post_init__(self) -> None:
        self.identifier = gen_uuid_id(MYTARDIS_NAMESPACE_UUID, self.mt_identifiers)

    @property
    def id(self) -> str | int | float:
        """Retrieve  uuid base on org name to act as RO-Crate ID"""
        return self.identifier


@dataclass(kw_only=True)
class Person:
    """Dataclass to hold the details of a person for RO-Crate

    Attr:
        identifier (List[str]): An optional list of unique mt_identifiers for the person
            - Must contain UPI for import into MyTardis
            - typically ORCID - default None
        name : the name of the person object in MyTardis (usually UPI)
        full_name (str): The full name (first name/last name) of the person
        email (str): A contact email address for the person named
        affilitation (Organisation): An organisation that is the primary affiliation for
            the person
        schema_type (str): the schema.org type of this entity
        full name: the first and last name of the person
    """

    identifier: str | int | float = Field(init=False, frozen=True)
    name: str
    email: str
    mt_identifiers: List[str]
    affiliation: Organisation
    schema_type: str = "Person"
    full_name: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "identifier", gen_uuid_id(MYTARDIS_NAMESPACE_UUID, self.name)
        )

    @property
    def id(self) -> str | int | float:
        """Retrieve name (usually upi) RO-Crate ID"""
        return self.identifier


@dataclass(kw_only=True)
class Group:
    """Dataclass to hold the details of a group for RO-Crate

    Attr:
        name (str): The group name of the group
    """

    identifier: str | int | float = Field(init=False, frozen=True)
    name: str
    schema_type: str = "Audience"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "identifier", gen_uuid_id(MYTARDIS_NAMESPACE_UUID, (self.name))
        )

    @property
    def id(self) -> str | int | float:
        """Return the group name as the RO-Crate ID"""
        return self.identifier


@dataclass(kw_only=True)
class BaseObject(ABC):
    """Abstract Most basic object that can be turned into an RO-Crate entity

    Attr:
        identifier (str): The identifier that will be used in the RO-Crate
            Assigned based on UUID generation
    """

    identifier: str | int | float = Field(init=False, frozen=True)

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", str(uuid.uuid4()))

    @property
    def id(self) -> str | int | float:
        """syntatic sugar for id used in RO-Crate"""
        return self.identifier


@dataclass(kw_only=True)
class ContextObject(BaseObject):  # pylint: disable=too-many-instance-attributes
    """Abstract dataclass for an object for RO-Crate

    Attr:
        name (str): The name of the object
        description (str): A longer form description of the object
        mt_identifiers (List[str]):
            A list of mt_identifiers for the object
        date_created (Optional[datetime]) : when was the object created
        date_modified (Optional[List[datetime]]) : when was the object last changed
        additional_properties Optional[Dict[str, Any]] : metadata not in schema
        schema_type (Optional[str | list[str]]) :Schema.org types or type
            Assigned based on dataclass
    """

    name: str
    description: str
    mt_identifiers: List[str | int | float]
    date_created: Optional[datetime] = None
    date_modified: Optional[List[datetime]] = None
    additional_properties: Optional[Dict[str, Any]] = None
    schema_type: Optional[str | list[str]] = Field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", gen_uuid_id(self.name))
        self.schema_type = "Thing"


@dataclass(kw_only=True)
class Instrument(ContextObject):
    """Dataclass for Instruments to be assoicated with MyTardis Datasets"""

    location: str
    schema_type = ["Instrument", "Thing"]


@dataclass(kw_only=True)
class MyTardisContextObject(ContextObject):
    """Context objects containing MyTardis specific properties.
    These properties are not used by other RO-Crate endpoints.

    Attr:
        mytardis_classification (DataClassification): the classification in MyTardis
            Default = Sensitive

    """

    mytardis_classification: Optional[DataClassification] = (
        DataClassification.SENSITIVE
    )  # NOT IN SCHEMA.ORG

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "identifier", gen_uuid_id(MYTARDIS_NAMESPACE_UUID, (self.name))
        )


@dataclass(kw_only=True)
class Project(MyTardisContextObject):
    """Concrete Project class for RO-Crate - inherits from ContextObject
    https://schema.org/Project

    Attr:
        principal_investigator (Person): The project lead
        contributors (List[Person]): A list of people associated with the project who are not
            the principal investigator
    """

    principal_investigator: Person  # NOT IN SCHEMA.ORG
    contributors: Optional[List[Person]] = None

    def __post_init__(self) -> None:
        self.schema_type = "Project"
        object.__setattr__(
            self,
            "identifier",
            gen_uuid_id(MYTARDIS_NAMESPACE_UUID, (generate_pedd_name(self))),
        )


@dataclass(kw_only=True)
class Experiment(MyTardisContextObject):
    """Concrete Experiment/Data-Catalog class for RO-Crate - inherits from yTardisContextObject
    https://schema.org/DataCatalog
    Attr:
        projects (List[Project]): the projects linked with this experiment
        contributors (List[Person]): A list of people associated with this experiment
    """

    projects: List[Project]  # NOT IN SCHEMA.ORG
    contributors: Optional[List[Person]] = None

    def __post_init__(self) -> None:
        self.schema_type = "DataCatalog"
        object.__setattr__(
            self,
            "identifier",
            gen_uuid_id(MYTARDIS_NAMESPACE_UUID, (generate_pedd_name(self))),
        )


@dataclass(kw_only=True)
class Dataset(MyTardisContextObject):
    """Concrete Dataset class for RO-crate - inherits from MyTardisContextObject
    Attr:
    experiments (List[Experiment]): the experiments linked with this dataset
    directory (Path): the local path of the directory of this dataset
    instrument (Instrument): the instrument associated with this dataset
    contributors (List[Person]): A list of people associated with this dataset
    """

    experiments: List[Experiment]
    directory: Path
    instrument: Instrument
    contributors: Optional[List[Person]] = None

    def __post_init__(self) -> None:
        self.schema_type = "Dataset"
        object.__setattr__(self, "identifier", self.directory.as_posix())


@dataclass(kw_only=True)
class Datafile(MyTardisContextObject):
    """Concrete datafile class for RO-crate - inherits from MyTaridsContextObject
    Attr:
    filepath (str): the relative path to this file
    dataset (Dataset): the Dataset parent of this datafile
    version (int): the version number of this file
    storage_box (Optional[URL]): The MyTardis storage box this file resides in
    """

    filepath: Path
    dataset: Dataset
    version: int = 1
    storage_box: Optional[Url] = None

    def __post_init__(self) -> None:
        self.schema_type = ["File", "MediaObject"]
        object.__setattr__(self, "identifier", self.filepath.as_posix())

    def update_to_root(self, dataset: Dataset) -> Path:
        """Update a datafile that is a child of a dataset so that dataset is now the root

        Args:
            dataset (Dataset): the dataset that is being updated to be root
        """
        self.dataset = dataset
        try:
            new_filepath = self.filepath.relative_to(dataset.directory)
        except ValueError:
            new_filepath = self.filepath
        self.filepath = new_filepath
        object.__setattr__(self, "identifier", self.filepath.as_posix())
        return self.filepath


@dataclass(kw_only=True)
class ACL(BaseObject):  # pylint: disable=too-many-instance-attributes
    """Acess level controls in MyTardis provided to people and groups
    based on https://schema.org/DigitalDocumentPermission
    grantee - the user or group granted access

        Attr:
        name (str): A name given to this ACL (user defined)
        Grantee (Person | Group): Grantee the person or group this ACL belongs to
        parent (MyTardisContextObject): the object this ACL applies to
        mytardis_owner (bool): does this ACL grant ownership
        mytardis_can_download (bool): does this ACL grant download rights
        mytardis_see_sensitive (bool): does this ACL grant rigthts to see sensitive metadata

    """

    name: str
    grantee: Person | Group
    grantee_type: Literal["Audiance", "Person"]
    parent: MyTardisContextObject
    mytardis_owner: bool = False
    mytardis_can_download: bool = False
    mytardis_see_sensitive: bool = False

    def __post_init__(self) -> None:
        self.permission_type = "ReadPermission"
        self.schema_type = "DigitalDocumentPermission"
        self.identifier = gen_uuid_id(
            MYTARDIS_NAMESPACE_UUID, (generate_pedd_name(self.parent), self.name)
        )


@dataclass(kw_only=True)
class MTMetadata(BaseObject):
    """Concrete Metadata class for RO-crate
    Contains all information to store or recreate MyTardis metadata.
    Used as backup and recovery option.

    Attr:
        name (str): what is the name of this metadata in mytardis
        value (str): what is the value held in this metadata (As a string)
        mt_type (MT_METADATA_TYPE): what is the type of this data in MyTardis
        mt_schema (URL): what MyTardis schema is this metadata linked to
        sensitive (bool): is this data sensitive
            should it be written as encrypted
        parent (MyTardisContextObject): the object this Metadata is linked to
    """

    name: str
    value: str
    mt_type: Literal[
        "NUMERIC",
        "STRING",
        "URL",
        "LINK",
        "FILENAME",
        "DATETIME",
        "LONGSTRING",
        "JSON",
        "STRING",
    ]
    mt_schema: Url
    sensitive: bool
    parent: MyTardisContextObject

    def __post_init__(self) -> None:
        self.identifier = gen_uuid_id(
            MYTARDIS_NAMESPACE_UUID, (generate_pedd_name(self.parent), self.name)
        )


def gen_uuid_id(  #  type: ignore
    *args, namespace: uuid.UUID = MYTARDIS_NAMESPACE_UUID
) -> str:
    """Generate a UUID for a myTarids object
    Args:
        namespace (uuid.UUID, optional): the namespace UUID for the base of this UUID.
            Defaults to MYTARDIS_NAMESPACE_UUID.
        args* (*Any): a collection of other values to base the UUID on the strings of

    Raises:
        TypeError: if a non UUID value is passed to the namespace UUID

    Returns:
        str: a uuid5 based on all inputs and namespaces
    """
    if not isinstance(namespace, uuid.UUID):
        raise TypeError("Namespace needs to be a UUID object.")
    if not args:
        return str(namespace)
    uuid_str = slugify(" ".join(map(str, args)))
    uuid_obj = uuid.uuid5(namespace, uuid_str)
    return str(uuid_obj)


def generate_pedd_name(mytardis_object: MyTardisContextObject) -> str:
    """Generate the Project, Experiment, Dataset, Datafile unique name
    for my Tardis uuid assignment

    Args:
        parent (MyTardisContextObject): the parent obejct of the entity being assinged this UUID

    Returns:
        str: the PEDD name for uuid assignment
    """
    obj_name: str = ""
    match mytardis_object:
        case Project():
            obj_name = mytardis_object.name
        case Experiment():
            obj_name = mytardis_object.name
        case Dataset():
            obj_name = f"{mytardis_object.directory.as_posix()}-{mytardis_object.name}"
        case Datafile():
            obj_name = "".join(
                [
                    f"{mytardis_object.filepath.as_posix()}-",
                    f"{mytardis_object.dataset.directory.as_posix()}-",
                    f"{mytardis_object.dataset.name}-",
                    f"{mytardis_object.version}",
                ]
            )
        case _:
            obj_name = mytardis_object.name
    return slugify(obj_name)
