# contentctl CI/CD 구축 가이드

## 1. 개요

`contentctl`은 Splunk에서 공식 제공하는 보안 탐지 콘텐츠 관리 도구이다. Detection SPL의 작성, 검증, 빌드, 테스트를 CLI 기반으로 수행할 수 있으며, Splunk의 `security_content` 저장소에서도 동일한 도구를 사용하여 CI/CD를 운영하고 있다.

이 가이드는 `contentctl` 기반 GitHub Actions CI/CD를 처음부터 구축하기 위한 단계별 설정 문서이다. PR 단위로 변경된 detection만 자동 빌드/테스트하여 품질을 보장하고, 실패 시 빠르게 피드백을 제공하는 것을 목표로 한다.

**이 CI/CD 구성이 해결하는 문제:**

- Detection SPL이 문법적으로 올바른지 자동 검증
- 테스트 데이터(`attack_data`)를 통해 true positive가 발생하는지 확인
- PR마다 변경된 detection만 회귀 테스트 수행
- 빌드/테스트 결과를 GitHub Actions Summary와 artifact로 보존

---

## 2. 사전 요구사항

| 항목 | 요구사항 | 비고 |
|------|---------|------|
| GitHub 계정 | 활성화된 계정 | GitHub Pro 권장 (private repo 사용 시) |
| 저장소 | contentctl 프로젝트 저장소 | public 권장 (무료 무제한 실행) |
| Python | 3.11 이상 | 로컬 개발 시 필요, CI에서는 자동 설치 |
| contentctl | 5.5.16 | `pip install contentctl==5.5.16` |
| Git | 최신 버전 | 로컬 개발 환경 |

**로컬 환경 확인 명령:**

```bash
# Python 버전 확인
python3 --version
# Python 3.11.x 이상이어야 함

# contentctl 설치
pip install contentctl==5.5.16

# 설치 확인
contentctl --version
```

---

## 3. 저장소 준비 (Step by Step)

### 3.1 저장소 생성

1. GitHub에 로그인한다 (`dollce` 계정 기준).
2. 우측 상단 `+` → `New repository` 클릭
3. 저장소 이름 입력 (예: `security_content`, `contentctl_detections`)
4. 저장소 설명 입력 (예: `Custom security content for Splunk - managed by contentctl`)
5. `Create repository` 클릭

### 3.2 공개 여부 결정

| 구분 | Public | Private |
|------|--------|---------|
| GitHub Actions 비용 | **무료 무제한** | Pro 기준 월 3,000분 |
| 추천 여부 | **권장** | 비용 관리 필요 |
| 외부 노출 | 탐지 룰이 공개됨 | 탐지 룰 비공개 |

> **권장:** 탐지 콘텐츠가 민감하지 않다면 **Public** 저장소를 권장한다. GitHub Actions 실행 시간이 무제한 무료이며, 커뮤니티 기여도 받을 수 있다.

### 3.3 기본 브랜치 확인

저장소의 기본 브랜치가 `main` 또는 `master`인지 확인한다.

`Settings → General` → **Default branch** 섹션에서 확인 가능하다.

> 이 프로젝트의 워크플로는 `main`, `master`, `develop` 브랜치를 모두 트리거 대상으로 포함하므로, 어떤 이름을 사용해도 무방하다.

---

## 4. GitHub 설정

### 4.1 Actions 활성화 확인

1. 저장소 페이지에서 `Settings → Actions → General` 로 이동
2. **Actions permissions** 섹션에서 아래 설정을 확인한다:

| 설정 항목 | 권장 값 | 설명 |
|-----------|---------|------|
| Actions permissions | `Allow all actions and reusable workflows` | 모든 Actions 허용 |
| Workflow permissions | `Read and write permissions` | 워크플로가 저장소에 쓰기 가능 |
| Allow GitHub Actions to create and approve pull requests | 체크 해제 | 불필요 |

> **참고:** 새로 생성한 저장소는 기본적으로 Actions가 활성화되어 있다. 조직(Organization) 저장소의 경우 조직 관리자가 별도로 허용해야 할 수 있다.

### 4.2 브랜치 보호 정책

기본 브랜치에 보호 규칙을 설정하여 검증되지 않은 코드가 병합되지 않도록 한다.

