/**
 * UI strings in English and Vietnamese. Data (paper titles, topics, venues, names) stays in its original language;
 * OpenAlex field names, publication types, countries, numbers and dates are localized.
 * Plain module (no "server-only"): server components read it via getT(), client components via useI18n().
 */
export const LOCALES = ["en", "vi"] as const;
export type Locale = (typeof LOCALES)[number];
export const hasLocale = (x: string | undefined | null): x is Locale => !!x && (LOCALES as readonly string[]).includes(x);

const en = {
  langName: "English",
  meta: {
    title: "UIUC Research Portal",
    description: "Two years of University of Illinois Urbana-Champaign research, from OpenAlex, with a research assistant.",
  },
  skip: "Skip to content",
  header: {
    brand: "UIUC Research Portal",
    nav: "Sections",
    links: { focus: "Focus areas", output: "Scholarly output", notable: "Notable publications", faculty: "Faculty expertise", collab: "Collaboration" },
    ask: "Ask the research assistant",
    switchTo: "Tiếng Việt",
    switchLabel: "Xem bằng tiếng Việt",
  },
  hero: {
    eyebrow: "University of Illinois Urbana-Champaign · Research profile",
    lines: ["What Illinois researchers", "published in the", "last two years"],
    lead: (n: string) => `Every number on this page is computed from OpenAlex records affiliated with UIUC, linked to ${n} faculty profiles.`,
    kpis: {
      works: ["Publications", "articles, preprints, conference papers, chapters, reviews"],
      citations: ["Citations received", "to those publications, per OpenAlex"],
      oa: ["Open access", "free to read at publication"],
      faculty: ["Faculty profiles", ""],
    },
    linked: (n: string, pct: string) => `${n} matched to OpenAlex authors (${pct})`,
    photo: "Photo",
    founded: "Founded",
  },
  sections: {
    focus: ["Research focus areas", "Publications grouped by the OpenAlex field of their primary topic. Tile size follows publication count; select a field to explore it."],
    output: ["Scholarly output", "About a thousand works a month. January peaks include works OpenAlex dates only by year, which it files under 1 January."],
    notable: ["Notable publications", "The most cited and the newest UIUC works. Names in bold are faculty in the directory; select one to open their profile."],
    faculty: ["Faculty expertise", "Search 999 faculty profiles by research keyword. Profiles linked to OpenAlex also show topics and recent publications."],
    collab: ["Collaboration & campus", ""],
    assistant: ["AI research assistant", "Answers questions from the UIUC records on this page and cites every source, in English or Vietnamese. It runs on a local model, so nothing you ask leaves this server."],
  },
  errors: {
    section: (what: string) => `${what} could not be loaded because the data service did not respond. Start the API with`,
    reload: "and reload.",
    overview: "The research overview",
    collab: "Collaboration data",
  },
  footer: {
    data: "Data:",
    rest: "(CC0) · faculty directory provided with the assessment · map © OpenStreetMap contributors",
    unofficial: "Not an official University of Illinois site",
  },
  focus: {
    showing: "Showing",
    across: "across the page · Clear filter",
    hint: "Select a field to see its subfields, rising topics and leading faculty, and to filter the page.",
    tilesLabel: "Research fields by number of publications",
    works: (n: string) => `${n} works`,
    topSub: "Top:",
    noRising: "No topic in this field has grown on enough recent works.",
    noFaculty: "No linked faculty publish in this field yet.",
    status: (n: string, field: string): [string, string] => [`${n}`, ` works in ${field}. Notable publications and faculty below are filtered too.`],
    pubs: "Publications",
    faculty: "Faculty",
    subfields: (f: string) => `Subfields of ${f}`,
    subfieldsNote: "Works by subfield of their primary topic.",
    risingField: "Rising in this field",
    risingFieldNote: "Last 12 months against the 12 before, at least 10 recent works.",
    topField: "Most published in this field",
    topFieldNote: "Linked faculty by works in this field. Select a name for the profile.",
    rising: "Rising topics",
    risingNote: "Last 12 months against the 12 before, topics with at least 40 recent works.",
    top: "Most published faculty",
    topNote: "Works by faculty matched to an OpenAlex author profile. Select a name for the profile.",
  },
  output: {
    summary: (from: string, to: string, lo: string, hi: string, max: string) =>
      `Monthly publications from ${from} to ${to}: usually ${lo} to ${hi} a month, peaking at ${max} in January.`,
    works: (n: string) => `${n} works`,
    janNote: "Includes works dated only by year",
    partial: "Partial month",
    inProgress: (m: string) => `${m} is still in progress.`,
    byType: "By publication type",
    oa: (pct: string): [string, string] => [pct, " are open access: free to read at publication."],
    venues: "Top venues",
  },
  types: { article: "Article", preprint: "Preprint", "conference-paper": "Conference paper", "book-chapter": "Book chapter", review: "Review" } as Record<string, string>,
  notable: {
    tabs: { cited: "Most cited", recent: "Most recent" },
    sortLabel: "Sort publications",
    error: "Publications could not be loaded. Reload the page to try again.",
    empty: (f: string) => `No publications in ${f} for this view.`,
  },
  work: {
    citations: (n: string) => `${n} citations`,
    oa: "Open access",
    source: "Source",
    authors: "UIUC authors: ",
    more: (n: number) => ` and ${n} more`,
    undated: "Undated",
  },
  facultySearch: {
    label: "Search faculty by expertise",
    placeholder: "Search by expertise, e.g. robotics",
    position: "Position",
    anyPosition: "Any position",
    positions: { Professor: "Professor", "Associate Professor": "Associate Professor", "Assistant Professor": "Assistant Professor" } as Record<string, string>,
    examples: "Example searches",
    suggestions: ["computer vision in healthcare", "machine learning", "climate change", "quantum materials", "crop genetics"],
    initial: "medical imaging",
    unavailable: "Faculty search is unavailable right now.",
    searching: "Searching…",
    count: (n: string, field: string | null, shown: number | null) =>
      `${n} faculty match${field ? ` in ${field}` : ""}${shown !== null ? `, showing ${shown}` : ""}.`,
    none: (q: string) => `No faculty keywords match “${q}”. Try a broader term or one of the examples.`,
    link: "OpenAlex link",
  },
  drawer: {
    title: "Faculty profile",
    close: "Close profile",
    loading: "Loading profile",
    error: "This profile could not be loaded. Close the panel and try again.",
    matched: "Matched to OpenAlex by",
    confidence: "confidence",
    methods: { exact: "exact name", first_last: "first + last name", initial_last: "initial + topic check" } as Record<string, string>,
    unmatched: "Not matched to an OpenAlex author, so only the directory keywords are known.",
    topics: "Topics of recent work",
    keywords: "Research keywords",
    recent: "Recent publications",
  },
  collab: {
    intro: (n: string) => `UIUC co-authored with ${n} other institutions. Illinois institutes such as NCSA and the Carl R. Woese Institute count as UIUC, not as partners.`,
    partners: "Top partner institutions",
    founded: "Founded",
    location: "Location",
    coordinates: "Coordinates",
    web: "Web",
    description: null as string | null,
    mapLabel: (n: number) => `Map of the ${n} institutions that co-author most often with UIUC`,
    loadingMap: "Loading map…",
    coWorks: (n: string) => `${n} co-authored works`,
  },
  assistant: {
    title: "Research assistant",
    checking: "Checking…",
    online: "Online · answers cite UIUC records only",
    offline: "Assistant offline: the local model server is not running",
    try: "Ask about recent UIUC research, notable publications or faculty expertise, in English or Vietnamese. Try:",
    examples: [
      "What are the most recent UIUC papers on AI in war conflict?",
      "Which faculty members work on Computer Vision in Healthcare?",
    ],
    intent: "intent",
    sort: "sort",
    intents: { papers: "papers", faculty: "faculty", both: "papers + faculty", out_of_scope: "out of scope" } as Record<string, string>,
    sorts: { recent: "newest first", cited: "most cited", relevance: "relevance" } as Record<string, string>,
    reading: "Reading the question…",
    searching: "Searching UIUC records…",
    writing: "Writing the answer…",
    unavailable: "The assistant is not available right now.",
    busy: "The assistant is answering other questions. Try again in a few seconds.",
    failed: "Something went wrong.",
    inputLabel: "Ask the research assistant",
    placeholder: "Ask about UIUC papers or faculty…",
    placeholderOffline: "Start Ollama to use the assistant",
    send: "Send question",
    button: "Ask the assistant",
  },
};

