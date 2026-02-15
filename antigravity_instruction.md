# Antigravity 指示書：意思決定中心型サーベイ分析・統合DSSアプリの構築

> 目的：ヒヤリング（定性）／サーベイ（定量）／実測KPI（業務データ）を統合し、「集計」ではなく**意思決定**を前に進めるための Evidence-Based DSS を構築する。  
> 設計の核は **Decision Card（意思決定論点）**。  
> 本指示は添付ガイドラインPDFに準拠（透明性・品質ゲート・協調型DSS、SAW/WASPAS、Freeze 等）。  

---

## 0. Antigravity への依頼の仕方（前置き）

Antigravity には次の2つを同時に要求すること：
1) **設計→実装**を一気通貫で行い、MVP を動く状態で納品する  
2) 仕様の「透明性（説明可能性）」と「品質ゲート（信頼性・欠損・n不足）」と「協調型DSS（人が最終決定）」を破らない  

また以下を必須成果物とする：
- リポジトリ一式（実行手順付き）
- Configスキーマ（顧客別に差し替え可能）
- サンプルデータ（架空でも可：形式が正しければ良い）
- 受入テスト（チェックリスト＋自動テスト）

---

## 1. 非交渉の設計原則（破ると失格）

### 1) Transparency（透明性）
- ブラックボックスランキング禁止（AHP/ANPのようなペア比較系は採用しない）
- 優先順位は **SAW / WASPAS** のように、式と内訳が説明できる方法を採用する  
- UI上で **Impact / Urgency / Uncertainty(Penalty)** の内訳を必ず表示

### 2) Quality Gate（品質担保）
- データを「勝手に補正」して推奨を作らない（Auto-Correction禁止）
- 品質が悪い場合は「警告」と「Confidence Penalty」で順位・推奨の強さを落とす
- Gate例：Sampling bias示唆、Cronbach’s alpha、Missing、n不足、尺度不整合など

### 3) Cooperative DSS（協調型DSS）
- 推奨は **Draft（下書き）** とし、人が **Edit/Override/Approve** できること
- 人が上書きした場合、理由を必須入力し、監査ログに残す

---

## 2. システムのゴール（ユーザー価値）

### ゴール
- 顧客会議で「で、何を決める？」が起きない状態を作る  
- Decision Cardごとに
  - 現状（事実）
  - 根拠（Evidence）
  - 確信度（Confidence）
  - 優先順位（Priority）
  - 推奨（Draft）
  - 人が最終決定した履歴
  を一枚で提示する

### 非ゴール（最初はやらない）
- 「唯一の正解」を自動で断定する
- 因果を断定する（Phase3でDEMATEL等を追加して扱う）
- 個人特定の介入最適化（リスクが大きい）

---

## 3. 現実的な意思決定プロセス（6週間ループ）をシステムで再現

### 6週間運用（必須）
- Week0: Agenda Setting（Decision Card作成／Evidence Plan確定）
- Week1-3: Collection（ヒヤリング／サーベイ／KPI収集・登録）
- Week4: Analysis & Gate（集計＋品質ゲート）
- Week5: Freeze & Meeting（スナップショット固定＋意思決定会議）
- Week6: Action（施策登録＋追跡開始）

**Freeze**（会議用スナップショット固定）は必須：
- 会議中に数字が変わる事故を防ぐ
- 出力物に wave_id / config_version / data_version を埋め込む

---

## 4. アーキテクチャ（3層）— 実装非依存

### Layer 1: Evidence Layer（Data）
- Quantitative：Survey（CSV/Excel）
- Qualitative：Interview（メモ/文字起こし＋タグ）
- Facts：KPI（時系列）

### Layer 2: Logic Layer（Engine）
- Ingestion & Validation（Quality Gate）
- Prioritization Engine（SAW/WASPAS）
- Recommendation Builder（Rule-based + XAI）

### Layer 3: Decision Layer（UI）
- Decision Card（Atomic Unit）
- Decision Board（一覧ダッシュボード）
- Report Generator（出力）

---

## 5. 必須データモデル（MVP）