1. `Settings → Branches` 로 이동
2. `Add branch protection rule` 클릭 (또는 `Add classic branch protection rule`)
3. **Branch name pattern** 에 `main` (또는 `master`) 입력
4. 아래 항목을 체크한다:

| 설정 항목 | 체크 여부 | 설명 |
|-----------|----------|------|
| Require a pull request before merging | **체크** | 직접 push 방지 |
| Require status checks to pass before merging | **체크** | CI 통과 필수 |
| Require branches to be up to date before merging | 선택 | 최신 base 기준 테스트 보장 |
| Do not allow bypassing the above settings | 선택 | 관리자도 규칙 준수 |

5. `Save changes` 클릭

### 4.3 Required Checks 설정

브랜치 보호 규칙에서 **Require status checks to pass before merging**을 활성화한 후, 필수 체크를 추가한다.

1. `Settings → Branches` → 보호 규칙 편집
2. **Status checks that are required** 섹션에서 검색
3. 아래 체크를 추가한다:

| Check 이름 | 워크플로 파일 | 역할 |
|------------|-------------|------|
| `build` | `contentctl-build.yml` | 빌드 성공 여부 |
| `test` | `contentctl-test.yml` | 테스트 통과 여부 |

> **주의:** Required check를 추가하려면 해당 워크플로가 최소 1회 이상 실행된 이력이 있어야 한다. 워크플로 파일을 push한 후 PR을 하나 생성하여 실행 이력을 만든 다음 설정한다.

**설정 순서:**
1. 워크플로 파일을 저장소에 push
2. 테스트 PR을 생성하여 워크플로 실행
3. `Settings → Branches` 에서 required check 추가
4. 이후 모든 PR에서 빌드/테스트 통과가 필수

---

## 5. 워크플로 파일 설명

이 프로젝트는 빌드와 테스트를 분리한 2개의 워크플로를 사용한다.

### 5.1 contentctl-build.yml

**파일 경로:** `.github/workflows/contentctl-build.yml`

**역할:** contentctl 프로젝트를 빌드하여 Splunk App 패키지를 생성한다.

**트리거 조건:**

| 이벤트 | 대상 브랜치 | 설명 |
|--------|-----------|------|
| `pull_request` | `main`, `master`, `develop` | PR 생성/업데이트 시 |
| `push` | `main`, `master`, `develop` | 직접 push 시 |
| `workflow_dispatch` | - | 수동 실행 |

**주요 Step:**

| Step | 이름 | 설명 |
|------|------|------|
| 1 | Checkout repository | `actions/checkout@v4`로 소스 체크아웃 |
| 2 | Setup Python | `actions/setup-python@v5`로 Python 3.11 설치 |
| 3 | Cache pip dependencies | `actions/cache@v4`로 pip 캐시 적용 |
| 4 | Install dependencies | `pip install -r requirements.txt` |
| 5 | Run contentctl build | `contentctl build` 실행 |
| 6 | Upload build artifact | 빌드 결과물(`output/`)을 artifact로 업로드 (5일 보존) |
| 7 | Build summary | `$GITHUB_STEP_SUMMARY`에 빌드 결과 출력 |

**동시 실행 제어:**

```yaml
concurrency:
  group: contentctl-build-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

같은 PR에서 새 커밋이 push되면 이전 실행을 자동 취소하여 리소스를 절약한다.

### 5.2 contentctl-test.yml

**파일 경로:** `.github/workflows/contentctl-test.yml`

**역할:** 변경된 detection에 대해 contentctl 테스트를 실행하고 결과를 요약한다.

**트리거 조건:**

| 이벤트 | 조건 | 설명 |
|--------|------|------|
| `pull_request` | `opened`, `synchronize`, `reopened` | PR 이벤트 시 |
| `workflow_dispatch` | `test_mode`, `target_branch` 입력 | 수동 실행 |

**핵심 테스트 명령:**

```bash
# PR 이벤트: 변경된 detection만 테스트
contentctl test \
  --disable-tqdm \
  --no-enable-integration-testing \
  --post-test-behavior never_pause \
  mode:changes \
  --mode.target-branch "${{ github.event.pull_request.base.ref }}"

