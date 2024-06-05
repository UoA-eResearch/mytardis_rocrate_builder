"""Definition of RO-Crate dataclasses"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import AfterValidator, PlainSerializer, WithJsonSchema
from validators import url

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
        identifier (List[str]): A list of mt_identifiers that can be used to uniquely
            identify the organisation - typically RoR
        name (str): The name of the organisation
        url (str): An optional URL for the organisation - default None
    """

    mt_identifiers: List[str]
    name: str
    location: Optional[str] = None
    url: Optional[Url] = None
    research_org: bool = True

    @property
    def id(self) -> str | int | float:
        """Retrieve first ID to act as RO-Crate ID"""
        return self.mt_identifiers[0]


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
    """

    name: str
    email: str
    mt_identifiers: List[str]
    affiliation: Organisation
    schema_type: str = "Person"
    full_name: Optional[str] = None

    @property
    def id(self) -> str | int | float:
        """Retrieve name (usually upi) RO-Crate ID"""
        return self.name


@dataclass(kw_only=True)
class Group:
    """Dataclass to hold the details of a group for RO-Crate

    Attr:
        name (str): The group name of the group
    """

    name: str
    schema_type: str = "Audience"

    @property
    def id(self) -> str:
        """Return the group name as the RO-Crate ID"""
        return self.name


@dataclass(kw_only=True)
class BaseObject(ABC):
    """Abstract Most basic object that can be turned into an RO-Crate entity"""

    identifier: str | int | float

    @property
    def id(self) -> str | int | float:
        """syntatic sugar for id used in RO-Crate"""
        return self.identifier


@dataclass(kw_only=True)
class MTMetadata(BaseObject):
    """Concrete Metadata class for RO-crate
    Contains all information to store or recreate MyTardis metadata.
    Used as backup and recovery option.

    creates an RO-Crate JSON-LD entity matching this schema
    "@id": string - unique ID in the RO-Crate,
    "@type": string = "MyTardis-Metadata_field" - RO-Crate type,
    "name": string - name of the metadata in MyTardis,
    "value": string | Any - Metadata value in my tardis,
    "mt-type": string - Metadata type as recorded in MyTardis,
    "mt-schema": url - the object schema in MyTardis that applies to this metadata record
    "sensitive": bool - Metadata ,
    "parents": List[string] - list of ids for all the parents

    Attr:
        experiment (str): An identifier for an experiment
    """

    name: str
    value: str
    mt_type: str
    mt_schema: Url
    sensitive: bool
    parents: List[str] | None


@dataclass(kw_only=True)
class ContextObject(BaseObject):
    """Abstract dataclass for an object for RO-Crate

    Attr:
        name (str): The name of the object
        description (str): A longer form description of the object
        mt_identifiers (List[str]):
            A list of mt_identifiers for the object
            the first of which will be used as a UUID in the RO-Crate
        date_created (Optional[datetime]) : when was the object created
        date_modified (Optional[List[datetime]]) : when was the object last changed
        metadata (Optional[Dict[str, MTMetadata]])  a list of the mytardis metadata elements
        additional_properties Optional[Dict[str, Any]] : metadata not in schema
        schema_type (Optional[str | list[str]]) :Schema.org types or type
    """

    name: str
    description: str
    mt_identifiers: List[str | int | float]
    date_created: Optional[datetime] = None
    date_modified: Optional[List[datetime]] = None
    additional_properties: Optional[Dict[str, Any]] = None
    schema_type: Optional[str | list[str]] = None


@dataclass(kw_only=True)
class Instrument(ContextObject):
    """Dataclass for Instruments to be assoicated with MyTardis Datasets"""

    location: str
    schema_type = ["Instrument", "Thing"]
    metadata: Optional[Dict[str, MTMetadata]] = None


@dataclass(kw_only=True)
class ACL(BaseObject):
    """Acess level controls in MyTardis provided to people and groups
    based on https://schema.org/DigitalDocumentPermission
    grantee - the user or group granted access"""

    grantee: Person | Group
    grantee_type: Literal["Audiance", "Person"]
    mytardis_owner: bool = False
    mytardis_can_download: bool = False
    mytardis_see_sensitive: bool = False

    def __post_init__(self) -> None:
        self.permission_type = "ReadPermission"
        self.schema_type = "DigitalDocumentPermission"


@dataclass(kw_only=True)
class MyTardisContextObject(ContextObject):
    """Context objects containing MyTardis specific properties.
    These properties are not used by other RO-Crate endpoints.

    Attr:
        acls (List[ACL]): access level controls associated with the object
        metadata (Dict[str: MTMetadata]): MyTardis metadata
        associated with the object
    """

    acls: Optional[List[ACL]] = None
    metadata: Optional[Dict[str, MTMetadata]] = None


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
    schema_type: Optional[str] = None

    def __post_init__(self) -> None:
        self.schema_type = "Project"


@dataclass(kw_only=True)
class Experiment(MyTardisContextObject):
    """Concrete Experiment/Data-Catalog class for RO-Crate - inherits from ContextObject
    https://schema.org/DataCatalog
    Attr:
        project (str): An identifier for a project
    """

    projects: List[Project]  # NOT IN SCHEMA.ORG
    contributors: Optional[List[Person]] = None
    mytardis_classification: Optional[DataClassification] = None  # NOT IN SCHEMA.ORG
    schema_type: Optional[str] = None

    def __post_init__(self) -> None:
        self.schema_type = "DataCatalog"


@dataclass(kw_only=True)
class Dataset(MyTardisContextObject):
    """Concrete Dataset class for RO-crate - inherits from ContextObject

    Attr:
        experiment (str): An identifier for an experiment
    """

    experiments: List[Experiment]
    directory: Path
    instrument: Instrument
    contributors: Optional[List[Person]] = None
    schema_type: Optional[str] = None

    def __post_init__(self) -> None:
        self.schema_type = "Dataset"


@dataclass(kw_only=True)
class Datafile(MyTardisContextObject):
    """Concrete datafile class for RO-crate - inherits from ContextObject

    Attr:
        experiment (str): An identifier for an experiment
    """

    filepath: Path
    dataset: Dataset
    schema_type: Optional[str] = None
    storage_box: Optional[Url] = None

    def __post_init__(self) -> None:
        self.schema_type = "File"
        self.mt_identifiers: list[str | int | float] = [  # type: ignore
            self.filepath.as_posix()
        ] + self.mt_identifiers  # type: ignore

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
        return self.filepath
