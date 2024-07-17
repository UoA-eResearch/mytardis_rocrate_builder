# pylint: disable=missing-function-docstring
"""
Functions and classes for managing RO-Crate manifests of all dataclasses to be added to an RO-Crate
"""
import copy
from typing import Dict, List, Optional

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
    """Reduce a crate manifest to a single dataset

    Args:
        in_manifest (CrateManifest): the input manifest to be reduced
        dataset (Dataset): the dataset that will become the new root dataset

    Returns:
        CrateManifest: the crate containing only the dataset and it's parents/children
    """
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
            metadata.parent == dataset
            or parent_id in out_experiments
            or parent_id in out_projects
            or parent_id in out_file_ids
        ):
            outmetadata.append(metadata)
    outacls = []
    for acl in in_manifest.acls:
        parent_id = acl.parent.id
        if (
            acl.parent == dataset
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