# 수동 실행: 선택한 모드로 테스트
contentctl test \
  --disable-tqdm \
  --no-enable-integration-testing \
  --post-test-behavior never_pause \
  mode:${{ github.event.inputs.test_mode }} \
  --mode.target-branch "${{ github.event.inputs.target_branch }}"
```

**주요 옵션 설명:**

| 옵션 | 설명 |
|------|------|
| `--disable-tqdm` | CI 환경에서 진행바 비활성화 |
| `--no-enable-integration-testing` | 통합 테스트 비활성화 (Splunk 서버 불필요) |
| `--post-test-behavior never_pause` | 테스트 후 즉시 종료 |
| `mode:changes` | PR 기준 변경된 detection만 테스트 |
| `--mode.target-branch` | 비교 기준 브랜치 지정 |

**continue-on-error 전략:**

테스트 step에는 `continue-on-error: true`가 적용되어 있다. 이는 테스트가 실패해도 결과 수집 및 요약 단계가 실행되도록 하기 위함이다. 최종 pass/fail은 별도 step에서 테스트 outcome을 확인하여 결정한다.

---

## 6. 비용 관점

### 6.1 Public Repository

| 항목 | 값 |
|------|-----|
| GitHub Actions 실행 | **무료 무제한** |
| 러너 | `ubuntu-latest` (GitHub-hosted) |
| 스토리지 (Artifacts) | 무료 (500 MB 기본 포함) |

Public 저장소에서는 GitHub-hosted runner 사용이 완전히 무료이므로 비용 걱정 없이 사용할 수 있다.

### 6.2 Private Repository

| 항목 | 값 |
|------|-----|
| GitHub Pro 포함량 | **월 3,000분** |
| 러너 | `ubuntu-latest` (1배수 소비) |
| 초과 시 과금 | $0.008/분 |

**예상 사용량 계산:**

| 항목 | 예상 시간 | 비고 |
|------|----------|------|
| Build 워크플로 1회 | 약 2~3분 | pip 캐시 적용 시 |
| Test 워크플로 1회 | 약 3~5분 | detection 수에 따라 변동 |
| PR 1개당 총 소비 | 약 5~8분 | build + test |
| 월간 PR 50개 가정 | 약 250~400분 | 3,000분 중 약 8~13% |

> **결론:** Private 저장소에서도 일반적인 사용 패턴이라면 월 포함량의 15% 미만을 사용하므로 추가 비용이 발생하지 않는다.

**비용 절감 팁:**

- `concurrency` 설정으로 불필요한 중복 실행 방지 (이미 적용됨)
- `mode:changes`로 변경된 detection만 테스트 (이미 적용됨)
- artifact `retention-days: 5`로 스토리지 최소화 (이미 적용됨)
- 불필요한 push 트리거 최소화

---

## 7. Secrets / Variables 설정

### 7.1 현재 단계 (불필요)

현재 구성에서는 Secrets나 Variables 설정이 **필요하지 않다.**

- `contentctl build`는 외부 인증 없이 실행 가능
- `contentctl test --no-enable-integration-testing`은 Splunk 서버 연결 없이 실행
- 모든 테스트 데이터는 공개 URL에서 다운로드

### 7.2 향후 통합 테스트 확장 시

Splunk 서버를 사용한 통합 테스트(`--enable-integration-testing`)로 확장할 경우, 아래 Secrets를 설정해야 한다.

`Settings → Secrets and variables → Actions → New repository secret` 에서 추가:

| Secret 이름 | 용도 | 예시 값 |
|-------------|------|---------|
| `SPLUNK_HOST` | Splunk 서버 주소 | `splunk.example.com` |
| `SPLUNK_USERNAME` | Splunk 관리자 계정 | `admin` |
| `SPLUNK_PASSWORD` | Splunk 관리자 비밀번호 | `changeme` |
| `SPLUNK_HEC_TOKEN` | HTTP Event Collector 토큰 | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

**워크플로에서 사용 예시:**

```yaml
- name: Run contentctl test (integration)
  env:
    SPLUNK_HOST: ${{ secrets.SPLUNK_HOST }}
    SPLUNK_USERNAME: ${{ secrets.SPLUNK_USERNAME }}
    SPLUNK_PASSWORD: ${{ secrets.SPLUNK_PASSWORD }}
    SPLUNK_HEC_TOKEN: ${{ secrets.SPLUNK_HEC_TOKEN }}
  run: |
    contentctl test \
      --enable-integration-testing \
      --post-test-behavior never_pause \
      mode:changes
