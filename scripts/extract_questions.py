import json
import re
from pathlib import Path

import pdfplumber


CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4}
HANGUL = {"가": 1, "나": 2, "다": 3, "라": 4}

# The first public-problem PDF in this folder does not include its answer sheet.
# Answer key source: https://www.scribd.com/document/950929635/
PUBLIC_1_ANSWERS = [
    4, 2, 4, 4, 1, 1, 3, 3, 1, 4,
    3, 3, 2, 2, 1, 3, 4, 1, 3, 3,
    2, 4, 3, 3, 3, 1, 2, 2, 2, 4,
    2, 3, 4, 3, 3, 1, 3, 2, 2, 2,
    3, 4, 1, 1, 3, 4, 3, 2, 4, 4,
]

PUBLIC_2_ANSWERS = [
    3, 3, 1, 4, 4, 3, 3, 1, 2, 1,
    4, 3, 1, 4, 2, 4, 1, 3, 2, 1,
    4, 2, 3, 4, 1, 1, 1, 3, 3, 2,
    4, 2, 2, 3, 2, 2, 3, 3, 2, 4,
    1, 3, 2, 2, 2, 3, 3, 1, 4, 4,
]

PUBLIC_3_ANSWERS = [
    4, 1, 3, 4, 4, 4, 1, 4, 2, 3,
    2, 1, 1, 3, 2, 3, 3, 3, 4, 4,
    1, 4, 4, 1, 4, 2, 1, 2, 2, 3,
    4, 1, 3, 1, 4, 3, 3, 4, 2, 2,
    1, 2, 4, 3, 1, 3, 2, 4, 3, 1,
]

SOURCES = [
    {
        "match": "BIM전문가 2급(건축)",
        "title": "BIM전문가 2급(건축) 필기시험 예시문제",
        "kind": "single",
    },
    {
        "match": "BIM전문가 2급(토목)",
        "title": "BIM전문가 2급(토목) 필기시험 예시문제",
        "kind": "single",
    },
    {
        "match": "공개문제 1",
        "title": "BIM 운용전문가 필기 공개문제 1회",
        "kind": "columns",
        "question_pages": (2, 6),
        "answers": PUBLIC_1_ANSWERS,
    },
    {
        "match": "공개문제 2",
        "title": "BIM 운용전문가 필기 공개문제 2회",
        "kind": "columns",
        "question_pages": (2, 6),
        "answers": PUBLIC_2_ANSWERS,
    },
]

ARCHITECTURE_PAGE_8_TEXT = """
28. 레빗에서 뷰 템플릿에 대한 설명으로 옳지 않은 것은? 3
① 명령은 뷰 탭의 그래픽 패널에 있다.
② 현재 뷰에 템플릿 특성을 적용하거나 현재 뷰에서 작성할 수 있다.
③ 뷰 템플릿 관리 도구는 관리 탭의 설정 패널에 있다.
④ 뷰의 인스턴스 특성에서 뷰 템플릿을 지정할 수 있다.
29. 레빗에서 난간에 대한 설명으로 옳지 않은 것은? 3
① 명령은 건축 탭의 순환 패널에 있다.
② 카테고리는 난간, 패밀리는 시스템 패밀리이다.
③ 계단 및 경사로를 통해서만 작성할 수 있고, 직접 작성할 수는 없다.
④ 상단, 난간 동자, 난간, 핸드레일로 구성된다.
30. 레빗에서 벽의 편집에 대한 설명으로 옳지 않은 것은? 3
① 벽에 개구부를 작성할 수 있다.
② 베이스 및 상단의 레벨과 간격띄우기를 수정할 수 있다.
③ 프로파일 편집을 통해 벽의 레이어 구성을 수정할 수 있다.
④ 벽의 측면에 면을 분할하고, 다른 재료를 설정할 수 있다.
31. 레빗에서 뷰 컨트롤 막대에서 사용할 수 있는 기능이 아닌 것은? 4
① 축척
② 뷰 자르기 및 영역 표시
③ 상세 수준
④ 창에 맞게 전체 줌
"""


