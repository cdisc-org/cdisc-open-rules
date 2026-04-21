# Test Data

## Preparing Test Data for Unit Testing

### Assumptions

- CORE MVP 1.0 must support SAS V5 XPT and Dataset-JSON data file formats for validation. Other formats such as CSV, Dataset-XML, etc. are a nice-to-haves.
- Many volunteer contributors do not have the ability to create SAS V5 XPT files, easily and quickly for creation of test data for unit testing.
- A CSV format approach is very similar to creating data examples in the wiki.
- A well-templated CSV adds consistency and reduces fatigue.
- Test data in CSV are to be used for unit testing = checking whether the rule logic works correctly and output matches with what is expected.
- Volunteer contributors could also use unit testing for debugging rule logic.

- Unit testing includes testing rule logic on both positive and negative test data.
    - Positive test data: Test data is in compliance with the conformance rule and will not result in output. All test data passes.
    - Negative test data: Test data is not in compliance with the conformance rule and will result in output. Not all test data passes.
- Unit testing will be conducted per CDISC Open Rule. If more than one conformance rule (e.g. conformance rules from 2 different standards like SDTMIG and SENDIG use exactly the same rule logic and scope) is included in 1 CDISC Open Rule, then unit testing should only be done once. The standard used to create test data can be chosen by the volunteer contributor.
- Test data should be kept relatively small, just enough data points to assert correctness and full functionality of the rule.
- Existing mock studies are available to the volunteer contributors as a valuable resource.
- Volunteer contributors will receive a report (= results file) for each run of unit testing.

### Not Covered

This Test Data section does not cover unit test execution.

### Test Data Format

Each test case lives inside a numbered folder under `positive/` or `negative/` within the rule directory, and contains a `data/` subdirectory with the following files:

```
positive/
└── 01/
    ├── data/
    │   ├── .env
    │   ├── _datasets.csv
    │   ├── _variables.csv
    │   └── <dataset>.csv   (one per entry in _datasets.csv)
    └── results/
negative/
└── 01/
    ├── data/
    └── results/
```

- Positive and negative test data are kept in separate numbered test case folders.
- Multiple datasets can be included in a single test case by providing multiple dataset CSV files.
- The `results/` folder will contain the `results.csv` --this can be generated using the local run script, outlined in the readme.  The local script also generates a `results.json` which can we used for testing but should be deleted when sending a rule to QC for publication.

#### SDTMIG & SENDIG

Each test case's `data/` folder must contain the following files:

**`.env`**

Specifies the standard and version to validate against. `PRODUCT` and `VERSION` are required; `CT`, and `DEFINE_XML` are optional depending on the rule.

```
PRODUCT=sdtmig
VERSION=3-4
CT=sdtmct-2024-03-29
```

- Based on the rule being tested and its IG scope, set the applicable `PRODUCT` and `VERSION`. Example: CG0100 is applicable for SDTMIG 3.3 so `PRODUCT=sdtmig` and `VERSION=3-3`.
- If a rule is applicable for multiple versions of an IG, then only 1 IG should be tested.  If there is a clear distinction in rule logic between IG versions--multiple versions for each version should be created.
- If a rule needs to use CDISC CT, add the `CT` key with the appropriate CT package.

**`_datasets.csv`**

Lists every dataset file present in the `data/` folder for this test case. Each row names a file and provides its human-readable label.

```
Filename,Label
ae,Adverse Events
dm,Demographics
```

- Based on the rule being tested and the scope (Class, Domain), include only the datasets needed. All datasets that are created should be listed here.
- This file should not list datasets that do not have a corresponding CSV file.

**`_variables.csv`**

Describes all variables across all datasets for this test case. The `dataset` column corresponds to the filename listed in `_datasets.csv`.

```
dataset,variable,label,type,length
ae,STUDYID,Study Identifier,Char,50
ae,DOMAIN,Domain Abbreviation,Char,2
ae,USUBJID,Unique Subject Identifier,Char,50
ae,AETERM,Reported Term for the Adverse Event,Char,200
dm,STUDYID,Study Identifier,Char,50
dm,DOMAIN,Domain Abbreviation,Char,2
dm,USUBJID,Unique Subject Identifier,Char,50
dm,AGE,Age,Num,8
```