```

> **보안 주의:** Secrets는 fork PR의 워크플로에서는 접근할 수 없다. 이는 GitHub의 보안 정책이며, 통합 테스트는 same-repo PR에서만 실행 가능하다.

---

## 8. Fork PR 정책

이 CI/CD 구성은 **same-repo PR**(같은 저장소 내에서 브랜치를 만들어 PR을 생성하는 방식)을 중심으로 설계되었다.

### Fork PR의 제한사항

| 항목 | Same-repo PR | Fork PR |
|------|-------------|---------|
| Secrets 접근 | 가능 | **불가** |
| 워크플로 실행 | 자동 | 초회 승인 필요 |
| `GITHUB_TOKEN` 권한 | Read/Write | **Read-only** |
| 권장 여부 | **권장** | 제한적 사용 |

### Fork PR 승인 설정

외부 기여자의 Fork PR 워크플로 실행을 관리하려면:

1. `Settings → Actions → General` 로 이동
2. **Fork pull request workflows from outside collaborators** 섹션에서 설정:
   - `Require approval for first-time contributors` (권장)
   - 또는 `Require approval for all outside collaborators`

> **권장 운영 방식:** 소규모 팀이라면 동일 저장소에서 브랜치를 생성하여 PR을 만드는 방식을 사용한다. Fork PR은 오픈소스 기여용으로만 허용한다.

---

## 9. Dependabot / Actions 버전 관리

GitHub Actions에서 사용하는 action들(`actions/checkout`, `actions/setup-python` 등)의 버전을 자동으로 업데이트하려면 Dependabot을 설정한다.

### Dependabot 설정 파일

아래 파일을 저장소에 추가한다:

**파일 경로:** `.github/dependabot.yml`

```yaml
version: 2
updates:
  # GitHub Actions 버전 자동 업데이트
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "chore"
      include: "scope"

  # Python 패키지 업데이트 (pip)
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "python"
    commit-message:
      prefix: "chore"
      include: "scope"
```

**동작 방식:**

- 매주 월요일에 의존성 업데이트를 확인
- 업데이트가 있으면 자동으로 PR 생성
- `dependencies` 라벨이 자동 부여되어 구분 용이
- GitHub Actions와 Python 패키지를 각각 관리

> **참고:** Dependabot이 생성하는 PR에도 브랜치 보호 규칙이 적용되므로, CI가 통과해야만 병합할 수 있다.

---

## 10. 트러블슈팅

### 10.1 `contentctl build` 실패: `contentctl.yml not found`

**증상:**

```
Error: contentctl.yml not found in the root directory
```

**원인:** 저장소 루트에 `contentctl.yml` 파일이 없거나 파일명이 다르다.

**해결:**

```bash
# 파일 존재 확인
ls -la contentctl.yml

# 파일이 없으면 생성
cat > contentctl.yml << 'EOF'
title: dollce_security_content
version: 1.0.0
description: Custom security content for Splunk - managed by contentctl
prefix: DOLLCE

build:
  build_app: true
  build_api: false
  path_root: "."
EOF
```

### 10.2 Python 버전 오류

**증상:**

```
Error: Version 3.11 with arch x64 not found
```

**원인:** `actions/setup-python` 에서 지정한 Python 버전을 찾을 수 없다.

**해결:** 워크플로 파일에서 Python 버전을 확인한다:

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.11"  # 따옴표로 감싸야 함 (YAML에서 3.11 → 3.1 변환 방지)
```

### 10.3 pip 캐시 관련 오류

**증상:**

```
Warning: Path Validation Error: Path(s) specified in the action for caching do(es) not exist
```

**원인:** 첫 실행 시 캐시가 없어 발생하는 경고이다.

**해결:** 이 경고는 무시해도 된다. 첫 실행 후 캐시가 생성되면 이후 실행에서는 발생하지 않는다.

### 10.4 Required check가 검색되지 않음

**증상:** `Settings → Branches` 에서 required check를 추가하려 하지만 `build` 또는 `test`가 목록에 나타나지 않는다.

