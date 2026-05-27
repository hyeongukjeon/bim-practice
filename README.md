# BIM전문가 2급 랜덤 문제 풀이

PDF 공개문제와 필기시험 예시문제를 정리해 만든 모바일용 랜덤 문제 풀이 웹앱입니다.

## 기능

- 전체 340문항 랜덤 출제
- 한 화면에 한 문제와 보기 4개 표시
- 답 선택 즉시 정답은 초록색, 오답은 빨간색 표시
- 이전문제 / 다음문제 이동
- 브라우저에 문제 순서와 풀이 기록 저장
- 우측 상단 버튼으로 문제 순서 초기화

## 파일 구성

- `index.html`: 웹앱 진입 파일
- `styles.css`: 모바일 중심 화면 스타일
- `app.js`: 랜덤 출제와 채점 로직
- `data/questions.js`: 브라우저에서 사용하는 문제 데이터
- `data/questions.json`: 원본 JSON 형태의 문제 데이터
- `scripts/extract_questions.py`: PDF에서 문제 데이터를 다시 생성하는 스크립트

## 로컬에서 실행

```powershell
python -m http.server 8080
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:8080/
```

같은 Wi-Fi의 휴대폰에서 보려면 PC의 내부 IP를 사용합니다.

```text
http://PC-IP주소:8080/
```

## GitHub Pages 배포

1. GitHub에서 새 저장소를 만듭니다.
2. 이 폴더에서 아래 명령을 실행합니다.

```powershell
git init
git add index.html styles.css app.js data/questions.js data/questions.json scripts/extract_questions.py README.md .gitignore .nojekyll
git commit -m "Add BIM practice web app"
git branch -M main
git remote add origin https://github.com/USER/REPOSITORY.git
git push -u origin main
```

3. GitHub 저장소에서 `Settings` -> `Pages`로 이동합니다.
4. `Build and deployment`에서 `Deploy from a branch`를 선택합니다.
5. Branch는 `main`, folder는 `/root`로 선택하고 저장합니다.

잠시 후 아래 형태의 주소로 접속할 수 있습니다.

```text
https://USER.github.io/REPOSITORY/
```

## 문제 데이터 다시 만들기

PDF 파일을 같은 폴더에 둔 상태에서 실행합니다.

```powershell
python scripts/extract_questions.py
```

`data/questions.json`과 `data/questions.js`가 다시 생성됩니다.
