# cdisc-open-rules
Contains rules and test data that can be processed by CORE

**BEFORE CONTRIBUTING, MAKE SURE YOU HAVE GONE THROUGH THE CDISC VOLUNTEERING ONBOARDING PROCESS** \
https://www.cdisc.org/volunteer

**SUPPLEMENTARY GUIDE** \
Instructions below will guide you step-by-step through the:
- First-time Local Setup Steps
- Rule Authoring and Test Data Creation Process

# First-time Local Setup Steps

***IMPORTANT NOTE*** \
_You may need your IT support team to install some of the following software for you. In particular, the setup script requires python3.12 to run properly. If you don't have it installed, the script will attempt to install it for you, but this is likely to be blocked by your company settings. If so, you will need to contact IT._

**Follow steps 1 - 9 carefully.**

1) Create a free GitHub account: https://github.com/signup
2) Install Git, following the instructions here: https://git-scm.com/install
   - When prompted, ensure you check the **"Add to PATH"** option (or select **"Git from the command line and also from 3rd-party software"**)
   - Keep all other default settings throughout the installer
   - You DO NOT need to actually run Git as a program, so close any pop-ups that appear after the installation
3) Install VSCode (***not*** VSCodeUser), following the instructions here: https://code.visualstudio.com/download
4) Open VSCode and a terminal within it:
   - Top Menu → Terminal → New Terminal (check the three dots in the top menu if you don't see 'Terminal')
5) Open VSCode and a terminal within it:
   - Top Menu → Terminal → New Terminal (check the three dots in the top menu if you don't see 'Terminal')
   - Configure your Git identity by running the following two commands in the terminal, replacing the placeholder values with your own:

      `git config --global user.name "Your Name"`

      `git config --global user.email "you@example.com"`

   Use the same email address you used when creating your GitHub account in step 1. You only need to do this once per machine.
6) Create a new empty directory on your machine for storing the repository and subsequent rule authoring and editing. Navigate to it in the terminal using `cd` commands. Avoid OneDrive if possible.
   - There is sometimes an AI 'helper' box popup in the terminal - make sure you are typing commands into the command line itself, not the box
   - If any of the folder names you are navigating through have spaces (eg 'My Folder'), you will need to wrap the path in quotes,\
     eg: `cd "C:\Users\sam\Documents\Rules Folder"`
7) Clone this repo into that directory by running the following command (**DO NOT RUN MORE THAN ONCE**): \
       `git clone --recurse-submodules https://github.com/cdisc-org/cdisc-open-rules.git`
   > **NOTE:** If you encounter `The term 'git' is not recognized as the name of a cmdlet, function, script file, or operable program.`, Git's installation directory has not been added to your system PATH. See [this StackOverflow answer](https://stackoverflow.com/questions/4492979/error-git-is-not-recognized-as-an-internal-or-external-command) for instructions on manually adding Git to your PATH.

   _***IMPORTANT NOTE***\
   Unless something goes badly wrong and you need to fully delete the entire directory, you should never need to run this command again._

8) In VSCode, select "Open Folder" and select the repository folder you just cloned - it should be called `cdisc-open-rules`
   - VSCode may show a prompt asking if you trust the authors of the files in this folder — click **Yes, I trust the authors**
   - You should also see a prompt to install the workspace recommended extensions in the bottom right corner — click **Install All**. If you miss this prompt, don't worry — step 10 will cover it

9) This should re-open a new terminal in the repository folder. If this doesn't happen, open a new terminal in VSCode and navigate to the repository folder again.

10) You will need to setup the python environment, which will take a little bit of time.
   - Assuming you are in the cdisc-open-rules folder in the VSCode terminal, run one of the following depending on your operating system (ignore messages and warnings):
     - WINDOWS: `.\setup\windows_setup.bat`
     - MAC: `./setup/bash_setup.sh`
   - Windows might prompt you asking if you want to install python - the answer is yes!

   _***IMPORTANT NOTE***\
   If you start the setup script and stop it midway through, you may get some strange errors when you try to run rules in the future. If you have any doubts, rerun the setup script, and make sure it completes._