export type Dict = typeof en;

const vi: Dict = {
  langName: "Tiếng Việt",
  meta: {
    title: "Cổng thông tin nghiên cứu UIUC",
    description: "Hai năm nghiên cứu của Đại học Illinois Urbana-Champaign, từ dữ liệu OpenAlex, kèm trợ lý nghiên cứu AI.",
  },
  skip: "Bỏ qua, đến nội dung chính",
  header: {
    brand: "Cổng nghiên cứu UIUC",
    nav: "Các mục",
    links: { focus: "Lĩnh vực", output: "Sản lượng", notable: "Công bố nổi bật", faculty: "Chuyên môn giảng viên", collab: "Hợp tác" },
    ask: "Hỏi trợ lý nghiên cứu",
    switchTo: "English",
    switchLabel: "View in English",
  },
  hero: {
    eyebrow: "Đại học Illinois Urbana-Champaign · Hồ sơ nghiên cứu",
    lines: ["Các nhà nghiên cứu Illinois", "đã công bố gì trong", "hai năm qua"],
    lead: (n: string) => `Mọi con số trên trang này được tính từ các bản ghi OpenAlex thuộc UIUC, liên kết với ${n} hồ sơ giảng viên.`,
    kpis: {
      works: ["Công bố", "bài báo, preprint, bài hội nghị, chương sách, bài tổng quan"],
      citations: ["Lượt trích dẫn", "cho các công bố đó, theo OpenAlex"],
      oa: ["Truy cập mở", "đọc miễn phí ngay khi công bố"],
      faculty: ["Hồ sơ giảng viên", ""],
    },
    linked: (n: string, pct: string) => `${n} hồ sơ khớp với tác giả OpenAlex (${pct})`,
    photo: "Ảnh",
    founded: "Thành lập",
  },
  sections: {
    focus: ["Lĩnh vực nghiên cứu trọng tâm", "Công bố được nhóm theo lĩnh vực OpenAlex của chủ đề chính. Kích thước ô theo số công bố; chọn một lĩnh vực để xem chi tiết."],
    output: ["Sản lượng khoa học", "Khoảng một nghìn công bố mỗi tháng. Đỉnh tháng Một gồm các công bố OpenAlex chỉ ghi năm, được xếp vào ngày 1 tháng 1."],
    notable: ["Công bố nổi bật", "Các công bố của UIUC được trích dẫn nhiều nhất và mới nhất. Tên in đậm là giảng viên trong danh bạ; chọn tên để mở hồ sơ."],
    faculty: ["Chuyên môn giảng viên", "Tìm trong 999 hồ sơ giảng viên theo từ khóa nghiên cứu (tiếng Anh). Hồ sơ đã liên kết OpenAlex còn có chủ đề và công bố gần đây."],
    collab: ["Hợp tác & khuôn viên", ""],
    assistant: ["Trợ lý nghiên cứu AI", "Trả lời câu hỏi từ dữ liệu UIUC trên trang này và trích dẫn từng nguồn, bằng tiếng Việt hoặc tiếng Anh. Chạy trên mô hình cục bộ, nên câu hỏi của bạn không rời khỏi máy chủ này."],
  },
  errors: {
    section: (what: string) => `Không tải được ${what.toLowerCase()} vì dịch vụ dữ liệu không phản hồi. Khởi động API bằng`,
    reload: "rồi tải lại trang.",
    overview: "Tổng quan nghiên cứu",
    collab: "Dữ liệu hợp tác",
  },
  footer: {
    data: "Dữ liệu:",
    rest: "(CC0) · danh bạ giảng viên do bài đánh giá cung cấp · bản đồ © những người đóng góp OpenStreetMap",
    unofficial: "Không phải trang chính thức của Đại học Illinois",
  },
  focus: {
    showing: "Đang lọc",
    across: "trên toàn trang · Bỏ lọc",
    hint: "Chọn một lĩnh vực để xem các phân ngành, chủ đề đang lên và giảng viên tiêu biểu, đồng thời lọc cả trang.",
    tilesLabel: "Các lĩnh vực nghiên cứu theo số công bố",
    works: (n: string) => `${n} công bố`,
    topSub: "Nhiều nhất:",
    noRising: "Chưa có chủ đề nào trong lĩnh vực này tăng trưởng trên đủ số công bố gần đây.",
    noFaculty: "Chưa có giảng viên đã liên kết nào công bố trong lĩnh vực này.",
    status: (n: string, field: string): [string, string] => [`${n}`, ` công bố thuộc ${field}. Công bố nổi bật và giảng viên bên dưới cũng được lọc theo.`],
    pubs: "Công bố",
    faculty: "Giảng viên",
    subfields: (f: string) => `Phân ngành của ${f}`,
    subfieldsNote: "Số công bố theo phân ngành của chủ đề chính.",
    risingField: "Đang lên trong lĩnh vực",
    risingFieldNote: "12 tháng gần nhất so với 12 tháng trước đó, tối thiểu 10 công bố gần đây.",
    topField: "Công bố nhiều nhất trong lĩnh vực",
    topFieldNote: "Giảng viên đã liên kết, theo số công bố trong lĩnh vực. Chọn tên để xem hồ sơ.",
    rising: "Chủ đề đang lên",
    risingNote: "12 tháng gần nhất so với 12 tháng trước đó, các chủ đề có tối thiểu 40 công bố gần đây.",
    top: "Giảng viên công bố nhiều nhất",
    topNote: "Số công bố của giảng viên đã khớp với hồ sơ tác giả OpenAlex. Chọn tên để xem hồ sơ.",
  },
  output: {
    summary: (from: string, to: string, lo: string, hi: string, max: string) =>
      `Số công bố hằng tháng từ ${from} đến ${to}: thường ${lo} đến ${hi} mỗi tháng, cao nhất ${max} vào tháng Một.`,
    works: (n: string) => `${n} công bố`,
    janNote: "Gồm các công bố chỉ ghi năm",
    partial: "Tháng chưa kết thúc",
    inProgress: (m: string) => `${m} chưa kết thúc.`,
    byType: "Theo loại công bố",
    oa: (pct: string): [string, string] => [pct, " là truy cập mở: đọc miễn phí ngay khi công bố."],
    venues: "Nơi công bố hàng đầu",
  },
  types: { article: "Bài báo", preprint: "Preprint", "conference-paper": "Bài hội nghị", "book-chapter": "Chương sách", review: "Bài tổng quan" },
  notable: {
    tabs: { cited: "Trích dẫn nhiều nhất", recent: "Mới nhất" },
    sortLabel: "Sắp xếp công bố",
    error: "Không tải được danh sách công bố. Hãy tải lại trang.",
    empty: (f: string) => `Không có công bố nào thuộc ${f} cho mục này.`,
  },
  work: {
    citations: (n: string) => `${n} trích dẫn`,
    oa: "Truy cập mở",
    source: "Nguồn",
    authors: "Tác giả UIUC: ",
    more: (n: number) => ` và ${n} người khác`,
    undated: "Không rõ ngày",
  },
  facultySearch: {
    label: "Tìm giảng viên theo chuyên môn",
    placeholder: "Tìm theo chuyên môn (tiếng Anh), vd. robotics",
    position: "Chức danh",
    anyPosition: "Mọi chức danh",
    positions: { Professor: "Giáo sư", "Associate Professor": "Phó giáo sư", "Assistant Professor": "Trợ lý giáo sư" },
    examples: "Ví dụ tìm kiếm",
    suggestions: ["computer vision in healthcare", "machine learning", "climate change", "quantum materials", "crop genetics"],
    initial: "medical imaging",
    unavailable: "Tìm kiếm giảng viên hiện không khả dụng.",
    searching: "Đang tìm…",
    count: (n: string, field: string | null, shown: number | null) =>
      `${n} giảng viên phù hợp${field ? ` trong ${field}` : ""}${shown !== null ? `, đang hiện ${shown}` : ""}.`,
    none: (q: string) => `Không có từ khóa giảng viên nào khớp “${q}”. Thử từ rộng hơn hoặc một ví dụ bên trên.`,
    link: "Liên kết OpenAlex",
  },
  drawer: {
    title: "Hồ sơ giảng viên",
    close: "Đóng hồ sơ",
    loading: "Đang tải hồ sơ",
    error: "Không tải được hồ sơ này. Đóng bảng và thử lại.",
    matched: "Khớp với OpenAlex theo",
    confidence: "độ tin cậy",
    methods: { exact: "tên chính xác", first_last: "tên + họ", initial_last: "chữ cái đầu + kiểm tra chủ đề" },
    unmatched: "Chưa khớp với tác giả OpenAlex nào, nên chỉ có từ khóa trong danh bạ.",
    topics: "Chủ đề nghiên cứu gần đây",
    keywords: "Từ khóa nghiên cứu",
    recent: "Công bố gần đây",
  },
  collab: {
    intro: (n: string) => `UIUC đồng tác giả với ${n} tổ chức khác. Các viện thuộc Illinois như NCSA và Viện Carl R. Woese được tính là UIUC, không phải đối tác.`,
    partners: "Đối tác hàng đầu",
    founded: "Thành lập",
    location: "Địa điểm",
    coordinates: "Tọa độ",
    web: "Website",
    description: "Đại học công lập hàng đầu của bang Illinois, thành lập năm 1867 tại hai thành phố Urbana và Champaign. UIUC nổi tiếng về kỹ thuật, khoa học máy tính, nông nghiệp và vật lý, và là nơi đặt Trung tâm Ứng dụng Siêu máy tính Quốc gia (NCSA).",
    mapLabel: (n: number) => `Bản đồ ${n} tổ chức đồng tác giả thường xuyên nhất với UIUC`,
    loadingMap: "Đang tải bản đồ…",
    coWorks: (n: string) => `${n} công bố chung`,
  },
  assistant: {
    title: "Trợ lý nghiên cứu",
    checking: "Đang kiểm tra…",
    online: "Trực tuyến · chỉ trích dẫn dữ liệu của UIUC",
    offline: "Trợ lý ngoại tuyến: máy chủ mô hình cục bộ chưa chạy",
    try: "Hỏi về nghiên cứu gần đây của UIUC, công bố nổi bật hoặc chuyên môn giảng viên, bằng tiếng Việt hoặc tiếng Anh. Thử:",
    examples: [
      "Những bài báo mới nhất của UIUC về AI trong chiến tranh, xung đột là gì?",
      "Giảng viên nào nghiên cứu thị giác máy tính trong y tế?",
    ],
    intent: "tìm",
    sort: "sắp xếp",
    intents: { papers: "bài báo", faculty: "giảng viên", both: "bài báo + giảng viên", out_of_scope: "ngoài phạm vi" },
    sorts: { recent: "mới nhất", cited: "trích dẫn nhiều nhất", relevance: "liên quan nhất" },
    reading: "Đang đọc câu hỏi…",
    searching: "Đang tìm trong dữ liệu UIUC…",
    writing: "Đang viết câu trả lời…",
    unavailable: "Trợ lý hiện không khả dụng.",
    busy: "Trợ lý đang trả lời câu hỏi khác. Vui lòng thử lại sau vài giây.",
    failed: "Đã có lỗi xảy ra.",
    inputLabel: "Hỏi trợ lý nghiên cứu",
    placeholder: "Hỏi về bài báo hoặc giảng viên UIUC…",
    placeholderOffline: "Hãy chạy Ollama để dùng trợ lý",
    send: "Gửi câu hỏi",
    button: "Hỏi trợ lý",
  },
};

