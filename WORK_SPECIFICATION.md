# contentctl GitHub Actions 구축 - 작업 명세서

## 개요

이 문서는 `contentctl` 기반 GitHub Actions CI/CD 구축을 위한 작업 명세서이다.
각 작업은 Claude Team 모드로 할당되며, Git Worktree를 통해 독립적으로 수행된 후 `master` 브랜치에 통합된다.

---

## 작업 의존성 다이어그램

```
Phase 0: [Task 0] Repository Base Structure (master 직접 커밋)
              │
              ▼
Phase 1: 병렬 작업 (각각 독립 worktree)
         ┌──────────┬──────────┬──────────┬──────────┬──────────┐
         │          │          │          │          │          │
      [Task 1]  [Task 2]  [Task 3]  [Task 4]  [Task 5]  [Task 6]
      Build WF  Test WF    Setup     Testing   Sample   README
                           Docs      Guide     Content
         │          │          │          │          │          │
         └──────────┴──────────┴──────────┴──────────┴──────────┘
              │
              ▼
Phase 2: [Task 7] 통합 검증 및 master 최종 커밋
```

---

## 기술 전제 조건 (리서치 결과)

| 항목 | 값 |
|------|-----|
| contentctl 최신 버전 | 5.5.16 |
| Python 지원 범위 | 3.11, 3.12, 3.13 (워크플로에서는 3.11 사용) |
| CI 테스트 명령 | `contentctl test --disable-tqdm --no-enable-integration-testing --post-test-behavior never_pause mode:changes` |
| 빌드 명령 | `contentctl build` (enrichments는 옵션) |
| 필수 루트 설정 파일 | `contentctl.yml` |
| 러너 | `ubuntu-latest` |

---

## Phase 0: Task 0 - Repository Base Structure

### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `master` (직접 커밋) |
| Worktree | 불필요 (기반 작업) |
| 선행 의존 | 없음 |
| 후속 의존 | Task 1~6 모두 이 작업 완료 후 시작 |
| 담당 | 단독 에이전트 |

### 작업 내용

Phase 1의 모든 병렬 작업이 공통으로 참조하는 기반 파일/디렉터리를 `master`에 직접 커밋한다.

#### 0-1. `.gitignore` 생성

아래 패턴을 포함:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg
.venv/
venv/

# contentctl build output
output/
dist/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Test results
test_results/

# Secrets (절대 커밋 금지)
.env
*.pem
credentials.json
```

#### 0-2. `contentctl.yml` 생성

contentctl이 프로젝트를 인식하기 위한 필수 루트 설정 파일. 최소 구성:

```yaml
title: dollce_security_content
version: 1.0.0
description: Custom security content for Splunk
prefix: DOLLCE

build:
  build_app: true
  build_api: false
  path_root: "."

# test_servers 섹션은 향후 통합 테스트 확장 시 추가
# test:
#   test_servers:
#     - address: ...
```

**주의사항:**
- `title`, `version`, `description`, `prefix`는 필수 필드
- `prefix`는 생성되는 Splunk App의 접두어로 사용됨
- contentctl의 실제 스키마에 맞게 조정 필요 (에이전트가 `contentctl init` 결과를 참고할 것)

#### 0-3. `requirements.txt` 생성

```text
contentctl==5.5.16
```

#### 0-4. 디렉터리 구조 생성

각 디렉터리에 `.gitkeep` 파일을 생성하여 빈 디렉터리를 Git에 반영:

```
detections/.gitkeep
stories/.gitkeep
macros/.gitkeep
lookups/.gitkeep
deployments/.gitkeep
data_sources/.gitkeep
docs/.gitkeep
```

### 완료 기준

- [ ] `master`에 위 파일이 모두 커밋됨
- [ ] `contentctl validate`를 실행했을 때 기본 구조 에러가 없음 (detection이 없으므로 경고는 허용)
- [ ] Phase 1 작업들이 이 상태를 base로 worktree를 생성할 수 있음

### 커밋 메시지

```
feat: initialize repository base structure for contentctl