11) Set up the rule authoring auto-completion and real-time schema validation:
    - When you opened the repository folder in step 7, VSCode should have shown a prompt to install the workspace recommended extensions — click **Install All** if you haven't already
    - If you missed the prompt, go to Extensions on the left sidebar, search for `@recommended` in the Extensions search bar and install them from there
    - That's it! Schema validation and CSV highlighting will be active automatically once the extensions are installed. If you don't see this behaviour after a few seconds, try restarting VSCode

**You are now ready with the setup steps and can start with the rule authoring!**

# Rule Authoring and Test Data Creation Process

**_*IMPORTANT NOTE*_**\
_In the following section, the exact process to follow with relevant Git commands to be executed in the terminal are described. If in doubt, you can always fall back to this process. However, VSCode integrates with Git very effectively, and so there are intuitive point-and-click alternatives to all of the following commands with only simple configuration required._

## Command Line Process

**Create a Local Branch.**

1) Make sure you are on the main branch and that both the main branch and the engine submodule are up to date. To do this, run the following three commands: \
       `git checkout main` \
       `git pull origin main` \
       `git submodule update --recursive`

2) Create a new branch to work on your changes, named as such: `<your-name>/<rule-id>/<change>` (eg `richard/CORE-000001/edit`): \
       `git branch <your-branch-name>`

   **_*IMPORTANT NOTE*_**\
   _Whenever you create a local branch to work on a rule, ensure that you are on the main branch. If you create a new local branch, when you are already on a local branch, the new branch will branch off the local branch and not from main. If you would then want to merge changes from your new local branch, it will merge with the first local branch and not with the main branch. Therefore, ensure to be on the main branch first prior to creating a local branch (git checkout main). Once the local branch exists, you can checkout out to it from any branch._

3) Switch to your new branch: \
       `git checkout <your-branch-name>`

**Set up Rule Folder.**

**_*IMPORTANT NOTE*_**\
_Step 4 is only applicable in case you want to create a rule for which the folder does not exist yet in the GitHub repository. It is therefore important to first check if a folder is already present. If no folder is present, you can automatically generate the required folder structure for a new rule including a blank YAML template and template files for the test data._

4) Initialize your new rule folder structure:
   - In the base directory of the project, activate the virtual environment by running:
     - WINDOWS: `venv\Scripts\activate`
     - MAC: `source venv/bin/activate`
   - Then run the following command in your terminal: \
       `python new-rule.py`
   - It will prompt you a few times.
     - If the `NEW-RULE` folder already exists, it will check you definitely want to make a new one. (NOTE: If the empty folder is a leftover from a previous branch, which is likely, you SHOULD run the script and overwrite the folder to make a new one, as this will set up the template properly for you).
     - You will also be prompted to enter the number of positive and negative test cases you want to create. Don't worry if you realise you need more later — you can easily add more manually.
   - This will create an `Unpublished/NEW-RULE` folder with all necessary subdirectories and template files.
   - The `NEW-RULE` folder should **NOT** be renamed. It will receive its final name after the PR has been approved.

**Rule and Test Data Directory Structure.**

Each in-progress rule lives under `Unpublished/NEW-RULE/` and follows this layout:

```
Unpublished/
└── NEW-RULE/
    ├── rule.yml
    ├── positive/
    │   ├── 01/
    │   │   ├── data/
    │   │   │   ├── .env
    │   │   │   ├── datasets.csv
    │   │   │   ├── variables.csv
    │   │   │   └── <dataset>.csv   (one per entry in datasets.csv)
    │   │   └── results/
    │   └── 02/
    │       ├── data/
    │       └── results/
    └── negative/
        └── 01/
            ├── data/
            └── results/
```

- **`rule.yml`** — the rule definition, at the root of the rule directory.
- **`positive/`** — test cases where the data contains no violations; the rule should produce no errors.
- **`negative/`** — test cases where the data deliberately violates the rule and errors are expected.
- Each test case is numbered (`01`, `02`, …) and contains a `data/` and a `results/` subdirectory.