**원인:** 해당 워크플로가 한 번도 실행된 적이 없다.

**해결:**

1. 워크플로 파일이 기본 브랜치에 존재하는지 확인
2. 테스트 PR을 생성하여 워크플로를 1회 실행
3. 실행 완료 후 다시 required check 설정 시도

### 10.5 `contentctl test` 실패: `mode:changes` 관련 오류

**증상:**

```
Error: No changes detected or invalid target branch
```

**원인:** `fetch-depth` 설정이 누락되어 Git 히스토리가 부족하다.

**해결:** 워크플로의 checkout step에 `fetch-depth: 0`이 설정되어 있는지 확인한다:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # 전체 히스토리 필요
```

### 10.6 Artifact 업로드 실패

**증상:**

```
Error: No files were found with the provided path: output/
```

**원인:** `contentctl build`가 실패하여 `output/` 디렉터리가 생성되지 않았다.

**해결:** 이 에러 자체는 빌드 실패의 부수 효과이다. 빌드 실패의 근본 원인(SPL 문법 오류, YAML 포맷 오류 등)을 먼저 해결한다. artifact 업로드 step에는 `if: always()`가 적용되어 있으므로 빌드 실패 시에도 실행을 시도하지만, `output/`이 없으면 이 경고가 발생한다.

### 10.7 워크플로가 트리거되지 않음

**증상:** PR을 생성했는데 워크플로가 실행되지 않는다.

**원인:** 워크플로 파일이 기본 브랜치에 없거나, 트리거 조건이 맞지 않는다.

**해결:**

1. `.github/workflows/` 디렉터리의 워크플로 파일이 기본 브랜치에 존재하는지 확인
2. PR의 대상 브랜치가 워크플로의 `branches` 목록에 포함되어 있는지 확인
3. `Settings → Actions → General` 에서 Actions가 활성화되어 있는지 확인
4. 저장소의 `Actions` 탭에서 워크플로 실행 이력 확인

### 10.8 `contentctl` 설치 실패

**증상:**

```
ERROR: Could not find a version that satisfies the requirement contentctl==5.5.16
```

**원인:** Python 버전이 호환되지 않거나, PyPI 네트워크 문제이다.

**해결:**

```bash
# Python 버전 확인 (3.11 이상 필요)
python3 --version

# pip 업그레이드 후 재설치
pip install --upgrade pip
pip install contentctl==5.5.16
```

---

## 11. 사용자 체크리스트

아래 항목을 순서대로 완료하여 CI/CD 구축을 마무리한다.

### 저장소 준비

- [ ] GitHub 저장소 생성 완료
- [ ] 공개/비공개 여부 결정
- [ ] 기본 브랜치 이름 확인 (`main` 또는 `master`)

### 필수 파일 확인

- [ ] `contentctl.yml` 이 저장소 루트에 존재
- [ ] `requirements.txt` 에 `contentctl==5.5.16` 포함
- [ ] `.gitignore` 설정 완료
- [ ] 콘텐츠 디렉터리 생성 (`detections/`, `stories/`, `macros/`, `lookups/`)

### 워크플로 파일 확인

- [ ] `.github/workflows/contentctl-build.yml` 존재
- [ ] `.github/workflows/contentctl-test.yml` 존재
- [ ] 테스트 PR 생성하여 워크플로 정상 실행 확인

### GitHub 설정

- [ ] `Settings → Actions → General` 에서 Actions 활성화 확인
- [ ] `Settings → Branches` 에서 브랜치 보호 규칙 추가
- [ ] Required checks에 `build`, `test` 추가

### 선택 사항

- [ ] `.github/dependabot.yml` 추가 (Actions 버전 자동 업데이트)
- [ ] Fork PR 승인 정책 설정 (`Settings → Actions → General`)
- [ ] 팀원에게 CI/CD 사용 방법 공유

### 검증

- [ ] 새 detection 추가 후 PR 생성 시 빌드/테스트 자동 실행 확인
- [ ] 테스트 실패 시 PR 병합 차단 확인
- [ ] GitHub Actions Summary에 결과 표시 확인
- [ ] Artifact에 빌드 결과물 / 테스트 결과 저장 확인