### 5.1 Wave（調査回）
- wave_id, name, time_window, target_population, owner, status(draft/collecting/analyzing/frozen/closed)

### 5.2 DecisionCard（意思決定論点）
必須フィールド：
- id, title, decision_question, stakeholders
- required_evidence: {drivers:[], interviews:[], kpis:[]}
- rules: ルール（しきい値・条件分岐）→ status（GREEN/YELLOW/RED）を返す
- priority_weights: {w_impact, w_urgency, w_uncertainty}
- recommendation_catalog_refs: []（推奨カタログ参照）

### 5.3 EvidencePlan（証拠設計）
- decision_card_id
- collection_tasks: [
  {type: interview/survey/kpi, owner_role, due_date, method, template_ref}
]
- acceptance_conditions（最低n、欠損率上限、必要KPIの期間等）

### 5.4 Evidence Items（登録単位）
**InterviewSession**
- session_id, wave_id, org_attrs, notes/transcript, tags(driver/theme/evidence_type), linked_cards

**SurveyRun**
- survey_run_id, wave_id, questionnaire_version, mapping_version, data_file_ref, ingestion_result_ref

**MetricSeries**
- metric_id, wave_id, definition, unit, time_grain, org_key, data_points[], source, data_version

### 5.5 QualityGateResult
- gate_id, target_ref, checks:[{name, status(pass/warn/fail), metrics, message}]
- confidence_penalty（0〜1）
- decision_impact（優先度計算に反映）

### 5.6 Snapshot（Freeze）
- snapshot_id, wave_id, created_at
- config_version_hash, data_version_hash
- exported_report_refs

### 5.7 DecisionLog（会議結果）
- decision_card_id, snapshot_id
- human_action: approve/edit/override
- final_decision_text, rationale, owner, due_date
- audit trail（誰がいつ）

---

## 6. 機能要件（MVP→段階拡張）

### Phase 1: MVP（最短で価値を出す）
1) Decision Card UI（作成・編集・一覧）
2) 収集・登録
   - Survey CSV import
   - KPI CSV import（時系列）
   - Interview 登録（メモ＋タグ＋カード紐付け）
3) 品質ゲート（最低限）
   - Format check（列・型）
   - Range check（尺度）
   - Missing（欠損率）
   - n check（セグメント最小n）
   - → Auto-correct禁止、Warning + Penaltyのみ
4) 優先順位（SAW：単純加重和）
   - Priority = (Impact*w1) + (Urgency*w2) - (Uncertainty*w3)
   - UIで内訳表示
5) 推奨生成（ルールベース）
   - status と evidence に応じた Draft を生成
   - 逆効果/副作用条件（Risk）を必ず添える
6) Freeze（スナップショット固定）
7) レポート出力（DOCX or PDF）

### Phase 2: Enhanced Logic（精度と説明の強化）
- WASPAS ランキング（SAW+WPMの融合）
- Cronbach’s alpha（条件満たす場合のみ）
- SHAP 可視化（可能な範囲で）

### Phase 3: Advanced AI（因果と反実仮想）
- DEMATEL（因果構造化）
- Counterfactual simulation（しきい値改善でGreen化の試算）

---

## 7. 優先順位・スコア仕様（厳密に）

### 7.1 Impact（影響）
- 対象人数（n）
- ギャップ量（目標/基準との差、または平均との差）
- 重要度重み（顧客設定）
→ 正規化して 0〜100 など同一スケールへ

### 7.2 Urgency（緊急）
- 悪化傾向（trend：前回比）
- ばらつき拡大（variance）
- 局在（特定部門の下位集中）
→ 正規化して 0〜100

### 7.3 Uncertainty / Confidence Penalty（不確実性）
- n不足
- 欠損率高
- 尺度不整合
- （Phase2）alpha < threshold
→ 0〜100（高いほど不確実）として扱い、式で減点

### 7.4 表示要件
- 各 DecisionCard に以下を必ず表示：
  - status（信号機）
  - confidence（High/Med/Low + 根拠）
  - priority（総合スコア）
  - key evidence（何が効いてこの判定か：ルール or XAI）
  - recommendation draft（編集可能）

