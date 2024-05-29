# Scripts used for building RO-Crates containing MyTardis Metadata

## RO-Crate objects unique to MyTardis
There are several entities in MyTardis RO-Crates that do not appear in schema.org specifically for ingestion and recovery of MyTardis metadata.


### MTmetadata object
The main entity that is unique to MyTardis RO-Crates is the MTmetadata object which contains all information specific to a piece of MyTardis Metadata. It can be used to recover this information and the associated schema if the MyTardis data or instance is lost.

There is usually one MTmetadata object per piece of unique metadata on a MyTardis Object in the crate.
```json
{
   "@id": {
       "type": "string",
       "description" : "unique ID in the RO-Crate"
    },
   "@type": "MyTardis-Metadata_field",
   "name": {
       "type": "string",
       "description" : "name of the metadata in MyTardis"
   },
   "value": {
       "description" : "Metadata value in my tardis"
    },
   "mt-type": {
       "type": "string",
       "description" : "Metadata type as recorded in MyTardis",
       "default": "STRING"
    },
   "sensitive": {
       "type": "bool",
       "description" : "Is this metadata marked as sensitive in MyTardis, used to encrypt metadata",
       "default": True
    },
    "Parents": {
       "type": "array",
       "items" : {
        "type": "string"
       },
       "description" : "The ID of any entity this metadata is associated with in the crate",
    },
    "required": [ "@id", "@type", "name","value","mt-type" ],
}
```
for example:
```json
{
    "@id": "#BAM_Analysis code",
    "@type": "my_tardis_metadata",
    "myTardis-type": "STRING",
    "name": "Analysis code",
    "sensitive": false,
    "value": "vs2",
    "parents":[
        "#BAM",
        "#BAM_sorted"
        ]
}
```
## Encryption
MyTardis RO-Crates employ encryption of RO-Crate metadata provided by [UoA's RO-Crate Fork](https://github.com/UoA-eResearch/ro-crate-py/tree/encrypted-metadata).

In order to use this encryption provide the script with a comma seperated list of gpg public key fingerprints using the `--pubkey_fingerprints` parameter, and the path of your gpg binary using the `gpg_binary` parameter (optional - defaults to OS standard location)
```sh
 ro_crate_builder print-lab -i /print_lab_dir/sampledata.xls -o /output_crate_location \
  --pubkey_fingerprints F523D60AED2D218D9EE1135B0DF7C73A2578B8E3,3630FBB4ED664C8B690AD951A1CA576366F78539 \
  --gpg_binary /path/to/gpg2
```

All metadata marked as sensitive in MyTardis will be read into a PGP encrypted block encrypted against the keys provided to the script.

These encrypted blocks are found in the `"@encrypted"` entity at the root of any ro-crate-metadata.json file.

If no keys or binary are provided then sensitive metadata will not be read in to the RO-Crate.

## Requirements
Mandatory:
- [poetry](https://python-poetry.org/docs/)
- [python3](https://www.python.org/downloads/) (version >=3.11)

Optional:
- a valid [GnuPG](https://www.gnupg.org/download/) binary (required for encryption)
- MyTardis API Key (required for user lookup in MyTardis)
- PassPy with UoA LDAP key (required for user lookup in LADP)