| Column | Description |
|--------|-------------|
| `dataset` | Filename of the dataset this variable belongs to (must match a `Filename` in `_datasets.csv`) |
| `variable` | Variable name (e.g. `USUBJID`) |
| `label` | Variable label |
| `type` | Data type — `Char` or `Num` |
| `length` | Maximum field length |

**Dataset CSV files**

For each dataset listed in `_datasets.csv`, provide a CSV file with a matching name (e.g. if `_datasets.csv` lists `ae`, include `ae.csv` in `data/` directory). Column headers must exactly match the `variable` values listed for that dataset in `_variables.csv`.

Example `ae.csv`:

```
STUDYID,DOMAIN,USUBJID,AETERM,...
STUDY01,AE,STUDY01-001,HEADACHE,...
```

- For **positive** cases, ensure the data satisfies all rule conditions so no errors are raised.
- For **negative** cases, include data that deliberately triggers the rule.

#### ADaMIG

under construction

#### Define-XML

- In case a CDISC Open Rule is using metadata captured in a define.xml to execute rule logic, then a test define.xml needs to be created (negative and positive) and uploaded for unit testing in the `data/` directory of each test.
- To create this test define.xml, the templates created for the Metadata Submission Guidelines for SDTM and ADaM can be used and adapted accordingly.
- Reference the define.xml in the `.env` file using `DEFINE_XML=define.xml`.  This should be equal to the name of the define file contained in the directory.

#### TIG

- Test data creation for TIG is similar to creation of test data for SDTMIG, SENDIG, or ADaMIG.
- There are 2 additional parameters in the `.env` file that need to be specified for TIG:
  - `SUBSTANDARD`: `sdtm`, `send`, `cdash`, or `adam`
  - `USE_CASE`: `PROD`, `INDH`, `NONCLIN`, or `ANALYSIS`
- The applicability of these 2 parameters is indicated in the TIG conformance rules spreadsheet published on the CDISC website: https://www.cdisc.org/system/files/members/standard/foundational/TIG%20Conformance%20Rules%20v1.0%20%281%29.xlsx

Example `.env` for a TIG rule:

```
PRODUCT=TIG
VERSION=1-0
SUBSTANDARD=SDTM
USE_CASE=PROD
```

#### USDM

under construction

### Creating Correct Test Data

**Best Practices**

Creating solid, qualitative test data is a skill on its own and needs to be done with care. Below best practices will help you during this process.
- Test data should test **all** functionalities of the rule logic.
- Test data should test both **condition** (if applicable) and **rule**.
- If more than 1 domain is in scope, test data should be created for more than 1 domain.
  - Scope = EVENTS, then for example test data can be made for AE and MH.
  - Scope = ALL then for example test data for 1 EVENTS domain and 1 FINDINGS domain can be made.
  - If a domain is excluded from the scope, then this domain should be included in the test data as positive test data.
- Generating too many rows in test data should be avoided. Only what is necessary to test the rule logic should be created.
- If the rule logic is testing >, =, < or something similar, then test data should be created that is testing the threshold values.
- Positive test data should not generate output in unit testing.
- Negative test data should generate output in unit testing.
- If the rule being tested references CDISC CT, then the correct name and version should be added as `CT` in the `.env` file.

Volunteer contributors should use the information available to create test data, such that:
- Dataset CSV files can be copied from sample data and adapted.
- Unused variables can be removed from `_variables.csv` and the dataset CSV.
- Variable metadata can be modified in `_variables.csv` in accordance with the test purpose of the associated rule logic.
- Dataset metadata can be modified in `_datasets.csv` in accordance with the test purpose.
- Mock study data will be available to volunteer contributors to easily borrow (i.e., copy and paste) rows as test data.

**Test Case Naming**

Test cases are numbered folders under `positive/` and `negative/`:

```
positive/01/    positive/02/ (only if applicable)    ...
negative/01/    negative/02/ (only if applicable)    ...
```

### Verifying Negative Test Results

For negative test cases, there is no automated cell-level validation check for CSV test data — human review of the results is required. When raising your PR:

- Describe the errors you expect to see in the PR description or as a comment.
- Reviewers will verify the generated `results.csv` against your stated intent.
- The CI pipeline diffs the `results.csv` you commit locally against engine output during review. If a difference is detected, the check will fail — re-run locally, verify the results look correct, and push the updated `results.csv`.

