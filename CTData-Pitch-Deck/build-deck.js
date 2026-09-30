const pptxgen = require("pptxgenjs");
const OUT = process.argv[2] || "CTData-Assistant-Pitch.pptx";

const C = {
  paper: "F5F1EA",
  ink: "22315C",
  coral: "F08A5D",
  coralDeep: "D9683A", // small coral text on paper, for legibility
  inkMuted: "5B6485",
  ruleLight: "CFC6B6",
  paperMuted: "C3C6D4",
  ruleDark: "46557F",
  ghost: "2B3B6B",
};
const SERIF = "Cambria";
const SANS = "Calibri";
const W = 13.333, H = 7.5, M = 0.75, CW = W - 2 * M;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "The CTData Assistant — Hackathon Pitch";
pres.author = "Team CTData-Chatbot";

function txt(slide, text, o) {
  slide.addText(text, { isTextBox: true, margin: 0, valign: "top", fontFace: SANS, ...o });
}
function hline(slide, x, y, w, color, pt = 0.75) {
  slide.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width: pt } });
}
function vline(slide, x, y, h, color, pt = 0.75) {
  slide.addShape(pres.shapes.LINE, { x, y, w: 0, h, line: { color, width: pt } });
}
// Kicker row: section label left, timing right, hairline beneath
function kicker(slide, num, label, timing, dark) {
  const ink = dark ? C.paper : C.ink;
  txt(slide, [
    { text: num + "  ", options: { color: dark ? C.coral : C.coralDeep, bold: true } },
    { text: label, options: { color: ink, bold: true } },
  ], { x: M, y: 0.55, w: 8, h: 0.3, fontSize: 10.5, charSpacing: 3 });
  txt(slide, timing, {
    x: W - M - 3, y: 0.55, w: 3, h: 0.3, fontSize: 10.5, charSpacing: 3, bold: true,
    align: "right", color: dark ? C.coral : C.coralDeep,
  });
  hline(slide, M, 0.95, CW, dark ? C.ruleDark : C.ruleLight);
}
function folio(slide, n, dark) {
  txt(slide, `0${n} / 06`, {
    x: W - M - 1.5, y: 6.85, w: 1.5, h: 0.25, fontSize: 9, charSpacing: 2,
    align: "right", color: dark ? C.paperMuted : C.inkMuted,
  });
}

// ─── 1 · COVER ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.ink };
  // Oversized question mark as texture
  txt(s, "?", {
    x: 8.6, y: -1.35, w: 5.2, h: 9.6, fontFace: SERIF, fontSize: 560, bold: true,
    color: C.ghost, align: "right",
  });
  txt(s, "AI HACKATHON  ·  CTDATA.ORG CHALLENGE", {
    x: M, y: 0.6, w: 8, h: 0.3, fontSize: 11, bold: true, charSpacing: 4, color: C.coral,
  });
  txt(s, "01 / 06", {
    x: W - M - 1.5, y: 0.6, w: 1.5, h: 0.3, fontSize: 10, charSpacing: 2, align: "right", color: C.paperMuted,
  });
  txt(s, [
    { text: "The Helpline,", options: { breakLine: true } },
    { text: "at Scale" },
    { text: ".", options: { color: C.coral } },
  ], {
    x: M, y: 1.55, w: 11, h: 3.1, fontFace: SERIF, fontSize: 100, bold: true,
    color: C.paper, lineSpacingMultiple: 0.88, charSpacing: -2,
  });
  txt(s,
    "A conversational AI assistant that lets anyone ask plain-language questions of Connecticut’s public education data — and get trustworthy, cited answers.",
    { x: M, y: 4.95, w: 7.4, h: 1.1, fontSize: 17, color: C.paperMuted, lineSpacingMultiple: 1.2 });
  hline(s, M, 6.6, CW, C.ruleDark);
  txt(s, "TEAM CTDATA-CHATBOT", {
    x: M, y: 6.78, w: 5, h: 0.3, fontSize: 10, bold: true, charSpacing: 3, color: C.paper,
  });
  txt(s, "github.com/1xavierdev/CTData-chatbot", {
    x: W - M - 6, y: 6.78, w: 6, h: 0.3, fontSize: 10.5, align: "right", color: C.paperMuted,
  });
  s.addNotes("Cover. Open with the hook: CTData already runs a human data helpline. We built the version that scales.");
}