- Add .gitignore, contentctl.yml, requirements.txt
- Create content directories (detections, stories, macros, lookups, deployments, data_sources, docs)
```

---

## Phase 1: 병렬 Worktree 작업

> Phase 1의 모든 Task는 Phase 0 완료 후 **동시에 병렬 실행** 가능하다.
> 각 Task는 독립 Git Worktree에서 작업하며, 서로 다른 파일을 수정하므로 병합 충돌이 발생하지 않는다.

---

### Task 1 - Build Workflow

#### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `feature/workflow-build` |
| Worktree | `isolation: worktree` |
| 선행 의존 | Task 0 |
| 후속 의존 | Task 7 (통합) |
| 생성 파일 | `.github/workflows/contentctl-build.yml` |

#### 상세 요구사항

**파일: `.github/workflows/contentctl-build.yml`**

```yaml
name: contentctl-build
```

**트리거 조건:**
- `pull_request`: `main`, `master`, `develop` 브랜치 대상
- `push`: 기본 브랜치 (`main` 또는 `master`)에 직접 push 시
- `workflow_dispatch`: 수동 실행 지원

**Job 구성 (단일 Job `build`):**

| Step | 내용 | 상세 |
|------|------|------|
| 1 | Checkout | `actions/checkout@v4` |
| 2 | Setup Python | `actions/setup-python@v5`, python-version: `3.11` |
| 3 | Cache pip | `actions/cache@v4`, key에 `requirements.txt` 해시 포함 |
| 4 | Install dependencies | `pip install --upgrade pip && pip install -r requirements.txt` |
| 5 | contentctl build | `contentctl build` 실행 |
| 6 | Upload build artifact | `actions/upload-artifact@v4`, `output/` 디렉터리 업로드, retention-days: 5 |
| 7 | Build summary | `$GITHUB_STEP_SUMMARY`에 빌드 결과 요약 출력 |

**enrichments 옵션 처리:**
- 기본 빌드에서는 `--enrichments` 사용하지 않음
- 주석으로 enrichments 사용 방법 안내 포함
- 외부 repo clone이 필요한 경우의 step을 주석 처리된 형태로 포함

**에러 처리:**
- build 실패 시 workflow 자체가 실패해야 함
- artifact 업로드 step에는 `if: always()`를 적용하여 실패 시에도 결과물 확보

#### 구현 시 참고해야 할 contentctl CLI 문법

```bash
# 기본 빌드
contentctl build