export const DICTS: Record<Locale, Dict> = { en, vi };

/** OpenAlex field names (the filter value stays English; only the label is translated). */
const FIELDS_VI: Record<string, string> = {
  "Agricultural and Biological Sciences": "Khoa học Nông nghiệp và Sinh học",
  "Arts and Humanities": "Nghệ thuật và Nhân văn",
  "Biochemistry, Genetics and Molecular Biology": "Hóa sinh, Di truyền và Sinh học phân tử",
  "Business, Management and Accounting": "Kinh doanh, Quản lý và Kế toán",
  "Chemical Engineering": "Kỹ thuật Hóa học",
  Chemistry: "Hóa học",
  "Computer Science": "Khoa học Máy tính",
  "Decision Sciences": "Khoa học Quyết định",
  Dentistry: "Nha khoa",
  "Earth and Planetary Sciences": "Khoa học Trái Đất và Hành tinh",
  "Economics, Econometrics and Finance": "Kinh tế, Kinh tế lượng và Tài chính",
  Energy: "Năng lượng",
  Engineering: "Kỹ thuật",
  "Environmental Science": "Khoa học Môi trường",
  "Health Professions": "Ngành Y tế",
  "Immunology and Microbiology": "Miễn dịch học và Vi sinh vật học",
  "Materials Science": "Khoa học Vật liệu",
  Mathematics: "Toán học",
  Medicine: "Y học",
  Neuroscience: "Khoa học Thần kinh",
  Nursing: "Điều dưỡng",
  "Pharmacology, Toxicology and Pharmaceutics": "Dược lý, Độc chất học và Dược học",
  "Physics and Astronomy": "Vật lý và Thiên văn học",
  Psychology: "Tâm lý học",
  "Social Sciences": "Khoa học Xã hội",
  Veterinary: "Thú y",
};