> **NOTE:** Rules and test data from SharePoint and the rule editor have been transferred and organized into their respective standards folders in this repository. If you are continuing work on an existing rule, move the `rule.yml` and any existing test data into the `NEW-RULE` folder on your branch, following the directory structure above, before running or testing the rule.

**Edit the Rule.**

5) Open `Unpublished/NEW-RULE/rule.yml` and edit the rule definition as desired.
   - Ensure that you save any changes (File → Save, or Ctrl/Cmd + S)

**Create Test Data.**

> **NOTE:** The workspace recommended extensions installed in step 10 include 'Excel Viewer' and 'Rainbow CSV'. Excel Viewer displays CSVs as a formatted table — to use it, open any CSV file and click the table icon in the top right corner of the editor, or right-click (Windows/Linux) / two-finger click (Mac) the file and select **Open With... → Excel Viewer**. Rainbow CSV color-codes each column directly in the raw CSV view to make it easier to read.

6) Each test case's `data/` folder must contain the following files:

   **`.env`**

   Specifies the standard and version to validate against. `PRODUCT` and `VERSION` are required; `SUBSTANDARD`, `USE_CASE`, `CT`, and `DEFINE_XML` are optional depending on the rule.

   ```
   PRODUCT=TIG
   VERSION=1-0
   SUBSTANDARD=SDTM
   USE_CASE=PROD
   CT=sdtmct2020-12-18
   DEFINE_XML=define.xml
   ```

   **`datasets.csv`**

   Lists every dataset file that must be present in the `data/` folder for this test case. Each row names a file and provides its human-readable label.

   ```
   Filename,Label
   cm.xpt,Concomitant/Prior Medications
   ```

   For every row in `datasets.csv` you must also provide a corresponding dataset CSV file in the same `data/` folder (see below).

   **`variables.csv`**

   Describes all variables across all datasets for this test case. The `dataset` column corresponds to the filename listed in `datasets.csv`.

   ```
   dataset,variable,label,type,length
   cm.xpt,STUDYID,Study Identifier,Char,50
   cm.xpt,DOMAIN,Domain Abbreviation,Char,50
   cm.xpt,USUBJID,Unique Subject Identifier,Char,50
   cm.xpt,CMTRT,"Reported Name of Drug, Med, or Therapy",Char,50
   dm.xpt,STUDYID,Study Identifier,Char,50
   dm.xpt,DOMAIN,Domain Abbreviation,Char,50
   dm.xpt,USUBJID,Unique Subject Identifier,Char,50
   dm.xpt,AGE,Age,Num,8
   ...
   ```

   | Column | Description |
   |--------|-------------|
   | `dataset` | Filename of the dataset this variable belongs to (must match a `Filename` in `datasets.csv`) |
   | `variable` | Variable name (e.g. `USUBJID`) |
   | `label` | Variable Label |
   | `type` | Data type — `Char` or `Num` |
   | `length` | Maximum field length |

   **Dataset CSV files**

   For each dataset listed in `datasets.csv`, provide a CSV file with a matching name (e.g. if `datasets.csv` lists `cm.xpt`, include `cm.csv` in `data/`). The columns must match the variables listed for that dataset in `variables.csv`.

   Example `cm.csv`:

   ```
   STUDYID,DOMAIN,USUBJID,CMSEQ,CMTRT,CMINDC,CMDOSE,CMDOSU,...
   STUDY01,CM,STUDY01-001,1,ASPIRIN,HEADACHE,500,mg,...
   ```

   - Column headers must exactly match the `variable` values in `variables.csv` for that dataset.
   - For **positive** cases, ensure the data satisfies all rule conditions so no errors are raised.
   - For **negative** cases, include data that deliberately triggers the rule. When raising your PR, describe the errors you expect to see in the PR description or as a comment so reviewers can verify the generated `results.json` against your intent. There is no automated validation check for CSV test data; human review of the results is required.

   **`results/`**

   Leave this folder empty when creating new test cases. The CI pipeline will generate and commit a `results.json` on the first run, or you can generate it locally using the run script below.

**Perform Local Testing.**