# enrichment 포함 빌드 (향후 확장용)
contentctl build --enrichments
```

#### 완료 기준

- [ ] `.github/workflows/contentctl-build.yml` 파일이 YAML 문법 오류 없이 작성됨
- [ ] `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4` 사용
- [ ] pip 캐시 적용
- [ ] `$GITHUB_STEP_SUMMARY`에 빌드 결과 출력
- [ ] enrichments는 주석 처리된 옵션으로 제공
- [ ] `if: always()` 전략이 artifact 업로드에 적용됨

#### 커밋 메시지

```
feat: add contentctl build workflow for PR and push triggers
```

---

### Task 2 - Test Workflow + 결과 포맷터

#### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `feature/workflow-test` |
| Worktree | `isolation: worktree` |
| 선행 의존 | Task 0 |
| 후속 의존 | Task 7 (통합) |
| 생성 파일 | `.github/workflows/contentctl-test.yml`, `.github/workflows/format_test_results.py` |

#### 상세 요구사항

##### 파일 1: `.github/workflows/contentctl-test.yml`

```yaml
name: contentctl-test
```

**트리거 조건:**
- `pull_request`: types `[opened, synchronize, reopened]`
  - 대상 브랜치: `main`, `master`, `develop`
- `workflow_dispatch`:
  - inputs:
    - `test_mode`: choice `[changes, all]`, default: `changes`
    - `target_branch`: string, default: `main`

**Job 구성 (단일 Job `test`):**

| Step | 내용 | 상세 |
|------|------|------|
| 1 | Checkout | `actions/checkout@v4`, `fetch-depth: 0` (전체 히스토리 필요, 변경분 비교용) |
| 2 | Fetch base branch | `git fetch origin ${{ github.event.pull_request.base.ref }}` |
| 3 | Setup Python | `actions/setup-python@v5`, python-version: `3.11` |
| 4 | Cache pip | `actions/cache@v4` |
| 5 | Install dependencies | `pip install --upgrade pip && pip install -r requirements.txt` |
| 6 | Run contentctl test | 아래 명령 실행, `id: test`, `continue-on-error: true` |
| 7 | Upload test results | `actions/upload-artifact@v4`, `if: always()` |
| 8 | Format test summary | Python 스크립트로 결과 파싱 후 `$GITHUB_STEP_SUMMARY` 출력, `if: always()` |
| 9 | Check test result | Step 6의 outcome을 확인하여 실패 시 `exit 1`, `if: always()` |

**Step 6 상세 - contentctl test 명령:**

```bash
# PR 이벤트일 때
contentctl test \
  --disable-tqdm \
  --no-enable-integration-testing \
  --post-test-behavior never_pause \
  mode:changes \
  --mode.target-branch "${{ github.event.pull_request.base.ref }}"

# workflow_dispatch일 때 (수동 실행)
contentctl test \
  --disable-tqdm \
  --no-enable-integration-testing \
  --post-test-behavior never_pause \
  mode:${{ github.event.inputs.test_mode }} \
  --mode.target-branch "${{ github.event.inputs.target_branch }}"
```

**주의: CLI 문법 확인 필수**
- `mode:changes`와 `--mode changes`의 차이를 에이전트가 확인할 것
- splunk/security_content의 실제 워크플로에서는 `mode:changes` (콜론 구문)을 사용
- `--mode.target-branch`는 `mode:changes`와 함께 사용하는 서브옵션

**continue-on-error 전략:**
- Step 6 (테스트 실행)에만 `continue-on-error: true` 적용
- 이유: 테스트 실패해도 결과 수집/요약 단계를 실행하기 위함
- Step 9에서 Step 6의 `outcome`을 확인하여 최종 pass/fail 결정

**PR base branch 비교 로직:**
- `github.event.pull_request.base.ref`로 PR의 대상 브랜치 자동 감지
- `fetch-depth: 0`으로 전체 히스토리를 가져와 diff 비교 가능하게 함
- fork PR 제한사항: same-repo PR 중심 설계, fork PR은 제한사항으로 문서화

##### 파일 2: `.github/workflows/format_test_results.py`

**역할:** contentctl test가 생성하는 결과 파일을 파싱하여 GitHub Actions Summary용 마크다운을 생성

**입력:**
- `test_results/` 디렉터리 내 `summary.yml` 또는 관련 결과 파일
- 파일이 없을 경우 "No test results found" 메시지 출력

**출력:**
- `$GITHUB_STEP_SUMMARY`에 쓸 마크다운 문자열을 stdout으로 출력
- 또는 직접 `$GITHUB_STEP_SUMMARY` 파일에 append

**마크다운 포맷:**

```markdown
## 🔍 contentctl Test Results

| Detection | Status | Duration |
|-----------|--------|----------|
| detection_name_1 | ✅ Pass | 12s |
| detection_name_2 | ❌ Fail | 8s |

