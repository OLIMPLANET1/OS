#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, json, re, hashlib

MASTER = "/tmp/g_873378172.csv"   # 프로젝트 진행현황 (상위)
ANNA   = "/tmp/g_189362339.csv"   # 안나 세부 (하위)
CHARLES= "/tmp/g_1380210860.csv"  # 찰스 업무 로그 (하위)
FEED   = "/tmp/g_2015258688.csv"  # 집뷰 서비스 피드백

def read(path):
    with open(path, encoding="utf-8") as f:
        return [row for row in csv.reader(f)]

def clean(s):
    return (s or "").strip()

def norm(s):
    # 매칭용 정규화: 공백/괄호/언더스코어/특수문자 제거
    s = clean(s).lower()
    s = re.sub(r"[\s_()\[\]·,/]+", "", s)
    s = re.sub(r"에스큐브쇼룸|에스큐브랩", "에스큐브", s)
    return s

DATE_RE = re.compile(r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})")
def parse_date(s):
    s = clean(s)
    if not s:
        return "", ""
    m = DATE_RE.search(s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}", ""
    return "", s  # 날짜가 아니면 (예: '매일','주2회','1달에 1번') 메모로 반환

def norm_status(s):
    s = clean(s)
    if s == "대기중":
        return "진행예정"
    return s if s in {"진행중", "완료", "진행예정"} else ""

_ids = set()
def uid(seed):
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()[:8]
    base = "t" + h
    i = base
    n = 0
    while i in _ids:
        n += 1
        i = base + str(n)
    _ids.add(i)
    return i

tasks = []
order = 0
def add(**kw):
    global order
    kw.setdefault("id", uid(json.dumps(kw, ensure_ascii=False)))
    kw.setdefault("parentId", None)
    kw.setdefault("category", "")
    kw.setdefault("assignee", "")
    kw.setdefault("priority", "")
    kw.setdefault("start", "")
    kw.setdefault("end", "")
    kw.setdefault("status", "")
    kw.setdefault("doc", "")
    kw.setdefault("progress", "")
    kw.setdefault("issue", "")
    kw["order"] = order
    order += 1
    tasks.append(kw)
    return kw["id"]

def join_notes(*parts):
    return " · ".join([p for p in (clean(x) for x in parts) if p])

# ---------- 1) 상위: 프로젝트 진행현황 ----------
rows = read(MASTER)
# 헤더는 3행(인덱스2): no,담당자,구분,프로젝트,진행업무,우선순위,시작일,종료일,상태,결과물,진행사항,이슈
project_parent = {}   # norm(project) -> parentId (해당 프로젝트의 첫 상위 항목)
for r in rows[3:]:
    r = (r + [""] * 12)[:12]
    no, assignee, cat, proj, task, pr, start, end, status, doc, prog, issue = [clean(x) for x in r]
    if not task and not proj:
        continue
    sdate, snote = parse_date(start)
    edate, enote = parse_date(end)
    pid = add(
        parentId=None,
        task=task or proj,
        project=proj or task,
        category=cat,
        assignee=assignee,
        priority=pr if pr in ("높음", "보통", "낮음") else "",
        start=sdate,
        end=edate,
        status=norm_status(status) or "진행중",
        doc=doc,
        progress=join_notes(prog, ("일정:" + snote) if snote else "", ("기한:" + enote) if enote else ""),
        issue=issue,
        src="master",
    )
    key = norm(proj or task)
    if key and key not in project_parent:
        project_parent[key] = (pid, proj or task)

def find_parent(proj):
    k = norm(proj)
    if not k:
        return None, None
    if k in project_parent:
        return project_parent[k]
    # prefix 매칭 (마스터 프로젝트가 자식 프로젝트의 접두 또는 반대)
    for mk, val in project_parent.items():
        if k.startswith(mk) or mk.startswith(k):
            return val
    return None, None

# ---------- 하위 항목 수집 (안나 + 찰스) ----------
# 먼저 모두 모은 뒤, 상위 매칭 / 미매칭 그룹핑을 한 번에 처리한다.
children = []  # dict: project, fields...

# 안나 세부
rows = read(ANNA)
# 헤더 3행: no,구분,프로젝트,진행업무,시작일,종료일,상태,결과물,진행사항,이슈
cur_cat, cur_proj = "", ""
for r in rows[3:]:
    r = (r + [""] * 10)[:10]
    no, cat, proj, task, start, end, status, doc, prog, issue = [clean(x) for x in r]
    if cat:  cur_cat = cat
    if proj: cur_proj = proj
    if not task:
        continue
    sdate, snote = parse_date(start)
    edate, enote = parse_date(end)
    children.append(dict(
        project=cur_proj, task=task, category=cur_cat, assignee="안나",
        start=sdate, end=edate, status=norm_status(status) or "진행예정", doc=doc,
        progress=join_notes(prog, ("일정:" + snote) if snote else "", ("기한:" + enote) if enote else ""),
        issue=issue, src="anna",
    ))

