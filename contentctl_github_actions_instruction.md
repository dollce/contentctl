# GitHub Actions 기반 `contentctl` 탐지 테스트 구축 지시서

## 목적

내 GitHub 계정(`dollce`)의 저장소에 `contentctl` 기반 CI/CD를 구축하여 아래 목적을 달성한다.

### 현재 목표
- detection SPL 자체가 정상 동작하는지 검증
- 테스트 데이터(`attack_data`)로 true positive가 발생하는지 검증
- 변경된 detection만 자동 회귀 테스트 수행
- GitHub Actions에서 PR 단위로 자동 실행
- 가능하면 비용이 거의 들지 않도록 구성
- **현재 단계에서는 Splunk Enterprise Security 전체 통합 테스트, notable 검증, RBA 검증, 운영 환경 배포 자동화는 제외**

---

## 배경 및 전제

### 핵심 전제
- `contentctl` 자체에 테스트 기능이 내장되어 있다.
- `contentctl test`는 기본적으로 테스트용 환경을 자동으로 사용하며, CI/CD에 적합하다.
- `splunk/security_content`의 공개 워크플로는 `contentctl build`, `contentctl test`, 결과 아티팩트 업로드 패턴을 사용한다.
- `splunk/security_content`의 detection YAML은 `tests.attack_data`를 정의할 수 있으며, 이 구조를 활용하면 detection별 테스트 자동화가 가능하다.
- 현재 목표는 **가벼운 탐지 검증**이므로 `contentctl test --mode changes` 중심으로 설계한다.
- 저장소가 **public repo**이면 일반적인 `ubuntu-latest` GitHub-hosted runner 사용은 비용 부담 없이 운영 가능한 방향으로 설계한다.
- 저장소가 **private repo**여도 GitHub Pro의 월 포함량(러너 시간) 안에서 충분히 운영 가능하도록 최대한 가볍게 설계한다.

---

## LLM에게 맡길 작업 범위

아래 작업을 내 저장소에 적용하는 방향으로 설계 및 코드 작성하라.

### 해야 할 일
1. `contentctl` 기반 GitHub Actions 워크플로 작성
2. PR 기준 변경분 detection만 테스트하도록 구성
3. 테스트 결과를 GitHub Actions Summary와 artifact로 남기도록 구성
4. 실패 원인을 파악하기 쉽게 로그와 summary를 남기도록 구성
5. 저장소에 필요한 디렉터리/파일 구조와 샘플 설정 파일 작성
6. 사용자가 GitHub에서 직접 해야 하는 설정을 문서화
7. 유지보수/확장 포인트를 문서화

### 현재 하지 말아야 할 일
- Splunk 운영 서버 자동 배포
- Splunk ES notable/risk 검증
- 장시간 integration testing
- self-hosted runner 전제 설계
- macOS/Windows runner 사용
- 유료 larger runner 사용
- 과도한 병렬 처리

---

## 최종 산출물 요구사항

LLM은 아래 산출물을 만들어야 한다.

### 1. GitHub Actions 워크플로
다음 파일을 생성 또는 제안하라.

- `.github/workflows/contentctl-build.yml`
- `.github/workflows/contentctl-test.yml`

또는 필요 시 하나의 workflow로 통합해도 되지만, 역할 구분이 명확해야 한다.

### 2. 문서
다음 문서를 생성하라.

- `docs/contentctl-cicd-setup.md`
- `docs/contentctl-testing-guide.md`

### 3. 보조 파일
필요 시 아래 보조 파일을 생성하라.

- `.github/workflows/format_test_results.py`
- `requirements.txt` 또는 `constraints.txt`
- 샘플 detection/test YAML 예시
- `.gitignore` 업데이트
- `README.md` 내 사용 방법 섹션 추가

### 4. 결과 설명
아래를 반드시 포함하라.

- 왜 `--mode changes`를 쓰는지
- 왜 `ubuntu-latest`를 쓰는지
- public/private repo 기준 비용 관점 설명
- 현재 범위에서 어떤 테스트가 가능한지 / 불가능한지
- 사용자가 GitHub UI에서 어디를 설정해야 하는지
- 향후 `test_servers` 또는 통합 테스트로 확장하는 방법