### Summary
- **Total:** 5
- **Passed:** 4
- **Failed:** 1
```

**구현 요구사항:**
- Python 표준 라이브러리만 사용 (yaml, json, os, sys, pathlib)
- `pyyaml`은 `requirements.txt`에 이미 contentctl 의존성으로 포함되므로 사용 가능
- 결과 파일 경로는 인자 또는 환경 변수로 받을 수 있도록 유연하게 설계
- 결과 파일이 없거나 파싱 실패 시에도 에러 없이 빈 결과 메시지 출력

#### 완료 기준

- [ ] `.github/workflows/contentctl-test.yml`이 YAML 문법 오류 없이 작성됨
- [ ] `fetch-depth: 0` 설정됨
- [ ] `continue-on-error` 전략이 올바르게 적용됨
- [ ] PR 이벤트와 workflow_dispatch 모두 처리됨
- [ ] `format_test_results.py`가 결과 파일 없이도 에러 없이 동작
- [ ] `$GITHUB_STEP_SUMMARY` 출력이 마크다운 테이블 형식
- [ ] Step 9에서 테스트 실패 시 workflow가 최종적으로 실패 처리됨

#### 커밋 메시지

```
feat: add contentctl test workflow with result formatter

- PR-triggered change detection testing
- Manual full test support via workflow_dispatch
- Test result summary in GitHub Actions Summary
```

---

### Task 3 - Setup Documentation

#### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `feature/docs-setup` |
| Worktree | `isolation: worktree` |
| 선행 의존 | Task 0 |
| 후속 의존 | Task 7 (통합) |
| 생성 파일 | `docs/contentctl-cicd-setup.md` |

#### 상세 요구사항

**문서 구조:**

```
# contentctl CI/CD 구축 가이드

## 1. 개요
## 2. 사전 요구사항
## 3. 저장소 준비 (Step by Step)
  ### 3.1 저장소 생성
  ### 3.2 공개 여부 결정
  ### 3.3 기본 브랜치 확인
## 4. GitHub 설정
  ### 4.1 Actions 활성화 확인
  ### 4.2 브랜치 보호 정책
  ### 4.3 Required Checks 설정
## 5. 워크플로 파일 설명
  ### 5.1 contentctl-build.yml
  ### 5.2 contentctl-test.yml
## 6. 비용 관점
  ### 6.1 Public Repository
  ### 6.2 Private Repository
## 7. Secrets / Variables 설정
  ### 7.1 현재 단계 (불필요)
  ### 7.2 향후 통합 테스트 확장 시
## 8. Fork PR 정책
## 9. Dependabot / Actions 버전 관리
## 10. 트러블슈팅
## 11. 사용자 체크리스트
```

**각 섹션별 필수 포함 내용:**

| 섹션 | 필수 포함 내용 |
|------|---------------|
| 개요 | contentctl이 무엇인지, 왜 CI/CD가 필요한지 1-2문단 |
| 사전 요구사항 | GitHub 계정, 저장소, Python 3.11+, contentctl 5.5.16 |
| 저장소 준비 | `dollce` 계정 기준 저장소 생성 절차, 스크린샷 경로 표시 위치 |
| Actions 활성화 | Settings → Actions → General 경로, 허용 정책 설명 |
| 브랜치 보호 | Settings → Branches → Add rule, 체크 항목 명시 |
| Required Checks | `contentctl-build`, `contentctl-test`를 required로 설정하는 방법 |
| 비용 (Public) | GitHub-hosted runner 무료 정책, `ubuntu-latest` 기준 무제한 |
| 비용 (Private) | GitHub Pro 월 3,000분 포함, 예상 사용량 계산 예시 |
| Secrets | 현재 불필요, 향후 `SPLUNK_HOST`, `SPLUNK_USERNAME`, `SPLUNK_PASSWORD`, `SPLUNK_HEC_TOKEN` |
| Fork PR | same-repo PR 중심, fork PR 시 승인 필요 정책 |
| Dependabot | `.github/dependabot.yml` 예시 (GitHub Actions 버전 자동 업데이트) |
| 트러블슈팅 | 흔한 에러 5개 이상과 해결 방법 |
| 체크리스트 | 마크다운 체크박스 목록 |

**문서 작성 원칙:**
- 모든 UI 경로는 `Settings → Actions → General` 형식으로 명시
- 설정값은 코드블록으로 감싸기
- 복사-붙여넣기 가능한 수준의 명령어 포함
- 한국어로 작성

#### 완료 기준

- [ ] `docs/contentctl-cicd-setup.md`가 위 구조를 모두 포함
- [ ] 모든 GitHub UI 경로가 명시됨
- [ ] 비용 관점 설명 포함 (public/private 구분)
- [ ] Secrets 향후 확장 설명 포함
- [ ] 체크리스트 포함
- [ ] 마크다운 문법 오류 없음

#### 커밋 메시지

```
docs: add contentctl CI/CD setup guide
```

---

### Task 4 - Testing Guide Documentation

#### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `feature/docs-testing-guide` |
| Worktree | `isolation: worktree` |
| 선행 의존 | Task 0 |
| 후속 의존 | Task 7 (통합) |
| 생성 파일 | `docs/contentctl-testing-guide.md` |

#### 상세 요구사항

**문서 구조:**

```
# contentctl 탐지 테스트 가이드

