# VersionLint
Automatic Repository Version Generation Utility

Generates simple and consistent textual and numerical versions from reposity meta-data.

# Requirements
1. The respository uses release branches, with a fixed prefix
  By default, the prefix is 'rel-', customizable on API interface
2. The repository uses annotated tags for release versions and milestones:
  - For release, tag is formatted as `v(major).(minor)`
  - For milestone, the tag is formatted as `m(major).(minor)[-extension]`
  - Prefix are customizable on API interface, but can only be a single character
  - Both major and minor tokens must be natrual numbers
  - The extension is optional for milestone tags, and can use any alphanumeric charaters

# Interface
## Commandline
```
python VersionLint.py [<token> <token> ...]
```

Possible tokens (case insensitive):
1. Ver: Casual version string `(major).(minor).(commit)-(branch)[.(prefix)(-extension)][.(state)]`
    - The commit token is the number of commit from the last annotated tag
    - The prefix token exists if the last annotated tag has non-release prefix
    - The state token provides addition description of the repository, with the following possible values:
        - "dirty" if the repository has untracked file, unstaged or uncommitted change, or modified submodules
2. NumVer: Fully numerical version string `(major).(minor).(commit).(flags)`
    - The flags token is bit field which describes that following states of the repository:
        - 0x01: Active branch is a non-release branch
        - 0x02: Last Annotated tag has non-release prefix
        - 0x08: Repository is dirty
            - 0x10: Repository has untracked file
            - 0x20: Repository has unstaged changes
            - 0x40: Repository has uncommitted changes
            - 0x80: Repository has modified submodules
3. MvnVer: Maven compatible version string
    - On a release branch
        Require: the last annotated tag has release prefix, and repository is not dirty
        - If requirement met: `(major).(minor).(commit)-(branch)`
        - Otherwise, fail with error message and non-zero return value
    - On a non-release branch
        - If last annotated tag has release prefix: `(major).(minor+1)-(branch)[-extension]-SNAPSHOT`
        - Otherwise: `(major).(minor)-(branch)[-extension]-SNAPSHOT`
4. Flags: Provide text description of the current repository status:
    Will output following if applicable
    - "Release branch" / "Non-release branch"
    - "Release tagged" / "Non-release tagged"
    - "Source Dirty"
        - "Untracked"
        - "Unstaged"
        - "Uncommitted"
        - "Submodule"
5. Hash: The long hash value of the current commit
6. Branch: The branch name of the current repository
7. Dirt: Provide statistics of dirts in the repository
    - How many untracked files, unstaged or uncommitted changes
    - What submodule is dirty, and its statistitcs


## Programmatic API
```python
from VersionLint import VersionLint
proj = VersionLint.GitProject("path-to-project-root")
```

- Fields:
    - `RepoTokens`: [object]
        - `prefix`
        - `major`
        - `minor`
        - `extension`
        - `commits`
        - `hashcode`
        - `branch`
        - `state`
    - `ReleaseBranch`: [True/False]
    - `ReleaseTagged`: [True/False]
    - `Modifications`: [object]
        - `name`: [string: submodule name, '.' for root]
        - `untracked`: [int: number of untracked files]
        - `unstaged`: [int: number of unstages changes]
        - `uncommitted`: [int: number of uncommitted changes]
        - `submodule`: [array of `Modifications` object, each for one submodule, recursive]
- Methods:
    - `isVolatile()`: whether building on current repo is "volatile"
        - True if output of the build is potentially irreproducible, e.g. repo is dirty
    - `isSane()`: whether building on current repo is "sane"
        - False if active branch is for release, but not tagged properly or isVolatile()
    - `getVersionString()`: return *Casual version string*
    - `getQualifierFlags()`: return numeric flag value used as the forth token of *Fully numerical version string*
    - `getNumericalVersion()`: return a tuple of four numeric version tokens
    - `explainQualifierFlags(flags)`: return an array of text decoding the qualifier flags
    - `getMavenVersionString()`: return *Maven compatible version string*
