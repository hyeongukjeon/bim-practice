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