## 1. 테스트 개요
  ### 1.1 contentctl test란?
  ### 1.2 --mode changes가 하는 일
  ### 1.3 단위 테스트 vs 통합 테스트
## 2. Detection YAML 작성법
  ### 2.1 필수 필드
  ### 2.2 tests 섹션 구조
  ### 2.3 attack_data 구조
## 3. 테스트 데이터 준비
  ### 3.1 attack_data 소스
  ### 3.2 source/sourcetype 매칭
  ### 3.3 true positive 검증 원칙
## 4. 예제: 첫 번째 Detection 테스트
  ### 4.1 단순 SPL Detection 예시
  ### 4.2 attack_data 연결
  ### 4.3 PR 생성 및 결과 확인
## 5. 현재 구성이 잘하는 것
## 6. 현재 구성의 제한사항
## 7. 테스트 실패 시 디버깅
  ### 7.1 SPL 오류
  ### 7.2 source/sourcetype mismatch
  ### 7.3 attack_data 형식 문제
  ### 7.4 CIM/data model 의존성 문제
## 8. 향후 확장
  ### 8.1 test_servers 연동
  ### 8.2 통합 테스트 전환
  ### 8.3 nightly full test
```

**각 섹션별 필수 포함 내용:**

| 섹션 | 필수 포함 내용 |
|------|---------------|
| --mode changes 설명 | PR의 base branch와 비교하여 변경된 detection만 테스트하는 원리 |
| Detection YAML | 완전한 예시 YAML (metadata + search + tests + attack_data) |
| attack_data | `splunk/attack_data` 레포 참조, URL 형식 설명 |
| source/sourcetype | detection SPL에서 기대하는 값과 attack_data의 값이 일치해야 하는 이유 |
| true positive 원칙 | 테스트 데이터는 SPL이 참이 되도록 설계, 최소 1건 결과 보장 |
| 잘하는 것 | SPL 검증, true positive 확인, 변경분 회귀 테스트, PR 품질 게이트 |
| 제한사항 | ES notable, RBA, data model acceleration, TA/App 재현, 대규모 통합 테스트 |
| CIM/data model | tstats/datamodel 의존 detection은 테스트 환경에서 제약 가능 |
| manual_test | 일부 detection은 수동 테스트가 더 적절한 경우 설명 |
| test_servers 확장 | 향후 `contentctl.yml`에 `test_servers` 섹션 추가하는 방법 |

**Detection YAML 예시 (필수):**

```yaml
name: Suspicious Process Creation
id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
version: 1
date: '2024-01-01'
author: dollce
type: TTP
status: production
description: Detects suspicious process creation events
data_source:
  - Sysmon EventID 1