# 찰스 업무 로그
rows = read(CHARLES)
# 헤더 1행: 프로젝트명,업체명,담당자,진행내용,완료일,비고
for r in rows[1:]:
    r = (r + [""] * 6)[:6]
    proj, company, contact, work, done, note = [clean(x) for x in r]
    if not proj and not work:
        continue
    if not work:
        work = proj
    edate, enote = parse_date(done)
    children.append(dict(
        project=proj or work, task=work, category="고객관리", assignee="찰스",
        start="", end=edate, status="완료" if edate else "진행중", doc="",
        progress=join_notes(
            ("거래처:" + company) if company else "",
            ("담당:" + contact) if contact else "",
            note, ("완료:" + enote) if enote else ""),
        issue="", src="charles",
    ))

# 미매칭 프로젝트별 개수 집계 → 2건 이상일 때만 합성 상위 생성
from collections import Counter
unmatched_counts = Counter()
for c in children:
    if not find_parent(c["project"])[0]:
        unmatched_counts[norm(c["project"])] += 1

def resolve_parent(c):
    pid, _ = find_parent(c["project"])
    if pid:
        return pid
    key = norm(c["project"])
    if unmatched_counts[key] > 1:
        # 같은 프로젝트가 여러 건 → 묶을 상위 1개 생성
        if key not in project_parent:
            nid = add(parentId=None, task=c["project"], project=c["project"],
                      category=c["category"], assignee=c["assignee"],
                      status="진행중", src="auto-parent")
            project_parent[key] = (nid, c["project"])
        return project_parent[key][0]
    return None  # 단일 건은 상위 항목 그 자체로 둔다

for c in children:
    parent = resolve_parent(c)
    src = c.pop("src")
    add(parentId=parent, src=src, **c)

# ---------- 4) 피드백 ----------
rows = read(FEED)
# 헤더 3행: no,날짜,대응담당자,(상태),프로젝트,업체,담당자,피드백,대응,개선방안
FEED_PARENT = add(parentId=None, task="집뷰 서비스 피드백", project="집뷰 서비스 피드백",
                  category="피드백", status="진행중", src="feed-parent")
for r in rows[3:]:
    r = (r + [""] * 10)[:10]
    no, date, owner, st, proj, company, contact, feedback, response, improve = [clean(x) for x in r]
    if not feedback and not proj:
        continue
    sdate, _ = parse_date(date)
    add(
        parentId=FEED_PARENT,
        task=(proj + " 피드백") if proj else (feedback[:30] or "피드백"),
        project="집뷰 서비스 피드백",
        category="피드백",
        assignee=owner,
        start=sdate,
        status="진행중" if (st and st != "완료") else (norm_status(st) or "진행중"),
        progress=join_notes(("거래처:" + company) if company else "",
                            ("담당:" + contact) if contact else "",
                            ("피드백:" + feedback) if feedback else "",
                            ("대응:" + response) if response else ""),
        issue=("개선:" + improve) if improve else "",
        src="feed",
    )

# 출력
with open("/home/user/schedule/data.js", "w", encoding="utf-8") as f:
    f.write("// 구글 시트에서 자동 변환된 초기 데이터 (프로젝트 진행현황 / 안나 / 찰스 / 피드백)\n")
    f.write("// 생성 스크립트: tools/transform (시트 원본 기준)\n")
    f.write("window.SEED_TASKS = ")
    json.dump(tasks, f, ensure_ascii=False, indent=1)
    f.write(";\n")

# 통계
top = [t for t in tasks if not t["parentId"]]
sub = [t for t in tasks if t["parentId"]]
print(f"총 {len(tasks)}건  | 상위 {len(top)}  하위 {len(sub)}")
from collections import Counter
print("src별:", dict(Counter(t['src'] for t in tasks)))
print("상태별:", dict(Counter(t['status'] for t in tasks)))
print("\n[상위 항목 미리보기]")
for t in top[:30]:
    kids = sum(1 for s in sub if s["parentId"] == t["id"])
    print(f"  - {t['project'][:24]:24} | {t['task'][:30]:30} | 하위 {kids}")