// ─── 2 · PROBLEM & USER ───────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "02", "PROBLEM & USER", "45 SEC");
  txt(s, [
    { text: "Public data is public.", options: { breakLine: true } },
    { text: "Accessible is ", options: {} },
    { text: "another story.", options: { italic: true, color: C.coral } },
  ], {
    x: M, y: 1.4, w: 7.0, h: 1.75, fontFace: SERIF, fontSize: 42, bold: true,
    color: C.ink, lineSpacingMultiple: 0.98,
  });
  txt(s, [
    { text: "CTData Collaborative’s education page holds graduation rates, chronic absenteeism, bullying and test scores — broken down by race, income, English-learner status and more. But using it means knowing which dataset, which portal, and how to filter spreadsheets.", options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: "Its users aren’t data scientists — they’re " },
    { text: "parents, teachers, students, nonprofits and journalists.", options: { bold: true } },
  ], { x: M, y: 3.35, w: 6.3, h: 2.5, fontSize: 14, color: C.ink, lineSpacingMultiple: 1.25 });

  vline(s, 7.95, 1.45, 4.85, C.ruleLight);

  txt(s, "DATA QUESTIONS / YEAR", {
    x: 8.45, y: 1.45, w: 4.1, h: 0.3, fontSize: 10, bold: true, charSpacing: 3, color: C.coralDeep,
  });
  txt(s, "200", {
    x: 8.3, y: 1.6, w: 4.5, h: 2.6, fontFace: SERIF, fontSize: 190, bold: true,
    color: C.ink, charSpacing: -6,
  });
  txt(s, [
    { text: "answered ", options: {} },
    { text: "by hand", options: { bold: true, italic: true } },
    { text: ", by email, through CTData’s human data helpline.", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "That’s the bottleneck — and the opportunity.", options: { bold: true, color: C.coralDeep } },
  ], { x: 8.45, y: 4.35, w: 4.1, h: 1.8, fontSize: 15, color: C.ink, lineSpacingMultiple: 1.2 });

  txt(s, "Sources: ctdata.org/education; MetroHartford Alliance, CTData 2024 summary", {
    x: M, y: 6.85, w: 8, h: 0.25, fontSize: 9, color: C.inkMuted,
  });
  folio(s, 2);
  s.addNotes("45 seconds. The data exists and is public — but the path to an answer runs through portals and spreadsheets. CTData answers ~200 questions a year by hand. That's our opening.");
}

// ─── 3 · RESEARCH & INSIGHT ───────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "03", "RESEARCH & INSIGHT", "45 SEC");
  txt(s, [
    { text: "Three findings shaped the build" },
    { text: ".", options: { color: C.coral } },
  ], { x: M, y: 1.3, w: CW, h: 0.85, fontFace: SERIF, fontSize: 44, bold: true, color: C.ink });

  const rows = [
    ["The data is scattered across portals",
      "CTData curates, but the numbers live on EdSight and CT’s open-data portal. Users get bounced between three websites for one answer."],
    ["The schema is remarkably consistent",
      "Nearly every education dataset breaks down by the same 7 dimensions: race/ethnicity, gender, English-learner status, free/reduced meals, special education, homelessness, foster care. Ideal for natural-language querying."],
    ["Same question, different readers",
      "A 7th grader and a policymaker ask the same thing but need different answers — so the assistant adapts reading level and framing to who is asking."],
  ];
  const top = 2.5, rh = 1.42;
  rows.forEach(([title, body], i) => {
    const y = top + i * rh;
    hline(s, M, y, CW, i === 0 ? C.ink : C.ruleLight, i === 0 ? 1 : 0.75);
    txt(s, String(i + 1), {
      x: M, y: y + 0.08, w: 1.1, h: 1.2, fontFace: SERIF, fontSize: 80, bold: true,
      color: C.coral, lineSpacingMultiple: 0.85,
    });
    txt(s, title, {
      x: 2.1, y: y + 0.28, w: 3.9, h: 0.95, fontFace: SERIF, fontSize: 21, bold: true,
      color: C.ink, lineSpacingMultiple: 1.0,
    });
    txt(s, body, {
      x: 6.45, y: y + 0.3, w: 6.13, h: 1.05, fontSize: 13, color: C.ink, lineSpacingMultiple: 1.2,
    });
  });
  hline(s, M, top + 3 * rh, CW, C.ruleLight);
  folio(s, 3);
  s.addNotes("45 seconds. Scattered portals created the need; the consistent 7-dimension schema made it tractable; different readers meant the answer has to adapt to who is asking.");
}

