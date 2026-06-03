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
        (["소구역"], "소구역은 기존 지형면 위에 도로, 주차장 같은 영역을 나누어 표현하는 도구입니다."),
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
    question = item["question"]
    correct = item["options"][item["answer"]]
    note = matching_note(question, correct)

    if is_negative_question(question):
        if note:
            return f"{note} 이 문제는 옳지 않은 보기를 고르는 유형이며, '{correct}'가 실제 기능이나 개념과 맞지 않는 설명입니다."
        return f"이 문제는 옳지 않은 보기를 고르는 유형입니다. '{correct}'가 실제 기능이나 개념과 맞지 않아 정답입니다."

    if note:
        return f"{note} 따라서 이 문항에서는 '{correct}'가 정답입니다."
    return f"문제에서 묻는 핵심 개념에 해당하는 항목은 '{correct}'입니다. 정답 표현과 용어를 함께 기억해두면 좋습니다."


def find_source(path: Path) -> dict:
    for source in SOURCES:
        if source["match"] in path.name:
            return source
    return {}


def main() -> None:
    questions = []
    warnings = []

    for pdf_path in sorted(Path(".").glob("*.pdf")):
        source = find_source(pdf_path)
        if not source:
            print(f"건너뜀: {pdf_path.name}")
            continue
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
        "generatedFrom": [p.name for p in sorted(Path(".").glob("*.pdf"))],
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