A `results.csv` summarizing issues found is generated alongside `results.json` after each local run. **Leave `results/` empty when first creating a test case.** After running locally and confirming results, commit the `results.csv` but delete `results.json` before opening your PR.

### Templates - Examples - Sample Data

This section contains links to the different Test Data Templates, Test Data Examples, and Sample Data. Together with the instructions given above, this should give volunteer contributors sufficient information to create consistent, qualitative test data.

  #### Template ####

  - The `_datasets.csv` template contains a list of datasets that can be used for unit testing.
  - The `_variables.csv` template includes Identifier, Events, Interventions, Findings, Timing, and Associated Persons variables from SDTM v2.0.
  - Domain-specific variable sets are drawn from SDTMIG v3.4, as well as AC, APRELSUB, DI, and TX from SDTM v2.0.

  [unit-test-sdtmig-sendig-template.xlsx](files/unit-test-sdtmig-sendig-template.xlsx ":ignore")

  #### Examples ####

  Also, here is a mock Excel workbook for positive and negative testing against which contains:

  - dm.xpt and ae.xpt.
  - Both with variable metadata adjusted, unused columns removed, data rows added.

  [unit-test-ruleid-sdtmigexample-positive.xlsx](files/unit-test-sdtmigexample-positive.xlsx ":ignore")
  [unit-test-ruleid-sdtmigexample-negative.xlsx](files/unit-test-sdtmigexample-negative.xlsx ":ignore")

  #### Sample Data ####

  CDISC has 2 sets of mock study in SDTM format. They have been converted for use as test data.

  - [CDISCTestData-sdtm-xpt-xlsx.zip](files/CDISCTestData-sdtm-xpt-xlsx.zip ":ignore") A set of test data files transformed from the CDISCTestData Github repo, sourced from /SDTM/XPT. Per Read Me, this mock study implements "SDTM IG Version 3.2.
  - [sdtm-msg-2-0-m5-datasets-xlsx.zip](files/sdtm-msg-2-0-m5-datasets-xlsx.zip ":ignore") A set of test data files transformed from the example submission bundled in the SDTM MSG v2.0, sourced from /m5/datasets/cdiscpilot01/tabulations/sdtm, as well as the split subdirectory. Per documentation, this example submission implements "SDTM v1.7/SDTMIG v3.3, and SDTM Terminology 2020-03-27.

## Storage

### Assumptions

- 1500 is an estimate of # of rules volunteer contributors will create.
- Each rule will have file artifacts, such as CSV and XML files.
- Main purpose for these file artifacts is to support unit testing. Secondary purpose is to support regression test.
- Unit testing will need both data for positive test & negative test, which each volunteer contributor is responsible to create & maintain.
- Each test may require 1:n files.
- Each rule may require 1:n positive & negative tests.
- Each test run will have a validate report as a result, which each rule author is responsible to save.
- Conceptually, this requires some deep folder structure, e.g., [Rule Id] > Unit Test > Positive > [#] > files

### Proposal

GitHub will be used for storage:

- Supports drag-and-drops.
- File versioning is a built-in functionality, behind the scene, without user interventions.
- Test data storage is directly linked to the rule YAML file and the results file generated via automated unit testing, allowing clear traceability and version control.

### Sharepoint Site

SharePoint will be used to store the source data catalogs, templates etc. for volunteer contributors to use whenever needed.

[CORE Rules SharePoint (permission required)](https://cdisc.sharepoint.com/sites/CORERules/Shared%20Documents/Forms/AllItems.aspx)

### Local OneDrive Access

It is recommended that you use OneDrive for access to the CORE Rules SharePoint. This will allow you the ability to consult files on your local desktop without the need to upload or edit within the browser.

There are two options for accessing the Sharepoint files from OneDrive. The choice is personal preference, but Sharepoint allows you to only do one or the other.

- [Sync Sharepoint site](https://support.microsoft.com/en-us/office/sync-sharepoint-files-and-folders-87a96948-4dd7-43e4-aca1-53f3e18bea9b)
- [Add shortcut to OneDrive](https://support.microsoft.com/en-us/office/add-shortcuts-to-shared-folders-in-onedrive-for-work-or-school-d66b1347-99b7-4470-9360-ffc048d35a33)