// ─── 4 · SOLUTION & DEMO ──────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "04", "SOLUTION & DEMO", "2 MIN");
  txt(s, [
    { text: "The CTData Assistant — " },
    { text: "retrieval to trusted answer.", options: { italic: true, color: C.coral } },
  ], { x: M, y: 1.25, w: CW, h: 0.7, fontFace: SERIF, fontSize: 36, bold: true, color: C.ink });

  const stages = [
    ["Scraper", "ctdata.org education pages"],
    ["Knowledge base", "Chunks + embeddings, BM25 fallback"],
    ["Local LLM", "LM Studio, audience-aware prompts"],
    ["Cited answer", "Sources linked, never invented"],
  ];
  const sw = 2.45, gap = (CW - 4 * sw) / 3, py = 2.35;
  stages.forEach(([name, desc], i) => {
    const x = M + i * (sw + gap);
    const last = i === stages.length - 1;
    hline(s, x, py, sw, last ? C.coral : C.ink, last ? 2 : 1);
    txt(s, "0" + (i + 1), {
      x, y: py + 0.15, w: sw, h: 0.25, fontSize: 10, bold: true, charSpacing: 3, color: C.coralDeep,
    });
    txt(s, name, {
      x, y: py + 0.45, w: sw, h: 0.45, fontFace: SERIF, fontSize: 22, bold: true,
      color: last ? C.coralDeep : C.ink,
    });
    txt(s, desc, { x, y: py + 0.95, w: sw, h: 0.55, fontSize: 12, color: C.inkMuted, lineSpacingMultiple: 1.15 });
    if (!last) {
      s.addShape(pres.shapes.LINE, {
        x: x + sw + 0.12, y: py + 0.67, w: gap - 0.24, h: 0,
        line: { color: C.coral, width: 1.5, endArrowType: "triangle" },
      });
    }
  });

  const dy = 4.3;
  hline(s, M, dy, CW, C.ruleLight);
  txt(s, "LIVE DEMO — THREE QUESTIONS", {
    x: M, y: dy + 0.18, w: 6, h: 0.3, fontSize: 10.5, bold: true, charSpacing: 3, color: C.ink,
  });
  const qs = [
    ["Q1", "“What education datasets does CTData have?”", "Retrieval + citations"],
    ["Q2", "“How can I use absenteeism data in my classroom?”", "Asked as a teacher profile — the answer adapts"],
    ["Q3", "“What’s the graduation rate by district?”", "Honest limits — routes to the right dataset, with a link"],
  ];
  const qw = 3.6, qgap = (CW - 3 * qw) / 2;
  qs.forEach(([q, text, note], i) => {
    const x = M + i * (qw + qgap);
    txt(s, q, { x, y: dy + 0.62, w: 1, h: 0.45, fontFace: SERIF, fontSize: 26, bold: true, color: C.coral });
    txt(s, text, {
      x, y: dy + 1.12, w: qw, h: 0.72, fontFace: SERIF, fontSize: 16, italic: true, color: C.ink,
      lineSpacingMultiple: 1.05,
    });
    txt(s, note, { x, y: dy + 1.88, w: qw, h: 0.3, fontSize: 11.5, color: C.inkMuted });
  });

  txt(s, [
    { text: "If the model server is down, the assistant degrades to keyword search. " },
    { text: "The demo never dies.", options: { bold: true, color: C.ink } },
  ], { x: M, y: 6.85, w: 9.5, h: 0.25, fontSize: 10.5, color: C.inkMuted });
  folio(s, 4);
  s.addNotes("2 minutes. Walk the pipeline in ~20 seconds, then switch to the live demo. Q1: retrieval with citations. Q2: switch profile to teacher and show the adapted answer. Q3: show honest limits — it routes to the right dataset rather than inventing a number.");
}