search: '| tstats count FROM datamodel=Endpoint.Processes
  WHERE Processes.process_name="cmd.exe"
  BY Processes.dest Processes.user Processes.process_name
  | `drop_dm_object_name(Processes)`
  | where count > 0'
how_to_implement: Requires Sysmon data with process creation events
known_false_positives: Legitimate admin activity
references:
  - https://attack.mitre.org/techniques/T1059/
tags:
  analytic_story:
    - Suspicious Command-Line Executions
  asset_type: Endpoint
  confidence: 80
  impact: 60
  mitre_attack_id:
    - T1059
  observable:
    - name: dest
      type: Hostname
      role:
        - Victim
  product:
    - Splunk Enterprise
  risk_score: 48
  security_domain: endpoint
tests:
  - name: True Positive Test
    attack_data:
      - data: https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/...
        source: XmlWinEventLog:Microsoft-Windows-Sysmon/Operational
        sourcetype: xmlwineventlog
```

**또한 가장 단순한 SPL 기반 예시도 포함:**

```yaml
# CIM/datamodel 의존 없는 단순 SPL 예시
search: 'index=main sourcetype="sysmon"
  EventCode=1 process_name="cmd.exe"
  | stats count by dest, user, process_name
  | where count > 0'
```

#### 완료 기준

- [ ] `docs/contentctl-testing-guide.md`가 위 구조를 모두 포함
- [ ] Detection YAML 완전한 예시 2개 이상 (CIM 의존 / 단순 SPL)
- [ ] attack_data 연결 방법 설명
- [ ] 현재 잘하는 것 / 제한사항 명확히 구분
- [ ] 향후 확장 방법 (test_servers, 통합 테스트) 설명
- [ ] 한국어로 작성
- [ ] 마크다운 문법 오류 없음

#### 커밋 메시지

```
docs: add contentctl testing guide with examples
```

---

### Task 5 - Sample Content

#### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `feature/sample-content` |
| Worktree | `isolation: worktree` |
| 선행 의존 | Task 0 |
| 후속 의존 | Task 7 (통합) |
| 생성 파일 | `detections/endpoint/sample_detection.yml`, `stories/sample_story.yml` |

#### 상세 요구사항

##### 파일 1: `detections/endpoint/sample_detection.yml`

**목적:** 사용자가 첫 PR을 만들어 테스트해볼 수 있는 실제 동작하는 샘플 detection

**요구사항:**
- contentctl의 detection 스키마를 완벽히 준수
- 가능하면 `splunk/attack_data`에서 실제로 사용 가능한 데이터를 참조
- 처음에는 CIM/datamodel 의존이 적은 단순한 SPL 사용
- `status: production`으로 설정 (test mode에서 테스트 대상이 되려면)
- `tests` 섹션에 `attack_data`가 올바르게 연결됨

**필수 필드 체크리스트:**
- `name`, `id` (UUID v4), `version`, `date`, `author`
- `type` (TTP, Anomaly, Hunting 등)
- `status: production`
- `description`
- `search` (SPL)
- `data_source`
- `how_to_implement`
- `known_false_positives`
- `references`
- `tags` (analytic_story, asset_type, confidence, impact, mitre_attack_id, observable, product, risk_score, security_domain)
- `tests` (name, attack_data with data URL, source, sourcetype)

**주의:** 에이전트는 `contentctl validate`를 실행하여 YAML이 스키마를 통과하는지 확인해야 함

##### 파일 2: `stories/sample_story.yml`

**목적:** sample detection이 참조하는 analytic story

**필수 필드:**
- `name`, `id`, `version`, `date`, `author`
- `description`
- `narrative`
- `references`
- `tags` (analytic_story, asset_type, product, security_domain, usecase)

#### 완료 기준

- [ ] `detections/endpoint/sample_detection.yml` 생성됨
- [ ] `stories/sample_story.yml` 생성됨
- [ ] detection의 `analytic_story` 태그가 story의 `name`과 일치
- [ ] 모든 필수 필드가 포함됨
- [ ] `contentctl validate` 통과 (가능한 경우 에이전트가 확인)
- [ ] attack_data URL이 현실적이거나, 사용자가 교체해야 함을 주석으로 명시

#### 커밋 메시지

```
feat: add sample detection and story for initial testing
```

---

### Task 6 - README

#### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `feature/readme` |
| Worktree | `isolation: worktree` |
| 선행 의존 | Task 0 |
| 후속 의존 | Task 7 (통합) |
| 생성 파일 | `README.md` |

#### 상세 요구사항

**문서 구조:**

```markdown
# dollce Security Content

