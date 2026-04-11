# 세션 컨텍스트 — 2026-04-11 v26

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A~E 완료**, **Phase γ(미세 조정) 완료**,
**Phase E(클라우드 배포) 완료**, **Phase 2 Bugfix 완료**,
**Phase F(Reserved Test Set 검증) 완료**.

파이프라인이 프로덕션 환경(Railway + Vercel + Supabase)에서 정상 작동 중이며,
TN 100% 정확, 정직한 침묵 패턴 확인. **베타 공개 가능한 안전 프로파일** 확보.

다음 마일스톤은 **Phase G — 매핑/임베딩 확장**이며, Phase F가 식별한
데이터 레이어 편중 해소가 핵심 과제다.

### v25→v26 변경 사항 (2026-04-11)

**Phase F 실행 및 완료 — Reserved Test Set 검증**

Reserved Test Set의 데이터 정제·블라인드 격리·63건 분석·집계 분석을
완료했다. 정량 지표보다 더 중요한 정성적 발견 5건이 식별되었으며,
이는 모두 Phase G의 작업 백로그로 이관되었다.

**1. Reserved Test Set 정제 (2026-04-11 오전, Gamnamu 수동 작업):**
- 원본 73건 중 데이터 누수 위험(source_url이 신문윤리위 심의 페이지로
  설정된 케이스) 전량 → 실제 기사 URL로 교체
- 텍스트 파이프라인 범위 외 케이스(만평·중간광고·유튜브·스톡이미지·
  지면 광고형 기사 등) 10건 제외
- 최종 63건 (`golden_dataset_reserved_test_set.json`, v2)
- 보관 위치: `/Users/gamnamu/Documents/Golden_Data_Set_Pool/` (리포 외부, 격리)

**2. 격리 3계층 설계 (코드 구현):**
- 물리: Pool 디렉토리는 리포 외부, CLI 미접근
- 논리: `backend/diagnostics/phase_f/injected/` 전체 .gitignore
- 코드: `phase_f_validation.py`의 `load_blind_subset()`이 allowlist 방식
  (`id` + `url`만 새 dict로 복사)으로 label 메모리 진입을 코드 레벨에서 차단
- 실행기/집계기 별도 파일 분리로 관심사 격리

**3. 63건 검증 실행:**
- 파일럿 5건 (seed=42): B2-08, A-15, A-03, C-03, A2-14 — 전건 성공
- 본실행 58건 — 53건 성공, 5건 HTTP 400 (매체별 파서 커버리지 갭)
- 총 소요 ~68분, 비용 ~$10
- TN 5/5 완벽 (`is_true_negative: true` 케이스 모두 탐지 0건으로 정확 판정)
- 파일럿 C-03 (전남일보, 이달의 기자상 수상작): "문제 없음" 정직 판정

**4. 집계 + 정량 지표 (관찰 일지):**
- precision_macro: 0.2787
- recall_macro: 0.6007
- f1_macro: 0.3808
- TN 정확도: 5/5 (100%)
- **이 수치는 절대 평가가 아니라 관찰 일지이며, Sonnet의 광범위 인용 성향과
  매핑 사전 커버리지 한계에 의해 구조적으로 영향받음.**

**5. 발견 사항 5건 (모두 Phase G 백로그로 이관):**

#### 발견 1: pattern_ethics_relations 매핑 편중 ⭐ (1순위)
DB의 14개 source 중 신문윤리실천요강 위주로만 패턴-규범 연결됨.
- 인권보도준칙 94건 active, 패턴 매핑 4건만
- 재난보도준칙 39건, 자살보도 윤리강령 22건 등 매핑 0건
- M2 시드 단계에서 누락된 큐레이션 작업

#### 발견 2: Sonnet의 인용 source 편향 (발견 1의 결과)
53건 분석에서 인용된 365개 마커 중:
- 신문윤리실천요강 69.3%
- 언론윤리헌장 25.2%
- 인권보도준칙 1.6%, 그 외 12개 source 사실상 0%

원인: 임베딩 인덱스 또는 RAG 검색 가중치가 신문윤리실천요강에 편중되어
다른 source가 사전 필터에서 탈락. v25 시점 임베딩 401건의 source별 분포
진단 필요.

#### 발견 3: ethics_to_pattern_map 자동 확장 미흡 (발견 1의 부수)
`generate_ethics_to_pattern_map.py`가 `pattern_ethics_relations`만 변환.
277개 ethics_codes는 사전 미수록. **발견 1 해소되면 자동 해결.**