// ─── 5 · IMPACT & DIFFERENTIATION ─────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.ink };
  kicker(s, "05", "IMPACT & DIFFERENTIATION", "1 MIN", true);
  txt(s, [
    { text: "The helpline becomes", options: { breakLine: true } },
    { text: "an answer engine" },
    { text: ".", options: { color: C.coral } },
  ], {
    x: M, y: 1.3, w: CW, h: 1.6, fontFace: SERIF, fontSize: 46, bold: true, color: C.paper,
    lineSpacingMultiple: 0.95,
  });
  const cols = [
    ["Audience-aware", "Same data, explained at a 5th-grade level for a student — with methodology caveats for a researcher."],
    ["Trustworthy by design", "Answers only from trusted CT sources, quotes figures exactly, cites every claim — and honestly says “here’s where to find it” when it doesn’t know."],
    ["Fully local", "Runs on LM Studio. Zero API cost, and user questions never leave the machine."],
  ];
  const cw = 3.55, cg = (CW - 3 * cw) / 2, cy = 3.3;
  cols.forEach(([t, b], i) => {
    const x = M + i * (cw + cg);
    if (i > 0) vline(s, x - cg / 2, cy, 1.85, C.ruleDark);
    txt(s, t, { x, y: cy, w: cw, h: 0.45, fontFace: SERIF, fontSize: 20, bold: true, color: C.paper });
    txt(s, b, { x, y: cy + 0.55, w: cw, h: 1.35, fontSize: 13, color: C.paperMuted, lineSpacingMultiple: 1.2 });
  });
  hline(s, M, 5.45, CW, C.ruleDark);
  txt(s, "Instant, 24/7, and built for exactly the people CTData exists to serve.", {
    x: M, y: 5.62, w: CW, h: 0.55, fontFace: SERIF, fontSize: 25, italic: true, bold: true, color: C.coral,
  });
  txt(s, "PARENTS  ·  TEACHERS  ·  STUDENTS  ·  NONPROFITS  ·  JOURNALISTS  ·  POLICYMAKERS", {
    x: M, y: 6.85, w: 10, h: 0.25, fontSize: 9.5, charSpacing: 3, color: C.paperMuted,
  });
  folio(s, 5, true);
  s.addNotes("1 minute. Three differentiators: it adapts to the reader, it never invents, and it runs fully local with zero API cost. Land the closing line.");
}

// ─── 6 · NEXT STEPS ───────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  kicker(s, "06", "NEXT STEPS", "30 SEC");
  txt(s, [
    { text: "Next —", options: { breakLine: true, color: C.coral } },
    { text: "answers with the data itself." },
  ], {
    x: M, y: 1.35, w: 4.5, h: 3.4, fontFace: SERIF, fontSize: 46, bold: true, color: C.ink,
    lineSpacingMultiple: 0.98,
  });
  const items = [
    ["Load the actual datasets", "Attendance, graduation and per-pupil spending are already identified on CT’s open-data portal — so the bot can answer “which district has the highest absenteeism?” with real numbers."],
    ["Validate against the real helpline", "Test actual questions from CTData staff against the assistant’s answers; measure accuracy and citation quality."],
    ["Expand beyond education", "Housing, health, demographics — the pipeline is already topic-agnostic; new topics are just new pages to scrape."],
  ];
  const ix = 5.85, iw = W - M - ix, iy = 1.45, ih = 1.62;
  items.forEach(([t, b], i) => {
    const y = iy + i * ih;
    hline(s, ix, y, iw, i === 0 ? C.ink : C.ruleLight, i === 0 ? 1 : 0.75);
    txt(s, "→", { x: ix, y: y + 0.18, w: 0.6, h: 0.5, fontFace: "Arial", fontSize: 26, color: C.coral });
    txt(s, t, { x: ix + 0.7, y: y + 0.24, w: iw - 0.7, h: 0.4, fontFace: SERIF, fontSize: 19, bold: true, color: C.ink });
    txt(s, b, { x: ix + 0.7, y: y + 0.68, w: iw - 0.7, h: 0.85, fontSize: 12.5, color: C.ink, lineSpacingMultiple: 1.2 });
  });
  hline(s, ix, iy + 3 * ih, iw, C.ruleLight);

  txt(s, "TEAM CTDATA-CHATBOT", {
    x: M, y: 6.85, w: 3, h: 0.25, fontSize: 9.5, bold: true, charSpacing: 3, color: C.ink,
  });
  txt(s, "github.com/1xavierdev/CTData-chatbot", {
    x: 3.6, y: 6.85, w: 5, h: 0.25, fontSize: 10, color: C.inkMuted,
  });
  folio(s, 6);
  s.addNotes("30 seconds. Real datasets, real helpline validation, then new topics. Thank the judges.");
}

pres.writeFile({ fileName: OUT }).then(f => console.log("wrote", f));