---

## 구현 원칙

### 설계 원칙
- 가장 단순하고 유지보수 쉬운 구조
- public repo에서 무료 사용 가능한 방향 우선
- private repo에서도 최소 실행 시간 기준
- PR마다 빠르게 피드백
- 실패해도 결과 artifact와 summary는 남김
- 외부 의존성은 최소화
- 버전 고정 또는 가능한 한 재현성 확보
- 설명 문서는 복붙 가능한 수준으로 상세히 작성

### 성능/비용 원칙
- runner는 `ubuntu-latest`
- `contentctl test --mode changes` 사용
- 필요 최소한의 artifact만 업로드
- 불필요한 matrix 빌드 금지
- 불필요한 full test 금지
- macOS/Windows 러너 금지
- `pull_request` 이벤트 중심 설계
- 필요 시 `workflow_dispatch` 수동 실행도 추가

### 안정성 원칙
- fork PR 고려 여부를 명확히 설명
- 실패 시 `summary.yml`을 artifact로 업로드
- 테스트 결과를 GitHub Actions Summary에 출력
- 디버깅을 위한 최소 로그 확보
- `continue-on-error`는 무분별하게 쓰지 말고, 결과 수집 단계에서만 전략적으로 사용

---

## 사용자가 GitHub에서 직접 해야 하는 설정

LLM은 아래 내용을 문서에 반드시 포함하라.

### A. 저장소 생성/준비
사용자가 해야 할 일:
1. 내 GitHub 계정 `dollce` 아래에 저장소 생성
2. 저장소 공개 여부 결정
   - public 권장: 비용 최소화 목적
   - private도 가능하지만 사용량 관리 필요
3. 기본 브랜치 이름 확인 (`main` 또는 `develop`)
4. PR 기반 개발 흐름을 사용할지 결정

### B. Actions 활성화 확인
GitHub 저장소에서 사용자가 확인해야 할 항목:
1. **Settings → Actions → General**
2. Actions 사용이 허용되어 있는지 확인
3. 필요 시
   - Allow all actions and reusable workflows
   - 또는 최소 허용 정책 설정
4. Workflow permissions 확인
   - 기본은 `Read repository contents permission`
   - 추가 권한이 필요 없도록 최소 권한 설계
5. fork PR 정책이 필요한 경우 승인 정책을 문서화

### C. 브랜치 보호 정책
사용자가 직접 설정해야 할 수 있다.
예:
1. **Settings → Branches**
2. `main` 또는 `develop`에 branch protection rule 적용
3. PR merge 전에 아래 체크 요구
   - contentctl build
   - contentctl test
4. 필요 시 직접 push 제한

### D. Secrets / Variables
현재 목표 범위에서는 **Splunk 서버 자격 증명 없이도 시작 가능**하도록 설계한다.
따라서 기본 구현에서는 GitHub Secrets가 반드시 필요하지 않도록 하라.

단, 향후 확장 섹션에는 아래를 별도 설명하라.
- `SPLUNK_HOST`
- `SPLUNK_USERNAME`
- `SPLUNK_PASSWORD`
- `SPLUNK_HEC_TOKEN`
- 기타 통합 테스트용 비밀값

### E. Dependabot / Actions 정책
선택 사항으로 설명:
- GitHub Actions 버전 업데이트를 위한 Dependabot
- workflow pinning 권장 여부
- third-party action 최소화

---

## 저장소 구조 권장안

LLM은 아래와 유사한 구조를 기준으로 설명하라.

```text
repo-root/
├── .github/
│   └── workflows/
│       ├── contentctl-build.yml
│       ├── contentctl-test.yml
│       └── format_test_results.py
├── detections/
├── stories/
├── macros/
├── lookups/
├── deployments/
├── data_sources/
├── docs/
│   ├── contentctl-cicd-setup.md
│   └── contentctl-testing-guide.md
├── requirements.txt
├── README.md
└── .gitignore
```

