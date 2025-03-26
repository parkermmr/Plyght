[![CI Status][ci-shield]][ci-url]
[![Coverage][coverage-shield]][coverage-url]
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]


<br />
<div align="center">
  <a href="https://github.com/parkermmr/plyght">
    <img src="docs/img/logo.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Plyght</h3>

  <p align="center">
    A Python utility library made for modern, robust, industry Python applications.
    <br />
    <a href="https://plyght.teampixl.info"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/parkermmr/plyght">View Demo</a>
    &middot;
    <a href="https://github.com/parkermmr/plyght/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://https://github.com/parkermmr/plyght/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#compendium-ci">Compendium CI</a></li>
      </ul>
    </li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

## About The Project


### Built With

<p align="center">
  
- [![Python][python]][python-url]
- [![Git][git]][git-url]
- [![GitHub Actions][github-actions]][github-actions-url]
- [![Docker][docker]][docker-url]

</p>
<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

### Installation

### Compendium CI
The current workflow being used is a Compendium CI Python Poetry pipeline with comprehensive checks for testing, linting, style, code security and structure. Compendium is a GitHub specific CI suite fully managed [here][compendium]. It is important that before any pushes are made the code quality checks and reformatting are ran. This can be done with the following commands:
```bash
poetry run black src && poetry run isort src
```
This will ensure the pipeline completes successfully and all code is to an appropriate format standard. For more information on the linting configuration seek out the `pyproject.toml` configuration under `[tools.black]` & `[tools.isort]` as well as the `.flake8` configuration file.

### Acknowledgments:

<a href="https://github.com/parkermmr/CAB320A1/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=parkermmr/CAB320A1" alt="contrib.rocks image" />
</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

[ci-shield]: https://img.shields.io/github/actions/workflow/status/parkermmr/plyght/compendium.yml?branch=main&style=for-the-badge
[ci-url]: https://github.com/parkermmr/plyght/actions/workflows/compendium.yml
[coverage-shield]: https://img.shields.io/codecov/c/github/parkermmr/cab320a1?style=for-the-badge
[coverage-url]: https://codecov.io/gh/parkermmr/plyght
[contributors-shield]: https://img.shields.io/github/contributors/parkermmr/plyght.svg?style=for-the-badge
[contributors-url]: https://github.com/parkermmr/plyght/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/parkermmr/plyght.svg?style=for-the-badge
[forks-url]: https://github.com/parkermmr/plyght/network/members
[stars-shield]: https://img.shields.io/github/stars/parkermmr/plyght.svg?style=for-the-badge
[stars-url]: https://github.com/parkermmr/plyght/stargazers
[issues-shield]: https://img.shields.io/github/issues/parkermmr/plyght.svg?style=for-the-badge
[issues-url]: https://github.com/parkermmr/plyght/issues
[python]: https://img.shields.io/badge/python-FFE873?style=for-the-badge&logo=python&logoColor
[python-url]: https://www.python.org/
[git]: https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=Git&logoColor=white
[git-url]: https://git-scm.com/
[github-actions]: https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=GitHub%20Actions&logoColor=white
[github-actions-url]: https://github.com/features/actions
[docker]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=Docker&logoColor=white
[docker-url]: https://www.docker.com/
[compendium]: https://github.com/parkermmr/compendium