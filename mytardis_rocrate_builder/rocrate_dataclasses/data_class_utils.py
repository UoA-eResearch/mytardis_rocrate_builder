# pylint: disable=missing-function-docstring
"""Helper functions and classes for managing and moving RO-Crate ingestible dataclasses.
"""

import copy
from typing import Any, Dict, List, Optional

from slugify import slugify

from .rocrate_dataclasses import ACL, Datafile, Dataset, Experiment, MTMetadata, Project


class CrateManifest:
    """Manifest for storing all dataclasses that will be built into and RO-Crate"""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        projcets: Optional[Dict[str, Project]] = None,
        experiments: Optional[Dict[str, Experiment]] = None,
        datasets: Optional[Dict[str, Dataset]] = None,
        datafiles: Optional[List[Datafile]] = None,
        metadata: Optional[List[MTMetadata]] = None,
        acls: Optional[List[ACL]] = None,
    ):
        self.projcets = projcets or {}
        self.experiments = experiments or {}
        self.datasets = datasets or {}
        self.datafiles = datafiles or []
        self.metadata = metadata or []
        self.acls = acls or []

    def add_projects(self, projcets: Dict[str, Project]) -> None:
        self.projcets = self.projcets | projcets

    def add_experiments(self, experiments: Dict[str, Experiment]) -> None:
        self.experiments = self.experiments | experiments

    def add_datasets(self, datasets: Dict[str, Dataset]) -> None:
        self.datasets = self.datasets | datasets

    def add_datafiles(self, datafiles: List[Datafile]) -> None:
        self.datafiles.extend(datafiles)

    def add_metadata(self, metadata: List[MTMetadata]) -> None:
        self.metadata.extend(metadata)

    def add_acls(self, acls: List[ACL]) -> None:
        self.acls.extend(acls)


def reduce_to_dataset(in_manifest: CrateManifest, dataset: Dataset) -> CrateManifest:
    dataset = copy.deepcopy(dataset)
    project_ids: set[str] = set()
    out_experiments: Dict[str, Experiment] = {}
    for experiment in dataset.experiments:
        if out_experiment := in_manifest.experiments.get(str(experiment.id)):
            out_experiments[str(experiment.id)] = out_experiment
            project_ids.update(str(project.id) for project in out_experiment.projects)
    out_projects: Dict[str, Project] = {
        project_id: in_manifest.projcets[project_id]
        for project_id in project_ids
        if in_manifest.projcets.get(project_id)
    }

    out_files = [
        copy.deepcopy(datafile)
        for datafile in in_manifest.datafiles
        if datafile.dataset.directory == dataset.directory
    ]
    out_file_ids = (outfile.id for outfile in out_files)
    outmetadata = []
    for metadata in in_manifest.metadata:
        parent_id = metadata.parent.id
        if (
            parent_id == dataset.id
            or parent_id in out_experiments
            or parent_id in out_projects
            or parent_id in out_file_ids
        ):
            outmetadata.append(metadata)
    outacls = []
    for acl in in_manifest.acls:
        parent_id = acl.parent.id
        if (
            parent_id == dataset.id
            or parent_id in out_experiments
            or parent_id in out_projects
            or parent_id in out_file_ids
        ):
            outacls.append(acl)

    _ = [df.update_to_root(dataset) for df in out_files]

    return CrateManifest(
        projcets=out_projects,
        experiments=out_experiments,
        datasets={str(dataset.id): dataset},
        datafiles=out_files,
        metadata=outmetadata,
        acls=outacls,
    )


def convert_to_property_value(
    json_element: Dict[str, Any] | Any, name: str
) -> Dict[str, Any]:
    """convert a json element into property values for compliance with RO-Crate

    Args:
        json_element (Dict[str, Any] | Any): the json to turn into a Property value
        name (str): the name for the partent json

    Returns:
        Dict[str, Any]: the input as a property value
    """
    if not isinstance(json_element, Dict) and not isinstance(json_element, List):
        return {"@type": "PropertyValue", "name": name, "value": json_element}
    if isinstance(json_element, List):
        return {
            "@type": "PropertyValue",
            "name": name,
            "value": [
                convert_to_property_value(item, slugify(f"{name}-{index}"))
                for index, item in enumerate(json_element)
            ],
        }
    json_element["@type"] = "PropertyValue"
    json_element["name"] = name
    for key, value in json_element.items():
        if isinstance(value, (Dict, List)):
            json_element[key] = convert_to_property_value(value, key)
    return json_element
