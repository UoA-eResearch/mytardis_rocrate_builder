# pylint: disable=import-error, no-name-in-module
"""Builder class and functions for translating RO-Crate dataclasses into RO-Crate Entities
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rocrate.model.contextentity import ContextEntity
from rocrate.model.data_entity import DataEntity
from rocrate.model.encryptedcontextentity import EncryptedContextEntity
from rocrate.model.person import Person as ROPerson
from rocrate.rocrate import ROCrate

from .rocrate_dataclasses.rocrate_dataclasses import (  # Group,
    ACL,
    ContextObject,
    Datafile,
    Dataset,
    Experiment,
    Instrument,
    MTMetadata,
    MyTardisContextObject,
    Organisation,
    Person,
    Project,
)

MT_METADATA_SCHEMATYPE = "my_tardis_metadata"
logger = logging.getLogger(__name__)

JsonProperties = Dict[str, str | List[str] | Dict[str, Any]]
IdentiferType = str | int | float


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

    def add_acl(self, acl: ACL) -> ContextEntity | None:
        """Add an ACL to the RO-Crate.
         updating relationships between ACL and parents

        Args:
            acl (ACL): the ACL to be added

        Returns:
            ContextEntity | None: the ACL as a context entity
        """
        acl_entity = self.crate.dereference(acl.id) or self._add_acl_to_crate(acl)
        parent_obj = self.crate.dereference(acl.parent.id) or self.add_my_tardis_obj(
            acl.parent
        )
        # Create person or group the ACL refers to here if it does not already exist
        acl_entity.append_to("subjectOf", parent_obj.id)
        parent_obj.append_to("hasDigitalDocumentPermission", acl.id)
        return acl_entity

    def __add_organisation(self, organisation: Organisation) -> None:
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
        if organisation.url:
            org.append_to("url", organisation.url)
        if len(organisation.mt_identifiers) > 1:
            for index, identifier in enumerate(organisation.mt_identifiers):
                if index != 0:
                    org.append_to("identifier", identifier)
        self.crate.add(org)

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
        if not any(
            (
                entity.type in ["Organization", "ResearchOrganization"]
                and entity.id == person.affiliation.id
            )
            for entity in self.crate.get_entities()
        ):
            self.__add_organisation(person.affiliation)
        person_obj = ROPerson(
            self.crate,
            person.id,
            properties={
                "name": person.name,
                "email": person.email,
                "affiliation": person.affiliation.id,
            },
        )
        if len(person.mt_identifiers) > 1:
            for identifier in person.mt_identifiers:
                if identifier != person_id:
                    person_obj.append_to("identifier", identifier)
        self.crate.add(person_obj)
        return person_obj

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
        for _, identifier in enumerate(obj_dataclass.mt_identifiers):
            if rocrate_obj.id != identifier:
                rocrate_obj.append_to("mt_identifiers", identifier)
        self.crate.add(rocrate_obj)
        return rocrate_obj

    def _add_metadata_to_crate(self, metadata_obj: MTMetadata) -> ContextEntity | None:
        """Add a MyTardis Metadata object to the crate

        Args:
            metadata_obj (MTMetadata): the MyTardis Metadata object
        """

        if metadata_obj.sensitive:
            if not self.crate.pubkey_fingerprints:
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
                    "parents": [metadata_obj.parent.id],
                    "mytardis-schema": metadata_obj.mt_schema,
                },
                pubkey_fingerprints=[],
            )
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
                    "parents": [metadata_obj.parent.id],
                    "mytardis-schema": metadata_obj.mt_schema,
                },
            )

        return self.crate.add(metadata)

    def _crate_contains_metadata(self, metadata: MTMetadata) -> ContextEntity | None:
        if crate_metadata := self.crate.dereference(metadata.id):
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
            metadata.parent.id
        ) or self.add_my_tardis_obj(metadata.parent)
        metadata_obj.append_to("parents", parent_obj.id)
        parent_obj.append_to("metadata", metadata_obj.id)

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
        properties = {
            "@type": "Project",
            "name": project.name,
            "description": project.description,
            "principal_investigator": principal_investigator.id,
            "contributors": [contributor.id for contributor in contributors],
        }

        properties = self._update_properties(data_object=project, properties=properties)
        project_obj = ContextEntity(
            self.crate,
            project.id,
            properties=properties,
        )

        return self._add_mt_identifiers(project, project_obj)

    def _update_experiment_meta(
        self,
        experiment: Experiment,
        properties: JsonProperties,
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
        return ContextEntity(
            self.crate,
            identifier,
            properties=properties,
        )

    def add_experiment(self, experiment: Experiment) -> ContextEntity:
        """Add an experiment to the RO crate

        Args:
            experiment (Experiment): The experiment to be added to the crate
        """
        # Note that this is being created as a data catalog object as there are no better
        # fits
        projects = []
        for project in experiment.projects:
            if crate_project := self.crate.dereference("#" + str(project.id)):
                projects.append(crate_project.id)
            else:
                projects.append(self.add_project(project).id)
        properties: JsonProperties = {
            "@type": "DataCatalog",
            "name": experiment.name,
            "description": experiment.description,
            "project": projects,
        }
        experiment_obj = self._update_experiment_meta(
            experiment=experiment, properties=properties
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
            if crate_experiment := self.crate.dereference("#" + str(experiment.id)):
                experiments.append(crate_experiment.id)
            else:
                experiments.append(self.add_experiment(experiment).id)

        properties: JsonProperties = {
            "name": dataset.name,
            "description": dataset.description,
            "includedInDataCatalog": experiments,
        }
        instrument_id = dataset.instrument.id
        if (
            dataset.instrument
            and isinstance(dataset.instrument, ContextObject)
            and not self.crate.dereference(dataset.instrument.id)
        ):
            instrument_id = self.add_context_object(dataset.instrument).id
        properties["instrument"] = str(instrument_id)
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
            "name": datafile.name,
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
        dataset_obj: DataEntity = self.crate.dereference(datafile.dataset.id)
        if not dataset_obj:
            dataset_obj = self.crate.root_dataset
        properties["dataset"] = dataset_obj.id
        destination_path = Path(dataset_obj.id) / datafile.filepath.relative_to(
            Path(dataset_obj.id)
        )
        datafile_obj = self.crate.add_file(
            source=source,
            properties=properties,
            dest_path=destination_path,
        )
        logger.info("Adding File to Crate %s", identifier)
        dataset_obj.append_to("hasPart", datafile_obj)
        return self._add_mt_identifiers(datafile, datafile_obj)

    def _add_acl_to_crate(self, acl: ACL) -> DataEntity:
        """Add an individual ACL to the RO-Crate

        Args:
            acl (ACL): the ACL to be added

        Returns:
            DataEntity: the RO-Crate context entity representing the ACL
        """
        # REPLACE WITH ADD GROUP AND ADD PERSON_ACL FUNCTION
        #  if not self.crate.dereference(acl.grantee):
        #     self.add_context_object(
        #         context_object=ContextObject(
        #             name=f"{acl.grantee} ACL holder",
        #             description=f"Owner of ACL: {acl.grantee}",
        #             mt_identifiers=[acl.grantee],
        #             schema_type=(
        #                 ["Organization"]
        #                 if "organization" in acl.grantee_type
        #                 else ["Person"]
        #             ),
        #             date_created=None,
        #             date_modified=None,
        #             additional_properties=None,
        #         )
        # )

        identifier = acl.id
        properties = {
            "@type": acl.schema_type,
            "permission_type": acl.permission_type,
            "grantee": acl.grantee.id,
            "grantee_type": acl.grantee_type,
            "my_tardis_can_download": acl.mytardis_can_download,
            "mytardis_owner": acl.mytardis_owner,
            "mytardis_see_sensitive": acl.mytardis_see_sensitive,
        }
        return self.crate.add(
            ContextEntity(self.crate, identifier, properties=properties)
        )

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

    def add_my_tardis_obj(self, obj: MyTardisContextObject) -> ContextEntity:
        """Add a MyTardis object of unknown type to the RO-Crate

        Args:
            obj (MyTardisContextObject): the my tardis object to be added to the crate

        Returns:
            ContextEntity: the my tardis object as an RO-Crate entity
        """
        match obj:
            case Project():
                return self.add_project(obj)
            case Experiment():
                return self.add_experiment(obj)
            case Dataset():
                return self.add_dataset(obj)
            case Datafile():
                return self.add_datafile(obj)
            case Instrument():
                pass
                # pass until add instrument included
            case _:
                return self.add_context_object(obj)
