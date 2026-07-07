# Changelog

## [0.2.1](https://github.com/gseg-ethz/geodispbench3d/compare/v0.2.0...v0.2.1) (2026-07-07)


### 📚 Documentation

* note iof3D research-access contact in README ([#10](https://github.com/gseg-ethz/geodispbench3d/issues/10)) ([7017f5b](https://github.com/gseg-ethz/geodispbench3d/commit/7017f5bf8b379af1e023f9cb625baa10f146cdbf))


### 🧹 Miscellaneous Chores

* remove .claude/ from public main ([#17](https://github.com/gseg-ethz/geodispbench3d/issues/17)) ([48b4bbf](https://github.com/gseg-ethz/geodispbench3d/commit/48b4bbfe8b939541f670bd22279e62a8c0c46c42))
* remove AGENTS.md and OVERVIEW.md from public main ([#15](https://github.com/gseg-ethz/geodispbench3d/issues/15)) ([684b4c1](https://github.com/gseg-ethz/geodispbench3d/commit/684b4c1164e5c3d53af1ea1fd9448d1ad1d8fe93))

## [0.2.0](https://github.com/gseg-ethz/geodispbench3d/compare/v0.1.0...v0.2.0) (2026-06-28)


### ✨ Features

* **04-01:** reconcile pyproject classifiers and project URLs (LIC-02, LIC-03) ([4e8ed2e](https://github.com/gseg-ethz/geodispbench3d/commit/4e8ed2ea0e0a288e69c11c0d4997fb07676e2dd6))
* **04-01:** reconcile README license + iof3d note (LIC-01, LIC-04) ([d4395d2](https://github.com/gseg-ethz/geodispbench3d/commit/d4395d2d047c0fee63f9d4cbc3285971beb3c281))
* **04-02:** disable iof3d extra, pin f2s3 pchandler ~= 2.1, fix extra hygiene (PKG-01/02/03) ([375d232](https://github.com/gseg-ethz/geodispbench3d/commit/375d23288ded4140b18028739c4dead9b17a1622))
* **04-02:** PEP 562 dormant-iof3D guard + cli launcher split (PKG-01, D-02/D-03) ([16bf4d2](https://github.com/gseg-ethz/geodispbench3d/commit/16bf4d21ca210345c6926eb3acc6fcb36e76cc0c))
* **05-01:** migrate package to Python 3.12-only, bump docs extra ([3aeb4d1](https://github.com/gseg-ethz/geodispbench3d/commit/3aeb4d141166fc63417715fbef11cd50c977b6ac))
* **05-03:** add OIDC publish workflows + production-publish preflight ([5c07880](https://github.com/gseg-ethz/geodispbench3d/commit/5c0788065892c9ac6bfbd6ba3b4ad56f6b425bbc))
* **05-03:** rewrite release-please to workflow_run + GitHub App token ([d527230](https://github.com/gseg-ethz/geodispbench3d/commit/d527230c439937c616ec0a9b2844b26cd192b8eb))
* **05-04:** add idempotent apply-rulesets.sh + ship-time README ([154bf77](https://github.com/gseg-ethz/geodispbench3d/commit/154bf77d341ee7c3781a0e2567dd023ef67f52de))
* **05-04:** add protect-main/develop ruleset payloads with exact CI contexts ([1726dce](https://github.com/gseg-ethz/geodispbench3d/commit/1726dce8cd4ad442dc27898481ba8a80bd699715))
* **05-05:** add check_ci_ruleset_contexts.py reconciliation guard ([d5b5a91](https://github.com/gseg-ethz/geodispbench3d/commit/d5b5a91e2a013ff6c5f0ee45af07c0e2ef013d39))
* **05-05:** add check_publish_gate.py supply-chain guard ([7b47a01](https://github.com/gseg-ethz/geodispbench3d/commit/7b47a018f39336f9bd25f730217a0747f0cfff53))
* **05-05:** add parametrized setup-python-deps composite action ([b52c1b1](https://github.com/gseg-ethz/geodispbench3d/commit/b52c1b1b5c67f6b024fbeba8016d84ca2db9c86b))
* **05-05:** restructure ci.yml (lint ‖ test matrix, build needs test, docs, SHA pins) ([8c70f73](https://github.com/gseg-ethz/geodispbench3d/commit/8c70f73ecc1ce0c143907742f119143e2411bbc6))
* add analysis YAML schema and loader ([58a7de1](https://github.com/gseg-ethz/geodispbench3d/commit/58a7de136753c6c98ec0d706d5fccf71b66e261f))
* add analyze runner and CLI verb ([cd48d9e](https://github.com/gseg-ethz/geodispbench3d/commit/cd48d9eff234478046b21c0df1ece4ff1445ef01))
* add core sweep framework ([6366d35](https://github.com/gseg-ethz/geodispbench3d/commit/6366d356281a3ad598ba6c89846b13dac1c8e74c))
* add F2S3 tool adapter ([a14987c](https://github.com/gseg-ethz/geodispbench3d/commit/a14987cf23b58b69d1cbef8d0ecc31af08b4a7d4))
* add iof3D tool adapter ([8d64334](https://github.com/gseg-ethz/geodispbench3d/commit/8d6433478f0c5b34a3716e1f3d13458a4918ee84))
* add Mattertal benchmark assets ([e5a848f](https://github.com/gseg-ethz/geodispbench3d/commit/e5a848ff20601258a237f7e7ed69efd52d4cc832))
* add rescore module for re-evaluating existing run dirs ([8b6f534](https://github.com/gseg-ethz/geodispbench3d/commit/8b6f534bb854d3a8e9d704dbf037b1dde69f2528))
* add Streamlit results dashboard ([595a7ac](https://github.com/gseg-ethz/geodispbench3d/commit/595a7ac7fbf75637a93794f0daf34929684f4983))
* cache phase-2 predictions to a separate location ([dd79ea9](https://github.com/gseg-ethz/geodispbench3d/commit/dd79ea97841033277201c3e465f6fcb6f92cf23c))
* enrich trial record with tool/dataset/parser provenance ([db20d8f](https://github.com/gseg-ethz/geodispbench3d/commit/db20d8f396d2927aa9db365e3fdfee339f63e4d4))
* wire --rescore into the geodispbench3d run CLI ([0b7268e](https://github.com/gseg-ethz/geodispbench3d/commit/0b7268ee443bc4bbc046fdac0c97280a040c78ee))


### 🐛 Bug Fixes

* **05-01:** scope pyright over src+tests on 3.12 and reach genuine 0 errors ([585a3a5](https://github.com/gseg-ethz/geodispbench3d/commit/585a3a575014b63583a7617ab743cb4a276f877c))
* **05-06:** adapt sweep runner to the Ax 1.3.x complete_trial contract ([b1299a2](https://github.com/gseg-ethz/geodispbench3d/commit/b1299a2a2751f9d0d74826b7a7178cd4f447b74e))
* **05-06:** declare pyarrow as a core dependency for the parquet store ([8e1dd37](https://github.com/gseg-ethz/geodispbench3d/commit/8e1dd37fd8ea59b4f884cfa349fe19647c0173ee))
* **05-06:** reclaim runner disk for the build install-smoke ([285ed3c](https://github.com/gseg-ethz/geodispbench3d/commit/285ed3c83878317ac367beaac1cf597422b20f1c))
* **05-06:** skip pchandler-coupled parser test when pchandler absent ([ebcd32a](https://github.com/gseg-ethz/geodispbench3d/commit/ebcd32a82b8d0a49f88bbc66e7b703605ce01287))


### 📚 Documentation

* **05-02:** add .readthedocs.yaml mirroring PCHandler (docs extra) ([5cab4d5](https://github.com/gseg-ethz/geodispbench3d/commit/5cab4d576637609d3831c48ea06372fe871fa197))
* **05-02:** add minimal myst conf.py; make existing Markdown warnings-clean under -W ([83fd3fe](https://github.com/gseg-ethz/geodispbench3d/commit/83fd3fe536f76f8f88d423a4c8a1b2ddf28f7e15))
* **05-02:** move Markdown under docs/source, rewrite repo-escaping links, repoint Documentation URL ([eaeb16a](https://github.com/gseg-ethz/geodispbench3d/commit/eaeb16aec12ddb0e78e0cf21b7d6084e4ab41898))
* add CITATION.cff ([ed73253](https://github.com/gseg-ethz/geodispbench3d/commit/ed732530222560f474743d10a1324b22836447ce))
* add user and integration documentation ([2e0429b](https://github.com/gseg-ethz/geodispbench3d/commit/2e0429b6205831dfb294e36075f1ecde996b70ef))
* create roadmap (5 phases) ([1f08e5d](https://github.com/gseg-ethz/geodispbench3d/commit/1f08e5d5b03352e09bec0512729c0cc78dbf3c06))
* **quick-260626-jix:** create OVERVIEW.md one-pager for ETH open-source docs ([eafdd93](https://github.com/gseg-ethz/geodispbench3d/commit/eafdd932888ea049b9d96fbe04e9fd5b53d5a16e))


### 🧹 Miscellaneous Chores

* **05-03:** seed durable 0.1.0 manifest baseline and bootstrap v0.2.0 ([fe33264](https://github.com/gseg-ethz/geodispbench3d/commit/fe332646a1786027888f8e766441ae4cd98bea67))
* add .gitignore ([746d9a3](https://github.com/gseg-ethz/geodispbench3d/commit/746d9a338e7a4d7f7919fb88d779e500398ddda9))
* add packaging metadata ([55b8874](https://github.com/gseg-ethz/geodispbench3d/commit/55b8874b065d9e7af6565e7e469c99197f1a6c68))
* add pre-commit config and apply ruff formatting ([611953a](https://github.com/gseg-ethz/geodispbench3d/commit/611953a10ad19d4dfcc4824322cab6e09b887627))
* align ruff pins to 0.15 family across dev + pre-commit ([5a5c4c2](https://github.com/gseg-ethz/geodispbench3d/commit/5a5c4c28fc3ec30e2f27b644c02a62a978470f57))
* gitignore editor *.code-workspace files ([43c7d22](https://github.com/gseg-ethz/geodispbench3d/commit/43c7d2271dcc61efeb0f379134d3a52a15d99beb))
* initial commit ([a806d80](https://github.com/gseg-ethz/geodispbench3d/commit/a806d80a3b46c6cf4153cbca9d05946df9b6ed64))
* switch LICENSE to BSD-3-Clause with ETH copyright ([c8de58c](https://github.com/gseg-ethz/geodispbench3d/commit/c8de58ca0e4c6964d8faeee9add894e3ecf9a047))


### ✅ Tests

* **04-01:** add failing metadata-assertion test for LIC-01..04 ([8a30e5b](https://github.com/gseg-ethz/geodispbench3d/commit/8a30e5bd2b659477b1929758c79cf5cc5e189f36))
* **04-02:** add failing dormant-iof3D import-guard + extras tests (RED) ([c20152e](https://github.com/gseg-ethz/geodispbench3d/commit/c20152e93c4998a5c3bea81f533b14a932d8a342))
* add core suites for predictions cache, rescore, and analyze ([80284fe](https://github.com/gseg-ethz/geodispbench3d/commit/80284fe7bbd3cd8af2300231d69ddfb4ebee717e))
* add core, iof3d, f2s3 test suites ([24e7a2f](https://github.com/gseg-ethz/geodispbench3d/commit/24e7a2f9ca395adbeda1b9a7943a8ae9a9cad02e))


### 🤖 Continuous Integration

* add release-please workflow and config ([9f545ef](https://github.com/gseg-ethz/geodispbench3d/commit/9f545ef646c70745ea1238666c29db3bcdc53365))
* add three-job matrix workflow ([05a55bb](https://github.com/gseg-ethz/geodispbench3d/commit/05a55bbd00abdd8416e12942dd0ee261db1c320a))
* rewrite workflow as single-pipeline lint+test+build ([1194908](https://github.com/gseg-ethz/geodispbench3d/commit/1194908e6deddcd389da8847c65f032a9d7b144a))
