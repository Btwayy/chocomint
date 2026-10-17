"""Apply six documented Codex editorial revisions; keep original drafts and checks."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab


def cloze(stem, options, translation, explanation, reasons):
    return {"stem": stem, "options": options, "answer_index": 0, "translation_zh": translation,
            "explanation_zh": explanation, "option_explanations_zh": reasons}


changes = {
    "v-672ae372a7-cloze": cloze(
        "住民の睡眠を妨げないよう、夜間の騒音に十分（　）する必要がある。",
        ["配慮", "促進", "排除", "把握"], "需要充分顾及夜间噪音的影响，以免妨碍居民睡眠。",
        "「〜に配慮する」表示顾及某个对象或情况。本句要顾及噪音的影响；其余动词通常用「を」连接对象。",
        ["「騒音に配慮する」指顾及噪音对周围的影响。", "「促進」表示促进，不能说「騒音に促進する」。", "可以说「騒音を排除する」，本句的「に」不能这样连接。", "「把握」的对象通常接「を」，不能说「騒音に把握する」。"]),
    "v-241f51574c-cloze": cloze(
        "利用者が一日数人から千人以上へ増え、施設は深刻な混雑に悩まされている。その増加は（　）。",
        ["著しい", "たやすい", "好ましい", "乏しい"], "使用人数从每天几人增加到上千人，设施深受严重拥挤之苦，增幅十分显著。",
        "人数大幅增加对应「著しい」。句末直接用形容词原形；严重拥挤也排除了表示理想、可喜的「好ましい」。",
        ["「著しい」表示变化显著，符合人数大幅增加的事实。", "「たやすい」表示容易，不能用来形容这里增幅的大小。", "「好ましい」表示理想、可喜，与深受严重拥挤之苦的评价不符。", "「乏しい」表示缺乏、很少，与数人增至千人的幅度矛盾。"]),
    "v-ef8415130d-reading": {"stem": "新たな証拠は、長年信じられてきた結論を【覆す】可能性がある。", "translation_zh": "新的证据可能推翻多年来一直被相信的结论。"},
    "v-bd89f26551-reading": {"stem": "このシステムは外部の電源に【依存】しており、停電すると機能しなくなる。", "translation_zh": "这个系统依赖外部电源，停电后便无法运作。"},
    "g-katawara-1": cloze(
        "彼は本業の医師として病院で診療を続ける（　）、二十年以上にわたり週末は地域の合唱団を指導している。",
        ["かたわら", "がてら", "や否や", "そばから"], "他以医生为本职在医院看诊，同时二十多年来一直在周末指导当地合唱团。",
        "「かたわら」用于长期从事本职活动的同时兼顾另一活动。二十多年的工作与周末活动并行，符合这一用法。",
        ["「動詞辞書形＋かたわら」表示长期并行的本业与另一活动。", "「がてら」多用于借一次行动顺便做另一件事，不合本句长期兼任。", "「や否や」表示动作刚发生紧接另一动作，不表示长期并行。", "「そばから」常表示刚做完就反复出现相反情况，本句没有这种反复落空。"]),
    "g-katawara-2": cloze(
        "平日は研究所の仕事に専念している。彼女はその仕事（　）、休日にはボランティアで子ども向けの科学教室を長年続けている。",
        ["のかたわら", "に先立ち", "にひきかえ", "をよそに"], "她在工作日专心从事研究所的工作，同时长期在休息日以志愿者身份为孩子们开办科学课堂。",
        "名词后接「のかたわら」，表示兼顾本职工作与长期副活动。这里没有事前准备、对比评价或不顾本职工作的意思。",
        ["「仕事のかたわら」表示在从事本职工作的同时长期兼做另一活动。", "「に先立ち」表示在某事之前；本句是两种长期活动并行。", "「にひきかえ」强调鲜明对比；本句没有比较两项活动的评价。", "「をよそに」表示不顾、无视；与平日专心工作、休日志愿服务的安排不符。"]),
}

targets = lab.read_json(lab.DATA / "targets.json")
patterns = {
    "katawara": "(?:の)?(?:かたわら|傍ら)",
    "nara-de-wa": "ならでは(?:の|だ|です)?",
    "o-yogi-naku-sareru": "を余儀なくさ(?:れ|せ)(?:る|た|て|ない)?",
    "you-ni-mo-nai": "うにも[^。！？]*ない",
    "kirai-ga-aru": "きらいが(?:ある|あった|あり|あって)",
}
for target in targets:
    if target["kind"] == "grammar" and target["source"]["id"] in patterns:
        target["answer_pattern"] = patterns[target["source"]["id"]]
lab.write_json(lab.DATA / "targets.json", targets)

notes_file = lab.DATA / "editorial-notes.json"
notes = lab.read_json(notes_file) if notes_file.exists() else {}
for file in (lab.DATA / "batches").glob("*.json"):
    batch = lab.read_json(file)
    edited = False
    for q in batch["questions"]:
        if q["id"] not in changes or q.get("editorial_revision", {}).get("revision_id") == "pilot-six-v1":
            continue
        original = copy.deepcopy(q)
        archive = f"data/revisions/{q['id']}-before-pilot-six-v1.json"
        lab.write_json(lab.ROOT / archive, {"question": original, "checks_at_revision": lab.annotate([copy.deepcopy(q)])[0]})
        q.update(changes[q["id"]])
        if q["kind"] != "reading":
            lab.shuffled(q)
        q["editorial_revision"] = {"revision_id": "pilot-six-v1", "actor": "Codex 主代理", "created_at": lab.now(),
                                   "original_content_hash": lab.question_hash(original), "archive_file": archive,
                                   "reason_zh": "修复明确的接续、助词、活用或填空未考查目标语法问题。修订不等于用户人工审核。"}
        notes[q["id"]] = {"content_hash": lab.question_hash(q), "decision": "revised_pending_review", "reviewer": "Codex 主代理（非用户人工审核）",
                           "note_zh": "原稿的问题已由 Codex 改写，原稿与检查记录保存在 data/revisions/。修订稿仍待你核对。", "created_at": lab.now()}
        edited = True
        print("REVISED", q["id"])
    if edited:
        lab.write_json(file, batch)
lab.write_json(notes_file, notes)
lab.export()
