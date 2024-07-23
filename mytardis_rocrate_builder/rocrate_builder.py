# pylint: disable=import-error, no-name-in-module
"""Builder class and functions for translating RO-Crate dataclasses into RO-Crate Entities
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gnupg import GPG
from rocrate.model.contextentity import ContextEntity
from rocrate.model.data_entity import DataEntity
from rocrate.model.encryptedcontextentity import EncryptedContextEntity
from rocrate.model.keyholder import Keyholder, PubkeyObject
from rocrate.model.person import Person as ROPerson
from rocrate.rocrate import ROCrate

from .rocrate_dataclasses.rocrate_dataclasses import (  # Group,
    ACL,
    ContextObject,
    Datafile,
    Dataset,
    Experiment,
    Facility,
    Group,
    Instrument,
    Lisence,
    MTMetadata,
    MyTardisContextObject,
    Organisation,
    Person,
    Project,
    User,
)

MT_METADATA_SCHEMATYPE = "my_tardis_metadata"
logger = logging.getLogger(__name__)

JsonProperties = Dict[str, str | List[str] | Dict[str, Any]]
IdentiferType = str | int | float


def serialize_optional_date(date: datetime | None) -> str | None:
    """Serialize a date to iso format, if it exists

    Args:
        date (datetime | None): the date to be serialized

    Returns:
        the date as an iso string or none
    """
    if date is None:
        return date
    return date.isoformat()


class ROBuilder:
    """A class to hold and add entries to an ROCrate

    Attr:
        crate (ROCrate): an RO-Crate to build or modifiy
        metadata_dict (Dict): a dictionary read in from a series of JSON files
    """

    def __init__(
        self, crate: ROCrate, flatten_additional_properties: bool = True
    ) -> None:
        """Initialisation of the ROBuilder

        Args:
            crate (ROCrate): an RO-Crate, either empty or reread in
            metadata_dict (Dict[str, str | List[str] | Dict[str,str]]): A dictionary of metadata
                relating to the entries to be added.
        """
        self.crate = crate
        self.flatten_additional_properties = flatten_additional_properties

    def _add_optional_attr(
        self, entity: ContextEntity, label: str, value: Any, compact: bool = False
    ) -> None:
        if value is None:
            return
        if isinstance(value, MyTardisContextObject):
            value_entity = self.crate.dereference(
                value.roc_id
            ) or self.add_my_tardis_obj(value)
            value = value_entity
        entity.append_to(label, value=value, compact=compact)

    def _add_acl_to_crate(self, acl: ACL) -> DataEntity:
        """Add an individual ACL to the RO-Crate

        Args:
            acl (ACL): the ACL to be added

        Returns:
            DataEntity: the RO-Crate context entity representing the ACL
        """

        identifier = acl.id
        properties = {
            "@type": acl.schema_type,
            "permission_type": acl.permission_type,
            "grantee_type": acl.grantee_type,
            "my_tardis_can_download": acl.mytardis_can_download,
            "mytardis_owner": acl.mytardis_owner,
            "mytardis_see_sensitive": acl.mytardis_see_sensitive,
        }
        return self.crate.add(
            ContextEntity(self.crate, identifier, properties=properties)
        )

    def add_acl(self, acl: ACL) -> ContextEntity | None:
        """Add an ACL to the RO-Crate.
         updating relationships between ACL and parents

        Args:
            acl (ACL): the ACL to be added

        Returns:
            ContextEntity | None: the ACL as a context entity
        """
        acl_entity = self.crate.dereference(acl.roc_id) or self._add_acl_to_crate(acl)
        parent_entitiy = self.crate.dereference(
            acl.parent.roc_id
        ) or self.add_my_tardis_obj(acl.parent)
        if grantee_entity := self.crate.dereference(acl.grantee.roc_id):
            pass
        else:
            match acl.grantee:
                case Group():
                    grantee_entity = self.add_group(acl.grantee)
                case Person():
                    grantee_entity = self.add_user(acl.grantee)
        grantee_entity.append_to("granteeOf", acl_entity)
        acl_entity.append_to("subjectOf", parent_entitiy)
        acl_entity.append_to("grantee", grantee_entity)
        parent_entitiy.append_to("hasDigitalDocumentPermission", acl_entity)
        return acl_entity

    def add_group(self, group: Group) -> ContextEntity:
        """Add a group to the crate

        Args:
            group (Group): the group dataclass to be added

        Returns:
            ContextEntity: the group as an RO-Crate context object
        """
        return ContextEntity(
            crate=self.crate,
            identifier=group.id,
            properties={
                "@type": group.schema_type,
                "name": group.name,
                "permissions": group.permissions,
            },
        )

    def __add_organisation(self, organisation: Organisation) -> ContextEntity:
        """Read in an Organisation object and create a Organization entity in the crate

        Args:
            organisation (Organisation): The Organisation to add
        """
        identifier = organisation.id
        org_type = "Organization"
        if organisation.research_org:
            org_type = "ResearchOrganization"
        org = ContextEntity(
            self.crate,
            identifier,
            properties={
                "@type": org_type,
                "name": organisation.name,
            },
        )
        self._add_optional_attr(org, "url", organisation.url)
        if len(organisation.mt_identifiers) > 1:
            for index, identifier in enumerate(organisation.mt_identifiers):
                if index != 0:
                    org.append_to("identifier", identifier)
        return self.crate.add(org)

    def __add_person_to_crate(self, person: Person) -> ROPerson:
        """Read in a Person object and create an entry for them in the crate.
        Without Active Directory auth this will just default to providing UPI


        Args:
            person (Person): the person to add to the crate
        """
        # orcid_regex = re.compile(
        #     r"https://orcid\.org/[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]{1}"
        # )
        upi_regex = re.compile(r"^[a-z]{2,4}[0-9]{3}$")
        person_id = person.id
        # # Check to see if any of the mt_identifiers are orcids - these are preferred
        # for identifier in person.mt_identifiers:
        #     if _ := orcid_regex.fullmatch(identifier):
        #         person_id = identifier
        # If no orcid is found check for UPIs
        if not upi_regex.fullmatch(str(person_id)):
            for identifier in person.mt_identifiers:
                if _ := upi_regex.fullmatch(identifier):
                    person_id = identifier
        # Finally, if no orcid or UPI is found, use the first identifier
        # if not person_id:
        #     person_id = person.mt_identifiers[0]

        person_obj = ROPerson(
            self.crate,
            person.id,
            properties={"name": person.name, "email": person.email},
        )

        if not any(
            (
                entity.type in ["Organization", "ResearchOrganization"]
                and entity.id == person.affiliation.id
            )
            for entity in self.crate.get_entities()
        ):
            person_obj.append_to(
                "affiliation", self.__add_organisation(person.affiliation)
            )
        if len(person.mt_identifiers) > 1:
            for identifier in person.mt_identifiers:
                if identifier != person_id:
                    person_obj.append_to("identifier", identifier)
        self.crate.add(person_obj)
        return person_obj

    def add_user(self, user: User) -> ROPerson:
        """Add a mytardis django user to the crate,
        including adding this user as a person.

        Args:
            user (User): the user to be added

        Returns:
            ROPerson: the user as an RO-Crate entity
        """
        user_entity: ROPerson = self.crate.dereference(
            user.roc_id
        ) or self.__add_person_to_crate(user)
        if user.groups:
            for group in user.groups:
                ro_group = self.crate.dereference(group.roc_id) or self.add_group(group)
                ro_group.append_to("has_member", user_entity)
                user_entity.append_to("groups", ro_group)
        self._add_optional_attr(user_entity, "permissions", user.permissions)
        self._add_optional_attr(
            user_entity, "isDjangoAccount", user.is_django_account, True
        )
        self._add_optional_attr(user_entity, "is_staff", user.is_staff, True)
        self._add_optional_attr(
            user_entity, "hashed_password", user.hashed_password, True
        )
        self._add_optional_attr(user_entity, "is_active", user.is_active, True)
        if user.last_login:
            user_entity.append_to(
                "last_login", serialize_optional_date(user.last_login), True
            )
        if user.date_joined:
            user_entity.append_to(
                "date_joined", serialize_optional_date(user.date_joined), True
            )
        return user_entity

    def add_principal_investigator(self, principal_investigator: Person) -> ROPerson:
        """Read in the principal investigator from the project and create an entry for them
        in the crate

        Args:
            principal_investigator (Person): _description_
        """
        return self.__add_person_to_crate(principal_investigator)

    def add_contributors(self, contributors: List[Person]) -> List[ROPerson]:
        """Add the contributors to a project into the crate

        Args:
            contributors (List[Person]): A list of people to add as contributors
        """
        return [self.__add_person_to_crate(contributor) for contributor in contributors]

    def _add_mt_identifiers(
        self,
        obj_dataclass: ContextObject,
        rocrate_obj: ContextEntity | DataEntity,
    ) -> ContextEntity | DataEntity:
        """Boilerplate code to add mt_identifiers to the RO Crate objects

        Args:
            obj_dataclass (BaseObject): A Project, Experiment or Dataset object
            rocrate_obj (ContextEntity | DataEntity): A RO-Crate object that the
                mt_identifiers are added to

        Returns:
            ContextEntity | DataEntity: The modified RO-Crate object
        """
        if obj_dataclass.mt_identifiers is None:
            return self.crate.add(rocrate_obj)
        for _, identifier in enumerate(obj_dataclass.mt_identifiers):
            if rocrate_obj.id != identifier:
                rocrate_obj.append_to("mt_identifiers", identifier)
        self.crate.add(rocrate_obj)
        return rocrate_obj

    def _add_pubkey_recipients(
        self, pubkey_fingerprints: List[str], keyserver: Optional[str] = None
    ) -> List[ContextEntity]:
        gpg = GPG(self.crate.gpg_binary)
        if keyserver:
            result = gpg.recv_keys(keyserver, pubkey_fingerprints)
            logger.info(
                "Attempted to retreive public keys from %s, result %s",
                keyserver,
                result,
            )
        held_keys = gpg.list_keys()
        recipients = []
        for fingerprint in pubkey_fingerprints:
            if recipent_key := held_keys.key_map.get(fingerprint):
                pubkey = PubkeyObject(
                    uids=recipent_key["uids"],
                    method=recipent_key["algo"],
                    key=fingerprint,
                )
            else:
                pubkey = PubkeyObject(
                    uids=[str(fingerprint)], key=fingerprint, method="unknown"
                )
            keyholder = Keyholder(self.crate, pubkey_fingerprint=pubkey)
            recipient = self.crate.dereference(keyholder.id) or self.crate.add(
                keyholder
            )
            recipients.append(recipient)
        return recipients

    def _add_metadata_to_crate(self, metadata_obj: MTMetadata) -> ContextEntity | None:
        """Add a MyTardis Metadata object to the crate

        Args:
            metadata_obj (MTMetadata): the MyTardis Metadata object
        """

        if metadata_obj.sensitive:
            if not metadata_obj.pubkey_fingerprints:
                return None
            metadata = EncryptedContextEntity(
                self.crate,
                metadata_obj.id,
                properties={
                    "@type": MT_METADATA_SCHEMATYPE,
                    "name": metadata_obj.name,
                    "value": metadata_obj.value,
                    "myTardis-type": metadata_obj.mt_type,
                    "sensitive": metadata_obj.sensitive,
                    "mytardis-schema": metadata_obj.mt_schema,
                },
            )
            recipents = self._add_pubkey_recipients(
                pubkey_fingerprints=metadata_obj.pubkey_fingerprints
            )
            metadata.append_to("recipients", recipents)
        else:
            metadata = ContextEntity(
                self.crate,
                metadata_obj.id,
                properties={
                    "@type": MT_METADATA_SCHEMATYPE,
                    "name": metadata_obj.name,
                    "value": metadata_obj.value,
                    "myTardis-type": metadata_obj.mt_type,
                    "sensitive": metadata_obj.sensitive,
                    "mytardis-schema": metadata_obj.mt_schema,
                },
            )
        return self.crate.add(metadata)

    def _crate_contains_metadata(self, metadata: MTMetadata) -> ContextEntity | None:
        if crate_metadata := self.crate.dereference(metadata.roc_id):
            if metadata.name == crate_metadata.get(
                "name"
            ) and metadata.value == crate_metadata.get("value"):
                return crate_metadata
        return None

    def add_metadata(
        self,
        metadata: MTMetadata,
    ) -> ContextEntity | None:
        """Add a metadata object to the RO-Crate
        generates parents and adds associated metadata if present

        Args:
            metadata (MTMetadata): the MyTardis metadata to add to the RO-Crate
        Returns:
            ContextEntity | None: the metadata as an RO-Crate entity
        """
        metadata_obj = self._crate_contains_metadata(
            metadata
        ) or self._add_metadata_to_crate(metadata)
        if not metadata_obj:
            return None
        parent_obj = self.crate.dereference(
            metadata.parent.roc_id
        ) or self.add_my_tardis_obj(metadata.parent)
        metadata_obj.append_to("parents", parent_obj)
        parent_obj.append_to("metadata", metadata_obj)

        return metadata_obj

    def _add_additional_properties(
        self,
        properties: Dict[str, Any],
        additional_properties: Dict[str, Any],
    ) -> JsonProperties:
        entity_properties = properties
        if not self.flatten_additional_properties:
            properties["additonal properties"] = {}
            entity_properties = properties["additonal properties"]
        for key, value in additional_properties.items():
            if isinstance(value, List):
                for index, item in enumerate(value):
                    value[index] = (
                        self.add_context_object(item).id
                        if isinstance(item, ContextObject)
                        else item
                    )
            if isinstance(value, ContextObject):
                value = self.add_context_object(value).id
            if key not in entity_properties.keys():  # pylint: disable=C0201
                entity_properties[key] = value
            elif isinstance(entity_properties[key], list):
                entity_properties[key].append(value)
            else:
                entity_properties[key] = [
                    properties,
                    value,
                ]
        return properties

    def _add_dates(
        self,
        properties: JsonProperties,
        date_created: datetime,
        date_modified: Optional[List[datetime]] = None,
    ) -> JsonProperties:
        """Add dates, where present, to the metadata

        Args:
            properties (Dict[str, str  |  List[str]  |  Dict[str, Any]]): properties of the RO-Crate
            date_created (datetime): created date of of the object
            date_modified (Optional[List[datetime]], optional): last modified date of the object
                Defaults to None.

        Returns:
            JsonProperties: _description_
        """
        properties["dateCreated"] = date_created.isoformat()
        if date_modified:
            properties["dateModified"] = [date.isoformat() for date in date_modified]
        properties["datePublished"] = date_created.isoformat()
        return properties

    def _update_properties(
        self, data_object: MyTardisContextObject, properties: JsonProperties
    ) -> JsonProperties:
        if data_object.date_created:
            properties = self._add_dates(
                properties,
                data_object.date_created,
                data_object.date_modified,
            )
        if data_object.additional_properties:
            properties = self._add_additional_properties(
                properties=properties,
                additional_properties=data_object.additional_properties,
            )
        if data_object.mytardis_classification:
            properties["mytardis_classification"] = str(
                data_object.mytardis_classification
            )
        return properties

    def add_project(self, project: Project) -> ContextEntity:
        """Add a project to the RO crate

        Args:
            project (Project): The project to be added to the crate
        """
        principal_investigator = self.add_principal_investigator(
            project.principal_investigator
        )
        contributors = []
        if project.contributors:
            contributors = self.add_contributors(project.contributors)

        properties: Dict[str, str | list[str] | dict[str, Any]] = {
            "@type": "Project",
            "name": project.name,
            "description": project.description,
        }

        properties = self._update_properties(data_object=project, properties=properties)
        project_obj = ContextEntity(
            self.crate,
            project.id,
            properties=properties,
        )

        project_obj.append_to("principal_investigator", principal_investigator)
        project_obj.append_to("contributors", contributors)
        if project.institution:
            parent_organization = self.crate.dereference(
                project.institution.roc_id
            ) or self.__add_organisation(project.institution)
            project_obj.append_to("parentOrganization", parent_organization)
            parent_organization.append_to("Projects", project_obj)

        self._add_optional_attr(
            project_obj,
            "embargo_until",
            serialize_optional_date(project.embargo_until),
            True,
        )
        self._add_optional_attr(
            project_obj, "start_time", serialize_optional_date(project.start_time), True
        )
        self._add_optional_attr(
            project_obj, "end_time", serialize_optional_date(project.end_time), True
        )
        if project.created_by is not None:
            creator = self.crate.dereference(
                project.created_by.roc_id
            ) or self.add_user(project.created_by)
            project_obj.append_to("createdBy", creator)
            creator.append_to("creator", project_obj)
            self._add_optional_attr(project_obj, "created_by", creator)
        self._add_optional_attr(project_obj, "url", project.url)
        return self._add_mt_identifiers(project, project_obj)

    def _update_experiment_meta(
        self,
        experiment: Experiment,
        properties: JsonProperties,
        projects: List[ContextEntity],
    ) -> ContextEntity:
        """Update the metadata for an experiment and create the context entity for the experiment

        Args:
            experiment (Experiment): the experiment object

        Returns:
            ContextEntity: the returned crate context entity
        """
        identifier = experiment.id
        properties = self._update_properties(
            data_object=experiment, properties=properties
        )
        experiment_entity = ContextEntity(
            self.crate,
            identifier,
            properties=properties,
        )
        self._add_optional_attr(experiment_entity, "url", experiment.url)
        self._add_optional_attr(
            experiment_entity, "url", serialize_optional_date(experiment.start_time)
        )
        self._add_optional_attr(
            experiment_entity, "url", serialize_optional_date(experiment.end_time)
        )
        if experiment.created_by:
            creator_entity = self.crate.dereference(
                experiment.created_by.roc_id
            ) or self.add_user(experiment.created_by)
            experiment_entity.append_to("creator", creator_entity.id)
            creator_entity.append_to("created", experiment_entity.id)
        self._add_optional_attr(experiment_entity, "locked", experiment.locked, True)
        self._add_optional_attr(experiment_entity, "handle", experiment.handle)
        self._add_optional_attr(
            experiment_entity, "approved", experiment.approved, True
        )
        if experiment.sd_license:
            lisence_id = experiment.sd_license
            if isinstance(experiment.sd_license, Lisence):
                lisence_id = str(
                    self.crate.dereference(experiment.sd_license.roc_id).id
                    or self.add_lisence(experiment.sd_license).id
                )
            experiment_entity.append_to("sdLicense", lisence_id)
        experiment_entity.append_to("project", projects)
        return experiment_entity

    def add_experiment(self, experiment: Experiment) -> ContextEntity:
        """Add an experiment to the RO crate

        Args:
            experiment (Experiment): The experiment to be added to the crate
        """
        # Note that this is being created as a data catalog object as there are no better
        # fits
        projects = []
        for project in experiment.projects:
            if crate_project := self.crate.dereference(project.roc_id):
                projects.append(crate_project)
            else:
                projects.append(self.add_project(project))
        properties: JsonProperties = {
            "@type": "DataCatalog",
            "name": experiment.name,
            "description": experiment.description,
        }
        experiment_obj = self._update_experiment_meta(
            experiment=experiment, properties=properties, projects=projects
        )
        return self._add_mt_identifiers(experiment, experiment_obj)

    def add_dataset(self, dataset: Dataset) -> DataEntity:
        """Add a dataset to the RO crate

        Args:
            dataset (Dataset): The dataset to be added to the crate
        """
        directory = dataset.directory
        identifier = directory.as_posix()
        if identifier != dataset.id:
            logger.warning(
                "dataset identifier should be relative filepaths updating %s to %s",
                dataset.id,
                identifier,
            )
        experiments = []
        for experiment in dataset.experiments:
            if crate_experiment := self.crate.dereference(experiment.roc_id):
                experiments.append(crate_experiment)
            else:
                experiments.append(self.add_experiment(experiment))

        properties: JsonProperties = {
            "name": dataset.name,
            "description": dataset.description,
        }
        instrument = dataset.instrument
        if (
            dataset.instrument
            and isinstance(dataset.instrument, ContextObject)
            and not self.crate.dereference(dataset.instrument.roc_id)
        ):
            instrument = self.add_instrument(dataset.instrument)
        properties = self._update_properties(data_object=dataset, properties=properties)

        if identifier == ".":
            logger.debug("Updating root dataset")
            self.crate.root_dataset.properties().update(properties)
            self.crate.root_dataset.source = (
                self.crate.source / Path(directory) if self.crate.source else None
            )
            dataset_obj = self.crate.root_dataset
        else:
            dataset_obj = self.crate.add_dataset(
                source=(
                    self.crate.source / Path(directory) if self.crate.source else None
                ),
                properties=properties,
                dest_path=Path(directory),
            )
        dataset_obj.append_to("includedInDataCatalog", experiments)
        dataset_obj.append_to("instrument", instrument)
        return self._add_mt_identifiers(dataset, dataset_obj)

    def add_datafile(self, datafile: Datafile) -> DataEntity:
        """Add a datafile to the RO-Crate,
        adding it to it's parent dataset has-part or the root if apropriate

        Args:
            datafile (Datafile): datafile to be added to the crate

        Returns:
            DataEntity: the datafile RO-Crate entity that will be written to the json-LD
        """
        identifier = datafile.filepath.as_posix()
        if identifier != datafile.id:
            logger.warning(
                "datafile mt_identifiers should be relative filepaths updating %s to %s",
                datafile.id,
                identifier,
            )
            datafile.mt_identifiers = [identifier] + datafile.mt_identifiers  # type: ignore
        properties: Dict[str, Any] = {
            "name": str(datafile.name),
            "description": datafile.description,
            "version": datafile.version,
        }
        properties = self._update_properties(
            data_object=datafile, properties=properties
        )
        source = (
            self.crate.source / datafile.filepath
            if self.crate.source and (self.crate.source / datafile.filepath).exists()
            else identifier
        )
        dataset_obj: DataEntity = self.crate.dereference(datafile.dataset.roc_id)
        if not dataset_obj:
            dataset_obj = self.crate.root_dataset

        destination_path = Path(dataset_obj.id) / datafile.filepath.relative_to(
            Path(dataset_obj.id)
        )
        datafile_obj = self.crate.add_file(
            source=source,
            properties=properties,
            dest_path=destination_path,
        )
        datafile_obj.append_to("dataset", dataset_obj)
        logger.info("Adding File to Crate %s", identifier)
        dataset_obj.append_to("hasPart", datafile_obj)
        return self._add_mt_identifiers(datafile, datafile_obj)

    def add_context_object(self, context_object: ContextObject) -> DataEntity:
        """Add a generic context object to the RO crate

        Args:
            context_object (ContextObject): the context object to be added

        Returns:
            DataEntity: the DataEntity in the RO-Crate
        """

        identifier = context_object.id
        properties = {
            key: value
            for key, value in context_object.__dict__.items()
            if value is not None and key != "identifier"
        }
        if properties.get("schema_type"):
            properties["@type"] = properties.pop("schema_type")
        if context_object.date_created:
            properties = self._add_dates(
                properties,
                context_object.date_created,
                context_object.date_modified,
            )
            properties.pop("date_created")
            properties.pop("date_modified")
        context_entitiy = self.crate.add(
            ContextEntity(self.crate, identifier, properties=properties)
        )
        return context_entitiy

    def add_facillity(self, facility: Facility) -> ContextEntity:
        """add a facility as a location to the RO-Crate

        Args:
            facility (Facility): the faciltiy object

        Returns:
            ContextEntity: the facility as an RO-crate object
        """

        properties: JsonProperties = {
            "@type": facility.schema_type,
            "name": facility.name,
            "description": facility.description,
        }
        if facility.manager_group:
            manager_group = self.crate.dereference(
                facility.manager_group.roc_id
            ) or self.add_group(facility.manager_group)
            properties["manager_group"] = manager_group.id
        properties = self._update_properties(facility, properties=properties)
        return self.crate.add(
            ContextEntity(
                crate=self.crate, identifier=facility.id, properties=properties
            )
        )

    def add_instrument(self, instrument: Instrument) -> ContextEntity:
        """Add an instrument to the RO-Crate

        Args:
            instrument (Instrument): the instrument object

        Returns:
            ContextEntity: the instrument as an RO-Crate entity
        """
        facility_location = self.crate.dereference(
            instrument.location.roc_id
        ) or self.add_facillity(instrument.location)
        properties: JsonProperties = {
            "@type": instrument.schema_type,
            "name": instrument.name,
            "description": instrument.description,
            "location": facility_location.id,
        }
        facility_location.append_to("containedInPlace", instrument.id)
        properties = self._update_properties(instrument, properties=properties)
        return self.crate.add(
            ContextEntity(
                crate=self.crate, identifier=instrument.id, properties=properties
            )
        )

    def add_lisence(self, lisence: Lisence) -> ContextEntity:
        """Add a lisence that should be associated with an experiment to the RO-Crate

        Args:
            lisence (Lisence): the lisence as a context object

        Returns:
            ContextEntity: the lisence entity in the RO-Crate
        """
        properties: JsonProperties = {
            "@type": str(lisence.schema_type),
            "name": lisence.name,
            "description": lisence.description,
        }
        lisence_entity = self.crate.add(
            ContextEntity(
                crate=self.crate, identifier=lisence.id, properties=properties
            )
        )

        self._add_optional_attr(
            lisence_entity, "allows_distribution", lisence.allows_distribution, True
        )
        self._add_optional_attr(lisence_entity, "is_active", lisence.is_active, True)
        self._add_optional_attr(lisence_entity, "image", lisence.image_url, False)
        return lisence_entity

    def add_my_tardis_obj(self, obj: MyTardisContextObject) -> ContextEntity:
        """Add a MyTardis object of unknown type to the RO-Crate

        Args:
            obj (MyTardisContextObject): the my tardis object to be added to the crate

        Returns:
            ContextEntity: the my tardis object as an RO-Crate entity
        """
        match obj:
            case Project():
                entity = self.add_project(obj)
            case Experiment():
                entity = self.add_experiment(obj)
            case Dataset():
                entity = self.add_dataset(obj)
            case Datafile():
                entity = self.add_datafile(obj)
            case Facility():
                entity = self.add_facillity(obj)
            case Instrument():
                entity = self.add_instrument(obj)
            case _:
                entity = self.add_context_object(obj)
        return entity
