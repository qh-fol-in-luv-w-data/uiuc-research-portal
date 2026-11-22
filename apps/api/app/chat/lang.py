"""Reply language for the assistant (English or Vietnamese) and its fixed, non-LLM replies."""
from __future__ import annotations

import re

VI_LETTERS = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)
# Vietnamese typed without accents ("giang vien nao nghien cuu robot"): needs two of these syllables
_VI_ASCII = re.compile(r"\b(nghien|cuu|giang|vien|bai|bao|nhung|cac|nao|cua|moi|nhat|gan|day|trich|dan|linh|vuc|"
                       r"cong|bo|giao|su|chuyen|gia|la|gi|ve)\b", re.I)
_EN_WORDS = re.compile(r"\b(the|what|which|who|papers?|publications?|on|of|and|is|are|in|for|about|most|recent|"
                       r"latest|faculty|work|works|research)\b", re.I)


def reply_language(question: str, ui_lang: str = "en") -> str:
    """Answer in the question's language; a question with no clear signal ("graphene") follows the UI language."""
    if VI_LETTERS.search(question) or len(_VI_ASCII.findall(question)) >= 2:
        return "vi"
    if _EN_WORDS.search(question):
        return "en"
    return "vi" if ui_lang == "vi" else "en"


TEXT = {
    "en": {
        "out_of_scope": "I can only help with research at the University of Illinois Urbana-Champaign (UIUC): recent "
                        "publications, notable papers and faculty expertise. Try asking about a research topic.",
        "broad": "UIUC research spans engineering, computer science, agriculture, life sciences, physics and more; the "
                 "Research focus areas section above shows the main fields. Ask me about a specific topic, for example "
                 "\"most recent papers on quantum computing\" or \"which faculty work on crop genetics?\"",
        "no_results": "I couldn't find UIUC publications or faculty from the last two years about {topic}. "
                      "Try a broader or differently worded question.",
        "this_topic": "this topic",
        "and": " and ",
        "error": "The assistant could not finish: {exc}",
        "newest": "The most recent matching paper is \"{title}\" ({date}) [1].",
    },
    "vi": {
        "out_of_scope": "Tôi chỉ hỗ trợ các câu hỏi về nghiên cứu tại Đại học Illinois Urbana-Champaign (UIUC): công bố "
                        "gần đây, bài báo nổi bật và chuyên môn của giảng viên. Hãy thử hỏi về một chủ đề nghiên cứu.",
        "broad": "Nghiên cứu của UIUC trải rộng từ kỹ thuật, khoa học máy tính, nông nghiệp, khoa học sự sống đến vật lý; "
                 "mục Lĩnh vực nghiên cứu trọng tâm ở trên cho thấy các lĩnh vực chính. Hãy hỏi về một chủ đề cụ thể, "
                 "ví dụ \"bài báo mới nhất về điện toán lượng tử\" hoặc \"giảng viên nào nghiên cứu di truyền cây trồng?\"",
        "no_results": "Tôi không tìm thấy công bố hay giảng viên nào của UIUC trong hai năm qua về {topic}. "
                      "Hãy thử hỏi rộng hơn hoặc diễn đạt theo cách khác.",
        "this_topic": "chủ đề này",
        "and": " và ",
        "error": "Trợ lý không thể hoàn tất câu trả lời: {exc}",
        "newest": "Công bố phù hợp mới nhất là \"{title}\" ({date}) [1].",
    },
}

# Source-card labels shown in the UI (the answer model always reads the English source text).
CARD = {
    "en": {"months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
           "types": {"article": "Article", "preprint": "Preprint", "conference-paper": "Conference paper",
                     "book-chapter": "Book chapter", "review": "Review"},
           "undated": "undated", "matched": "matched"},
    "vi": {"months": None,
           "types": {"article": "Bài báo", "preprint": "Preprint", "conference-paper": "Bài hội nghị",
                     "book-chapter": "Chương sách", "review": "Bài tổng quan"},
           "undated": "không rõ ngày", "matched": "khớp"},
}


def text(lang: str, key: str) -> str:
    return TEXT.get(lang, TEXT["en"])[key]