7) When you want to run the rule against test data locally, make sure you are in the cdisc-open-rules folder and run one of the following: \
   WINDOWS: `.\run\windows_run.bat` \
   MAC: `./run/bash_run.sh`
   - If you haven't run the setup script before, don't worry; it will run automatically when you execute this command.
   - You will be prompted to select the rule you wish to run, as well as the test case(s).

**Verify Results.**

8) Check your run results in the `results/` folder of each test case.
   - There will be a `results.json` file with the engine output.
   - For positive cases, verify that no errors are reported.
   - For negative cases, verify that the errors reported match the violations you introduced in the test data. Include a summary of the expected errors in your PR description so reviewers can confirm the output is correct.

9) If you are unhappy with the results of your changes, continue to edit and run the rule until you are satisfied.

**Request Review via PR.**

10) Create a PR to add your changes to the repository. To do this, run the following commands: \
       `git add .` \
       `git commit -m "your custom message"` \
       `git push origin <your-branch-name>`
    - The first time you commit, you may have to log in to GitHub

11) Go to the online repository and create a pull request (PR) from your newly pushed branch

12) On the PR page, make sure the information at the top is correct. It should be: \
       `base: main ← compare: <branch-name>`

13) Name your PR using the format `<rule-id> <fix>` and add a brief description of your changes. If you are making a new rule, use `<conformance-rule-id> create`. Include a description of the errors expected in any negative test cases so reviewers can audit the generated `results.json`.

14) On the PR, add reviewers (both the 'Rules Team' and 'Engineers Team' are required) by clicking the cog in the top right corner, and add yourself as an assignee

15) You're done!
    - The CI pipeline will automatically run the rule against all test cases and post a validation report as a PR comment. It will also commit the generated `results.json` files back to your branch.
    - Keep an eye on the PR to make sure the automated checks pass, as well as to respond to any comments from reviewers.
    - If you need to make further changes, simply checkout your branch (`git checkout <your-branch-name>`), make your changes, and commit and push them — the PR will automatically update and re-run validation.

**Approval - Merge PR**

16) Once your PR is approved, merge your changes to the source code. If you created a new rule in your PR, a new CORE-id will be assigned to it.

**Let's do another rule!**

17) If you want to start editing another rule, don't forget to run the below commands on VSCode terminal again: \
       `git checkout main` \
       `git pull origin main`

For further detail on any of these steps or git in general, see [supplementary guide](https://docs.google.com/document/d/15ydgj4AqtEnFtlXL-J4DLJV32q_Q71gKn0ucu4tYYQw/edit?pli=1&tab=t.0)

# Something's Wrong!

Git is great, but it is easy to overlook something and make a mistake. \
If you're stuck or confused, please reach out to Richard (richard@verisian.com) or Maximo (maximo@verisian.com) for support - we're always happy to help! \
However, here are some quick fixes for common issues you might experience: \
<br />

> ***I accidentally made my changes on the main branch but haven't committed them yet***

If the branch you want to move your changes to already exists, run: \
`git checkout main` \
`git stash` \
`git checkout <existing-branch-name>` \
`git stash pop` \
If you want to move the changes to a new branch, you can run this useful one-liner: \
`git switch -c <new-branch-name>` \
<br />

> ***I accidentally made my changes on the main branch and committed them***

In this case, you won't be able to move your changes to an already existing branch easily. If you desperately need to do this, reach out to us. \
Otherwise, create a new branch from main which includes your changes and then reset main: \
`git checkout -b <new-branch-name>` \
`git checkout main` \
`git reset --hard HEAD~1` \
`git checkout <new-branch-name>`

***IMPORTANT NOTE*** - if you've committed more than once on main, you'll need to replace `HEAD~1` with `HEAD~n` where `n` is the number of commits you've made \
<br />

> ***I've made some changes that I want to push to the repo and other changes that I don't want to keep***

In the source control sidebar panel (the icon is three dots connected by lines), you will see all of the changes you've made. \
You can right-click on any of these and select 'Discard Changes'. \
This will completely remove your changes, so make sure you don't want them before doing this! \
<br />

> ***I want to work on multiple rules at once!***

You can! You can create multiple branches for different rules and they will all be isolated from each other. \
Just make sure to use `checkout` commands or the console to switch to the relevant branch before you make changes. \
<br />