실제 내 저장소가 `splunk/security_content` 구조와 완전히 동일하지 않아도 되지만, `contentctl` 테스트가 가능하도록 필요한 최소 구조를 설명하라.

---

## 워크플로 구현 요구사항

### 1. Build Workflow 요구사항
다음 조건을 만족하라.

- 이름 예: `contentctl-build`
- 트리거:
  - `pull_request`
  - 필요 시 `push` on default branch
  - 선택적으로 `workflow_dispatch`
- 러너:
  - `ubuntu-latest`
- 단계:
  1. checkout
  2. Python 설치
  3. pip 업그레이드
  4. `contentctl` 설치
  5. 필요 시 enrichment용 외부 repo clone 여부를 옵션화
  6. `contentctl build` 실행
  7. 생성된 결과물을 artifact 업로드

### Build 관련 주의사항
- 처음 구현은 최대한 단순화하라.
- enrichment가 필수 아니면 `contentctl build`만 먼저 제안해도 된다.
- `--enrichments`는 옵션으로 분리하라.
- 외부 repo clone이 필요한 경우 이유를 문서화하라.

### 2. Test Workflow 요구사항
다음 조건을 만족하라.

- 이름 예: `contentctl-test`
- 트리거:
  - `pull_request` (opened, synchronize, reopened)
  - 필요 시 `workflow_dispatch`
- 러너:
  - `ubuntu-latest`
- 기본 전략:
  - 변경된 detection만 테스트
  - `contentctl test --mode changes` 사용
- 결과:
  - `test_results/summary.yml` artifact 업로드
  - Actions Summary 출력
  - 로그 가독성 확보

### Test 명령 요구사항
기본안은 아래 방향을 따르라.

```bash
contentctl test --mode changes --mode.target-branch <default-branch> --disable-tqdm --post-test-behavior never_pause
```

실제 최신 CLI 문법 차이가 있으면, **현재 contentctl 기준으로 올바른 문법으로 조정**하라.

### 실패 처리 요구사항
- 테스트 실패 시 workflow는 실패 처리되어야 한다.
- 하지만 실패하더라도 결과 요약 파일 업로드와 summary 렌더링은 되도록 설계하라.
- 이를 위해 artifact 업로드와 summary 출력 단계는 `if: always()` 전략을 고려하라.

### PR 기준 비교 요구사항
- 현재 PR의 base branch와 변경분을 비교하는 방식 설명
- fork PR 지원이 복잡하면 우선 same-repo PR 중심으로 설계하고, fork PR은 제한사항으로 명시 가능
- 다만 가능하면 `splunk/security_content`의 패턴처럼 base branch 기준 변경분 테스트 방식을 참고하라.

---

## 테스트 데이터 및 detection 작성 가이드 요구사항

LLM은 문서에 아래를 포함하라.

### detection YAML에 포함되어야 할 내용
- detection metadata
- SPL search
- `tests`
- `attack_data`
  - `data`
  - `source`
  - `sourcetype`

### 예시를 반드시 포함하라
아래 수준의 예시를 작성하라.

```yaml
tests:
  - name: True Positive Test
    attack_data:
      - data: https://example.com/sample.log
        source: sample_source
        sourcetype: sample:sourcetype
```

단, 가능하면 실제 `splunk/attack_data` 또는 현실적인 예시 구조를 반영하라.

### true positive 검증 관점에서 설명할 것
- 테스트 데이터는 detection SPL이 참이 되도록 설계되어야 함
- sourcetype/source가 detection에서 기대하는 형태와 맞아야 함
- CIM/data model 의존 detection은 테스트 환경에서 제약이 있을 수 있음
- 처음에는 단순 SPL 기반 detection부터 시작할 것을 권장

---

## 반드시 문서화해야 할 제한사항

LLM은 아래 내용을 명시하라.

### 현재 구성이 잘하는 것
- detection SPL 기본 동작 검증
- 테스트 데이터 기반 true positive 확인
- 변경분 detection 자동 회귀 테스트
- PR 기반 품질 게이트

