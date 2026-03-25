import random
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="FSP Terminoloji Quiz", page_icon="🩺", layout="wide")


@dataclass
class TermPair:
    colloquial_de: str
    medical_latin: str


def read_uploaded_text(file) -> str:
    """Read text from uploaded PDF or TXT."""
    if file is None:
        return ""

    file_name = file.name.lower()
    if file_name.endswith(".txt"):
        return file.getvalue().decode("utf-8", errors="ignore")

    if file_name.endswith(".pdf"):
        reader = PdfReader(file)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)

    return ""


def normalize_for_match(text: str) -> str:
    """Case-insensitive and umlaut-tolerant normalization."""
    text = text.strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s\-/,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_pairs_from_text(raw_text: str) -> List[TermPair]:
    """Extract colloquial-German / medical-Latin term pairs using flexible patterns."""
    pairs: List[TermPair] = []

    # Pattern 1: separators like / | ; : ->
    separator_pattern = re.compile(
        r"^\s*([^\n\r:;|\-]{2,80}?)\s*(?:/|\||;|:|->|=>|=)\s*([^\n\r]{2,120})\s*$"
    )

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or len(line) < 4:
            continue

        m = separator_pattern.match(line)
        if m:
            left = m.group(1).strip(" -\t")
            right = m.group(2).strip(" -\t")
            if left and right and left.lower() != right.lower():
                pairs.append(TermPair(colloquial_de=left, medical_latin=right))
            continue

        # Pattern 2: bracket forms (left (right))
        bracket_match = re.match(r"^(.{2,80}?)\s*\((.{2,120}?)\)\s*$", line)
        if bracket_match:
            left = bracket_match.group(1).strip()
            right = bracket_match.group(2).strip()
            if left and right and left.lower() != right.lower():
                pairs.append(TermPair(colloquial_de=left, medical_latin=right))

    return deduplicate_pairs(pairs)


