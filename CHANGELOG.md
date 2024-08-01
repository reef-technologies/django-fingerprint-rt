# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the
upcoming release can be found in [changelog.d](changelog.d).

<!-- towncrier release notes start -->

## [0.1.0](https://github.com/reef-technologies/django-fingerprint-rt/releases/tag/v0.1.0) - 2024-08-01


### Added

- Add `cf-ipcountry` and `referer` to persistet headers


### Fixed

- Fix missing imports in fingerprint admin code.

### Infrastructure

- Rebase project to cookiecutter-rt-pkg template for improved CI&CD pipeline.