### 현재 구성이 못하는 것 또는 제한이 있는 것
- Splunk ES notable 생성 검증
- Risk event/RBA 전체 검증
- 운영과 동일한 data model acceleration 재현 보장
- 운영용 TA/App/lookup/macros 전체 재현
- 대규모 통합 테스트
- 운영 Splunk 서버 자동 배포

### 주의점
- 일부 detection은 datamodel/tstats/매크로/lookup 의존성이 강해 테스트가 까다로울 수 있음
- 일부 detection은 `manual_test`가 더 적절할 수 있음
- public repo가 아니라면 Actions 사용량 관리 필요
- 외부 attack_data URL 가용성에 의존할 수 있음

---

## 사용자가 실제로 따라 해야 할 단계 문서 요구사항

문서에는 아래 절차를 복붙 가능한 수준으로 넣어라.

### 1단계: 저장소 준비
- 저장소 생성
- 기본 브랜치 결정
- 공개 여부 결정
- 로컬 clone

### 2단계: 기본 파일 반영
- workflow 파일 추가
- requirements 추가
- docs 추가
- 필요한 최소 디렉터리 생성

### 3단계: GitHub 설정
- Actions 허용
- branch protection
- required checks 지정

### 4단계: 첫 detection 테스트
- 샘플 detection 추가
- 샘플 attack_data 연결
- PR 생성
- Actions 결과 확인
- artifact 다운로드
- summary 해석

### 5단계: 실패 시 점검 포인트
- detection SPL 오류
- source/sourcetype mismatch
- attack_data 형식 문제
- base branch 비교 설정 문제
- workflow 권한 문제
- contentctl 버전 문제

---

## LLM 출력 형식 요구사항

LLM은 아래 형식으로 답하라.

### 우선순위
1. 내 저장소에서 바로 쓸 수 있는 현실적인 최소 구현안
2. 사용자가 GitHub UI에서 직접 해야 하는 설정
3. 실제 파일 내용 전체
4. 각 파일의 역할 설명
5. 제한사항과 향후 확장 포인트

### 필수 스타일
- 모두 마크다운으로 작성
- 코드블록 포함
- 복붙 가능한 YAML/Python/Markdown 제공
- 추상론보다 실제 설정값과 경로 중심
- “무엇을 직접 클릭해야 하는지” 명확히 쓰기
- public repo 기준 무료 사용 가능성도 별도 섹션으로 설명

---

## 구현 시 추가 요청

LLM은 다음도 함께 해라.

### A. 최소 구현안
가장 먼저 **오늘 바로 적용 가능한 최소 구현안**을 제시하라.
이 구현안은 아래를 만족해야 한다.
- public repo에서 무료 운영 가능성 높음
- `ubuntu-latest`
- `contentctl test --mode changes`
- 결과 요약 artifact 업로드
- branch protection과 연동 가능

### B. 개선안
그 다음에 선택적 개선안을 제시하라.
예:
- build/test 분리
- 수동 전체 테스트 workflow
- nightly full test
- 향후 `test_servers` 확장
- pinning 강화
- fork PR 대응 강화

### C. 사용자가 직접 해야 하는 체크리스트
문서 마지막에 체크리스트를 포함하라.

예:
- [ ] 저장소 생성
- [ ] Actions 허용
- [ ] workflow 파일 커밋
- [ ] 기본 브랜치 확인
- [ ] 샘플 detection 추가
- [ ] PR 생성
- [ ] 결과 확인

---

## 최종 목표

이 지시서의 최종 목적은, LLM이 내 GitHub 저장소에 적용 가능한 수준으로 다음을 완성하게 하는 것이다.

- `contentctl` 기반 GitHub Actions CI/CD
- 변경분 detection 자동 테스트
- true positive 중심 탐지 검증
- GitHub에서 사용자가 해야 하는 설정까지 포함한 완전한 구축 가이드

이 목표를 벗어나는 과도한 통합 테스트 설계는 현재 단계에서는 제외하라.
