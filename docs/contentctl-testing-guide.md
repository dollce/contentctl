# contentctl 탐지 테스트 가이드

이 문서는 `contentctl`을 사용한 Splunk detection 테스트의 전체 과정을 설명한다.
Detection YAML 작성법, 테스트 데이터 준비, 실행 방법, 디버깅까지 포함한다.

---

## 목차

1. [테스트 개요](#1-테스트-개요)
2. [Detection YAML 작성법](#2-detection-yaml-작성법)
3. [테스트 데이터 준비](#3-테스트-데이터-준비)
4. [예제: Detection 테스트](#4-예제-detection-테스트)
5. [현재 구성이 잘하는 것](#5-현재-구성이-잘하는-것)
6. [현재 구성의 제한사항](#6-현재-구성의-제한사항)
7. [테스트 실패 시 디버깅](#7-테스트-실패-시-디버깅)
8. [향후 확장](#8-향후-확장)

---

## 1. 테스트 개요

### 1.1 contentctl test란?

`contentctl test`는 detection YAML에 정의된 테스트를 자동으로 실행하는 명령이다.
내부적으로 다음 과정을 수행한다:

1. 테스트용 Splunk 컨테이너를 자동으로 시작
2. detection YAML의 `tests.attack_data`에 지정된 데이터를 Splunk에 인덱싱
3. detection의 `search` SPL을 실행
4. 결과가 1건 이상 존재하면 **Pass**, 0건이면 **Fail**
5. 테스트 완료 후 결과를 `test_results/summary.yml`로 출력

CI/CD에서 사용할 때의 기본 명령:

```bash
contentctl test \
  --disable-tqdm \
  --no-enable-integration-testing \
  --post-test-behavior never_pause \
  mode:changes
```

| 옵션 | 설명 |
|------|------|
| `--disable-tqdm` | 진행 바 비활성화 (CI 환경에서 불필요한 출력 제거) |
| `--no-enable-integration-testing` | ES 통합 테스트 비활성화 (현재 단계에서 불필요) |
| `--post-test-behavior never_pause` | 테스트 완료 후 일시정지 없이 즉시 종료 |
| `mode:changes` | 변경된 detection만 테스트 |

### 1.2 --mode changes가 하는 일

`mode:changes`는 PR의 base branch와 현재 브랜치를 비교하여 **변경된 detection 파일만** 테스트한다.

```
main (base branch)
  │
  ├── detections/endpoint/existing_detection.yml  ← 변경 없음 → 테스트 안 함
  │
  └── feature-branch (PR)
       ├── detections/endpoint/existing_detection.yml  ← 변경 없음 → 테스트 안 함
       ├── detections/endpoint/new_detection.yml        ← 새로 추가 → 테스트 대상
       └── detections/endpoint/modified_detection.yml   ← 수정됨 → 테스트 대상
```

**동작 원리:**

1. `git diff`로 base branch와의 변경 파일 목록을 추출
2. `detections/` 디렉터리 하위의 변경된 `.yml` 파일만 필터링
3. 해당 detection들에 대해서만 테스트 실행

**장점:**

- PR마다 빠른 피드백 (전체 테스트 대비 실행 시간 대폭 감소)
- 변경하지 않은 detection의 불필요한 테스트 방지
- GitHub Actions 러너 사용 시간 최소화

base branch를 지정하려면 `--mode.target-branch` 옵션을 사용한다:

```bash
contentctl test \
  mode:changes \
  --mode.target-branch main
```

### 1.3 단위 테스트 vs 통합 테스트

| 구분 | 단위 테스트 (현재) | 통합 테스트 (향후) |
|------|-------------------|-------------------|
| 환경 | contentctl 내장 컨테이너 | 외부 Splunk 서버 (test_servers) |
| 범위 | SPL 실행 + 결과 건수 확인 | ES notable, RBA, 상관 분석 |
| 속도 | 빠름 (detection당 수십 초) | 느림 (환경 구성 포함 수 분) |
| 비용 | GitHub-hosted runner만 필요 | Splunk 라이선스 + 서버 필요 |
| 적용 | `--no-enable-integration-testing` | `--enable-integration-testing` |

**현재 단계에서는 단위 테스트만 사용한다.**
통합 테스트는 [8. 향후 확장](#8-향후-확장) 섹션을 참고한다.

---

## 2. Detection YAML 작성법

### 2.1 필수 필드

모든 detection YAML은 다음 필드를 포함해야 한다:

```yaml
name: Detection Name                          # 탐지 규칙 이름
id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx      # 고유 UUID
version: 1                                     # 버전 (정수)
date: '2024-01-01'                            # 최초 작성일
author: dollce                                 # 작성자
type: TTP                                      # 유형: TTP, Anomaly, Hunting, Correlation
status: production                             # 상태: production, experimental, deprecated
description: 설명 텍스트                         # 탐지 규칙 설명
data_source:                                   # 데이터 소스
  - Sysmon EventID 1
search: 'SPL 쿼리'                              # Splunk SPL 검색 쿼리
how_to_implement: 구현 방법 설명                  # 필수 데이터 소스/TA 설명
known_false_positives: 오탐 가능성 설명           # 알려진 오탐 사례
references:                                     # 참조 URL
  - https://attack.mitre.org/techniques/T1059/
tags:                                           # 메타데이터 태그
  analytic_story:
    - Story Name
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
tests:                                          # 테스트 정의
  - name: True Positive Test
    attack_data:
      - data: https://...
        source: source_name
        sourcetype: sourcetype_name
```

### 2.2 tests 섹션 구조

`tests` 섹션은 detection의 테스트 케이스를 정의한다:

```yaml
tests:
  - name: True Positive Test          # 테스트 이름 (설명적으로 작성)
    attack_data:                       # 테스트에 사용할 데이터 목록
      - data: https://...             # 테스트 데이터 URL
        source: WinEventLog           # Splunk source 값
        sourcetype: WinEventLog       # Splunk sourcetype 값
```

**필드별 설명:**

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | O | 테스트 케이스의 이름. 결과 리포트에 표시됨 |
| `attack_data` | O | 테스트 데이터 배열. 최소 1개 필요 |
| `attack_data[].data` | O | 테스트 데이터 파일의 URL (raw 로그 파일) |
| `attack_data[].source` | O | Splunk에 인덱싱 시 사용할 `source` 값 |
| `attack_data[].sourcetype` | O | Splunk에 인덱싱 시 사용할 `sourcetype` 값 |

**`manual_test` 사용:**

일부 detection은 자동 테스트가 불가능하거나 부적절할 수 있다.
이 경우 `manual_test`를 지정하여 자동 테스트에서 제외할 수 있다:

```yaml
tests:
  - name: True Positive Test
    attack_data:
      - data: https://...
        source: source_name
        sourcetype: sourcetype_name
    manual_test: >
      이 detection은 data model acceleration이 필수이므로
      자동 테스트 환경에서는 검증이 불가합니다.
      운영 환경에서 수동으로 테스트하세요.
```

### 2.3 attack_data 구조

`attack_data`는 테스트 시 Splunk에 인덱싱될 로그 데이터를 지정한다:

```yaml
attack_data:
  - data: https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1059.001/powershell_execution/windows-sysmon.log
    source: XmlWinEventLog:Microsoft-Windows-Sysmon/Operational
    sourcetype: xmlwineventlog
```

**핵심 원칙:**

1. `data` URL은 raw 로그 파일을 직접 가리켜야 한다
2. `source`와 `sourcetype`은 detection SPL에서 참조하는 값과 정확히 일치해야 한다
3. 테스트 데이터는 detection SPL이 **최소 1건 이상의 결과를 반환**하도록 설계되어야 한다

---

## 3. 테스트 데이터 준비

### 3.1 attack_data 소스

테스트 데이터의 주요 출처:

**1. splunk/attack_data 공식 저장소**

Splunk이 제공하는 공식 테스트 데이터 저장소이다.
다양한 MITRE ATT&CK 기법에 대한 실제 로그 샘플이 포함되어 있다.

URL 형식:
```
https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/{TECHNIQUE_ID}/{SCENARIO}/{LOG_FILE}
```

예시:
```
https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1059.001/powershell_execution/windows-sysmon.log
```

디렉터리 구조:
```
splunk/attack_data/
└── datasets/
    ├── attack_techniques/
    │   ├── T1059.001/
    │   │   └── powershell_execution/
    │   │       ├── windows-sysmon.log
    │   │       └── windows-security.log
    │   ├── T1053.005/
    │   │   └── scheduled_task/
    │   │       └── windows-sysmon.log
    │   └── ...
    └── ...
```

**2. 자체 테스트 데이터**

공식 저장소에 적합한 데이터가 없을 경우, 직접 테스트 데이터를 생성할 수 있다:

- 테스트 환경에서 공격 시뮬레이션 실행
- Splunk에서 해당 로그를 `| outputlookup` 또는 export로 추출
- raw 로그 파일로 저장 후 GitHub 저장소에 업로드
- `attack_data[].data`에 해당 파일의 raw URL을 지정

### 3.2 source/sourcetype 매칭

**detection SPL과 테스트 데이터의 `source`/`sourcetype`이 반드시 일치해야 한다.**

이것은 테스트 실패의 가장 흔한 원인 중 하나이다.

| Detection SPL에서 사용하는 값 | attack_data에 지정해야 하는 값 |
|------|------|
| `sourcetype="xmlwineventlog"` | `sourcetype: xmlwineventlog` |
| `source="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"` | `source: XmlWinEventLog:Microsoft-Windows-Sysmon/Operational` |
| `sourcetype="WinEventLog"` | `sourcetype: WinEventLog` |
| `index=main` | 기본 인덱스가 `main`이므로 별도 설정 불필요 |

**확인 방법:**

1. detection의 `search` 필드에서 `sourcetype=`, `source=` 조건을 확인한다
2. `attack_data`의 `source`, `sourcetype`이 동일한지 비교한다
3. CIM/datamodel 기반 detection의 경우, 해당 datamodel이 기대하는 sourcetype을 확인한다

### 3.3 true positive 검증 원칙

테스트의 핵심은 **true positive 검증**이다:

> 테스트 데이터를 Splunk에 인덱싱하고 detection SPL을 실행했을 때,
> **최소 1건 이상의 결과가 반환되어야** 테스트가 Pass이다.

**설계 원칙:**

1. **SPL이 참이 되는 데이터를 준비한다**
   - detection이 `process_name="cmd.exe"`를 찾는다면, 테스트 데이터에 `cmd.exe` 프로세스 생성 이벤트가 포함되어야 한다

2. **최소 1건의 결과를 보장한다**
   - `| where count > 0` 같은 필터가 있다면, 테스트 데이터에 해당 조건을 만족하는 이벤트가 충분히 포함되어야 한다

3. **시간 범위를 고려한다**
   - SPL에 `earliest=-24h` 같은 시간 제한이 있으면, 테스트 데이터의 타임스탬프가 해당 범위 내에 있어야 한다
   - contentctl test는 일반적으로 시간 범위를 `All time`으로 설정하므로 대부분 문제 없다

4. **처음에는 단순 SPL detection부터 시작한다**
   - CIM/datamodel 의존 detection보다 직접 `index`/`sourcetype`을 참조하는 detection이 테스트하기 쉽다
   - tstats/datamodel 기반 detection은 추가 구성이 필요할 수 있다

---

## 4. 예제: Detection 테스트

### 4.1 예제 1: CIM/datamodel 의존 Detection (tstats 사용)

다음은 `tstats`와 `Endpoint.Processes` datamodel을 사용하는 detection의 완전한 예시이다.

**파일: `detections/endpoint/suspicious_cmd_execution_via_tstats.yml`**

```yaml
name: Suspicious Cmd Execution via Tstats
id: b8c5f3e2-7d4a-4f1e-9c6b-2a8d5e0f3c71
version: 1
date: '2024-01-15'
author: dollce
type: TTP
status: production
description: >
  tstats를 사용하여 Endpoint.Processes 데이터모델에서
  cmd.exe 프로세스 실행을 탐지합니다.
  공격자가 명령줄 인터페이스를 통해 악성 명령을 실행하는 행위를 탐지합니다.
data_source:
  - Sysmon EventID 1
search: >
  | tstats count min(_time) as firstTime max(_time) as lastTime
  FROM datamodel=Endpoint.Processes
  WHERE Processes.process_name="cmd.exe"
  BY Processes.dest Processes.user Processes.process_name Processes.parent_process_name
  | `drop_dm_object_name(Processes)`
  | where count > 0
how_to_implement: >
  Sysmon 또는 EDR 데이터가 Endpoint 데이터모델에 매핑되어 있어야 합니다.
  CIM App이 설치되어 있어야 하며, 데이터모델 가속(acceleration)이 활성화되어야
  최적의 성능을 발휘합니다.
known_false_positives: >
  시스템 관리자의 정상적인 cmd.exe 사용, 자동화 스크립트 등에서 오탐이 발생할 수 있습니다.
references:
  - https://attack.mitre.org/techniques/T1059/003/
tags:
  analytic_story:
    - Suspicious Command-Line Executions
  asset_type: Endpoint
  confidence: 70
  impact: 50
  mitre_attack_id:
    - T1059.003
  observable:
    - name: dest
      type: Hostname
      role:
        - Victim
    - name: user
      type: User
      role:
        - Victim
  product:
    - Splunk Enterprise
    - Splunk Enterprise Security
    - Splunk Cloud
  risk_score: 35
  security_domain: endpoint
tests:
  - name: True Positive Test
    attack_data:
      - data: https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1059.001/powershell_execution/windows-sysmon.log
        source: XmlWinEventLog:Microsoft-Windows-Sysmon/Operational
        sourcetype: xmlwineventlog
```

**주의사항:**

- `tstats` + datamodel 기반 detection은 테스트 환경에서 datamodel acceleration이 없으므로 **테스트가 실패할 수 있다**
- contentctl의 내장 테스트 환경은 CIM App을 포함하지만, acceleration 없이는 `tstats`가 결과를 반환하지 않을 수 있다
- 이 경우 `manual_test`를 사용하거나, SPL을 직접 검색 방식으로 수정한 별도의 테스트용 detection을 고려한다

### 4.2 예제 2: 단순 SPL Detection (CIM 비의존)

다음은 CIM/datamodel에 의존하지 않고 직접 `index`/`sourcetype`을 참조하는 detection이다.
**테스트가 가장 쉬운 유형**이므로 처음 시작할 때 권장한다.

**파일: `detections/endpoint/suspicious_cmd_execution_simple.yml`**

```yaml
name: Suspicious Cmd Execution Simple
id: d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f80
version: 1
date: '2024-01-15'
author: dollce
type: TTP
status: production
description: >
  Sysmon 이벤트에서 cmd.exe 프로세스 실행을 직접 탐지합니다.
  CIM 데이터모델에 의존하지 않으며, raw 이벤트를 직접 검색합니다.
data_source:
  - Sysmon EventID 1
search: >
  index=* sourcetype="xmlwineventlog" EventCode=1 process_name="cmd.exe"
  | stats count min(_time) as firstTime max(_time) as lastTime
  by dest user process_name parent_process_name
  | where count > 0
how_to_implement: >
  Sysmon이 설치되어 있고, 프로세스 생성 이벤트(EventCode=1)가
  sourcetype xmlwineventlog으로 수집되어야 합니다.
known_false_positives: >
  시스템 관리자의 정상적인 cmd.exe 사용에서 오탐이 발생할 수 있습니다.
references:
  - https://attack.mitre.org/techniques/T1059/003/
tags:
  analytic_story:
    - Suspicious Command-Line Executions
  asset_type: Endpoint
  confidence: 70
  impact: 50
  mitre_attack_id:
    - T1059.003
  observable:
    - name: dest
      type: Hostname
      role:
        - Victim
    - name: user
      type: User
      role:
        - Victim
  product:
    - Splunk Enterprise
  risk_score: 35
  security_domain: endpoint
tests:
  - name: True Positive Test
    attack_data:
      - data: https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1059.001/powershell_execution/windows-sysmon.log
        source: XmlWinEventLog:Microsoft-Windows-Sysmon/Operational
        sourcetype: xmlwineventlog
```

**이 방식이 권장되는 이유:**

| 항목 | CIM/tstats 방식 | 직접 SPL 방식 |
|------|-----------------|--------------|
| datamodel 필요 | O (acceleration 포함) | X |
| CIM App 필요 | O | X |
| 테스트 환경 호환성 | 낮음 | 높음 |
| 운영 환경 성능 | 높음 (tstats 최적화) | 보통 |
| 첫 테스트 적합성 | 낮음 | **높음** |

### 4.3 PR 생성에서 결과 확인까지

detection YAML을 작성한 후, PR을 통해 자동 테스트를 실행하는 전체 절차이다.

#### Step 1: 브랜치 생성 및 detection 추가

```bash
# 새 브랜치 생성
git checkout -b feature/add-cmd-detection main

# detection 파일 추가
cp your_detection.yml detections/endpoint/suspicious_cmd_execution_simple.yml

# story 파일이 필요한 경우 추가
# (analytic_story에서 참조하는 story가 존재해야 함)

# 커밋
git add detections/endpoint/suspicious_cmd_execution_simple.yml
git commit -m "feat: add suspicious cmd execution detection"

# 원격에 push
git push origin feature/add-cmd-detection
```

#### Step 2: PR 생성

GitHub 웹에서 PR을 생성하거나, CLI를 사용한다:

```bash
gh pr create \
  --title "feat: add suspicious cmd execution detection" \
  --body "새로운 cmd.exe 실행 탐지 규칙을 추가합니다."
```

#### Step 3: 자동 테스트 실행 확인

PR이 생성되면 다음이 자동으로 실행된다:

1. **contentctl-build** 워크플로: YAML 문법 검증 + 빌드
2. **contentctl-test** 워크플로: 변경된 detection에 대한 테스트

GitHub PR 페이지에서 확인할 수 있는 항목:

```
Checks 탭:
  ✅ contentctl-build    — 빌드 성공
  ✅ contentctl-test     — 테스트 통과
  또는
  ❌ contentctl-test     — 테스트 실패 (클릭하여 상세 확인)
```

#### Step 4: 결과 확인

**Actions Summary 확인:**

PR의 Checks 탭에서 워크플로를 클릭하면 Summary 페이지에 테스트 결과가 표시된다:

```
## contentctl Test Results

| Detection | Status | Duration |
|-----------|--------|----------|
| Suspicious Cmd Execution Simple | Pass | 45s |

### Summary
- Total: 1
- Passed: 1
- Failed: 0
```

**Artifact 다운로드:**

Actions 실행 결과 페이지 하단에서 `test-results` artifact를 다운로드할 수 있다.
`summary.yml` 파일에 상세한 테스트 결과가 포함되어 있다.

#### Step 5: 실패 시 대응

테스트가 실패하면:

1. Actions 로그에서 실패 원인 확인
2. `summary.yml` artifact 다운로드하여 상세 분석
3. detection YAML 수정
4. 수정 사항을 같은 브랜치에 push하면 테스트가 자동 재실행

```bash
# detection 수정 후
git add detections/endpoint/suspicious_cmd_execution_simple.yml
git commit -m "fix: correct sourcetype in cmd detection"
git push origin feature/add-cmd-detection
# → PR의 테스트가 자동으로 다시 실행됨
```

---

## 5. 현재 구성이 잘하는 것

### 5.1 Detection SPL 기본 동작 검증

- detection의 SPL이 문법적으로 올바른지 확인
- Splunk에서 실제로 실행 가능한 쿼리인지 검증
- `contentctl build` 단계에서 YAML 스키마 검증도 수행

### 5.2 True Positive 확인

- 테스트 데이터를 인덱싱한 후 SPL을 실행하여 결과가 나오는지 확인
- "이 detection이 실제 공격 데이터에서 탐지를 수행하는가?"를 자동으로 검증
- 결과가 0건이면 실패 → detection 로직 또는 테스트 데이터 수정 필요

### 5.3 변경분 회귀 테스트

- `mode:changes`를 사용하여 변경된 detection만 테스트
- 새로 추가하거나 수정한 detection이 정상 동작하는지 즉시 확인
- 전체 테스트 대비 실행 시간 대폭 감소

### 5.4 PR 품질 게이트

- PR에 대한 자동 테스트 결과가 GitHub Checks로 표시
- branch protection과 연동하면 테스트 통과를 merge 조건으로 설정 가능
- 검증되지 않은 detection이 기본 브랜치에 병합되는 것을 방지

---

## 6. 현재 구성의 제한사항

### 6.1 Splunk Enterprise Security (ES) Notable 검증 불가

`contentctl test`의 단위 테스트 환경에는 ES가 설치되어 있지 않다.
따라서 다음은 검증할 수 없다:

- Notable event 생성 여부
- Notable의 필드 매핑 정확성
- Investigation 워크플로 동작

### 6.2 Risk-Based Alerting (RBA) 검증 불가

RBA는 ES의 기능이므로 단위 테스트 환경에서 검증할 수 없다:

- Risk event 생성 여부
- risk_score 적용 확인
- Risk incident 생성 여부

### 6.3 Data Model Acceleration 재현 불가

테스트 환경에서는 data model acceleration이 비활성화되어 있다:

- `tstats` 기반 detection은 acceleration 없이 결과를 반환하지 않을 수 있다
- `| datamodel` 명령도 acceleration이 없으면 동작이 다를 수 있다
- **대안:** 직접 `index`/`sourcetype` 기반 SPL로 테스트하거나, `manual_test`로 표시

### 6.4 운영용 TA/App/Lookup/Macros 재현 한계

- 운영 환경의 모든 Technology Add-on (TA)이 테스트 환경에 설치되지 않는다
- 커스텀 lookup이나 macros가 테스트 환경에 없으면 참조 시 오류 발생
- 매크로를 사용하는 detection은 해당 매크로가 저장소의 `macros/` 디렉터리에 정의되어 있어야 한다

### 6.5 manual_test가 필요한 경우

다음과 같은 detection은 `manual_test`로 표시하는 것이 적절하다:

- ES Correlation Search 기반 detection
- 여러 데이터 소스를 조합하는 복잡한 detection
- data model acceleration이 필수인 detection
- 외부 lookup이나 KV Store에 의존하는 detection
- 실시간 검색(real-time search) 기반 detection

```yaml
tests:
  - name: True Positive Test
    attack_data:
      - data: https://...
        source: source_name
        sourcetype: sourcetype_name
    manual_test: >
      이 detection은 ES Correlation Search와 data model acceleration에
      의존하므로 자동 테스트 환경에서 검증이 불가합니다.
      운영 환경 또는 ES가 설치된 테스트 환경에서 수동 검증이 필요합니다.
```

---

## 7. 테스트 실패 시 디버깅

### 7.1 SPL 오류

**증상:** Actions 로그에 SPL 문법 오류 메시지가 표시된다.

**확인 사항:**

```
- SPL 문법이 올바른지 확인 (괄호, 파이프, 따옴표 등)
- Splunk에서 직접 SPL을 실행하여 동작 확인
- 매크로 참조가 있다면 macros/ 디렉터리에 정의되어 있는지 확인
- lookup 참조가 있다면 lookups/ 디렉터리에 파일이 있는지 확인
```

**흔한 오류 예시:**

| 오류 | 원인 | 해결 |
|------|------|------|
| `Unknown search command 'tstats'` | SA-Utils App 미설치 | 직접 SPL 방식으로 변경하거나 manual_test 사용 |
| `Unknown search command 'datamodel'` | CIM App 미설치 | 직접 SPL 방식으로 변경하거나 manual_test 사용 |
| `Search syntax error` | SPL 문법 오류 | SPL을 Splunk 검색창에서 직접 테스트 |
| `Macro 'xxx' not found` | 매크로 미정의 | macros/ 디렉터리에 매크로 YAML 추가 |

### 7.2 source/sourcetype mismatch

**증상:** 테스트가 실행되지만 결과가 0건이다 (SPL은 정상이지만 데이터를 찾지 못함).

**확인 사항:**

1. detection SPL의 `sourcetype`과 `attack_data`의 `sourcetype`이 일치하는지 확인
2. detection SPL의 `source`와 `attack_data`의 `source`가 일치하는지 확인
3. 대소문자가 정확히 일치하는지 확인

**디버깅 예시:**

```yaml
# detection SPL
search: 'sourcetype="XmlWinEventLog" ...'

# attack_data - 잘못된 예 (대소문자 불일치)
attack_data:
  - sourcetype: xmlwineventlog    # ← "XmlWinEventLog"와 불일치!

# attack_data - 올바른 예
attack_data:
  - sourcetype: XmlWinEventLog    # ← SPL과 일치
```

> **팁:** Splunk에서 `sourcetype`은 대소문자를 구분한다.
> detection SPL에서 사용하는 값과 정확히 동일하게 지정해야 한다.

### 7.3 attack_data 형식 문제

**증상:** 데이터 인덱싱 단계에서 오류가 발생하거나, 인덱싱은 되지만 필드 추출이 안 된다.

**확인 사항:**

1. `data` URL이 유효하고 접근 가능한지 확인
2. 파일이 Splunk이 파싱할 수 있는 형식인지 확인 (raw log, JSON, XML 등)
3. URL이 raw 파일을 직접 가리키는지 확인 (GitHub의 경우 `raw.githubusercontent.com` 사용)

**URL 형식 확인:**

```yaml
# 올바른 예 - raw 콘텐츠 URL
data: https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/...

# 잘못된 예 - GitHub 웹 페이지 URL
data: https://github.com/splunk/attack_data/blob/master/datasets/...
```

### 7.4 CIM/data model 의존성 문제

**증상:** `tstats` 또는 `datamodel` 명령을 사용하는 detection이 결과를 반환하지 않는다.

**원인:** 테스트 환경에서 data model acceleration이 비활성화되어 있다.

**해결 방법:**

| 방법 | 설명 |
|------|------|
| 직접 SPL로 변환 | `tstats`를 직접 `index`/`sourcetype` 검색으로 변경하여 테스트 |
| `manual_test` 사용 | 자동 테스트 대상에서 제외하고 수동 검증 |
| 테스트용 SPL 분리 | 운영용은 `tstats`, 테스트는 직접 SPL로 별도 유지 (비권장) |

**권장 접근법:**

CIM/datamodel 의존 detection을 처음 테스트할 때는 다음 순서를 따른다:

1. 먼저 직접 SPL 방식으로 detection을 작성하고 테스트를 통과시킨다
2. 테스트가 안정적으로 통과하면, 운영 환경용으로 `tstats` 버전을 작성한다
3. `tstats` 버전에는 필요 시 `manual_test`를 설정한다

---

## 8. 향후 확장

### 8.1 test_servers 연동

`contentctl.yml`에 `test_servers` 섹션을 추가하면 외부 Splunk 서버에서 테스트를 실행할 수 있다:

```yaml
# contentctl.yml - 향후 확장 예시
title: dollce_security_content
version: 1.0.0
description: Custom security content for Splunk - managed by contentctl
prefix: DOLLCE

build:
  build_app: true
  build_api: false
  path_root: "."

test:
  test_servers:
    - address: https://splunk-test.example.com:8089
      username: admin
      password: $SPLUNK_PASSWORD
      hec_token: $SPLUNK_HEC_TOKEN
```

**필요 사항:**

- Splunk Enterprise 테스트 서버 (라이선스 필요)
- GitHub Secrets에 자격 증명 등록:
  - `SPLUNK_HOST`: Splunk 서버 주소
  - `SPLUNK_USERNAME`: 관리자 계정
  - `SPLUNK_PASSWORD`: 관리자 비밀번호
  - `SPLUNK_HEC_TOKEN`: HTTP Event Collector 토큰

**GitHub Secrets 등록 방법:**

1. `Settings → Secrets and variables → Actions` 이동
2. `New repository secret` 클릭
3. 각 시크릿을 등록

### 8.2 통합 테스트 전환

외부 Splunk 서버가 준비되면 통합 테스트로 전환할 수 있다:

```bash
# 통합 테스트 명령 (test_servers 필요)
contentctl test \
  --enable-integration-testing \
  --disable-tqdm \
  --post-test-behavior never_pause \
  mode:changes
```

통합 테스트에서 추가로 검증할 수 있는 항목:

- ES Notable event 생성
- Risk event 생성 및 risk_score 적용
- Data model acceleration 환경에서의 `tstats` 동작
- 운영 환경과 동일한 TA/App 구성에서의 동작

### 8.3 Nightly Full Test

`workflow_dispatch`와 `schedule` 트리거를 조합하여 전체 detection을 정기적으로 테스트할 수 있다:

```yaml
# .github/workflows/contentctl-test-nightly.yml (향후 확장 예시)
name: contentctl-test-nightly

on:
  schedule:
    - cron: '0 2 * * *'  # 매일 UTC 02:00 (KST 11:00)
  workflow_dispatch:
    inputs:
      test_mode:
        type: choice
        options:
          - all
          - changes
        default: all

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run full test
        run: |
          contentctl test \
            --disable-tqdm \
            --no-enable-integration-testing \
            --post-test-behavior never_pause \
            mode:all

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: nightly-test-results
          path: test_results/
          retention-days: 30
```

**Nightly full test의 장점:**

- 모든 detection의 정기적 회귀 테스트
- attack_data URL 가용성 확인
- contentctl 버전 업데이트 시 호환성 확인
- 전체 테스트 현황 파악

**비용 고려:**

- detection 수가 많으면 실행 시간이 길어질 수 있다
- public repo: 무료 (GitHub-hosted runner 무제한)
- private repo: 월 포함 시간 내에서 관리 필요

---

## 부록: 빠른 참조

### Detection YAML 최소 템플릿

```yaml
name: YOUR_DETECTION_NAME
id: 00000000-0000-0000-0000-000000000000   # uuidgen으로 생성
version: 1
date: 'YYYY-MM-DD'
author: dollce
type: TTP
status: production
description: 탐지 설명
data_source:
  - YOUR_DATA_SOURCE
search: >
  index=* sourcetype="YOUR_SOURCETYPE"
  YOUR_SEARCH_LOGIC
  | stats count by field1 field2
  | where count > 0
how_to_implement: 구현 방법
known_false_positives: 오탐 가능성
references:
  - https://attack.mitre.org/techniques/TXXXX/
tags:
  analytic_story:
    - YOUR_STORY_NAME
  asset_type: Endpoint
  confidence: 50
  impact: 50
  mitre_attack_id:
    - T0000
  observable:
    - name: dest
      type: Hostname
      role:
        - Victim
  product:
    - Splunk Enterprise
  risk_score: 25
  security_domain: endpoint
tests:
  - name: True Positive Test
    attack_data:
      - data: https://YOUR_TEST_DATA_URL
        source: YOUR_SOURCE
        sourcetype: YOUR_SOURCETYPE
```

### 자주 사용하는 sourcetype 매핑

| 데이터 소스 | source | sourcetype |
|------------|--------|------------|
| Sysmon (XML) | `XmlWinEventLog:Microsoft-Windows-Sysmon/Operational` | `xmlwineventlog` |
| Windows Security | `WinEventLog:Security` | `WinEventLog` |
| Windows PowerShell | `WinEventLog:Microsoft-Windows-PowerShell/Operational` | `WinEventLog` |
| Linux Syslog | `/var/log/syslog` | `syslog` |
| Linux Audit | `/var/log/audit/audit.log` | `linux:audit` |
| AWS CloudTrail | `aws:cloudtrail` | `aws:cloudtrail` |

### contentctl test 명령 옵션 요약

```bash
# 변경분만 테스트 (PR용)
contentctl test --disable-tqdm --no-enable-integration-testing --post-test-behavior never_pause mode:changes --mode.target-branch main

# 전체 테스트
contentctl test --disable-tqdm --no-enable-integration-testing --post-test-behavior never_pause mode:all

# 통합 테스트 (test_servers 필요)
contentctl test --disable-tqdm --enable-integration-testing --post-test-behavior never_pause mode:changes
```