def squeeze(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+A-$", "", text)
    text = text.replace(" .", ".").replace(" ,", ",")
    return text.strip()


def clean_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("A-") or re.fullmatch(r"-\d+", line):
            continue
        if "(cid:" in line:
            continue
        if "Korea Institute" in line or "Education Evaluation" in line:
            line = line.replace("Edu작c성a한ti다o.n Evaluation", "작성한다.")
            line = line.replace("Education Evaluation", "")
        if re.fullmatch(r"A-\d+-\d+|-?\d+-\d+-\d+|-?\d+-", line):
            continue
        if any(
            skip in line
            for skip in [
                "수험번호 성 명",
                "자격종목 및 등급",
                "답안카드 작성시",
                "전적으로 수험자의 귀책사유",
                "필 기 공 개 문 제",
                "필 기 시 험 공 개 문 제",
                "BIM 운 용 전 문 가",
            ]
        ):
            continue
        if re.fullmatch(r"(시험시간\s*)?형별|A|수 있습니다\.?", line):
            continue
        line = line.replace("나,", "나.")
        line = re.sub(r"^나\s+", "나. ", line)
        line = line.replace("Detai)", "Detail)")
        line = line.replace("Express언오", "EXPRESS언어")
        line = line.replace("Edu작c성a한ti다o.n Evaluation", "작성한다.")
        line = re.sub(r"(?:IM\s*)?E\s*라d\.\s*uSAcTa\(SttiaondnardEAvCaISluTeaxtt\)ion", "라. SAT(Standard ACIS Text)", line)
        line = re.sub(r"E\s*가d\.\s*uOcGaCtion\s*Evaluat나io\.\s*CnORENET", "가. OGC 나. CORENET", line)
        lines.append(line)
    return lines


def extract_single_column(path: Path) -> str:
    parts = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            parts.extend(clean_lines(page.extract_text() or ""))
            if "BIM전문가 2급(건축)" in path.name and index == 8:
                parts.extend(clean_lines(ARCHITECTURE_PAGE_8_TEXT))
    return "\n".join(parts)


def extract_columns(path: Path, start_page: int, end_page: int) -> str:
    parts = []
    with pdfplumber.open(path) as pdf:
        for page_no in range(start_page - 1, end_page):
            page = pdf.pages[page_no]
            width, height = page.width, page.height
            top = 30
            bottom = height - 38
            boxes = [
                (0, top, width / 2 - 8, bottom),
                (width / 2 + 8, top, width, bottom),
            ]
            for box in boxes:
                parts.extend(clean_lines(page.crop(box).extract_text(x_tolerance=1, y_tolerance=3) or ""))
    return "\n".join(parts)


def split_question_blocks(text: str) -> list[tuple[int, str]]:
    blocks = []
    current_no = None
    current_lines = []

    for line in text.splitlines():
        match = re.match(r"^(\d{1,3})\.\s*(.*)", line)
        if match:
            if current_no is not None:
                blocks.append((current_no, "\n".join(current_lines)))
            current_no = int(match.group(1))
            current_lines = [match.group(2).strip()]
        elif current_no is not None:
            current_lines.append(line)

    if current_no is not None:
        blocks.append((current_no, "\n".join(current_lines)))
    return blocks


def split_options(option_text: str, mode: str) -> list[str]:
    if mode == "circled":
        pattern = r"([①②③④])"
        marker_map = CIRCLED
    else:
        pattern = r"(?<![가-힣])([가나다라])\."
        marker_map = HANGUL

    parts = re.split(pattern, option_text)
    options = ["", "", "", ""]
    index = 0
    while index < len(parts):
        marker = parts[index]
        if marker in marker_map and index + 1 < len(parts):
            options[marker_map[marker] - 1] += " " + parts[index + 1]
            index += 2
        else:
            index += 1
    return [squeeze(option) for option in options]


def parse_block(block: str, fallback_answer: int | None) -> dict:
    mode = "circled" if re.search(r"[①②③④]", block) else "hangul"
    marker_pattern = r"[①②③④]" if mode == "circled" else r"(?<![가-힣])[가나다라]\."
    marker_match = re.search(marker_pattern, block)
    if not marker_match:
        raise ValueError(f"선택지 표식을 찾지 못했습니다: {block[:100]}")

    question = block[: marker_match.start()]
    option_text = block[marker_match.start() :]
    answer = fallback_answer

    if mode == "circled":
        answer_match = re.search(r"\s([1-4])\s*$", question)
        if answer_match:
            answer = int(answer_match.group(1))
            question = question[: answer_match.start()]

    options = split_options(option_text, mode)
    if len(options) != 4 or any(not option for option in options):
        raise ValueError(f"선택지 4개 파싱 실패: {question[:80]} / {options}")
    if answer not in (1, 2, 3, 4):
        raise ValueError(f"정답 없음: {question[:80]}")

    return {
        "question": squeeze(question),
        "options": options,
        "answer": answer - 1,
    }


def is_negative_question(question: str) -> bool:
    negative_words = ["옳지", "아닌", "아닌것", "아닌 것은", "적절하지", "틀린", "잘못된", "해당하지"]
    return any(word in question for word in negative_words)


OPTION_RULES = [
    (["위, 아래, 좌, 우 4방향"], "단면 상자는 좌우와 상하뿐 아니라 앞뒤 방향 면도 조정할 수 있어 4방향만 조정한다는 설명은 맞지 않습니다."),
    (["부분 상세"], "부분 상세는 도면 표현을 보완하는 상세 요소에 가깝고, 프로젝트 브라우저가 모든 도면화 요소를 직접 관리한다는 뜻은 아닙니다."),
    (["공간 범위를 정의"], "공간객체는 층, 실, 구역처럼 건축물 안의 공간 범위를 정보로 정의하는 객체를 말합니다."),
    (["에너지 사용 성격"], "에너지 사용 성격은 분석을 위한 속성 구분에 가깝고, 공간객체 자체의 정의와는 다릅니다."),
    (["구조 기초"], "구조 기초는 구조 기준선과 위치 기준을 활용해 배치하는 부재로 다루어집니다."),
    (["구조 바닥"], "구조 바닥은 주로 경계 스케치와 레벨을 기준으로 작성하는 면 요소라 그리드 자동배치 기능 대상과 거리가 있습니다."),
    (["구조 프레임"], "구조 프레임은 보와 같은 선형 구조 부재로, 그리드 기준 배치와 연결해 다루는 경우가 많습니다."),
    (["구조 기둥"], "구조 기둥은 그리드 교차점 같은 기준 위치에 자동 배치하는 대표 구조 요소입니다."),
    (["프로젝트 브라우저"], "프로젝트 브라우저는 프로젝트 안의 뷰, 시트, 일람표, 패밀리 목록을 열고 관리하는 패널입니다."),
    (["보행 시선", "보행시선"], "보행시선은 카메라 경로를 따라 모델 내부를 이동하며 검토하는 기능입니다."),
    (["파일 탐색기"], "파일 탐색기는 운영체제에서 파일을 관리하는 개념이고, Revit 프로젝트 내부 뷰 관리 기능은 아닙니다."),
    (["뷰를 관리", "뷰의 이름", "뷰 추가"], "Revit의 뷰 관리는 평면도, 입면도, 3D뷰, 시트 등을 찾아 열고 정리하는 작업입니다."),
    (["단면 상자"], "단면 상자는 3D뷰에서 모델을 박스 형태로 잘라 특정 범위나 내부를 확인할 때 사용합니다."),
    (["가시성", "그래픽"], "가시성/그래픽은 해당 뷰에서 카테고리와 요소가 어떻게 보일지 조정하는 설정입니다."),
    (["뷰 템플릿"], "뷰 템플릿은 여러 뷰에 같은 표시 설정을 반복 적용해 도면 표현을 일관되게 만드는 기능입니다."),
    (["Clash Detective", "간섭"], "Clash Detective는 Navisworks에서 통합된 3D 모델 요소 사이의 충돌을 찾는 대표 도구입니다."),
    (["리포트", "보고서"], "검토 결과를 리포트로 내보내면 간섭 위치와 상태를 협업자에게 전달하기 쉽습니다."),
    (["유형 특성"], "유형 특성은 같은 유형을 쓰는 모든 요소에 공통으로 적용되는 설정입니다."),
    (["인스턴스", "선택한 요소"], "인스턴스 특성은 선택한 개별 요소에만 적용되는 값입니다."),
    (["파라미터", "매개변수"], "매개변수는 객체의 치수, 재료, 표기 정보처럼 모델 정보를 담는 값입니다."),
    (["정렬 치수"], "정렬 치수는 평행한 기준선이나 여러 점 사이의 거리를 표시할 때 사용합니다."),
    (["반지름 치수"], "반지름 치수는 원호나 곡선의 반지름 값을 표시하는 치수 도구입니다."),
    (["지정점 레벨"], "지정점 레벨은 특정 지점의 높이값을 표시하는 주석이며 일반 치수 도구와 구분됩니다."),
    (["지정점 좌표"], "지정점 좌표는 프로젝트 기준에 따른 동서/남북 좌표값을 표시하는 주석입니다."),
    (["일람표"], "일람표는 모델 요소의 정보를 표로 보여주며 모델 데이터와 연결되어 함께 갱신됩니다."),
    (["상세선"], "상세선은 특정 뷰에서 도면 표현을 보완하기 위한 2D 선 요소입니다."),
    (["채워진 영역"], "채워진 영역은 닫힌 영역에 패턴을 채워 상세 표현을 만드는 2D 주석 요소입니다."),
    (["구름형 수정기호"], "구름형 수정기호는 변경된 설계 영역을 시트나 뷰에서 표시할 때 사용합니다."),
    (["단열재"], "단열재 주석은 작성한 뷰의 도면 표현에 배치되는 요소이며 모든 뷰에 자동 표시되는 모델 요소가 아닙니다."),
    (["패밀리 로드"], "패밀리 로드는 현재 프로젝트에 없는 외부 패밀리를 불러오는 명령입니다."),
    (["장비 로드", "컴포넌트 로드", "기구 로드"], "이 표현은 Revit의 일반적인 외부 패밀리 불러오기 명령 이름으로 보기 어렵습니다."),
    (["상세 요소"], "상세 요소는 모델 전체에 영향을 주기보다 작성한 뷰의 2D 도면 표현에 사용됩니다."),
    (["저장된 관측점", "관측점"], "관측점은 현재 화면 방향, 위치, 표시 상태를 저장해 검토 지점으로 다시 돌아갈 수 있게 합니다."),
    (["선택 트리"], "선택 트리는 Navisworks에서 모델을 파일과 요소 계층 구조로 보여주는 패널입니다."),
    (["특성"], "특성 패널은 선택한 요소나 뷰의 속성 값을 확인하고 수정할 때 사용합니다."),
    (["레벨"], "레벨은 층과 수직 기준 높이를 정의하며 평면도, 입면도, 모델 요소 구속에 연결됩니다."),
    (["형상 결합"], "형상 결합은 겹치는 모델 요소의 중복 형상을 정리해 하나처럼 보이게 할 때 사용합니다."),
    (["코핑"], "코핑은 주로 구조 부재 끝단을 다른 부재 형상에 맞춰 잘라내는 구조 모델링 기능입니다."),
    (["면 분할"], "면 분할은 하나의 면을 나눠 서로 다른 재료나 표현을 적용할 때 사용합니다."),
    (["페인트"], "페인트는 요소의 면에 재료를 덧입혀 보이게 하는 도구입니다."),
    (["그리드"], "그리드는 기둥과 주요 구조 축을 잡는 기준선으로 협업과 배치 기준에 중요합니다."),
    (["참조 평면"], "참조 평면은 모델링 기준이나 패밀리 제작 기준으로 쓰는 보조 평면입니다."),
    (["작업 기준면", "작업면"], "작업 기준면은 요소를 작성할 기준 평면을 지정하는 개념입니다."),
    (["벽"], "벽은 Revit에서 레벨, 구속조건, 레이어, 재료 정보를 갖는 대표적인 시스템 패밀리입니다."),
    (["바닥"], "바닥은 스케치 경계와 구조/마감 레이어를 통해 작성되는 수평 건축 요소입니다."),
    (["지붕"], "지붕은 스케치나 면 기반 방식으로 건물 상부를 구성하는 시스템 요소입니다."),
    (["천장"], "천장은 천장 평면도에서 작성하며 실내 마감과 조명 배치 기준이 됩니다."),
    (["계단"], "계단은 건축 탭에서 실행하며 계단진행, 계단참, 지지, 난간 등으로 구성됩니다."),
    (["난간"], "난간은 계단/경사로와 연결하거나 경로를 직접 그려 작성할 수 있는 시스템 패밀리입니다."),
    (["커튼월"], "커튼월은 그리드, 멀리언, 패널로 구성되는 벽 유형이며 패널 교체로 문도 넣을 수 있습니다."),
    (["커튼월패널", "패널"], "커튼월 패널은 커튼월 시스템에서 유리, 문, 다른 패널 유형으로 교체 가능한 구성요소입니다."),
    (["멀리언"], "멀리언은 커튼월 그리드 위에 배치되는 프레임 부재입니다."),
    (["재질", "재료"], "재질은 요소의 그래픽 표시, 렌더링, 물량 정보에 영향을 주는 속성입니다."),
    (["레이어"], "레이어는 벽, 바닥, 지붕처럼 여러 재료층을 가진 시스템 요소의 구조를 구성합니다."),
    (["간격띄우기"], "간격띄우기는 기준 레벨이나 기준선에서 일정 거리만큼 떨어뜨려 요소를 배치하는 값입니다."),
    (["프로파일"], "프로파일 편집은 벽이나 바닥 경계 형상을 수정하는 작업이며 재료 레이어 구성 변경과는 다릅니다."),
    (["시트"], "시트는 뷰와 일람표를 배치해 출력용 도면 한 장을 구성하는 페이지입니다."),
    (["콜아웃"], "콜아웃은 특정 영역을 확대하거나 다른 뷰를 참조해 상세 도면을 만들 때 사용합니다."),
    (["가는 선"], "가는 선은 화면 표시에서 선 두께를 단일 폭으로 보여주는 Revit 기능입니다."),
    (["TL"], "TL은 Revit에서 가는 선 기능에 쓰이는 대표 단축키입니다."),
    (["VV", "VG"], "VV 또는 VG는 Revit에서 가시성/그래픽 대화상자를 여는 단축키입니다."),
    (["ZE"], "ZE는 Zoom Extents처럼 전체 범위를 화면에 맞추는 확대/축소 계열 단축키입니다."),
    (["WT"], "WT는 Window Tile, 즉 창 배열과 관련된 단축키입니다."),
    (["AL"], "AL은 Align, 즉 정렬 도구의 단축키입니다."),
    (["OF"], "OF는 Offset, 즉 간격 띄우기 도구의 단축키입니다."),
    (["LS"], "LS는 Revit 기본 단축키에서 간격 띄우기(Offset)를 의미하지 않습니다."),
    (["LI"], "LI는 일반적으로 모델 선(Model Line) 계열 단축키로 쓰이며 간격 띄우기 단축키가 아닙니다."),
    (["MA"], "MA는 Match Type Properties, 즉 유형 특성 일치 도구의 단축키입니다."),
    (["HR"], "HR은 가시성/그래픽 재지정(VV/VG) 단축키가 아닙니다."),
    (["WA"], "WA는 Wall, 즉 벽 작성 도구의 단축키입니다."),
    (["CS"], "CS는 가시성/그래픽 재지정(VV/VG) 단축키가 아닙니다."),
    (["설계 옵션"], "설계 옵션은 같은 프로젝트 안에서 대안 설계를 나누어 비교하고 관리하는 기능입니다."),
    (["작업 세트"], "작업 세트는 작업공유 프로젝트에서 요소를 작업 범위별로 나누어 관리하는 단위입니다."),
    (["중앙 파일"], "중앙 파일은 작업공유 프로젝트에서 모든 로컬 파일 변경 사항이 모이고 배포되는 기준 파일입니다."),
    (["로컬 파일"], "로컬 파일은 사용자가 자신의 컴퓨터에서 작업한 뒤 중앙 파일과 동기화하는 사본입니다."),
    (["동기화"], "동기화는 로컬 변경 사항을 중앙 파일에 반영하고 중앙의 변경 사항을 다시 받아오는 작업입니다."),
    (["링크"], "링크 모델은 원본 파일과 연결된 참조 모델로, 원본 수정 후 다시 불러와 최신 상태로 맞출 수 있습니다."),
    (["그룹으로 로드"], "그룹으로 로드는 외부 모델 그룹을 프로젝트로 가져와 내부에서 사용할 수 있게 하는 방식입니다."),
    (["스위치백"], "스위치백은 Navisworks에서 선택한 요소를 원본 작성 프로그램 위치로 되돌려 확인하는 기능입니다."),
    (["NWF"], "NWF는 Navisworks 작업 파일로, 연결된 모델과 검토 설정을 저장하는 형식입니다."),
    (["NWC"], "NWC는 Navisworks 캐시 파일 형식입니다."),
    (["NWD"], "NWD는 Navisworks 모델과 검토 데이터를 패키징해 공유하는 형식입니다."),
    (["RFA"], "RFA는 Revit 패밀리 파일 형식으로 Navisworks 저장 확장자와는 다릅니다."),
    (["RVT", "rvt"], "RVT는 Revit 프로젝트 파일 형식입니다."),
    (["CAD"], "CAD 파일은 Revit에서 링크하거나 가져올 수 있는 도면 파일 계열입니다."),
    (["DWF"], "DWF는 설계 검토와 공유용 Autodesk 파일 형식으로 Revit에서 링크 대상으로 다룰 수 있습니다."),
    (["docx"], "docx는 Word 문서 파일 형식이라 Revit 모델 링크 형식이 아닙니다."),
    (["pptx"], "pptx는 PowerPoint 프레젠테이션 형식이라 Revit 저장 파일 형식이 아닙니다."),
    (["RTE", "rte"], "RTE는 Revit 프로젝트 템플릿 파일 형식입니다."),
    (["IFC"], "IFC는 서로 다른 BIM 소프트웨어 간 객체 정보를 교환하기 위한 개방형 표준 포맷입니다."),
    (["CAD 가져오기"], "CAD 가져오기는 외부 CAD 도면을 Revit 프로젝트에 불러오는 삽입 계열 기능입니다."),
    (["BIM"], "BIM은 단순 3D 형상뿐 아니라 객체 정보와 생애주기 정보를 함께 다루는 모델 기반 업무 방식입니다."),
    (["3D 모델"], "단순 3D 모델은 주로 형상 표현에 머물 수 있지만 BIM은 객체 정보와 속성 데이터를 함께 다룹니다."),
    (["전 생애주기"], "BIM은 설계, 시공, 유지관리까지 이어지는 건축물 생애주기 정보 관리에 활용됩니다."),
    (["파라메트릭"], "파라메트릭 모델링은 치수와 제약조건을 바꾸면 관련 형상과 정보가 함께 갱신되는 방식입니다."),
    (["상호운용성"], "상호운용성은 서로 다른 프로그램과 참여자가 BIM 정보를 교환하고 재사용할 수 있는 능력입니다."),
    (["EXPRESS", "UML"], "EXPRESS와 UML은 BIM 정보모델을 정의하거나 표현할 때 언급되는 모델링 언어입니다."),
    (["IPD"], "IPD는 참여자 간 통합 협업, 공동 목표, 상호 신뢰를 강조하는 프로젝트 수행 방식입니다."),
    (["CORENET"], "CORENET은 싱가포르의 건설 인허가 전자 제출·승인 시스템 사례입니다."),
    (["BIM 매뉴얼", "BIM 핸드북", "BIM 설계 업무지침서", "시설사업 BIM적용 기본지침서"], "공공 BIM 기준 명칭 문제는 발주기관의 공식 지침서 이름을 구분하는 유형입니다."),
    (["품질", "해상도", "출력설정", "배경", "그림자"], "렌더링 설정은 품질과 해상도, 조명·배경 조건에 따라 시간과 결과가 달라집니다."),
    (["초안", "중간", "낮음", "높음"], "렌더 품질은 낮을수록 계산량이 적어 빠르고, 높을수록 시간이 오래 걸립니다."),
    (["지형면"], "지형면은 대지의 높이와 지형 형태를 표현하는 Revit 대지 모델 요소입니다."),
    (["태그"], "태그는 요소의 매개변수 값을 도면에 문자로 표시하는 주석 요소입니다."),
    (["다중카테고리"], "다중카테고리 태그는 여러 카테고리에 공통으로 적용되는 공유 매개변수를 표시할 수 있습니다."),
    (["주석"], "주석은 치수, 문자, 태그, 기호처럼 도면 정보를 설명하기 위해 배치하는 요소입니다."),
    (["표제블록"], "표제블록은 시트에 들어가는 도면명, 프로젝트명, 작성자 등 도면 정보를 담는 패밀리입니다."),
]


def option_detail(question: str, option: str) -> str:
    for keywords, detail in OPTION_RULES:
        if any(keyword in option for keyword in keywords):
            return detail
    return ""


def make_option_explanations(item: dict) -> list[str]:
    question = item["question"]
    correct_index = item["answer"]
    negative = is_negative_question(question)
    explanations = []

    for index, option in enumerate(item["options"]):
        detail = option_detail(question, option)
        if not detail:
            explanations.append("")
            continue
        label = "정답" if index == correct_index else "오답"
        explanations.append(f"{optionMarks(index)} {label}: {detail}")

    return explanations


def optionMarks(index: int) -> str:
    return ["①", "②", "③", "④"][index]


def matching_note(question: str, correct: str) -> str:
    text = f"{question} {correct}"
    rules = [
        (["프로젝트 브라우저"], "프로젝트 브라우저는 뷰, 시트, 패밀리 등을 찾아 열고 관리하는 Revit의 탐색 패널입니다."),
        (["뷰 템플릿"], "뷰 템플릿은 뷰의 가시성, 그래픽, 축척 같은 설정을 여러 뷰에 일관되게 적용하는 기능입니다."),
        (["3D뷰", "3차원 뷰"], "3D뷰는 단면 상자, 가시성/그래픽, 뷰 템플릿 등으로 모델을 확인하고 표현하는 뷰입니다."),
        (["단면 상자"], "단면 상자는 3D 모델을 입체적으로 잘라 내부나 특정 범위를 확인할 때 사용합니다."),
        (["유형 특성", "특성의 차이"], "유형 특성은 같은 유형 전체에, 인스턴스 특성은 선택한 개별 요소에 영향을 줍니다."),
        (["일람표"], "일람표는 모델 데이터와 연결된 표이므로 모델이나 표의 변경이 서로 반영됩니다."),
        (["패밀리 로드"], "프로젝트에 없는 외부 패밀리는 '패밀리 로드'로 불러와 사용할 수 있습니다."),
        (["상세 요소", "상세선", "채워진 영역"], "상세 요소는 모델 자체가 아니라 작성한 뷰에서 도면 표현을 보완하는 2D 요소입니다."),
        (["Clash Detective", "간섭"], "Navisworks의 Clash Detective는 통합 3D 모델의 요소 충돌을 찾아 검토하는 도구입니다."),
        (["레벨"], "레벨은 층과 수직 기준 높이를 정의하며 평면도와 입면도 등 모델 기준에 연결됩니다."),
        (["그리드"], "그리드는 기둥, 벽 등 주요 부재 배치를 위한 수평 기준선 역할을 합니다."),
        (["벽"], "Revit의 벽은 레벨 구속, 프로파일, 레이어, 재료 등을 통해 형상과 정보를 함께 관리합니다."),
        (["커튼월"], "커튼월은 패널, 그리드, 멀리언으로 구성되며 패널 교체나 문 삽입도 가능합니다."),
        (["문", "창"], "문과 창은 벽이나 커튼월에 삽입되는 호스트 기반 패밀리로 일람표와 태그 작성이 가능합니다."),
        (["시트"], "시트는 뷰, 일람표, 주석을 배치해 출력용 도면을 구성하는 페이지입니다."),
        (["뷰 컨트롤 막대"], "뷰 컨트롤 막대에서는 축척, 상세 수준, 비주얼 스타일, 자르기 등 현재 뷰 표시를 조정합니다."),
        (["가시성", "그래픽"], "가시성/그래픽 설정은 뷰별로 카테고리와 요소의 표시 방식을 조절합니다."),
        (["단축키"], "단축키 문제는 기능명과 약어를 짝지어 기억하는 유형입니다."),
        (["렌더"], "렌더링은 품질, 해상도, 조명, 배경, 표시 범위에 따라 시간과 결과가 달라집니다."),
        (["보행시선"], "보행시선은 카메라 경로를 따라 건물을 검토하고 이미지나 동영상으로 확인하는 기능입니다."),
        (["작업공유", "공동작업", "중앙 파일", "로컬 파일", "작업 세트"], "작업공유는 중앙 파일과 로컬 파일, 작업 세트를 이용해 여러 사용자가 한 모델을 나누어 작업하는 방식입니다."),
        (["링크"], "링크 모델은 원본과 연결된 참조 모델이며, 업데이트와 일부 요소 복사에 활용됩니다."),
        (["그룹으로 로드"], "그룹으로 로드는 외부 모델 그룹을 프로젝트에 불러와 프로젝트 내부에서 활용하는 방식입니다."),
        (["매스", "대지"], "매스작업과 대지 도구는 초기 형상, 지형면, 소구역, 대지 경계 등을 다룰 때 사용합니다."),
    (["지형면 소구역은 기존 지형면 외부"], "소구역은 기존 지형면 위에 경계를 스케치해 그 지형면의 일부 영역을 나누는 기능입니다. 기존 지형면 바깥에 만드는 영역이 아니므로 이 설명은 틀립니다."),
    (["소구역을 사용하면 도로", "주차장을 그릴"], "소구역은 지형면 위에 재료가 다른 도로, 포장면, 주차장 같은 영역을 표현할 때 사용할 수 있습니다."),
    (["경계 편집"], "이미 만든 소구역은 경계 편집으로 스케치 경계를 수정해 영역 모양을 바꿀 수 있습니다."),
    (["소구역은 다중"], "하나의 대지 안에서도 여러 소구역을 만들어 서로 다른 포장면이나 구역을 나누어 표현할 수 있습니다."),
    (["소구역"], "소구역은 기존 지형면 위에 도로, 주차장 같은 영역을 나누어 표현하는 도구입니다."),
    (["표면 분할"], "표면 분할은 기존 지형면을 별도의 지형면 조각으로 나누는 기능입니다. 내부에 다른 지형면을 새로 작성한다는 설명과는 다릅니다."),
    (["표면 병합"], "표면 병합은 분리되어 있는 지형면을 하나의 지형면으로 합칠 때 사용하는 대지 수정 기능입니다."),
    (["대지 경계선"], "대지 경계선은 평면도에서 부지의 법적 경계나 대지 영역을 표시하기 위해 작성합니다."),
    (["데이터 가져오기를 통해 생성한 지형"], "가져온 데이터로 만든 지형도 점 편집이나 대지 수정 도구를 통해 조정할 수 있으므로, 전혀 수정할 수 없다는 설명은 틀립니다."),
    (["점 배치"], "점 배치는 각 점의 높이값을 지정해 지형면을 만들거나 지형 높이를 조정하는 방식입니다."),
    (["대지경계선을 따라 스케치"], "대지경계선은 경계를 스케치해 부지 범위를 표현하는 기능입니다."),
        (["지형"], "대지 모델은 점, 등고선, 가져오기 데이터 등을 이용해 지형면을 만들고 수정합니다."),
        (["형상 결합"], "형상 결합은 서로 겹치는 모델 요소의 중복 형상을 정리해 하나처럼 표현할 때 사용합니다."),
        (["코너로 자르기", "자르기/연장"], "코너로 자르기/연장은 벽이나 선을 코너에서 만나도록 자르거나 연장하는 수정 도구입니다."),
        (["설계 옵션"], "설계 옵션은 하나의 프로젝트 안에서 여러 대안 설계를 비교하고 관리하는 기능입니다."),
        (["패밀리"], "패밀리는 Revit에서 반복 사용하는 객체 단위이며 유형, 치수, 재료, 매개변수를 가질 수 있습니다."),
        (["매개변수"], "매개변수는 객체의 정보와 동작을 정의하는 값이며 일람표, 태그, 유형 관리에 활용됩니다."),
        (["태그"], "태그는 요소의 매개변수 값을 도면에 표시하는 주석 요소입니다."),
        (["다중카테고리 태그"], "다중카테고리 태그는 여러 카테고리에 공통으로 쓰는 공유 매개변수 정보를 표시할 수 있습니다."),
        (["룸", "공간"], "룸과 공간 객체는 실, 층, 영역 같은 공간 정보를 모델 안에서 관리하는 데 사용됩니다."),
        (["Navisworks", "NAVISWORKS", "나비스웍스"], "Navisworks는 여러 모델을 통합해 검토, 간섭 확인, 관측점, 시뮬레이션 등에 활용하는 도구입니다."),
        (["스위치백"], "스위치백은 Navisworks에서 선택한 요소를 원본 작성 도구로 되돌려 확인하는 기능입니다."),
        (["관측점"], "관측점은 현재 화면 상태와 검토 위치를 저장해 이슈 확인이나 리뷰에 활용합니다."),
        (["파일 형식", "확장자", "저장할 수 있는"], "확장자 문제는 Revit과 Navisworks가 실제로 저장하거나 링크할 수 있는 파일 형식을 구분하는 유형입니다."),
        (["IFC"], "IFC는 서로 다른 BIM 소프트웨어 간 정보 교환을 위한 개방형 표준 포맷입니다."),
        (["BIM 개념", "BIM의 도입", "BIM을 활용"], "BIM은 3D 형상뿐 아니라 속성 정보와 생애주기 정보를 함께 다루는 모델 기반 업무 방식입니다."),
        (["파라메트릭"], "파라메트릭 모델링은 치수와 제약조건 변경이 관련 형상과 정보에 함께 반영되는 방식입니다."),
        (["상호운용성"], "상호운용성은 서로 다른 시스템과 참여자가 BIM 정보를 정확하게 교환하고 재사용할 수 있는 능력입니다."),
        (["IPD"], "IPD는 참여자 간 신뢰, 공동 목표, 협업을 바탕으로 프로젝트를 통합 수행하는 방식입니다."),
        (["CORENET"], "CORENET은 싱가포르의 건설 행정 전자 제출·승인 체계와 관련된 대표 사례입니다."),
        (["조달청"], "조달청 BIM 지침은 공공 시설공사에서 BIM 모델 작성, 납품, 활용 기준을 정리한 자료입니다."),
    ]

    for keywords, note in rules:
        if any(keyword in text for keyword in keywords):
            return note
    return ""


def make_explanation(item: dict) -> str:
    return "\n".join(make_option_explanations(item))


def find_source(path: Path) -> dict:
    for source in SOURCES:
        if source["match"] in path.name:
            return source
    return {}


def main() -> None:
    questions = []
    warnings = []
    generated_from = []

    for pdf_path in sorted(Path(".").glob("*.pdf")):
        source = find_source(pdf_path)
        if not source:
            print(f"건너뜀: {pdf_path.name}")
            continue
        generated_from.append(pdf_path.name)
        if source["kind"] == "single":
            text = extract_single_column(pdf_path)
            answer_map = {}
        else:
            start, end = source["question_pages"]
            text = extract_columns(pdf_path, start, end)
            answer_map = {i + 1: answer for i, answer in enumerate(source["answers"])}

        parsed_for_source = []
        for number, block in split_question_blocks(text):
            if source["kind"] == "columns" and number > len(source["answers"]):
                continue
            try:
                item = parse_block(block, answer_map.get(number))
            except ValueError as error:
                warnings.append(f"{pdf_path.name} #{number}: {error}")
                continue
            item["optionExplanations"] = make_option_explanations(item)
            item["explanation"] = make_explanation(item)
            item.update(
                {
                    "id": f"{pdf_path.stem}-{number}",
                    "number": number,
                    "source": source["title"],
                    "file": pdf_path.name,
                }
            )
            parsed_for_source.append(item)

        questions.extend(parsed_for_source)
        print(f"{source['title']}: {len(parsed_for_source)}문항")

    out = {
        "generatedFrom": generated_from,
        "total": len(questions),
        "questions": questions,
    }
    Path("data/questions.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/questions.js").write_text(
        "window.BIM_QUESTIONS = "
        + json.dumps(out, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"총 {len(questions)}문항 저장: data/questions.json")
    if warnings:
        print("\n경고:")
        for warning in warnings:
            print("-", warning)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
