# dollce Security Content

contentctl 기반 Splunk 탐지 콘텐츠 관리 저장소. PR 기반 자동 빌드/테스트로 detection 품질을 보장합니다.

## 개요

- contentctl을 사용하여 Splunk detection 콘텐츠를 관리
- PR 생성 시 자동으로 빌드 및 테스트 실행
- 변경된 detection만 선별적으로 테스트하여 효율적 운영
- GitHub Actions Summary에서 결과 즉시 확인 가능

## 저장소 구조

```
├── .github/workflows/     # CI/CD 워크플로
│   ├── contentctl-build.yml
│   ├── contentctl-test.yml
│   └── format_test_results.py
├── detections/            # Detection SPL 정의
├── stories/               # Analytic Stories
├── macros/                # 재사용 가능한 SPL 매크로
├── lookups/               # Lookup 데이터
├── deployments/           # 배포 설정
├── data_sources/          # 데이터 소스 정의
├── docs/                  # 문서
├── contentctl.yml         # contentctl 프로젝트 설정
├── requirements.txt       # Python 의존성
└── README.md
```

## 빠른 시작

### 사전 요구사항

- Python 3.11 이상
- Git

### 1단계: 저장소 클론

```bash
git clone <repository-url>
cd contentctl_github_actions
```

### 2단계: 환경 설정

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3단계: 로컬 빌드 확인

```bash
contentctl build
```

### 4단계: Detection 추가

- `detections/` 하위에 YAML 파일 생성
- 필수 필드 및 `tests` 섹션 포함
- 상세 가이드: [docs/contentctl-testing-guide.md](docs/contentctl-testing-guide.md) 참조

### 5단계: PR 생성 및 자동 테스트

```bash
git checkout -b feature/new-detection
git add detections/your_new_detection.yml
git commit -m "Add new detection for ..."
git push origin feature/new-detection
```

- GitHub에서 PR 생성
- Actions 탭에서 빌드/테스트 결과 자동 확인

## CI/CD 워크플로

### Build (contentctl-build)

- **트리거:** PR, push (main/develop)
- **동작:** `contentctl build` 실행 → Splunk App 패키지 생성
- **결과:** build artifact 업로드

### Test (contentctl-test)

- **트리거:** PR (opened, synchronize, reopened)
- **동작:** 변경된 detection만 `contentctl test --mode changes`로 테스트
- **결과:** 테스트 요약 Summary + artifact 업로드

## 결과 확인 방법

### GitHub Actions Summary

1. PR 페이지 하단 **Checks** 확인
2. workflow 이름 클릭
3. **Summary** 탭에서 테스트 결과 테이블 확인

### Artifact 다운로드

1. **Actions** 탭 → 해당 workflow run 클릭
2. 하단 **Artifacts** 섹션에서 다운로드
3. `test_results/` 내 상세 결과 확인

## 문서

| 문서 | 설명 |
|------|------|
| [CI/CD 구축 가이드](docs/contentctl-cicd-setup.md) | GitHub 설정, Actions, 브랜치 보호 등 |
| [테스트 가이드](docs/contentctl-testing-guide.md) | Detection 작성법, 테스트 데이터, 디버깅 |

## 향후 계획

- [ ] Splunk 통합 테스트 (test_servers 연동)
- [ ] Nightly 전체 regression 테스트
- [ ] ES notable/RBA 검증
- [ ] 운영 환경 자동 배포

## 라이선스

이 프로젝트는 내부 보안 콘텐츠 관리 목적으로 사용됩니다.