## 개요
## 저장소 구조
## 빠른 시작
  ### 사전 요구사항
  ### 로컬 설정
  ### 첫 번째 Detection 추가
  ### PR 생성 및 테스트
## CI/CD 워크플로
  ### Build Workflow
  ### Test Workflow
## 결과 확인 방법
  ### GitHub Actions Summary
  ### Artifact 다운로드
## 문서
## 향후 계획
## 라이선스
```

**각 섹션별 포함 내용:**

| 섹션 | 내용 |
|------|------|
| 개요 | contentctl 기반 Splunk 탐지 콘텐츠 관리 저장소, PR 기반 자동 테스트 |
| 저장소 구조 | 디렉터리 트리 (`detections/`, `stories/`, `macros/` 등) |
| 빠른 시작 | `pip install contentctl`, `contentctl build`, PR 생성까지 5단계 |
| CI/CD | build/test 워크플로 간략 설명, 링크 |
| 결과 확인 | Actions 탭에서 Summary 보는 방법, Artifact 다운로드 방법 |
| 문서 | `docs/` 디렉터리의 문서 링크 |
| 향후 계획 | 통합 테스트, ES 연동, nightly test 등 |

**작성 원칙:**
- 한국어로 작성
- 간결하고 실용적
- 복사-붙여넣기 가능한 명령어 포함
- 배지(badge)는 선택 사항 (Actions status badge 정도)

#### 완료 기준

- [ ] `README.md` 생성됨
- [ ] 저장소 구조가 정확히 반영됨
- [ ] 빠른 시작 가이드가 5단계 이내
- [ ] CI/CD 워크플로 설명 포함
- [ ] `docs/` 문서 링크 포함
- [ ] 마크다운 문법 오류 없음

#### 커밋 메시지

```
docs: add README with quickstart and CI/CD overview
```

---

## Phase 2: Task 7 - 통합 검증 및 Master 커밋

### 메타 정보

| 항목 | 값 |
|------|-----|
| 브랜치 | `master` |
| Worktree | 불필요 (master에서 직접 작업) |
| 선행 의존 | Task 1, 2, 3, 4, 5, 6 모두 완료 |
| 후속 의존 | 없음 (최종 작업) |
| 담당 | 통합 에이전트 |

### 작업 내용

#### 7-1. 각 feature 브랜치를 master에 병합

병합 순서 (충돌 최소화를 위한 권장 순서):

```bash
git checkout master

# 1. 워크플로 파일 (서로 다른 파일이므로 순서 무관)
git merge feature/workflow-build --no-ff -m "merge: workflow-build into master"
git merge feature/workflow-test --no-ff -m "merge: workflow-test into master"

# 2. 샘플 콘텐츠
git merge feature/sample-content --no-ff -m "merge: sample-content into master"

# 3. 문서 (서로 다른 파일이므로 순서 무관)
git merge feature/docs-setup --no-ff -m "merge: docs-setup into master"
git merge feature/docs-testing-guide --no-ff -m "merge: docs-testing-guide into master"