---

## 8. 収集・登録UI（現実運用に耐える導線）

### 8.1 Evidence Plan Wizard（必須）
- カード作成 → そのカードの「証拠設計」に必ず誘導
- 収集担当・期日・方法・テンプレを登録
- 未充足項目があるとボードに警告

### 8.2 Intake Inbox（必須）
- 未紐付けのInterview/KPI/Surveyを受ける箱
- 分析担当が整形・タグ付け・カード紐付けを行う

### 8.3 Freeze 操作（会議用）
- Freeze 前に Gate 未通過がある場合は警告
- Freeze 後は再計算結果が会議資料に混ざらないよう固定

---

## 9. 推奨（Recommendation）仕様：安全設計
推奨は必ず以下の構造を持つ（テンプレート化）：
- What（施策）
- Why（根拠：どのEvidenceが効いたか）
- Preconditions（実装条件）
- Risks（逆効果/副作用条件）
- Owner/Horizon（責任者/期限）
- Success Metrics（検証指標）

**協調型DSS要件**：
- Draft → Human Edit/Override → Approve のステップを持つ
- Override には理由必須
- ログに残す

---

## 10. 実装要求（Antigravityへの具体タスク）

### 10.1 リポジトリと実行
- 1コマンドで起動（例：make run / docker compose up）
- ローカルでもDockerでも動く
- .env で設定可能

### 10.2 技術選定（推奨だが縛りではない）
- UI：Streamlit（高速にMVPを出すため）
- Data：DuckDB or SQLite（まずは簡易で良い）
- 型/検証：Pydantic（Configスキーマ検証）
- 出力：DOCX（python-docx）or PDF（reportlab）
- テスト：pytest

### 10.3 モジュール分割（必須）
- core/io.py（インポート）
- core/quality.py（品質ゲート）
- core/metrics.py（指標計算）
- core/priority.py（SAW/WASPAS）
- core/decision.py（ルール評価）
- core/recommend.py（推奨生成）
- core/snapshot.py（freeze）
- core/report.py（出力）
- core/audit.py（ログ）
- app/pages/*.py（UI）

### 10.4 Configファイル
- configs/customer_default.yaml を提供
- DecisionCard/Drivers/Rules/ReportTemplate を含む
- 変更してもコード改修なしで動く

---

## 11. 受入テスト（チェックリスト）
Antigravity は以下を満たすデモを用意すること：

1) Wave を作成し、DecisionCard を3件作る  
2) EvidencePlan を定義し、Interviewを2件登録（タグ付き）  
3) Survey CSV を取り込み、品質ゲートの warn を発生させる（欠損など）  
4) KPI CSV を取り込み、部門別時系列を表示できる  
5) Decision Board が priority 順に並び、内訳が見える  
6) 推奨が Draft 生成され、編集→Approve でき、ログが残る  
7) Freeze して、会議用スナップショットが固定される  
8) レポートを出力でき、スナップショットID等が埋め込まれる

---

## 12. 完了条件（Definition of Done）
- README に実行手順があり、第三者が起動できる
- Config差し替えで顧客仕様を変更できる
- 透明性・品質ゲート・協調型DSSの3原則が守られている
- Freeze と監査ログが動作する
- MVP範囲の自動テストが最低限ある

---

## 13. Antigravity に渡す「実行プロンプト」（コピペ用）

あなたはプロダクトアーキテクト兼フルスタックエンジニアです。  
添付ガイドライン（Decision Card中心、Transparency/Quality Gate/Cooperative DSS、SAW/WASPAS、Freeze）に準拠して、意思決定中心型サーベイ統合DSSを実装してください。  
要件：MVP（Phase1）を最優先で動く形にし、その後Phase2/3の拡張余地を残す。  
必須：Config駆動、品質ゲート（自動補正禁止、警告＋確信度ペナルティ）、優先順位（式と内訳の可視化）、推奨の人間上書き、Freeze、監査ログ、レポート出力。  
成果物：Gitリポジトリ一式、README、Config例、サンプルデータ、受入テスト手順、pytest。  

---

以上。