def deduplicate_pairs(pairs: List[TermPair]) -> List[TermPair]:
    seen = set()
    unique = []
    for pair in pairs:
        key = (
            normalize_for_match(pair.colloquial_de),
            normalize_for_match(pair.medical_latin),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(pair)
    return unique


def parse_manual_pairs(text: str) -> List[TermPair]:
    return extract_pairs_from_text(text)


def answer_is_correct(user_answer: str, expected: str) -> bool:
    user_norm = normalize_for_match(user_answer)
    expected_options = [x.strip() for x in re.split(r"[,/;|]", expected) if x.strip()]
    expected_norms = [normalize_for_match(x) for x in expected_options] or [
        normalize_for_match(expected)
    ]

    if user_norm in expected_norms:
        return True

    # Fuzzy-like containment for close forms (e.g. slight word-order variants)
    for exp in expected_norms:
        if exp and (user_norm in exp or exp in user_norm):
            if abs(len(user_norm) - len(exp)) <= 4:
                return True

    return False


def init_state() -> None:
    defaults = {
        "pairs": [],
        "current_idx": None,
        "score": 0,
        "asked": 0,
        "wrong_pool": [],
        "mode": "Günlük Almanca → Latince",
        "history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def pick_next_question(use_wrong_pool: bool = False) -> int | None:
    pool = st.session_state["wrong_pool"] if use_wrong_pool else list(range(len(st.session_state["pairs"])))
    if not pool:
        return None
    return random.choice(pool)


def get_question_and_answer(pair: TermPair, mode: str) -> Tuple[str, str]:
    if mode == "Günlük Almanca → Latince":
        return pair.colloquial_de, pair.medical_latin
    return pair.medical_latin, pair.colloquial_de


def render_header() -> None:
    st.title("🩺 FSP Terminoloji Quiz (Hafif Sürüm)")
    st.caption(
        "PDF/TXT dosyandan terimleri çıkar, çift yönlü quiz yap, yanlışları tekrar çöz."
    )


def render_sidebar() -> None:
    st.sidebar.header("⚙️ Ayarlar")
    st.session_state["mode"] = st.sidebar.radio(
        "Quiz modu",
        ["Günlük Almanca → Latince", "Latince → Günlük Almanca"],
        index=0 if st.session_state["mode"] == "Günlük Almanca → Latince" else 1,
    )

    if st.sidebar.button("🔄 Skoru sıfırla"):
        st.session_state["score"] = 0
        st.session_state["asked"] = 0
        st.session_state["wrong_pool"] = []
        st.session_state["history"] = []
        st.session_state["current_idx"] = None
        st.sidebar.success("Skor ve geçmiş sıfırlandı.")


def render_ingestion_section() -> None:
    st.subheader("1) Dosya yükleme (PDF/TXT)")
    uploaded = st.file_uploader("Dosyanı yükle", type=["pdf", "txt"])

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📥 Dosyadan terimleri çıkar", use_container_width=True):
            raw_text = read_uploaded_text(uploaded)
            if not raw_text:
                st.warning("Önce PDF/TXT dosyası yükle.")
                return
            extracted = extract_pairs_from_text(raw_text)
            st.session_state["pairs"] = deduplicate_pairs(st.session_state["pairs"] + extracted)
            st.success(f"{len(extracted)} çift çıkarıldı. Toplam: {len(st.session_state['pairs'])}")

    with col_b:
        if st.button("🧪 Örnek veriyi yükle", use_container_width=True):
            with open("sample_data/fsp_terms_sample.txt", "r", encoding="utf-8") as f:
                extracted = extract_pairs_from_text(f.read())
            st.session_state["pairs"] = deduplicate_pairs(st.session_state["pairs"] + extracted)
            st.success(f"Örnekten {len(extracted)} çift eklendi. Toplam: {len(st.session_state['pairs'])}")


def render_manual_add_section() -> None:
    st.subheader("2) Manuel terim ekleme")
    st.markdown("Her satır için örnek format: `Böbrek taşı / Nephrolithiasis`")
    manual_text = st.text_area("Terim çiftleri", height=150, placeholder="Halsentzündung / Pharyngitis")

    if st.button("➕ Manuel listeyi ekle"):
        pairs = parse_manual_pairs(manual_text)
        if not pairs:
            st.warning("Uygun format bulunamadı. Ayraç olarak / | ; : kullan.")
            return
        st.session_state["pairs"] = deduplicate_pairs(st.session_state["pairs"] + pairs)
        st.success(f"{len(pairs)} manuel çift eklendi. Toplam: {len(st.session_state['pairs'])}")


def render_dataset_preview() -> None:
    st.subheader("3) Terim listesi")
    pairs = st.session_state["pairs"]
    if not pairs:
        st.info("Henüz terim yok. Dosya yükle veya manuel ekle.")
        return

    df = pd.DataFrame(
        [{"Günlük Almanca": p.colloquial_de, "Tıbbi/Latince": p.medical_latin} for p in pairs]
    )
    st.dataframe(df, use_container_width=True, height=240)


def render_quiz() -> None:
    st.subheader("4) Quiz")
    pairs = st.session_state["pairs"]
    if not pairs:
        st.info("Quiz başlatmak için önce en az 1 terim çifti ekle.")
        return

    cols = st.columns([1, 1, 1])
    with cols[0]:
        if st.button("🎯 Yeni soru", use_container_width=True):
            st.session_state["current_idx"] = pick_next_question(use_wrong_pool=False)
    with cols[1]:
        if st.button("🔁 Yanlışlardan sor", use_container_width=True):
            idx = pick_next_question(use_wrong_pool=True)
            if idx is None:
                st.warning("Yanlış havuzun boş.")
            st.session_state["current_idx"] = idx
    with cols[2]:
        st.metric("Puan", f"{st.session_state['score']} / {st.session_state['asked']}")

    idx = st.session_state["current_idx"]
    if idx is None:
        return

    pair = pairs[idx]
    question, answer = get_question_and_answer(pair, st.session_state["mode"])

    st.markdown(f"### ❓ Soru: **{question}**")
    user_answer = st.text_input("Cevabın", key=f"answer_{idx}_{st.session_state['asked']}")

    if st.button("✅ Cevabı kontrol et"):
        correct = answer_is_correct(user_answer, answer)
        st.session_state["asked"] += 1

        if correct:
            st.session_state["score"] += 1
            st.success("Doğru! 🎉")
            if idx in st.session_state["wrong_pool"]:
                st.session_state["wrong_pool"].remove(idx)
        else:
            st.error(f"Yanlış. Doğru cevap: {answer}")
            if idx not in st.session_state["wrong_pool"]:
                st.session_state["wrong_pool"].append(idx)

        st.session_state["history"].append(
            {
                "Soru": question,
                "Beklenen": answer,
                "Senin Cevabın": user_answer,
                "Durum": "Doğru" if correct else "Yanlış",
            }
        )

    if st.session_state["history"]:
        st.markdown("#### Son cevaplar")
        hist_df = pd.DataFrame(st.session_state["history"][-10:][::-1])
        st.dataframe(hist_df, use_container_width=True)


def main() -> None:
    init_state()
    render_header()
    render_sidebar()
    render_ingestion_section()
    st.divider()
    render_manual_add_section()
    st.divider()
    render_dataset_preview()
    st.divider()
    render_quiz()


if __name__ == "__main__":
    main()