#### 발견 4: 매체별 파서 커버리지 갭
5건 HTTP 400 — 모두 "X 본문을 찾을 수 없습니다" 패턴.
- 확인된 매체: 문화일보(E-05), 한국일보(E-18), 그 외 D-03 등 3건
- backend/core 스크래퍼에 매체별 셀렉터 보강 필요

#### 발견 5: 제목 레이어 선정성/재난 부적절 어휘 (Gamnamu 직접 검토)
- A2-10: "'숏타임' 즐기고", "경악" 등 제목 선정성 미탐지
- A2-04: 지진 사망자 "돌파" 등 재난 부적절 표현 미탐지
- 본문은 통과하나 제목·소제목 한정 검사 단계 신설 검토 가치 있음

**6. Gamnamu 직접 검토에서 확인된 행동 패턴 (긍정):**
- C-03 전남일보 이달의 기자상 수상작 → 정직한 침묵
- E-08 미 대선 통신사 출처 (정치적 맥락의 신문윤리위 결정) → 모델의 자율적 절제
- A2-02 사진 모자이크 사안 → 텍스트 파이프라인 합리적 한계 인정
- 신문윤리위 지적 후 매체가 제목 자체수정한 다수 케이스 → 모델이 외부 맥락
  끌어오지 않고 "보이는 텍스트"만 평가 (행동 정직성)

**7. PR 이력:**
- PR #34 (예정): `feature/phase-f-validation` → `main`
  - 5d53bdc chore(phase-f): 사전 준비 — 격리 주입 경로 및 실행 설계
  - a634a2d feat(phase-f): 블라인드 실행기 + 사후 집계기 추가
  - dc0a612 fix(phase-f): Reserved Test Set v2 스키마 적응
  - 603e4e5 fix(phase-f): 주입 파일 wrapper(candidates 키) 구조 대응
  - (예정) feat(phase-f): 매핑 사전 + 마커 추출 + 최종 리포트

---

## M6 진행 현황 체크리스트

- [x] Phase A~γ ✅
- [x] Phase D: 아카이빙 + 링크 공유 통합 ✅
- [x] Phase E: 클라우드 배포 ✅
- [x] Phase 2 Bugfix ✅
- [x] **Phase F: Reserved Test Set 검증 ✅** ← v26 완료
- [ ] **Phase G: 매핑/임베딩 확장 + 파서 커버리지 보강** ← 다음 세션 첫 작업
- [ ] Phase H (또는 베타 공개): 기타 마무리

---

## 다음 세션 작업 (Phase G)

### 1순위: 매핑/임베딩 확장 (Phase F 발견 1+2+3 통합 해소)

**1-1. 임베딩 인덱스 진단**
- `embeddings` 테이블의 source별 카운트 조회
- 401건이 14개 source에 어떻게 분포되어 있는지 확인
- 신문윤리실천요강 외 source의 청크가 충분히 임베딩되어 있는지 검증

**1-2. ethics_codes 큐레이션 (Gamnamu 핵심 작업)**
- 14개 source × 평균 20+ ethics_codes를 119개 패턴에 의미 매핑
- 인권보도준칙·재난보도준칙·자살보도 윤리강령부터 우선
- 큐레이터의 판단이 필요한 작업 (CLI/AI 자동화 불가)

**1-3. pattern_ethics_relations 시드 확장**
- 1-2 결과를 SQL로 반영
- `generate_ethics_to_pattern_map.py` 재실행으로 사전 자동 갱신

**1-4. 임베딩 재구축 (필요 시)**
- 누락된 source의 청킹 + 임베딩 신규 생성

**1-5. Phase F 회귀 검증**
- 같은 53건 결과를 재집계 (분석 재실행 없이)
- 매핑 보강 후 precision/recall 변화 측정
- 비용 0원, 30초 작업

### 2순위: 매체별 파서 보강 (Phase F 발견 4)
- `backend/core` 스크래퍼에 문화일보 등 5개 매체 셀렉터 추가
- HTTP 400 5건 재실행으로 검증

### 3순위 (검토 후 결정): 제목 한정 검사 단계 신설 (Phase F 발견 5)
- A2-04 ("돌파"), A2-10 ("숏타임", "경악") 류 제목 부적절 표현
- 본문 분석과 분리된 제목 전용 패턴 검사 단계 도입 가능성

### 운영 과제
- GitHub PAT 갱신 (만료일: **2026-05-05** — 24일 남음, 주의)
- Supabase heartbeat 동작 확인
- RLS 정책 활성화 (Phase G 후반)

