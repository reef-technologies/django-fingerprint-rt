# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the
upcoming release can be found in [changelog.d](changelog.d).

<!-- towncrier release notes start -->

## [0.2.2](https://github.com/reef-technologies/django-fingerprint-rt/releases/tag/v0.2.2) - 2026-08-27

### Changed

- Raise supported floors to Python 3.11+ and Django 4.2+; declare Python 3.13/3.14 and Django 5.2 support.

### Added

- Add `rebuild_hit_counts` management command to recompute cached hit counts from fingerprint rows.
- Cache unique-session hit counts per URL so `get_count_for_urls` reads denormalized counts instead of aggregating fingerprint rows.


## [0.2.1](https://github.com/reef-technologies/django-fingerprint-rt/releases/tag/v0.2.1) - 2026-02-13

### Fixed

- Fix: reduce number of requests in `get_count_for_urls`
- Fix long values handing

## [0.2.0](https://github.com/reef-technologies/django-fingerprint-rt/releases/tag/v0.2.0) - 2025-03-19

### Added

- Capture and save UTM params in user session.
- Save referer header to UserSession in `fingerprint` decorator.


## [0.1.0](https://github.com/reef-technologies/django-fingerprint-rt/releases/tag/v0.1.0) - 2024-08-01


### Added

- Add `cf-ipcountry` and `referer` to persistet headers


### Fixed

- Fix missing imports in fingerprint admin code.

### Infrastructure

- Rebase project to cookiecutter-rt-pkg template for improved CI&CD pipeline.
