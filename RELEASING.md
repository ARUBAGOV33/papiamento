# Releasing

How to publish a version of the dataset. [GOVERNANCE.md](GOVERNANCE.md#releases) says when a release is major, minor or patch; this file says how to make one.

A release has three copies, all built from the same tag:

| Where | What | Made by |
|---|---|---|
| GitHub release | The tag, release notes, and the built files attached | A maintainer, then the release workflow |
| Zenodo | An archive of the repository at the tag, with a DOI | Zenodo, automatically |
| Hugging Face | The JSON Lines files and the dataset card | The release workflow |

## One-time setup

These need the **ARUBAGOV33** account, because only a repository admin can turn them on.

### Zenodo

1. Sign in at [zenodo.org](https://zenodo.org) with **Log in with GitHub**, using the ARUBAGOV33 account.
2. Open **Account → GitHub**, press **Sync now**, and switch on `ARUBAGOV33/papiamento`.

Zenodo only archives releases published after the switch is on. It reads the title, description, licence and keywords from [`.zenodo.json`](.zenodo.json).

### Hugging Face

1. Create the Hugging Face account or organisation that will own the dataset.
2. Create an access token with write access (**Settings → Access Tokens**).
3. On GitHub, add it as a repository secret named `HF_TOKEN` (**Settings → Secrets and variables → Actions**).
4. The dataset is published as `ARUBAGOV33/papiamento`. To use another name, add a repository variable `HF_DATASET_REPO`, for example `my-org/papiamento`.

Without the `HF_TOKEN` secret, the release workflow skips Hugging Face and says so. The other steps still run.

## Each release

### 1. Release pull request

Branch `release-vX.Y.Z` from `main` and change:

- `CHANGELOG.md`: move the entries under "Unreleased" to a new `## [X.Y.Z] - YYYY-MM-DD` section, and update the links at the bottom.
- `CITATION.cff`: set `version` (without the `v`) and `date-released`.
- `README.md`: update "Project status" if it changed.

Then build the release files and read them:

```sh
python3 tools/build_dist.py
```

Check `dist/RELEASE_NOTES.md` (rows per table and status) and `dist/README.md` (the dataset card). `dist/` is never committed.

Open the pull request. The gauntlet must pass and a maintainer must approve it.

If the merge happens on a later day than `date-released`, correct the date in the pull request before merging.

### 2. Tag and publish

After the merge:

```sh
git switch main
git pull
python3 tools/build_dist.py
gh release create vX.Y.Z --target main --title "vX.Y.Z" --notes-file dist/RELEASE_NOTES.md
```

Or on GitHub: **Releases → Draft a new release**, create the tag `vX.Y.Z` on `main`, and paste `dist/RELEASE_NOTES.md` as the description.

### 3. What happens next

Publishing the release starts [`.github/workflows/release.yml`](.github/workflows/release.yml). It:

1. stops if the tag does not match `version` in `CITATION.cff`;
2. runs the gauntlet;
3. builds `dist/` and attaches the JSON Lines files, `rule_pack.json`, `manifest.json` and a zip of everything to the release;
4. publishes `dist/` to Hugging Face and tags it there with the same version.

If a step fails, fix the cause and run the workflow again from the **Actions** tab (**Release → Run workflow**, with the tag).

At the same time, Zenodo archives the release and gives it a DOI. This takes a few minutes.

### 4. Add the DOI

Zenodo gives two DOIs: one for this version, and a concept DOI that always points to the latest version. Open a small pull request that adds:

- to `CITATION.cff`: `doi:` with the concept DOI, and under `identifiers` the version DOI with a description such as "Version X.Y.Z";
- to `README.md`: the Zenodo DOI badge and the DOI under "How to cite".

## Rules

- A published version is never changed. Corrections go into the next version.
- Never move or delete a tag.
- Ids never change between versions.