const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Locale-aware formatters; plain functions so both server and client components can build them. */
export function formatters(lang: Locale) {
  const tag = lang === "vi" ? "vi-VN" : "en-US";
  const regions = new Intl.DisplayNames([tag], { type: "region" });
  return {
    fmt: (n: number) => n.toLocaleString(tag),
    pct: (x: number, digits = 1) => `${(x * 100).toLocaleString(tag, { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`,
    monthLabel(isoMonth: string) {
      const [y, m] = isoMonth.split("-").map(Number);
      return lang === "vi" ? `tháng ${m}/${y}` : `${MONTHS_EN[m - 1]} ${y}`;
    },
    /** Short axis label: "Mar ’25" / "T3/25". */
    axisLabel(isoMonth: string) {
      const [y, m] = isoMonth.split("-").map(Number);
      return lang === "vi" ? `T${m}/${String(y).slice(2)}` : `${MONTHS_EN[m - 1]} ’${String(y).slice(2)}`;
    },
    dateLabel(iso: string | null) {
      if (!iso) return DICTS[lang].work.undated;
      const [y, m, d] = iso.split("-").map(Number);
      return lang === "vi" ? `${d}/${m}/${y}` : `${d} ${MONTHS_EN[m - 1]} ${y}`;
    },
    field: (name: string | null | undefined) => (name && lang === "vi" ? FIELDS_VI[name] ?? name : name ?? ""),
    country(code: string | null | undefined) {
      if (!code) return "";
      try {
        return regions.of(code) ?? code;
      } catch {
        return code;
      }
    },
    type: (t: string) => DICTS[lang].types[t] ?? t,
  };
}
export type Formatters = ReturnType<typeof formatters>;