# 4. README (마지막: 다른 파일 참조 가능성)
git merge feature/readme --no-ff -m "merge: readme into master"
```

#### 7-2. 통합 검증

| 검증 항목 | 방법 |
|-----------|------|
| 파일 존재 확인 | 모든 산출물 파일이 master에 존재하는지 확인 |
| YAML 문법 | `python -c "import yaml; yaml.safe_load(open('contentctl.yml'))"` 등 |
| Workflow YAML | `python -c "import yaml; yaml.safe_load(open('.github/workflows/contentctl-build.yml'))"` |
| Python 문법 | `python -m py_compile .github/workflows/format_test_results.py` |
| 마크다운 구조 | 각 .md 파일의 헤더 구조 확인 |
| 디렉터리 구조 | 지시서에 명시된 구조와 일치하는지 확인 |
| 교차 참조 | README에서 docs/ 링크가 유효한지 확인 |
| detection-story 연결 | sample detection의 analytic_story가 sample story의 name과 일치 |

#### 7-3. 최종 정리 커밋 (필요시)

통합 검증에서 발견된 사소한 수정 사항이 있으면 하나의 커밋으로 정리:

```
fix: post-merge integration fixes
```

#### 7-4. Feature 브랜치 정리

```bash
git branch -d feature/workflow-build
git branch -d feature/workflow-test
git branch -d feature/docs-setup
git branch -d feature/docs-testing-guide
git branch -d feature/sample-content
git branch -d feature/readme
```

### 완료 기준

- [ ] 모든 feature 브랜치가 master에 병합됨
- [ ] 병합 충돌 없음
- [ ] 모든 산출물 파일이 master에 존재
- [ ] YAML/Python 문법 오류 없음
- [ ] 교차 참조가 유효함
- [ ] feature 브랜치 정리 완료

---

## 최종 산출물 파일 목록

| 파일 경로 | 담당 Task | 설명 |
|-----------|-----------|------|
| `.gitignore` | Task 0 | Git 무시 패턴 |
| `contentctl.yml` | Task 0 | contentctl 프로젝트 설정 |
| `requirements.txt` | Task 0 | Python 의존성 |
| `.github/workflows/contentctl-build.yml` | Task 1 | Build 워크플로 |
| `.github/workflows/contentctl-test.yml` | Task 2 | Test 워크플로 |
| `.github/workflows/format_test_results.py` | Task 2 | 결과 포맷터 |
| `docs/contentctl-cicd-setup.md` | Task 3 | CI/CD 구축 가이드 |
| `docs/contentctl-testing-guide.md` | Task 4 | 테스트 가이드 |
| `detections/endpoint/sample_detection.yml` | Task 5 | 샘플 detection |
| `stories/sample_story.yml` | Task 5 | 샘플 story |
| `README.md` | Task 6 | 저장소 메인 문서 |

---

## Claude Team 할당 요약

| Task | Agent 이름 | Worktree Branch | 병렬 가능 | 예상 작업 규모 |
|------|-----------|-----------------|-----------|---------------|
| 0 | `base-setup` | master (직접) | - | 소 |
| 1 | `workflow-build` | `feature/workflow-build` | Phase 1 병렬 | 중 |
| 2 | `workflow-test` | `feature/workflow-test` | Phase 1 병렬 | 대 |
| 3 | `docs-setup` | `feature/docs-setup` | Phase 1 병렬 | 대 |
| 4 | `docs-testing` | `feature/docs-testing-guide` | Phase 1 병렬 | 대 |
| 5 | `sample-content` | `feature/sample-content` | Phase 1 병렬 | 중 |
| 6 | `readme` | `feature/readme` | Phase 1 병렬 | 소 |
| 7 | `integrator` | master (직접) | - | 중 |

---

## 실행 순서 요약

```
1. Task 0 실행 (단독)
2. Task 0 완료 확인
3. Task 1, 2, 3, 4, 5, 6 동시 실행 (6개 병렬)
4. 전체 완료 확인
5. Task 7 실행 (단독, 통합)
6. 최종 master 상태 확인
```