---

## 핵심 지침 (다음 세션 Claude에게)

**Phase F가 식별한 진실**: CR-Check의 정밀도 한계는 모델이 아닌 데이터
레이어에 있다. Phase G는 ethics_codes 매핑·임베딩의 source 다양성 확장을
1순위로 한다. 모델 튜닝이나 프롬프트 재설계로 풀려는 시도는 우선순위가
낮다.

1. **Phase F 완료. 베타 공개 가능한 안전 프로파일 확보.** TN 100%, 정직한
   침묵 확인. 다음은 정밀도 개선이며, 그 길은 데이터 보강이다.
2. **main 브랜치가 프로덕션.** push 시 자동 배포. 반드시 PR 경유.
3. **Phase 1 = Sonnet 4.5, Phase 2 = Sonnet 4.6.** 분리 구조 유지.
4. **인용 형식은 〔〕 마커.** Phase F의 마커 추출 집계기가 이 가정에 의존.
5. **Reserved Test Set은 격리 디렉토리에 보관.** Pool 경로는 코드/문서에
   명시 금지. 재검증 시 v25 격리 설계 그대로 재사용.
6. **CLI 자율 진행 제한.** STEP 단위 승인 게이트 엄격 적용.
7. **Phase G의 큐레이션은 Gamnamu 핵심 작업.** AI는 형식과 SQL은 도울 수
   있어도 ethics_code의 의미 매핑은 큐레이터 판단 영역.

---

## 주요 산출물 경로 (v26 갱신)

### Phase F 산출물 (신규)
````
backend/scripts/
├── phase_f_validation.py          ← 블라인드 실행기 (v2 스키마, wrapper 대응)
├── phase_f_scoring.py             ← 사후 집계기 (마커 추출 + 카테고리 정규화)
├── generate_ethics_to_pattern_map.py ← DB → 매핑 사전 자동 생성
└── ethics_to_pattern_map.json     ← 89 entries (Phase G 1-3 후 재생성 예정)

backend/diagnostics/phase_f/
├── injected/                      ← gitignore (Reserved Test Set 주입 경로)
│   └── reserved_test_set_63.json  ← Gamnamu 수동 배치 (커밋 안 됨)
├── run_20260411_164820/           ← 파일럿 5건
├── run_20260411_172053/           ← 본실행 58건 + _scoring.json
└── pilot_log.txt / full_log.txt   ← 실행 로그

docs/
├── SESSION_CONTEXT_2026-04-11_v26.md  ← ★ 이 문서
├── PHASE_F_FINAL_REPORT.md            ← Phase F 최종 리포트
├── PHASE_F_EXECUTION_DESIGN.md        ← Phase F 설계 (격리 3계층)
└── ...
````

### Reserved Test Set 보관 (불변)
````
/Users/gamnamu/Documents/Golden_Data_Set_Pool/
└── golden_dataset_reserved_test_set.json  ← 63건, v2, 리포 외부 격리
````

---

## 주의사항 (v25 계승 + v26 추가)

(v25의 모든 주의사항 유지)

- **Phase F 발견 사항은 결함이 아닌 백로그.** "오분류 14건"이라는 표현에
  과민 반응 금지. precision 0.28은 모델의 광범위 인용 성향 + 매핑 커버리지
  한계의 합산 결과이며, 시민 사용 안전성과는 다른 차원의 지표.
- **TN 5/5 완벽이 베타 안전성의 핵심 지표.** 이것이 흔들리면 즉시 멈출 것.
- **Phase F의 격리 설계는 Phase G에서도 그대로 재사용.** 회귀 검증 시
  같은 `injected/` 경로 + 같은 매핑 사전 생성 절차.
- **`generate_ethics_to_pattern_map.py`는 멱등.** 재실행해도 안전.
- **Phase G 1-2 큐레이션은 Gamnamu 직접 작업.** CLI에 위임 금지.
- **이달의 기자상 수상작에 대한 정직한 침묵 사례(C-03)는 보존할 가치 있는
  참고 케이스.** 향후 도구 소개 자료에 인용 가능.

---

*이 세션 컨텍스트는 2026-04-11 밤에 v25→v26으로 갱신되었다.*
*Phase F 완료: 격리 3계층 설계, 63건 분석, 매핑 편중 발견, 베타 안전성 확인.*
*다음 작업: Phase G — ethics_codes 매핑 확장 (1순위), 파서 보강 (2순위).*
*핵심 통찰: 정밀도의 길은 모델이 아닌 데이터 레이어에 있다.*